"""Base data types and error hierarchy for media providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class ProviderError(RuntimeError):
    """Structured error raised by a provider adapter."""

    def __init__(self, message: str, *, code: str = "provider_error", retryable_next_route: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable_next_route = retryable_next_route


@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    family: str  # api | local | offline
    kind: str  # image | video
    default_model: str
    max_references: int
    supports_transparent: bool = False
    supports_last_frame: bool = False
    estimate_usd: float = 0.0
    env_vars: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MediaRequest:
    kind: str  # image | video
    prompt: str
    out_dir: Path
    references: list[Path] = field(default_factory=list)
    last_frame: Path | None = None
    size: str = "1024x1024"
    duration_seconds: int = 6
    resolution: str = "720p"
    transparent: bool = False
    model: str | None = None
    seed: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutePlan:
    kind: str
    requested_route: str
    selected_route: str | None
    model: str | None
    estimate_usd: float
    references_count: int
    notes: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MediaResult:
    status: str  # ok | dry_run | no_route
    route: str
    model: str | None
    artifact_path: Path | None
    sha256: str | None = None
    estimate_usd: float = 0.0
    job_id: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "route": self.route,
            "model": self.model,
            "artifact_path": str(self.artifact_path) if self.artifact_path else None,
            "sha256": self.sha256,
            "estimate_usd": self.estimate_usd,
            "job_id": self.job_id,
            "notes": self.notes,
        }
