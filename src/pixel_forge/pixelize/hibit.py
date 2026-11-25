"""Hi-bit pixelization engine: luminance-weighted k-means++ palette, majority-vote downscale,
temporal hysteresis, lone-pixel cleanup, and auto hue-shifted outlining.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from pixel_forge.core.palette import (
    Palette,
    RGB_WEIGHTS,
    auto_outline_color,
    index_rgb,
    kmeans_palette,
    parse_hex,
)
from pixel_forge.pixelize.operations import add_outline

TRANSPARENT = -1


def _majority_vote_downsample(
    index_map: np.ndarray,
    target_w: int,
    target_h: int,
    n_colors: int,
    *,
    coverage: float = 0.45,
    prev_map: np.ndarray | None = None,
    hold_share: float = 0.80,
    coverage_hold: float = 0.12,
) -> np.ndarray:
    """Downscale an indexed map via strict majority vote per output cell (never color-blending)."""
    src_h, src_w = index_map.shape
    out = np.full((target_h, target_w), TRANSPARENT, dtype=np.int32)

    ys = np.linspace(0, src_h, target_h + 1, dtype=np.int32)
    xs = np.linspace(0, src_w, target_w + 1, dtype=np.int32)

    for r in range(target_h):
        y0, y1 = int(ys[r]), max(int(ys[r]) + 1, int(ys[r + 1]))
        for c in range(target_w):
            x0, x1 = int(xs[c]), max(int(xs[c]) + 1, int(xs[c + 1]))
            cell = index_map[y0:y1, x0:x1].ravel()
            total = len(cell)
            if total == 0:
                continue
            valid = cell[cell >= 0]
            cov = len(valid) / total
            prev_idx = int(prev_map[r, c]) if (prev_map is not None and prev_map.shape == (target_h, target_w)) else TRANSPARENT
            min_cov = (coverage - coverage_hold) if prev_idx >= 0 else coverage
            if cov < min_cov or len(valid) == 0:
                continue

            counts = np.bincount(valid, minlength=n_colors)
            winner = int(np.argmax(counts))
            winner_count = int(counts[winner])
            if prev_idx >= 0 and prev_idx < n_colors and counts[prev_idx] >= winner_count * hold_share:
                out[r, c] = prev_idx
            else:
                out[r, c] = winner
    return out


def _clean_isolated_pixels(
    idx_map: np.ndarray,
    palette_rgb: np.ndarray,
    *,
    keep_contrast: float = 90.0,
) -> np.ndarray:
    """Replace 1px color noise with majority 4-neighbor while keeping high-contrast features (eyes/glints)."""
    h, w = idx_map.shape
    out = idx_map.copy()
    wpal = palette_rgb.astype(np.float32) * RGB_WEIGHTS

    for y in range(h):
        for x in range(w):
            cur = int(idx_map[y, x])
            if cur < 0:
                continue
            nbrs: list[int] = []
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and idx_map[ny, nx] >= 0:
                    nbrs.append(int(idx_map[ny, nx]))
            if not nbrs:
                out[y, x] = TRANSPARENT
                continue
            if cur in nbrs:
                continue
            maj = max(set(nbrs), key=nbrs.count)
            dist = float(np.linalg.norm(wpal[cur] - wpal[maj]))
            if dist < keep_contrast:
                out[y, x] = maj
    return out


def hibit_pixelize(
    image: Image.Image,
    target_size: tuple[int, int],
    *,
    n_colors: int = 16,
    palette: Palette | np.ndarray | None = None,
    prev_index_map: np.ndarray | None = None,
    outline: str = "auto",
    coverage: float = 0.45,
    seed: int = 0,
) -> tuple[Image.Image, np.ndarray, np.ndarray, dict[str, Any]]:
    """Run the complete Hi-bit pixelization pipeline on a keyed RGBA source image."""
    rgba = np.asarray(image.convert("RGBA"))
    opaque_mask = rgba[..., 3] >= 128
    if not opaque_mask.any():
        empty = Image.new("RGBA", target_size, (0, 0, 0, 0))
        return empty, np.full((target_size[1], target_size[0]), TRANSPARENT, dtype=np.int32), np.zeros((0, 3), dtype=np.uint8), {
            "colors_learned": 0,
            "outline": "none",
        }

    ys, xs = np.where(opaque_mask)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    crop = rgba[y0:y1, x0:x1]

    if palette is None:
        pal_rgb = kmeans_palette(crop[crop[..., 3] >= 128][:, :3], n_colors, seed=seed)
    elif isinstance(palette, Palette):
        pal_rgb = palette.array
    else:
        pal_rgb = np.asarray(palette, dtype=np.uint8)

    src_h, src_w = crop.shape[:2]
    src_idx = np.full((src_h, src_w), TRANSPARENT, dtype=np.int32)
    solid = crop[..., 3] >= 128
    src_idx[solid] = index_rgb(crop[solid][:, :3], pal_rgb)

    tw, th = target_size
    pad_outline = 1 if outline and outline != "none" else 0
    avail_w = max(1, tw - 2 * pad_outline)
    avail_h = max(1, th - 2 * pad_outline)
    scale = min(avail_w / src_w, avail_h / src_h)
    fit_w = max(1, min(avail_w, int(round(src_w * scale))))
    fit_h = max(1, min(avail_h, int(round(src_h * scale))))

    down = _majority_vote_downsample(
        src_idx,
        fit_w,
        fit_h,
        len(pal_rgb),
        coverage=coverage,
        prev_map=prev_index_map,
    )
    down = _clean_isolated_pixels(down, pal_rgb)

    canvas_idx = np.full((th, tw), TRANSPARENT, dtype=np.int32)
    ox = (tw - fit_w) // 2
    oy = th - fit_h - pad_outline
    canvas_idx[oy : oy + fit_h, ox : ox + fit_w] = down

    out_rgba = np.zeros((th, tw, 4), dtype=np.uint8)
    valid = canvas_idx >= 0
    out_rgba[valid, :3] = pal_rgb[canvas_idx[valid]]
    out_rgba[valid, 3] = 255
    result = Image.fromarray(out_rgba, mode="RGBA")

    outline_hex: str | None = None
    if outline and outline != "none":
        if outline == "auto":
            ocol = auto_outline_color(result)
            result = add_outline(result, color=ocol, mode="outer")
            outline_hex = f"#{ocol[0]:02x}{ocol[1]:02x}{ocol[2]:02x}"
        elif outline == "selective":
            result = add_outline(result, color="selective", mode="outer")
            outline_hex = "selective"
        elif outline == "dark":
            result = add_outline(result, color=(20, 13, 24), mode="outer")
            outline_hex = "#140d18"
        else:
            ocol = parse_hex(outline)
            result = add_outline(result, color=ocol, mode="outer")
            outline_hex = f"#{ocol[0]:02x}{ocol[1]:02x}{ocol[2]:02x}"

    report = {
        "colors_learned": int(len(pal_rgb)),
        "fitted_box": [ox, oy, fit_w, fit_h],
        "outline": outline_hex or "none",
    }
    return result, canvas_idx, pal_rgb, report
