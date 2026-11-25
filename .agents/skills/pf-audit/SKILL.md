---
name: pf-audit
description: >-
  Slash command `/pf-audit` — Run Pixel Forge 2-tier Quality Audit Gates (binary alpha, grid,
  palette, orphan pixels, chroma fringe, banding, jaggies, ground alignment, tile seams, and
  animation anchor/motion delta) and diagnose fixes.
---

# `/pf-audit` — 2-Tier Pixel Art & Animation QA Gate

Use this skill when the user invokes `/pf-audit` or asks to review, validate, or fix pixel art quality issues.

## Workflow

1. **Run automated 2-tier audit**:
   ```bash
   python -m pixel_forge audit <image_or_dir> --preset <preset> --json
   ```
   - Add `--check-seams` for tileable textures/tilesets.
   - Add `--static-bottom-rows N` to enforce zero drift on static bases in animations.

2. **Interpret Tier 1 (Hard Gates — must pass) vs Tier 2 (Style Warnings)**:
   - `binary_alpha` fail → re-run `matte.remove_background(..., binarize_alpha=True)` or verify preset `allow_ground_shadow_alpha`.
   - `palette` fail → run `python -m pixel_forge palette remap <img.png> --palette <name> --policy strict --out <fixed.png>`.
   - `key_fringe` fail → increase chroma-key tolerance / despill or switch to `hibit` mode.
   - `orphan_pixels` fail → run Hi-bit isolated pixel cleanup or edit manually in Aseprite.
   - `low_motion_delta` warning → increase motion amplitude or adjust frame sampling.
   - `banding` / `jaggies` warning → consult `.agents/rules/pixel_art_common_mistakes.md` and refine pixel clusters.
