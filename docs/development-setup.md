# Thiết lập môi trường phát triển CapCap trên Windows

## Mục tiêu

Môi trường chuẩn của milestone là CPython 3.11 trong `.venv` tại repository. Python 3.14 hệ thống không được dùng cho pipeline vì các wheel AI/media chưa đồng đều. Dependency/model được pin hoàn chỉnh ở Task 2.5; Task 1.1 cố định phiên bản Python, quy trình dựng và lưu chính xác version thực tế vào báo cáo.

## 1. Cài Python 3.11

Kiểm tra:

```powershell
py -0p
py -3.11 --version
```

Nếu chưa có, cài bản user-scoped từ Windows Package Manager:

```powershell
winget install --id Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements
```

Mở terminal mới và chạy lại hai lệnh kiểm tra.

## 2. Tạo hoặc khôi phục `.venv`

Pipeline đầy đủ:

```powershell
powershell -ExecutionPolicy Bypass -File tools/bootstrap_python311.ps1 -Requirements local
```

Chỉ dựng GUI nền tảng:

```powershell
powershell -ExecutionPolicy Bypass -File tools/bootstrap_python311.ps1 -Requirements base
```

Script có tính idempotent: nó tái sử dụng `.venv` hợp lệ và dừng nếu thư mục hiện có không chạy Python 3.11. Script không tự xóa môi trường cũ.

## 3. Chạy preflight

Tạo video test cục bộ, không chứa dữ liệu riêng tư:

```powershell
New-Item -ItemType Directory -Path temp -Force | Out-Null
bin\ffmpeg\ffmpeg.exe -y `
  -f lavfi -i color=c=0x121B2B:s=640x360:d=2 `
  -f lavfi -i sine=frequency=440:duration=2 `
  -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac `
  temp\preflight-smoke.mp4
```

Thu báo cáo:

```powershell
.\.venv\Scripts\python.exe tools/preflight.py `
  --video temp\preflight-smoke.mp4 `
  --gui-smoke `
  --json artifacts\evidence\day-1-preflight.json
```

Preflight dùng standard library để vẫn chạy khi môi trường chưa hoàn chỉnh. Nó không đọc `.env`, không gọi API, không tải model và không lưu đường dẫn user-home. Thiếu model/resource là cảnh báo; sai Python 3.11, thiếu base GUI package, GPU mục tiêu, FFmpeg/ffprobe/H.264 encoder, video probe hoặc GUI smoke là lỗi.

## 4. Chạy kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_preflight -v
.\.venv\Scripts\python.exe -m compileall tools tests
```

## Khôi phục

- Nếu `.venv` dùng sai Python, đổi tên nó thủ công để giữ khả năng khôi phục rồi chạy bootstrap lại.
- Nếu FFmpeg báo thiếu, khôi phục `bin/ffmpeg/ffmpeg.exe` và `ffprobe.exe`; không cần thêm FFmpeg vào `PATH`.
- Nếu model báo thiếu, dùng Resource Manager ở task liên quan; không tải âm thầm trong preflight.
- Báo cáo máy nằm tại `artifacts/evidence/day-1-preflight.json`; video tổng hợp và `.venv` nằm trong `.gitignore`.
