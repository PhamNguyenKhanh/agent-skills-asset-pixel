"""Unified export orchestrator: PNG + GIF + .aseprite + Unity 6 + Preview in one call."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from PIL import Image

from pixel_forge.core.spec import ExportSpec, FrameMeta, SpatialMeta
from pixel_forge.export.aseprite import write_aseprite, write_aseprite_lua
from pixel_forge.export.gif import write_gif
from pixel_forge.export.png import export_png_package
from pixel_forge.export.preview import export_preview_bundle
from pixel_forge.export.unity import export_unity_bundle


def export_bundle(
    frames: Sequence[Image.Image],
    out_dir: Path,
    *,
    asset_id: str,
    action: str = "idle",
    fps: int = 8,
    playback: str = "loop",
    frame_metas: Sequence[FrameMeta] | None = None,
    spatial: SpatialMeta | None = None,
    export_spec: ExportSpec | None = None,
) -> dict[str, Any]:
    """Export any sprite or animation frame list to all requested formats cleanly."""
    if not frames:
        raise ValueError("No frames provided to export_bundle.")
    spec = export_spec or ExportSpec()
    fw, fh = frames[0].size
    sp = spatial or SpatialMeta.default_for(fw, fh)
    default_dur = max(10, round(1000 / max(1, fps)))
    metas = list(frame_metas) if frame_metas else [
        FrameMeta(index=i, duration_ms=default_dur, name=f"{asset_id}_{action}_{i:02d}")
        for i in range(len(frames))
    ]
    durations = [m.duration_ms for m in metas]

    out_dir.mkdir(parents=True, exist_ok=True)
    exported: dict[str, Any] = {"output_dir": str(out_dir), "formats": list(spec.formats)}

    if "png" in spec.formats:
        exported["png"] = export_png_package(
            frames,
            metas,
            out_dir,
            asset_id=asset_id,
            action=action,
            playback=playback,
            spatial=sp,
            columns=spec.sheet_columns,
            padding=spec.sheet_padding,
            preview_scale=spec.preview_scale,
        )

    if "gif" in spec.formats:
        gif_dir = out_dir / "gif"
        gif_dir.mkdir(parents=True, exist_ok=True)
        exported["gif"] = write_gif(
            frames,
            durations,
            gif_dir / f"{asset_id}_{action}.gif",
            playback=playback,
            scale=1,
        )
        if spec.preview_scale > 1:
            exported["gif_preview"] = write_gif(
                frames,
                durations,
                gif_dir / f"{asset_id}_{action}_{spec.preview_scale}x.gif",
                playback=playback,
                scale=spec.preview_scale,
            )

    if "aseprite" in spec.formats:
        ase_dir = out_dir / "aseprite"
        ase_dir.mkdir(parents=True, exist_ok=True)
        exported["aseprite"] = write_aseprite(
            frames,
            durations,
            ase_dir / f"{asset_id}_{action}.aseprite",
            tag_name=action,
            playback=playback,
            pivot=(sp.pivot_x, sp.pivot_y),
        )

    if spec.emit_lua:
        lua_dir = out_dir / "lua"
        lua_dir.mkdir(parents=True, exist_ok=True)
        exported["lua"] = write_aseprite_lua(
            frames,
            durations,
            lua_dir / f"{asset_id}_{action}.lua",
            asset_id=asset_id,
            action=action,
            spatial=sp,
        )

    if "unity" in spec.formats:
        exported["unity"] = export_unity_bundle(
            frames,
            metas,
            out_dir,
            asset_id=asset_id,
            action=action,
            fps=fps,
            playback=playback,
            pixels_per_unit=spec.pixels_per_unit,
            spatial=sp,
        )

    if spec.emit_html_preview:
        exported["preview"] = export_preview_bundle(
            frames,
            out_dir,
            asset_id=asset_id,
            action=action,
            scale=spec.preview_scale,
            copy_html_viewers=True,
        )

    return exported
