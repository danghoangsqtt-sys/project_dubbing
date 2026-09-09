# CapCap UI Direction Notes

Session: `2026-09-09`  
Mode: multi-page UI direction  
Target: Windows desktop, 1440×900 recommended; minimum working width 1280 px  
Responsive strategy: desktop-only product. CSS reflows only to keep the direction browsable; it is not a mobile product requirement.

## Product intent

Thiết kế cho một người dùng cá nhân cần xử lý video tiếng Trung/tiếng Anh sang cả phụ đề tiếng Việt và lồng tiếng tiếng Việt. Độ chính xác được ưu tiên trước tốc độ tuyệt đối, nhưng pipeline phải tận dụng RTX 3060 12 GB và có CPU fallback.

## Source of truth

- Visual reference: `assets/preview.JPG`.
- Existing launcher: `ui/views/launcher.py`.
- Existing workspace controls: `ui/views/start_panel.py`, `ui/views/preview_panel.py`, `ui/main_window.py`.
- Existing resources and review dialogs: `ui/views/resource_manager.py`, `ui/widgets/subtitle_editor_dialog.py`, `ui/widgets/voice_clone_dialog.py`.
- Product decisions: `docs/brainstorm/session-2026-09-09.md`.

## Pages inventory

| Slug | File | Title | Purpose | Key sections | Navigation |
|---|---|---|---|---|---|
| launcher | `pages/launcher.html` | Launcher | Device/resource readiness and project entry | device selector, readiness gate, recent projects | Workspace, Resources |
| workspace | `pages/workspace.html` | Workspace | Main edit and orchestration surface | workflow, preview, cue inspector, timeline | all pages |
| transcript-translation | `pages/transcript-translation.html` | Transcript & Translation | Accuracy review for source/subtitle/dubbing text | filters, cue table, issue inspector | Workspace, Voice |
| voice-dubbing | `pages/voice-dubbing.html` | Voice & Dubbing | Voice mapping and duration-fit review | VieNeu profile, speaker map, generation queue | Translation, Export |
| resources-settings | `pages/resources-settings.html` | Resources & Settings | Offline/hybrid model and provider readiness | execution profile, models, storage | Launcher, Workspace |
| export-report | `pages/export-report.html` | Export & Report | Output validation, encoding and evidence | preflight, quality, output package, metrics | Workspace, Launcher |

Inventory invariant: every HTML file in the pages directory appears exactly once above, and every row resolves to an existing file.

## Core information architecture

`Launcher → Workspace → Transcript & Translation → Voice & Dubbing → Export & Report`

`Resources & Settings` is accessible from Launcher and Workspace because missing models must be resolved before a long-running stage begins.

## Key UX decisions

1. The app never merges subtitle text with dubbing text. A readable subtitle may be longer than a speakable line; both remain traceable to the same source cue.
2. Generation is stage-based and resumable. “Generate full pipeline” remains available, but every stage exposes status, issues and a retry action.
3. Confidence is an attention signal, not a claim of correctness. Low-confidence transcription and terminology warnings enter the review queue.
4. Lip-sync is not promised in Phase 1. The UI exposes duration fit and waveform alignment, not mouth-shape controls.
5. VieNeu v3 Turbo is the default Vietnamese voice engine. OmniVoice belongs to a later experimental adapter and is not shown as production-ready.
6. Video/audio, ASR, TTS, mix and export remain local. **Hybrid is the default translation profile** for accuracy/speed, but only text cues may leave the machine and the UI labels this explicitly. Offline Lock remains a one-click profile.

## Status model

| Status | Meaning | Visual |
|---|---|---|
| Not started | no artifact exists | muted |
| Queued | waiting for worker/GPU | blue |
| Running | active, progress known when possible | blue + progress |
| Needs review | output exists but has a quality/timing issue | yellow |
| Done | artifact exists and passed current checks | green |
| Blocked/Error | cannot continue without action | red |

## Phase 1 coverage

| Capability | Primary page | UI acceptance signal |
|---|---|---|
| Import local video | Launcher | project card created and media probe succeeds |
| Chinese/English transcription | Workspace | Transcript stage complete; cue count visible |
| Vietnamese subtitle translation | Transcript & Translation | `subtitle_vi` present; review issues filterable |
| Vietnamese dubbing rewrite | Transcript & Translation | `dubbing_vi` separate and duration estimate visible |
| VieNeu TTS | Voice & Dubbing | speaker mappings valid; cues can be auditioned |
| Mix and timing fit | Voice & Dubbing | overflow warnings resolved or accepted |
| SRT/MP4 export | Export & Report | preflight passes; output paths and encode mode recorded |
| Test/report evidence | Export & Report | run metrics and manifest saved with project |

## design_tokens

```yaml
color:
  bg: "#0A101E"
  surface: "#121B2B"
  surfaceRaised: "#132033"
  border: "#2F4868"
  text: "#F8FBFF"
  textMuted: "#8EA3BB"
  primary: "#4ED0B3"
  accent: "#8AD7FF"
  success: "#54D18B"
  warning: "#FFD400"
  error: "#FF6B6B"
type:
  family: "Segoe UI, Inter, sans-serif"
  base: "14px/1.45"
spacing: [4, 8, 12, 16, 24, 32, 48]
radius: {sm: 6, md: 10, lg: 14, pill: 999}
layout:
  sidebar: 276
  inspector: 360
  targetViewport: "1440x900+"
```

## Out of scope for this direction

- Mobile/tablet application.
- Production implementation details or final pixel-perfect component specs.
- Real-time lip-sync or Wav2Lip control surface.
- Multi-user review, cloud collaboration and account/billing flows.
- OmniVoice production workflow.

## Visual QA evidence

Static 1440×900 renders are stored under `previews/` for the hub and all six screens:

- `previews/hub.png`
- `previews/launcher.png`
- `previews/workspace.png`
- `previews/translation.png`
- `previews/voice.png`
- `previews/resources.png`
- `previews/export.png`

The renders were checked for navigation visibility, clipped primary actions, separation of the three text fields, status-label legibility, and preflight/resource blockers.

## Validation checklist

- [x] Hub opens and links to all six pages.
- [x] Every page links back to the hub and key adjacent pages.
- [x] Transcript, subtitle VI and dubbing VI are visibly separate.
- [x] Offline/hybrid execution is explicit.
- [x] Missing models and export blockers are visible before execution.
- [x] All status colors include a textual label.
- [x] Visual review at 1440×900 completed.
