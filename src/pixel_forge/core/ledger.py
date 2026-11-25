"""Cost ledger, budget guardrails, and secret redaction for AI provider calls."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

LEDGER_REL_PATH = Path(".forge") / "ledger.jsonl"

SECRET_ENV_KEYS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "XAI_API_KEY",
    "FAL_KEY",
    "ARK_API_KEY",
)


def redact_secrets(text: object, extra_secrets: Iterable[str] = ()) -> str:
    """Replace any configured secret values with '[redacted]' before logging or printing."""
    result = str(text)
    secrets: list[str] = []
    for key in SECRET_ENV_KEYS:
        val = os.environ.get(key)
        if val and len(val) >= 8:
            secrets.append(val)
    for extra in extra_secrets:
        if extra and len(extra) >= 8:
            secrets.append(extra)
    for secret in secrets:
        result = result.replace(secret, "[redacted]")
    return result


class SpendLedger:
    """Append-only JSONL ledger at `<project>/.forge/ledger.jsonl` enforcing optional spend/call caps."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path.cwd()).resolve()
        self.path = self.root / LEDGER_REL_PATH

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def summary(self) -> dict[str, Any]:
        rows = self.entries()
        total_usd = 0.0
        paid_calls = 0
        by_route: dict[str, int] = {}
        for row in rows:
            route = str(row.get("route", "unknown"))
            by_route[route] = by_route.get(route, 0) + 1
            est = row.get("estimate_usd")
            if isinstance(est, (int, float)) and est > 0:
                total_usd += float(est)
                paid_calls += 1
        return {
            "ledger_path": str(self.path),
            "total_calls": len(rows),
            "paid_calls": paid_calls,
            "total_estimate_usd": round(total_usd, 6),
            "by_route": by_route,
        }

    def check_budget(
        self,
        next_estimate_usd: float,
        *,
        budget_usd: float | None = None,
        max_calls: int | None = None,
    ) -> None:
        """Raise PermissionError if the next call would exceed configured spend or call caps."""
        if budget_usd is None:
            env_budget = os.environ.get("PIXEL_FORGE_BUDGET_USD")
            if env_budget:
                budget_usd = float(env_budget)
        if max_calls is None:
            env_calls = os.environ.get("PIXEL_FORGE_MAX_CALLS")
            if env_calls:
                max_calls = int(env_calls)

        stats = self.summary()
        if max_calls is not None and stats["paid_calls"] + (1 if next_estimate_usd > 0 else 0) > max_calls:
            raise PermissionError(
                f"Paid call cap exceeded: {stats['paid_calls']} already used, max_calls={max_calls}."
            )
        if budget_usd is not None and stats["total_estimate_usd"] + max(0.0, next_estimate_usd) > budget_usd:
            raise PermissionError(
                f"Budget cap exceeded: ${stats['total_estimate_usd']:.4f} used + "
                f"${next_estimate_usd:.4f} > limit ${budget_usd:.4f}."
            )

    def record(
        self,
        *,
        kind: str,
        route: str,
        model: str | None,
        estimate_usd: float,
        status: str,
        artifact_path: str | None = None,
        artifact_sha256: str | None = None,
        job_id: str | None = None,
        note: str | None = None,
        extra_secrets: Iterable[str] = (),
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "route": route,
            "model": model,
            "estimate_usd": round(float(estimate_usd), 6),
            "status": status,
            "artifact_path": artifact_path,
            "artifact_sha256": artifact_sha256,
            "job_id": job_id,
            "note": redact_secrets(note, extra_secrets) if note else None,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact_secrets(json.dumps(entry, ensure_ascii=True, separators=(",", ":")), extra_secrets)
        with self.path.open("a", encoding="utf-8", newline="\n") as fp:
            fp.write(line + "\n")
        return entry
