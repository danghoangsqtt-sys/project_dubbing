# Phase 1 State

- **Status:** In progress
- **Progress:** 3/13 tasks
- **Planned days:** 1–7
- **Current task:** 1.4 — Repair translation and dubbing pipeline P0s (`in_progress`)
- **Entry condition:** Crystallize artifacts validated and committed
- **Exit gate:** Day 7 Core Feature Complete
- **Blockers:** None; model packs and ONNX CUDA provider remain readiness warnings assigned to later setup/integration tasks

## Evidence index

- `artifacts/evidence/day-1-preflight.json` — Task 1.1 machine/runtime/video/GUI preflight (`pass`, 2026-09-10)
- `tests/test_project_state_migration.py` — Task 1.2 migration/atomicity/provenance contract (15/15 pass, 2026-09-10)
- `docs/project-state-schema.md` — schema v2 and recovery contract
- `tests/test_asr_contract.py` — Task 1.3 explicit-language/config/provenance contract (7/7 pass, 2026-09-10)
- `docs/asr-transcription.md` — locked zh/en Faster-Whisper behavior and runtime provenance

## Task status

| Task | Status | Evidence/notes |
|---|---|---|
| 1.1 | Done | `artifacts/evidence/day-1-preflight.json`; final state at the Task 1.1 done tag |
| 1.2 | Done | Schema v2 migration, atomic persistence and provenance signatures; `b315f69` |
| 1.3 | Done | Explicit zh/en, eager inference, editable cues and ASR provenance; `0d6f2fb` |
| 1.4 | In progress | Hybrid/offline/mapping/optimization/dubbing repair underway |
| 1.5 | Not started | — |
| 1.6 | Not started | — |
| 1.7 | Not started | — |
| 1.8 | Not started | — |
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
