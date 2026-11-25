---
name: pf-unity
description: >-
  Slash command `/pf-unity` — Export Pixel Forge assets as Unity 6 Pixel-Perfect 2D bundles
  (Textures + PixelForge.job.json + PixelForgeImporter.cs with ISpriteFrameEditCapability safety checks)
  and guide URP/Built-in PixelPerfectCamera setup.
---

# `/pf-unity` — Unity 6 Pixel-Perfect 2D Export & Integration

Use this skill when the user invokes `/pf-unity` or wants to bring Pixel Forge sprites/animations into Unity 6 cleanly.

## Steps

1. **Export Unity bundle** (if not already exported):
   ```bash
   python -m pixel_forge export --frames-dir <dir> --name <asset_id> --action <action> --fps 8 --ppu 32 --formats png,unity --out output/<asset_id> --json
   ```
   - Match `--ppu` to the project's base tile pixel width (e.g., `16` for 16×16 tiles, `32` for 32×32 tiles).

2. **Copy into Unity project**:
   - Copy `output/<asset_id>/unity/<asset_id>/` into `Assets/PixelForge/<asset_id>/`.
   - Select `PixelForge.job.json` → click **Assets > Pixel Forge > Import Bundle**.

3. **Verify Unity 2D Pixel Perfect Checklist**:
   - `PixelForgeImporter.cs` automatically enforces `FilterMode.Point`, `mipmapEnabled = false`, `TextureImporterCompression.Uncompressed`, `SpriteMeshType.FullRect`, `ISpriteEditorDataProvider` + `ISpriteFrameEditCapability` checks, and pixel-aligned `SpriteAlignment.Custom` pivots.
   - **URP**: attach `UnityEngine.Rendering.Universal.PixelPerfectCamera` (do NOT install `com.unity.2d.pixel-perfect`).
   - **Built-in**: install `com.unity.2d.pixel-perfect` and attach `UnityEngine.U2D.PixelPerfectCamera`.
   - Disable Anti-Aliasing in Quality Settings and camera `allowMSAA = false`, `allowHDR = false`.
   - Recommended integer reference resolutions: `320x180`, `480x270`, or `640x360`.
