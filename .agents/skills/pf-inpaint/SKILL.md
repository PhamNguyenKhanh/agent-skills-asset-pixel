---
name: pf-inpaint
description: >-
  Slash command `/pf-inpaint` — Edit a specific masked region of a pixel-art sprite while
  guaranteeing 0 RGBA bytes modified outside the binary black/white mask (verified by SHA-256).
---

# `/pf-inpaint` — RGBA-Protected Mask Inpainting

Use this skill when the user invokes `/pf-inpaint` or asks to recolor/replace one part of an existing sprite (e.g., cape, weapon, helmet) without touching a single pixel outside the mask.

## Requirements

- `--source <sprite.png>`: base sprite PNG
- `--mask <mask.png>`: strictly binary opaque PNG matching source size (`#FFFFFF` = edit, `#000000` = protect). Empty or non-binary masks are rejected before any provider call.

## Execution

1. **Dry-run first**:
   ```bash
   python -m pixel_forge inpaint "<edit instruction>" --source <sprite.png> --mask <mask.png> --out output/<name> --dry-run --json
   ```
2. **Execute & verify `changed_outside_mask == 0`**:
   ```bash
   python -m pixel_forge inpaint "<edit instruction>" --source <sprite.png> --mask <mask.png> --out output/<name> --json
   ```
3. Report the output PNG path, `changed_inside_mask`, and confirm `changed_outside_mask: 0`.
