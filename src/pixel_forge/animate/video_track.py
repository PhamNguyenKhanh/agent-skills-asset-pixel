"""Track B — Image-to-Video -> FFmpeg -> Soft-Matte -> Lattice Snap -> Gait/Retime -> OKLab Colour Lock."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from pixel_forge.animate.timing import find_best_loop, lock_static_zone, register_frames_to_anchor, retime_oneshot
from pixel_forge.core.image_io import save_deterministic_png
from pixel_forge.core.palette import color_lock_oklab, extract_palette, remap_image_to_palette
from pixel_forge.core.presets import get_preset
from pixel_forge.core.spec import AnimationSpec
from pixel_forge.pixelize.matte import quiet_key_color, remove_background
from pixel_forge.pixelize.operations import fit_canvas
from pixel_forge.providers.base import MediaRequest
from pixel_forge.providers.router import MediaRouter


def prepare_i2v_input(
    master_img: Image.Image,
    key_rgb: tuple[int, int, int],
    *,
    canvas_size: tuple[int, int] = (512, 512),
) -> tuple[Image.Image, dict[str, Any]]:
    """Integer-upscale the 1x pixel sprite onto a solid quiet-key video canvas with action headroom."""
    cw, ch = canvas_size
    max_scale = max(1, min((cw * 3 // 4) // max(1, master_img.width), (ch * 3 // 4) // max(1, master_img.height)))
    up_w = master_img.width * max_scale
    up_h = master_img.height * max_scale
    up = master_img.resize((up_w, up_h), Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", (cw, ch), (*key_rgb, 255))
    ox = (cw - up_w) // 2
    oy = int(ch * 0.85) - up_h
    oy = max(0, min(ch - up_h, oy))
    canvas.alpha_composite(up, dest=(ox, oy))
    return canvas, {"scale": max_scale, "offset": [ox, oy], "canvas": [cw, ch], "key_rgb": list(key_rgb)}


def _extract_video_frames(video_path: Path, frames_dir: Path, max_fps: int = 16) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Video animation track requires `ffmpeg` on PATH.")
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "vframe_%04d.png"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={max_fps}",
        str(pattern),
    ]
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {done.stderr[-300:]}")
    return sorted(frames_dir.glob("vframe_*.png"))


def _lattice_snap_frame(
    video_frame: Image.Image,
    prep_meta: dict[str, Any],
    master_size: tuple[int, int],
    key_rgb: tuple[int, int, int],
    *,
    align: str = "bottom",
) -> Image.Image:
    """Read a video frame back onto the sprite's original 1x pixel lattice via cell median sampling."""
    keyed, _ = remove_background(video_frame, key_color=key_rgb, tolerance=56.0, despill=True, binarize_alpha=True)
    scale = int(prep_meta["scale"])
    ox, oy = prep_meta["offset"]
    mw, mh = master_size
    arr = np.asarray(keyed)
    vh, vw = arr.shape[:2]

    # Sample strictly on the known integer lattice around the original sprite placement.
    if scale >= 2 and ox + mw * scale <= vw and oy + mh * scale <= vh:
        out = np.zeros((mh, mw, 4), dtype=np.uint8)
        margin = max(0, scale // 5)
        for r in range(mh):
            y0 = oy + r * scale + margin
            y1 = max(y0 + 1, oy + (r + 1) * scale - margin)
            for c in range(mw):
                x0 = ox + c * scale + margin
                x1 = max(x0 + 1, ox + (c + 1) * scale - margin)
                patch = arr[y0:y1, x0:x1]
                solid = patch[..., 3] >= 128
                if float(solid.mean()) < 0.45:
                    continue
                med = np.median(patch[solid][:, :3], axis=0)
                out[r, c] = (int(round(med[0])), int(round(med[1])), int(round(med[2])), 255)
        snapped = Image.fromarray(out, mode="RGBA")
        if snapped.getchannel("A").getbbox() is not None:
            return snapped

    return fit_canvas(keyed, master_size, fit_mode="contain", align=align, padding=0)


def run_video_track(
    master_path: Path,
    master_img: Image.Image,
    spec: AnimationSpec,
    router: MediaRouter,
    out_dir: Path,
    *,
    dry_run: bool = False,
) -> tuple[list[Image.Image], dict[str, Any]]:
    """Animate a pixel sprite via Image-to-Video, lattice-snap, OKLab colour lock, and loop/retime."""
    preset = get_preset(spec.preset)
    key_name, key_rgb = quiet_key_color(master_img)
    raw_dir = out_dir / "_raw_video"
    raw_dir.mkdir(parents=True, exist_ok=True)

    prep_img, prep_meta = prepare_i2v_input(master_img, key_rgb)
    prep_path = raw_dir / "i2v_input.png"
    save_deterministic_png(prep_img, prep_path)

    prompt = (
        f"Animate this enlarged 2D pixel art character/object in place performing '{spec.action}': {spec.brief or spec.action}. "
        "Static locked camera, no zoom, no pan. Keep the big crisp square pixels, flat palette colors, hard edges, "
        f"and completely flat uniform {key_name} background throughout every frame. No blur, no anti-aliasing, no new props."
    )
    req = MediaRequest(
        kind="video",
        prompt=prompt,
        out_dir=raw_dir,
        references=[prep_path],
        last_frame=prep_path if spec.playback == "loop" else None,
        duration_seconds=5,
        resolution="720p",
        extra={"key_rgb": key_rgb},
    )
    media = router.execute(req, dry_run=dry_run)
    if dry_run:
        return [], {
            "status": "dry_run",
            "track": "video",
            "route": media.route,
            "model": media.model,
            "estimate_usd": media.estimate_usd,
            "key_color": key_name,
            "prep": prep_meta,
            "compiled_prompt": prompt,
        }
    if media.status != "ok" or media.artifact_path is None:
        raise RuntimeError(f"Video animation track has no available video route: {media.notes}")

    extracted = _extract_video_frames(media.artifact_path, raw_dir / "decoded_frames", max_fps=max(12, spec.fps * 2))
    if not extracted:
        raise RuntimeError("No frames decoded from generated video clip.")

    master_pal = extract_palette(master_img, max_colors=preset.max_colors, name=f"{spec.asset_id}_master")
    align = "bottom" if preset.enforce_ground_alignment else "center"

    dense_frames: list[Image.Image] = []
    for fpath in extracted:
        with Image.open(fpath) as vf:
            snapped = _lattice_snap_frame(vf, prep_meta, master_img.size, key_rgb, align=align)
            locked = color_lock_oklab(snapped, master_pal.array, strength=0.85)
            if spec.lock_palette:
                locked, _ = remap_image_to_palette(locked, master_pal, policy="strict")
            dense_frames.append(locked)

    if spec.playback == "once":
        chosen, timing_rep = retime_oneshot(dense_frames, spec.frame_count)
    else:
        chosen, timing_rep = find_best_loop(dense_frames, spec.frame_count)

    chosen = register_frames_to_anchor(master_img, chosen, lock_bottom=preset.enforce_ground_alignment)
    chosen = lock_static_zone(
        master_img,
        chosen,
        bottom_rows=spec.lock_static_bottom_rows,
        preserve_ground_shadow_alpha=preset.allow_ground_shadow_alpha,
    )
    return chosen, {
        "status": "ok",
        "track": "video",
        "route": media.route,
        "model": media.model,
        "estimate_usd": media.estimate_usd,
        "key_color": key_name,
        "decoded_frames": len(extracted),
        "timing": timing_rep,
        "raw_video": str(media.artifact_path),
    }
