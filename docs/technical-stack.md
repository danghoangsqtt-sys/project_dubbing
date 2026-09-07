# Technical Stack

| Area | Technology |
| --- | --- |
| Desktop UI | PySide6 |
| Video preview | libmpv with Qt Multimedia fallback |
| Background work | QThread workers |
| Audio transcription | Faster-Whisper / CTranslate2, SenseVoice / Sherpa-ONNX |
| OCR | RapidOCR PP-OCRv4 with OpenCV and ONNX Runtime |
| Speaker diarization | Sherpa-ONNX |
| VAD | Silero VAD via Sherpa-ONNX |
| Translation | Google Translate, OpenAI, Google AI Studio, and Ollama |
| TTS | Piper, Edge TTS, CapCut TTS, and VieNeu TTS (Voice Cloning) |
| Video/audio processing | FFmpeg (NVENC GPU accelerated with CPU libx264 failover), pydub, NumPy, SciPy, librosa, soundfile |
| External integrations | CapCut Draft project generator |
| Packaging | PyInstaller |

## Processing notes

- GPU Faster-Whisper uses CUDA when available, with standard inference as the safe path and optional batched inference controls.
- RapidOCR uses one GPU inference worker to avoid competing CUDA sessions.
- Video export implements an intelligent two-tier encoding strategy: dynamically selecting NVIDIA NVENC (`h264_nvenc` with p2–p5 presets) when supported, and falling back automatically to CPU `libx264` (with veryfast–slow presets and matched CRF) if NVENC or CUDA drivers are unavailable.
- Timeline waveforms and thumbnails are generated once, cached per project/video, and reused during editing.
- Speaker diarization runs only for audio-based transcription and is optional.

## References

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice)
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)
- [Piper](https://github.com/rhasspy/piper)
- [Edge TTS](https://github.com/rany2/edge-tts)
- [FFmpeg](https://ffmpeg.org/)
- [PyInstaller](https://pyinstaller.org/)
