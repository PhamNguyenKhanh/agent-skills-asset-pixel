"""Border-hue flood keying and vectorized soft-matte chroma removal with edge despill."""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np
from PIL import Image

from pixel_forge.core.palette import parse_hex

DECLARED_KEYS: dict[str, tuple[int, int, int]] = {
    "magenta": (255, 0, 255),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
}


def resolve_key_rgb(key_color: str | tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(key_color, tuple):
        return (int(key_color[0]), int(key_color[1]), int(key_color[2]))
    text = key_color.strip().lower()
    if text in DECLARED_KEYS:
        return DECLARED_KEYS[text]
    return parse_hex(text)


def key_dominance(rgb: np.ndarray, key_rgb: tuple[int, int, int]) -> np.ndarray:
    """Measure how strongly RGB pixels lean toward a primary/secondary chroma-key color."""
    arr = rgb.astype(np.float32)
    kr, kg, kb = key_rgb
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    if kr >= 200 and kb >= 200 and kg <= 60:  # magenta
        return np.minimum(r, b) - g
    if kg >= 200 and kr <= 60 and kb <= 60:  # green
        return g - np.maximum(r, b)
    if kb >= 200 and kr <= 60 and kg <= 60:  # blue
        return b - np.maximum(r, g)
    # Generic fallback: negative Euclidean distance inverted to dominance scale.
    dist = np.sqrt(((arr - np.array(key_rgb, dtype=np.float32)) ** 2).sum(axis=-1))
    return 255.0 - dist


def quiet_key_color(image: Image.Image) -> tuple[str, tuple[int, int, int]]:
    """Choose the chroma-key color (magenta, green, or blue) that conflicts least with the sprite."""
    rgba = np.asarray(image.convert("RGBA"))
    opaque = rgba[..., 3] > 0
    if not opaque.any():
        return "magenta", DECLARED_KEYS["magenta"]
    pixels = rgba[opaque][:, :3]
    # Border ring of the sprite (1px inward)
    padded = np.pad(opaque, 1, mode="constant", constant_values=False)
    eroded = padded[1:-1, 1:-1] & padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
    ring = opaque & (~eroded)
    edge_px = rgba[ring][:, :3] if ring.any() else pixels

    best_name = "magenta"
    best_score = float("inf")
    for name, rgb in DECLARED_KEYS.items():
        own_share = float((key_dominance(pixels, rgb) >= 40.0).mean())
        edge_share = float((key_dominance(edge_px, rgb) >= 24.0).mean())
        score = own_share * 10.0 + edge_share
        if score < best_score:
            best_score = score
            best_name = name
    return best_name, DECLARED_KEYS[best_name]


def detect_border_key(image: Image.Image) -> tuple[tuple[int, int, int], float]:
    """Measure the median opaque RGB color along the outer border of an image and its uniformity ratio."""
    rgba = np.asarray(image.convert("RGBA"))
    h, w = rgba.shape[:2]
    top = rgba[0, :, :]
    bottom = rgba[h - 1, :, :]
    left = rgba[:, 0, :]
    right = rgba[:, w - 1, :]
    border = np.concatenate([top, bottom, left, right], axis=0)
    opaque = border[border[:, 3] >= 200]
    if len(opaque) == 0:
        return (255, 0, 255), 0.0
    rgb = opaque[:, :3].astype(np.float32)
    med = np.median(rgb, axis=0)
    dists = np.sqrt(((rgb - med) ** 2).sum(axis=-1))
    uniformity = float((dists <= 36.0).mean())
    return (int(round(med[0])), int(round(med[1])), int(round(med[2]))), uniformity


def _remove_small_specks(opaque: np.ndarray, min_size: int = 2) -> np.ndarray:
    """Remove tiny disconnected alpha specks (1px isolated islands) using pure numpy 4-neighbor check."""
    if min_size <= 1 or not opaque.any():
        return opaque
    p = np.pad(opaque, 1, mode="constant", constant_values=False)
    neighbors = (
        p[:-2, 1:-1].astype(np.uint8)
        + p[2:, 1:-1].astype(np.uint8)
        + p[1:-1, :-2].astype(np.uint8)
        + p[1:-1, 2:].astype(np.uint8)
    )
    return opaque & (neighbors > 0)


def _despill_edges(rgba: np.ndarray, key_rgb: tuple[int, int, int], band_px: int = 2) -> np.ndarray:
    """Suppress chroma-key color bleed on outer-edge foreground pixels while preserving luma."""
    out = rgba.copy()
    opaque = out[..., 3] > 0
    if not opaque.any():
        return out

    # Find outer band within `band_px` of transparent pixels.
    bg = ~opaque
    near_bg = bg.copy()
    for _ in range(max(1, band_px)):
        p = np.pad(near_bg, 1, mode="constant", constant_values=True)
        near_bg = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    edge = opaque & near_bg
    if not edge.any():
        return out

    kr, kg, kb = key_rgb
    px = out[edge][:, :3].astype(np.float32)
    if kr >= 200 and kb >= 200 and kg <= 60:  # magenta spill: clamp excess of R,B above G
        dom = np.minimum(px[:, 0], px[:, 2]) - px[:, 1]
        spill = dom > 18.0
        if spill.any():
            excess = (dom[spill] - 10.0) * 0.65
            px[spill, 0] = np.clip(px[spill, 0] - excess, 0, 255)
            px[spill, 2] = np.clip(px[spill, 2] - excess, 0, 255)
            px[spill, 1] = np.clip(px[spill, 1] + excess * 0.25, 0, 255)
    elif kg >= 200 and kr <= 60 and kb <= 60:  # green spill
        dom = px[:, 1] - np.maximum(px[:, 0], px[:, 2])
        spill = dom > 18.0
        if spill.any():
            excess = (dom[spill] - 10.0) * 0.65
            px[spill, 1] = np.clip(px[spill, 1] - excess, 0, 255)
    elif kb >= 200 and kr <= 60 and kg <= 60:  # blue spill
        dom = px[:, 2] - np.maximum(px[:, 0], px[:, 1])
        spill = dom > 18.0
        if spill.any():
            excess = (dom[spill] - 10.0) * 0.65
            px[spill, 2] = np.clip(px[spill, 2] - excess, 0, 255)

    out[edge, :3] = np.clip(np.round(px), 0, 255).astype(np.uint8)
    return out


def remove_background_flood(
    image: Image.Image,
    key_rgb: tuple[int, int, int],
    *,
    tolerance: float = 52.0,
    despill: bool = True,
    binarize_alpha: bool = True,
    remove_enclosed_key_holes: bool = True,
) -> tuple[Image.Image, dict[str, Any]]:
    """Remove solid/chroma-key background via border-seeded BFS + soft-matte edge cleanup & despill."""
    rgba = np.asarray(image.convert("RGBA")).copy()
    h, w = rgba.shape[:2]
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3]
    key_vec = np.array(key_rgb, dtype=np.float32)

    # Distance to key + dominance check for known chroma keys (magenta/green/blue)
    dist = np.sqrt(((rgb - key_vec) ** 2).sum(axis=-1))
    is_chroma = key_rgb in DECLARED_KEYS.values()
    if is_chroma:
        dom = key_dominance(rgb, key_rgb)
        bg_candidate = (alpha < 16) | (dist <= tolerance) | ((dom >= 70.0) & (dist <= tolerance * 2.1))
    else:
        bg_candidate = (alpha < 16) | (dist <= tolerance)

    visited = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg_candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    for y in range(1, h - 1):
        for x in (0, w - 1):
            if bg_candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))

    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and bg_candidate[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    if remove_enclosed_key_holes and is_chroma:
        # Strong pure chroma pockets enclosed between legs/arms should also become transparent.
        strong_hole = (dist <= tolerance * 0.65) & (key_dominance(rgb, key_rgb) >= 110.0)
        visited |= strong_hole

    # Soft fringe cleanup: pixels directly adjacent to visited background with high key bleed
    if is_chroma:
        p = np.pad(visited, 1, mode="constant", constant_values=True)
        adj_bg = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        fringe = (~visited) & adj_bg & (key_dominance(rgb, key_rgb) >= 48.0) & (dist <= tolerance * 2.5)
        visited |= fringe

    out = rgba.copy()
    out[visited] = (0, 0, 0, 0)

    if binarize_alpha:
        opaque = out[..., 3] >= 128
        opaque = _remove_small_specks(opaque, min_size=2)
        out[~opaque] = (0, 0, 0, 0)
        out[opaque, 3] = 255

    if despill and is_chroma:
        out = _despill_edges(out, key_rgb, band_px=2)

    removed_count = int(visited.sum())
    report = {
        "key_rgb": list(key_rgb),
        "tolerance": tolerance,
        "removed_pixels": removed_count,
        "foreground_pixels": int((out[..., 3] > 0).sum()),
        "despilled": bool(despill and is_chroma),
    }
    return Image.fromarray(out, mode="RGBA"), report


def remove_background(
    image: Image.Image,
    *,
    key_color: str | tuple[int, int, int] = "auto",
    tolerance: float = 52.0,
    despill: bool = True,
    binarize_alpha: bool = True,
) -> tuple[Image.Image, dict[str, Any]]:
    """Smart background removal: preserves existing clean transparency or keys out solid/chroma backdrops."""
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba)
    border_alpha = np.concatenate([arr[0, :, 3], arr[-1, :, 3], arr[:, 0, 3], arr[:, -1, 3]])
    already_transparent_ratio = float((border_alpha == 0).mean())

    # If the image already has clean transparency around the border (e.g. a real sprite PNG), keep its alpha!
    if key_color == "auto" and already_transparent_ratio >= 0.70:
        out = arr.copy()
        if binarize_alpha:
            opaque = out[..., 3] >= 128
            out[~opaque] = (0, 0, 0, 0)
            out[opaque, 3] = 255
        return Image.fromarray(out, mode="RGBA"), {
            "key_rgb": None,
            "already_transparent": True,
            "removed_pixels": 0,
            "foreground_pixels": int((out[..., 3] > 0).sum()),
            "despilled": False,
        }

    if key_color == "auto":
        measured_rgb, uniformity = detect_border_key(rgba)
        # Snap measured border color to nearest declared key if close (e.g. slightly compressed magenta/green)
        snapped = measured_rgb
        for _, dec_rgb in DECLARED_KEYS.items():
            d = float(np.linalg.norm(np.array(measured_rgb, dtype=np.float32) - np.array(dec_rgb, dtype=np.float32)))
            if d <= 65.0:
                snapped = dec_rgb
                break
        result, rep = remove_background_flood(
            rgba, snapped, tolerance=tolerance, despill=despill, binarize_alpha=binarize_alpha
        )
        rep["measured_border_rgb"] = list(measured_rgb)
        rep["border_uniformity"] = round(uniformity, 4)
        return result, rep

    key_rgb = resolve_key_rgb(key_color)
    return remove_background_flood(rgba, key_rgb, tolerance=tolerance, despill=despill, binarize_alpha=binarize_alpha)
