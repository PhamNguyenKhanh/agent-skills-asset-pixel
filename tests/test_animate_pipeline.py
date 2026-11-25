"""Tests for all 3 animation tracks: procedural (offline), sheet (simulated), and video (FFmpeg simulated)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from pixel_forge.animate.pipeline import create_animation
from pixel_forge.core.spec import AnimationSpec
from pixel_forge.providers.router import MediaRouter


def _make_clean_sprite(size: int = 32) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Grounded symmetrical character silhouette with warm hue-shifted colors
    draw.rectangle([10, 6, 21, 27], fill=(133, 68, 30, 255), outline=(20, 13, 24, 255))
    draw.rectangle([12, 8, 19, 13], fill=(186, 107, 50, 255))
    draw.rectangle([13, 10, 14, 11], fill=(232, 168, 37, 255))
    draw.rectangle([17, 10, 18, 11], fill=(232, 168, 37, 255))
    # Soft ground contact shadow 'S' at rows 28..29
    draw.ellipse([9, 27, 22, 30], fill=(16, 8, 24, 130))
    # Re-stamp bottom foot border opaque on top of shadow
    draw.line([10, 27, 21, 27], fill=(20, 13, 24, 255))
    return img


class TestAnimatePipeline(unittest.TestCase):
    def test_procedural_track_all_actions_and_static_zone(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            master = root / "hero.png"
            _make_clean_sprite(32).save(master)
            router = MediaRouter(offline=True, project_root=root)

            for action in ("idle", "walk", "jump", "attack", "fire", "sway", "open", "hurt"):
                spec = AnimationSpec(
                    asset_id="hero",
                    action=action,
                    brief=f"hero {action}",
                    frame_count=6,
                    fps=8,
                    track="procedural",
                    preset="topdown-34-stardew",
                    lock_static_bottom_rows=2,
                )
                res = create_animation(master, spec, router, root / f"out_{action}")
                self.assertEqual(res.status, "ok")
                self.assertEqual(len(res.frames), 6)
                # Verify bottom 2 static rows stayed 100% pixel-identical across all frames!
                base_bot = np.asarray(Image.open(master).convert("RGBA"))[-2:]
                for f in res.frames:
                    self.assertTrue(np.array_equal(np.asarray(f)[-2:], base_bot))
                # Verify animation is not completely frozen
                diffs = [
                    int(np.any(np.asarray(res.frames[i]) != np.asarray(res.frames[i + 1]), axis=-1).sum())
                    for i in range(len(res.frames) - 1)
                ]
                self.assertGreater(sum(diffs), 0, f"Action {action} produced frozen frames")

    def test_sheet_track_simulated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            master = root / "chest.png"
            _make_clean_sprite(32).save(master)
            router = MediaRouter(offline=True, project_root=root)
            spec = AnimationSpec(
                asset_id="chest",
                action="idle",
                brief="gentle idle pulse",
                frame_count=4,
                fps=8,
                track="sheet",
                preset="freestyle",
            )
            res = create_animation(master, spec, router, root / "out_sheet")
            self.assertEqual(res.status, "ok")
            self.assertEqual(len(res.frames), 4)
            self.assertEqual(res.frames[0].size, (32, 32))

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not on PATH")
    def test_video_track_simulated_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            master = root / "hero.png"
            _make_clean_sprite(32).save(master)
            router = MediaRouter(offline=True, project_root=root)
            spec = AnimationSpec(
                asset_id="hero",
                action="walk",
                brief="hero walking loop",
                frame_count=6,
                fps=8,
                playback="loop",
                track="video",
                preset="side-view-pixel-look",
            )
            res = create_animation(master, spec, router, root / "out_video")
            self.assertEqual(res.status, "ok")
            self.assertEqual(len(res.frames), 6)
            self.assertEqual(res.frames[0].size, (32, 32))


if __name__ == "__main__":
    unittest.main()
