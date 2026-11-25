---
name: pf-export
description: >-
  Slash command `/pf-export` — Repackage existing PNG frames or a sprite sheet into
  PNG (frames + atlas + indexed), crisp transparent GIF, pure-Python binary `.aseprite`,
  optional Aseprite Lua script, Unity 6 bundle, and interactive HTML viewer.
---

# `/pf-export` — Multi-Format Exporter (PNG · GIF · .aseprite · Unity)

Use this skill when the user invokes `/pf-export` or wants to package existing frames or a sprite sheet into game-ready formats without needing Aseprite CLI installed.

## Commands

- **From a folder of ordered frame PNGs**:
  ```bash
  python -m pixel_forge export --frames-dir <dir> --name <asset_id> --action <action> --fps 8 --playback loop --ppu 32 --formats png,gif,aseprite,unity --out output/<asset_id> --json
  ```
- **From an existing sprite sheet PNG**:
  ```bash
  python -m pixel_forge export --sheet <sheet.png> --cols 6 --rows 1 --name <asset_id> --action <action> --fps 8 --ppu 32 --formats png,gif,aseprite,unity --out output/<asset_id> --json
  ```
- **Verify `.aseprite` binary integrity**:
  ```bash
  python -m pixel_forge inspect-aseprite output/<asset_id>/aseprite/<asset_id>_<action>.aseprite --json
  ```
- Add `,lua` to `--formats` if the user also wants an editable Aseprite Lua ASCII-matrix script.
