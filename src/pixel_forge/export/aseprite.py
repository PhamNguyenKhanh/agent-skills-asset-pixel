"""Pure-Python native binary `.aseprite` writer, structural reader, and optional Lua script emitter.

Implements the official Aseprite binary specification:
https://github.com/aseprite/aseprite/blob/main/docs/ase-file-specs.md
Zero dependency on Aseprite CLI being installed.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any, BinaryIO, Sequence

import numpy as np
from PIL import Image

from pixel_forge.core.palette import rgb_to_hex
from pixel_forge.core.spec import SpatialMeta

ASE_MAGIC = 0xA5E0
ASE_FRAME_MAGIC = 0xF1FA
CHUNK_LAYER = 0x2004
CHUNK_CEL = 0x2005
CHUNK_TAGS = 0x2018
CHUNK_SLICE = 0x2022

ASE_BLEND = {"normal": 0, "multiply": 1, "screen": 2, "additive": 16}


def _ase_string(text: str) -> bytes:
    data = text.encode("utf-8")
    return struct.pack("<H", len(data)) + data


def _ase_chunk(fp: BinaryIO, kind: int, *parts: bytes) -> None:
    size = 6 + sum(len(p) for p in parts)
    fp.write(struct.pack("<IH", size, kind))
    fp.writelines(parts)


def _split_shadow_and_main(frame: Image.Image) -> tuple[Image.Image | None, Image.Image]:
    """If semi-transparent ground contact shadow pixels exist, split them onto a dedicated Shadow layer."""
    arr = np.asarray(frame.convert("RGBA"))
    semi = (arr[..., 3] > 0) & (arr[..., 3] < 255)
    if not semi.any():
        return None, frame.convert("RGBA")
    shadow_arr = np.zeros_like(arr)
    main_arr = arr.copy()
    shadow_arr[semi] = arr[semi]
    main_arr[semi] = (0, 0, 0, 0)
    return Image.fromarray(shadow_arr, mode="RGBA"), Image.fromarray(main_arr, mode="RGBA")


def write_aseprite(
    frames: Sequence[Image.Image],
    durations_ms: Sequence[int],
    output_path: Path | str,
    *,
    tag_name: str = "idle",
    playback: str = "loop",
    pivot: tuple[int, int] | None = None,
    split_shadow_layer: bool = True,
    blend_mode: str = "normal",
) -> dict[str, Any]:
    """Write a complete native binary `.aseprite` file with layers, compressed RGBA cels, tags, and pivot slice."""
    if not frames:
        raise ValueError("Cannot write .aseprite with zero frames.")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    w, h = frames[0].size
    px, py = pivot if pivot is not None else (w // 2, h - 1)

    # Determine whether any frame carries a ground-contact shadow layer.
    split_frames = [_split_shadow_and_main(f) for f in frames] if split_shadow_layer else [(None, f.convert("RGBA")) for f in frames]
    has_shadow = any(sh is not None for sh, _ in split_frames)
    layer_names = ["Shadow", "Main"] if has_shadow else ["Main"]

    blend_val = ASE_BLEND.get(blend_mode, 0)
    direction = 2 if playback == "ping_pong" else 0
    repeats = 1 if playback == "once" else 0

    with target.open("wb") as fp:
        fp.seek(128)  # Reserve 128-byte Aseprite header
        for f_idx, (sh_img, main_img) in enumerate(split_frames):
            frame_start = fp.tell()
            fp.seek(frame_start + 16)
            chunks = 0

            if f_idx == 0:
                # 1. Layer chunks (0x2004)
                for lname in layer_names:
                    # flags=3 (visible + editable), type=0 (normal image layer)
                    layer_hdr = struct.pack("<6HB3x", 3, 0, 0, 0, 0, blend_val, 255)
                    _ase_chunk(fp, CHUNK_LAYER, layer_hdr, _ase_string(lname))
                    chunks += 1

                # 2. Tags chunk (0x2018)
                tag_hdr = struct.pack(
                    "<H8xHHBH6x3Bx",
                    1,  # number of tags
                    0,  # from frame
                    len(frames) - 1,  # to frame
                    direction,  # 0=forward, 2=ping-pong
                    repeats,  # 0=infinite, 1=once
                    96, 170, 251,  # tag RGB highlight color
                )
                _ase_chunk(fp, CHUNK_TAGS, tag_hdr, _ase_string(tag_name))
                chunks += 1

                # 3. Pivot Slice chunk (0x2022) with pivot flag (bit 1 = 2)
                slice_hdr = struct.pack("<III", 1, 2, 0)  # 1 key, flags=2 (has pivot), reserved=0
                slice_key = struct.pack("<IiiIIii", 0, 0, 0, w, h, px, py)
                _ase_chunk(fp, CHUNK_SLICE, slice_hdr, _ase_string("pivot"), slice_key)
                chunks += 1

            # Write Cel chunks (0x2005) — compressed RGBA (cel_type = 2)
            layer_images = [(0, sh_img), (1, main_img)] if has_shadow else [(0, main_img)]
            for l_idx, img in layer_images:
                if img is None:
                    continue
                rgba = img.convert("RGBA")
                if rgba.size != (w, h):
                    rgba = rgba.resize((w, h), Image.Resampling.NEAREST)
                cel_hdr = struct.pack("<HhhBHh5xHH", l_idx, 0, 0, 255, 2, 0, w, h)
                _ase_chunk(fp, CHUNK_CEL, cel_hdr, zlib.compress(rgba.tobytes()))
                chunks += 1

            frame_end = fp.tell()
            if frame_end > 0xFFFFFFFF:
                raise ValueError("Aseprite binary exceeds 32-bit file size limit.")
            dur_ms = int(durations_ms[f_idx]) if f_idx < len(durations_ms) else 125
            fp.seek(frame_start)
            fp.write(struct.pack("<IHHH2xI", frame_end - frame_start, ASE_FRAME_MAGIC, min(chunks, 0xFFFF), dur_ms, chunks))
            fp.seek(frame_end)

        total_size = fp.tell()
        first_dur = int(durations_ms[0]) if durations_ms else 125
        fp.seek(0)
        fp.write(
            struct.pack(
                "<I5HIH12xHBB92x",
                total_size,
                ASE_MAGIC,
                len(frames),
                w,
                h,
                32,  # color depth: 32 bpp RGBA
                1,   # flags: layer opacity valid
                first_dur,
                0,   # transparent index (unused in RGBA)
                1,   # pixel width ratio
                1,   # pixel height ratio
            )
        )

    return {
        "path": str(target),
        "width": w,
        "height": h,
        "frames": len(frames),
        "layers": layer_names,
        "tag": tag_name,
        "pivot": [px, py],
        "bytes": target.stat().st_size,
    }


def inspect_aseprite_file(path: Path | str) -> dict[str, Any]:
    """Parse and validate a binary `.aseprite` file, decompressing every cel to verify integrity."""
    raw = Path(path).read_bytes()
    if len(raw) < 128:
        raise ValueError("File too short to be a valid .aseprite binary.")

    file_size, magic, num_frames, w, h, bpp = struct.unpack_from("<I5H", raw, 0)
    if magic != ASE_MAGIC:
        raise ValueError(f"Invalid Aseprite magic: {hex(magic)} (expected 0xA5E0)")
    if file_size != len(raw):
        raise ValueError(f"Header file_size ({file_size}) != actual size ({len(raw)})")

    offset = 128
    layers: list[str] = []
    tags: list[dict[str, Any]] = []
    slices: list[dict[str, Any]] = []
    frame_durations: list[int] = []
    cels_decompressed = 0

    for _ in range(num_frames):
        f_bytes, f_magic, old_chunks, dur_ms, new_chunks = struct.unpack_from("<IHHH2xI", raw, offset)
        if f_magic != ASE_FRAME_MAGIC:
            raise ValueError(f"Invalid frame magic {hex(f_magic)} at offset {offset}")
        frame_durations.append(dur_ms)
        chunk_count = new_chunks if new_chunks > 0 else old_chunks
        c_pos = offset + 16
        for _ in range(chunk_count):
            c_size, c_type = struct.unpack_from("<IH", raw, c_pos)
            body = raw[c_pos + 6 : c_pos + c_size]
            if c_type == CHUNK_LAYER:
                name_len = struct.unpack_from("<H", body, 16)[0]
                layers.append(body[18 : 18 + name_len].decode("utf-8"))
            elif c_type == CHUNK_TAGS:
                tag_count = struct.unpack_from("<H", body, 0)[0]
                t_off = 10
                for _ in range(tag_count):
                    t_from, t_to, t_dir, t_rep = struct.unpack_from("<HHBH", body, t_off)
                    n_len = struct.unpack_from("<H", body, t_off + 17)[0]
                    t_name = body[t_off + 19 : t_off + 19 + n_len].decode("utf-8")
                    tags.append({"name": t_name, "from": t_from, "to": t_to, "direction": t_dir, "repeats": t_rep})
                    t_off += 19 + n_len
            elif c_type == CHUNK_SLICE:
                _, s_flags, _ = struct.unpack_from("<III", body, 0)
                n_len = struct.unpack_from("<H", body, 12)[0]
                s_name = body[14 : 14 + n_len].decode("utf-8")
                k_off = 14 + n_len
                _, sx, sy, sw, sh = struct.unpack_from("<IiiII", body, k_off)
                entry: dict[str, Any] = {"name": s_name, "rect": [sx, sy, sw, sh]}
                if s_flags & 2:
                    px, py = struct.unpack_from("<ii", body, k_off + 20)
                    entry["pivot"] = [px, py]
                slices.append(entry)
            elif c_type == CHUNK_CEL:
                cel_type = struct.unpack_from("<B", body, 7)[0]
                if cel_type == 2:  # compressed image
                    cw, ch = struct.unpack_from("<HH", body, 16)
                    pixels = zlib.decompress(body[20:])
                    expected = cw * ch * (bpp // 8)
                    if len(pixels) != expected:
                        raise ValueError(f"Decompressed cel size mismatch: {len(pixels)} != {expected}")
                    cels_decompressed += 1
            c_pos += c_size
        offset += f_bytes

    return {
        "valid": True,
        "width": w,
        "height": h,
        "bpp": bpp,
        "frames": num_frames,
        "durations_ms": frame_durations,
        "layers": layers,
        "tags": tags,
        "slices": slices,
        "cels_decompressed": cels_decompressed,
        "file_size": file_size,
    }


def write_aseprite_lua(
    frames: Sequence[Image.Image],
    durations_ms: Sequence[int],
    output_path: Path | str,
    *,
    asset_id: str,
    action: str = "idle",
    spatial: SpatialMeta | None = None,
) -> dict[str, Any]:
    """Optional ASCII-matrix Aseprite Lua script emitter compatible with legacy Aseprite CLI workflows."""
    if not frames:
        raise ValueError("Cannot emit Lua script with zero frames.")
    w, h = frames[0].size
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Map unique visible RGB colors to single ASCII characters (up to ~60 chars)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@$%^&*"
    color_to_char: dict[tuple[int, int, int, int], str] = {}
    palette_entries: list[str] = ['    ["."] = nil,']
    next_idx = 0

    lua_frames: list[str] = []
    for f_idx, frame in enumerate(frames):
        arr = np.asarray(frame.convert("RGBA"))
        rows_str: list[str] = []
        for y in range(h):
            chars: list[str] = []
            for x in range(w):
                r, g, b, a = (int(v) for v in arr[y, x])
                if a == 0:
                    chars.append(".")
                    continue
                if a < 255:
                    key = (r, g, b, a)
                    if key not in color_to_char:
                        color_to_char[key] = "S"
                        palette_entries.append(f'    ["S"] = {{ hex = "{rgb_to_hex((r, g, b))}", alpha = {a} }},')
                    chars.append(color_to_char[key])
                    continue
                key = (r, g, b, 255)
                if key not in color_to_char:
                    ch = alphabet[next_idx % len(alphabet)]
                    if ch == "S":
                        next_idx += 1
                        ch = alphabet[next_idx % len(alphabet)]
                    next_idx += 1
                    color_to_char[key] = ch
                    palette_entries.append(f'    ["{ch}"] = {{ hex = "{rgb_to_hex((r, g, b))}", alpha = 255 }},')
                chars.append(color_to_char[key])
            rows_str.append('        "' + "".join(chars) + '",')
        lua_frames.append("    {\n" + "\n".join(rows_str) + "\n    },")

    fps = max(1, round(1000 / max(1, durations_ms[0]))) if durations_ms else 8
    lua_src = "\n".join(
        [
            f"-- Generated by Pixel Forge ({w}x{h}, {len(frames)} frames @ {fps} FPS)",
            f'local asset_id = "{asset_id}"',
            f"local width, height = {w}, {h}",
            f"local frameDuration = {1.0 / fps:.6f}",
            "local sprite = Sprite(width, height, ColorMode.RGB)",
            'local layer = sprite.layers[1]; layer.name = "Main"',
            "sprite.frames[1].duration = frameDuration",
            "local PALETTE = {",
            *palette_entries,
            "}",
            "local frames_data = {",
            *lua_frames,
            "}",
            "local function renderGrid(img, gridData, pal)",
            "    for y = 1, #gridData do",
            "        local line = gridData[y]",
            "        for x = 1, #line do",
            "            local entry = pal[line:sub(x, x)]",
            "            if entry then",
            '                local h = entry.hex:gsub("#", "")',
            "                img:drawPixel(x - 1, y - 1, Color{ r=tonumber(h:sub(1,2),16), g=tonumber(h:sub(3,4),16), b=tonumber(h:sub(5,6),16), a=entry.alpha })",
            "            end",
            "        end",
            "    end",
            "end",
            "renderGrid(sprite.cels[1].image, frames_data[1], PALETTE)",
            "for i = 2, #frames_data do",
            "    local nf = sprite:newFrame(); nf.duration = frameDuration",
            "    local cel = layer:cel(i) or sprite:newCel(layer, nf)",
            "    cel.image:clear(); renderGrid(cel.image, frames_data[i], PALETTE)",
            "end",
            f'if #frames_data > 1 then local tag = sprite:newTag(1, #frames_data); tag.name = "{action}" end',
            f'sprite:saveCopyAs("{asset_id}_{action}.aseprite")',
            "",
        ]
    )
    target.write_text(lua_src, encoding="utf-8", newline="\n")
    return {"path": str(target), "colors": len(color_to_char), "frames": len(frames)}
