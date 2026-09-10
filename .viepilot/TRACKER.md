# CapCap — Tracker

## Current state

- **Milestone:** Personal Usable v0.1 — 21-day delivery
- **Status:** In progress
- **Current phase:** Phase 1 — Core Feature Complete
- **Current task:** 1.3 — Lock Faster-Whisper zh/en transcript path (`ready`)
- **Last activity:** 2026-09-10 — Task 1.2 completed; schema v2 migration, atomic save/reopen and provenance tests passed
- **Feature freeze:** Planned at end of Day 7

## Progress

```text
Phase 1 — Core Feature Complete         [##--------] 2/13
Phase 2 — RC1 Stability & Performance   [----------] 0/7
Phase 3 — Validation, Package & Report  [----------] 0/7
Overall                                 [#---------] 2/27
```

Existing upstream capabilities are the brownfield baseline; percentages track this 21-day stabilization milestone only.

## Gate status

| Gate | Target | Status | Evidence |
|---|---|---|---|
| Day 1 | Clean Python 3.11 GUI + open video | Passed | `artifacts/evidence/day-1-preflight.json` |
| Day 3 | Correct Vietnamese SRT from zh and en | Pending | Day 3 translation/SRT report |
| Day 5 | Dubbed MP4 + lossless reopen | Pending | Day 5 E2E report |
| Day 7 | Core Feature Complete | Pending | `artifacts/evidence/day-7.json` |
| Day 14 | RC1, no P0, rerunnable benchmark | Pending | `artifacts/evidence/day-14-benchmark.json` |
| Day 21 | Package + guide + demo + report | Pending | `artifacts/evidence/day-21-final.json` |

## Decision log

| Date | Decision | Rationale | Applies |
|---|---|---|---|
| 2026-09-09 | Personal/local-first Windows product | One owner/user; privacy and practical delivery | All phases |
| 2026-09-09 | Hybrid translation default; Offline Lock optional | Prioritize translation accuracy/speed while preserving zero-network mode | Phase 1+ |
| 2026-09-09 | VieNeu-TTS v3 Turbo default | Best current fit for Vietnamese local TTS | Phase 1+ |
| 2026-09-09 | OmniVoice production and lip-sync deferred | Too much model/license/timing risk for 21 days | Future |
| 2026-09-09 | One heavy GPU stage at a time | RTX 3060 has 12 GB VRAM | All phases |
| 2026-09-09 | Separate source/subtitle/dubbing fields | Accuracy and dubbing naturalness require different editable text | Phase 1+ |
| 2026-09-09 | Feature freeze Day 7 | Protect Weeks 2–3 for stability and evidence | Milestone |
| 2026-09-09 | Export approved UI Direction to root `design.md` | Give implementation a single design contract | Phase 1 |

## Known baseline P0s

- Dubbing rewrite is not consistently wired as an independent downstream path.
- `optimize_subtitles` is forced to false at several entry points.
- Resolved in Task 1.2: translation/TTS signatures now include provider/engine/model/revision/prompt/schema/normalizer provenance and stable cue inputs.

The two remaining pipeline P0s are assigned to Task 1.4.

## Blockers

None. Task 1.1 records the i7-12700/RTX 3060 workstation. Missing model/native packs and the unavailable ONNX CUDA provider remain explicit readiness warnings for later resource and pipeline tasks.

## Next action

Refine and start Task 1.3: lock the explicit Chinese/English Faster-Whisper transcript path and persist model revision/configuration on canonical cues.
