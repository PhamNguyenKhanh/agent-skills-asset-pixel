# ⚠️ Danh Mục Lỗi Ngớ Ngẩn Đã Biết & Cách Phòng Tránh

Tài liệu này là **"Bộ Nhớ Tập Thể"** — danh sách các lỗi thực tế đã xảy ra trong quá trình sinh tài nguyên. Mọi AI sinh asset **BẮT BUỘC** đọc tài liệu này và tự kiểm tra danh sách trước khi xuất bản bất kỳ ma trận khung hình nào.

---

## NHÓM 1 — Lỗi Cấu Trúc Tĩnh (Static Structure Mistakes)

### ❌ M-001: Silhouette Không Nhận Diện Được
**Triệu chứng:** Biến asset thành bóng đen vẫn không đọc được là vật thể gì trong 3 giây.
**Nguyên nhân thường gặp:** Thêm quá nhiều chi tiết nhỏ, thiếu hình khối chủ đạo to rõ ràng.
**Phòng tránh:**
- Trước khi vẽ chi tiết, vẽ khối Primary Mass chiếm 60–70% canvas với 1 màu đặc.
- Tự hỏi: *"Nếu tôi chỉ nhìn bóng đen này, tôi có ngay lập tức nghĩ đến [tên vật thể] không?"*
- Đặc biệt: Lò rèn phải có hình chữ nhật đứng rõ + miệng lò tối + mái chụp khói ở trên.

### ❌ M-002: Góc Nhìn Không Phải Top-Down 3/4
**Triệu chứng:** Asset trông như nhìn thẳng từ bên cạnh (Side View) hoặc từ trên xuống hoàn toàn (Pure Top View).
**Nguyên nhân:** Quên nén trục Y, vẽ mặt đứng phẳng dẹt không có chiều sâu.
**Phòng tránh:**
- Top-Down 3/4 = bạn thấy **mặt đứng phía trước** (chiều cao đầy đủ) + **mặt trên nén dẹt** (khoảng 30–40% chiều rộng).
- Nắp hòm, mái lò, mặt bàn làm việc PHẢI được vẽ dạng hình thang dẹt ở phía trên vật thể.
- Kiểm tra: Có thấy "độ dày" của mặt trên vật thể không? Nếu không có → sai góc nhìn.

### ❌ M-003: Pixel Cluster Bẩn (Dirty Clusters)
**Triệu chứng:** Asset nhìn mờ, lấm tấm, không rõ nét khi zoom ra.
**Nguyên nhân:** Dùng các pixel đơn lẻ rải rác như dithering; banding dải màu song song đều đặn.
**Phòng tránh:**
- Mỗi vùng màu phải là **khối liền mạch** (ít nhất 2×2 pixel), không phải lưa thưa pixel đơn.
- Chỉ pixel đơn 1px được phép khi: Specular 1px, tàn lửa/hạt bay, giọt nước.
- Tự test: Zoom ra 100% native và nhìn 30cm. Asset có rõ hình thể không?

### ❌ M-004: Đá và Kim Loại Trông Giống Nhau
**Triệu chứng:** Không phân biệt được vùng nào là đá, vùng nào là sắt thép.
**Nguyên nhân:** Dùng cùng một dải màu cho cả hai vật liệu, thiếu specular cho kim loại.
**Phòng tránh:**
- **Đá:** Tone xám-tím lạnh (`Stone` family), bề mặt nhám KHÔNG có specular, rãnh nứt gợn.
- **Kim loại:** Tone xanh xám lạnh (`Iron` family), PHẢI có specular sáng 1–2px cố định hướng Trên-Trái, bề mặt phẳng trơn.
- Hai họ màu KHÔNG ĐƯỢC chia sẻ bất kỳ mã hex nào.

### ❌ M-005: Vật Thể Bay Lơ Lửng (Floating Object)
**Triệu chứng:** Vật thể không chạm đất — không có bóng tiếp đất `S`, không có chân đế.
**Nguyên nhân:** Quên vẽ bóng ellipse mờ `S` ở các dòng dưới cùng canvas.
**Phòng tránh:**
- Dòng cuối cùng của canvas (Y = height-1 và Y = height-2) PHẢI chứa các ký tự `S` tạo bóng ellipse.
- Bóng `S` phải có hình elip dẹt, không phải đường thẳng ngang.

---

## NHÓM 2 — Lỗi Hoạt Họa (Animation Mistakes)

### ❌ M-006: Cấu Trúc Tĩnh Bị Thay Đổi Giữa Các Frame
**Triệu chứng:** Tường đá, mái kim loại, thân lò bị "rung" giữa các frame dù không có lý do động lực học.
**Nguyên nhân:** Copy-paste ma trận không đồng nhất, chỉnh sửa lỗi ở một frame mà quên cập nhật frame khác.
**Phòng tránh:**
- Tách rõ 2 hệ thống: `STATIC_LAYER` (copy y hệt qua tất cả frame) và `DYNAMIC_LAYER` (chỉ phần này thay đổi).
- Workflow bắt buộc:
  1. Vẽ Frame 1 hoàn chỉnh
  2. Copy toàn bộ Frame 1 → paste làm Frame 2, 3, 4
  3. Chỉ chỉnh sửa vùng dynamic (lửa, sóng, ánh sáng OSL)
- Kiểm tra: So sánh pixel-by-pixel vùng static giữa Frame 1 và Frame 4. Phải hoàn toàn giống nhau.

### ❌ M-007: Lửa Không Tạo Cảm Giác Lửa (Static Fire)
**Triệu chứng:** 4 frame lửa trông như ảnh đứng yên — không cảm giác bốc cháy.
**Nguyên nhân:** Thay đổi quá nhỏ (<5% diện tích) hoặc chỉ đổi màu mà không đổi hình.
**Phòng tránh:**
- Mỗi frame lửa PHẢI thay đổi ít nhất 15–20% số pixel trong vùng lửa.
- Ngọn lửa phải thay đổi **cả hình dạng (shape)** lẫn **vị trí đỉnh** (apex).
- Chu kỳ lửa 4 frame: (1) Trung bình → (2) Bùng cao → (3) Xẹp rung → (4) Hồi phục.
- Màu sắc lõi lửa phải thay đổi: frame bùng sáng có lõi trắng `#ffffff`, frame tắt bớt không có lõi trắng.
- Tàn lửa `ember` 1px PHẢI xuất hiện và biến mất qua các frame.

### ❌ M-008: Ánh Sáng OSL Lửa Không Hắt Màu Xuống Sàn
**Triệu chứng:** Lửa cháy nhưng thành lò và sàn xung quanh vẫn màu xám lạnh hoàn toàn.
**Nguyên nhân:** Quên áp dụng OSL (Object-Space Lighting / Color Bleed) từ nguồn sáng tự thân.
**Phòng tránh:**
- Các pixel tiếp giáp ngay với vùng lửa PHẢI được tô màu cam/đỏ nhạt (OSL blend):
  - Thành đá ngay cạnh lò: thêm 2–4px viền màu `#8a1c0d` hoặc `#de4512` mờ.
  - Sàn phía trước miệng lò: phải có dải màu cam ấm `#6b3010` to `#3d1808`.
- OSL yếu dần theo khoảng cách: Cạnh lò sáng nhất → xa hơn → tối dần.
- Kiểm tra: Che vùng lửa lại, phần thành lò vẫn phải trông "ấm" hơn stone bình thường.

### ❌ M-009: Bóng Tiếp Đất Bị Thay Đổi Vị Trí Giữa Frame
**Triệu chứng:** Bóng `S` "nhảy" hoặc "di chuyển" giữa các frame gây rung giật.
**Nguyên nhân:** Copy bóng không đồng nhất về tọa độ Y giữa các frame.
**Phòng tránh:**
- Bóng `S` của vật tĩnh (lò rèn, cây, cột) phải có tọa độ Y TUYỆT ĐỐI KHÔNG đổi.
- Chỉ bóng của vật chuyển động (con lắc, bóng nẩy) mới được di chuyển đồng bộ với vật.

---

## NHÓM 3 — Lỗi Kỹ Thuật Lua (Technical Lua Mistakes)

### ❌ M-010: Dòng Ma Trận Sai Độ Dài
**Triệu chứng:** Asset bị méo, lệch, co giãn kỳ lạ khi render.
**Nguyên nhân:** Một hoặc nhiều dòng trong `frames_data` có độ dài ≠ `width` (thêm hoặc thiếu ký tự).
**Phòng tránh — KIỂM TRA BẮT BUỘC trước khi finalize:**
```
Với canvas 48x48: Mỗi dòng PHẢI có đúng 48 ký tự.
Đếm tay dòng đầu tiên và dòng cuối cùng của mỗi frame.
Chạy: python python/validate_asset.py scripts/<name>.lua
```

### ❌ M-011: Ký Tự Trong Ma Trận Chưa Định Nghĩa Trong PALETTE
**Triệu chứng:** Script lỗi khi render; pixel bị transparent hoặc màu sai.
**Nguyên nhân:** Dùng ký tự mới trong ma trận nhưng quên thêm vào bảng `PALETTE`.
**Phòng tránh:**
- Xác định trước toàn bộ ký tự sẽ dùng, định nghĩa hết trong `PALETTE` trước khi điền ma trận.
- Mỗi lần thêm ký tự mới vào ma trận, ngay lập tức thêm entry tương ứng vào `PALETTE`.

### ❌ M-012: Frame Count Không Khớp
**Triệu chứng:** Animation bị cắt ngắn hoặc lặp dư frame trống.
**Nguyên nhân:** `frames_data` có N phần tử nhưng code render chỉ tạo N-1 frame, hoặc ngược lại.
**Phòng tránh:**
- Khai báo `local frameCount = #frames_data` và dùng biến này nhất quán trong toàn script.
- Luôn dùng vòng lặp `for i = 2, #frames_data do` để thêm frame tự động.

### ❌ M-013: File Xuất Bị Đặt Tên Sai
**Triệu chứng:** File output tồn tại nhưng không khớp với asset_id → validate_asset.py báo MISSING.
**Nguyên nhân:** Hard-code tên file thay vì dùng biến `asset_id`.
**Phòng tránh:**
- LUÔN dùng: `sprite:saveCopyAs("output/gif/" .. asset_id .. ".gif")`
- KHÔNG bao giờ: `sprite:saveCopyAs("output/gif/blacksmith_forge_48.gif")` (hard-coded).

---

## NHÓM 4 — Lỗi Chất Lượng Mỹ Thuật (Visual Quality Mistakes)

### ❌ M-014: Viền Contour Màu Đen Thuần #000000
**Triệu chứng:** Asset trông "flat", không hài hòa với nền game, viền quá cứng.
**Nguyên nhân:** Dùng `#000000` làm màu viền thay vì tím đen trầm của Master Palette.
**Phòng tránh:**
- Màu viền mặc định PHẢI là `#140d18` (Contour Deepest).
- Ngoại lệ DUY NHẤT: Style Terraria khi được yêu cầu cụ thể.

### ❌ M-015: Value-Only Shading (Không Hue-Shifting)
**Triệu chứng:** Bóng tối trông như đổ thêm màu xám lên trên màu gốc — vật thể trông "chết".
**Nguyên nhân:** Chỉ giảm brightness giữ nguyên hue khi tạo shadow.
**Phòng tránh:**
- Shadow của bất kỳ màu nào PHẢI dịch hue về phía tím/xanh lạnh ($-15° → -35°$).
- Highlight PHẢI dịch hue về phía vàng/cam ấm ($+10° → +25°$).
- Kiểm tra: Mở eyedropper tại vùng sáng nhất và tối nhất — nếu cùng một hue → sai.

### ❌ M-016: Tỷ Lệ Không Gian Sai (Wrong Scale Proportions)
**Triệu chứng:** Cái đinh tán to bằng cánh cửa; lò rèn bé hơn cái xô nước.
**Nguyên nhân:** Không có mental model về scale tương đối giữa các chi tiết.
**Phòng tránh:**
- Trong canvas 48x48 FreeStyle, nhân vật người cao khoảng 36–40px.
- Đinh tán: 1–2px. Chốt cửa: 2–3px. Cửa sổ: 6–10px. Cổng lớn: 20–30px.
- Specular highlight: TỐI ĐA 2px. Không bao giờ 4px trở lên.

---

## CHECKLIST TỰ KIỂM TRA TRƯỚC KHI SUBMIT (Pre-Submit Checklist)

Trước khi nộp bất kỳ ma trận hoàn chỉnh nào, AI phải tự trả lời 10 câu hỏi sau. Nếu bất kỳ câu nào trả lời "Không" → BẮT BUỘC sửa trước khi tiếp tục.

| # | Câu Hỏi Kiểm Tra | Tiêu Chuẩn Pass |
|---|-----------------|-----------------|
| 1 | Nhìn silhouette bóng đen, có nhận ra ngay vật thể trong 3 giây không? | ✅ Có |
| 2 | Góc nhìn có đúng Top-Down 3/4 không (thấy cả mặt đứng + mặt trên dẹt)? | ✅ Có |
| 3 | Pixel cluster có sạch (không banding, không orphan pixel)? | ✅ Không có lỗi |
| 4 | Đá và kim loại có khác biệt rõ ràng (màu, specular, texture)? | ✅ Khác biệt |
| 5 | Lửa có thật sự tạo cảm giác bốc cháy (≥15% thay đổi/frame)? | ✅ Có thay đổi |
| 6 | OSL có hắt ánh cam/đỏ vào thành lò và sàn xung quanh lửa không? | ✅ Có OSL |
| 7 | Bóng tiếp đất `S` có cố định ở cùng vị trí qua tất cả frame không? | ✅ Cố định |
| 8 | Cấu trúc tĩnh (thân lò, mái, thành đá) có pixel-identical qua frame không? | ✅ Identical |
| 9 | Tất cả dòng ma trận có đúng `width` ký tự, đủ `height` dòng không? | ✅ Đúng kích thước |
| 10 | Tất cả ký tự trong ma trận có entry tương ứng trong `PALETTE` không? | ✅ Đầy đủ |
