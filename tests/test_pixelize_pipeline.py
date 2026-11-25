"""Tests for soft-matte, grid unzoom, hibit, RGBA-protected inpainting, and 3-track asset pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from pixel_forge.core.palette import load_palette
from pixel_forge.core.spec import AssetSpec
from pixel_forge.pixelize.grid_unzoom import detect_pixel_grid, unzoom_to_grid
from pixel_forge.pixelize.hibit import hibit_pixelize
from pixel_forge.pixelize.inpaint import composite_protected_inpaint, validate_binary_mask
from pixel_forge.pixelize.matte import remove_background
from pixel_forge.pixelize.operations import bayer_dither, value_noise_tile
from pixel_forge.pixelize.pipeline import create_asset
from pixel_forge.providers.router import MediaRouter
from pixel_forge.qa.gates import audit_tile_seams


def _make_fake_ai_rough_sprite(cell: int = 8) -> Image.Image:
    """Create a 16x16 logical sprite rendered at `cell`x scale on a slightly noisy magenta chroma-key."""
    logical = 16
    w = logical * cell
    img = Image.new("RGBA", (w, w), (252, 4, 250, 255))
    draw = ImageDraw.Draw(img)
    for gy in range(3, 14):
        for gx in range(4, 12):
            is_edge = gy in (3, 13) or gx in (4, 11)
            col = (20, 13, 24, 255) if is_edge else ((186, 107, 50, 255) if gy < 7 else (133, 68, 30, 255))
            draw.rectangle([gx * cell, gy * cell, (gx + 1) * cell - 1, (gy + 1) * cell - 1], fill=col)
    # Golden emblem inside
    draw.rectangle([7 * cell, 7 * cell, 9 * cell - 1, 9 * cell - 1], fill=(232, 168, 37, 255))
    return img


class TestPixelizePipeline(unittest.TestCase):
    def test_matte_and_grid_unzoom_recovery(self) -> None:
        raw = _make_fake_ai_rough_sprite(cell=8)  # 128x128 with 8x8 fake pixels
        keyed, matte_rep = remove_background(raw, key_color="auto", binarize_alpha=True)
        self.assertGreater(matte_rep["removed_pixels"], 0)
        # Corners must be 100% transparent
        self.assertEqual(keyed.getpixel((0, 0))[3], 0)

        grid = detect_pixel_grid(keyed)
        self.assertEqual(grid["cell_w"], 8)
        self.assertEqual(grid["cell_h"], 8)
        unzoomed, urep = unzoom_to_grid(keyed)
        self.assertTrue(urep["applied"])
        self.assertEqual(unzoomed.size, (16, 16))

    def test_direct_and_hibit_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rough_path = root / "rough.png"
            _make_fake_ai_rough_sprite(cell=8).save(rough_path)

            router = MediaRouter(offline=True, project_root=root)
            spec = AssetSpec(
                asset_id="test_chest",
                brief="wooden chest",
                width=32,
                height=32,
                preset="topdown-34-stardew",
                mode="direct",
                add_ground_shadow=True,
            )
            res = create_asset(spec, router, root / "out_direct", rough_image=rough_path)
            self.assertEqual(res.status, "ok")
            self.assertIsNotNone(res.image)
            assert res.image is not None
            self.assertEqual(res.image.size, (32, 32))

            # Hibit majority-vote finish
            keyed, _ = remove_background(Image.open(rough_path), key_color="auto")
            hb_img, hb_idx, hb_pal, hb_rep = hibit_pixelize(keyed, (32, 32), n_colors=8, outline="auto")
            self.assertEqual(hb_img.size, (32, 32))
            self.assertGreater(hb_rep["colors_learned"], 0)
            self.assertEqual(hb_idx.shape, (32, 32))
            self.assertLessEqual(len(hb_pal), 8)

    def test_rgba_protected_inpaint_zero_outside_changes(self) -> None:
        # Include hidden non-zero RGB under alpha=0 to verify strict 4-byte protection!
        src_arr = np.zeros((16, 16, 4), dtype=np.uint8)
        src_arr[0, 0] = (123, 45, 67, 0)  # hidden RGB under transparent pixel
        src_arr[4:12, 4:12] = (133, 68, 30, 255)
        src = Image.fromarray(src_arr, mode="RGBA")

        mask = Image.new("RGB", (16, 16), (0, 0, 0))
        ImageDraw.Draw(mask).rectangle([6, 6, 9, 9], fill=(255, 255, 255))
        edit_mask = validate_binary_mask(mask, (16, 16))

        # Candidate changes EVERY pixel to blue
        cand = Image.new("RGBA", (16, 16), (30, 90, 220, 255))
        out, rep = composite_protected_inpaint(src, cand, edit_mask)
        self.assertEqual(rep["changed_outside_mask"], 0)
        self.assertEqual(rep["changed_inside_mask"], 16)
        # Hidden RGB under alpha=0 outside mask MUST remain byte-identical!
        self.assertEqual(out.getpixel((0, 0)), (123, 45, 67, 0))
        self.assertEqual(out.getpixel((7, 7)), (30, 90, 220, 255))

    def test_dither_and_tileable_noise(self) -> None:
        d = bayer_dither(32, 32, "#1d2b53", "#29adff", matrix=4)
        self.assertEqual(d.size, (32, 32))
        n = value_noise_tile(32, 32, load_palette("master_topdown"), scale=8, octaves=2, seed=42)
        self.assertEqual(n.size, (32, 32))
        seams = audit_tile_seams(n, max_mean_diff=60.0)
        self.assertIn("x_seam_diff", seams)


if __name__ == "__main__":
    unittest.main()
