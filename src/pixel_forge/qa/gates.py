"""Tier 1 Universal Hard Gates & Tier 2 Style/Perspective QA checks."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
from PIL import Image

from pixel_forge.core.presets import StylePreset, get_preset
from pixel_forge.pixelize.matte import DECLARED_KEYS, key_dominance


def check_binary_alpha(img: Image.Image, *, allowed_shadow_alpha: int | None = None) -> dict[str, Any]:
    arr = np.asarray(img.convert("RGBA"))
    a = arr[..., 3]
    semi = (a > 0) & (a < 255)
    if allowed_shadow_alpha is not None:
        semi = semi & (a != allowed_shadow_alpha)
    bad = int(semi.sum())
    return {"semi_transparent_pixels": bad, "allowed_shadow_alpha": allowed_shadow_alpha, "passed": bad == 0}


def check_grid_alignment(img: Image.Image, grid_size: int) -> dict[str, Any]:
    w, h = img.size
    gs = max(1, int(grid_size))
    aligned = (w % gs == 0) and (h % gs == 0)
    return {"width": w, "height": h, "grid_size": gs, "passed": aligned}


def check_palette_compliance(
    img: Image.Image,
    max_colors: int,
    *,
    forbid_pure_black: bool = False,
) -> dict[str, Any]:
    arr = np.asarray(img.convert("RGBA"))
    vis = arr[arr[..., 3] >= 128][:, :3]
    if len(vis) == 0:
        return {"unique_colors": 0, "max_allowed": max_colors, "pure_black_pixels": 0, "passed": True}
    unique = np.unique(vis, axis=0)
    pure_black = int(((vis[:, 0] == 0) & (vis[:, 1] == 0) & (vis[:, 2] == 0)).sum())
    count = int(len(unique))
    passed = (count <= max_colors) and (not forbid_pure_black or pure_black == 0)
    return {
        "unique_colors": count,
        "max_allowed": max_colors,
        "pure_black_pixels": pure_black,
        "forbid_pure_black": forbid_pure_black,
        "passed": passed,
    }


def check_orphan_pixels(img: Image.Image) -> dict[str, Any]:
    arr = np.asarray(img.convert("RGBA"))
    opaque = arr[..., 3] >= 128
    if not opaque.any():
        return {"orphan_pixels": 0, "passed": True}
    p = np.pad(opaque.astype(np.uint8), 1, mode="constant", constant_values=0)
    nbrs = (
        p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:]
        + p[1:-1, :-2] + p[1:-1, 2:]
        + p[2:, :-2] + p[2:, 1:-1] + p[2:, 2:]
    )
    orphans = int((opaque & (nbrs == 0)).sum())
    return {"orphan_pixels": orphans, "passed": orphans == 0}


def check_key_fringe(img: Image.Image) -> dict[str, Any]:
    """Detect magenta or green chroma-key bleed along the outer opaque silhouette ring."""
    arr = np.asarray(img.convert("RGBA"))
    opaque = arr[..., 3] >= 128
    if not opaque.any():
        return {"fringe_pixels": 0, "fringe_ratio": 0.0, "passed": True}
    p = np.pad(opaque, 1, mode="constant", constant_values=False)
    eroded = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    ring = opaque & (~eroded)
    if not ring.any():
        return {"fringe_pixels": 0, "fringe_ratio": 0.0, "passed": True}
    ring_rgb = arr[ring][:, :3]
    mag_dom = key_dominance(ring_rgb, DECLARED_KEYS["magenta"])
    fringe_count = int((mag_dom >= 85.0).sum())
    ratio = round(fringe_count / max(1, int(ring.sum())), 4)
    return {"fringe_pixels": fringe_count, "fringe_ratio": ratio, "passed": ratio <= 0.02}


def check_banding(img: Image.Image) -> dict[str, Any]:
    """Heuristic banding detector: counts long identical parallel color transitions along adjacent rows/cols."""
    arr = np.asarray(img.convert("RGBA"))
    opaque = arr[..., 3] >= 128
    h, w = opaque.shape
    if h < 4 or w < 4:
        return {"banding_events": 0, "passed": True}
    rgb = arr[..., :3].astype(np.int16)
    # Horizontal transition mask where pixel differs from left neighbor inside opaque area
    h_change = np.any(rgb[:, 1:] != rgb[:, :-1], axis=-1) & opaque[:, 1:] & opaque[:, :-1]
    # Parallel staircase: two adjacent columns both transitioning on >= 4 consecutive rows identically
    events = 0
    for c in range(w - 2):
        both = h_change[:, c] & h_change[:, c + 1]
        run = 0
        for v in both.tolist():
            if v:
                run += 1
                if run == 4:
                    events += 1
            else:
                run = 0
    return {"banding_events": events, "passed": events <= 2}


def check_jaggies(img: Image.Image) -> dict[str, Any]:
    """Detect isolated protruding 90-degree L-corners on outer silhouette edges."""
    arr = np.asarray(img.convert("RGBA"))
    opaque = arr[..., 3] >= 128
    h, w = opaque.shape
    if h < 5 or w < 5:
        return {"jag_corners": 0, "passed": True}
    p = np.pad(opaque, 1, mode="constant", constant_values=False)
    up, dn, lt, rt = p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]
    ul, ur, dl, dr = p[:-2, :-2], p[:-2, 2:], p[2:, :-2], p[2:, 2:]
    # Single pixel sticking out of a diagonal step (2 orthogonal neighbors, opposite diagonal empty, adjacent outer empty)
    c1 = opaque & up & lt & (~dn) & (~rt) & (~dr) & (~ur) & (~dl)
    c2 = opaque & up & rt & (~dn) & (~lt) & (~dl) & (~ul) & (~dr)
    c3 = opaque & dn & lt & (~up) & (~rt) & (~ur) & (~ul) & (~dr)
    c4 = opaque & dn & rt & (~up) & (~lt) & (~ul) & (~ur) & (~dl)
    jags = int((c1 | c2 | c3 | c4).sum())
    return {"jag_corners": jags, "passed": jags <= max(4, (w + h) // 16)}


def check_ground_alignment(img: Image.Image) -> dict[str, Any]:
    """Check that top-down / grounded sprites sit close to the bottom edge (not floating mid-canvas)."""
    arr = np.asarray(img.convert("RGBA"))
    h = arr.shape[0]
    vis = arr[..., 3] > 0
    if not vis.any():
        return {"bottom_margin_px": h, "passed": False}
    ys = np.where(vis)[0]
    margin = int(h - 1 - ys.max())
    max_allowed = max(2, int(round(h * 0.18)))
    return {"bottom_margin_px": margin, "max_allowed_margin_px": max_allowed, "passed": margin <= max_allowed}


def audit_tile_seams(img: Image.Image, *, max_mean_diff: float = 28.0) -> dict[str, Any]:
    """Measure numeric seam continuity across X (left-right) and Y (top-bottom) tile edges."""
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32)
    x_diff = float(np.abs(arr[:, 0, :3] - arr[:, -1, :3]).mean())
    y_diff = float(np.abs(arr[0, :, :3] - arr[-1, :, :3]).mean())
    return {
        "x_seam_diff": round(x_diff, 3),
        "y_seam_diff": round(y_diff, 3),
        "tileable_x": x_diff <= max_mean_diff,
        "tileable_y": y_diff <= max_mean_diff,
        "passed": x_diff <= max_mean_diff and y_diff <= max_mean_diff,
    }


def audit_image(
    img: Image.Image,
    *,
    preset_name: str = "freestyle",
    grid_size: int | None = None,
    max_colors: int | None = None,
    check_seams: bool = False,
) -> dict[str, Any]:
    """Run Tier 1 Universal Hard Gates + Tier 2 Style/Perspective Gates on a single sprite."""
    preset: StylePreset = get_preset(preset_name)
    gs = grid_size if grid_size is not None else preset.grid_size
    mc = max_colors if max_colors is not None else preset.max_colors

    tier1 = {
        "binary_alpha": check_binary_alpha(img, allowed_shadow_alpha=preset.allow_ground_shadow_alpha),
        "grid_alignment": check_grid_alignment(img, gs),
        "palette": check_palette_compliance(img, mc, forbid_pure_black=preset.forbid_pure_black_outline),
        "orphan_pixels": check_orphan_pixels(img),
        "key_fringe": check_key_fringe(img),
    }

    tier2: dict[str, Any] = {}
    if preset.enforce_banding_check:
        tier2["banding"] = check_banding(img)
    if preset.enforce_jaggies_check:
        tier2["jaggies"] = check_jaggies(img)
    if preset.enforce_ground_alignment:
        tier2["ground_alignment"] = check_ground_alignment(img)
    if check_seams:
        tier2["tile_seams"] = audit_tile_seams(img)

    hard_pass = all(v["passed"] for v in tier1.values())
    soft_warnings = [name for name, res in tier2.items() if not res["passed"]]
    status = "pass" if (hard_pass and not soft_warnings) else ("warn" if hard_pass else "fail")

    return {
        "status": status,
        "preset": preset.name,
        "size": list(img.size),
        "tier1_hard": tier1,
        "tier2_style": tier2,
        "hard_passed": hard_pass,
        "warnings": soft_warnings,
    }


def audit_animation(
    frames: Sequence[Image.Image],
    *,
    preset_name: str = "freestyle",
    grid_size: int | None = None,
    max_colors: int | None = None,
    static_bottom_rows: int = 0,
) -> dict[str, Any]:
    """Run 2-tier QA on every frame plus inter-frame motion delta and static-zone anchor checks."""
    preset = get_preset(preset_name)
    if not frames:
        return {"status": "fail", "error": "No frames provided", "hard_passed": False}

    per_frame = [
        audit_image(f, preset_name=preset_name, grid_size=grid_size, max_colors=max_colors)
        for f in frames
    ]
    sizes = {f.size for f in frames}
    uniform_size = len(sizes) == 1

    # Compute pixel change ratio between consecutive frames relative to foreground area
    deltas: list[float] = []
    static_drift = 0
    arrs = [np.asarray(f.convert("RGBA")) for f in frames]
    for i in range(len(arrs) - 1):
        a, b = arrs[i], arrs[i + 1]
        if a.shape != b.shape:
            continue
        union = (a[..., 3] > 0) | (b[..., 3] > 0)
        denom = max(1, int(union.sum()))
        changed = int(np.any(a != b, axis=-1).sum())
        deltas.append(round(changed / denom, 4))
        if static_bottom_rows > 0:
            rows = min(a.shape[0], static_bottom_rows)
            static_drift += int(np.any(a[-rows:] != b[-rows:], axis=-1).sum())

    mean_delta = round(sum(deltas) / len(deltas), 4) if deltas else 0.0
    motion_ok = (len(frames) == 1) or (mean_delta >= preset.min_dynamic_delta_ratio)
    static_ok = static_drift == 0

    all_hard_pass = uniform_size and static_ok and all(r["hard_passed"] for r in per_frame)
    warnings: list[str] = []
    if not motion_ok:
        warnings.append(f"low_motion_delta ({mean_delta:.4f} < {preset.min_dynamic_delta_ratio:.4f})")
    for idx, r in enumerate(per_frame):
        for w in r["warnings"]:
            warnings.append(f"frame_{idx:02d}:{w}")

    status = "pass" if (all_hard_pass and not warnings) else ("warn" if all_hard_pass else "fail")
    return {
        "status": status,
        "preset": preset.name,
        "frame_count": len(frames),
        "uniform_size": uniform_size,
        "frame_deltas": deltas,
        "mean_delta_ratio": mean_delta,
        "motion_passed": motion_ok,
        "static_zone_drift_pixels": static_drift,
        "static_zone_passed": static_ok,
        "hard_passed": all_hard_pass,
        "warnings": warnings,
        "frames": per_frame,
    }
