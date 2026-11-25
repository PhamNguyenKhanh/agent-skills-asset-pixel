"""Tests for PNG, transparent GIF, pure-Python binary .aseprite round-trip, Lua, and Unity 6 exporters."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from pixel_forge.core.spec import ExportSpec, SpatialMeta
from pixel_forge.export.aseprite import inspect_aseprite_file
from pixel_forge.export.bundle import export_bundle


def _sample_frames(n: int = 4) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for i in range(n):
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        dy = i % 2
        # Soft ground shadow layer (alpha 130) to also test automatic Shadow + Main layer splitting in .aseprite!
        draw.ellipse([9, 27, 22, 30], fill=(16, 8, 24, 130))
        draw.rectangle([10, 8 + dy, 21, 26 + dy], fill=(133, 68, 30, 255), outline=(20, 13, 24, 255))
        draw.rectangle([14, 14 + dy, 17, 17 + dy], fill=(232, 168, 37, 255))
        frames.append(img)
    return frames


class TestExporters(unittest.TestCase):
    def test_full_export_bundle_png_gif_aseprite_unity_lua_html(self) -> None:
        frames = _sample_frames(4)
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "chest_bundle"
            spatial = SpatialMeta.default_for(32, 32, "top_down_3_4")
            exp = export_bundle(
                frames,
                out_dir,
                asset_id="oak_chest",
                action="idle",
                fps=8,
                playback="loop",
                spatial=spatial,
                export_spec=ExportSpec(
                    formats=("png", "gif", "aseprite", "unity"),
                    pixels_per_unit=32,
                    preview_scale=4,
                    emit_lua=True,
                    emit_html_preview=True,
                ),
            )

            # 1. PNG + Spritesheet + Indexed PNG-8 + Atlas JSON
            sheet_path = Path(exp["png"]["sheet"]["path"])
            self.assertTrue(sheet_path.is_file())
            with Image.open(sheet_path) as s_img:
                self.assertEqual(s_img.size, (32 * 4, 32))
            indexed_path = Path(exp["png"]["indexed"]["path"])
            with Image.open(indexed_path) as idx_img:
                self.assertEqual(idx_img.mode, "P")
            atlas = json.loads(Path(exp["png"]["atlas_json"]).read_text(encoding="utf-8"))
            self.assertEqual(len(atlas["frames"]), 4)

            # 2. Animated GIF decoding check
            gif_path = Path(exp["gif"]["path"])
            self.assertTrue(gif_path.is_file())
            with Image.open(gif_path) as g_img:
                self.assertEqual(getattr(g_img, "n_frames", 1), 4)
                self.assertEqual(g_img.info.get("transparency"), 255)
                self.assertEqual(g_img.convert("RGBA").getpixel((0, 0))[3], 0)

            # 3. Pure-Python .aseprite binary structural round-trip verification!
            ase_path = Path(exp["aseprite"]["path"])
            self.assertTrue(ase_path.is_file())
            parsed = inspect_aseprite_file(ase_path)
            self.assertTrue(parsed["valid"])
            self.assertEqual((parsed["width"], parsed["height"]), (32, 32))
            self.assertEqual(parsed["frames"], 4)
            self.assertEqual(parsed["layers"], ["Shadow", "Main"])
            self.assertEqual(parsed["cels_decompressed"], 8)  # 4 frames x 2 layers
            self.assertEqual(parsed["tags"][0]["name"], "idle")
            self.assertEqual(parsed["slices"][0]["pivot"], [spatial.pivot_x, spatial.pivot_y])

            # 4. Optional Lua script
            lua_path = Path(exp["lua"]["path"])
            self.assertTrue(lua_path.is_file())
            self.assertIn("frames_data", lua_path.read_text(encoding="utf-8"))

            # 5. Unity 6 bundle + PixelForgeImporter.cs Safe Core Pattern checks
            job_path = Path(exp["unity"]["job_json"])
            self.assertTrue(job_path.is_file())
            job = json.loads(job_path.read_text(encoding="utf-8"))
            self.assertEqual(job["version"], 1)
            self.assertEqual(job["pixelsPerUnit"], 32)
            self.assertEqual(len(job["texture"]["slices"]), 4)
            self.assertEqual(len(job["clips"][0]["frames"]), 4)

            cs_text = Path(exp["unity"]["importer_cs"]).read_text(encoding="utf-8")
            for required_token in (
                "FilterMode.Point",
                "mipmapEnabled = false",
                "TextureImporterCompression.Uncompressed",
                "SpriteMeshType.FullRect",
                "ISpriteEditorDataProvider",
                "ISpriteFrameEditCapability",
                "EEditCapability.CreateAndDeleteSprite",
                "EEditCapability.EditSpriteRect",
                "EEditCapability.EditPivot",
                "SpriteAlignment.Custom",
            ):
                self.assertIn(required_token, cs_text)

            # 6. Review sheet & HTML viewers
            self.assertTrue(Path(exp["preview"]["review_sheet"]["path"]).is_file())
            self.assertGreaterEqual(len(exp["preview"]["html_viewers"]), 3)


if __name__ == "__main__":
    unittest.main()
