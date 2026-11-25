"""Track A — Anchor-locked Sprite Sheet animation generation via image-to-image."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from pixel_forge.animate.timing import lock_static_zone, register_frames_to_anchor
from pixel_forge.core.image_io import load_normalized_rgba, save_deterministic_png
from pixel_forge.core.palette import extract_palette, remap_image_to_palette
from pixel_forge.core.presets import get_preset
from pixel_forge.core.spec import AnimationSpec
from pixel_forge.pixelize.grid_unzoom import unzoom_to_grid
from pixel_forge.pixelize.matte import quiet_key_color, remove_background
from pixel_forge.pixelize.operations import fit_canvas
from pixel_forge.providers.base import MediaRequest
from pixel_forge.providers.router import MediaRouter


def _grid_dims(frame_count: int) -> tuple[int, int]:
    cols = min(frame_count, max(2, math.ceil(math.sqrt(frame_count))))
    rows = math.ceil(frame_count / cols)
    return cols, rows


def make_layout_guide(
    master: Image.Image,
    frame_count: int,
    key_rgb: tuple[int, int, int],
    *,
    cell_scale: int = 4,
) -> tuple[Image.Image, int, int, int, int]:
    """Create an anchor-locked sprite-sheet layout guide image with Frame 1 stamped in cell 0."""
    cols, rows = _grid_dims(frame_count)
    cell_w = max(64, master.width * cell_scale)
    cell_h = max(64, master.height * cell_scale)
    guide = Image.new("RGBA", (cols * cell_w, rows * cell_h), (*key_rgb, 255))
    draw = ImageDraw.Draw(guide)

    # Subtle guide borders (contrasting slightly against key) & master stamped in cell (0,0)
    up_master = master.resize((cell_w, cell_h), Image.Resampling.NEAREST)
    guide.alpha_composite(up_master, dest=(0, 0))
    border_col = (240, 240, 240, 255) if sum(key_rgb) < 400 else (30, 30, 30, 255)
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * cell_w, r * cell_h
            draw.rectangle([x0, y0, x0 + cell_w - 1, y0 + cell_h - 1], outline=border_col, width=1)
    return guide, cols, rows, cell_w, cell_h


def run_sheet_track(
    master_path: Path,
    master_img: Image.Image,
    spec: AnimationSpec,
    router: MediaRouter,
    out_dir: Path,
    *,
    dry_run: bool = False,
) -> tuple[list[Image.Image], dict[str, Any]]:
    """Generate an N-frame animation sprite sheet from the master sprite using image-to-image."""
    preset = get_preset(spec.preset)
    key_name, key_rgb = quiet_key_color(master_img)
    cols, rows = _grid_dims(spec.frame_count)

    raw_dir = out_dir / "_raw_sheet"
    raw_dir.mkdir(parents=True, exist_ok=True)
    guide_img, cols, rows, cell_w, cell_h = make_layout_guide(master_img, spec.frame_count, key_rgb)
    guide_path = raw_dir / "layout_guide.png"
    save_deterministic_png(guide_img, guide_path)

    prompt = (
        f"Create a clean {cols}x{rows} grid sprite sheet ({spec.frame_count} sequential animation frames, row-major order) "
        f"for the EXACT character/object in the reference image performing action '{spec.action}': {spec.brief or spec.action}. "
        f"Style: {preset.prompt_style_clause}. "
        "Keep exact identity, proportions, palette colors, pixel density, and consistent footline across every frame. "
        f"Place every frame cleanly inside its grid cell on a completely flat solid {key_name} background with zero grid lines, "
        "no text, no anti-aliasing, and no cropping at cell edges."
    )
    req = MediaRequest(
        kind="image",
        prompt=prompt,
        out_dir=raw_dir,
        references=[master_path, guide_path],
        size="1024x1024",
        extra={
            "key_rgb": key_rgb,
            "sheet_cols": cols,
            "sheet_rows": rows,
            "cell_w": cell_w,
            "cell_h": cell_h,
        },
    )
    media = router.execute(req, dry_run=dry_run)
    if dry_run:
        return [], {
            "status": "dry_run",
            "track": "sheet",
            "route": media.route,
            "model": media.model,
            "estimate_usd": media.estimate_usd,
            "grid": [cols, rows],
            "key_color": key_name,
            "compiled_prompt": prompt,
        }
    if media.status != "ok" or media.artifact_path is None:
        raise RuntimeError(f"Sheet animation track has no available image route: {media.notes}")

    sheet_img, _ = load_normalized_rgba(media.artifact_path)
    cw = sheet_img.width // cols
    ch = sheet_img.height // rows
    master_pal = extract_palette(master_img, max_colors=preset.max_colors, name=f"{spec.asset_id}_master")
    align = "bottom" if preset.enforce_ground_alignment else "center"

    frames: list[Image.Image] = []
    for idx in range(spec.frame_count):
        r_idx, c_idx = divmod(idx, cols)
        cell = sheet_img.crop((c_idx * cw, r_idx * ch, (c_idx + 1) * cw, (r_idx + 1) * ch))
        keyed, _ = remove_background(cell, key_color=key_rgb, binarize_alpha=True)
        unzoomed, _ = unzoom_to_grid(keyed)
        fitted = fit_canvas(unzoomed, master_img.size, fit_mode="contain", align=align, padding=0)
        if spec.lock_palette:
            fitted, _ = remap_image_to_palette(fitted, master_pal, policy="strict")
        frames.append(fitted)

    frames = register_frames_to_anchor(master_img, frames, lock_bottom=preset.enforce_ground_alignment)
    frames = lock_static_zone(
        master_img,
        frames,
        bottom_rows=spec.lock_static_bottom_rows,
        preserve_ground_shadow_alpha=preset.allow_ground_shadow_alpha,
    )
    return frames, {
        "status": "ok",
        "track": "sheet",
        "route": media.route,
        "model": media.model,
        "estimate_usd": media.estimate_usd,
        "grid": [cols, rows],
        "key_color": key_name,
        "raw_sheet": str(media.artifact_path),
    }
