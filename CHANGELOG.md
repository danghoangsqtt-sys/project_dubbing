# Changelog

Mọi thay đổi đáng chú ý của nhánh cá nhân này được ghi tại đây theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) và [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Bộ project context ViePilot: kiến trúc, requirements, schemas, phase specs và roadmap giao hàng 21 ngày.
- UI Direction sáu màn hình và design contract `design.md` cho ứng dụng PySide6.
- Quy trình dựng `.venv` Python 3.11 tái lập được, bộ kiểm tra preflight phần cứng/runtime và báo cáo bằng chứng Day 1.
- Schema project/segment v2 với ba trường văn bản độc lập, stable cue ID, provenance theo stage và hướng dẫn migration/recovery.
- Hợp đồng Faster-Whisper cục bộ cho `zh`/`en` với cấu hình/model revision, confidence và provenance trên từng cue.

### Changed

- Khóa chiến lược milestone: core complete Ngày 7, RC1 Ngày 14, package/report Ngày 21.
- VieNeu-TTS v3 Turbo là TTS mặc định; Hybrid là profile dịch mặc định; Offline Lock là tùy chọn riêng tư.
- Lưu project và JSON artifact theo cơ chế atomic replace; project cũ được sao lưu trước khi tự động migrate và có thể phục hồi segment từ artifact legacy.
- Transcript cache nay bị vô hiệu hóa khi model revision hoặc cấu hình suy luận ASR thay đổi; auto-detect bị chặn trong luồng zh/en đã khóa.

### Fixed

- Cache signature dịch/TTS nay bao gồm producer/model/revision/prompt/schema/normalizer và stable cue input; thay đổi chỉ thuộc mix không làm mất cache TTS.

## [0.0.0] - 2026-09-09

### Added

- Khởi tạo lịch sử milestone cho nhánh cá nhân dựa trên CapCap upstream.

[Unreleased]: https://github.com/danghoangsqtt-sys/project_dubbing/compare/v0.0.0...HEAD
[0.0.0]: https://github.com/danghoangsqtt-sys/project_dubbing/releases/tag/v0.0.0
