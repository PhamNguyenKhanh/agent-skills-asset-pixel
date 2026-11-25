"""Tests for core presets, palettes, OKLab math, and SpendLedger security."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from pixel_forge.core.ledger import SpendLedger, redact_secrets
from pixel_forge.core.palette import (
    extract_palette,
    kmeans_palette,
    list_palettes,
    load_palette,
    oklab_to_srgb,
    remap_image_to_palette,
    srgb_to_oklab,
)
from pixel_forge.core.presets import get_preset, list_presets
from pixel_forge.core.spec import parse_size, slugify


class TestCoreModules(unittest.TestCase):
    def test_presets_and_palettes_loaded(self) -> None:
        pals = list_palettes()
        self.assertGreaterEqual(len(pals), 11)
        self.assertIn("master_topdown", pals)
        self.assertIn("pico-8", pals)
        self.assertIn("gameboy", pals)

        presets = list_presets()
        self.assertGreaterEqual(len(presets), 8)
        stardew = get_preset("topdown-34-stardew")
        self.assertTrue(stardew.forbid_pure_black_outline)
        self.assertEqual(stardew.allow_ground_shadow_alpha, 130)

    def test_parse_size_and_slugify(self) -> None:
        self.assertEqual(parse_size("32x48"), (32, 48))
        self.assertEqual(parse_size("64"), (64, 64))
        self.assertEqual(slugify("Wooden Chest!! #1"), "wooden_chest_1")
        with self.assertRaises(ValueError):
            parse_size("0x16")

    def test_oklab_roundtrip_and_palette_remap(self) -> None:
        sample = np.array([[20, 13, 24], [232, 168, 37], [28, 224, 201], [255, 255, 255]], dtype=np.uint8)
        back = oklab_to_srgb(srgb_to_oklab(sample))
        self.assertTrue(np.allclose(sample, back, atol=1))

        # Test strict vs guided remap preserving alpha
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(2, 6):
            for x in range(2, 6):
                img.putpixel((x, y), (200, 50, 40, 255))
        pal = load_palette("gameboy")
        guided_img, guided_rep = remap_image_to_palette(img, pal, policy="guided")
        self.assertEqual(guided_rep["out_of_palette_pixels"], 16)
        self.assertEqual(guided_rep["remapped_pixels"], 0)
        self.assertEqual(guided_img.tobytes(), img.tobytes())

        strict_img, strict_rep = remap_image_to_palette(img, pal, policy="strict")
        self.assertEqual(strict_rep["remapped_pixels"], 16)
        extracted = extract_palette(strict_img, max_colors=8)
        self.assertTrue(set(extracted.colors).issubset(set(pal.colors)))

        km = kmeans_palette(np.random.default_rng(0).integers(0, 255, size=(200, 3), dtype=np.uint8), 6, seed=0)
        self.assertEqual(km.shape[1], 3)
        self.assertLessEqual(len(km), 6)

    def test_ledger_redaction_and_budget_cap(self) -> None:
        secret = "sk-super-secret-key-987654321"
        self.assertNotIn(secret, redact_secrets(f"Bearer {secret}", extra_secrets=[secret]))
        self.assertIn("[redacted]", redact_secrets(f"Bearer {secret}", extra_secrets=[secret]))

        with tempfile.TemporaryDirectory() as td:
            ledger = SpendLedger(Path(td))
            ledger.record(
                kind="image",
                route="api:gemini",
                model="gemini-2.5-flash-image",
                estimate_usd=0.04,
                status="ok",
                note=f"key={secret}",
                extra_secrets=[secret],
            )
            raw_text = ledger.path.read_text(encoding="utf-8")
            self.assertNotIn(secret, raw_text)
            self.assertEqual(ledger.summary()["paid_calls"], 1)
            with self.assertRaises(PermissionError):
                ledger.check_budget(0.05, budget_usd=0.05)


if __name__ == "__main__":
    unittest.main()
