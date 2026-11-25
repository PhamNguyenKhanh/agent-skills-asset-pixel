"""Local CLI route discovery and invocation (Codex CLI / Grok CLI)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pixel_forge.core.image_io import sha256_file
from pixel_forge.providers.base import MediaRequest, MediaResult, ProviderCapabilities, ProviderError

CLI_CAPABILITIES: dict[tuple[str, str], ProviderCapabilities] = {
    ("codex-cli", "image"): ProviderCapabilities(
        name="codex-cli",
        family="local",
        kind="image",
        default_model="codex-imagegen",
        max_references=5,
        supports_transparent=False,
        estimate_usd=0.0,
    ),
    ("grok-cli", "image"): ProviderCapabilities(
        name="grok-cli",
        family="local",
        kind="image",
        default_model="grok-imagegen",
        max_references=1,
        supports_transparent=False,
        estimate_usd=0.0,
    ),
}


def available_local_clis() -> dict[str, str | None]:
    return {
        "codex-cli": shutil.which("codex"),
        "grok-cli": shutil.which("grok"),
    }


def call_local_cli(provider: str, req: MediaRequest) -> MediaResult:
    """Invoke a local signed-in CLI if installed, else raise retryable NOT_INSTALLED error."""
    binary = available_local_clis().get(provider)
    if not binary:
        raise ProviderError(
            f"{provider}: CLI binary not found on PATH",
            code="not_installed",
            retryable_next_route=True,
        )
    req.out_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = req.out_dir / "prompt.txt"
    prompt_file.write_text(req.prompt, encoding="utf-8")
    out_file = req.out_dir / "generated.png"

    if provider == "codex-cli":
        cmd = [binary, "exec", "--ephemeral", f"Generate a single PNG image saved to {out_file.name}: {req.prompt}"]
        done = subprocess.run(cmd, cwd=str(req.out_dir), capture_output=True, text=True, timeout=180)
        if done.returncode != 0 or not out_file.is_file():
            raise ProviderError(
                f"codex-cli failed (exit {done.returncode})",
                code="cli_failed",
                retryable_next_route=True,
            )
        return MediaResult(
            status="ok",
            route="local:codex-cli",
            model="codex-imagegen",
            artifact_path=out_file,
            sha256=sha256_file(out_file),
            estimate_usd=0.0,
        )

    raise ProviderError(f"{provider}: unsupported local CLI invocation", code="unsupported", retryable_next_route=True)
