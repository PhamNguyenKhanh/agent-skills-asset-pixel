---
name: pf-doctor
description: >-
  Slash command `/pf-doctor` — Diagnose Pixel Forge environment: Python, FFmpeg, configured API
  keys (never printing secrets), local CLIs, resolved image/video routes, palettes, presets, and
  cumulative spend ledger.
---

# `/pf-doctor` — Environment & Provider Diagnostics

Use this skill when the user invokes `/pf-doctor` or wants to check why a provider isn't selected, verify FFmpeg/palettes/presets, or inspect API spend totals.

## Commands

```bash
python -m pixel_forge doctor --json
python -m pixel_forge presets
python -m pixel_forge palette list
```

Report:
- Which providers have keys configured (yes/no only — **never print secrets**)
- Resolved default image and video routes
- Whether FFmpeg is on `PATH` (needed for `--track video`)
- Total estimated spend in `.forge/ledger.jsonl`
