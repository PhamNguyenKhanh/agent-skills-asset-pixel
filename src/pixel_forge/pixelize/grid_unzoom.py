"""Pixel grid detection ('unzoom') and clean cell-center recovery for AI-generated pixel art."""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image


def _estimate_period_1d(signal: np.ndarray, min_step: int = 2, max_step: int = 64) -> tuple[int, int, float]:
    """Estimate dominant periodic step and phase offset of pixel-block edges in a 1D gradient profile."""
    n = len(signal)
    if n < min_step * 3:
        return 1, 0, 0.0
    upper = min(max_step, n // 3)
    if upper < min_step:
        return 1, 0, 0.0

    # Compress giant silhouette alpha jumps so interior color boundaries contribute fairly.
    weighted = np.log1p(np.maximum(0.0, signal))
    total_energy = float(weighted.sum())
    if total_energy <= 1e-6:
        return 1, 0, 0.0

    best_score = 0.0
    best_step = 1
    best_offset = 0

    for step in range(min_step, upper + 1):
        best_phase_sum = -1.0
        best_phase = 0
        for phase in range(step):
            samples = weighted[phase::step]
            if len(samples) < 3:
                continue
            val = float(samples.sum())
            if val > best_phase_sum:
                best_phase_sum = val
                best_phase = phase
        if best_phase_sum <= 0.0:
            continue
        captured = best_phase_sum / total_energy
        # Fundamental period maximizes captured^3 * step:
        # - sub-multiples (P/2) have captured=1.0 but half the step score
        # - super-multiples (2P, 4P) miss interior transitions so captured^3 drops steeply
        score = (captured ** 3.0) * step
        if score > best_score + 0.05:
            best_score = score
            best_step = step
            best_offset = best_phase

    if best_score < 1.35:
        return 1, 0, round(best_score, 3)
    return best_step, best_offset, round(best_score, 3)


def detect_pixel_grid(image: Image.Image, *, max_cell: int = 64) -> dict[str, Any]:
    """Detect apparent AI pixel block cell size (cell_w, cell_h) and phase offsets."""
    rgba = np.asarray(image.convert("RGBA"))
    h, w = rgba.shape[:2]
    if w < 16 or h < 16:
        return {"cell_w": 1, "cell_h": 1, "offset_x": 0, "offset_y": 0, "confidence_x": 0.0, "confidence_y": 0.0}

    # Include alpha discontinuities strongly because AI pixel silhouettes reveal grid boundaries cleanly.
    feats = rgba.astype(np.float32)
    feats[..., 3] *= 1.5

    dx = np.abs(np.diff(feats, axis=1)).sum(axis=-1).mean(axis=0)  # length w - 1
    dy = np.abs(np.diff(feats, axis=0)).sum(axis=-1).mean(axis=1)  # length h - 1

    cell_w, ox, conf_x = _estimate_period_1d(dx, min_step=2, max_step=min(max_cell, w // 4))
    cell_h, oy, conf_y = _estimate_period_1d(dy, min_step=2, max_step=min(max_cell, h // 4))

    # If both axes detected very similar square cell sizes, unify them.
    if cell_w > 1 and cell_h > 1 and abs(cell_w - cell_h) <= 1:
        unified = min(cell_w, cell_h)
        cell_w = cell_h = unified
    elif cell_w > 1 and cell_h == 1 and conf_x >= 1.8:
        cell_h = cell_w
    elif cell_h > 1 and cell_w == 1 and conf_y >= 1.8:
        cell_w = cell_h

    return {
        "cell_w": int(cell_w),
        "cell_h": int(cell_h),
        "offset_x": int((ox + 1) % max(1, cell_w)),
        "offset_y": int((oy + 1) % max(1, cell_h)),
        "confidence_x": conf_x,
        "confidence_y": conf_y,
    }


def unzoom_to_grid(
    image: Image.Image,
    *,
    cell_w: int | None = None,
    cell_h: int | None = None,
    offset_x: int | None = None,
    offset_y: int | None = None,
    coverage_threshold: float = 0.45,
) -> tuple[Image.Image, dict[str, Any]]:
    """Recover true 1x pixel art by sampling the clean inner core median color of each grid cell."""
    detected = detect_pixel_grid(image)
    cw = int(cell_w or detected["cell_w"])
    ch = int(cell_h or detected["cell_h"])
    ox = int(detected["offset_x"] if offset_x is None else offset_x)
    oy = int(detected["offset_y"] if offset_y is None else offset_y)

    rgba = np.asarray(image.convert("RGBA"))
    h, w = rgba.shape[:2]

    if cw <= 1 and ch <= 1:
        return image.convert("RGBA"), {**detected, "applied": False, "recovered_size": [w, h]}

    cols = max(1, (w - ox) // cw)
    rows = max(1, (h - oy) // ch)
    out = np.zeros((rows, cols, 4), dtype=np.uint8)

    # Trim 20% border inside each cell to avoid blurry anti-aliased transitions between AI blocks.
    mx = max(0, cw // 5)
    my = max(0, ch // 5)

    for r in range(rows):
        y0 = oy + r * ch + my
        y1 = max(y0 + 1, oy + (r + 1) * ch - my)
        for c in range(cols):
            x0 = ox + c * cw + mx
            x1 = max(x0 + 1, ox + (c + 1) * cw - mx)
            patch = rgba[y0:y1, x0:x1]
            opaque = patch[..., 3] >= 128
            if float(opaque.mean()) < coverage_threshold:
                continue
            vis = patch[opaque][:, :3]
            med = np.median(vis, axis=0)
            out[r, c, 0] = int(round(med[0]))
            out[r, c, 1] = int(round(med[1]))
            out[r, c, 2] = int(round(med[2]))
            out[r, c, 3] = 255

    recovered = Image.fromarray(out, mode="RGBA")
    return recovered, {
        **detected,
        "applied": True,
        "used_cell": [cw, ch],
        "used_offset": [ox, oy],
        "recovered_size": [cols, rows],
    }
