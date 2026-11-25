"""Deterministic raster image I/O: EXIF transpose, sRGB ICC normalization, and content hashing."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

EXIF_ORIENTATION_TAG = 0x0112
DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_MAX_PIXELS = 8192 * 8192


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rgba_sha256(image: Image.Image) -> str:
    """Compute a deterministic hash over the exact RGBA dimensions and pixel bytes."""
    rgba = image.convert("RGBA")
    h = hashlib.sha256()
    h.update(f"{rgba.width}x{rgba.height}:".encode("ascii"))
    h.update(rgba.tobytes())
    return h.hexdigest()


def _to_rgba(image: Image.Image) -> Image.Image:
    mode = image.mode
    if mode in ("I;16", "I;16B", "I;16L", "I"):
        return image.convert("I").point(lambda v: v * (1.0 / 256.0)).convert("L").convert("RGBA")
    if mode == "F":
        return image.convert("L").convert("RGBA")
    return image.convert("RGBA")


def _to_srgb(image: Image.Image, icc_bytes: bytes | None) -> tuple[Image.Image, bool]:
    if not icc_bytes:
        return _to_rgba(image), False
    try:
        src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_bytes))
    except (OSError, ImageCms.PyCMSError):
        return _to_rgba(image), False
    srgb = ImageCms.createProfile("sRGB")
    if image.mode == "CMYK":
        rgb = ImageCms.profileToProfile(image, src_profile, srgb, outputMode="RGB")
        return rgb.convert("RGBA"), True
    rgba = _to_rgba(image)
    alpha = rgba.getchannel("A")
    rgb = ImageCms.profileToProfile(rgba.convert("RGB"), src_profile, srgb, outputMode="RGB")
    rgb.putalpha(alpha)
    return rgb, True


def load_normalized_rgba(
    path: Path | str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> tuple[Image.Image, dict[str, Any]]:
    """Safely load any image file, apply EXIF orientation, convert ICC to sRGB RGBA 8-bit."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Image file not found: {file_path}")
    size_bytes = file_path.stat().st_size
    if size_bytes > max_bytes:
        raise ValueError(f"Image {file_path.name} ({size_bytes} bytes) exceeds limit {max_bytes}.")

    prev_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(file_path) as img:
            fmt = img.format
            orig_size = img.size
            orig_mode = img.mode
            if orig_size[0] * orig_size[1] > max_pixels:
                raise ValueError(f"Image {orig_size[0]}x{orig_size[1]} exceeds max pixel limit {max_pixels}.")
            img.load()
            orientation = int(img.getexif().get(EXIF_ORIENTATION_TAG, 1))
            icc = img.info.get("icc_profile")
            oriented = ImageOps.exif_transpose(img) or img
            rgba, icc_converted = _to_srgb(oriented, icc)
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unrecognized image format: {file_path}") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = prev_limit

    alpha_hist = rgba.getchannel("A").histogram()
    report = {
        "source": str(file_path),
        "format": fmt,
        "original_mode": orig_mode,
        "original_size": list(orig_size),
        "size": [rgba.width, rgba.height],
        "exif_orientation": orientation,
        "icc_converted": icc_converted,
        "has_alpha": sum(alpha_hist[:255]) > 0,
        "has_partial_alpha": sum(alpha_hist[1:255]) > 0,
        "bytes": size_bytes,
        "rgba_sha256": rgba_sha256(rgba),
    }
    return rgba, report


def save_deterministic_png(image: Image.Image, path: Path | str) -> dict[str, Any]:
    """Save PNG with fixed compression settings so identical pixels produce identical bytes."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG", compress_level=6, optimize=False)
    info: dict[str, Any] = {
        "path": str(target),
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "sha256": sha256_file(target),
    }
    if image.mode == "RGBA":
        info["rgba_sha256"] = rgba_sha256(image)
    return info
