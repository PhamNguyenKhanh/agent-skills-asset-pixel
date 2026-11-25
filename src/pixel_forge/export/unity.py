"""Unity 6 Pixel-Perfect 2D Bundle Exporter (Textures + PixelForge.job.json + PixelForgeImporter.cs)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from PIL import Image

from pixel_forge.core.image_io import save_deterministic_png
from pixel_forge.core.palette import project_root
from pixel_forge.core.spec import FrameMeta, SpatialMeta
from pixel_forge.export.png import pack_spritesheet


def _deterministic_unity_guid(seed_text: str) -> str:
    """Produce a 32-hex-char Unity GUID deterministically from asset + slice name."""
    return hashlib.md5(seed_text.encode("utf-8")).hexdigest()


def _load_importer_cs() -> str:
    template_path = project_root() / "unity" / "Editor" / "PixelForgeImporter.cs"
    if template_path.is_file():
        return template_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Missing Unity C# importer template at {template_path}")


def export_unity_bundle(
    frames: Sequence[Image.Image],
    frame_metas: Sequence[FrameMeta],
    out_dir: Path,
    *,
    asset_id: str,
    action: str = "idle",
    fps: int = 8,
    playback: str = "loop",
    pixels_per_unit: int = 32,
    spatial: SpatialMeta | None = None,
) -> dict[str, Any]:
    """Export a self-contained Unity 6 bundle ready to copy into `Assets/PixelForge/<asset_id>/`."""
    if not frames:
        raise ValueError("Cannot export Unity bundle with zero frames.")

    fw, fh = frames[0].size
    sp = spatial or SpatialMeta.default_for(fw, fh)
    unity_dir = out_dir / "unity" / asset_id
    tex_dir = unity_dir / "Textures"
    editor_dir = unity_dir / "Editor"
    tex_dir.mkdir(parents=True, exist_ok=True)
    editor_dir.mkdir(parents=True, exist_ok=True)

    sheet_img, rects = pack_spritesheet(frames, columns=len(frames), padding=0)
    tex_filename = f"{asset_id}_{action}_sheet.png"
    tex_path = tex_dir / tex_filename
    save_deterministic_png(sheet_img, tex_path)

    # Unity texture origin (0, 0) is bottom-left! Convert top-left PIL coordinates accordingly.
    unity_pivot_x = float(sp.pivot_x)
    unity_pivot_y = float(fh - sp.pivot_y)

    slices: list[dict[str, Any]] = []
    clip_frames: list[dict[str, Any]] = []
    elapsed_ms = 0

    for idx, rect in enumerate(rects):
        fm = frame_metas[idx] if idx < len(frame_metas) else FrameMeta(index=idx, duration_ms=max(10, round(1000 / max(1, fps))))
        sname = fm.name or f"{asset_id}_{action}_{idx:02d}"
        unity_y = sheet_img.height - (rect["y"] + rect["h"])
        slices.append(
            {
                "name": sname,
                "guid": _deterministic_unity_guid(f"{asset_id}:{action}:{sname}:{idx}"),
                "x": rect["x"],
                "y": unity_y,
                "width": rect["w"],
                "height": rect["h"],
                "pivotX": unity_pivot_x,
                "pivotY": unity_pivot_y,
            }
        )
        clip_frames.append(
            {
                "sliceName": sname,
                "startMs": elapsed_ms,
                "durationMs": fm.duration_ms,
                "eventName": fm.event or "",
            }
        )
        elapsed_ms += fm.duration_ms

    job_doc = {
        "version": 1,
        "assetId": asset_id,
        "pixelsPerUnit": int(pixels_per_unit),
        "texture": {
            "relativePath": f"Textures/{tex_filename}",
            "width": sheet_img.width,
            "height": sheet_img.height,
            "slices": slices,
        },
        "clips": [
            {
                "name": action,
                "playback": playback,
                "fps": int(fps),
                "frames": clip_frames,
            }
        ],
    }

    job_path = unity_dir / "PixelForge.job.json"
    job_path.write_text(json.dumps(job_doc, indent=2) + "\n", encoding="utf-8")

    importer_cs_path = editor_dir / "PixelForgeImporter.cs"
    importer_cs_path.write_text(_load_importer_cs(), encoding="utf-8", newline="\n")

    setup_md = "\n".join(
        [
            f"# Unity 2D Pixel Perfect Import Guide — `{asset_id}`",
            "",
            "## Quick Import (Unity 6 + `com.unity.2d.sprite`)",
            f"1. Copy this folder (`{asset_id}/`) into your Unity project under `Assets/PixelForge/{asset_id}/`.",
            "2. Wait for Unity to compile `Editor/PixelForgeImporter.cs`.",
            f"3. Select `Assets/PixelForge/{asset_id}/PixelForge.job.json` in the Project window.",
            "4. Click **Assets > Pixel Forge > Import Bundle**.",
            "",
            "The importer automatically configures:",
            f"- `FilterMode.Point`, `mipmapEnabled = false`, `Compression = Uncompressed`, `PixelsPerUnit = {pixels_per_unit}`",
            "- `SpriteMeshType.FullRect` and exact pixel-aligned `SpriteAlignment.Custom` pivots via `ISpriteEditorDataProvider` (with mandatory `ISpriteFrameEditCapability` safety checks)",
            "- `AnimationClip`, `AnimatorController`, and a ready-to-drop `Prefab` in `Generated/`.",
            "",
            "## Pixel Perfect Camera Checklist (URP vs Built-in)",
            "- **URP projects**: Use `UnityEngine.Rendering.Universal.PixelPerfectCamera` (built into URP — do **not** install `com.unity.2d.pixel-perfect`).",
            "- **Built-in projects**: Install `com.unity.2d.pixel-perfect` and use `UnityEngine.U2D.PixelPerfectCamera`.",
            "- Disable Anti-Aliasing (`Quality Settings > Anti Aliasing = Disabled`) and set camera `allowMSAA = false`, `allowHDR = false`.",
            f"- Set `Assets Pixels Per Unit = {pixels_per_unit}` and choose a clean integer Reference Resolution (`320x180`, `480x270`, or `640x360`).",
            "",
        ]
    )
    setup_path = unity_dir / "UNITY_SETUP.md"
    setup_path.write_text(setup_md, encoding="utf-8", newline="\n")

    return {
        "bundle_dir": str(unity_dir),
        "job_json": str(job_path),
        "texture": str(tex_path),
        "importer_cs": str(importer_cs_path),
        "setup_md": str(setup_path),
        "pixels_per_unit": pixels_per_unit,
        "slice_count": len(slices),
    }
