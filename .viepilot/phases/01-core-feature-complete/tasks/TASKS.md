# Phase 1 Task Cards

## 1.1 Baseline and preflight

Implement/record the clean Python 3.11 launch, hardware/runtime/resource probes and one video-open smoke test. Done when `artifacts/evidence/day-1-preflight.json` exists and the Day 1 gate passes.

## 1.2 Segment/state/provenance

Migrate without edit loss; add independent text fields, stable IDs, atomic persistence and provenance-aware cache signatures. Tests must cover older project input and one-cue invalidation.

## 1.3 Faster-Whisper zh/en

Lock explicit language, model/compute settings and editable timestamps. Materialize inference in the worker and persist config/provenance.

## 1.4 Translation/dubbing P0 repair

Wire separate dubbing rewrite, propagate subtitle optimization instead of forcing false, validate IDs/names/numbers, and enforce Offline Lock below UI.

## 1.5 SRT/media/export foundation

Keep SRT independent, use argument-list FFmpeg, probe results, detect NVENC and test libx264 fallback with one final encode.

## 1.6 VieNeu/timing

Use `dubbing_vi`, pin VieNeu model, audition/retry per cue, reject silence, preserve sample rate and use bounded time-fit with visible overflow.

## 1.7–1.12 UI Direction

Implement Launcher, Workspace, Transcript & Translation, Voice & Dubbing, Resources & Settings, and Export & Report against root `design.md`. Each page must expose named states and relevant blockers; no heavy work may run on the GUI thread.

## 1.13 Integration and freeze

Run both smoke clips, fix P0, save the report and freeze features. Do not tag unless all gate facts are present.
