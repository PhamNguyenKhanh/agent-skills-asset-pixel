# 🎬 2D Pixel Art Animation & Dynamics Framework

Tài liệu này xác lập các nguyên lý hoạt họa động lực học, thời gian chuyển động (Timing), giãn cách khung hình (Spacing) và kỹ thuật bảo toàn khối lượng cho game 2D Top-Down. Mục tiêu là biến các pixel tĩnh thành các chuyển động tràn đầy sinh khí, cảm giác va đập đầm chắc (Game Feel) và loại bỏ hoàn toàn hiện tượng rung giật (Flicker / Jitter).

---

## 1. 12 Nguyên Lý Hoạt Họa Trong Không Gian Pixel (Pixel-Art Animation Principles)

### 1.1. Co Nén & Giãn Dài Bảo Toàn Thể Tích (Squash & Stretch with Mass Conservation)
*   **Định luật bảo toàn thể tích:** Khi một vật thể hữu cơ hoặc bán đàn hồi (Slime, nấm nhảy, nhân vật tiếp đất) biến dạng, tổng diện tích pixel của khối phải được bảo toàn:
    $$W_{\text{nén}} \times H_{\text{nén}} \approx W_{\text{chuẩn}} \times H_{\text{chuẩn}} \approx W_{\text{dãn}} \times H_{\text{dãn}}$$
*   *Quy tắc ứng dụng:*
    *   Khi nén dẹp (Squash tiếp đất): Chiều cao giảm $2\text{px} \rightarrow 3\text{px}$ thì bề ngang bắt buộc phình rộng thêm $2\text{px} \rightarrow 4\text{px}$.
    *   Khi vọt bay lên (Stretch đỉnh tốc độ): Bề ngang thu hẹp lại $2\text{px} \rightarrow 3\text{px}$, chiều cao kéo dài thon nhọn lên trên.
    *   **CẤM:** Vừa thu hẹp chiều cao vừa thu hẹp chiều ngang làm vật thể teo tóp như bị hút chân không.

### 1.2. Chuẩn Bị & Dự Đoán (Anticipation)
*   Trước mỗi hành động lớn (chém kiếm, phóng đạn, nhảy bổng, quái vật húc), vật thể BẮT BUỘC có **1–2 frame chuẩn bị thế ngược chiều với hướng chuyển động**:
    *   Trước khi chém tới trước: Kiếm lùi ra sau, vai hơi xoay nghiêng.
    *   Trước khi nhảy vọt lên cao: Toàn thân chùng gối hạ trọng tâm xuống sàn.
*   *Ý nghĩa Gameplay:* Giúp người chơi đọc trước đòn đánh (Telegraphing) để kịp thời né tránh hoặc phản xạ.

### 1.3. Khung Hình Xé Gió (Smear Frames & Motion Blur)
*   Tại pha vận tốc cực đại ($V_{\text{max}}$ - thường là frame thứ 2 trong đòn đánh 4 frame):
    *   Lưỡi kiếm hoặc cánh tay không vẽ chi tiết từng khớp mà biến dạng thành **Vệt vòng cung xé gió (Arc Slash / Smear)** dài và mảnh.
    *   Vệt smear sử dụng dải màu phát quang năng lượng (Trắng $\rightarrow$ Cyan $\rightarrow$ Xanh thẫm).
    *   Chuôi vũ khí hoặc khớp vai luôn khóa chặt quanh trục tâm chuyển động.

### 1.4. Quán Tính & Động Lượng Chậm Pha (Follow-Through & Overlapping Action)
*   Khi khối thân chính dừng lại, các bộ phận mềm phụ thuộc (tà áo choàng, dải ruy băng, đuôi tóc, chuông treo, dây xích) **tiếp tục chuyển động theo quán tính thêm 1–2 frame** trước khi bị giật ngược trở lại:
    *   Khung $i$: Thân dừng lại tư thế đứng (Idle).
    *   Khung $i+1$: Tà áo văng tới điểm cực đại phía trước (Overshoot).
    *   Khung $i+2$: Tà áo hồi lưu rủ xuống vị trí cân bằng (Settling).

### 1.5. Giảm Tốc Đầu & Cuối Nhịp (Slow In and Slow Out / Easing)
*   Chuyển động tự nhiên không bao giờ có vận tốc đều tăm tắp (Linear).
*   Các frame tập trung dày đặc ở hai đầu mút của quỹ đạo chuyển động (điểm đảo chiều vận tốc bằng 0), và thưa thớt ở đoạn giữa khi vật thể lướt qua với vận tốc lớn nhất.
    *   *Ví dụ con lắc đung đưa 6 frame:* Frame 1 (Cực đại Trái - dừng tích tắc) $\rightarrow$ Frame 2 (Rơi nhanh qua giữa) $\rightarrow$ Frame 3 (Lướt cực nhanh) $\rightarrow$ Frame 4 (Cực đại Phải - khựng lại) $\rightarrow$ Frame 5 (Rơi nhanh về) $\rightarrow$ Frame 6 (Qua giữa khép vòng lặp).

---

## 2. Rào Cản Chống Rung Giật (Frame-to-Frame Consistency & Anti-Flicker)

Lỗi phổ biến nhất của AI khi sinh animation là hình ảnh bị "co giật" (jitter) qua các frame do thiếu sự kiểm soát điểm neo và khối lượng.

### 2.1. Khóa Chặt Điểm Neo Trọng Tâm (Anchor Locking)
1.  **Chân đế tĩnh (Static Floor Pivot):**
    *   Đối với mọi hoạt ảnh tại chỗ (Cây rung rinh, Lò rèn cháy, Rương mở nắp, Nhân vật thở/chém đứng tại chỗ): **Tọa độ Y của đường chân đế và bóng tiếp đất BẮT BUỘC KHÓA BẤT BIẾN 100% qua toàn bộ các frame**.
    *   CẤM di dời chân đế lệch $\pm 1\text{px}$ giữa các frame liên tiếp khiến sprite nhảy tưng tưng trên màn hình.
2.  **Bản lề xoay (Hinge / Joint Pivot):**
    *   Nắp rương khi mở ngửa ra sau phải xoay quanh trục bản lề đáy nắp cố định.
    *   Cánh tay robot vung đấm phải khóa chốt tâm tại ổ trục vai.

### 2.2. Tính Nhất Quán Về Bảng Màu & Ánh Sáng (Palette & Shading Stability)
*   **Palette cố định:** Không thay đổi mã Hex của vật liệu giữa các frame (Gỗ ở frame 1 là `#85441e` thì ở frame 4 vẫn phải là `#85441e`).
*   **Specular tĩnh:** Ánh sáng môi trường đến từ góc Trên - Trái là cố định. Khi bề mặt kim loại uốn éo hoặc xoay, điểm phản quang không được trôi dạt hỗn loạn mà chỉ trượt mượt mà dọc theo diện vát đón sáng.

---

## 3. Các Phân Nhóm Hoạt Ảnh Chuẩn (Animation Archetypes)

| Nhóm Tài Nguyên | Tên Hoạt Ảnh | Số Frame Chuẩn | FPS Đề Xuất | Hành Vi Chuyển Động & Động Lực Học |
| :--- | :--- | :--- | :--- | :--- |
| **Môi Trường** | Thảo mộc rung gió | 4–6 frames | 6–8 FPS | Đỉnh ngọn lắc lư $\pm 1$–$2$px, gốc thân đứng yên. Chu kỳ lặp điều hòa đối xứng. |
| **Môi Trường** | Lửa lò rèn / Đuốc | 3–4 frames | 6–8 FPS | Ngọn lửa cuộn tịnh tiến lên trên, tách 1–2 hạt tàn lửa bay lên rồi tan biến. |
| **Môi Trường** | Cỗ máy bánh răng | 4–8 frames | 8–12 FPS | Piston thụt thò thẳng hàng; bánh răng xoay tịnh tiến đơn điệu $\theta_i = (i-1) \cdot \frac{360^\circ}{N}$. |
| **Đạo Cụ Tương Tác** | Rương mở nắp | 3–4 frames | 8 FPS | Đóng $\rightarrow$ Bật hé $\rightarrow$ Ngửa bung cực đại lộ kho báu phát sáng (OSL). |
| **Đạo Cụ Tương Tác** | Chuông reo / Đèn treo | 6–8 frames | 8 FPS | Dao động con lắc quét qua 2 phía đối diện trục tâm; bóng trên sàn trượt ngang đồng bộ. |
| **Đạo Cụ Tương Tác** | Đập vỡ (Bình / Thùng) | 4–5 frames | 12 FPS | Điểm vỡ bùng từ đáy sàn lên; mảnh văng parabol; nước/rượu đổ loang thành ellipse dẹt. |
| **Sinh Vật / Slime** | Bật nhảy & Tiếp đất | 4–6 frames | 8 FPS | Nghỉ $\rightarrow$ Nén dẹp (Squash) $\rightarrow$ Búng cao thu hẹp (Stretch) $\rightarrow$ Rơi tự do $\rightarrow$ Dẹp hoãn xung $\rightarrow$ Nghỉ. |
| **Hiệu Ứng Combat** | Vệt chém kiếm (Slash) | 4 frames | 12 FPS | Vung chuẩn bị $\rightarrow$ Smear Arc xé gió cực đại $\rightarrow$ Tan rã tia năng lượng $\rightarrow$ Hết đòn. |
| **Hiệu Ứng Combat** | Giọt bắn & Sóng nước | 4–5 frames | 8–12 FPS | Giọt rơi chạm đất $\rightarrow$ Bắn vương miện (Crown) vọt lên $\rightarrow$ Sóng loang rỗng ruột (Hollow Ripple) $\rightarrow$ Tan biến. |
