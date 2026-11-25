"""Offline deterministic simulated provider for testing, dry-runs, and zero-cost prototyping."""

from __future__ import annotations

import hashlib
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from pixel_forge.core.image_io import save_deterministic_png, sha256_file
from pixel_forge.providers.base import MediaRequest, MediaResult, ProviderCapabilities, ProviderError

SIMULATED_CAPABILITIES: dict[str, ProviderCapabilities] = {
    "image": ProviderCapabilities(
        name="simulated",
        family="offline",
        kind="image",
        default_model="simulated-pixel-v1",
        max_references=16,
        supports_transparent=True,
        estimate_usd=0.0,
    ),
    "video": ProviderCapabilities(
        name="simulated",
        family="offline",
        kind="video",
        default_model="simulated-video-v1",
        max_references=4,
        supports_last_frame=True,
        estimate_usd=0.0,
    ),
}


def _seed_from_prompt(prompt: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{prompt}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


def _draw_simulated_sprite(canvas_size: tuple[int, int], prompt: str, seed: int, key_rgb: tuple[int, int, int]) -> Image.Image:
    """Render an oversized synthetic pixel-art block sprite on a chroma-key background."""
    w, h = canvas_size
    rng_seed = _seed_from_prompt(prompt, seed)
    img = Image.new("RGBA", (w, h), (*key_rgb, 255))
    draw = ImageDraw.Draw(img)

    # Render on a logical 16x16 virtual grid upscaled cleanly into the canvas (mimicking AI block output).
    grid = 16
    cell = max(2, min(w, h) // grid)
    ox = (w - grid * cell) // 2
    oy = (h - grid * cell) // 2

    low = prompt.lower()
    if any(k in low for k in ("chest", "box", "crate", "wood")):
        body = (133, 68, 30, 255)
        light = (186, 107, 50, 255)
        trim = (232, 168, 37, 255)
        outline = (20, 13, 24, 255)
    elif any(k in low for k in ("potion", "flask", "fire", "red", "ruby")):
        body = (222, 69, 18, 255)
        light = (247, 158, 30, 255)
        trim = (255, 250, 122, 255)
        outline = (64, 12, 8, 255)
    elif any(k in low for k in ("slime", "leaf", "tree", "green", "forest")):
        body = (42, 115, 58, 255)
        light = (77, 176, 80, 255)
        trim = (155, 227, 102, 255)
        outline = (13, 33, 23, 255)
    else:
        r = 60 + (rng_seed % 140)
        g = 60 + ((rng_seed >> 8) % 140)
        b = 80 + ((rng_seed >> 16) % 140)
        body = (r, g, b, 255)
        light = (min(255, r + 50), min(255, g + 50), min(255, b + 40), 255)
        trim = (232, 168, 37, 255)
        outline = (20, 13, 24, 255)

    def put_cell(gx: int, gy: int, color: tuple[int, int, int, int]) -> None:
        x0 = ox + gx * cell
        y0 = oy + gy * cell
        draw.rectangle([x0, y0, x0 + cell - 1, y0 + cell - 1], fill=color)

    # Symmetric iconic silhouette (body + cap/helmet + eyes/trim)
    for gy in range(3, 14):
        half_w = 5 if 5 <= gy <= 11 else (4 if gy in (4, 12) else 3)
        for gx in range(8 - half_w, 8 + half_w):
            is_edge = gy in (3, 13) or gx in (8 - half_w, 8 + half_w - 1)
            if is_edge:
                put_cell(gx, gy, outline)
            elif gy <= 6 and gx < 9:
                put_cell(gx, gy, light)
            else:
                put_cell(gx, gy, body)
    # Trim / eyes / emblem
    for gx in (6, 9):
        put_cell(gx, 7, trim)
    for gx in range(5, 11):
        put_cell(gx, 9, trim)
    return img


def call_simulated(req: MediaRequest) -> MediaResult:
    """Produce deterministic offline image, sprite sheet, or MP4 clip for tests & offline runs."""
    req.out_dir.mkdir(parents=True, exist_ok=True)
    key_rgb = tuple(req.extra.get("key_rgb", (255, 0, 255)))

    if req.kind == "image":
        cols = int(req.extra.get("sheet_cols", 1))
        rows = int(req.extra.get("sheet_rows", 1))
        if cols > 1 or rows > 1:
            cell_w = int(req.extra.get("cell_w", 64))
            cell_h = int(req.extra.get("cell_h", 64))
            sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (*key_rgb, 255))
            base = None
            if req.references and req.references[0].is_file():
                base = Image.open(req.references[0]).convert("RGBA").resize((cell_w, cell_h), Image.Resampling.NEAREST)
            total = cols * rows
            for idx in range(total):
                r_idx, c_idx = divmod(idx, cols)
                frame = base.copy() if base is not None else _draw_simulated_sprite((cell_w, cell_h), req.prompt, req.seed, key_rgb)
                dy = int(round(math.sin(2.0 * math.pi * idx / max(1, total)) * max(1, cell_h // 16)))
                cell_img = Image.new("RGBA", (cell_w, cell_h), (*key_rgb, 255))
                cell_img.alpha_composite(frame, dest=(0, dy))
                sheet.paste(cell_img, (c_idx * cell_w, r_idx * cell_h))
            out_path = req.out_dir / "generated.png"
            info = save_deterministic_png(sheet, out_path)
            return MediaResult(
                status="ok",
                route="offline:simulated",
                model="simulated-sheet-v1",
                artifact_path=out_path,
                sha256=info["sha256"],
                estimate_usd=0.0,
                notes=["Generated offline with simulated provider (zero API cost)."],
            )

        w, h = 256, 256
        if "x" in req.size:
            parts = req.size.lower().split("x")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                w, h = min(512, int(parts[0])), min(512, int(parts[1]))
        img = _draw_simulated_sprite((w, h), req.prompt, req.seed, key_rgb)
        out_path = req.out_dir / "generated.png"
        info = save_deterministic_png(img, out_path)
        return MediaResult(
            status="ok",
            route="offline:simulated",
            model="simulated-pixel-v1",
            artifact_path=out_path,
            sha256=info["sha256"],
            estimate_usd=0.0,
            notes=["Generated offline with simulated provider (zero API cost)."],
        )

    # Simulated video via FFmpeg if available
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ProviderError("simulated video requires ffmpeg on PATH", code="missing_ffmpeg")
    if not req.references or not req.references[0].is_file():
        raise ProviderError("simulated video requires an input reference PNG", code="invalid_request")
    src = Image.open(req.references[0]).convert("RGBA")
    frames_dir = req.out_dir / "_sim_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    num_frames = 12
    for idx in range(num_frames):
        frame = Image.new("RGBA", src.size, (*key_rgb, 255))
        dy = int(round(math.sin(2.0 * math.pi * idx / num_frames) * 4))
        frame.alpha_composite(src, dest=(0, dy))
        frame.convert("RGB").save(frames_dir / f"f_{idx:03d}.png")
    out_mp4 = req.out_dir / "generated.mp4"
    cmd = [
        ffmpeg, "-y", "-framerate", "12",
        "-i", str(frames_dir / "f_%03d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "12",
        str(out_mp4),
    ]
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if done.returncode != 0 or not out_mp4.is_file():
        raise ProviderError(f"ffmpeg failed creating simulated video: {done.stderr[-200:]}", code="ffmpeg_failed")
    return MediaResult(
        status="ok",
        route="offline:simulated",
        model="simulated-video-v1",
        artifact_path=out_mp4,
        sha256=sha256_file(out_mp4),
        estimate_usd=0.0,
        notes=["Generated offline simulated MP4 via FFmpeg."],
    )
