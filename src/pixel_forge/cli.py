"""Unified CLI for Pixel Forge (`pixelforge` / `python -m pixel_forge`)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import click
from PIL import Image
from rich.console import Console
from rich.table import Table

from pixel_forge import __version__
from pixel_forge.animate.pipeline import create_animation
from pixel_forge.core.image_io import load_normalized_rgba, save_deterministic_png
from pixel_forge.core.palette import extract_palette, list_palettes, load_palette, remap_image_to_palette, save_palette
from pixel_forge.core.presets import get_preset, list_presets
from pixel_forge.core.spec import AnimationSpec, AssetSpec, ExportSpec, parse_size, slugify
from pixel_forge.export.aseprite import inspect_aseprite_file
from pixel_forge.export.bundle import export_bundle
from pixel_forge.pixelize.inpaint import run_inpaint
from pixel_forge.pixelize.operations import bayer_dither, value_noise_tile
from pixel_forge.pixelize.pipeline import create_asset
from pixel_forge.providers.router import MediaRouter
from pixel_forge.qa.gates import audit_animation, audit_image
from pixel_forge.qa.report import format_audit_markdown

console = Console()


def _emit(payload: dict[str, Any], *, as_json: bool, title: str | None = None) -> None:
    if as_json:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    if title:
        console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print_json(json.dumps(payload, ensure_ascii=False))


@click.group()
@click.version_option(__version__, prog_name="pixelforge")
def main() -> None:
    """Pixel Forge — Unified 2D Pixel Art & Animation Studio (PNG · GIF · .aseprite · Unity)."""


# --------------------------------------------------------------------------- doctor & presets


@main.command()
@click.option("--route", default="auto", show_default=True, help="Provider route to check.")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
def doctor(route: str, as_json: bool) -> None:
    """Check Python environment, FFmpeg, configured API keys (yes/no only), palettes, presets, and spend ledger."""
    router = MediaRouter(route=route)
    report = {
        "version": __version__,
        "python": sys.version.split()[0],
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "aseprite_binary_writer": "pure-python (no Aseprite CLI required)",
        "palettes": list_palettes(),
        "presets": [p.name for p in list_presets()],
        **router.doctor_report(),
    }
    if as_json:
        click.echo(json.dumps(report, indent=2, ensure_ascii=False))
        return

    table = Table(title=f"Pixel Forge v{__version__} — Environment Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Python", report["python"])
    table.add_row("FFmpeg (for video track)", "Available" if report["ffmpeg"] else "Missing")
    table.add_row("Aseprite Exporter", report["aseprite_binary_writer"])
    table.add_row("API Keys", ", ".join(f"{k}={'YES' if v else 'no'}" for k, v in report["api_keys"].items()))
    table.add_row("Local CLIs", ", ".join(f"{k}={'YES' if v else 'no'}" for k, v in report["local_clis"].items()))
    table.add_row("Resolved Image Route", str(report["resolved_image_route"] or "none (use --offline / direct)"))
    table.add_row("Resolved Video Route", str(report["resolved_video_route"] or "none (use --track procedural/sheet)"))
    table.add_row("Palettes Loaded", str(len(report["palettes"])))
    table.add_row("Presets Loaded", str(len(report["presets"])))
    table.add_row("Ledger Spend (est.)", f"${report['ledger']['total_estimate_usd']:.4f} ({report['ledger']['total_calls']} calls)")
    console.print(table)


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
def presets(as_json: bool) -> None:
    """List all built-in Style & Perspective presets."""
    items = [p.to_dict() for p in list_presets()]
    if as_json:
        click.echo(json.dumps({"presets": items}, indent=2, ensure_ascii=False))
        return
    table = Table(title="Pixel Forge Style Presets")
    table.add_column("Name", style="cyan")
    table.add_column("Perspective")
    table.add_column("Mode")
    table.add_column("Palette")
    table.add_column("Max Colors", justify="right")
    table.add_column("Description")
    for p in list_presets():
        table.add_row(p.name, p.perspective, p.default_mode, p.default_palette or "learned", str(p.max_colors), p.description)
    console.print(table)


# --------------------------------------------------------------------------- asset


@main.command()
@click.argument("brief")
@click.option("--name", default=None, help="Asset ID / filename stem (auto-derived from brief if omitted).")
@click.option("--rough", "rough_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Optional rough sketch / reference image.")
@click.option("--size", default="32x32", show_default=True, help="Target logical pixel grid size (e.g. 32x32, 48x64).")
@click.option("--preset", default="topdown-34-stardew", show_default=True, help="Style preset name.")
@click.option("--mode", type=click.Choice(["auto", "ai-pixel-look", "hibit", "direct"], case_sensitive=False), default="auto", show_default=True)
@click.option("--palette", default=None, help="Palette name/path or 'none' to learn from image.")
@click.option("--palette-policy", type=click.Choice(["strict", "guided", "none"]), default="strict", show_default=True)
@click.option("--max-colors", type=int, default=None, help="Override preset max color limit.")
@click.option("--outline", default=None, help="Outline mode: auto, selective, dark, none, or #rrggbb.")
@click.option("--fit", "fit_mode", type=click.Choice(["contain", "stretch"]), default="contain", show_default=True)
@click.option("--align", type=click.Choice(["auto", "bottom", "center"]), default="auto", show_default=True)
@click.option("--key-color", default="auto", show_default=True, help="Chroma-key color: auto, magenta, green, blue, or #rrggbb.")
@click.option("--ground-shadow", is_flag=True, help="Add soft ground-contact shadow ('S') underneath the sprite.")
@click.option("--formats", default="png,gif,aseprite,unity", show_default=True, help="Comma-separated export formats: png,gif,aseprite,unity,lua,html.")
@click.option("--ppu", type=int, default=32, show_default=True, help="Unity Pixels Per Unit.")
@click.option("--scale", "preview_scale", type=int, default=4, show_default=True, help="Integer preview scale factor.")
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path), default=None, help="Output folder.")
@click.option("--route", default="auto", show_default=True, help="AI provider route.")
@click.option("--budget-usd", type=float, default=None, help="Optional spend cap in USD.")
@click.option("--max-calls", type=int, default=None, help="Optional max paid API calls cap.")
@click.option("--offline", is_flag=True, help="Run 100% offline (direct mode if --rough given, else simulated provider).")
@click.option("--dry-run", is_flag=True, help="Preview route, prompt, and cost estimate without generating.")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
def asset(
    brief: str,
    name: str | None,
    rough_path: Path | None,
    size: str,
    preset: str,
    mode: str,
    palette: str | None,
    palette_policy: str,
    max_colors: int | None,
    outline: str | None,
    fit_mode: str,
    align: str,
    key_color: str,
    ground_shadow: bool,
    formats: str,
    ppu: int,
    preview_scale: int,
    out_dir: Path | None,
    route: str,
    budget_usd: float | None,
    max_calls: int | None,
    offline: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Create a 2D pixel-art asset from a text brief and optional rough image."""
    w, h = parse_size(size)
    asset_id = slugify(name or brief)
    target_dir = out_dir or (Path("output") / asset_id)

    spec = AssetSpec(
        asset_id=asset_id,
        brief=brief,
        width=w,
        height=h,
        preset=preset,
        mode=mode,
        palette=palette,
        palette_policy=palette_policy,
        max_colors=max_colors,
        outline=outline,
        fit_mode=fit_mode,
        align=align,
        key_color=key_color,
        add_ground_shadow=ground_shadow,
    )
    router = MediaRouter(route=route, budget_usd=budget_usd, max_calls=max_calls, offline=offline)
    res = create_asset(spec, router, target_dir, rough_image=rough_path, dry_run=dry_run)

    if dry_run or res.image is None:
        _emit(
            {
                "status": res.status,
                "asset_id": res.asset_id,
                "mode": res.mode,
                "preset": res.preset,
                "route": res.route,
                "model": res.model,
                "estimate_usd": res.estimate_usd,
                "report": res.report,
            },
            as_json=as_json,
            title="Dry-Run Asset Plan",
        )
        return

    preset_obj = get_preset(preset)
    spatial = spec.resolved_spatial(preset_obj.perspective)
    exp_spec = ExportSpec.from_csv(formats, pixels_per_unit=ppu, preview_scale=preview_scale)
    exported = export_bundle(
        [res.image],
        target_dir,
        asset_id=asset_id,
        action="static",
        fps=8,
        playback="once",
        spatial=spatial,
        export_spec=exp_spec,
    )
    if res.palette:
        save_palette(res.palette, target_dir / "metadata" / f"{asset_id}.palette.json")

    qa = audit_image(res.image, preset_name=preset, max_colors=max_colors)
    (target_dir / "metadata" / f"{asset_id}.qa.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    (target_dir / "metadata" / f"{asset_id}.qa.md").write_text(format_audit_markdown(qa), encoding="utf-8")

    payload = {
        "status": "ok",
        "asset_id": asset_id,
        "mode": res.mode,
        "preset": res.preset,
        "route": res.route,
        "model": res.model,
        "size": [res.image.width, res.image.height],
        "qa_status": qa["status"],
        "qa_warnings": qa["warnings"],
        "exports": exported,
    }
    _emit(payload, as_json=as_json, title=f"Asset Created: {asset_id} ({qa['status'].upper()})")


# --------------------------------------------------------------------------- animate


@main.command()
@click.argument("asset_png", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("brief", default="")
@click.option("--name", default=None, help="Asset ID (defaults to input filename stem).")
@click.option("--action", default="idle", show_default=True, help="Action tag name (idle, walk, run, attack, jump, open, fire, sway, hurt).")
@click.option("--frames", "frame_count", type=int, default=6, show_default=True, help="Target frame count.")
@click.option("--fps", type=int, default=8, show_default=True, help="Playback FPS.")
@click.option("--playback", type=click.Choice(["loop", "once", "ping_pong"]), default="loop", show_default=True)
@click.option("--track", type=click.Choice(["auto", "sheet", "video", "procedural"]), default="auto", show_default=True)
@click.option("--preset", default="topdown-34-stardew", show_default=True, help="Style preset for prompt and QA.")
@click.option("--no-palette-lock", is_flag=True, help="Allow new colors outside the master asset palette.")
@click.option("--lock-bottom-rows", type=int, default=0, show_default=True, help="Keep bottom N rows pixel-identical (Static Zone).")
@click.option("--mirror", type=click.Choice(["horizontal", "vertical"]), default=None, help="Explicitly mirror generated frames.")
@click.option("--allow-asymmetric-mirror", is_flag=True, help="Force mirroring even when sprite is asymmetric.")
@click.option("--formats", default="png,gif,aseprite,unity", show_default=True, help="Comma-separated export formats.")
@click.option("--ppu", type=int, default=32, show_default=True, help="Unity Pixels Per Unit.")
@click.option("--scale", "preview_scale", type=int, default=4, show_default=True, help="Integer preview scale factor.")
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path), default=None, help="Output folder.")
@click.option("--route", default="auto", show_default=True, help="AI provider route.")
@click.option("--budget-usd", type=float, default=None, help="Optional spend cap in USD.")
@click.option("--max-calls", type=int, default=None, help="Optional max paid API calls cap.")
@click.option("--offline", is_flag=True, help="Run 100% offline (uses procedural or simulated track).")
@click.option("--dry-run", is_flag=True, help="Preview track, route, and cost estimate without generating.")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
def animate(
    asset_png: Path,
    brief: str,
    name: str | None,
    action: str,
    frame_count: int,
    fps: int,
    playback: str,
    track: str,
    preset: str,
    no_palette_lock: bool,
    lock_bottom_rows: int,
    mirror: str | None,
    allow_asymmetric_mirror: bool,
    formats: str,
    ppu: int,
    preview_scale: int,
    out_dir: Path | None,
    route: str,
    budget_usd: float | None,
    max_calls: int | None,
    offline: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Create a multi-frame pixel animation from an existing asset image + description."""
    asset_id = slugify(name or asset_png.stem)
    action_slug = slugify(action)
    target_dir = out_dir or (Path("output") / f"{asset_id}_{action_slug}")

    spec = AnimationSpec(
        asset_id=asset_id,
        action=action_slug,
        brief=brief or action,
        frame_count=frame_count,
        fps=fps,
        playback=playback,
        track=track,
        preset=preset,
        lock_palette=not no_palette_lock,
        lock_static_bottom_rows=lock_bottom_rows,
        mirror_direction=mirror,
        allow_asymmetric_mirror=allow_asymmetric_mirror,
    )
    router = MediaRouter(route=route, budget_usd=budget_usd, max_calls=max_calls, offline=offline)
    res = create_animation(asset_png, spec, router, target_dir, dry_run=dry_run)

    if dry_run or not res.frames:
        _emit(
            {
                "status": res.status,
                "asset_id": res.asset_id,
                "action": res.action,
                "track": res.track,
                "route": res.route,
                "model": res.model,
                "estimate_usd": res.estimate_usd,
                "report": res.report,
            },
            as_json=as_json,
            title="Dry-Run Animation Plan",
        )
        return

    preset_obj = get_preset(preset)
    fw, fh = res.frames[0].size
    from pixel_forge.core.spec import SpatialMeta

    spatial = SpatialMeta.default_for(fw, fh, preset_obj.perspective)
    exp_spec = ExportSpec.from_csv(formats, pixels_per_unit=ppu, preview_scale=preview_scale)
    exported = export_bundle(
        res.frames,
        target_dir,
        asset_id=asset_id,
        action=action_slug,
        fps=fps,
        playback=playback,
        frame_metas=res.frame_metas,
        spatial=spatial,
        export_spec=exp_spec,
    )

    qa = audit_animation(res.frames, preset_name=preset, static_bottom_rows=lock_bottom_rows)
    (target_dir / "metadata" / f"{asset_id}_{action_slug}.qa.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    (target_dir / "metadata" / f"{asset_id}_{action_slug}.qa.md").write_text(format_audit_markdown(qa), encoding="utf-8")

    payload = {
        "status": "ok",
        "asset_id": asset_id,
        "action": action_slug,
        "track": res.track,
        "route": res.route,
        "model": res.model,
        "frame_count": len(res.frames),
        "fps": fps,
        "qa_status": qa["status"],
        "qa_warnings": qa["warnings"] + res.warnings,
        "exports": exported,
    }
    _emit(payload, as_json=as_json, title=f"Animation Created: {asset_id}_{action_slug} ({qa['status'].upper()})")


# --------------------------------------------------------------------------- export


@main.command("export")
@click.option("--frames-dir", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Directory of ordered frame PNGs.")
@click.option("--sheet", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Existing sprite sheet PNG to slice.")
@click.option("--cols", type=int, default=1, show_default=True, help="Columns when slicing --sheet.")
@click.option("--rows", type=int, default=1, show_default=True, help="Rows when slicing --sheet.")
@click.option("--name", required=True, help="Asset ID.")
@click.option("--action", default="idle", show_default=True, help="Animation tag name.")
@click.option("--fps", type=int, default=8, show_default=True)
@click.option("--playback", type=click.Choice(["loop", "once", "ping_pong"]), default="loop", show_default=True)
@click.option("--formats", default="png,gif,aseprite,unity", show_default=True)
@click.option("--ppu", type=int, default=32, show_default=True)
@click.option("--scale", "preview_scale", type=int, default=4, show_default=True)
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path), required=True)
@click.option("--json", "as_json", is_flag=True)
def export_cmd(
    frames_dir: Path | None,
    sheet: Path | None,
    cols: int,
    rows: int,
    name: str,
    action: str,
    fps: int,
    playback: str,
    formats: str,
    ppu: int,
    preview_scale: int,
    out_dir: Path,
    as_json: bool,
) -> None:
    """Package existing frames or a sprite sheet into PNG, GIF, .aseprite, Unity bundle, and HTML preview."""
    frames: list[Image.Image] = []
    if frames_dir is not None:
        for p in sorted(frames_dir.glob("*.png")):
            img, _ = load_normalized_rgba(p)
            frames.append(img)
    elif sheet is not None:
        sheet_img, _ = load_normalized_rgba(sheet)
        cw = sheet_img.width // max(1, cols)
        ch = sheet_img.height // max(1, rows)
        for r in range(rows):
            for c in range(cols):
                frames.append(sheet_img.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)))
    else:
        raise click.UsageError("Provide either --frames-dir or --sheet.")

    if not frames:
        raise click.UsageError("No PNG frames found to export.")

    exp_spec = ExportSpec.from_csv(formats, pixels_per_unit=ppu, preview_scale=preview_scale)
    exported = export_bundle(
        frames,
        out_dir,
        asset_id=slugify(name),
        action=slugify(action),
        fps=fps,
        playback=playback,
        export_spec=exp_spec,
    )
    _emit({"status": "ok", "frame_count": len(frames), "exports": exported}, as_json=as_json, title="Export Complete")


# --------------------------------------------------------------------------- inpaint


@main.command()
@click.argument("instruction")
@click.option("--source", "source_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--mask", "mask_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path), default=Path("output/inpaint"))
@click.option("--route", default="auto", show_default=True)
@click.option("--offline", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def inpaint(
    instruction: str,
    source_path: Path,
    mask_path: Path,
    out_dir: Path,
    route: str,
    offline: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Inpaint a masked region while guaranteeing 0 RGBA bytes change outside the mask."""
    router = MediaRouter(route=route, offline=offline)
    result = run_inpaint(source_path, mask_path, instruction, router, out_dir, dry_run=dry_run)
    _emit(result, as_json=as_json, title="RGBA-Protected Inpaint")


# --------------------------------------------------------------------------- audit & inspect


@main.command()
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("--preset", default="freestyle", show_default=True)
@click.option("--grid", "grid_size", type=int, default=None)
@click.option("--max-colors", type=int, default=None)
@click.option("--check-seams", is_flag=True, help="Also measure tile X/Y seam continuity.")
@click.option("--static-bottom-rows", type=int, default=0, show_default=True)
@click.option("--json", "as_json", is_flag=True)
def audit(
    target: Path,
    preset: str,
    grid_size: int | None,
    max_colors: int | None,
    check_seams: bool,
    static_bottom_rows: int,
    as_json: bool,
) -> None:
    """Run 2-tier pixel-art QA gates on a PNG file or a folder of animation frames."""
    if target.is_dir():
        frames_dir = target / "frames" if (target / "frames").is_dir() else target
        pngs = sorted(frames_dir.glob("*.png"))
        if not pngs:
            raise click.UsageError(f"No PNG files found in {frames_dir}")
        imgs = [load_normalized_rgba(p)[0] for p in pngs]
        report = audit_animation(
            imgs,
            preset_name=preset,
            grid_size=grid_size,
            max_colors=max_colors,
            static_bottom_rows=static_bottom_rows,
        )
    else:
        img, _ = load_normalized_rgba(target)
        report = audit_image(img, preset_name=preset, grid_size=grid_size, max_colors=max_colors, check_seams=check_seams)

    if as_json:
        click.echo(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        click.echo(format_audit_markdown(report))
    if not report.get("hard_passed", False):
        sys.exit(1)


@main.command("inspect-aseprite")
@click.argument("ase_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def inspect_aseprite_cmd(ase_file: Path, as_json: bool) -> None:
    """Parse and verify a binary `.aseprite` file (header, layers, tags, pivot, compressed cels)."""
    info = inspect_aseprite_file(ase_file)
    _emit(info, as_json=as_json, title=f"Aseprite Binary Inspection: {ase_file.name}")


# --------------------------------------------------------------------------- palette tools


@main.group()
def palette() -> None:
    """List, extract, or remap pixel-art color palettes."""


@palette.command("list")
@click.option("--json", "as_json", is_flag=True)
def palette_list(as_json: bool) -> None:
    """List all built-in curated palettes."""
    names = list_palettes()
    entries = [load_palette(n).to_dict() for n in names]
    if as_json:
        click.echo(json.dumps({"palettes": entries}, indent=2, ensure_ascii=False))
        return
    table = Table(title="Built-in Pixel Forge Palettes")
    table.add_column("Name", style="cyan")
    table.add_column("Colors", justify="right")
    table.add_column("Sample Hexes")
    for p in entries:
        table.add_row(p["name"], str(len(p["colors"])), " ".join(p["colors"][:6]))
    console.print(table)


@palette.command("extract")
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--max-colors", type=int, default=16, show_default=True)
@click.option("--out", "out_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
@click.option("--json", "as_json", is_flag=True)
def palette_extract_cmd(image_path: Path, max_colors: int, out_path: Path, as_json: bool) -> None:
    """Extract a palette JSON from an existing PNG image."""
    img, _ = load_normalized_rgba(image_path)
    pal = extract_palette(img, max_colors=max_colors, name=image_path.stem)
    save_palette(pal, out_path)
    _emit({"status": "ok", "output": str(out_path), "palette": pal.to_dict()}, as_json=as_json)


@palette.command("remap")
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--palette", "palette_ref", required=True, help="Palette name or JSON path.")
@click.option("--policy", type=click.Choice(["strict", "guided"]), default="strict", show_default=True)
@click.option("--out", "out_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
@click.option("--json", "as_json", is_flag=True)
def palette_remap_cmd(image_path: Path, palette_ref: str, policy: str, out_path: Path, as_json: bool) -> None:
    """Remap an image's visible pixels to a target palette without altering alpha."""
    img, _ = load_normalized_rgba(image_path)
    pal = load_palette(palette_ref)
    remapped, report = remap_image_to_palette(img, pal, policy=policy)
    saved = save_deterministic_png(remapped, out_path)
    _emit({"status": "ok", "output": saved, "report": report}, as_json=as_json)


# --------------------------------------------------------------------------- procedural texture utilities


@main.command()
@click.option("--size", default="64x64", show_default=True)
@click.option("--color1", default="#1d2b53", show_default=True)
@click.option("--color2", default="#29adff", show_default=True)
@click.option("--matrix", type=click.Choice(["2", "4"]), default="4", show_default=True)
@click.option("--direction", type=click.Choice(["vertical", "horizontal"]), default="vertical", show_default=True)
@click.option("--out", "out_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
def dither(size: str, color1: str, color2: str, matrix: str, direction: str, out_path: Path) -> None:
    """Generate an ordered Bayer-dithered pixel-art gradient."""
    w, h = parse_size(size)
    img = bayer_dither(w, h, color1, color2, matrix=int(matrix), direction=direction)
    info = save_deterministic_png(img, out_path)
    click.echo(json.dumps({"status": "ok", **info}, indent=2))


@main.command()
@click.option("--size", default="64x64", show_default=True)
@click.option("--palette", "palette_ref", default="master_topdown", show_default=True)
@click.option("--scale", type=int, default=8, show_default=True)
@click.option("--octaves", type=int, default=2, show_default=True)
@click.option("--seed", type=int, default=0, show_default=True)
@click.option("--out", "out_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
def noise(size: str, palette_ref: str, scale: int, octaves: int, seed: int, out_path: Path) -> None:
    """Generate a seamless tileable procedural value-noise texture."""
    w, h = parse_size(size)
    pal = load_palette(palette_ref)
    img = value_noise_tile(w, h, pal, scale=scale, octaves=octaves, seed=seed)
    info = save_deterministic_png(img, out_path)
    click.echo(json.dumps({"status": "ok", **info}, indent=2))


if __name__ == "__main__":
    main()
