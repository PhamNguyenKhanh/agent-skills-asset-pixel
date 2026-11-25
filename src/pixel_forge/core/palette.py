"""Palette management, luminance-weighted k-means++, OKLab color math, and palette remapping."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image

RGB_WEIGHTS = np.sqrt(np.array([0.30, 0.59, 0.11], dtype=np.float32))
LUMA = np.array([0.30, 0.59, 0.11], dtype=np.float32)


def project_root() -> Path:
    """Locate repository root containing `palettes/` and `templates/`."""
    here = Path(__file__).resolve()
    for parent in (here.parents[3], here.parents[2], Path.cwd()):
        if (parent / "palettes").is_dir():
            return parent
    return Path.cwd()


def palettes_dir() -> Path:
    return project_root() / "palettes"


@dataclass(frozen=True)
class Palette:
    name: str
    colors: tuple[tuple[int, int, int], ...]
    max_colors: int
    description: str = ""

    @property
    def hex_colors(self) -> list[str]:
        return [rgb_to_hex(c) for c in self.colors]

    @property
    def array(self) -> np.ndarray:
        return np.array(self.colors, dtype=np.uint8)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "max_colors": self.max_colors,
            "colors": self.hex_colors,
        }


def parse_hex(value: str) -> tuple[int, int, int]:
    """Parse '#RRGGBB' or '#RGB' into an (R, G, B) uint8 tuple."""
    text = str(value).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
        raise ValueError(f"Invalid hex color: {value!r}")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def rgb_to_hex(rgb: Sequence[int]) -> str:
    return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"


def list_palettes() -> list[str]:
    """Return sorted names of all curated palettes available in `palettes/`."""
    pdir = palettes_dir()
    if not pdir.is_dir():
        return []
    return sorted(p.stem for p in pdir.glob("*.json"))


def load_palette(name_or_path: str | Path) -> Palette:
    """Load a palette by built-in name (e.g. 'pico-8', 'master_topdown') or JSON file path."""
    candidate = Path(name_or_path)
    if not candidate.is_file():
        candidate = palettes_dir() / f"{str(name_or_path).strip().lower()}.json"
    if not candidate.is_file():
        available = ", ".join(list_palettes())
        raise FileNotFoundError(f"Palette {name_or_path!r} not found. Available: {available}")
    data = json.loads(candidate.read_text(encoding="utf-8"))
    raw_colors = data.get("colors")
    if not isinstance(raw_colors, list) or not raw_colors:
        raise ValueError(f"Palette file {candidate} must contain a non-empty 'colors' array.")
    colors = tuple(parse_hex(c) for c in raw_colors)
    return Palette(
        name=str(data.get("name") or candidate.stem),
        colors=colors,
        max_colors=int(data.get("max_colors") or len(colors)),
        description=str(data.get("description") or ""),
    )


def save_palette(palette: Palette, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(palette.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- OKLab conversions


def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055) * 255.0


def srgb_to_oklab(rgb: Any) -> np.ndarray:
    """Convert sRGB uint8 (..., 3) to OKLab float64 (..., 3)."""
    lin = _srgb_to_linear(np.asarray(rgb, dtype=np.float64))
    lms = lin @ np.array(
        [
            [0.4122214708, 0.2119034982, 0.0883024619],
            [0.5363325363, 0.6806995451, 0.2817188376],
            [0.0514459929, 0.1073969566, 0.6299787005],
        ]
    )
    lms = np.cbrt(lms)
    return lms @ np.array(
        [
            [0.2104542553, 1.9779984951, 0.0259040371],
            [0.7936177850, -2.4285922050, 0.7827717662],
            [-0.0040720468, 0.4505937099, -0.8086757660],
        ]
    )


def oklab_to_srgb(lab: Any) -> np.ndarray:
    """Convert OKLab float64 (..., 3) to sRGB uint8 (..., 3)."""
    lab_arr = np.asarray(lab, dtype=np.float64)
    lms = lab_arr @ np.array(
        [
            [1.0, 1.0, 1.0],
            [0.3963377774, -0.1055613458, -0.0894841775],
            [0.2158037573, -0.0638541728, -1.2914855480],
        ]
    )
    lms = lms**3
    lin = lms @ np.array(
        [
            [4.0767416621, -1.2684380046, -0.0041960863],
            [-3.3077115913, 2.6097574011, -0.7034186147],
            [0.2309699292, -0.3413193965, 1.7076147010],
        ]
    )
    return np.clip(np.round(_linear_to_srgb(lin)), 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------- K-means++ & indexing


def _assign_nearest(points: np.ndarray, centres: np.ndarray, chunk: int = 131072) -> np.ndarray:
    out = np.empty(len(points), dtype=np.int32)
    for start in range(0, len(points), chunk):
        block = points[start : start + chunk]
        dists = ((block[:, None, :] - centres[None, :, :]) ** 2).sum(axis=-1)
        out[start : start + chunk] = np.argmin(dists, axis=1)
    return out


def kmeans_palette(
    pixels: Any,
    k: int,
    *,
    seed: int = 0,
    sample: int = 60000,
    iters: int = 12,
) -> np.ndarray:
    """Deterministic luminance-weighted RGB k-means++ palette (dark -> light), shape (n, 3) uint8."""
    points = np.asarray(pixels, dtype=np.float32).reshape(-1, 3)
    if len(points) == 0:
        raise ValueError("Cannot build palette from empty pixel array.")
    if not 1 <= int(k) <= 254:
        raise ValueError("Palette size k must be within 1..254.")
    rng = np.random.default_rng(int(seed))
    weighted = points * RGB_WEIGHTS
    if len(weighted) > sample:
        weighted = weighted[rng.choice(len(weighted), size=sample, replace=False)]
    distinct = np.unique(np.round(weighted, 2), axis=0)
    k = int(min(k, len(distinct)))
    if k <= 1:
        mean_rgb = np.clip(np.round(points.mean(axis=0)), 0, 255).astype(np.uint8)
        return mean_rgb.reshape(1, 3)

    centres = [weighted[int(rng.integers(len(weighted)))]]
    nearest = ((weighted - centres[0]) ** 2).sum(axis=1)
    for _ in range(k - 1):
        total = float(nearest.sum())
        if total > 0:
            pick = int(rng.choice(len(weighted), p=nearest / total))
        else:
            pick = int(rng.integers(len(weighted)))
        centres.append(weighted[pick])
        nearest = np.minimum(nearest, ((weighted - weighted[pick]) ** 2).sum(axis=1))
    centres_arr = np.array(centres, dtype=np.float32)

    for _ in range(int(iters)):
        labels = _assign_nearest(weighted, centres_arr)
        for j in range(k):
            members = weighted[labels == j]
            if len(members):
                centres_arr[j] = members.mean(axis=0)

    palette = np.clip(np.round(centres_arr / RGB_WEIGHTS), 0, 255).astype(np.uint8)
    palette = np.unique(palette, axis=0)
    order = np.argsort(palette.astype(np.float32) @ LUMA, kind="stable")
    return palette[order]


def extract_palette(image: Image.Image, max_colors: int = 16, *, name: str = "extracted", seed: int = 0) -> Palette:
    """Extract up to `max_colors` representative colors from visible pixels of an RGBA image."""
    rgba = np.asarray(image.convert("RGBA"))
    visible = rgba[rgba[..., 3] > 0][..., :3]
    if len(visible) == 0:
        raise ValueError("Image has no visible pixels to extract a palette from.")
    unique = np.unique(visible.reshape(-1, 3), axis=0)
    if len(unique) <= max_colors:
        order = np.argsort(unique.astype(np.float32) @ LUMA, kind="stable")
        chosen = unique[order]
    else:
        chosen = kmeans_palette(visible, max_colors, seed=seed)
    colors = tuple((int(r), int(g), int(b)) for r, g, b in chosen)
    return Palette(name=name, colors=colors, max_colors=max_colors, description=f"Extracted {len(colors)} colors")


def index_rgb(rgb: Any, palette_rgb: np.ndarray) -> np.ndarray:
    """Return nearest palette index for every pixel in `rgb` (..., 3)."""
    arr = np.asarray(rgb)
    flat = arr.reshape(-1, 3).astype(np.float32) * RGB_WEIGHTS
    centres = np.asarray(palette_rgb, dtype=np.float32).reshape(-1, 3) * RGB_WEIGHTS
    return _assign_nearest(flat, centres).reshape(arr.shape[:-1])


def remap_image_to_palette(
    image: Image.Image,
    palette: Palette | np.ndarray,
    *,
    policy: str = "strict",
) -> tuple[Image.Image, dict[str, Any]]:
    """Remap visible RGB pixels to a target palette without changing alpha.

    - `strict`: remaps every visible pixel to nearest color in `palette`.
    - `guided`: leaves image pixels untouched and reports how many visible pixels fall outside `palette`.
    """
    rgba = np.asarray(image.convert("RGBA")).copy()
    pal_arr = palette.array if isinstance(palette, Palette) else np.asarray(palette, dtype=np.uint8)
    visible_mask = rgba[..., 3] > 0
    total_visible = int(visible_mask.sum())
    if total_visible == 0:
        return Image.fromarray(rgba, mode="RGBA"), {
            "policy": policy,
            "total_visible_pixels": 0,
            "out_of_palette_pixels": 0,
            "remapped_pixels": 0,
        }

    pal_set = {(int(r), int(g), int(b)) for r, g, b in pal_arr}
    vis_rgb = rgba[visible_mask][:, :3]
    out_of_pal = sum(1 for r, g, b in vis_rgb.tolist() if (r, g, b) not in pal_set)

    if policy == "guided":
        return Image.fromarray(rgba, mode="RGBA"), {
            "policy": "guided",
            "total_visible_pixels": total_visible,
            "out_of_palette_pixels": out_of_pal,
            "remapped_pixels": 0,
        }

    if policy != "strict":
        raise ValueError(f"Unknown palette policy: {policy!r}. Expected 'strict' or 'guided'.")

    indices = index_rgb(vis_rgb, pal_arr)
    rgba[visible_mask, :3] = pal_arr[indices]
    return Image.fromarray(rgba, mode="RGBA"), {
        "policy": "strict",
        "total_visible_pixels": total_visible,
        "out_of_palette_pixels": out_of_pal,
        "remapped_pixels": out_of_pal,
    }


def auto_outline_color(image: Image.Image) -> tuple[int, int, int]:
    """Compute a deep hue-shifted outline color derived from the sprite's dominant saturated hue."""
    rgba = np.asarray(image.convert("RGBA"))
    visible = rgba[rgba[..., 3] >= 128][:, :3]
    if len(visible) == 0:
        return (20, 13, 24)  # Master Contour Deepest #140d18
    lab = srgb_to_oklab(visible)
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    saturated = lab[chroma >= 0.04]
    if len(saturated) == 0:
        return (20, 13, 24)
    # Weight hue direction by chroma so dominant material tint drives the outline.
    weights = np.hypot(saturated[:, 1], saturated[:, 2])
    mean_a = float(np.average(saturated[:, 1], weights=weights))
    mean_b = float(np.average(saturated[:, 2], weights=weights))
    hue_norm = max(1e-6, float(np.hypot(mean_a, mean_b)))
    # Deep shadow L=0.18 with subtle chromatic tint (never pure dead black).
    target_lab = np.array([[0.18, 0.055 * (mean_a / hue_norm), 0.055 * (mean_b / hue_norm)]])
    rgb = oklab_to_srgb(target_lab)[0]
    return int(rgb[0]), int(rgb[1]), int(rgb[2])


def color_lock_oklab(
    frame: Image.Image,
    master_palette_rgb: np.ndarray,
    *,
    strength: float = 0.85,
) -> Image.Image:
    """Lock frame chroma toward nearest colors in the master palette in OKLab space while preserving lightness.

    Adapted from agent-sprite-forge's HD/pixel colour lock to eliminate video limb shimmer.
    """
    rgba = np.asarray(frame.convert("RGBA")).copy()
    mask = rgba[..., 3] > 0
    if not mask.any() or len(master_palette_rgb) == 0:
        return Image.fromarray(rgba, mode="RGBA")
    vis = rgba[mask][:, :3]
    vis_lab = srgb_to_oklab(vis)
    pal_lab = srgb_to_oklab(master_palette_rgb)
    # Find nearest master color in full OKLab distance.
    dists = ((vis_lab[:, None, :] - pal_lab[None, :, :]) ** 2).sum(axis=-1)
    nearest_idx = np.argmin(dists, axis=1)
    target_lab = pal_lab[nearest_idx]
    blended = vis_lab.copy()
    blended[:, 1] = vis_lab[:, 1] * (1.0 - strength) + target_lab[:, 1] * strength
    blended[:, 2] = vis_lab[:, 2] * (1.0 - strength) + target_lab[:, 2] * strength
    rgba[mask, :3] = oklab_to_srgb(blended)
    return Image.fromarray(rgba, mode="RGBA")
