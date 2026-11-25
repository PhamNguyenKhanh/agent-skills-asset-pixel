"""Crisp transparent animated GIF writer (disposal=2, reserved slot 255, zero ghosting)."""

from __future__ import annotations

from itertools import chain
from pathlib import Path
from typing import Sequence

from PIL import GifImagePlugin, Image, ImageChops

GIF_TRANSPARENT = 255
GIF_ALPHA_LUT = (0,) * 128 + (255,) * 128


def _quantize_frame_for_gif(canvas: Image.Image) -> Image.Image:
    rgba = canvas.convert("RGBA")
    visible = rgba.getchannel("A").point(GIF_ALPHA_LUT)
    bbox = visible.getbbox()
    if bbox is None:
        indexed = Image.new("P", rgba.size, GIF_TRANSPARENT)
        indexed.putpalette(bytes(768))
        return indexed

    rgb = rgba.convert("RGB")
    invisible = None
    if visible.getextrema()[0] == 0:
        # Mask transparent pixels with an existing visible pixel color so quantization wastes 0 palette slots.
        left, top, right, _ = bbox
        row = visible.crop((left, top, right, top + 1)).getbbox()
        assert row is not None
        invisible = ImageChops.invert(visible)
        rgb.paste(rgb.getpixel((left + row[0], top)), (0, 0, *rgba.size), invisible)

    indexed = rgb.quantize(colors=GIF_TRANSPARENT, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    if invisible is not None:
        indexed.paste(GIF_TRANSPARENT, (0, 0, *rgba.size), invisible)

    palette = bytes(indexed.getpalette()[: 3 * GIF_TRANSPARENT]).ljust(768, b"\0")
    indexed.putpalette(palette)
    return indexed


def write_gif(
    frames: Sequence[Image.Image],
    durations_ms: Sequence[int],
    output_path: Path | str,
    *,
    playback: str = "loop",
    scale: int = 1,
) -> dict:
    """Write a crisp transparent animated GIF with explicit per-frame disposal=2 and exact 10ms timing."""
    if not frames:
        raise ValueError("Cannot write GIF with zero frames.")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    prepared: list[Image.Image] = []
    for f in frames:
        rgba = f.convert("RGBA")
        if scale > 1:
            rgba = rgba.resize((rgba.width * scale, rgba.height * scale), Image.Resampling.NEAREST)
        prepared.append(rgba)

    reverse = range(len(prepared) - 2, 0, -1) if playback == "ping_pong" and len(prepared) > 2 else ()
    order = list(chain(range(len(prepared)), reverse))

    with target.open("wb") as fp:
        for out_idx, src_idx in enumerate(order):
            indexed = _quantize_frame_for_gif(prepared[src_idx])
            dur_ms = durations_ms[src_idx] if src_idx < len(durations_ms) else 100
            rounded_ms = max(1, (int(dur_ms) + 5) // 10) * 10
            if out_idx == 0:
                info = {"background": GIF_TRANSPARENT, "transparency": GIF_TRANSPARENT}
                if playback != "once":
                    info["loop"] = 0
                header, _ = GifImagePlugin.getheader(indexed, info=info)
                fp.writelines(header)
            fp.writelines(
                GifImagePlugin.getdata(
                    indexed,
                    duration=rounded_ms,
                    transparency=GIF_TRANSPARENT,
                    disposal=2,
                    include_color_table=out_idx != 0,
                )
            )
        fp.write(b";")

    return {
        "path": str(target),
        "width": prepared[0].width,
        "height": prepared[0].height,
        "frames_written": len(order),
        "playback": playback,
        "scale": scale,
    }
