---
name: pf-animate
description: >-
  Slash command `/pf-animate` — Animate an existing 2D pixel asset image from a natural-language
  motion description using Pixel Forge (`sheet`, `video`, or `procedural` offline), enforce palette
  and Static Zone lock, run animation QA, and export PNG spritesheet, transparent GIF, `.aseprite`,
  and Unity 6 AnimationClip bundle.
---

# `/pf-animate` — Quick 2D Pixel Animation Workflow

Use this skill whenever the user invokes `/pf-animate` or asks to animate an existing sprite PNG from a description.

## Execution Steps

1. **Confirm inputs**:
   - `asset_png`: path to the base sprite PNG
   - `brief` & `--action`: e.g., `idle`, `walk`, `run`, `attack`, `jump`, `open`, `fire`, `sway`, `hurt`
   - `--frames` (default `6`), `--fps` (default `8`), `--playback` (`loop`, `once`, or `ping_pong`)
   - `--track`:
     - `auto`: picks `video` (if video provider ready + complex action), `sheet` (if image provider ready), or `procedural` (offline)
     - `procedural`: 100% offline deterministic physics animator (0 cost)
     - `sheet`: anchor-locked AI sprite sheet img2img
     - `video`: Image-to-Video → FFmpeg → soft-matte → lattice snap → OKLab color lock

2. **Dry-run first when using AI tracks (`sheet` / `video`)**:
   ```bash
   python -m pixel_forge animate <asset.png> "<motion brief>" --action <action> --frames 6 --fps 8 --playback loop --track <track> --dry-run --json
   ```

3. **Execute animation generation & multi-format export**:
   ```bash
   python -m pixel_forge animate <asset.png> "<motion brief>" --action <action> --frames 6 --fps 8 --playback loop --track <track> --formats png,gif,aseprite,unity --out output/<asset_id>_<action> --json
   ```
   - Use `--lock-bottom-rows 2` for static pedestals/props whose ground base must stay 100% pixel-identical.

4. **Verify & report**:
   - Inspect `qa_status`, `mean_delta_ratio`, and `preview/<asset_id>_<action>_review.png`.
   - Share clickable links to `sheet/`, `gif/`, `aseprite/`, `unity/`, and `preview/sprite_sheet.html`.
