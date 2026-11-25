# 🔍 Production Asset Validation & Quality Assurance Pipeline

Tài liệu này xác lập quy trình nghiệm thu chất lượng (Quality Assurance), tiêu chuẩn kiểm thử tự động và thủ công cho mọi tài nguyên pixel art trước khi đưa vào kho game chính thức. Mọi asset bắt buộc trải qua 4 giai đoạn khép kín: **Khởi tạo $\rightarrow$ Kiểm thử $\rightarrow$ Sửa lỗi $\rightarrow$ Xuất bản**.

---

## 1. Ba Trụ Cột Nghiệm Thu (The 3 Validation Pillars)

```text
[ASSET GENERATION]
        │
        ├──▶ 1. TECHNICAL AUDIT  (Kích thước, FPS, Kênh màu, Metadata, Đường dẫn xuất)
        │
        ├──▶ 2. VISUAL AUDIT     (Silhouette, Palette, Jaggies, Banding, OSL, Specular)
        │
        └──▶ 3. ENGINE INTEGRATE (Điểm Pivot, Hitbox va chạm, Y-Sorting, Tương tác)
        │
[PRODUCTION APPROVAL & EXPORT]
```

### 1.1. Trụ Cột 1: Nghiệm Thu Kỹ Thuật (Technical Validation)
*   [ ] **Kích thước Canvas chuẩn:** Chiều rộng và cao thuộc bảng kích thước chuẩn (`16x16`, `24x24`, `32x32`, `48x48`, `64x64`, `96x96`, `128x128`).
*   [ ] **Độ dài dòng ma trận:** Tất cả các dòng chuỗi trong `frames_data` phải có độ dài chính xác bằng `width`. Số dòng phải chính xác bằng `height`.
*   [ ] **Số lượng Frame & FPS:** Frame rate cố định (`6`, `8`, `12`, `16` FPS). Không để frameDuration = 0 hoặc frame bị giật thời gian.
*   [ ] **Độ sạch kênh Alpha:** Toàn bộ vùng ngoài hình thể (`.`) phải trong suốt hoàn toàn (`Alpha = 0`). Không có đốm pixel rác trôi nổi ở 4 góc mép canvas.
*   [ ] **Đúng thư mục xuất bản:**
    *   File gốc: `output/aseprite/<name>.aseprite`
    *   Animation GIF: `output/gif/<name>.gif`
    *   Spritesheet ngang: `output/Sheet/<name>_sheet.png`
    *   Ảnh tĩnh đơn: `output/png/<name>.png` (hoặc `output/Sheet/<name>.png`)
    *   Metadata kỹ thuật: `output/metadata/<name>.json`

### 1.2. Trụ Cột 2: Nghiệm Thu Mỹ Thuật & Độ Đọc (Visual Validation)
*   [ ] **Thử nghiệm Silhouette (Bóng đen):** Khi biến toàn bộ pixel thành màu đen trên nền trắng, hình thể vật thể vẫn phải lập tức nhận diện được là gì trong vòng 3 giây.
*   [ ] **Giới hạn Palette:** Tuân thủ ngân sách màu: 1 màu viền tối + 3–4 sắc độ thân chính + 2 màu phụ kiện (+ tối đa 3 màu phát quang OSL).
*   [ ] **Không có Banding:** Không có các hàng pixel cùng màu xếp song song thẳng đuột dọc theo cạnh khối.
*   [ ] **Không có Jaggies:** Đường cong bo viền theo nhịp bước đều đặn (`1-1-2-2` hoặc `1-2-3`). Không có pixel thừa chìa ra tạo góc vuông $90^\circ$ vô lý.
*   [ ] **Nguồn sáng nhất quán:** Ánh sáng chính luôn chiếu từ góc Trên - Trái ($10:30 \rightarrow 11:00$). Điểm specular khóa tĩnh trên bề mặt kim loại/thủy tinh khi vật xoay.
*   [ ] **Bóng tiếp đất mềm mại (`S`):** Chân đế vật thể đứng trên sàn bắt buộc có bóng elip mờ mã `S` (Alpha 130) khóa chặt chân đế, cấm vật thể bay lơ lửng.

### 1.3. Trụ Cột 3: Tích Hợp Game Engine (Gameplay Integration)
*   [ ] **Điểm Pivot chuẩn xác:** Pivot nằm tại tâm tiếp đất đáy vật thể ($X = \frac{W}{2}, Y \approx H - 4$).
*   [ ] **Hộp va chạm Collision hợp lý:** Hitbox chỉ bao quanh phần chân đế tiếp xúc mặt đất (chiếm 15%–35% chiều cao). Tuyệt đối không để collision box bao phủ toàn bộ tán cây hoặc mái nhà khiến người chơi không đi lướt phía sau được.
*   [ ] **Sắp xếp lớp Y-Sorting:** Chiều cao và chân đế đảm bảo khi nhân vật đi ngang qua thì thứ tự đè lớp (Render Order) hoạt động chính xác tự nhiên.
*   [ ] **Bảo toàn khối lượng khi chuyển động:** Không có frame nào bị teo tóp diện tích đột ngột; hoạt ảnh lặp khép vòng chu kỳ mượt mà không khựng giật.

---

## 2. Tiêu Chuẩn Bảng Metadata Game Engine (`output/metadata/<name>.json`)

Mọi asset khi xuất xưởng bắt buộc đi kèm 1 file JSON chuẩn hóa theo định dạng sau:

```json
{
  "asset_id": "blacksmith_forge_64",
  "category": "environment_prop",
  "tier": "production",
  "canvas": {
    "width": 64,
    "height": 64
  },
  "animation": {
    "is_animated": true,
    "frame_count": 4,
    "fps": 8,
    "frame_duration_ms": 125,
    "loop": true,
    "tags": [
      { "name": "idle_fire", "from": 0, "to": 3, "direction": "forward" }
    ]
  },
  "spatial": {
    "pivot": { "x": 32, "y": 58 },
    "ground_footprint": { "x": 12, "y": 50, "width": 40, "height": 10 },
    "collision_box": { "x": 14, "y": 44, "width": 36, "height": 14 },
    "interaction_region": { "x": 16, "y": 54, "width": 32, "height": 10 }
  },
  "materials": ["stone", "forged_iron", "fire"],
  "palette_count": 14
}
```
