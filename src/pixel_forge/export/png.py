"""PNG exporter: individual frames, horizontal/grid spritesheet, indexed PNG-8, scaled preview, and JSON metadata."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence

from PIL import Image

from pixel_forge.core.image_io import save_deterministic_png
from pixel_forge.core.spec import FrameMeta, SpatialMeta
from pixel_forge.pixelize.operations import nearest_resize


def export_indexed_png(image: Image.Image, path: Path, *, max_colors: int = 255) -> dict[str, Any]:
    """Convert an RGBA pixel-art image to crisp indexed PNG-8 preserving slot 255 for transparency."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    transparent_mask = alpha.point(lambda v: 255 if v < 128 else 0)
    has_transparent = transparent_mask.getbbox() is not None

    rgb = rgba.convert("RGB")
    colors_budget = min(255, max(1, max_colors))
    indexed = rgb.quantize(colors=colors_budget, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    if has_transparent:
        indexed.paste(255, (0, 0, rgba.width, rgba.height), transparent_mask)
        pal = bytes(indexed.getpalette()[: 3 * 255]).ljust(768, b"\0")
        indexed.putpalette(pal)

    path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs: dict[str, Any] = {"format": "PNG", "compress_level": 6, "optimize": False}
    if has_transparent:
        save_kwargs["transparency"] = 255
    indexed.save(path, **save_kwargs)
    return {"path": str(path), "width": indexed.width, "height": indexed.height, "mode": "P", "transparent_index": 255 if has_transparent else None}


def pack_spritesheet(
    frames: Sequence[Image.Image],
    *,
    columns: int | None = None,
    padding: int = 0,
) -> tuple[Image.Image, list[dict[str, int]]]:
    """Pack uniform frames into a horizontal strip (default) or grid sprite sheet."""
    if not frames:
        raise ValueError("Cannot pack an empty frame sequence.")
    fw, fh = frames[0].size
    n = len(frames)
    cols = min(n, columns) if columns and columns > 0 else n
    rows = math.ceil(n / cols)
    sheet_w = cols * fw + max(0, cols - 1) * padding
    sheet_h = rows * fh + max(0, rows - 1) * padding

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    rects: list[dict[str, int]] = []
    for idx, frame in enumerate(frames):
        r, c = divmod(idx, cols)
        x = c * (fw + padding)
        y = r * (fh + padding)
        rgba = frame.convert("RGBA")
        if rgba.size != (fw, fh):
            rgba = rgba.resize((fw, fh), Image.Resampling.NEAREST)
        sheet.paste(rgba, (x, y))
        rects.append({"x": x, "y": y, "w": fw, "h": fh})
    return sheet, rects


def export_png_package(
    frames: Sequence[Image.Image],
    frame_metas: Sequence[FrameMeta],
    out_dir: Path,
    *,
    asset_id: str,
    action: str = "idle",
    playback: str = "loop",
    spatial: SpatialMeta | None = None,
    columns: int | None = None,
    padding: int = 0,
    preview_scale: int = 4,
) -> dict[str, Any]:
    """Write individual PNGs, spritesheet, indexed PNG, scaled preview, atlas.json, and spatial.json."""
    if not frames:
        raise ValueError("No frames to export.")
    fw, fh = frames[0].size
    sp = spatial or SpatialMeta.default_for(fw, fh)

    frames_dir = out_dir / "frames"
    png_dir = out_dir / "png"
    sheet_dir = out_dir / "sheet"
    preview_dir = out_dir / "preview"
    meta_dir = out_dir / "metadata"
    for d in (frames_dir, png_dir, sheet_dir, preview_dir, meta_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Save individual frames
    saved_frames: list[dict[str, Any]] = []
    for idx, frame in enumerate(frames):
        f_path = frames_dir / f"{asset_id}_{action}_{idx:03d}.png"
        saved_frames.append(save_deterministic_png(frame.convert("RGBA"), f_path))

    # Save static / poster PNG and indexed PNG-8
    poster_info = save_deterministic_png(frames[0].convert("RGBA"), png_dir / f"{asset_id}.png")
    indexed_info = export_indexed_png(frames[0], png_dir / f"{asset_id}_indexed.png")

    # Pack spritesheet + integer scaled preview
    sheet_img, rects = pack_spritesheet(frames, columns=columns, padding=padding)
    sheet_path = sheet_dir / f"{asset_id}_{action}_sheet.png"
    sheet_info = save_deterministic_png(sheet_img, sheet_path)
    preview_sheet = nearest_resize(sheet_img, max(1, preview_scale))
    preview_info = save_deterministic_png(preview_sheet, preview_dir / f"{asset_id}_{action}_sheet_{preview_scale}x.png")

    # Aseprite-compatible JSON atlas (works with Phaser, PixiJS, Godot, Unity, and HTML sprite_sheet.html)
    atlas_frames: list[dict[str, Any]] = []
    for idx, rect in enumerate(rects):
        fm = frame_metas[idx] if idx < len(frame_metas) else FrameMeta(index=idx)
        entry: dict[str, Any] = {
            "filename": fm.name or f"{asset_id}_{action}_{idx:03d}",
            "frame": rect,
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": fw, "h": fh},
            "sourceSize": {"w": fw, "h": fh},
            "duration": fm.duration_ms,
        }
        if fm.event:
            entry["event"] = fm.event
        atlas_frames.append(entry)

    atlas_doc = {
        "frames": atlas_frames,
        "meta": {
            "app": "pixel-forge",
            "version": "1.0.0",
            "image": sheet_path.name,
            "format": "RGBA8888",
            "size": {"w": sheet_img.width, "h": sheet_img.height},
            "scale": "1",
            "frameSize": {"w": fw, "h": fh},
            "pivot": {"x": sp.pivot_x, "y": sp.pivot_y},
            "frameTags": [
                {
                    "name": action,
                    "from": 0,
                    "to": len(frames) - 1,
                    "direction": "pingpong" if playback == "ping_pong" else "forward",
                }
            ],
        },
    }
    atlas_path = meta_dir / f"{asset_id}_{action}.atlas.json"
    atlas_path.write_text(json.dumps(atlas_doc, indent=2) + "\n", encoding="utf-8")

    spatial_doc = {
        "asset_id": asset_id,
        "canvas": {"width": fw, "height": fh},
        "animation": {
            "is_animated": len(frames) > 1,
            "action": action,
            "frame_count": len(frames),
            "playback": playback,
            "durations_ms": [f["duration"] for f in atlas_frames],
        },
        "spatial": sp.to_dict(),
    }
    spatial_path = meta_dir / f"{asset_id}.spatial.json"
    spatial_path.write_text(json.dumps(spatial_doc, indent=2) + "\n", encoding="utf-8")

    return {
        "poster": poster_info,
        "indexed": indexed_info,
        "sheet": sheet_info,
        "sheet_rects": rects,
        "preview": preview_info,
        "frames": saved_frames,
        "atlas_json": str(atlas_path),
        "spatial_json": str(spatial_path),
    }
