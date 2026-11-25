"""Tests for 2-tier QA gates and end-to-end CLI workflows."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner
from PIL import Image, ImageDraw

from pixel_forge.cli import main
from pixel_forge.qa.gates import audit_image


class TestQAAndCLI(unittest.TestCase):
    def test_qa_detects_bad_and_passes_clean(self) -> None:
        # Clean 32x32 sprite aligned to 16px grid, zero AA, zero orphans, warm outline (no #000000)
        clean = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(clean)
        draw.rectangle([8, 12, 23, 30], fill=(133, 68, 30, 255), outline=(20, 13, 24, 255))
        rep_clean = audit_image(clean, preset_name="topdown-34-stardew")
        self.assertTrue(rep_clean["hard_passed"], rep_clean)

        # Broken sprite: anti-aliased pixel, pure #000000, orphan pixel, bad grid 30x30
        broken = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
        broken.putpixel((2, 2), (255, 0, 255, 100))  # semi-alpha + orphan
        broken.putpixel((10, 10), (0, 0, 0, 255))  # pure black forbidden in stardew + orphan
        rep_bad = audit_image(broken, preset_name="topdown-34-stardew")
        self.assertFalse(rep_bad["hard_passed"])
        self.assertFalse(rep_bad["tier1_hard"]["binary_alpha"]["passed"])
        self.assertFalse(rep_bad["tier1_hard"]["grid_alignment"]["passed"])
        self.assertFalse(rep_bad["tier1_hard"]["orphan_pixels"]["passed"])
        self.assertFalse(rep_bad["tier1_hard"]["palette"]["passed"])

    def test_cli_end_to_end_offline_workflow(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            # 1. doctor --json
            r_doc = runner.invoke(main, ["doctor", "--json"])
            self.assertEqual(r_doc.exit_code, 0, r_doc.output)
            doc_data = json.loads(r_doc.output)
            self.assertIn("palettes", doc_data)
            self.assertIn("presets", doc_data)

            # 2. asset --offline (simulated) -> PNG + GIF + .aseprite + Unity
            out_asset = root / "knight_asset"
            r_asset = runner.invoke(
                main,
                [
                    "asset",
                    "wooden treasure chest",
                    "--size",
                    "32x32",
                    "--preset",
                    "topdown-34-stardew",
                    "--offline",
                    "--formats",
                    "png,gif,aseprite,unity",
                    "--out",
                    str(out_asset),
                    "--json",
                ],
            )
            self.assertEqual(r_asset.exit_code, 0, r_asset.output)
            asset_data = json.loads(r_asset.output)
            self.assertEqual(asset_data["status"], "ok")
            poster_png = Path(asset_data["exports"]["png"]["poster"]["path"])
            self.assertTrue(poster_png.is_file())

            # 3. animate --offline (procedural) from generated asset
            out_anim = root / "chest_open"
            r_anim = runner.invoke(
                main,
                [
                    "animate",
                    str(poster_png),
                    "chest opening slowly",
                    "--action",
                    "open",
                    "--frames",
                    "6",
                    "--fps",
                    "8",
                    "--playback",
                    "once",
                    "--offline",
                    "--formats",
                    "png,gif,aseprite,unity",
                    "--out",
                    str(out_anim),
                    "--json",
                ],
            )
            self.assertEqual(r_anim.exit_code, 0, r_anim.output)
            anim_data = json.loads(r_anim.output)
            self.assertEqual(anim_data["frame_count"], 6)
            ase_file = Path(anim_data["exports"]["aseprite"]["path"])
            self.assertTrue(ase_file.is_file())

            # 4. inspect-aseprite --json
            r_ase = runner.invoke(main, ["inspect-aseprite", str(ase_file), "--json"])
            self.assertEqual(r_ase.exit_code, 0, r_ase.output)
            ase_info = json.loads(r_ase.output)
            self.assertTrue(ase_info["valid"])
            self.assertEqual(ase_info["frames"], 6)

            # 5. audit --json
            r_aud = runner.invoke(main, ["audit", str(out_anim), "--preset", "topdown-34-stardew", "--json"])
            self.assertEqual(r_aud.exit_code, 0, r_aud.output)
            aud_data = json.loads(r_aud.output)
            self.assertTrue(aud_data["hard_passed"])


if __name__ == "__main__":
    unittest.main()
