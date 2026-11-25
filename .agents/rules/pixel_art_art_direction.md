# 🎨 2D Top-Down Central Art Direction & Visual Identity Specification

Tài liệu này xác lập bản sắc thị giác trung tâm (Visual Identity) bất biến cho toàn bộ tài nguyên đồ họa trong thế giới game. Mọi asset (từ đạo cụ nhỏ nhất đến công trình lớn và quái vật) phải trông như được sinh ra từ cùng **MỘT TRÒ CHƠI DUY NHẤT**.

---

## 1. Triết Lý Ngôn Ngữ Pixel (Pixel Language)

### 1.1. Mật độ Pixel & Tỷ lệ logic (Pixel Density & Scale)
*   **Logical Pixel Scale:** Toàn bộ game vận hành ở tỷ lệ pixel gốc **1:1** (Native Pixel Resolution).
*   **TUYỆT ĐỐI CẤM MIXELS:** Không bao giờ trộn lẫn các sprite có kích thước pixel khác nhau trên cùng một khung nhìn. Một pixel trên vũ khí hay một pixel trên cây cổ thụ đều phải có kích thước thực tế bằng nhau trên lưới màn hình.
*   **Đường biên sắc nét (Hard Edges):** Không khử răng cưa mờ (anti-aliasing) bằng thuật toán làm nhòe. Pixel art đạt độ sắc nét tuyệt đối thông qua việc xếp đặt pixel thủ công có chủ đích.

### 1.2. Phân Cấp Khối Pixel (Cluster Hierarchy)
Không vẽ từng pixel lẻ tẻ lấm tấm (salt-and-pepper noise). Tư duy tạo hình bắt buộc tuân theo thứ bậc cụm khối (Cluster Hierarchy):
```text
Cụm khối lớn (Primary Mass: 60-70% diện tích)
     ↓
Cụm khối trung (Secondary Mass: 20-30% tạo nếp, vạt, diện sáng/tối)
     ↓
Điểm nhấn vi mô (Micro Accents: 5-10% đinh tán, vết nứt, specular)
```
*   **CẤM PIXEL CÔ ĐƠN (Orphan Pixels):** Không để lại pixel đơn lẻ trôi nổi một mình trừ khi đó là:
    *   Hạt bụi/tàn lửa phát quang (Embers/Particles).
    *   Đốm sáng phản quang cực điểm (Specular 1px).
    *   Giọt nước bắn rời ở frame va chạm vận tốc cao.
*   **CẤM BANDING & DITHERING TÙY TIỆN:** Không kẻ các dải màu song song đều đặn dọc theo viền khối. Chuyển dịch sắc độ phải uốn lượn theo cấu trúc mặt phẳng 3D. Cấm trải caro giả mờ (checkerboard dithering) làm bẩn bề mặt ở kích thước màn hình nhỏ.

### 1.3. Triết Lý Bo Viền (Outline Philosophy)
*   **Viền ngoài (Outer Contour):** Sử dụng viền chọn lọc (Selective Outlining). Không dùng màu đen thuần `#000000` (trừ chế độ Terraria khi được yêu cầu cụ thể). Viền ngoài luôn mang sắc độ tối nhất của vật liệu hoặc màu bóng môi trường hòa trộn (Mahogany tối `#241218`, Xanh đen cổ kính `#141824`, Tím thạch anh `#1b0e24`).
*   **Mép đón sáng (Light-Facing Rim):** Ở cạnh trên và cạnh trái đón ánh sáng chính, viền ngoài chuyển thành viền màu sáng (Rim Highlight) hoặc viền mỏng 1-step tone tối, không bao giờ viền đen đè lên mép đón nắng.
*   **Rãnh nối bên trong (Internal Crevices):** Các rãnh chia khối bên trong vật thể dùng tone tối trung bình (Mid-Shadow), sáng hơn viền bao ngoài 1-2 sắc độ để không xé vụn hình thể.

---

## 2. Hệ Thống Bảng Màu Master (Master Palette System)

Để đảm bảo 50 asset vẽ ở 50 thời điểm khác nhau vẫn hoàn toàn đồng nhất, toàn bộ pipeline sử dụng hệ thống **Palette Families** chuẩn hóa dưới đây.

### 2.1. Quy Luật Dịch Chuyển Sắc Độ (Hue-Shifting Principle)
*   **Vùng sáng (Highlights):** Luôn dịch chuyển góc màu (Hue) về phía **VÀNG / CAM / ẤM** ($+10^\circ \rightarrow +25^\circ$), đồng thời giảm nhẹ độ bão hòa (Saturation) hoặc giữ mức tươi sáng.
*   **Vùng tối (Shadows):** Luôn dịch chuyển góc màu (Hue) về phía **TÍM / XANH DƯƠNG / LẠNH** ($-15^\circ \rightarrow -35^\circ$), đồng thời tăng độ sâu (Value thấp).
*   **CẤM VALUE-ONLY SHADING:** Không bao giờ tạo bóng bằng cách chỉ giảm thanh trượt Brightness/Lightness giữ nguyên Hue. Shading không đổi Hue sẽ biến vật thể thành màu xám chì chết chóc.

### 2.2. Dải Màu Gia Đình Chuẩn (Master Palette Families)

#### A. Nền Móng & Đường Viền Chung (World Contours & Shadows)
*   `Contour Deepest` : `#140d18` (Màu viền sẫm đa dụng, tím đen trầm)
*   `Shadow Ambient`  : `#1a1226` (Bóng râm khuất sáng tổng thể)
*   `Ground Contact S`: `#100818` (Bóng tiếp xúc sàn, vẽ ở mã `S` với Alpha 130 trong sprite/engine)

#### B. Họ Gỗ & Thuộc Da (Warm Timber & Leather)
*   `Timber Deep`     : `#2b140d` (Rãnh ván, bóng kẽ gỗ)
*   `Timber Shadow`   : `#522714` (Mặt gỗ khuất sáng)
*   `Timber Mid`      : `#85441e` (Thân gỗ sồi/tuyết tùng tự nhiên)
*   `Timber Light`    : `#ba6b32` (Thớ gỗ đón sáng)
*   `Timber Highlight`: `#e89e5a` (Gờ mép vát, vết xước sáng)

#### C. Họ Đá Cổ & Gạch Lâu Đài (Ancient Stone & Masonry)
*   `Stone Deep`      : `#1b1926` (Khe nứt đá, hốc tối chân móng)
*   `Stone Shadow`    : `#343147` (Khối đá khuất sáng)
*   `Stone Mid`       : `#54506e` (Mặt đá tự nhiên trung tính)
*   `Stone Light`     : `#7d789e` (Gờ đá đón sáng)
*   `Stone Highlight` : `#aba7cf` (Chóp nhọn sứt mẻ phản quang)

#### D. Họ Kim Loại Rèn & Sắt Thép (Forged Iron & Cold Steel)
*   `Iron Deep`       : `#161a24` (Khe nối đinh tán, rãnh kim loại)
*   `Iron Shadow`     : `#2b3344` (Thép tối)
*   `Iron Mid`        : `#49576e` (Tấm thép xám chuẩn)
*   `Iron Light`      : `#75879e` (Mặt thép bóng loáng đón sáng)
*   `Iron Specular`   : `#c2d3e8` (Gờ vát phản quang mạnh)
*   `Iron White Hot`  : `#ffffff` (Đốm lóa 1-2px)

#### E. Họ Đồng Đỏ & Vàng Kim (Burnished Bronze & Gilded Gold)
*   `Gold Deep`       : `#381c08` (Rãnh khảm vàng, bóng đai đồng)
*   `Gold Shadow`     : `#6e3d0c` (Đồng khuất sáng)
*   `Gold Mid`        : `#b06f15` (Sắc độ đồng cổ / Vàng trầm)
*   `Gold Bright`     : `#e8a825` (Vàng kim rực sáng)
*   `Gold Specular`   : `#ffea6b` (Điểm lóa đỉnh vàng kim)

#### F. Họ Thảm Thực Vật & Lá Cây (Verdant Foliage & Vines)
*   `Flora Deep`      : `#0d2117` (Bóng râm tán lá rậm rạp)
*   `Flora Shadow`    : `#184227` (Tán lá dưới)
*   `Flora Mid`       : `#2a733a` (Lá xanh tươi nhiệt đới)
*   `Flora Light`     : `#4db050` (Tán trên hứng trọn nắng)
*   `Flora Sunburst`  : `#9be366` (Chồi non viền sáng)

#### G. Họ Nước & Đại Dương (Clear Water & Oceanic Depths)
*   `Water Abyss`     : `#091626` (Đáy vực sâu thẳm)
*   `Water Deep`      : `#113254` (Lớp nước sâu)
*   `Water Mid`       : `#1d5c8f` (Mặt nước hồ trong vắt)
*   `Water Light`     : `#329cd4` (Gợn sóng khúc xạ sáng)
*   `Water Foam/Crest`: `#8eedff` (Bọt sóng vỡ, bọt khí)

#### H. Họ Năng Lượng Ma Thuật & Tinh Thể (Arcane Cyan & Crystals)
*   `Arcane Deep`     : `#09242e` (Lõi chìm khuất quang)
*   `Arcane Mid`      : `#0f6b7d` (Thân tinh thể thạch anh xanh)
*   `Arcane Bright`   : `#1ce0c9` (Phát quang dạ quang rực rỡ)
*   `Arcane White Core`: `#d9ffff` (Tâm điểm nguồn năng lượng)

#### I. Họ Lửa Rực & Dung Nham (Blazing Flame & Magma)
*   `Fire Crust`      : `#400c08` (Vảy xỉ than, viền ngoài tàn khói)
*   `Fire Dark`       : `#8a1c0d` (Đỏ thẫm rìa nhiệt)
*   `Fire Mid`        : `#de4512` (Cam lửa nhiệt lượng cao)
*   `Fire Bright`     : `#f79e1e` (Vàng cam cuồn cuộn)
*   `Fire Heart`      : `#fffa7a` (Lõi vàng sáng cực nhiệt)
*   `Fire White Core` : `#ffffff` (Tâm hạt lóa trắng)

---

## 3. Mô Hình Chiếu Sáng Toàn Cầu (Global Lighting Model)

Mọi asset trong thế giới game bắt buộc tuân theo **nguồn sáng môi trường mặc định** trừ khi asset đó tự mang nguồn sáng tự thân (Self-illuminating):

```text
       ÁNH SÁNG MẶT TRỜI TOÀN CẦU (Global Sun)
       [Góc Chiếu: Trên - Trái ~10:30, Cao Độ 45°]
                       \
                        \
                         ▼
                   +-----------+
                   |  HIGHLIGHT| (Mặt Trên & Trái hứng trọn sáng)
                   |           |
                   |   MID     |
                   |           |
                   | SHADOW    | (Mặt Phải & Dưới chìm trong bóng)
                   +-----------+
                         \
                          \
                           ▼
                    BÓNG ĐỔ TRÊN SÀN (Cast Shadow)
                    (Trượt xiên dẹt về phía Dưới - Phải)
```

1.  **Hướng sáng chính (Key Light):** Góc **Trên - Trái** (Top-Left, khoảng 10:30 đến 11:00). Góc tà phương $45^\circ$.
2.  **Ánh sáng khuếch tán (Ambient Fill):** Nhẹ nhàng từ góc Dưới - Phải hắt lên với sắc thái lạnh (lấy từ bầu trời/môi trường tím xanh).
3.  **Điểm phản quang (Specular Highlights):** Luôn khóa cố định tại mép tiếp giáp Trên - Trái của các bề mặt bóng (Kim loại, Thủy tinh, Thạch). Khi vật xoay tròn, specular **KHÔNG ĐƯỢC XOAY THEO** mà đứng yên theo nguồn sáng toàn cầu.
4.  **Bóng tiếp xúc (Ambient Occlusion / Contact Shadow):** Dải 1-2 pixel sẫm màu nằm ngay tại khe tiếp giáp giữa 2 bề mặt va chạm (VD: chân đế chạm đất, nắp đậy lên miệng hòm, đai sắt ôm lấy gỗ).
