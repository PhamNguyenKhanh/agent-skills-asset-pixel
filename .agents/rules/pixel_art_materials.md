# 🧱 16 Core Pixel Art Game Materials Specification

Tài liệu này định nghĩa hệ thống ngôn ngữ vật liệu tái sử dụng cho 16 loại chất liệu cơ bản trong thế giới game 2D Top-Down. Mục tiêu là giúp AI nhận diện và diễn tả chất cảm chuẩn xác, dễ đọc ở kích thước pixel game mà không sa đà vào chủ nghĩa hiện thực vụn vặt.

---

## 1. Gỗ (Wood / Timber)
*   **Sắc độ cơ bản:** Nâu hạt dẻ, sồi vàng ấm, tuyết tùng trầm (`#2b140d` $\rightarrow$ `#ba6b32` $\rightarrow$ `#e89e5a`).
*   **Hành vi bóng (Shadow):** Bóng rãnh ván sẫm màu, tụ lại ở các mắt gỗ và khe tiếp giáp đinh tán.
*   **Hành vi sáng (Highlight):** Vệt sáng mảnh 1px chạy dọc theo thớ gỗ đón nắng; gờ vát cạnh ván sáng rõ.
*   **Mật độ vân (Texture Density):** Thấp đến trung bình. Ván ngang dùng dải 3–5px, cột đứng dùng dải 2–4px.
*   **Mẫu pixel đặc trưng:** Dải màu liên tục đan xen rãnh rãnh (VD: `A A B A A`), thỉnh thoảng có mắt gỗ chữ U hoặc V (`# # V # #`). CẤM chấm dăm lấm tấm ngẫu nhiên.
*   **Hoạt họa:** Cố định, không biến dạng dẻo; khi vỡ gãy bung ra các dăm gỗ sắc nhọn hình tam giác.

---

## 2. Đá (Stone & Ancient Masonry)
*   **Sắc độ cơ bản:** Xám hoa cương, đá tím cổ kính, phiến đá rêu phong (`#1b1926` $\rightarrow$ `#54506e` $\rightarrow$ `#aba7cf`).
*   **Hành vi bóng:** Bóng thô ráp, gãy góc dứt khoát tại các mép nứt và mạch vữa.
*   **Hành vi sáng:** Đốm sáng đứt đoạn tại các gờ nhô sứt mẻ (chisel chip).
*   **Mật độ vân:** Trung bình. Khối đá chia thành các mảng diện phẳng vuông vắn.
*   **Mẫu pixel đặc trưng:** Bậc thang góc $90^\circ$ hoặc đường zigzag biểu thị vết nứt nứt nẻ; khe vữa tối chia các viên đá so le.
*   **Hoạt họa:** Không co giãn. Khi rung chuyển rơi bụi cát 1px; khi vỡ nứt toác theo đường rãnh có sẵn.

---

## 3. Kim Loại (Metal - Forged Iron, Steel, Bronze)
*   **Sắc độ cơ bản:** Thép xám xanh lạnh (`#161a24` $\rightarrow$ `#49576e` $\rightarrow$ `#ffffff`) hoặc Đồng hun ấm (`#381c08` $\rightarrow$ `#b06f15` $\rightarrow$ `#ffea6b`).
*   **Hành vi bóng:** Chuyển biến sắc độ cực gắt từ tối sang sáng, tương phản biên độ cao (High Dynamic Range).
*   **Hành vi sáng (Specular):** Vệt Highlight trắng/vàng kim chói lóa sắc bén 1–2px tại mép vát lưỡi kiếm, đỉnh đinh tán hoặc chóp chỏm cung vòm.
*   **Mật độ vân:** Rất mịn và phẳng phiu. Bề mặt kim loại không có hạt nhám.
*   **Mẫu pixel đặc trưng:** Dải phản quang kéo dài theo đường lưỡi; đốm trắng đơn lập tại góc vuông đón sáng.
*   **Hoạt họa:** Phản quang giữ nguyên vị trí (Static Specular) khi vật xoay; khi va chạm sinh tia lửa văng (1-frame spark).

---

## 4. Thủy Tinh (Glass / Phial)
*   **Sắc độ cơ bản:** Xanh lơ trong suốt, viền xám lấp lánh (`#0e2a38` $\rightarrow$ `#2bb8d4` $\rightarrow$ `#ffffff`).
*   **Hành vi bóng:** Không có bóng tối đặc ở thân giữa (vì cho ánh sáng xuyên qua), bóng tập trung ở độ dày thành bình và đáy bình.
*   **Hành vi sáng:** Vệt cong highlight màu trắng tinh khiết (`#ffffff`) vắt chéo qua toàn bộ thành bình, đè lên cả phần chất lỏng bên trong.
*   **Mật độ vân:** Trơn láng tuyệt đối.
*   **Mẫu pixel đặc trưng:** Đường viền mảnh 1px, vệt lóa cong hình lưỡi liềm bo theo hình cầu/trụ.
*   **Hoạt họa:** Khi vỡ bắn ra các mảnh kính mảnh sắc nhọn hình tam giác trong suốt.

---

## 5. Vải Vóc (Cloth / Cape / Banners)
*   **Sắc độ cơ bản:** Đỏ thẫm, xanh hoàng gia, trắng ngà (`#240a18` $\rightarrow$ `#8c234a` $\rightarrow$ `#f28dae`).
*   **Hành vi bóng:** Bóng lượn sóng hình chữ U hoặc V mềm mại giữa các nếp gấp (folds).
*   **Hành vi sáng:** Tán sáng mềm trải dài dọc theo đỉnh sóng vải, không có đốm specular sắc gắt.
*   **Mật độ vân:** Thấp. Tạo hình hoàn toàn bằng nếp gập khối lớn.
*   **Mẫu pixel đặc trưng:** Đỉnh sóng sáng lượn cong $\rightarrow$ rãnh nếp gấp tối $\rightarrow$ đỉnh sóng tiếp theo. Mép đuôi vải duỗi tự nhiên theo chiều gió.
*   **Hoạt họa:** Sóng tịnh tiến từ gốc ra ngọn ($X_{\text{sóng}}(i) < X_{\text{sóng}}(i+1)$). Gốc vải rủ võng nhẹ 1–2px do trọng lực trước khi đón gió.

---

## 6. Thuộc Da (Leather / Straps)
*   **Sắc độ cơ bản:** Nâu da bò, hổ phách trầm (`#331509` $\rightarrow$ `#7d3e1b` $\rightarrow$ `#d68b4f`).
*   **Hành vi bóng:** Tối ở các mép viền may và nếp nhăn nơi bị uốn cong (khớp gối, đai thắt lưng).
*   **Hành vi sáng:** Điểm sáng ấm, mềm, độ bóng mờ (matte finish), không chói như kim loại.
*   **Mật độ vân:** Rất mịn, điểm xuyết đường chỉ khâu hoặc khuy bấm kim loại.
*   **Mẫu pixel đặc trưng:** Các dải 2–3px bo tròn ôm lấy thân thể hoặc cán kiếm; nếp gấp dẹt 1px.
*   **Hoạt họa:** Uốn cong đàn hồi nhẹ nhưng bảo toàn độ dày đai da.

---

## 7. Tinh Thể & Đá Quý (Crystal & Gems)
*   **Sắc độ cơ bản:** Xanh ngọc, tím thạch anh, đỏ ruby (`#09242e` $\rightarrow$ `#1ce0c9` $\rightarrow$ `#d9ffff`).
*   **Hành vi bóng:** Các mặt khuất sáng chìm vào màu bão hòa đậm; không dùng màu đen đục.
*   **Hành vi sáng:** Mặt đón sáng lóa màu pastel sáng; đỉnh nhọn có hạt specular sao trắng 1px.
*   **Mật độ vân:** Hình học đa diện sắc bén (Faceted geometry). Cạnh vát thẳng tắp dứt khoát.
*   **Mẫu pixel đặc trưng:** Các mặt phẳng tam giác/ngũ giác giao nhau tại đường gờ 1px rõ ràng.
*   **Hoạt họa:** Phát xung nhịp thở (Pulsing glow), tỏa hạt bụi ma thuật (Arcane motes) bay lơ lửng rồi tan biến.

---

## 8. Thảm Thực Vật & Lá Cây (Plants & Foliage)
*   **Sắc độ cơ bản:** Xanh rêu nhiệt đới, xanh ngọc bích (`#0d2117` $\rightarrow$ `#2a733a` $\rightarrow$ `#9be366`).
*   **Hành vi bóng:** Tán lá tầng dưới chìm trong bóng mát rậm rạp; có bóng râm hắt xuống thân cành.
*   **Hành vi sáng:** Đỉnh các cụm tán lá hướng lên trời đón nắng ngả sắc vàng chanh tươi rói.
*   **Mật độ vân:** Cụm khối đám mây (Cloud clusters). CẤM tỉa từng chiếc lá 1px tạo nhiễu hạt.
*   **Mẫu pixel đặc trưng:** Cụm vòm bo tròn hình nấm/đám mây chồng lớp lên nhau; cuống lá uốn lượn tự nhiên.
*   **Hoạt họa:** Đung đưa chậm rãi (Gentle sway) trễ pha giữa gốc và ngọn; rụng 1-2 chiếc lá xoay chao đảo.

---

## 9. Nước (Water & Liquids)
*   **Sắc độ cơ bản:** Xanh lam trong vắt, xanh ngọc đại dương (`#091626` $\rightarrow$ `#1d5c8f` $\rightarrow$ `#8eedff`).
*   **Hành vi bóng:** Tối dần theo độ sâu lòng bồn/đáy hồ; bóng râm thành bồn đổ nghiêng xuống mặt nước.
*   **Hành vi sáng:** Gợn sóng phản chiếu khúc xạ ánh sáng (Caustics); bọt mép nước màu trắng sáng.
*   **Mật độ vân:** Các dải cong nằm ngang rỗng ruột (Hollow Ripples dày 1px).
*   **Mẫu pixel đặc trưng:** Ellipse đồng tâm dẹt tỷ lệ $1:2$ rỗng ở giữa để lộ màu nước nền.
*   **Hoạt họa:** Sóng gợn tịnh tiến nở rộng dần ra ngoài rồi tiêu biến; phản chiếu mặt nước bị biến dạng zigzag $\pm 1$px.

---

## 10. Lửa (Fire & Combustion)
*   **Sắc độ cơ bản:** Đỏ thẫm viền $\rightarrow$ Cam rực $\rightarrow$ Vàng chói $\rightarrow$ Lõi trắng cực nhiệt (`#400c08` $\rightarrow$ `#de4512` $\rightarrow$ `#fffa7a` $\rightarrow$ `#ffffff`).
*   **Hành vi bóng:** LỬA LÀ NGUỒN SÁNG TỰ THÂN - KHÔNG CÓ SHADING TỐI ĐEN. Vùng ngoài cùng là màu đỏ ấm rực, không dùng viền đen `#000000`.
*   **Hành vi sáng:** Lõi trung tâm luôn đạt màu trắng chói nhiệt lượng cao nhất (`#ffffff`).
*   **Mật độ vân:** Khối lỏng bốc lên cuồn cuộn vuốt nhọn ở đỉnh.
*   **Mẫu pixel đặc trưng:** Hình ngọn đuốc/giọt nước lộn ngược, cuộn xoắn tịnh tiến lên trên.
*   **Hoạt họa:** Tách rời 1–3 hạt tàn lửa nhỏ bay vọt lên cao rồi phân rã; diện tích ngọn lửa co giãn 20% mỗi frame.

---

## 11. Băng Giá (Ice & Frost)
*   **Sắc độ cơ bản:** Xanh băng tuyết, lam phấn trắng (`#122338` $\rightarrow$ `#4da8da` $\rightarrow$ `#e8f7ff`).
*   **Hành vi bóng:** Xanh tím lạnh trong trẻo, phản chiếu ánh sáng môi trường.
*   **Hành vi sáng:** Mặt trên đóng lớp sương muối trắng mịn; cạnh vát phản chiếu ánh sáng sắc lẹm.
*   **Mật độ vân:** Mảng khối sắc nhọn kết hợp các đường nứt gãy bên trong lòng băng.
*   **Mẫu pixel đặc trưng:** Các góc nhọn $45^\circ$ và $60^\circ$; rãnh nứt mảnh 1px chạy ziczac.
*   **Hoạt họa:** Tĩnh lặng kiên cố; khi tan chảy nhỏ giọt nước chậm; khi vỡ toác thành các mảnh băng vụn tinh thể.

---

## 12. Chất Thạch (Slime & Gelatinous Mass)
*   **Sắc độ cơ bản:** Xanh ngọc phát quang, tím độc dược (`#180529` $\rightarrow$ `#0ea9cc` $\rightarrow$ `#ffffff`).
*   **Hành vi bóng:** Trong mờ (Translucent) - ánh sáng xuyên thấu tạo vùng rực sáng ở phía đối diện bóng đổ.
*   **Hành vi sáng:** Điểm lóa trắng cong ở mặt đón sáng; có thể nhìn thấy lõi ma thuật (Core) phát sáng bên trong.
*   **Mật độ vân:** Mềm mại, trơn bóng, vòm cung hoàn hảo.
*   **Mẫu pixel đặc trưng:** Khối bán cầu dẹt; lõi hình giọt nước hoặc viên ngọc chìm bên trong.
*   **Hoạt họa:** Biến dạng đàn hồi cực mạnh (Squash & Stretch: Nén dẹp khi tiếp đất $\rightarrow$ Co dãn thon dài khi vọt lên cao), nhưng bảo toàn thể tích khối.

---

## 13. Năng Lượng Ma Thuật (Magical Energy & Spells)
*   **Sắc độ cơ bản:** Tím hồ quang, vàng thần thánh, cyan năng lượng (`#200a30` $\rightarrow$ `#ca5cf5` $\rightarrow$ `#ffffff`).
*   **Hành vi bóng:** Không có bóng tối; viền ngoài cùng là vầng hào quang (Aura halo) bão hòa cao.
*   **Hành vi sáng:** Lõi hạt photon màu trắng nguyên chất, viền ngoài hắt sáng đổi màu (OSL Bleed) lên vật cản lân cận.
*   **Mật độ vân:** Vòng xoáy ma trận năng lượng vô định hình hoặc tia sét rẽ nhánh.
*   **Mẫu pixel đặc trưng:** Vệt chém bán nguyệt dẹt (Smear Arc), vòng tròn rune cổ, chùm tia năng lượng vuốt nhọn.
*   **Hoạt họa:** Tần số dao động cao (FPS nhanh 12–16), biến dạng xé gió chớp nhoáng (1–2 frames).

---

## 14. Xương & Ngà (Bone & Ivory)
*   **Sắc độ cơ bản:** Vàng tro, trắng ngà cổ kính, nâu đất mục (`#2b221b` $\rightarrow$ `#8f806d` $\rightarrow$ `#f2ede4`).
*   **Hành vi bóng:** Nâu đất ấm chìm trong các hốc rỗng (mắt sọ, tủy xương, rãnh khớp).
*   **Hành vi sáng:** Trắng ngà mờ (Matte bone white), các gờ sọ và sống mũi nhô sáng rõ ràng.
*   **Mật độ vân:** Bề mặt rạn nứt chân chim nhẹ, mòn vẹt tự nhiên.
*   **Mẫu pixel đặc trưng:** Hình cầu đôi ở đầu khớp xương, vòm tròn rỗng ở hốc mắt.
*   **Hoạt họa:** Cứng nhắc, khớp nối quay quanh ổ khớp; khi gãy vỡ toác thành các mảnh vụn hình que.

---

## 15. Đất Mẹ & Bùn Lầy (Dirt & Mud)
*   **Sắc độ cơ bản:** Nâu bùn sẫm, đất sét ẩm ướt (`#24150e` $\rightarrow$ `#5c3722` $\rightarrow$ `#9c6947`).
*   **Hành vi bóng:** Tối mùn, không phản quang, hút sáng hoàn toàn.
*   **Hành vi sáng:** Đốm đất khô xước nhẹ ở mặt trên gò đất; nếu là bùn ướt có thêm đốm lóa specular 1px nước đọng.
*   **Mật độ vân:** Thô ráp, lồi lõm hữu cơ tự nhiên.
*   **Mẫu pixel đặc trưng:** Các gò đất xếp tầng so le; hạt sỏi nhỏ 2x2px chìm trong nền đất.
*   **Hoạt họa:** Bắn bùn văng dẹt khi dẫm đạp; lún nén theo bước chân.

---

## 16. Cát Sa Mạc (Sand & Dunes)
*   **Sắc độ cơ bản:** Vàng cát cháy, be sa mạc ấm áp (`#422915` $\rightarrow$ `#b8863b` $\rightarrow$ `#f0d38d`).
*   **Hành vi bóng:** Bóng râm thoai thoải uốn theo sườn gợn sóng cồn cát (Dune ridges).
*   **Hành vi sáng:** Dải sáng mịn màng chạy dài dọc theo sống lưng cồn cát.
*   **Mật độ vân:** Sóng cát song song uốn lượn mềm mại. Tuyệt đối không rải chấm hạt mè li ti.
*   **Mẫu pixel đặc trưng:** Đường cong gợn sóng bước nhịp `1-2-3-2-1` phân chia mặt đón nắng và mặt khuất gió.
*   **Hoạt họa:** Bào mòn và cuộn bay theo chiều gió (Windward erosion); bụi cát mờ bốc lên khi có luồng xung kích.
