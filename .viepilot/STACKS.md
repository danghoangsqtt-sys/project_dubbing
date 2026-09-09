# CapCap — Stack Intelligence Index

Official-source guidance was refreshed on 2026-09-09 and is stored in the global ViePilot cache.

| Stack | Role | Global cache |
|---|---|---|
| Python 3.11 + PySide6 | Desktop UI, workers, subprocess orchestration | `~/.viepilot/stacks/python-pyside6-desktop/` |
| Faster-Whisper + CTranslate2 | Local Chinese/English ASR | `~/.viepilot/stacks/faster-whisper-ctranslate2/` |
| VieNeu-TTS v3 Turbo | Default Vietnamese TTS | `~/.viepilot/stacks/vieneu-tts/` |
| FFmpeg + NVENC | Probe, audio processing, mix, mux, export | `~/.viepilot/stacks/ffmpeg-nvenc/` |
| PyInstaller | Windows portable/package | `~/.viepilot/stacks/pyinstaller/` |
| pytest | Unit, integration, golden and hardware tests | `~/.viepilot/stacks/pytest/` |

Read `SUMMARY.md`, then `BEST-PRACTICES.md` and `ANTI-PATTERNS.md`; use `SOURCES.md` when validating a version-sensitive decision.
