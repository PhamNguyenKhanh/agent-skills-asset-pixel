"""Review contact sheet PNG generator and zero-server HTML viewer exporter."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw

from pixel_forge.core.image_io import save_deterministic_png
from pixel_forge.core.palette import project_root
from pixel_forge.pixelize.operations import nearest_resize


def build_review_sheet(
    frames: Sequence[Image.Image],
    *,
    title: str,
    scale: int = 4,
    columns: int = 6,
) -> Image.Image:
    """Create a numbered checkerboard-backed contact sheet for rapid visual inspection."""
    if not frames:
        raise ValueError("Cannot build review sheet with zero frames.")
    fw, fh = frames[0].size
    cw, ch = fw * scale, fh * scale
    pad = 12
    header_h = 26
    label_h = 16
    cols = min(len(frames), max(1, columns))
    rows = (len(frames) + cols - 1) // cols

    total_w = max(240, cols * (cw + pad) + pad)
    total_h = header_h + rows * (ch + label_h + pad) + pad
    canvas = Image.new("RGBA", (total_w, total_h), (28, 28, 36, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 6), title, fill=(235, 238, 245, 255))

    for idx, frame in enumerate(frames):
        r, c = divmod(idx, cols)
        x0 = pad + c * (cw + pad)
        y0 = header_h + pad + r * (ch + label_h + pad)
        # Draw subtle dark checkerboard behind transparent pixels
        tile = max(4, scale * 2)
        for ty in range(0, ch, tile):
            for tx in range(0, cw, tile):
                col = (46, 48, 58, 255) if ((tx // tile + ty // tile) % 2 == 0) else (36, 38, 48, 255)
                draw.rectangle([x0 + tx, y0 + ty, min(x0 + cw - 1, x0 + tx + tile - 1), min(y0 + ch - 1, y0 + ty + tile - 1)], fill=col)
        up = nearest_resize(frame, scale)
        canvas.alpha_composite(up, dest=(x0, y0))
        draw.rectangle([x0, y0, x0 + cw - 1, y0 + ch - 1], outline=(90, 96, 114, 255), width=1)
        draw.text((x0 + 2, y0 + ch + 2), f"#{idx:02d}", fill=(190, 198, 215, 255))

    return canvas


def export_preview_bundle(
    frames: Sequence[Image.Image],
    out_dir: Path,
    *,
    asset_id: str,
    action: str = "idle",
    scale: int = 4,
    copy_html_viewers: bool = True,
) -> dict[str, Any]:
    """Save numbered review sheet PNG and copy zero-server HTML viewers into `preview/`."""
    preview_dir = out_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    review_img = build_review_sheet(frames, title=f"{asset_id} ({action}) - {len(frames)}f @ {scale}x", scale=scale)
    review_info = save_deterministic_png(review_img, preview_dir / f"{asset_id}_{action}_review.png")

    copied_html: list[str] = []
    if copy_html_viewers:
        tpl_dir = project_root() / "templates"
        if tpl_dir.is_dir():
            for html_file in sorted(tpl_dir.glob("*.html")):
                dest = preview_dir / html_file.name
                shutil.copy2(html_file, dest)
                copied_html.append(str(dest))

    return {
        "review_sheet": review_info,
        "html_viewers": copied_html,
    }
