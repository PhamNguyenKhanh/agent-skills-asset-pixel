"""Unified 3-track Animation Pipeline orchestrator (sheet / video / procedural)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from pixel_forge.animate.procedural_track import generate_procedural_frames
from pixel_forge.animate.sheet_track import run_sheet_track
from pixel_forge.animate.video_track import run_video_track
from pixel_forge.core.image_io import load_normalized_rgba
from pixel_forge.core.spec import AnimationSpec, FrameMeta
from pixel_forge.pixelize.operations import check_symmetry, mirror_sprite
from pixel_forge.providers.router import MediaRouter


@dataclass
class AnimationResult:
    status: str
    asset_id: str
    action: str
    track: str
    frames: list[Image.Image]
    frame_metas: list[FrameMeta]
    route: str
    model: str | None
    estimate_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)


def create_animation(
    asset_path: Path,
    spec: AnimationSpec,
    router: MediaRouter,
    out_dir: Path,
    *,
    dry_run: bool = False,
) -> AnimationResult:
    """Create a multi-frame pixel animation from an existing asset PNG and action description."""
    master_img, ingest_rep = load_normalized_rgba(asset_path)
    track = spec.track.strip().lower()

    if track == "auto":
        if router.offline:
            track = "procedural"
        elif router.has_route("video") and spec.action.lower() in ("walk", "run", "attack", "jump", "cast"):
            track = "video"
        elif router.has_route("image"):
            track = "sheet"
        else:
            track = "procedural"

    if track not in ("sheet", "video", "procedural"):
        raise ValueError(f"Unsupported animation track {track!r}. Use 'auto', 'sheet', 'video', or 'procedural'.")

    out_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    if track == "procedural":
        if dry_run:
            return AnimationResult(
                status="dry_run",
                asset_id=spec.asset_id,
                action=spec.action,
                track="procedural",
                frames=[],
                frame_metas=spec.default_frames(),
                route="offline:procedural",
                model="procedural-physics-v1",
                estimate_usd=0.0,
                report={"source": str(asset_path), "frame_count": spec.frame_count, "fps": spec.fps},
            )
        frames, rep = generate_procedural_frames(master_img, spec)
    elif track == "sheet":
        frames, rep = run_sheet_track(asset_path, master_img, spec, router, out_dir, dry_run=dry_run)
        if dry_run:
            return AnimationResult(
                status="dry_run",
                asset_id=spec.asset_id,
                action=spec.action,
                track="sheet",
                frames=[],
                frame_metas=spec.default_frames(),
                route=str(rep.get("route", "none")),
                model=rep.get("model"),
                estimate_usd=float(rep.get("estimate_usd", 0.0)),
                report=rep,
            )
    else:
        frames, rep = run_video_track(asset_path, master_img, spec, router, out_dir, dry_run=dry_run)
        if dry_run:
            return AnimationResult(
                status="dry_run",
                asset_id=spec.asset_id,
                action=spec.action,
                track="video",
                frames=[],
                frame_metas=spec.default_frames(),
                route=str(rep.get("route", "none")),
                model=rep.get("model"),
                estimate_usd=float(rep.get("estimate_usd", 0.0)),
                report=rep,
            )

    # Explicit mirroring guard (from pixel-studio: never silently mirror asymmetric art).
    if spec.mirror_direction:
        sym_score = check_symmetry(master_img, axis=spec.mirror_direction)
        if sym_score < 0.70 and not spec.allow_asymmetric_mirror:
            warnings.append(
                f"Mirror skipped: master sprite symmetry is {sym_score:.2f} (<0.70). "
                "Pass --allow-asymmetric-mirror to force mirroring."
            )
        else:
            frames = [mirror_sprite(f, axis=spec.mirror_direction) for f in frames]
            rep["mirrored"] = spec.mirror_direction

    # Build FrameMeta list with any detected motion events (e.g. hit, footstep, land).
    events_map = rep.get("events") or {}
    if isinstance(rep.get("timing"), dict) and "peak_frame_index" in rep["timing"]:
        events_map.setdefault(rep["timing"]["peak_frame_index"], "peak")
    dur = spec.frame_duration_ms
    metas = [
        FrameMeta(
            index=idx,
            duration_ms=dur,
            name=f"{spec.asset_id}_{spec.action}_{idx:02d}",
            event=events_map.get(idx),
        )
        for idx in range(len(frames))
    ]

    rep["ingest"] = ingest_rep
    return AnimationResult(
        status="ok",
        asset_id=spec.asset_id,
        action=spec.action,
        track=track,
        frames=frames,
        frame_metas=metas,
        route=str(rep.get("route", f"offline:{track}")),
        model=rep.get("model"),
        estimate_usd=float(rep.get("estimate_usd", 0.0)),
        warnings=warnings,
        report=rep,
    )
