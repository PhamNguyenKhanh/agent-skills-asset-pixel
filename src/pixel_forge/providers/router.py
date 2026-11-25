"""Multi-provider MediaRouter with capability checks, dry-run planning, cost ledger, and failover."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pixel_forge.core.ledger import SpendLedger
from pixel_forge.providers.api_adapters import API_CAPABILITIES, dispatch_api
from pixel_forge.providers.base import MediaRequest, MediaResult, ProviderCapabilities, ProviderError, RoutePlan
from pixel_forge.providers.cli_adapters import CLI_CAPABILITIES, available_local_clis, call_local_cli
from pixel_forge.providers.config import configured_model, get_api_key, known_secrets, preferred_order
from pixel_forge.providers.simulated import SIMULATED_CAPABILITIES, call_simulated

DEFAULT_API_ORDER: dict[str, tuple[str, ...]] = {
    "image": ("gemini", "openai", "openrouter", "xai", "fal"),
    "video": ("xai", "fal"),
}

DEFAULT_CLI_ORDER: dict[str, tuple[str, ...]] = {
    "image": ("codex-cli", "grok-cli"),
    "video": (),
}


class MediaRouter:
    """Unified entry point for all image and video generation requests."""

    def __init__(
        self,
        *,
        route: str = "auto",
        project_root: Path | None = None,
        budget_usd: float | None = None,
        max_calls: int | None = None,
        offline: bool = False,
    ) -> None:
        self.route = "simulated" if offline else route.strip().lower()
        self.ledger = SpendLedger(project_root)
        self.budget_usd = budget_usd
        self.max_calls = max_calls
        self.offline = offline

    def _candidate_routes(self, kind: str) -> list[tuple[str, ProviderCapabilities]]:
        pref = preferred_order(kind)
        api_names = list(DEFAULT_API_ORDER.get(kind, ()))
        ordered_api = [p for p in pref if p in api_names] + [p for p in api_names if p not in pref]
        cli_names = list(DEFAULT_CLI_ORDER.get(kind, ()))

        all_routes: list[tuple[str, ProviderCapabilities]] = []
        for name in ordered_api:
            cap = API_CAPABILITIES.get((name, kind))
            if cap:
                all_routes.append((f"api:{name}", cap))
        for name in cli_names:
            cap = CLI_CAPABILITIES.get((name, kind))
            if cap:
                all_routes.append((f"local:{name}", cap))

        if self.route == "simulated":
            return [("offline:simulated", SIMULATED_CAPABILITIES[kind])]
        if self.route == "auto":
            return all_routes
        if self.route == "api":
            return [item for item in all_routes if item[0].startswith("api:")]
        if self.route == "local":
            return [item for item in all_routes if item[0].startswith("local:")]
        return [item for item in all_routes if item[0].split(":", 1)[1] == self.route]

    def resolve(self, req: MediaRequest) -> RoutePlan:
        """Resolve which provider would run without calling any remote service or writing files."""
        candidates = self._candidate_routes(req.kind)
        skipped: list[dict[str, str]] = []
        clis = available_local_clis()

        for route_id, cap in candidates:
            if len(req.references) > cap.max_references:
                skipped.append({"route": route_id, "reason": f"max_references={cap.max_references} < {len(req.references)}"})
                continue
            if cap.family == "api" and not get_api_key(cap.name):
                skipped.append({"route": route_id, "reason": "API key not configured"})
                continue
            if cap.family == "local" and not clis.get(cap.name):
                skipped.append({"route": route_id, "reason": "Local CLI binary not installed"})
                continue

            model = req.model or configured_model(cap.name, req.kind) or cap.default_model
            notes: list[str] = []
            if req.transparent and not cap.supports_transparent:
                notes.append("Provider lacks native alpha; pipeline will use solid chroma-key background + matte removal.")
            if req.last_frame and not cap.supports_last_frame:
                notes.append("Provider does not pin last frame; last_frame will be ignored.")
            return RoutePlan(
                kind=req.kind,
                requested_route=self.route,
                selected_route=route_id,
                model=model,
                estimate_usd=cap.estimate_usd,
                references_count=len(req.references),
                notes=notes,
                skipped=skipped,
            )

        return RoutePlan(
            kind=req.kind,
            requested_route=self.route,
            selected_route=None,
            model=None,
            estimate_usd=0.0,
            references_count=len(req.references),
            notes=["No configured AI provider available; use --offline / direct / procedural fallback or set an API key."],
            skipped=skipped,
        )

    def has_route(self, kind: str) -> bool:
        dummy = MediaRequest(kind=kind, prompt="", out_dir=Path("."))
        return self.resolve(dummy).selected_route is not None

    def execute(self, req: MediaRequest, *, dry_run: bool = False) -> MediaResult:
        """Resolve, budget-check, execute with clean failover, and record to `.forge/ledger.jsonl`."""
        plan = self.resolve(req)
        if dry_run:
            return MediaResult(
                status="dry_run",
                route=plan.selected_route or "none",
                model=plan.model,
                artifact_path=None,
                estimate_usd=plan.estimate_usd,
                notes=plan.notes,
            )
        if not plan.selected_route:
            return MediaResult(
                status="no_route",
                route="none",
                model=None,
                artifact_path=None,
                estimate_usd=0.0,
                notes=plan.notes,
            )

        self.ledger.check_budget(plan.estimate_usd, budget_usd=self.budget_usd, max_calls=self.max_calls)

        candidates = self._candidate_routes(req.kind)
        # Start from the resolved candidate and allow clean account-level failover to subsequent routes.
        started = False
        last_err: ProviderError | None = None
        secrets = known_secrets()

        for route_id, cap in candidates:
            if not started:
                if route_id != plan.selected_route:
                    continue
                started = True
            if cap.family == "api" and not get_api_key(cap.name):
                continue
            model = req.model or configured_model(cap.name, req.kind) or cap.default_model
            try:
                if cap.family == "offline":
                    result = call_simulated(req)
                elif cap.family == "api":
                    result = dispatch_api(cap.name, req, model, cap.estimate_usd)
                else:
                    result = call_local_cli(cap.name, req)
                self.ledger.record(
                    kind=req.kind,
                    route=result.route,
                    model=result.model,
                    estimate_usd=result.estimate_usd,
                    status="ok",
                    artifact_path=str(result.artifact_path) if result.artifact_path else None,
                    artifact_sha256=result.sha256,
                    job_id=result.job_id,
                    extra_secrets=secrets,
                )
                return result
            except ProviderError as exc:
                last_err = exc
                self.ledger.record(
                    kind=req.kind,
                    route=route_id,
                    model=model,
                    estimate_usd=0.0,
                    status=f"error:{exc.code}",
                    note=str(exc),
                    extra_secrets=secrets,
                )
                if not exc.retryable_next_route:
                    raise

        if last_err:
            raise last_err
        return MediaResult(status="no_route", route="none", model=None, artifact_path=None)

    def doctor_report(self) -> dict[str, Any]:
        """Summarize available API keys (yes/no only), local CLIs, resolved routes, and ledger stats."""
        img_plan = self.resolve(MediaRequest(kind="image", prompt="", out_dir=Path(".")))
        vid_plan = self.resolve(MediaRequest(kind="video", prompt="", out_dir=Path(".")))
        return {
            "api_keys": {p: bool(get_api_key(p)) for p in ("gemini", "openai", "openrouter", "xai", "fal")},
            "local_clis": {k: bool(v) for k, v in available_local_clis().items()},
            "resolved_image_route": img_plan.selected_route,
            "resolved_video_route": vid_plan.selected_route,
            "ledger": self.ledger.summary(),
        }
