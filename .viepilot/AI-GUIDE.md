# CapCap — AI Navigation Guide

> Read this file before starting a task. The current milestone is a personal, 21-day stabilization and delivery effort—not a rewrite.

## Quick context

- **Owner/profile:** `personal`, bound by `.viepilot/META.md`; global source `~/.viepilot/profiles/personal.md`.
- **Target:** Windows, RTX 3060 12 GB VRAM, 32 GB RAM, one primary user.
- **Input/output:** Chinese or English video → separate Vietnamese subtitles and Vietnamese dubbing.
- **Default:** Hybrid translation; local media/ASR/TTS/mix/export; optional Offline Lock.
- **TTS:** VieNeu-TTS v3 Turbo. OmniVoice and lip-sync are outside this milestone.
- **Design contract:** root `design.md`; six approved screens under `.viepilot/ui-direction/2026-09-09/`.

## Quick lookup

| Need | Read |
|---|---|
| Scope, domain rules, requirements | `PROJECT-CONTEXT.md` |
| Architecture and diagrams | `ARCHITECTURE.md` + `architecture/*.mermaid` |
| Ordered 21-day work | `ROADMAP.md` |
| Current/next task | `TRACKER.md`, `HANDOFF.json` |
| Coding and safety rules | `SYSTEM-RULES.md` |
| Metadata and attribution | `PROJECT-META.md` |
| Stack guidance | `STACKS.md` |
| Contracts | `schemas/` |
| UI implementation | `design.md` and UI Direction pages |
| Decision rationale | `docs/brainstorm/session-2026-09-09.md` |

## Loading strategy

1. Always read `TRACKER.md` and the active phase/task in `ROADMAP.md`.
2. Before coding, read the relevant requirements in `PROJECT-CONTEXT.md`, the architecture boundary, `SYSTEM-RULES.md`, and root `design.md` for UI work.
3. For architecture or scope changes, read all of `PROJECT-CONTEXT.md`, future roadmap phases, the brainstorm, and record the decision.
4. Never implement a deferred feature by accident; OmniVoice production, lip-sync, FunASR production, remote worker expansion, and a full UI rewrite require a later `/vp-evolve` milestone.

## Critical invariants

- `original_text`, `subtitle_vi`, and `dubbing_vi` are different user-owned fields.
- Stable segment IDs survive every stage; names/numbers are preserved or flagged.
- Only one heavy GPU stage owns the RTX 3060 at a time.
- Cache keys include input plus provider/engine/model/prompt/normalizer provenance.
- SRT export remains possible when TTS fails.
- Offline Lock permits zero outbound requests.
- Long-running UI operations are cancellable, resumable, observable, and never block Qt's main thread.

## File relationships

`PROJECT-CONTEXT.md` defines what → `ARCHITECTURE.md` defines boundaries → `ROADMAP.md` orders implementation → `TRACKER.md` and `HANDOFF.json` record state → phase `SPEC.md` and task files define acceptance.

## Commands

- `/vp-auto` — execute the next roadmap task.
- `/vp-status` — inspect milestone progress.
- `/vp-pause` / `/vp-resume` — preserve and restore execution context.
- `/vp-evolve` — propose a later milestone or deferred feature.
