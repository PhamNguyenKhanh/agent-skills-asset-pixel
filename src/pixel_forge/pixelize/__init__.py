"""Image-to-pixel processing: soft-matte keying, grid unzoom, hi-bit finish, inpainting, and 3-track pipeline."""

from pixel_forge.pixelize.grid_unzoom import detect_pixel_grid, unzoom_to_grid
from pixel_forge.pixelize.hibit import hibit_pixelize
from pixel_forge.pixelize.inpaint import composite_protected_inpaint, run_inpaint
from pixel_forge.pixelize.matte import quiet_key_color, remove_background
from pixel_forge.pixelize.operations import (
    add_ground_shadow,
    add_outline,
    bayer_dither,
    fit_canvas,
    mirror_sprite,
    nearest_resize,
    value_noise_tile,
)
from pixel_forge.pixelize.pipeline import AssetResult, create_asset

__all__ = [
    "AssetResult",
    "add_ground_shadow",
    "add_outline",
    "bayer_dither",
    "composite_protected_inpaint",
    "create_asset",
    "detect_pixel_grid",
    "fit_canvas",
    "hibit_pixelize",
    "mirror_sprite",
    "nearest_resize",
    "quiet_key_color",
    "remove_background",
    "run_inpaint",
    "unzoom_to_grid",
    "value_noise_tile",
]
