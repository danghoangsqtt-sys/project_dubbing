# How to Use CapCap

## Basic workflow

1. Open CapCap and select CPU or GPU mode in the launcher.
2. Create or open a video project. **Prepare** becomes complete once the video is ready.
3. In **Settings**, choose a Subtitle Source: Audio (SenseVoice or Whisper) or Video (OCR). This choice is saved with the project, not globally.
4. Set source/target language and choose a translation provider.
5. Use **Generate**:
   - **Full Pipeline** runs Transcript → Translate → TTS.
   - **Step-by-Step** runs each stage in order. At TTS, choose **TTS** or **Skip**.
6. Review subtitles, speaker assignments, style, and timed layers in the editor.
7. Use **Fast Preview** to check a five-second rendered sample, then export.

## Transcript editing

- Select a TS1 segment to edit its text, timing, speaker, or voice speed in the Subtitle Inspector.
- Use **+ Layer → Subtitle Segment** to add a missing subtitle at the playhead.
- Use the timeline **Selection Range** and **Alt: OCR/Whisper** to re-transcribe only a problematic section with the opposite recognition engine.
- Alt Transcribe only changes transcription for the selected range; it does not run Translate, TTS, or Export.

## Timeline editing

- Use **Select Range** to create an interval on the ruler. Clear it when finished.
- Select a layer, then use **Split** or **Delete**. A range supplies split boundaries but never changes the selected target layer.
- Use the lock icon in an editable track header to prevent edits without affecting preview or export.
- **Layers** hides/shows whole tracks in the timeline only; it does not affect preview or export.

## Speaker diarization

Enable **Speaker Diarization** in Media before transcription when using Audio source. Detected speakers are colour-coded on TS1. In Voice → Detected Speakers, assign a voice per speaker; in Subtitle Inspector, correct an individual segment's speaker assignment.

## OCR Translator

OCR Translator is independent of subtitle transcription. Open it from the preview toolbar, position its region, capture visible text, then translate or copy the result. It does not modify subtitles, timeline data, or project transcript.

## Text-to-Speech and Voice Cloning

- CapCap supports multiple TTS engines: **Piper TTS** (local offline), **Edge TTS** (online Microsoft voices), **CapCut TTS** (expressive online voices), and **VieNeu TTS**.
- Open the **Voice Clone** dialog to clone voices from custom reference audio files or pick from bundled sample voices.
- Voice pitch, rate, and volume can be adjusted per speaker or per individual subtitle segment in the Subtitle Inspector.

## Layers and export

- Blur, Logo, Mask, and Text layers support direct positioning, timing fields, edge resizing, and timeline splitting. Text layers and subtitles are included in Fast Preview and final export.
- You can export directly to a **CapCut Draft** project to continue advanced video editing and styling inside CapCut.

## Video Export and Quality Profiles

When clicking **Export**, the **Export Summary** dialog displays output parameters (resolution, frame rate, audio configuration, subtitle styling, and visual layers) and lets you choose a **Video Quality / Compression** profile:

- **Medium (Recommended - Balanced)**: Balanced sharpness and encoding speed (CRF 22 / CQ 25, fast/p3 preset). Ideal for web and social media.
- **High (High Quality)**: High detail retention (CRF 18 / CQ 22, medium/p4 preset).
- **Very High (Maximum Quality)**: Near-lossless master quality with deep motion estimation (CRF 15 / CQ 18, slow/p5 preset).
- **Low (Fastest - Smallest File Size)**: Maximum compression and fastest render speed (CRF 26 / CQ 28, veryfast/p2 preset). Ideal for quick draft review.

**Hardware Acceleration & Automatic CPU Fallback**:
Export automatically leverages NVIDIA NVENC GPU acceleration when available. On systems without an NVIDIA GPU, missing CUDA drivers, or in case of encoder errors, CapCap automatically falls back to multithreaded CPU encoding (`libx264`) seamlessly.

