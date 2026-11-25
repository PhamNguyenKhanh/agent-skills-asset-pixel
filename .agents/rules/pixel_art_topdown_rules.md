# 🗺️ 2D Top-Down Spatial & Gameplay Integration Rules

Tài liệu này quy chuẩn hóa toàn bộ hình học không gian, góc nhìn camera, điểm neo (Pivot), vùng va chạm (Collision) và phân lớp hiển thị (Y-Sorting) cho game 2D Top-Down góc nhìn 3/4. Mọi sprite được vẽ ra không chỉ đẹp mắt mà bắt buộc phải tích hợp mượt mà vào Game Engine (Unity, Godot, Unreal, Defold, Phaser).

---

## 1. Giả Định Camera & Tỷ Lệ Chiếu Không Gian (Camera Model)

*   **Góc nhìn:** Top-Down 3/4 Oblique (Góc hạ camera khoảng $45^\circ \rightarrow 60^\circ$ so với mặt đất).
*   **Độ co ngắn trục đứng (Vertical Foreshortening):**
    *   Mặt phẳng nằm ngang (mặt sàn, nóc hòm, mặt nước) hiển thị dưới dạng **hình ellipse dẹt theo tỷ lệ trục $Y:X \approx 1:2$ hoặc nén $50\% \rightarrow 60\%$**.
    *   Mặt phẳng dựng đứng (mặt trước bức tường, thân cây, ngực nhân vật) bị nén nhẹ khoảng **$85\% \rightarrow 90\%$** so với chiều cao thực.
*   **Hướng diện (Facing / Orientation):**
    *   Mặt trước (South / South-East / South-West) là mặt lộ diện rõ nhất, nhận nhiều chi tiết nhất.
    *   Nóc/Mặt trên (Top surface) luôn lộ một dải mỏng từ 3–8px tùy chiều sâu vật thể.
    *   Mặt sau (North) chìm hoàn toàn vào khuất tầm nhìn.

---

## 2. Phân Tách 4 Vùng Biên Kỹ Thuật (The 4-Bounds Separation)

Tuyệt đối KHÔNG ĐỒNG NHẤT kích thước ảnh canvas với vùng va chạm vật lý. Một asset chuyên nghiệp bắt buộc phân biệt rõ 4 ranh giới:

```text
+------------------------------------------+  <-- 1. VISUAL BOUNDS (Toàn bộ sprite: 64x64)
|                  [Khói bay / Ngọn cây]   |
|                                          |
|                +----------------+        |
|                |  Tán cây / Mái |        |
|                +----------------+        |
|                       ||                 |
|                   [Thân cây]             |
|                       ||                 |
|             +--------------------+       |  <-- 2. COLLISION BOUNDS (Chỉ chặn ở gốc: 20x10px)
|             |###### Gốc cây #####|       |
|          ---(====================)----   |  <-- 3. GROUND CONTACT & SHADOW (Bóng tiếp đất)
|         /                            \   |
|        +------------------------------+  |  <-- 4. INTERACTION REGION (Vùng bấm "E" nhặt táo)
+------------------------------------------+
                    [x] PIVOT / ANCHOR (Tâm đáy tiếp đất: X=32, Y=58)
```

1.  **Visual Bounds (Biên thị giác):** Toàn bộ kích thước pixel nhìn thấy của sprite, bao gồm cả hiệu ứng khói, tàn lửa bay, ngọn tháp vươn cao.
2.  **Ground Footprint (Dấu chân tiếp đất):** Vùng tiếp xúc thực tế giữa đáy vật thể và mặt sàn. Luôn là hình ellipse dẹt hoặc bục bo tròn.
3.  **Collision Bounds (Biên va chạm vật lý):** Vùng hitbox chặn người chơi không thể đi xuyên qua.
    *   *Quy tắc vàng:* Đối với công trình và cây cối, Collision Box **CHỈ NẰM Ở CHÂN ĐẾ (chiếm 15%–35% chiều cao phía dưới)**. Phần thân trên và tán cây người chơi có thể đi lướt phía sau hoặc bị che khuất tự nhiên.
4.  **Interaction Region (Vùng tương tác):** Vùng bán kính kích hoạt (Action Trigger) phía trước hoặc xung quanh vật thể để người chơi mở hòm, rèn vũ khí, đọc biển báo.

---

## 3. Hệ Thống Điểm Neo & Phân Lớp Sâu (Anchor, Pivot & Y-Sorting)

### 3.1. Vị Trí Điểm Neo (Anchor / Pivot Point)
*   **Quy ước tuyệt đối:** Điểm Pivot của mọi vật thể đứng trên mặt đất (Cây, Hòm, Nhân vật, Lò rèn, Quái vật) **BẮT BUỘC ĐẶT TẠI TÂM TIẾP ĐẤT (Ground Center / Feet Center)**.
*   *Tọa độ chuẩn:* $X_{\text{pivot}} = \frac{\text{Width}}{2}$, $Y_{\text{pivot}} = \text{Height} - (\text{Độ dày mép sàn})$ (Thường cách đáy canvas 2–6px để chừa chỗ cho vạt bóng tiếp đất).
*   **Vật thể treo tường (Wall Mounts / Hanging):** Pivot đặt tại điểm đóng đinh neo trên tường ($X = \text{Center}, Y = \text{Top Anchor}$).
*   **Vũ khí / Hiệu ứng vung kiếm:** Pivot đặt tại vị trí chuôi cầm (Hilt / Grip Point).
*   **Đạn / Projectile:** Pivot đặt tại tâm điểm hình học ($X = \frac{W}{2}, Y = \frac{H}{2}$).

### 3.2. Quy Tắc Sắp Lớp Chiều Sâu (Y-Sorting / Z-Index)
Game Engine sử dụng tọa độ Y của điểm Pivot để quyết định thứ tự vẽ đè (Layering):
$$\text{Render Depth} \propto Y_{\text{pivot}}$$
*   Nếu Nhân vật có $Y_{\text{feet}} < Y_{\text{cây}}$: Nhân vật đang đứng phía sau cây $\rightarrow$ Tán cây vẽ đè lên che khuất nhân vật.
*   Nếu Nhân vật có $Y_{\text{feet}} > Y_{\text{cây}}$: Nhân vật đang đứng phía trước cây $\rightarrow$ Nhân vật vẽ đè lên gốc cây.
*   **CẤM:** Vẽ gốc cây hoặc chân tường tràn xuống quá sâu dưới điểm Pivot làm sai lệch hiển thị thứ tự bước đi của nhân vật.

---

## 4. Cao Độ Không Gian Trục Z & Bóng Đổ (Elevation & Cast Shadows)

### 4.1. Phân Biệt Cao Độ (Height / Elevation Z)
Trong không gian 2D giả 3D, khi một vật nhảy lên hoặc bay lơ lửng ở cao độ $Z$:
$$\text{Vị trí vẽ sprite} = (X_{\text{gốc}}, Y_{\text{gốc}} - Z)$$
$$\text{Vị trí bóng tiếp đất} = (X_{\text{gốc}}, Y_{\text{gốc}})$$
*   Khi slime nhảy lên cao: Bóng tiếp đất (`S`) **NẰM NGUYÊN TẠI MẶT ĐẤT** và thu nhỏ kích thước (hoặc giảm nhẹ độ mờ), thân slime tịnh tiến lên trên theo trục Y âm.
*   **CẤM:** Kéo bóng bay lơ lửng theo nhân vật lên trời.

### 4.2. Hệ Thống Bóng Đổ Top-Down 3/4
1.  **Bóng tiếp xúc (Contact Shadow):**
    *   Dày 1–2px, màu tối nhất (`#100818` / Alpha 130), nằm dính sát mép dưới cùng của vật thể.
    *   Báo hiệu trực quan: "Vật thể đang đặt vững chắc trên mặt sàn".
2.  **Bóng đổ ngả dài (Directional Cast Shadow):**
    *   Theo nguồn sáng Top-Left $\rightarrow$ Bóng đổ ngả xiên sang góc **Dưới - Phải** ($+X, +Y$).
    *   Vật thể càng cao (cột cờ, ống khói, tượng đài), bóng đổ ngả trên sàn càng dài.
    *   Bóng đổ trên sàn bị nén dẹt theo trục Y tỷ lệ $1:2$.
3.  **Vật thể nổi trên mặt nước:**
    *   Tuân thủ quy tắc Inverted Y Reflection: Không vẽ bóng tiếp xúc elip đen đặc, mà vẽ hình ảnh phản chiếu lộn ngược đầu nhạt màu dập dềnh theo sóng nước.
