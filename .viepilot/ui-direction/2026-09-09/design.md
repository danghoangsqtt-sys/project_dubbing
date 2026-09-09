---
name: "CapCap"
description: "Windows local-media video translation and Vietnamese dubbing studio"
colors:
  primary: "#4ED0B3"
  surface: "#121B2B"
  accent: "#8AD7FF"
  error: "#FF6B6B"
  success: "#54D18B"
  warning: "#FFD400"
typography:
  fontFamily: "Segoe UI, Inter, sans-serif"
  fontSize:
    base: 14
spacing:
  base: 8
  scale: [4, 8, 12, 16, 24, 32, 48]
rounded:
  sm: 6px
  md: 10px
  lg: 14px
  full: 999px
---

# CapCap Design Direction

## Tính cách

CapCap là một bàn dựng kỹ thuật đáng tin cậy, không phải một trình tạo video “một nút bấm”. Giao diện ưu tiên khả năng nhìn thấy trạng thái, sửa từng cue và khôi phục khi một bước thất bại. Cảm giác tổng thể: **professional, dense-but-calm, privacy-aware, reviewable**.

## Ngôn ngữ thị giác

- Nền xanh đen giảm mỏi mắt khi xem video lâu; surface phân cấp bằng biên thay vì đổ bóng nặng.
- Mint là hành động chính và trạng thái đã sẵn sàng. Xanh da trời dành cho lựa chọn hoặc thông tin. Vàng chỉ cảnh báo cần xem lại; đỏ là lỗi chặn pipeline.
- Góc bo 6–14 px, tương thích với code PySide6 hiện có. Không dùng glassmorphism hoặc gradient trang trí ngoài logo/preview.
- Segoe UI là font hệ thống Windows; số liệu thời gian và đường dẫn có thể dùng monospace.

## Phân cấp tương tác

1. Hành động tạo thay đổi lớn: Generate, Regenerate voice, Export dùng primary.
2. Hành động hỗ trợ: Preview, Import SRT, Open folder dùng secondary.
3. Hành động phá hủy: Clean data, Reset chỉ dùng danger và phải xác nhận.
4. Mọi tác vụ dài có trạng thái queued/running/done/warning/error và có thể mở log.

## Quy tắc nội dung

- UI chính bằng tiếng Việt; tên engine/model giữ nguyên.
- Dùng động từ rõ: “Tạo bản dịch”, “Tạo lại giọng”, “Xuất video”.
- Phân biệt ba trường không nhập nhằng: **Bản gốc**, **Phụ đề VI**, **Lồng tiếng VI**.
- Cảnh báo phải nói cả nguyên nhân lẫn hành động tiếp theo, ví dụ: “Dài hơn cảnh 1,2 giây — rút gọn câu hoặc tăng tốc lên 1,08×”.

## Mục tiêu accessibility

- Text chính ≥ 4.5:1; màu trạng thái luôn đi cùng nhãn/icon.
- Focus ring mint 2 px; mọi thao tác cue quan trọng có đường bàn phím.
- Không dùng màu người nói làm tín hiệu duy nhất; luôn hiển thị Speaker 1/2.
