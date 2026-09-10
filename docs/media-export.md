# SRT and media export contract

Vietnamese SRT is an independent product artifact. CapCap writes it as UTF-8 through a sibling temporary file, flushes it, and atomically replaces the destination. It does not require a voice model or successful TTS, so subtitle-only work remains usable when dubbing fails.

Before export, CapCap verifies the source video plus the required subtitle/audio inputs. Final success requires an ffprobe JSON result with at least one video stream and positive duration. The latest project export report records input/output stream facts, the selected encoder policy, and whether SRT was independent.

The bundled FFmpeg is queried with `-encoders`. `h264_nvenc` is preferred only when advertised; `libx264` is the CPU fallback. All subprocesses use argument arrays, no shell, bounded timeouts for probes, and UTF-8 diagnostic decoding.

For Subtitle + Voice, audio is first muxed while video uses stream copy. Scaling, FPS conversion, filters, overlays, and subtitles are then combined in one final render. Subtitle-only and voice-only paths likewise perform no more than one full video encode. A failed ffprobe validation marks export failed and does not publish the result as completed.
