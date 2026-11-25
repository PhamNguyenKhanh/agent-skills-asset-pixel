"""Unified 3-track Asset Creation Pipeline: ai-pixel-look, hibit, and direct (offline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from pixel_forge.core.image_io import load_normalized_rgba, save_deterministic_png
from pixel_forge.core.palette import Palette, extract_palette, load_palette, remap_image_to_palette
from pixel_forge.core.presets import StylePreset, get_preset
from pixel_forge.core.spec import AssetSpec
from pixel_forge.pixelize.grid_unzoom import unzoom_to_grid
from pixel_forge.pixelize.hibit import hibit_pixelize
from pixel_forge.pixelize.matte import DECLARED_KEYS, remove_background
from pixel_forge.pixelize.operations import add_ground_shadow, add_outline, fit_canvas
from pixel_forge.providers.base import MediaRequest
from pixel_forge.providers.router import MediaRouter


@dataclass
class AssetResult:
    status: str
    asset_id: str
    mode: str
    preset: str
    image: Image.Image | None
    palette: Palette | None
    route: str
    model: str | None
    estimate_usd: float = 0.0
    raw_path: Path | None = None
    report: dict[str, Any] = field(default_factory=dict)


def build_asset_prompt(
    spec: AssetSpec,
    preset: StylePreset,
    *,
    key_name: str = "magenta",
    has_rough: bool = False,
    mode: str = "ai-pixel-look",
) -> str:
    """Compile an Art-Director-grade generation prompt from AssetSpec + StylePreset."""
    key_hex = {"magenta": "#FF00FF", "green": "#00FF00", "blue": "#0000FF"}.get(key_name, "#FF00FF")
    parts = [
        f"Single isolated 2D game asset: {spec.brief}.",
        f"Style: {preset.prompt_style_clause}.",
        f"Lighting: {preset.prompt_lighting_clause}.",
        f"Target logical grid: {spec.width}x{spec.height} pixels (100% crisp readable silhouette).",
    ]
    if has_rough:
        parts.append(
            "Follow the exact silhouette, proportions, and pose of the attached rough sketch/reference image, "
            "refining it into clean production game art."
        )
    if mode == "hibit":
        parts.append(
            "Paint as clean flat lineless cel-shaded illustration (max 3 flat tones per material, no outlines, no gradients) "
            "so deterministic majority-vote pixelization recovers razor-sharp pixels."
        )
    parts.append(
        f"Place centered on a completely flat, solid uniform {key_name} ({key_hex}) chroma-key background. "
        "No ground floor, no checkerboard, no frame borders, no text labels, no drop shadow on the background."
    )
    return " ".join(parts)


def _resolve_target_palette(spec: AssetSpec, preset: StylePreset, img: Image.Image) -> Palette | None:
    pal_name = spec.palette if spec.palette is not None else preset.default_palette
    if pal_name and pal_name.lower() != "none":
        return load_palette(pal_name)
    max_c = spec.max_colors or preset.max_colors
    return extract_palette(img, max_colors=max_c, name=f"{spec.asset_id}_palette")


def create_asset(
    spec: AssetSpec,
    router: MediaRouter,
    out_dir: Path,
    *,
    rough_image: Path | None = None,
    dry_run: bool = False,
) -> AssetResult:
    """Generate or convert a 2D pixel asset via `direct`, `ai-pixel-look`, or `hibit` track."""
    preset = get_preset(spec.preset)
    mode = spec.mode.strip().lower()
    if mode == "auto":
        if rough_image is not None and (router.offline or not router.has_route("image")):
            mode = "direct"
        else:
            mode = preset.default_mode

    if mode not in ("direct", "ai-pixel-look", "hibit"):
        raise ValueError(f"Unsupported asset mode {mode!r}. Use 'auto', 'ai-pixel-look', 'hibit', or 'direct'.")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "_raw"
    align = spec.align if spec.align != "auto" else ("bottom" if preset.enforce_ground_alignment else "center")
    outline_choice = spec.outline if spec.outline is not None else preset.outline_mode
    key_name = spec.key_color if spec.key_color in DECLARED_KEYS else "magenta"

    if mode == "direct":
        if rough_image is None:
            raise ValueError("Direct mode requires a rough/source image (--rough <image>).")
        if dry_run:
            return AssetResult(
                status="dry_run",
                asset_id=spec.asset_id,
                mode="direct",
                preset=preset.name,
                image=None,
                palette=None,
                route="offline:direct",
                model="deterministic-pixelize",
                estimate_usd=0.0,
                raw_path=rough_image,
                report={"source": str(rough_image), "target_size": [spec.width, spec.height]},
            )
        src_img, ingest_rep = load_normalized_rgba(rough_image)
        keyed, matte_rep = remove_background(src_img, key_color=spec.key_color, binarize_alpha=True)
        unzoomed, unzoom_rep = unzoom_to_grid(keyed)
        pad = 1 if (outline_choice and outline_choice != "none") else 0
        fitted = fit_canvas(unzoomed, (spec.width, spec.height), fit_mode=spec.fit_mode, align=align, padding=pad)
        palette = _resolve_target_palette(spec, preset, fitted)
        remap_rep: dict[str, Any] = {}
        if palette is not None and spec.palette_policy != "none":
            fitted, remap_rep = remap_image_to_palette(fitted, palette, policy=spec.palette_policy)
        if outline_choice and outline_choice != "none":
            fitted = add_outline(fitted, color=outline_choice, mode="outer")
        if spec.add_ground_shadow or (preset.allow_ground_shadow_alpha is not None and preset.enforce_ground_alignment):
            fitted = add_ground_shadow(fitted, alpha=preset.allow_ground_shadow_alpha or 130)
        final_pal = extract_palette(fitted, max_colors=spec.max_colors or preset.max_colors, name=f"{spec.asset_id}_palette")
        return AssetResult(
            status="ok",
            asset_id=spec.asset_id,
            mode="direct",
            preset=preset.name,
            image=fitted,
            palette=final_pal,
            route="offline:direct",
            model="deterministic-pixelize",
            raw_path=rough_image,
            report={"ingest": ingest_rep, "matte": matte_rep, "unzoom": unzoom_rep, "palette_remap": remap_rep},
        )

    prompt = build_asset_prompt(spec, preset, key_name=key_name, has_rough=rough_image is not None, mode=mode)
    refs = [rough_image] if rough_image is not None else []
    req = MediaRequest(
        kind="image",
        prompt=prompt,
        out_dir=raw_dir,
        references=refs,
        size="1024x1024",
        transparent=False,
        extra={"key_rgb": DECLARED_KEYS[key_name]},
    )
    media = router.execute(req, dry_run=dry_run)
    if dry_run:
        return AssetResult(
            status="dry_run",
            asset_id=spec.asset_id,
            mode=mode,
            preset=preset.name,
            image=None,
            palette=None,
            route=media.route,
            model=media.model,
            estimate_usd=media.estimate_usd,
            report={"compiled_prompt": prompt, "notes": media.notes},
        )
    if media.status != "ok" or media.artifact_path is None:
        if rough_image is not None:
            fallback_spec = AssetSpec(**{**spec.to_dict(), "mode": "direct"})
            return create_asset(fallback_spec, router, out_dir, rough_image=rough_image, dry_run=False)
        raise RuntimeError(
            "No AI image provider available. Configure an API key (GEMINI_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY), "
            "pass --rough <sketch.png> for direct mode, or pass --offline to test with the simulated provider."
        )

    raw_img, ingest_rep = load_normalized_rgba(media.artifact_path)
    (raw_dir / f"{spec.asset_id}.prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    save_deterministic_png(raw_img, raw_dir / f"{spec.asset_id}.raw.png")

    keyed, matte_rep = remove_background(raw_img, key_color=spec.key_color, binarize_alpha=True)

    if mode == "hibit":
        target_pal = load_palette(spec.palette) if (spec.palette and spec.palette.lower() != "none") else None
        max_c = spec.max_colors or preset.max_colors
        pixel_img, _, pal_arr, hibit_rep = hibit_pixelize(
            keyed,
            (spec.width, spec.height),
            n_colors=max_c,
            palette=target_pal,
            outline=outline_choice or "auto",
        )
        if spec.add_ground_shadow:
            pixel_img = add_ground_shadow(pixel_img, alpha=preset.allow_ground_shadow_alpha or 130)
        pal_obj = Palette(
            name=f"{spec.asset_id}_hibit",
            colors=tuple((int(r), int(g), int(b)) for r, g, b in pal_arr),
            max_colors=len(pal_arr),
        )
        return AssetResult(
            status="ok",
            asset_id=spec.asset_id,
            mode="hibit",
            preset=preset.name,
            image=pixel_img,
            palette=pal_obj,
            route=media.route,
            model=media.model,
            estimate_usd=media.estimate_usd,
            raw_path=media.artifact_path,
            report={"ingest": ingest_rep, "matte": matte_rep, "hibit": hibit_rep, "prompt": prompt},
        )

    unzoomed, unzoom_rep = unzoom_to_grid(keyed)
    pad = 1 if (outline_choice and outline_choice not in ("none", "auto") and not unzoom_rep.get("applied")) else 0
    fitted = fit_canvas(unzoomed, (spec.width, spec.height), fit_mode=spec.fit_mode, align=align, padding=pad)
    palette = _resolve_target_palette(spec, preset, fitted)
    remap_rep = {}
    if palette is not None and spec.palette_policy != "none":
        fitted, remap_rep = remap_image_to_palette(fitted, palette, policy=spec.palette_policy)
    if spec.add_ground_shadow:
        fitted = add_ground_shadow(fitted, alpha=preset.allow_ground_shadow_alpha or 130)
    final_pal = extract_palette(fitted, max_colors=spec.max_colors or preset.max_colors, name=f"{spec.asset_id}_palette")
    return AssetResult(
        status="ok",
        asset_id=spec.asset_id,
        mode="ai-pixel-look",
        preset=preset.name,
        image=fitted,
        palette=final_pal,
        route=media.route,
        model=media.model,
        estimate_usd=media.estimate_usd,
        raw_path=media.artifact_path,
        report={"ingest": ingest_rep, "matte": matte_rep, "unzoom": unzoom_rep, "palette_remap": remap_rep, "prompt": prompt},
    )
