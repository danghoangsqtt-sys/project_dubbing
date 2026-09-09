# Đóng góp cho CapCap

Đây là dự án cá nhân nhưng issue và pull request có phạm vi rõ ràng vẫn được chào đón.

## Thiết lập

Yêu cầu chính: Windows 10/11, Python 3.11, FFmpeg/ffprobe và các resource/model được khai báo trong ứng dụng.

```powershell
git clone https://github.com/danghoangsqtt-sys/project_dubbing.git
cd project_dubbing
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-local.txt
python ui/gui.py
```

Không đưa `.env`, API key, video riêng tư, voice reference, model weight hoặc output/cache lớn vào Git.

## Quy trình

1. Đọc `.viepilot/AI-GUIDE.md`, `TRACKER.md`, task hiện tại trong `ROADMAP.md` và `SYSTEM-RULES.md`.
2. Với thay đổi UI, đọc root `design.md` và trang tương ứng trong UI Direction.
3. Tạo nhánh `<type>/<short-description>` từ `main`.
4. Thực hiện một thay đổi có phạm vi, thêm test/evidence phù hợp.
5. Chạy các verification commands của task/phase.
6. Cập nhật changelog, contract hoặc tài liệu nếu hành vi/boundary thay đổi.

## Commit và pull request

Theo Conventional Commits, ví dụ:

```text
feat(tts): synthesize from independent dubbing text
fix(translate): preserve segment ids across provider batches
test(state): cover atomic project migration
docs(report): record day 14 benchmark limits
```

PR phải nêu: vấn đề, thay đổi, test/evidence, ảnh UI nếu có, tác động privacy/resource/license và cách rollback.

## Cổng chất lượng

- Không làm mất `original_text`, `subtitle_vi`, `dubbing_vi` hoặc chỉnh sửa đã xác nhận.
- Không gọi mạng khi Offline Lock bật.
- Không chặn Qt main thread; không truy cập widget từ worker.
- Không tạo cache hit khi provenance thay đổi hoặc audio/output không hợp lệ.
- Không thêm model/voice/binary thiếu nguồn, revision, checksum và license.
- Không đưa lip-sync/OmniVoice production hoặc refactor lớn vào milestone 21 ngày.

Chi tiết đầy đủ: [.viepilot/SYSTEM-RULES.md](.viepilot/SYSTEM-RULES.md).

## Attribution

Giữ nguyên copyright/license notice của upstream và dependency. Mã GPL không được ghép trực tiếp vào lõi Apache. Voice cloning/reference audio cần quyền sử dụng rõ ràng.

Liên hệ: `danghoang.sqtt@gmail.com` hoặc mở issue tại repository cá nhân.
