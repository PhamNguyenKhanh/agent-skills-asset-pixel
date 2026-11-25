# Hướng Dẫn Sử Dụng Pixel Forge (Từ Cơ Bản Đến Nâng Cao)

Tài liệu này hướng dẫn từng bước làm chủ **Pixel Forge** — từ chạy offline 0 đồng trên máy cá nhân, kết hợp AI đa nhà cung cấp (Gemini, OpenAI, OpenRouter, xAI, fal.ai), cho đến kiểm định QA 2 tầng, chỉnh sửa khóa byte RGBA, và tích hợp trọn gói vào **Unity 6 (2D Pixel Perfect)**.

---

## Mục Lục
1. [Phần 1 — Cơ bản: Cài đặt & chạy Offline 0 đồng](#phần-1--cơ-bản-cài-đặt--chạy-offline-0-đồng)
2. [Phần 2 — Trung cấp: Cấu hình AI Multi-Provider & chọn chế độ tối ưu](#phần-2--trung-cấp-cấu-hình-ai-multi-provider--chọn-chế-độ-tối-ưu)
3. [Phần 3 — Tạo Animation từ ảnh Asset (3-Track Pipeline)](#phần-3--tạo-animation-từ-ảnh-asset-3-track-pipeline)
4. [Phần 4 — Chỉnh sửa cục bộ (RGBA-Protected Inpaint) & Tiện ích bảng màu](#phần-4--chỉnh-sửa-cục-bộ-rgba-protected-inpaint--tiện-ích-bảng-màu)
5. [Phần 5 — Kiểm định chất lượng QA 2 tầng & Đọc lỗi](#phần-5--kiểm-định-chất-lượng-qa-2-tầng--đọc-lỗi)
6. [Phần 6 — Xuất xưởng PNG, GIF, `.aseprite` & Tích hợp Unity 6](#phần-6--xuất-xưởng-png-gif-aseprite--tích-hợp-unity-6)
7. [Phần 7 — Nâng cao: Dùng Slash Commands & Python API cho Batch Pipeline](#phần-7--nâng-cao-dùng-slash-commands--python-api-cho-batch-pipeline)

---

## Phần 1 — Cơ bản: Cài đặt & chạy Offline 0 đồng

### 1.1. Cài đặt môi trường
Máy chỉ cần **Python 3.10+** và các gói nhẹ (`Pillow`, `numpy`, `httpx`, `click`, `rich`). Không bắt buộc cài Aseprite CLI.

```powershell
# Tại thư mục gốc repo
pip install -e .

# Kiểm tra hệ thống
pixelforge doctor
```
*(Nếu chưa cài editable, bạn luôn có thể chạy `$env:PYTHONPATH="src"; python -m pixel_forge ...`)*

### 1.2. Xem danh sách Style Presets & 11 Bảng màu có sẵn
```powershell
pixelforge presets
pixelforge palette list
```

### 1.3. Chuyển ảnh thô / ảnh phác thảo thành Pixel Art (Mode `direct` — Offline)
Khi bạn đã có một bức vẽ phác thảo, icon thô, hoặc ảnh tạo sẵn từ công cụ khác (`sketch.png`), dùng `--mode direct`:

```powershell
pixelforge asset "cozy oak treasure chest" `
  --rough path\to\sketch.png `
  --size 32x32 `
  --preset topdown-34-stardew `
  --mode direct `
  --palette master_topdown `
  --ground-shadow `
  --formats png,gif,aseprite,unity `
  --out output/my_chest
```

Pipeline sẽ tự động:
1. Chuẩn hóa hướng EXIF & không gian màu sRGB (`image_io.py`).
2. Tự đo màu nền dọc biên ảnh và tách nền sạch 0 viền (`matte.py`).
3. Tự phát hiện lưới pixel ảo ("unzoom") nếu ảnh đầu vào là pixel giả phóng to (`grid_unzoom.py`).
4. Căn khít vào đúng lưới `32x32` bằng nearest-neighbor, ánh xạ về bảng màu `master_topdown`, bo viền 1px chọn lọc, thêm bóng tiếp đất `S` (`alpha=130`).
5. Xuất cùng lúc **PNG + Spritesheet + GIF + `.aseprite` + Unity 6 bundle + Review Sheet + HTML Viewer**.

### 1.4. Xem trước trực quan không cần cài phần mềm
- Mở `output/my_chest/preview/my_chest_static_review.png` để xem phóng đại 4× trên nền caro.
- Mở `output/my_chest/preview/sprite_sheet.html` trực tiếp trong trình duyệt (Chrome/Edge) rồi kéo file trong `sheet/` và `metadata/*.atlas.json` vào để xem animation chạy thật.

---

## Phần 2 — Trung cấp: Cấu hình AI Multi-Provider & chọn chế độ tối ưu

### 2.1. Cấu hình API Key an toàn (không bao giờ lưu key trong repo!)
Bạn có 2 cách (biến môi trường luôn được ưu tiên hơn file cấu hình):

**Cách A — Biến môi trường (PowerShell):**
```powershell
$env:GEMINI_API_KEY = "AIza..."
# Hoặc: OPENAI_API_KEY, OPENROUTER_API_KEY, XAI_API_KEY, FAL_KEY
```

**Cách B — File cấu hình người dùng ngoài dự án:**
- Windows: `%APPDATA%\pixel-forge\config.json`
- macOS / Linux: `~/.config/pixel-forge/config.json`

```json
{
  "GEMINI_API_KEY": "AIza...",
  "OPENROUTER_API_KEY": "sk-or-...",
  "XAI_API_KEY": "xai-...",
  "providers": {
    "order": {
      "image": ["gemini", "openrouter", "openai", "xai", "fal"],
      "video": ["xai", "fal"]
    }
  },
  "models": {
    "gemini": { "image": "gemini-2.5-flash-image" },
    "openrouter": { "image": "openai/gpt-image-1" }
  }
}
```

Kiểm tra lại (chỉ hiển thị `YES`/`no`, **tuyệt đối không lộ key**):
```powershell
pixelforge doctor
```

### 2.2. Kiểm soát chi phí với `--dry-run` & `--budget-usd`
Trước khi chạy tác vụ tốn phí API, **luôn xem trước kế hoạch** bằng `--dry-run`:

```powershell
pixelforge asset "silver knight with blue cape" --size 48x48 --preset side-view-hibit --dry-run --json
```
Khi chạy thật, bạn có thể đặt trần ngân sách (mọi lệnh gọi được ghi vào `.forge/ledger.jsonl`):
```powershell
pixelforge asset "silver knight with blue cape" --size 48x48 --preset side-view-hibit --budget-usd 0.50 --max-calls 5
```

### 2.3. Khi nào chọn mode nào cho Asset?

| Mode | Nguyên lý | Phù hợp nhất khi |
|---|---|---|
| `ai-pixel-look` | AI vẽ theo mô tả/ảnh thô → tự phát hiện lưới pixel ảo (**unzoom**) → fit canvas → remap palette | Icon 16×16–64×64, đạo cụ Top-Down 3/4, phong cách Stardew/Terraria/Retro |
| `hibit` | AI vẽ hình phẳng cel-shaded không viền → học bảng màu k-means++ → **majority-vote downscale** → tự sinh viền hòa sắc | Nhân vật 48×48–96×96 cần đường nét siêu sạch kiểu Hi-bit hiện đại |
| `direct` | 100% Python xác định, không gọi AI | Chuyển ảnh sketch/PNG có sẵn thành pixel art sạch hoặc xử lý hàng loạt 0 đồng |

---

## Phần 3 — Tạo Animation từ ảnh Asset (3-Track Pipeline)

Từ một file ảnh asset chuẩn (`hero.png` hoặc `chest.png`), bạn tạo animation bằng lệnh `pixelforge animate`:

### 3.1. Track C — `procedural` (Offline, 0 đồng, chuẩn vật lý 2D)
Hỗ trợ sẵn các mẫu động học: `idle` (thở 1px khóa chân), `walk`/`run` (bước nhún), `jump` (quỹ đạo parabol + thu nhỏ bóng + Squash khi tiếp đất), `attack` (tạo đà + vệt chém Smear Arc), `sway` (sóng gió tịnh tiến), `fire` (ngọn lửa + hạt tàn bay tách rời), `hurt` (giật lùi + hit-flash), `open` (mở nắp rương phát sáng).

```powershell
pixelforge animate output/my_chest/png/my_chest.png "slowly open chest lid revealing bright gold" `
  --action open --frames 6 --fps 8 --playback once --track procedural `
  --lock-bottom-rows 3 --out output/chest_open
```
> **Mẹo Art Director:** Dùng `--lock-bottom-rows N` để khóa cứng phần chân đế / bóng tiếp đất `S` giống nhau 100% giữa mọi khung hình (Static Zone Lock).

### 3.2. Track A — `sheet` (AI Image-to-Image Sprite Sheet)
Tự tạo lưới hướng dẫn (`layout_guide.png`), chọn màu nền an toàn (`quiet_key_color` không trùng màu sprite), gọi AI vẽ trọn bộ khung hình, tự cắt ô, căn chỉnh trục chân và khóa về đúng bảng màu gốc:

```powershell
pixelforge animate hero.png "hero casting blue arcane spell raising staff" `
  --action cast --frames 6 --fps 10 --playback once --track sheet `
  --preset topdown-34-stardew --out output/hero_cast
```

### 3.3. Track B — `video` (Image-to-Video → Pixel Lattice Snap)
Phóng đại nguyên lần sprite gốc lên nền chroma-key an toàn → gọi model video (`xai` hoặc `fal`) → dùng **FFmpeg** tách frame → đọc ngược từng frame về **đúng lưới pixel 1× ban đầu** → khóa màu bằng **OKLab Colour Lock** → tự động chọn vòng lặp mượt nhất (`find_best_loop`) hoặc cắt đoạn chết cho đòn đánh (`retime_oneshot`):

```powershell
pixelforge animate hero.png "hero running steadily to the right in place" `
  --action run --frames 8 --fps 12 --playback loop --track video `
  --preset side-view-hibit --out output/hero_run
```

### 3.4. Lật hướng có kiểm soát (Explicit Mirroring)
Để sinh hướng đối diện (`west` từ `east`), dùng `--mirror horizontal`. Hệ thống tự đo độ đối xứng: nếu sprite bất đối xứng (ví dụ cầm kiếm tay phải, khiên tay trái), nó sẽ **cảnh báo và không tự ý lật** trừ khi bạn xác nhận `--allow-asymmetric-mirror`.

---

## Phần 4 — Chỉnh sửa cục bộ (RGBA-Protected Inpaint) & Tiện ích bảng màu

### 4.1. Sửa 1 vùng nhỏ mà không làm hỏng phần còn lại (`inpaint`)
Tạo 1 ảnh mask đen-trắng cùng kích thước với sprite (`#FFFFFF` = vùng cho phép sửa, `#000000` = vùng khóa cứng):

```powershell
pixelforge inpaint "change red cape into royal blue cape with gold trim" `
  --source hero.png --mask cape_mask.png --out output/hero_blue
```
Pixel Forge ghép kết quả bằng mã Python và **kiểm chứng ở cấp từng byte RGBA**: đảm bảo `changed_outside_mask == 0`.

### 4.2. Quản lý bảng màu & Texture nền
```powershell
# Trích xuất bảng màu 16 màu từ một sprite mẫu để dùng thống nhất cho cả game
pixelforge palette extract hero.png --max-colors 16 --out my_game_palette.json

# Ánh xạ một sprite khác sang đúng bảng màu của game
pixelforge palette remap npc.png --palette my_game_palette.json --policy strict --out npc_matched.png

# Tạo bầu trời gradient Bayer dither & tile đất/cỏ liền mạch không vết nối
pixelforge dither --size 64x64 --color1 "#1d2b53" --color2 "#29adff" --matrix 4 --out sky.png
pixelforge noise --size 64x64 --palette master_topdown --scale 8 --octaves 2 --out terrain_tile.png
pixelforge audit terrain_tile.png --check-seams
```

---

## Phần 5 — Kiểm định chất lượng QA 2 tầng & Đọc lỗi

```powershell
# Kiểm định 1 ảnh đơn
pixelforge audit output/my_chest/png/my_chest.png --preset topdown-34-stardew

# Kiểm định cả bộ animation (tự kiểm tra frame delta & static bottom rows)
pixelforge audit output/chest_open --preset topdown-34-stardew --static-bottom-rows 3 --json
```

### Ý nghĩa 2 tầng QA:
- **Tier 1 — Universal Hard Gates (Bắt buộc PASS, fail sẽ trả exit code 1):**
  - `binary_alpha`: Không có pixel bán trong suốt (anti-aliasing). Riêng các preset Top-Down 3/4 cho phép đúng giá trị `alpha=130` cho bóng tiếp đất `S`.
  - `grid_alignment`: Kích thước chia hết cho bước lưới của preset.
  - `palette`: Số màu ≤ `max_colors` (và kiểm tra cấm `#000000` trên preset Stardew/Hibit).
  - `orphan_pixels`: Không có pixel rác cô lập (0 hàng xóm 8 hướng).
  - `key_fringe`: Tỉ lệ tàn dư viền chroma-key ngoài biên ≤ 2%.
- **Tier 2 — Style & Perspective Gates (Cảnh báo mỹ thuật theo Preset):**
  - `banding`: Cảnh báo các dải màu chạy song song tạo bậc thang giả.
  - `jaggies`: Cảnh báo pixel lồi góc 90° trên đường cong.
  - `ground_alignment`: Cảnh báo vật thể Top-Down bị vẽ lơ lửng xa mép dưới.
  - `tile_seams` (khi bật `--check-seams`): Đo sai số màu mép Trái-Phải & Trên-Dưới.

---

## Phần 6 — Xuất xưởng PNG, GIF, `.aseprite` & Tích hợp Unity 6

### 6.1. Xuất file `.aseprite` nhị phân thuần Python (Không cần cài Aseprite CLI)
Mỗi lần xuất với `--formats ...,aseprite`, Pixel Forge tạo file `.aseprite` chuẩn đặc tả nhị phân chính thức (`0xA5E0`):
- Tự động tách riêng layer `Shadow` (nếu có bóng bán trong suốt `S`) và `Main`.
- Ghi đầy đủ **Animation Tag** (tên action, chiều `forward` / `ping_pong`, số lần lặp) và **Slice `pivot`** ở đúng tọa độ pixel.
- Kiểm tra file bất kỳ lúc nào:
  ```powershell
  pixelforge inspect-aseprite output/chest_open/aseprite/chest_open_open.aseprite --json
  ```
- Nếu bạn muốn có thêm file kịch bản Lua để chỉnh tay trong Aseprite CLI, chỉ cần thêm `,lua` vào `--formats`.

### 6.2. Nhập gói Unity 6 tự động (`PixelForgeImporter.cs`)
1. Copy thư mục `output/<asset_id>/unity/<asset_id>/` vào trong dự án Unity tại `Assets/PixelForge/<asset_id>/`.
2. Đảm bảo Unity đã cài gói **`com.unity.2d.sprite`** (2D Sprite).
3. Trong Unity Project Window, chọn file `PixelForge.job.json` → bấm menu **Assets > Pixel Forge > Import Bundle**.
4. Script C# sẽ tự động:
   - Đặt `FilterMode.Point`, tắt Mipmaps, `Compression = Uncompressed`, `SpriteMeshType.FullRect`, đúng `PixelsPerUnit`.
   - Cắt Sprite Sheet bằng `ISpriteEditorDataProvider` (có kiểm tra an toàn bắt buộc `ISpriteFrameEditCapability`).
   - Đặt `SpriteAlignment.Custom` tại tọa độ nguyên pixel (tránh lệch 0.5px gây rung hình).
   - Tạo sẵn `AnimationClip` (kèm `AnimationEvent` như `hit`, `footstep_left`, `land`), `AnimatorController`, và `Prefab` trong thư mục `Generated/`.

### 6.3. Checklist Camera Pixel Perfect trong Unity 6
- **Dự án URP**: Gắn component `UnityEngine.Rendering.Universal.PixelPerfectCamera` (có sẵn trong URP — **không cài** gói `com.unity.2d.pixel-perfect`).
- **Dự án Built-in**: Cài `com.unity.2d.pixel-perfect` và gắn `UnityEngine.U2D.PixelPerfectCamera`.
- Tắt Anti-Aliasing (`Quality Settings > Anti Aliasing = Disabled`), đặt Camera `allowMSAA = false`, `allowHDR = false`.
- Chọn Reference Resolution chia hết nguyên cho 1080p/4K: **`320×180`** (an toàn nhất), `480×270`, hoặc `640×360`.

---

## Phần 7 — Nâng cao: Dùng Slash Commands & Python API cho Batch Pipeline

### 7.1. Gọi nhanh bằng Slash Commands khi làm việc với AI Agent
Trong Antigravity IDE (hoặc Claude Code / Codex), bạn chỉ cần gõ trực tiếp:
- `/pf-asset vẽ rương gỗ viền vàng 32x32 phong cách Stardew từ sketch.png`
- `/pf-animate làm animation mở nắp rương 6 frame 8fps từ output/chest/png/chest.png`
- `/pf-audit kiểm tra toàn bộ sprite trong output/chest_open theo chuẩn topdown-34-stardew`
- `/pf-inpaint đổi áo choàng sang màu xanh dương cho hero.png theo cape_mask.png`
- `/pf-export đóng gói thư mục frames/ sang PNG, GIF, .aseprite và Unity PPU 32`
- `/pf-unity kiểm tra và đóng gói asset để kéo vào Unity 6 URP`
- `/pf-doctor kiểm tra API keys và tổng chi phí đã dùng`

### 7.2. Tự động hóa hàng loạt bằng Python API
Bạn có thể import trực tiếp `pixel_forge` trong script Python của mình để sinh cả bộ hàng chục asset/animation nhất quán bảng màu:

```python
from pathlib import Path
from pixel_forge.core.spec import AssetSpec, AnimationSpec, ExportSpec
from pixel_forge.providers.router import MediaRouter
from pixel_forge.pixelize.pipeline import create_asset
from pixel_forge.animate.pipeline import create_animation
from pixel_forge.export.bundle import export_bundle

router = MediaRouter(offline=True)  # hoặc MediaRouter(route="auto", budget_usd=2.0)

# 1. Tạo asset từ ảnh thô
asset_spec = AssetSpec(
    asset_id="forest_slime",
    brief="cute emerald forest slime monster",
    width=32,
    height=32,
    preset="topdown-34-stardew",
    mode="direct",
)
asset_res = create_asset(asset_spec, router, Path("output/slime"), rough_image=Path("slime_sketch.png"))

# 2. Xuất asset tĩnh
export_bundle([asset_res.image], Path("output/slime"), asset_id="forest_slime", action="static")

# 3. Tạo hàng loạt hành động (idle, walk, jump, hurt) giữ nguyên bảng màu gốc
master_png = Path("output/slime/png/forest_slime.png")
for action, frames, playback in [("idle", 4, "loop"), ("walk", 6, "loop"), ("jump", 6, "once"), ("hurt", 4, "once")]:
    anim_spec = AnimationSpec(
        asset_id="forest_slime",
        action=action,
        brief=f"slime {action}",
        frame_count=frames,
        fps=8,
        playback=playback,
        track="procedural",
        preset="topdown-34-stardew",
    )
    anim_res = create_animation(master_png, anim_spec, router, Path(f"output/slime_{action}"))
    export_bundle(
        anim_res.frames,
        Path(f"output/slime_{action}"),
        asset_id="forest_slime",
        action=action,
        fps=8,
        playback=playback,
        frame_metas=anim_res.frame_metas,
        export_spec=ExportSpec(formats=("png", "gif", "aseprite", "unity"), pixels_per_unit=32),
    )
```
