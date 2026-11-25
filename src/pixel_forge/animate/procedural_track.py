"""Track C — Deterministic offline procedural pixel-art animation respecting 2D physics rules."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from pixel_forge.animate.timing import lock_static_zone
from pixel_forge.core.palette import extract_palette, remap_image_to_palette
from pixel_forge.core.presets import get_preset
from pixel_forge.core.spec import AnimationSpec


def _classify_motion(action: str, brief: str) -> str:
    text = f"{action} {brief}".lower()
    if any(k in text for k in ("walk", "run", "stride", "march", "move", "step")):
        return "walk"
    if any(k in text for k in ("jump", "hop", "bounce", "leap")):
        return "jump"
    if any(k in text for k in ("attack", "slash", "swing", "strike", "hit", "sword")):
        return "attack"
    if any(k in text for k in ("fire", "flame", "burn", "torch", "lava", "spark", "magic", "glow", "cast")):
        return "fire"
    if any(k in text for k in ("sway", "wind", "cape", "flag", "leaf", "tree", "wave", "float")):
        return "sway"
    if any(k in text for k in ("hurt", "damage", "shake", "flinch", "knock")):
        return "hurt"
    if any(k in text for k in ("open", "chest", "lid", "door", "unlock")):
        return "open"
    return "idle"


def _split_shadow(arr: np.ndarray, shadow_alpha: int | None) -> tuple[np.ndarray, np.ndarray]:
    """Separate optional semi-transparent ground shadow layer ('S') from main opaque sprite."""
    body = arr.copy()
    shadow = np.zeros_like(arr)
    if shadow_alpha is not None:
        is_shadow = (arr[..., 3] > 0) & (arr[..., 3] < 255)
        shadow[is_shadow] = arr[is_shadow]
        body[is_shadow] = (0, 0, 0, 0)
    return body, shadow


def _merge_shadow(body: np.ndarray, shadow: np.ndarray) -> np.ndarray:
    out = shadow.copy()
    opaque = body[..., 3] >= 128
    out[opaque] = body[opaque]
    return out


def _shift_rows(arr: np.ndarray, row_shifts_x: list[int], dy: int = 0) -> np.ndarray:
    """Shift rows horizontally by per-row pixel offsets and vertically by `dy` (pure integer pixels)."""
    h, w = arr.shape[:2]
    out = np.zeros_like(arr)
    for y in range(h):
        ny = y + dy
        if not (0 <= ny < h):
            continue
        dx = row_shifts_x[y]
        if dx == 0:
            out[ny] = arr[y]
        elif dx > 0 and dx < w:
            out[ny, dx:] = arr[y, : w - dx]
        elif dx < 0 and (-dx) < w:
            out[ny, : w + dx] = arr[y, -dx:]
    return out


def _squash_stretch(body: np.ndarray, scale_x: float, scale_y: float) -> np.ndarray:
    """Bottom-anchored nearest-neighbor squash & stretch preserving ground contact."""
    h, w = body.shape[:2]
    opaque = body[..., 3] >= 128
    if not opaque.any():
        return body.copy()
    ys, xs = np.where(opaque)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    crop = Image.fromarray(body[y0:y1, x0:x1], mode="RGBA")
    nw = max(1, min(w, int(round(crop.width * scale_x))))
    nh = max(1, min(h, int(round(crop.height * scale_y))))
    resized = crop.resize((nw, nh), Image.Resampling.NEAREST)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx = (x0 + x1) // 2
    ox = max(0, min(w - nw, cx - nw // 2))
    oy = max(0, min(h - nh, y1 - nh))  # anchored at bottom y1!
    out.paste(resized, (ox, oy))
    return np.asarray(out)


def _scale_shadow(shadow: np.ndarray, factor: float) -> np.ndarray:
    """Shrink ground shadow symmetrically around its center when jumping upward (Z-axis rule)."""
    if not (shadow[..., 3] > 0).any() or abs(factor - 1.0) < 0.05:
        return shadow.copy()
    h, w = shadow.shape[:2]
    ys, xs = np.where(shadow[..., 3] > 0)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    crop = Image.fromarray(shadow[y0:y1, x0:x1], mode="RGBA")
    nw = max(2, int(round(crop.width * factor)))
    nh = max(1, int(round(crop.height * factor)))
    resized = crop.resize((nw, nh), Image.Resampling.NEAREST)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = (x0 + x1) // 2 - nw // 2
    oy = (y0 + y1) // 2 - nh // 2
    out.paste(resized, (max(0, ox), max(0, oy)))
    return np.asarray(out)


def generate_procedural_frames(
    master_img: Image.Image,
    spec: AnimationSpec,
) -> tuple[list[Image.Image], dict[str, Any]]:
    """Synthesize deterministic pixel-perfect animation frames directly from a master sprite (offline)."""
    preset = get_preset(spec.preset)
    motion = _classify_motion(spec.action, spec.brief)
    m_rgba = master_img.convert("RGBA")
    m_arr = np.asarray(m_rgba)
    h, w = m_arr.shape[:2]
    body, shadow = _split_shadow(m_arr, preset.allow_ground_shadow_alpha)

    opaque = body[..., 3] >= 128
    ys, xs = np.where(opaque) if opaque.any() else (np.array([0]), np.array([0]))
    y_top, y_bot = int(ys.min()), int(ys.max())
    x_left, x_right = int(xs.min()), int(xs.max())
    body_h = max(1, y_bot - y_top + 1)
    cx = (x_left + x_right) // 2

    # Choose highlight/accent color from the sprite's palette for FX (never arbitrary muddy colors).
    pal = extract_palette(m_rgba, max_colors=max(4, preset.max_colors), name="proc_pal")
    brightest = pal.colors[-1] if pal.colors else (255, 240, 140)
    warm_accent = (255, 234, 107) if not spec.lock_palette else brightest

    n = max(2, spec.frame_count)
    frames: list[Image.Image] = []
    events: dict[int, str] = {}

    for i in range(n):
        phase = i / n
        f_body = body.copy()
        f_shadow = shadow.copy()

        if motion == "idle":
            # Upper torso breathes down 1px at mid-cycle while feet & shadow stay 100% locked!
            drop = 1 if (0.25 <= phase < 0.75) else 0
            split_y = y_top + int(body_h * 0.68)
            if drop:
                upper = body[:split_y].copy()
                f_body[:split_y] = (0, 0, 0, 0)
                f_body[1 : split_y + 1] = np.where(upper[..., 3:4] >= 128, upper, f_body[1 : split_y + 1])
                # Subtle specular glint pulse on upper-left edge so frame delta stays lively.
                glint_y = min(h - 1, y_top + max(1, body_h // 5))
                glint_x = min(w - 1, x_left + max(1, (x_right - x_left) // 3))
                if f_body[glint_y, glint_x, 3] >= 128:
                    f_body[glint_y, glint_x, :3] = brightest

        elif motion == "walk":
            # Rhythmic 2-step bounce + alternating foot stride + slight forward upper tilt.
            bob = -1 if (i % 2 == 1) else 0
            stride = int(round(math.sin(2.0 * math.pi * phase) * max(1, w // 16)))
            leg_y = y_top + int(body_h * 0.72)
            shifts = [0] * h
            for y in range(h):
                if y >= leg_y:
                    shifts[y] = stride if ((y - leg_y) % 2 == 0) else -stride
                elif y < y_top + body_h // 3:
                    shifts[y] = 1 if stride > 0 else (-1 if stride < 0 else 0)
            f_body = _shift_rows(body, shifts, dy=bob)
            if i == 0:
                events[i] = "footstep_left"
            elif i == n // 2:
                events[i] = "footstep_right"

        elif motion == "jump":
            # Parabolic Z arc: anticipation -> rise -> apex (shadow shrinks) -> descend -> landing squash!
            if i == 0:
                f_body = _squash_stretch(body, 1.08, 0.90)  # anticipation crouch
            elif i == n - 1:
                f_body = _squash_stretch(body, 1.12, 0.86)  # landing squash (Physics Rule 3.3)
                events[i] = "land"
            else:
                t = (i - 0.5) / max(1, n - 2)
                arc = math.sin(math.pi * min(1.0, max(0.0, t)))
                lift = int(round(arc * max(2, min(h // 4, body_h // 2))))
                stretch_y = 1.06 if arc > 0.6 else 1.0
                stretch_x = 0.95 if arc > 0.6 else 1.0
                stretched = _squash_stretch(body, stretch_x, stretch_y)
                f_body = _shift_rows(stretched, [0] * h, dy=-lift)
                f_shadow = _scale_shadow(shadow, max(0.45, 1.0 - 0.45 * arc))
                if i == 1:
                    events[i] = "takeoff"

        elif motion == "attack":
            # Anticipation lean back -> Smear Arc slash at 1/3 cycle (Physics Rule 3.4) -> recovery
            hit_frame = max(1, n // 3)
            if i < hit_frame:
                f_body = _shift_rows(body, [-1 if y < y_bot - 2 else 0 for y in range(h)], dy=0)
            elif i == hit_frame:
                f_body = _shift_rows(body, [2 if y < y_bot - 2 else 0 for y in range(h)], dy=0)
                # Draw crisp 1-2px slash arc on right edge
                slash_img = Image.fromarray(f_body, mode="RGBA")
                draw = ImageDraw.Draw(slash_img)
                ax0 = min(w - 3, x_right - 1)
                ay0 = max(1, y_top)
                ax1 = min(w - 1, x_right + max(2, w // 6))
                ay1 = min(h - 2, y_bot)
                if ax1 > ax0 and ay1 > ay0:
                    draw.arc([ax0 - 4, ay0, ax1, ay1], start=-70, end=65, fill=(*warm_accent, 255), width=2)
                f_body = np.asarray(slash_img)
                events[i] = "hit"
            elif i == hit_frame + 1:
                f_body = _shift_rows(body, [1 if y < y_bot - 2 else 0 for y in range(h)], dy=0)
            else:
                f_body = body.copy()

        elif motion == "sway":
            # Progressive wind wave traveling upward/rightward while root stays anchored!
            shifts = [0] * h
            for y in range(h):
                if y < y_bot - max(1, body_h // 5):
                    height_ratio = (y_bot - y) / body_h
                    wave = math.sin(2.0 * math.pi * phase - height_ratio * 2.2)
                    shifts[y] = int(round(wave * max(1.0, height_ratio * 1.6)))
            f_body = _shift_rows(body, shifts, dy=0)

        elif motion == "fire":
            # Flickering upper dynamic zone + 1-2px rising ember particles (Physics Rule 3.5)
            shifts = [0] * h
            top_zone = y_top + int(body_h * 0.55)
            for y in range(y_top, min(h, top_zone)):
                wave = math.sin(2.0 * math.pi * phase + (y - y_top) * 0.9)
                shifts[y] = int(round(wave * 1.2))
            f_body = _shift_rows(body, shifts, dy=0)
            # Emit 2 rising ember pixels above top silhouette
            for p_idx in range(2):
                prog = (phase + p_idx * 0.5) % 1.0
                ey = int(round(y_top - 1 - prog * max(2, min(6, y_top))))
                ex = cx + int(round(math.sin((prog + p_idx) * 6.28) * max(1, (x_right - x_left) // 4)))
                if 0 <= ey < h and 0 <= ex < w and f_body[ey, ex, 3] == 0:
                    f_body[ey, ex] = (*warm_accent, 255)

        elif motion == "hurt":
            # Knockback recoil + hit flash
            dx = -2 if i == 0 else (-1 if i == 1 else 0)
            f_body = _shift_rows(body, [dx] * h, dy=0)
            if i == 0:
                mask = f_body[..., 3] >= 128
                f_body[mask, :3] = brightest
                events[i] = "hurt_flash"

        elif motion == "open":
            # Progressive lid/top lift revealing warm bright glow inside!
            prog = i / max(1, n - 1)
            lid_y = y_top + max(2, int(body_h * 0.42))
            lift = int(round(prog * max(2, min(y_top, body_h // 4))))
            f_body = body.copy()
            if lift > 0:
                lid = body[y_top:lid_y].copy()
                f_body[y_top:lid_y] = (0, 0, 0, 0)
                ny0 = max(0, y_top - lift)
                ny1 = ny0 + lid.shape[0]
                f_body[ny0:ny1] = lid
                # Fill dark interior + warm treasure glint between lid and base
                gap_y0 = min(h - 1, ny1)
                gap_y1 = min(h, lid_y)
                gx0 = x_left + max(1, (x_right - x_left) // 5)
                gx1 = max(gx0 + 1, x_right - max(1, (x_right - x_left) // 5))
                if gap_y1 > gap_y0:
                    f_body[gap_y0:gap_y1, gx0:gx1] = (20, 13, 24, 255)
                    if prog >= 0.5:
                        mid_x = (gx0 + gx1) // 2
                        f_body[gap_y0, max(0, mid_x - 1) : min(w, mid_x + 2)] = (*warm_accent, 255)
            if i == n - 1:
                events[i] = "opened"

        merged = _merge_shadow(f_body, f_shadow)
        frame_img = Image.fromarray(merged, mode="RGBA")
        if spec.lock_palette and motion not in ("fire", "attack", "open"):
            frame_img, _ = remap_image_to_palette(frame_img, pal, policy="strict")
        frames.append(frame_img)

    frames = lock_static_zone(
        m_rgba,
        frames,
        bottom_rows=spec.lock_static_bottom_rows,
        preserve_ground_shadow_alpha=preset.allow_ground_shadow_alpha,
    )
    return frames, {
        "status": "ok",
        "track": "procedural",
        "motion_model": motion,
        "route": "offline:procedural",
        "model": f"procedural-{motion}-v1",
        "estimate_usd": 0.0,
        "events": events,
    }
