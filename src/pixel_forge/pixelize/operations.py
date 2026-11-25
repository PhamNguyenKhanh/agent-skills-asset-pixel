"""Deterministic pixel-art raster operations: fit, resize, outline, shadow, mirror, dither, noise."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from pixel_forge.core.palette import Palette, auto_outline_color, parse_hex


def fit_canvas(
    image: Image.Image,
    target_size: tuple[int, int],
    *,
    fit_mode: str = "contain",
    align: str = "bottom",
    padding: int = 0,
    trim: bool = True,
) -> Image.Image:
    """Fit an RGBA sprite cleanly onto an exact logical WxH canvas using nearest-neighbor scaling."""
    rgba = image.convert("RGBA")
    tw, th = target_size
    if trim:
        bbox = rgba.getchannel("A").getbbox()
        if bbox is None:
            return Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        rgba = rgba.crop(bbox)

    avail_w = max(1, tw - 2 * padding)
    avail_h = max(1, th - 2 * padding)

    if fit_mode == "stretch":
        resized = rgba.resize((avail_w, avail_h), Image.Resampling.NEAREST)
    else:
        scale = min(avail_w / rgba.width, avail_h / rgba.height)
        new_w = max(1, min(avail_w, int(round(rgba.width * scale))))
        new_h = max(1, min(avail_h, int(round(rgba.height * scale))))
        resized = rgba.resize((new_w, new_h), Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ox = (tw - resized.width) // 2
    if align == "bottom":
        oy = max(0, th - resized.height - padding)
    elif align == "top":
        oy = padding
    else:
        oy = (th - resized.height) // 2
    canvas.paste(resized, (ox, oy))
    return canvas


def nearest_resize(image: Image.Image, scale: int) -> Image.Image:
    """Integer nearest-neighbor upscaling (never blurs pixel art)."""
    if scale < 1:
        raise ValueError("Scale factor must be >= 1.")
    rgba = image.convert("RGBA")
    if scale == 1:
        return rgba
    return rgba.resize((rgba.width * scale, rgba.height * scale), Image.Resampling.NEAREST)


def add_outline(
    image: Image.Image,
    *,
    color: str | tuple[int, int, int] = "auto",
    mode: str = "outer",
) -> Image.Image:
    """Add a crisp 1px 4-connected pixel-art outline around opaque regions."""
    rgba = np.asarray(image.convert("RGBA")).copy()
    h, w = rgba.shape[:2]
    opaque = rgba[..., 3] >= 128
    if not opaque.any():
        return Image.fromarray(rgba, mode="RGBA")

    p = np.pad(opaque, 1, mode="constant", constant_values=False)
    adj_up = p[:-2, 1:-1]
    adj_dn = p[2:, 1:-1]
    adj_lt = p[1:-1, :-2]
    adj_rt = p[1:-1, 2:]
    border = (~opaque) & (adj_up | adj_dn | adj_lt | adj_rt)

    if mode != "outer":
        raise ValueError(f"Unsupported outline mode: {mode!r}")

    if isinstance(color, str) and color.lower() == "selective":
        ys, xs = np.where(border)
        for y, x in zip(ys.tolist(), xs.tolist()):
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and opaque[ny, nx]:
                    nr, ng, nb = int(rgba[ny, nx, 0]), int(rgba[ny, nx, 1]), int(rgba[ny, nx, 2])
                    rgba[y, x] = (
                        max(12, int(nr * 0.34)),
                        max(10, int(ng * 0.30)),
                        max(18, int(min(255, nb * 0.42 + 8))),
                        255,
                    )
                    break
        return Image.fromarray(rgba, mode="RGBA")

    if isinstance(color, str):
        rgb = auto_outline_color(image) if color.lower() == "auto" else parse_hex(color)
    else:
        rgb = (int(color[0]), int(color[1]), int(color[2]))

    rgba[border] = (rgb[0], rgb[1], rgb[2], 255)
    return Image.fromarray(rgba, mode="RGBA")


def add_ground_shadow(
    image: Image.Image,
    *,
    color: tuple[int, int, int] = (16, 8, 24),
    alpha: int = 130,
) -> Image.Image:
    """Add a soft elliptical ground-contact shadow ('S') underneath the sprite's opaque footprint."""
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba)
    opaque = arr[..., 3] >= 128
    if not opaque.any():
        return rgba
    ys, xs = np.where(opaque)
    x0, x1 = int(xs.min()), int(xs.max())
    y_bot = int(ys.max())
    w, h = rgba.size

    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_layer)
    sx0 = max(0, x0)
    sx1 = min(w - 1, x1)
    sy0 = max(0, y_bot - max(1, h // 16))
    sy1 = min(h - 1, y_bot + max(1, h // 16))
    if sx1 > sx0 and sy1 >= sy0:
        draw.ellipse([sx0, sy0, sx1, sy1], fill=(color[0], color[1], color[2], alpha))

    sh_arr = np.asarray(shadow_layer).copy()
    sh_arr[opaque] = arr[opaque]
    return Image.fromarray(sh_arr, mode="RGBA")


def check_symmetry(image: Image.Image, axis: str = "horizontal") -> float:
    """Return 0.0..1.0 pixel agreement ratio between sprite and its mirror."""
    arr = np.asarray(image.convert("RGBA"))
    flipped = np.fliplr(arr) if axis == "horizontal" else np.flipud(arr)
    union = (arr[..., 3] > 0) | (flipped[..., 3] > 0)
    if not union.any():
        return 1.0
    same = np.all(arr == flipped, axis=-1) & union
    return round(float(same.sum()) / float(union.sum()), 4)


def mirror_sprite(image: Image.Image, axis: str = "horizontal") -> Image.Image:
    """Mirror sprite cleanly along horizontal or vertical axis."""
    rgba = image.convert("RGBA")
    if axis == "horizontal":
        return rgba.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if axis == "vertical":
        return rgba.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    raise ValueError(f"Unsupported mirror axis: {axis!r}. Use 'horizontal' or 'vertical'.")


def bayer_dither(
    width: int,
    height: int,
    color1: str | tuple[int, int, int],
    color2: str | tuple[int, int, int],
    *,
    matrix: int = 4,
    direction: str = "vertical",
) -> Image.Image:
    """Generate an ordered Bayer-matrix dithered pixel-art gradient."""
    c1 = parse_hex(color1) if isinstance(color1, str) else color1
    c2 = parse_hex(color2) if isinstance(color2, str) else color2
    if matrix == 2:
        bayer = np.array([[0, 2], [3, 1]], dtype=np.float32) / 4.0
    else:
        bayer = (
            np.array(
                [
                    [0, 8, 2, 10],
                    [12, 4, 14, 6],
                    [3, 11, 1, 9],
                    [15, 7, 13, 5],
                ],
                dtype=np.float32,
            )
            / 16.0
        )
    m = bayer.shape[0]
    yy, xx = np.mgrid[0:height, 0:width]
    t = (yy / max(1, height - 1)) if direction == "vertical" else (xx / max(1, width - 1))
    thresh = bayer[yy % m, xx % m]
    choose_c2 = t > thresh
    out = np.zeros((height, width, 4), dtype=np.uint8)
    out[~choose_c2] = (*c1, 255)
    out[choose_c2] = (*c2, 255)
    return Image.fromarray(out, mode="RGBA")


def value_noise_tile(
    width: int,
    height: int,
    palette: Palette,
    *,
    scale: int = 8,
    octaves: int = 2,
    seed: int = 0,
) -> Image.Image:
    """Generate a seamless tileable procedural value-noise texture snapped to a palette."""
    rng = np.random.default_rng(seed)
    field = np.zeros((height, width), dtype=np.float32)
    amp = 1.0
    total_amp = 0.0
    cur_scale = max(2, scale)

    for _ in range(max(1, octaves)):
        gx = max(2, width // cur_scale)
        gy = max(2, height // cur_scale)
        grid = rng.random((gy, gx), dtype=np.float32)
        yy = (np.arange(height, dtype=np.float32) / height) * gy
        xx = (np.arange(width, dtype=np.float32) / width) * gx
        y0 = np.floor(yy).astype(np.int32) % gy
        x0 = np.floor(xx).astype(np.int32) % gx
        y1 = (y0 + 1) % gy
        x1 = (x0 + 1) % gx
        fy = yy - np.floor(yy)
        fx = xx - np.floor(xx)
        sy = fy * fy * (3.0 - 2.0 * fy)
        sx = fx * fx * (3.0 - 2.0 * fx)
        top = grid[y0[:, None], x0[None, :]] * (1.0 - sx[None, :]) + grid[y0[:, None], x1[None, :]] * sx[None, :]
        bot = grid[y1[:, None], x0[None, :]] * (1.0 - sx[None, :]) + grid[y1[:, None], x1[None, :]] * sx[None, :]
        layer = top * (1.0 - sy[:, None]) + bot * sy[:, None]
        field += layer * amp
        total_amp += amp
        amp *= 0.5
        cur_scale = max(1, cur_scale // 2)

    field /= max(1e-6, total_amp)
    pal_arr = palette.array
    idx = np.clip(np.floor(field * len(pal_arr)).astype(np.int32), 0, len(pal_arr) - 1)
    out = np.zeros((height, width, 4), dtype=np.uint8)
    out[..., :3] = pal_arr[idx]
    out[..., 3] = 255
    return Image.fromarray(out, mode="RGBA")
