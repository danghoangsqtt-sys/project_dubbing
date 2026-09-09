# Phase 2 Spec — RC1 Stability & Performance

## Objective

Convert the frozen core into a reproducible release candidate by Day 14: no P0, deterministic tests, representative golden data, measured hardware behavior, reliable cancel/resume/offline behavior and a smoke-tested portable build.

## Deliverables

- 6–10 clip golden manifest and deterministic pytest suite.
- Cache/selective rerun correctness tests.
- Benchmark reports for RTF, RAM/VRAM, warm-up, timing and cache.
- Offline/cancel/resume/recovery evidence.
- Pinned dependencies/models/resources and portable build smoke report.

## Scope control

No new main feature. One stretch improvement (basic diarization override or Voice Library polish) is allowed only if all core tests are green before Day 12 and RC work remains protected.

## Exit criteria

No P0, primary zh/en pipelines rerun, benchmark/test commands are documented, source and portable build pass smoke, and RC1 report exists.
