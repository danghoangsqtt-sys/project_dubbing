# Phase 1 Spec — Core Feature Complete

## Objective

By Day 7, both 2–5 minute golden smoke clips (one Chinese, one English) complete local media processing, editable transcript, separate Vietnamese subtitle/dubbing, VieNeu audio, mix and validated MP4; SRT remains independently exportable and reopen preserves edits.

## Inputs

- Existing CapCap brownfield code and user-owned working changes.
- Root `design.md` and all six UI Direction pages.
- RTX 3060 12 GB / RAM 32 GB workstation.
- Two rights-cleared 2–5 minute smoke clips.

## Deliverables

- Reproducible Python 3.11 environment and preflight report.
- Versioned canonical segment/project state and provenance signatures.
- Repaired zh/en ASR, translation/dubbing, VieNeu, SRT/mix/export path.
- Six approved PySide6 UI surfaces implemented incrementally.
- Deterministic P0 tests and Day 7 gate report.

## Risks and controls

| Risk | Control |
|---|---|
| Existing manual edits lost by schema change | Backup + migration tests + atomic replace |
| 12 GB VRAM OOM | One heavy GPU stage; unload; telemetry |
| Provider mapping corrupts cues | Stable-ID validation, reject/retry, preserve source |
| TTS quality/timing blocks SRT | Independent SRT output and per-cue failure |
| UI scope consumes week | Apply approved components to existing PySide6; no rewrite |

## Exit criteria

All Phase 1 acceptance rows in `ROADMAP.md` pass; open defects are classified; no unresolved P0; feature freeze is recorded.
