# 📋 Production Asset Specification & Quality Tiers Standard

Tài liệu này chuẩn hóa quy trình chuyển đổi mọi yêu cầu bằng ngôn ngữ tự nhiên (Prompt) thành **Bản Đặc Tả Kỹ Thuật Chính Xác (Asset Technical Specification)** trước khi bắt đầu tạo hình. Đây là cầu nối giữa khâu Ý Tưởng (Concept) và khâu Lập Trình Sinh Mã (Lua Generation).

---

## 1. Mẫu Bản Đặc Tả Kỹ Thuật Chuẩn (Asset Specification Template)

Trước khi viết bất kỳ dòng mã Lua hay ma trận ký tự nào, AI BẮT BUỘC biên soạn bản đặc tả kỹ thuật theo mẫu sau:

```yaml
Asset ID: "blacksmith_forge_64"
Display Name: "Lò Rèn Thợ Rèn Khổng Lồ"
Category: "environment_prop"         # [environment | environment_prop | character | weapon | combat_effect | ui]
Quality Tier: "production"          # [draft | game_ready | production | hero]
Purpose: "Điểm chế tạo vũ khí của người chơi trong làng"

Dimensions:
  Canvas: [64, 64]                  # [Width, Height]
  Logical Scale: "1:1"              # Chuẩn mật độ không mixels
  Frame Count: 4
  FPS: 8
  Frame Duration: 0.125             # Giây (1.0 / FPS)
  Loop Mode: "looping"              # [looping | one_shot | ping_pong]

Spatial & Game Engine Integration:
  Perspective: "Top-Down 3/4 Oblique (~45° pitch, South facing)"
  Anchor / Pivot: [32, 58]          # [X, Y] - Tâm đáy tiếp xúc sàn
  Ground Footprint:
    Shape: "flattened_ellipse"
    Bounds: { x: 12, y: 50, w: 40, h: 10 }
  Collision Footprint:              # Vùng chặn nhân vật đi xuyên qua
    Bounds: { x: 14, y: 44, w: 36, h: 14 }
  Interaction Region:               # Vùng bấm 'E' để tương tác (phía trước lò)
    Bounds: { x: 16, y: 54, w: 32, h: 10 }
  Render Layer: "Y-Sort"            # Depth sắp xếp theo Y của Pivot

Aesthetic & Materials:
  Art Style: "FreeStyle"            # [FreeStyle (Hue-shifting) | Stardew (Warm soft) | Terraria (High contrast dark)]
  Master Palette Families:
    - "Forged Iron & Cold Steel"    # Thân ống khói & mái che
    - "Castle / Dungeon Stone"      # Gạch nung & đá bệ lò
    - "Blazing Flame & Magma"       # Ngọn lửa & than hồng phát sáng
    - "World Contours & Shadows"    # Viền contour #140d18 & bóng S
  Material Breakdown:
    - Primary: "Stone & Masonry" (Thân lò gạch nung đỏ sẫm)
    - Secondary: "Forged Iron" (Mái chụp hút khói đinh tán)
    - Dynamic: "Fire & Combustion" (Ngọn lửa bốc cuồn cuộn)
  Lighting & Shading:
    - Global Light: "Top-Left (10:30, 45°)"
    - Ambient Shadow: "Cool purple cast to bottom-right"
    - Self-Illumination (OSL): "Ánh lửa hắt sáng cam/đỏ lên thành lò và sàn xung quanh"

Animation Dynamic:
  Phases:
    - Frame 1: "Lửa bốc cao trung bình, cuộn nhẹ sang trái, than hồng đỏ rực"
    - Frame 2: "Lửa bùng sáng cực đại, 2 hạt tàn lửa 1px bay tách rời lên cao"
    - Frame 3: "Ngọn lửa xẹp nhẹ, tàn lửa bay lên tan biến, rực lõi trắng"
    - Frame 4: "Hồi vị ngọn lửa chuẩn bị lặp chu kỳ mượt mà"
  Physics Behaviors: ["Fluid flame buoyancy", "Ember particle dissipation", "Static specular on metal hood"]

Exports:
  Formats: [".aseprite", ".gif", "_sheet.png", ".json"]
  Output Paths:
    - "output/aseprite/blacksmith_forge_64.aseprite"
    - "output/gif/blacksmith_forge_64.gif"
    - "output/Sheet/blacksmith_forge_64_sheet.png"
    - "output/metadata/blacksmith_forge_64.json"
```

---

## 2. 4 Tầng Chất Lượng Tài Nguyên (Quality Tiers)

Không phải mọi tài nguyên đều cần số lượng frame và độ chi tiết khổng lồ như nhau. AI cần lựa chọn tầng chất lượng phù hợp với vai trò của vật thể:

### 2.1. Tầng Nháp (Draft - Concept Asset)
*   **Mục đích:** Kiểm tra hình thể, tỷ lệ tương quan với nhân vật, silhouette tổng quát.
*   **Đặc điểm:** 1–2 frame tĩnh hoặc chuyển động thô. Palette 3–4 màu cơ bản. Không có OSL phức tạp.
*   **Thời gian thực thi:** Cực nhanh.

### 2.2. Tầng Game-Ready (Gameplay Asset Tiêu Chuẩn)
*   **Mục đích:** Đưa vào gameplay thực tế cho các vật thể phụ (hàng rào, hòn đá, bụi cỏ, thùng gỗ, biển báo).
*   **Đặc điểm:** Đúng tỷ lệ lưới, sạch bóng jaggies, bo góc chuẩn, bóng tiếp đất (`S`) chính xác, va chạm Collision Box chuẩn xác.
*   **Số frame:** 1 frame tĩnh hoặc 3–4 frame lặp đơn giản.

### 2.3. Tầng Sản Xuất (Production - Chuyên Nghiệp Hoàn Chỉnh)
*   **Mục đích:** Các đạo cụ tương tác chính, quái vật thông thường, vũ khí, hiệu ứng kỹ năng.
*   **Đặc điểm:** Đầy đủ dải màu Master Palette (5–7 sắc độ), Hue-shifting rõ nét, OSL hắt sáng mềm mại, bóng đổ ngả sàn, bảo toàn thể tích khi chuyển động, file JSON metadata hoàn chỉnh.
*   **Số frame:** 4–8 frames, animation mượt mà có Anticipation và Follow-through.

### 2.4. Tầng Hero Asset (Tài Nguyên Điểm Nhấn / Boss / Công Trình Đỉnh Cao)
*   **Mục đích:** Nhân vật chính, Boss, Công trình biểu tượng trung tâm (Lò rèn thần thoại, Tháp pháp sư, Cây đại thụ thế giới).
*   **Đặc điểm:** Kích thước lớn ($48\times 48 \rightarrow 64\times 64+$), phối hợp nhiều vật liệu tương phản (Đá rêu + Kim loại mạ vàng + Tinh thể phát quang), hạt ma thuật bay phân rã, chuyển động nhiều lớp (Multi-layered animation).
*   **Số frame:** 6–12 frames hoặc nhiều chu kỳ (Idle, Attack, Damaged).

---

## 3. Tiêu Chuẩn Kích Thước Lưới Theo Phân Nhóm (Grid Sizes)

Tuyệt đối KHÔNG chọn kích thước canvas ngẫu nhiên (như 37x41 hay 53x53). Bắt buộc sử dụng các kích thước chuẩn theo bảng sau:

| Kích Thước Lưới | Nhóm Tài Nguyên Đại Diện | Ví Dụ Cụ Thể |
| :--- | :--- | :--- |
| **`16x16`** | Vật phẩm nhặt, Icon UI, Hạt projectile, Đạn ma thuật | Đồng tiền, lọ thuốc nhỏ, phi tiêu, quả mọng |
| **`24x24`** | Trang bị cá nhân, Bẫy sàn, Đạo cụ rất nhỏ | Nhẫn, chìa khóa, dao găm, nấm độc, bẫy chông |
| **`32x32`** | Đạo cụ vừa, Vũ khí cận chiến, NPC nhỏ, Hiệu ứng va chạm | Thùng gỗ, bình thuốc lớn, kiếm dài, đuốc tường, giọt axit |
| **`48x48`** | Nhân vật tiêu chuẩn, Quái vật, Đạo cụ lớn, Rương báu | Hiệp sĩ, Slime ma thuật, Rương vàng, Cột cờ, Chuông đồng, Đài phun nước |
| **`64x64`** | Công trình, Cây cối cổ thụ, Cỗ máy cơ khí, Quái vật Boss | Lò rèn blacksmith, Cây cổ thụ xoắn, Cỗ máy hơi nước, Cổng ma thuật |
| **`96x96` – `128x128`** | Công trình khổng lồ, Rồng/Boss kích thước lớn | Lâu đài, Tàu chiến hải tặc, Hang rồng cổ |
