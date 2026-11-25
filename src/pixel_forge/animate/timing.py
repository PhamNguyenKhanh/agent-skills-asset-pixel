"""Animation registration, static-zone locking, gait loop selection, and one-shot retiming."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from PIL import Image


def _opaque_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    arr = np.asarray(img.convert("RGBA"))
    mask = arr[..., 3] >= 128
    if not mask.any():
        return None
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def register_frames_to_anchor(
    master: Image.Image,
    frames: Sequence[Image.Image],
    *,
    lock_bottom: bool = True,
) -> list[Image.Image]:
    """Align every frame's bottom footline and horizontal center to the master's anchor."""
    w, h = master.size
    m_box = _opaque_bbox(master)
    if m_box is None:
        return [f.convert("RGBA").resize((w, h), Image.Resampling.NEAREST) for f in frames]
    m_cx = (m_box[0] + m_box[2]) // 2
    m_bot = m_box[3]

    out: list[Image.Image] = []
    for frame in frames:
        rgba = frame.convert("RGBA")
        if rgba.size != (w, h):
            rgba = rgba.resize((w, h), Image.Resampling.NEAREST)
        f_box = _opaque_bbox(rgba)
        if f_box is None:
            out.append(rgba)
            continue
        f_cx = (f_box[0] + f_box[2]) // 2
        f_bot = f_box[3]
        dx = m_cx - f_cx
        dy = (m_bot - f_bot) if lock_bottom else 0
        if dx == 0 and dy == 0:
            out.append(rgba)
            continue
        shifted = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        shifted.paste(rgba, (dx, dy))
        out.append(shifted)
    return out


def lock_static_zone(
    master: Image.Image,
    frames: Sequence[Image.Image],
    *,
    bottom_rows: int = 0,
    preserve_ground_shadow_alpha: int | None = None,
) -> list[Image.Image]:
    """Keep designated static bottom rows (and optional ground shadow 'S') pixel-identical to master."""
    if bottom_rows <= 0 and preserve_ground_shadow_alpha is None:
        return [f.convert("RGBA") for f in frames]

    m_arr = np.asarray(master.convert("RGBA"))
    h, w = m_arr.shape[:2]
    shadow_mask = (
        (m_arr[..., 3] == preserve_ground_shadow_alpha)
        if preserve_ground_shadow_alpha is not None
        else np.zeros((h, w), dtype=bool)
    )

    locked: list[Image.Image] = []
    for frame in frames:
        f_arr = np.asarray(frame.convert("RGBA")).copy()
        if bottom_rows > 0:
            rows = min(h, bottom_rows)
            f_arr[h - rows :, :, :] = m_arr[h - rows :, :, :]
        if shadow_mask.any():
            # Restore static ground shadow wherever the animated sprite itself isn't opaque on top.
            restore = shadow_mask & (f_arr[..., 3] < 128)
            f_arr[restore] = m_arr[restore]
        locked.append(Image.fromarray(f_arr, mode="RGBA"))
    return locked


def _frame_distance(a: Image.Image, b: Image.Image) -> float:
    aa = np.asarray(a.convert("RGBA"), dtype=np.float32)
    bb = np.asarray(b.convert("RGBA"), dtype=np.float32)
    return float(np.abs(aa - bb).mean())


def find_best_loop(frames: Sequence[Image.Image], target_count: int) -> tuple[list[Image.Image], dict]:
    """Select `target_count` evenly spaced frames from the cleanest closed loop window in a clip."""
    n = len(frames)
    if n == 0:
        return [], {"window": [0, 0], "seam_error": 0.0}
    if n <= target_count:
        return list(frames), {"window": [0, n - 1], "seam_error": round(_frame_distance(frames[0], frames[-1]), 3)}

    min_len = max(target_count, n // 3)
    best_pair = (0, n - 1)
    best_score = float("inf")

    for start in range(0, n - min_len + 1):
        for end in range(start + min_len - 1, n):
            seam = _frame_distance(frames[start], frames[end])
            # Encourage non-trivial motion inside the loop (avoid picking a completely frozen span).
            mid = (start + end) // 2
            motion = _frame_distance(frames[start], frames[mid])
            score = seam - min(motion, 15.0) * 0.15
            if score < best_score:
                best_score = score
                best_pair = (start, end)

    s_idx, e_idx = best_pair
    # Sample `target_count` frames across [s_idx, e_idx) so the wrap back to s_idx closes smoothly.
    indices = np.linspace(s_idx, max(s_idx, e_idx - 1), target_count, dtype=np.int32).tolist()
    picked = [frames[i] for i in indices]
    return picked, {
        "window": [s_idx, e_idx],
        "picked_indices": indices,
        "seam_error": round(_frame_distance(frames[s_idx], frames[e_idx]), 3),
    }


def retime_oneshot(frames: Sequence[Image.Image], target_count: int) -> tuple[list[Image.Image], dict]:
    """Trim frozen head/tail holds and sample `target_count` frames at equal cumulative motion steps."""
    n = len(frames)
    if n == 0:
        return [], {"active_span": [0, 0], "picked_indices": []}
    if n <= target_count:
        return list(frames), {"active_span": [0, n - 1], "picked_indices": list(range(n))}

    diffs = [_frame_distance(frames[i], frames[i + 1]) for i in range(n - 1)]
    max_diff = max(diffs) if diffs else 0.0
    thresh = max(0.25, max_diff * 0.08)

    active = [i for i, d in enumerate(diffs) if d >= thresh]
    start = active[0] if active else 0
    end = min(n - 1, (active[-1] + 1) if active else (n - 1))
    span_len = end - start + 1
    if span_len <= target_count:
        indices = list(range(start, end + 1))
        return [frames[i] for i in indices], {"active_span": [start, end], "picked_indices": indices}

    # Cumulative motion arc-length sampling (pins fastest peak automatically).
    cum = [0.0]
    for i in range(start, end):
        cum.append(cum[-1] + max(0.05, diffs[i]))
    total_motion = cum[-1]
    targets = np.linspace(0.0, total_motion, target_count)
    indices: list[int] = []
    for t in targets:
        best_j = min(range(len(cum)), key=lambda j: abs(cum[j] - t))
        indices.append(start + best_j)

    # Identify peak velocity frame as candidate hit/apex event.
    peak_offset = int(np.argmax(diffs[start:end])) if end > start else 0
    peak_frame = start + peak_offset
    peak_out_idx = min(range(len(indices)), key=lambda k: abs(indices[k] - peak_frame))

    return [frames[i] for i in indices], {
        "active_span": [start, end],
        "picked_indices": indices,
        "peak_frame_index": peak_out_idx,
    }
