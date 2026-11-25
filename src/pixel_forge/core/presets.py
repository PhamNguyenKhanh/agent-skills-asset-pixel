"""Two-tier Style & Perspective Presets reconciling Art Director rules with multi-genre 2D workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StylePreset:
    """Configuration profile controlling prompt direction, post-processing defaults, and Tier-2 QA rules."""

    name: str
    description: str
    perspective: str  # top_down_3_4 | side_view | isometric | front_icon
    default_mode: str  # ai-pixel-look | hibit | direct
    default_palette: str | None  # palette name or None (learned from source)
    max_colors: int
    grid_size: int
    outline_mode: str  # auto | selective | dark | none | #rrggbb
    forbid_pure_black_outline: bool
    allow_ground_shadow_alpha: int | None  # e.g. 130 for Stardew/Top-Down 'S' shadow, None for strict binary alpha
    enforce_ground_alignment: bool
    enforce_banding_check: bool
    enforce_jaggies_check: bool
    min_dynamic_delta_ratio: float  # minimum pixel change ratio between animated frames
    prompt_style_clause: str
    prompt_lighting_clause: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PRESETS: dict[str, StylePreset] = {
    "topdown-34-stardew": StylePreset(
        name="topdown-34-stardew",
        description="Warm cozy Top-Down 3/4 pixel art (Stardew Valley style): tinted dark outlines, no pure #000000 outline, soft ground contact shadow.",
        perspective="top_down_3_4",
        default_mode="ai-pixel-look",
        default_palette="master_topdown",
        max_colors=16,
        grid_size=16,
        outline_mode="selective",
        forbid_pure_black_outline=True,
        allow_ground_shadow_alpha=130,
        enforce_ground_alignment=True,
        enforce_banding_check=True,
        enforce_jaggies_check=True,
        min_dynamic_delta_ratio=0.04,
        prompt_style_clause=(
            "cozy top-down 3/4 RPG pixel art sprite, warm hue-shifted colors, clean pixel clusters, "
            "soft tinted dark material outlines (never pure black #000000), crisp hard edges, no anti-aliasing, "
            "no dithering noise, grounded bottom-aligned silhouette"
        ),
        prompt_lighting_clause="top-left 45-degree warm sunlight (10:30), cool purple-tinted shadows, subtle rim highlight on top-left edges",
    ),
    "topdown-34-terraria": StylePreset(
        name="topdown-34-terraria",
        description="High-contrast chunky pixel art (Terraria style): bold dark contours, tactile surface texture, high readability.",
        perspective="top_down_3_4",
        default_mode="ai-pixel-look",
        default_palette="db32",
        max_colors=16,
        grid_size=16,
        outline_mode="#140d18",
        forbid_pure_black_outline=False,
        allow_ground_shadow_alpha=130,
        enforce_ground_alignment=True,
        enforce_banding_check=True,
        enforce_jaggies_check=True,
        min_dynamic_delta_ratio=0.05,
        prompt_style_clause=(
            "bold chunky retro RPG pixel art sprite, high contrast shading, thick dark outline, "
            "crisp tactile material clusters, zero anti-aliasing, zero blur"
        ),
        prompt_lighting_clause="strong top-left directional light, deep dark crevices, crisp specular accents on metal",
    ),
    "freestyle": StylePreset(
        name="freestyle",
        description="Modern indie pixel art with mandatory hue-shifting, clean line art, flexible perspective and 24-color budget.",
        perspective="front_icon",
        default_mode="ai-pixel-look",
        default_palette=None,
        max_colors=24,
        grid_size=8,
        outline_mode="selective",
        forbid_pure_black_outline=False,
        allow_ground_shadow_alpha=None,
        enforce_ground_alignment=False,
        enforce_banding_check=True,
        enforce_jaggies_check=True,
        min_dynamic_delta_ratio=0.03,
        prompt_style_clause=(
            "modern indie 2D pixel art sprite, rich hue-shifted color ramps (warm highlights, cool shadows), "
            "clean pixel clusters, zero anti-aliasing, zero soft blur"
        ),
        prompt_lighting_clause="top-left key light with warm highlights and cool purple-blue ambient shadows",
    ),
    "side-view-hibit": StylePreset(
        name="side-view-hibit",
        description="Hi-bit studio look (agent-sprite-forge): flat lineless cel art downscaled via 8x8 majority vote with learned 16-color palette and auto hue-matched outline.",
        perspective="side_view",
        default_mode="hibit",
        default_palette=None,
        max_colors=20,
        grid_size=8,
        outline_mode="auto",
        forbid_pure_black_outline=True,
        allow_ground_shadow_alpha=None,
        enforce_ground_alignment=True,
        enforce_banding_check=False,
        enforce_jaggies_check=False,
        min_dynamic_delta_ratio=0.03,
        prompt_style_clause=(
            "clean flat lineless 2D cel-shaded game character illustration, side view facing right, "
            "at most 3 flat color tones per material, no outlines, no gradients, no texture noise, sharp geometric shapes"
        ),
        prompt_lighting_clause="clean directional studio light from upper-left, crisp flat shadow shapes",
    ),
    "side-view-pixel-look": StylePreset(
        name="side-view-pixel-look",
        description="Classic side-view pixel sprite with lattice grid recovery, binary alpha, and up to 48 learned colors.",
        perspective="side_view",
        default_mode="ai-pixel-look",
        default_palette=None,
        max_colors=48,
        grid_size=1,
        outline_mode="dark",
        forbid_pure_black_outline=False,
        allow_ground_shadow_alpha=None,
        enforce_ground_alignment=True,
        enforce_banding_check=False,
        enforce_jaggies_check=False,
        min_dynamic_delta_ratio=0.02,
        prompt_style_clause=(
            "classic 16-bit side-view pixel art character sprite facing right, clear silhouette, "
            "flat color blocks, crisp closed outline, zero soft edges"
        ),
        prompt_lighting_clause="upper-left key light, clear readable silhouette",
    ),
    "retro-pico8": StylePreset(
        name="retro-pico8",
        description="PICO-8 fantasy console strict 16-color palette, bold readable micro-sprites (8x8/16x16/32x32).",
        perspective="front_icon",
        default_mode="ai-pixel-look",
        default_palette="pico-8",
        max_colors=16,
        grid_size=8,
        outline_mode="#1d2b53",
        forbid_pure_black_outline=False,
        allow_ground_shadow_alpha=None,
        enforce_ground_alignment=False,
        enforce_banding_check=True,
        enforce_jaggies_check=True,
        min_dynamic_delta_ratio=0.04,
        prompt_style_clause="vibrant PICO-8 16-color fantasy console pixel art sprite, chunky readable silhouette, flat colors",
        prompt_lighting_clause="simple high-contrast top-left lighting",
    ),
    "retro-gameboy": StylePreset(
        name="retro-gameboy",
        description="Game Boy DMG-01 strict 4-color monochrome green palette.",
        perspective="front_icon",
        default_mode="ai-pixel-look",
        default_palette="gameboy",
        max_colors=4,
        grid_size=8,
        outline_mode="#0f380f",
        forbid_pure_black_outline=False,
        allow_ground_shadow_alpha=None,
        enforce_ground_alignment=False,
        enforce_banding_check=False,
        enforce_jaggies_check=True,
        min_dynamic_delta_ratio=0.04,
        prompt_style_clause="classic Game Boy DMG-01 4-shade green pixel art sprite, bold iconic silhouette, clean pixels",
        prompt_lighting_clause="high-contrast 4-level value separation",
    ),
    "retro-db32": StylePreset(
        name="retro-db32",
        description="DawnBringer 32 classic indie RPG palette with crisp binary alpha.",
        perspective="top_down_3_4",
        default_mode="ai-pixel-look",
        default_palette="db32",
        max_colors=32,
        grid_size=16,
        outline_mode="selective",
        forbid_pure_black_outline=False,
        allow_ground_shadow_alpha=None,
        enforce_ground_alignment=True,
        enforce_banding_check=True,
        enforce_jaggies_check=True,
        min_dynamic_delta_ratio=0.04,
        prompt_style_clause="classic 16-bit indie RPG pixel art sprite using DawnBringer 32 palette, crisp edges, zero blur",
        prompt_lighting_clause="top-left sunlight with rich earthy shadows",
    ),
}


def get_preset(name: str) -> StylePreset:
    """Return a StylePreset by name (case-insensitive)."""
    key = name.strip().lower()
    if key not in PRESETS:
        available = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown style preset {name!r}. Available presets: {available}")
    return PRESETS[key]


def list_presets() -> list[StylePreset]:
    """Return all registered presets sorted by name."""
    return [PRESETS[k] for k in sorted(PRESETS)]
