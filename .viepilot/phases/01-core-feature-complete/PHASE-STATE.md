# Phase 1 State

- **Status:** In progress
- **Progress:** 8/13 tasks
- **Planned days:** 1–7
- **Current task:** 1.9 — Transcript & Translation UI direction (`not_started`)
- **Entry condition:** Crystallize artifacts validated and committed
- **Exit gate:** Day 7 Core Feature Complete
- **Blockers:** None; model packs and ONNX CUDA provider remain readiness warnings assigned to later setup/integration tasks

## Evidence index

- `artifacts/evidence/day-1-preflight.json` — Task 1.1 machine/runtime/video/GUI preflight (`pass`, 2026-09-10)
- `tests/test_project_state_migration.py` — Task 1.2 migration/atomicity/provenance contract (15/15 pass, 2026-09-10)
- `docs/project-state-schema.md` — schema v2 and recovery contract
- `tests/test_asr_contract.py` — Task 1.3 explicit-language/config/provenance contract (7/7 pass, 2026-09-10)
- `docs/asr-transcription.md` — locked zh/en Faster-Whisper behavior and runtime provenance
- `tests/test_translation_contract.py` — Task 1.4 hybrid/offline/mapping/dubbing contract (7/7 pass, 2026-09-10)
- `tests/test_media_export_contract.py` — Task 1.5 atomic SRT/probe/single-pass contract (5/5 pass, 2026-09-10)
- `tests/test_vieneu_timing_contract.py` — Task 1.6 VieNeu serialization/48 kHz/silence/timing/audition contract (7/7 pass, 2026-09-10)
- `docs/vieneu-timing.md` — VieNeu engine and timing-fit boundary
- `tests/test_launcher_ui.py` — Task 1.7 launcher state/drop/offscreen contract (4/4 pass, 2026-09-10)
- `artifacts/evidence/task-1.7-launcher.png` — reviewed production Launcher render
- `tests/test_workspace_ui.py` — Task 1.8 stage/navigation/stop-resume/offscreen contract (8/8 pass, 2026-09-10)
- `docs/ui-workspace.md` — Workspace state, operation and recovery behavior

## Task status

| Task | Status | Evidence/notes |
|---|---|---|
| 1.1 | Done | `artifacts/evidence/day-1-preflight.json`; final state at the Task 1.1 done tag |
| 1.2 | Done | Schema v2 migration, atomic persistence and provenance signatures; `b315f69` |
| 1.3 | Done | Explicit zh/en, eager inference, editable cues and ASR provenance; `0d6f2fb` |
| 1.4 | Done | Hybrid/offline policy, optimization, stable mapping and independent dubbing; `545b31e` |
| 1.5 | Done | Atomic SRT, ffprobe validation, NVENC fallback and one final encode; `3e9a3ea` |
| 1.6 | Done | VieNeu v3 Turbo default, serialized inference, 48 kHz, silence rejection and 0.92–1.12x timing; `c15b741` |
| 1.7 | Done | Vietnamese readiness/resume/drop launcher aligned with approved direction; `8dbfa60` |
| 1.8 | Done | Vietnamese five-stage Workspace, observable progress/log and cooperative stop/resume; `f2f6fc6` |
| 1.9 | Not started | — |
| 1.10 | Not started | — |
| 1.11 | Not started | — |
| 1.12 | Not started | — |
| 1.13 | Not started | — |

## Files changed

| Task | File |
|---|---|
| 1.2 | `.viepilot/HANDOFF.json` |
| 1.2 | `.viepilot/ROADMAP.md` |
| 1.2 | `.viepilot/TRACKER.md` |
| 1.2 | `.viepilot/phases/01-core-feature-complete/PHASE-STATE.md` |
| 1.2 | `.viepilot/phases/01-core-feature-complete/tasks/1.2.md` |
| 1.2 | `CHANGELOG.md` |
| 1.2 | `app/core/models/__init__.py` |
| 1.2 | `app/core/models/segment.py` |
| 1.2 | `app/core/state/__init__.py` |
| 1.2 | `app/core/state/project_state.py` |
| 1.2 | `app/services/gui_project_bridge.py` |
| 1.2 | `app/services/project_service.py` |
| 1.2 | `app/services/segment_service.py` |
| 1.2 | `app/workflows/prepare_workflow.py` |
| 1.2 | `artifacts/evidence/day-1-preflight.json` |
| 1.2 | `docs/project-state-schema.md` |
| 1.2 | `tests/test_project_state_migration.py` |
| 1.3 | `.viepilot/phases/01-core-feature-complete/tasks/1.3.md` |
| 1.3 | `app/asr_config.py` |
| 1.3 | `app/whisper_processor.py` |
| 1.3 | `app/engines/whisper_adapter.py` |
| 1.3 | `app/services/engine_runtime.py` |
| 1.3 | `app/services/asr_merge_service.py` |
| 1.3 | `app/services/project_service.py` |
| 1.3 | `app/services/segment_service.py` |
| 1.3 | `app/workflows/prepare_workflow.py` |
| 1.3 | `tests/test_asr_contract.py` |
| 1.3 | `docs/asr-transcription.md` |
| 1.3 | `artifacts/evidence/day-1-preflight.json` |
| 1.4 | `.viepilot/phases/01-core-feature-complete/tasks/1.4.md` |
| 1.4 | `app/network_policy.py` |
| 1.4 | `app/translation/orchestrator.py` |
| 1.4 | `app/translation/providers/gemini_polisher.py` |
| 1.4 | `app/translation/providers/google_web_translator.py` |
| 1.4 | `app/translation/srt_utils.py` |
| 1.4 | `app/translation/validation.py` |
| 1.4 | `app/workflows/prepare_workflow.py` |
| 1.4 | `app/workflows/voice_workflow.py` |
| 1.4 | `ui/main_window.py` |
| 1.4 | `ui/worker_adapters/processing_workers.py` |
| 1.4 | `tests/test_translation_contract.py` |
| 1.4 | `docs/translation-profiles.md` |
| 1.5 | `app/media_contract.py` |
| 1.5 | `app/subtitle_builder.py` |
| 1.5 | `app/engines/subtitle_adapter.py` |
| 1.5 | `app/workflows/export_workflow.py` |
| 1.5 | `tests/test_media_export_contract.py` |
| 1.5 | `docs/media-export.md` |
| 1.6 | `.viepilot/phases/01-core-feature-complete/tasks/1.6.md` |
| 1.6 | `app/tts_processor.py` |
| 1.6 | `app/utils/voice_preview_utils.py` |
| 1.6 | `app/vieneu_tts.py` |
| 1.6 | `app/workflows/voice_workflow.py` |
| 1.6 | `artifacts/evidence/day-1-preflight.json` |
| 1.6 | `docs/vieneu-timing.md` |
| 1.6 | `tests/test_vieneu_timing_contract.py` |
| 1.7 | `.viepilot/phases/01-core-feature-complete/tasks/1.7.md` |
| 1.7 | `ui/views/launcher.py` |
| 1.7 | `tests/test_launcher_ui.py` |
| 1.7 | `tools/render_launcher.py` |
| 1.7 | `docs/ui-launcher.md` |
| 1.7 | `artifacts/evidence/task-1.7-launcher.png` |
| 1.7 | `artifacts/evidence/day-1-preflight.json` |
| 1.8 | `.viepilot/phases/01-core-feature-complete/tasks/1.8.md` |
| 1.8 | `ui/views/main_window.py` |
| 1.8 | `ui/views/start_panel.py` |
| 1.8 | `ui/main_window.py` |
| 1.8 | `ui/controllers/pipeline_controller.py` |
| 1.8 | `ui/widgets/progress_dialog.py` |
| 1.8 | `tests/test_workspace_ui.py` |
| 1.8 | `docs/ui-workspace.md` |
| 1.8 | `artifacts/evidence/day-1-preflight.json` |
