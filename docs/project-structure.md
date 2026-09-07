# Project Structure

```text
CapCap/
├── ui/
│   ├── gui.py                 # Application entry point
│   ├── main_window.py         # Main-window behavior and signal handling
│   ├── controllers/           # Pipeline, preview, and subtitle controllers
│   ├── views/                 # Launcher, panels, timeline, inspectors
│   ├── widgets/               # MPV preview and custom Qt widgets
│   ├── worker_adapters/       # QThread adapters
│   └── utils/                 # UI/media/settings helpers
├── app/
│   ├── capcut/                # CapCut STT, TTS, signing, and draft integration
│   ├── workflows/             # Prepare, voice, and export workflows
│   ├── translation/           # Translation orchestration and providers
│   ├── engines/               # Whisper, OCR, TTS, FFmpeg adapters
│   ├── services/              # Project, resource, ASR, diarization services
│   ├── layers/                # Timeline track and layer domain models
│   ├── vieneu_tts.py          # VieNeu TTS and voice cloning integration
│   ├── ocr_processor.py       # OCR subtitle extraction
│   ├── whisper_processor.py   # Faster-Whisper integration
│   └── sensevoice_processor.py
├── bin/                       # FFmpeg, MPV, on-demand CUDA runtime
├── models/                    # Downloaded ASR, Piper, and diarization models
├── assets/                    # Icons, fonts, voice samples, and image assets
│   ├── voices/                # Reference voice samples for cloning and preview
│   └── capcut/                # CapCut voice metadata definitions
├── docs/                      # Focused project documentation
├── .env_example               # Optional environment template
└── requirements-*.txt         # Python dependency sets
```

Projects and generated artifacts are stored beneath `projects/`; temporary preview and processing files are stored beneath `temp/`.
