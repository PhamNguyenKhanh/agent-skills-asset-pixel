---
name: pf-asset
description: >-
  Slash command `/pf-asset` — Draw or convert a 2D pixel art asset from a text description
  and optional rough sketch image using Pixel Forge (`direct`, `ai-pixel-look`, or `hibit`),
  run 2-tier QA, and export PNG, GIF, native binary `.aseprite`, and Unity 6 bundle.
---

# `/pf-asset` — Quick 2D Pixel Art Asset Workflow

Use this skill whenever the user invokes `/pf-asset` or asks to draw/generate/pixelize a 2D pixel art sprite, item icon, prop, or character from a description and/or rough image.

## Execution Steps

1. **Clarify missing parameters only if ambiguous**:
   - `brief`: visual description of the asset
   - `rough`: optional path to rough sketch/reference PNG/JPG
   - `size`: logical grid size (default `32x32`; common: `16x16`, `32x32`, `48x48`, `64x64`)
   - `preset`: `topdown-34-stardew`, `topdown-34-terraria`, `freestyle`, `side-view-hibit`, `side-view-pixel-look`, `retro-pico8`, `retro-gameboy`, `retro-db32`
   - `mode`: `auto` (`direct` for offline rough-image conversion, `ai-pixel-look` for AI + grid unzoom, `hibit` for flat cel-art + majority vote)

2. **Check environment & dry-run first** (required before any paid AI call):
   ```bash
   python -m pixel_forge asset "<brief>" --rough <optional.png> --size 32x32 --preset <preset> --mode <mode> --dry-run --json
   ```
   - If `route` is `none` and the user supplied `--rough`, run with `--mode direct --offline`.
   - If `route` is `none` and no `--rough` was supplied, inform the user to configure an API key (`GEMINI_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY`) or run with `--offline` for simulated prototype output.

3. **Execute asset creation & export**:
   ```bash
   python -m pixel_forge asset "<brief>" --rough <optional.png> --size 32x32 --preset <preset> --mode <mode> --formats png,gif,aseprite,unity --out output/<asset_id> --json
   ```

4. **Review QA & inspect visually**:
   - Inspect `qa_status` and `qa_warnings` in the JSON result (`output/<asset_id>/metadata/<asset_id>.qa.md`).
   - Open `output/<asset_id>/preview/<asset_id>_static_review.png` (or `png/<asset_id>.png`) and report clickable file links to the PNG, GIF, `.aseprite`, Unity bundle, and QA summary.
