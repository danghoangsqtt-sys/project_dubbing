# VieNeu-TTS and timing contract

VieNeu-TTS v3 Turbo (`pnnbao-ump/VieNeu-TTS-v3-Turbo`, ONNX backend) is the default local Vietnamese engine. CapCap serializes calls to the shared model so concurrent cues cannot race one GPU-backed instance. Every generated cue can carry engine, model revision, package, voice, speed and 48 kHz provenance.

TTS always reads `dubbing_vi` first. The cue audition method uses the same synthesis boundary as a full run, so previewed text, voice and speed match production. Existing cue-level retry logic rewrites or retries difficult cues and retains attempt/action metrics.

VieNeu audio remains 48 kHz PCM through cue generation and is resampled only if a later mix/export boundary requires it. WAV validation rejects missing headers, empty frames and digital silence; a failed cue is never treated as a valid cache result.

Automatic and user-requested speed values are clamped to 0.92–1.12x. Timing outside the accepted band is marked `needs_review` with `tts_timing_review`, rather than being hidden by aggressive speed-up. This is timing fit, not lip-sync; mouth-shape synchronization remains outside the milestone.
