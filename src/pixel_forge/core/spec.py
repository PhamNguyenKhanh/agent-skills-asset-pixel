"""Typed specifications for Pixel Forge assets, animations, and exports."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


def parse_size(size_str: str) -> tuple[int, int]:
    """Parse 'WxH' or single integer 'N' into (width, height)."""
    cleaned = size_str.strip().lower().replace("×", "x")
    if cleaned.isdigit():
        n = int(cleaned)
        if n <= 0 or n > 2048:
            raise ValueError(f"Size out of supported range (1..2048): {size_str!r}")
        return (n, n)
    match = re.fullmatch(r"(\d+)x(\d+)", cleaned)
    if not match:
        raise ValueError(f"Invalid size {size_str!r}. Expected 'WxH' (e.g. 32x32) or 'N' (e.g. 32).")
    w, h = int(match.group(1)), int(match.group(2))
    if not (1 <= w <= 2048 and 1 <= h <= 2048):
        raise ValueError(f"Size out of supported range (1..2048): {size_str!r}")
    return (w, h)


def slugify(text: str) -> str:
    """Convert arbitrary text to a safe lowercase asset identifier."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug[:64] or "asset"


@dataclass
class SpatialMeta:
    """Game-engine spatial anchor, ground footprint, and collision metadata (in pixel units)."""

    perspective: str = "top_down_3_4"
    pivot_x: int = 16
    pivot_y: int = 28
    ground_footprint: tuple[int, int, int, int] | None = None  # x, y, w, h
    collision_box: tuple[int, int, int, int] | None = None  # x, y, w, h
    render_layer: str = "Y-Sort"

    @classmethod
    def default_for(cls, width: int, height: int, perspective: str = "top_down_3_4") -> SpatialMeta:
        # Pixel-aligned pivot to prevent 0.5px misalignment in Unity PixelPerfectCamera.
        pivot_x = width // 2
        if perspective in ("top_down_3_4", "side_view", "isometric"):
            pivot_y = max(0, height - max(1, height // 12))
            fp_x = int(width * 0.2)
            fp_w = max(2, int(width * 0.6))
            fp_h = max(2, int(height * 0.14))
            fp_y = max(0, height - fp_h - 1)
            col_h = max(2, int(height * 0.25))
            col_y = max(0, height - col_h - 2)
            return cls(
                perspective=perspective,
                pivot_x=pivot_x,
                pivot_y=pivot_y,
                ground_footprint=(fp_x, fp_y, fp_w, fp_h),
                collision_box=(fp_x, col_y, fp_w, col_h),
                render_layer="Y-Sort" if perspective != "side_view" else "Default",
            )
        return cls(
            perspective=perspective,
            pivot_x=pivot_x,
            pivot_y=height // 2,
            ground_footprint=None,
            collision_box=(0, 0, width, height),
            render_layer="UI",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "perspective": self.perspective,
            "pivot": {"x": self.pivot_x, "y": self.pivot_y},
            "ground_footprint": (
                {
                    "x": self.ground_footprint[0],
                    "y": self.ground_footprint[1],
                    "width": self.ground_footprint[2],
                    "height": self.ground_footprint[3],
                }
                if self.ground_footprint
                else None
            ),
            "collision_box": (
                {
                    "x": self.collision_box[0],
                    "y": self.collision_box[1],
                    "width": self.collision_box[2],
                    "height": self.collision_box[3],
                }
                if self.collision_box
                else None
            ),
            "render_layer": self.render_layer,
        }


@dataclass
class FrameMeta:
    """Metadata for a single frame in an asset or animation."""

    index: int
    duration_ms: int = 125
    name: str = ""
    event: str | None = None  # e.g. "hit", "footstep_left", "spawn"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "index": self.index,
            "name": self.name or f"frame_{self.index:03d}",
            "duration_ms": self.duration_ms,
        }
        if self.event:
            d["event"] = self.event
        return d


@dataclass
class AssetSpec:
    """Complete technical specification for generating or processing a 2D pixel asset."""

    asset_id: str
    brief: str
    width: int = 32
    height: int = 32
    preset: str = "topdown-34-stardew"
    mode: str = "auto"  # auto | ai-pixel-look | hibit | direct
    palette: str | None = None
    palette_policy: str = "strict"  # strict | guided | none
    max_colors: int | None = None
    outline: str | None = None  # auto | selective | dark | none | #rrggbb
    fit_mode: str = "contain"  # contain | stretch
    align: str = "auto"  # auto | bottom | center
    key_color: str = "auto"  # auto | magenta | green | blue | #rrggbb
    add_ground_shadow: bool = False
    spatial: SpatialMeta | None = None

    def resolved_spatial(self, perspective: str) -> SpatialMeta:
        return self.spatial or SpatialMeta.default_for(self.width, self.height, perspective)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnimationSpec:
    """Technical specification for generating an animation from an asset image + description."""

    asset_id: str
    action: str = "idle"
    brief: str = ""
    frame_count: int = 6
    fps: int = 8
    playback: str = "loop"  # loop | once | ping_pong
    track: str = "auto"  # auto | sheet | video | procedural
    preset: str = "topdown-34-stardew"
    lock_palette: bool = True
    lock_static_bottom_rows: int = 0  # >0 keeps bottom rows pixel-identical (e.g. pedestal / ground shadow)
    mirror_direction: str | None = None  # horizontal | vertical | None
    allow_asymmetric_mirror: bool = False
    frames: list[FrameMeta] = field(default_factory=list)

    @property
    def frame_duration_ms(self) -> int:
        return max(10, round(1000 / max(1, self.fps)))

    def default_frames(self) -> list[FrameMeta]:
        if self.frames:
            return self.frames
        dur = self.frame_duration_ms
        return [
            FrameMeta(index=i, duration_ms=dur, name=f"{self.asset_id}_{self.action}_{i:02d}")
            for i in range(self.frame_count)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "action": self.action,
            "brief": self.brief,
            "frame_count": self.frame_count,
            "fps": self.fps,
            "frame_duration_ms": self.frame_duration_ms,
            "playback": self.playback,
            "track": self.track,
            "preset": self.preset,
            "lock_palette": self.lock_palette,
            "lock_static_bottom_rows": self.lock_static_bottom_rows,
            "frames": [f.to_dict() for f in self.default_frames()],
        }


@dataclass
class ExportSpec:
    """Output formats and engine target settings."""

    formats: tuple[str, ...] = ("png", "gif", "aseprite", "unity")
    pixels_per_unit: int = 32
    preview_scale: int = 4
    sheet_columns: int | None = None
    sheet_padding: int = 0
    emit_lua: bool = False
    emit_html_preview: bool = True
    layer_names: tuple[str, ...] = ("Main",)

    @classmethod
    def from_csv(cls, formats_csv: str, **kwargs: Any) -> ExportSpec:
        valid = {"png", "gif", "aseprite", "unity", "lua", "html"}
        parts = tuple(p.strip().lower() for p in formats_csv.split(",") if p.strip())
        invalid = [p for p in parts if p not in valid]
        if invalid:
            raise ValueError(f"Unsupported export formats: {', '.join(invalid)}. Valid: {', '.join(sorted(valid))}")
        emit_lua = kwargs.pop("emit_lua", False) or ("lua" in parts)
        emit_html = kwargs.pop("emit_html_preview", True) or ("html" in parts)
        core_formats = tuple(p for p in parts if p in ("png", "gif", "aseprite", "unity"))
        return cls(formats=core_formats, emit_lua=emit_lua, emit_html_preview=emit_html, **kwargs)
