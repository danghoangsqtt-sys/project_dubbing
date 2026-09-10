# Workspace CapCap

Workspace là màn hình làm việc chính sau khi mở hoặc tạo project. Bố cục giữ phần điều khiển ở bên trái và khu vực xem trước/timeline ở bên phải để người dùng theo dõi pipeline mà không rời khỏi nội dung đang biên tập.

## Điều hướng và hành động

Thanh đầu trang có bốn điểm đến ổn định:

- **Studio**: quay về cấu hình media và chạy pipeline.
- **Bản dịch**: mở phần ngôn ngữ để kiểm tra đầu vào và bản dịch.
- **Lồng tiếng**: mở cấu hình giọng đọc.
- **Tài nguyên**: mở Resource Manager để kiểm tra model, binary và trạng thái sẵn sàng.

Các hành động chính gồm **Xem nhanh**, **Tạo tiếp toàn bộ** và **Xuất**. Menu **Thêm** giữ các thao tác ít dùng hơn như xuất SRT nguồn, xuất SRT tiếng Việt, dọn project và cài đặt.

## Năm giai đoạn

Thanh quy trình luôn hiển thị năm giai đoạn với tổng trọng số 100%:

| Giai đoạn | Trọng số | Dữ liệu xác định trạng thái |
|---|---:|---|
| Chuẩn bị media | 20% | Video nguồn và bước `extract_audio` |
| Chép lời | 20% | Segment nguồn hoặc artifact transcript |
| Dịch & kiểm duyệt | 24% | `translate_raw`, segment dịch và cờ QA |
| Tạo giọng | 18% | `generate_tts`, `mix_audio` và artifact âm thanh |
| Trộn & xuất | 18% | Bước export và artifact video cuối |

Mỗi hàng dùng cả chữ và màu, với các trạng thái: **Chờ**, **Đang chạy**, **Cần duyệt**, **Xong**, **Bỏ qua**, **Đã dừng** hoặc **Lỗi**. Giai đoạn đang chạy đóng góp một nửa trọng số để phần trăm tổng thể phản ánh tiến độ nhưng không báo hoàn tất sớm.

Chế độ chỉ xuất phụ đề có thể đánh dấu TTS là **Bỏ qua**. Đây là trạng thái hoàn tất có chủ ý, nên project vẫn đạt 100% khi video/SRT đã xuất thành công.

## Tiến độ, nhật ký và dừng tác vụ

- **Mở tiến độ** hiện lại hộp tiến độ đang chạy. Việc ẩn hộp thoại không dừng bộ đếm thời gian hoặc worker.
- **Nhật ký** mở vùng log runtime để xem thông báo, lỗi và quyết định fallback.
- **Dừng tác vụ** yêu cầu worker dừng hợp tác, yêu cầu QThread ngắt, chờ có giới hạn và giữ nguyên các bước/artifact đã hoàn tất.
- Khi một bước bị dừng hoặc lỗi, **Tiếp tục** xuất hiện. Lần chạy kế tiếp đọc `ProjectState` đã lưu và tái sử dụng artifact còn hợp lệ.

Luồng dừng thông thường không dùng `QThread.terminate()`. Nếu worker cần thêm thời gian giải phóng tài nguyên, tín hiệu hoàn tất của worker tiếp tục chịu trách nhiệm dọn dẹp.

## Xác minh không cần GPU/mạng

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m unittest tests.test_workspace_ui -v
```

Bộ kiểm thử xác minh ánh xạ năm giai đoạn, phần trăm, điều hướng, trạng thái tiếp tục, dừng hợp tác, lưu trạng thái lỗi và khả năng ẩn/mở lại hộp tiến độ. Các fixture không tải model, không gọi dịch vụ mạng và không yêu cầu GPU.
