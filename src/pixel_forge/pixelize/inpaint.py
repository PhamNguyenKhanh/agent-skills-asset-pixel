"""RGBA-protected mask inpainting: guarantees 0 bytes modified outside the editable mask."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from pixel_forge.core.image_io import load_normalized_rgba, rgba_sha256, save_deterministic_png
from pixel_forge.providers.base import MediaRequest
from pixel_forge.providers.router import MediaRouter


def validate_binary_mask(mask_image: Image.Image, expected_size: tuple[int, int]) -> np.ndarray:
    """Validate an opaque binary black (0=protect) / white (255=edit) mask and return bool edit array."""
    if mask_image.size != expected_size:
        raise ValueError(
            f"Mask size {mask_image.size[0]}x{mask_image.size[1]} does not match source {expected_size[0]}x{expected_size[1]}."
        )
    rgba = np.asarray(mask_image.convert("RGBA"))
    if int(rgba[..., 3].min()) < 255:
        raise ValueError("Mask contains transparency; use opaque black (0=protect) and white (255=edit).")
    r, g, b = rgba[..., 0], rgba[..., 1], rgba[..., 2]
    if not (np.array_equal(r, g) and np.array_equal(g, b)):
        raise ValueError("Mask is colored; use pure black (#000000) and pure white (#FFFFFF).")
    non_binary = (r > 0) & (r < 255)
    if non_binary.any():
        raise ValueError("Mask contains intermediate gray values; use strictly binary 0 or 255.")
    edit_mask = r == 255
    if not edit_mask.any():
        raise ValueError("Mask is empty (0 editable pixels); aborted before calling any provider.")
    return edit_mask


def composite_protected_inpaint(
    source: Image.Image,
    candidate: Image.Image,
    edit_mask: np.ndarray,
) -> tuple[Image.Image, dict[str, Any]]:
    """Composite candidate strictly inside `edit_mask`, restoring exact original RGBA bytes outside."""
    src_rgba = np.asarray(source.convert("RGBA"))
    cand_resized = candidate.convert("RGBA")
    if cand_resized.size != source.size:
        cand_resized = cand_resized.resize(source.size, Image.Resampling.NEAREST)
    cand_rgba = np.asarray(cand_resized)

    result = src_rgba.copy()
    result[edit_mask] = cand_rgba[edit_mask]

    protected = ~edit_mask
    changed_outside = int(np.any(result[protected] != src_rgba[protected], axis=-1).sum()) if protected.any() else 0
    if changed_outside != 0:
        raise RuntimeError(f"RGBA protection invariant violated: {changed_outside} protected pixels changed!")

    changed_inside = int(np.any(result[edit_mask] != src_rgba[edit_mask], axis=-1).sum())
    out_img = Image.fromarray(result, mode="RGBA")
    return out_img, {
        "editable_pixels": int(edit_mask.sum()),
        "protected_pixels": int(protected.sum()),
        "changed_inside_mask": changed_inside,
        "changed_outside_mask": changed_outside,
        "full_regeneration": bool(not protected.any()),
        "rgba_sha256": rgba_sha256(out_img),
    }


def run_inpaint(
    source_path: Path,
    mask_path: Path,
    instruction: str,
    router: MediaRouter,
    out_dir: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run mask-protected inpainting end-to-end with zero-pixel-leak verification."""
    source_img, _ = load_normalized_rgba(source_path)
    mask_img = Image.open(mask_path)
    edit_mask = validate_binary_mask(mask_img, source_img.size)

    prompt = (
        f"Edit ONLY the masked region of this pixel art sprite: {instruction}. "
        "Keep the exact pixel grid, perspective, lighting, palette harmony, and silhouette outside the masked region unchanged. "
        "Zero anti-aliasing, crisp hard pixel edges."
    )
    req = MediaRequest(
        kind="image",
        prompt=prompt,
        out_dir=out_dir / "_raw_inpaint",
        references=[source_path, mask_path],
        size=f"{max(256, source_img.width * 8)}x{max(256, source_img.height * 8)}",
    )
    media = router.execute(req, dry_run=dry_run)
    if dry_run:
        return {
            "status": "dry_run",
            "route": media.route,
            "model": media.model,
            "estimate_usd": media.estimate_usd,
            "editable_pixels": int(edit_mask.sum()),
            "protected_pixels": int((~edit_mask).sum()),
        }
    if media.status != "ok" or not media.artifact_path:
        raise RuntimeError(f"Inpainting provider unavailable: {media.notes}")

    cand_img, _ = load_normalized_rgba(media.artifact_path)
    out_img, report = composite_protected_inpaint(source_img, cand_img, edit_mask)
    saved = save_deterministic_png(out_img, out_dir / f"{source_path.stem}_inpainted.png")
    return {
        "status": "ok",
        "route": media.route,
        "model": media.model,
        "output": saved,
        "protection_report": report,
    }
