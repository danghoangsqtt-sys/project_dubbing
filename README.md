# <img src="assets/capcap.png" style="width: 5%; height: auto;"> CapCap

[English](README_en.md) | [ Tiếng Việt](README.md)

![Giao diện CapCap](assets/preview.JPG)

### [🎬 Demo & Hướng dẫn sử dụng](https://www.tiktok.com/@nguyenthach617/video/7674305087023369493)

**CapCap** là ứng dụng biên tập và bản địa hóa video dành cho Windows, giúp đơn giản hóa toàn bộ quy trình từ nhận diện giọng nói, dịch nội dung, lồng tiếng, chỉnh sửa hình ảnh cho đến xuất video hoàn chỉnh.

CapCap hỗ trợ tạo **phụ đề tiếng Việt và tiếng Anh**, dịch nội dung video, tạo giọng đọc bằng TTS và chỉnh sửa các lớp nội dung theo thời gian trực tiếp trên timeline.

## 🎯 Nhánh cá nhân: Trung/Anh → Việt trong 21 ngày

Nhánh này tập trung vào nhu cầu sử dụng cá nhân trên **RTX 3060 12 GB / RAM 32 GB**: video tiếng Trung hoặc tiếng Anh → **phụ đề tiếng Việt và lồng tiếng tiếng Việt** trong một project có thể lưu, mở lại và kiểm duyệt từng cue.

* **Tuần 1:** hoàn thành pipeline chính và hai smoke test Trung/Anh.
* **Tuần 2:** kiểm thử, tối ưu tài nguyên/cache và đóng RC1.
* **Tuần 3:** xác nhận chất lượng, đóng gói, kiểm tra license và viết báo cáo bằng số liệu.
* **Mặc định:** Hybrid cho dịch; media, ASR, VieNeu TTS, mix và export chạy local. Có **Offline Lock** để chặn hoàn toàn kết nối ra ngoài.
* **Ngoài mốc 21 ngày:** lip-sync, OmniVoice production, FunASR production và remote worker mở rộng.

Tài liệu thực thi: [Project Context](.viepilot/PROJECT-CONTEXT.md), [Architecture](.viepilot/ARCHITECTURE.md), [Roadmap 21 ngày](.viepilot/ROADMAP.md), [Tracker](.viepilot/TRACKER.md) và [UI Design Direction](design.md).

## ✨ Điểm nổi bật

* Quy trình xử lý trực quan theo từng bước: **Chuẩn bị → Chép lời → Dịch → TTS → Xuất video**
* Chuyển giọng nói thành văn bản với **Faster-Whisper** hoặc **SenseVoice**
* Trích xuất phụ đề có sẵn trong video bằng **OCR**
* Hỗ trợ nhiều dịch vụ dịch thuật qua Cloud/API, với **Google Translate** làm phương án dự phòng
* Hỗ trợ tạo giọng đọc đa dạng: **Piper TTS**, **Edge TTS**, **CapCut TTS** và **VieNeu TTS**
* Tính năng **Voice Cloning** (nhân bản giọng nói) và thư viện mẫu giọng đọc phong phú
* Tùy chọn nhận diện người nói (Speaker Diarization) và gán giọng đọc riêng cho từng người
* Hỗ trợ xuất trực tiếp sang **CapCut Draft** để tiếp tục hậu kỳ và chỉnh sửa nâng cao
* Timeline biên tập với nhiều loại lớp nội dung:
  * Phụ đề
  * Vùng làm mờ
  * Logo
  * Mặt nạ
  * Văn bản
  * Vùng chọn
* Hỗ trợ khóa lớp để tránh chỉnh sửa ngoài ý muốn
* **Fast Preview** giúp xem nhanh kết quả mà không cần xuất toàn bộ video
* **Tùy chọn chất lượng xuất thông minh**: Hỗ trợ nhiều profile (**Low, Medium, High, Very High**) tự động tối ưu hóa mã hóa phần cứng (NVIDIA NVENC / CPU libx264) giúp tối ưu dung lượng và tốc độ render

## 🚀 Tính năng sắp tới

CapCap vẫn đang được phát triển tích cực, với nhiều tính năng mới và cải tiến được bổ sung theo thời gian.

👉 [Xem lộ trình phát triển](https://github.com/users/notepower2k1/projects/2)

## 📚 Tài liệu

* [Hướng dẫn sử dụng](docs/how-to-use.md)
* [Yêu cầu hệ thống và tài nguyên](docs/requirements.md)
* [Công nghệ sử dụng](docs/technical-stack.md)
* [Cấu trúc dự án](docs/project-structure.md)
* [Requirements và phạm vi milestone](.viepilot/PROJECT-CONTEXT.md)
* [Kiến trúc mục tiêu](.viepilot/ARCHITECTURE.md)
* [Roadmap 21 ngày](.viepilot/ROADMAP.md)
* [Quy chuẩn phát triển](.viepilot/SYSTEM-RULES.md)

## 🛠️ Chạy từ mã nguồn

Thiết lập tái lập được với Python 3.11 và kiểm tra GPU/FFmpeg/resource được mô tả tại [Thiết lập môi trường phát triển](docs/development-setup.md).

```powershell
git clone https://github.com/notepower2k1/CapCap.git
cd CapCap

.\tools\bootstrap_python311.ps1 -Requirements local
.\.venv\Scripts\Activate.ps1
python ui/gui.py
```

Bạn chỉ cần sao chép `.env_example` thành `.env` nếu muốn cấu hình thủ công các dịch vụ dịch thuật hoặc máy chủ từ xa.

Phần lớn thiết lập của CapCap có thể được cấu hình trực tiếp ngay trong ứng dụng.

## ❤️ Ủng hộ CapCap

Nếu CapCap hữu ích với bạn, bạn có thể ủng hộ để giúp dự án tiếp tục được duy trì và phát triển.

### 🇻🇳 Ủng hộ tại Việt Nam

Quét mã QR bên dưới:

<img src="assets/qr.png" style="width: 25%; height: auto;">

### 🌍 Ủng hộ quốc tế

[![Buy Me a Coffee](assets/buymeacoffee.png)](https://buymeacoffee.com/hcaht)

Nhấp vào hình ảnh phía trên hoặc truy cập [Buy Me a Coffee](https://buymeacoffee.com/hcaht).

## 📄 Giấy phép

CapCap được phát hành theo **Apache License 2.0**.

Xem chi tiết tại [LICENSE](LICENSE).
