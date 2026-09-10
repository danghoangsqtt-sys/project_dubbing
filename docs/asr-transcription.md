# Faster-Whisper transcription contract

CapCap’s milestone ASR path is local Faster-Whisper for explicitly selected Chinese (`zh`) or English (`en`). Automatic language detection and Whisper’s translate-to-English task are intentionally disabled in this path: choosing the source language prevents silent language changes between reruns and improves cache correctness.

## Recorded configuration

Every run records the following in `settings.asr_config`, `provenance.asr`, and each canonical cue’s `provenance.asr`:

- requested and resolved model identity plus model revision;
- Faster-Whisper and CTranslate2 package versions;
- requested and effective device/compute type;
- beam size, VAD, word timestamps, batching policy and batch size;
- source language, `transcribe` task, and configuration schema version.

A Hugging Face snapshot directory uses its commit directory as the revision. A locally unpacked model uses its resource manifest revision when present, otherwise a stable local model-file identity. A named model that is not installed records `registry-main-unresolved`; installing a concrete snapshot changes the revision and invalidates the transcript cache.

## RTX 3060 execution

The normal target is CUDA with `int8_float16`, beam size 5, VAD and word timestamps. Batching is selected conservatively from available VRAM. If CUDA model loading fails, the engine falls back visibly to CPU `int8`; effective runtime provenance is attached to generated cues. Long audio is chunked and uses standard per-chunk inference for stable segmentation. The lazy Faster-Whisper segment generator is consumed while the GPU/worker lock is still held.

## Outputs and editing

Each non-empty result becomes a canonical cue with a stable ID, valid seconds-based start/end timestamps, Unicode `original_text`, source language, approximate confidence derived from average log probability, optional word timings, and ASR provenance. Project JSON is UTF-8 and atomic, so Chinese text and later timestamp/text edits survive save/reopen.

Model weights remain outside Git. Offline operation requires the selected model snapshot and CUDA runtime pack to be installed through CapCap’s resource workflow before locking the application offline.
