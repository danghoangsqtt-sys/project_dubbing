# CapCap — Roadmap 21 ngày

## Milestone: Personal Usable v0.1

- **Version target:** 0.1.0
- **Window:** 2026-09-09 → 2026-09-29 (21 ngày liên tục)
- **Strategy:** Core Feature Complete → RC1 → Validation/Package/Report
- **Owner:** `@dhsystem.sys`
- **Hardware:** RTX 3060 12 GB, RAM 32 GB; CPU captured by Task 1.1
- **Change control:** feature freeze after Day 7; Week 3 permits regression/P0 fixes only

## Phase 1 — Core Feature Complete (Ngày 1–7)

**Goal:** Both Chinese→Vietnamese and English→Vietnamese produce editable SRT and a playable dubbed MP4, with save/reopen and visible failure recovery.

**Status:** In progress — 6/13 tasks complete; ASR, translation, media and VieNeu cue foundations passed on 2026-09-10.

| Task | Day | Description | Acceptance criteria | Size |
|---|---:|---|---|---|
| 1.1 | 1 | Reproducible baseline and preflight | Clean Python 3.11 environment launches GUI; CPU/GPU/RAM, CUDA, FFmpeg/NVENC and required resources are recorded; one local video opens | M |
| 1.2 | 1–2 | Canonical segment/state/provenance migration | Existing projects migrate safely; stable IDs; separate `original_text`/`subtitle_vi`/`dubbing_vi`; atomic save/reopen; signatures include full provenance | XL |
| 1.3 | 2 | Lock Faster-Whisper zh/en transcript path | Explicit zh and en modes create editable timed cues; Unicode/state persists; model revision/config recorded | L |
| 1.4 | 3 | Repair translation and dubbing pipeline P0s | Hybrid primary + fallback configured; dubbing rewrite wired; subtitle optimization obeys setting; IDs/names/numbers validated; Offline path cannot call provider | XL |
| 1.5 | 2–5 | Independent SRT and single-pass media/export foundation | UTF-8 SRT works with TTS failure; ffprobe validation; NVENC probe + libx264 fallback; final video encoded once | L |
| 1.6 | 4–5 | VieNeu cue pipeline and timing fit | VieNeu v3 Turbo default; audition/retry; `dubbing_vi` is spoken; high-quality sample rate preserved; silence rejected; speed 0.92–1.12x then review | XL |
| 1.7 | 2–3 | Launcher UI direction | Create/open cards, profile and media/readiness state match `launcher.html` and root `design.md` | M |
| 1.8 | 3–5 | Workspace UI direction | Stage rail, preview, project status, progress, log, cancel/resume are responsive and match `workspace.html` | L |
| 1.9 | 3–4 | Transcript & Translation UI direction | Three independent fields, issue filters, timestamp edit and selective save match `transcript-translation.html` | L |
| 1.10 | 4–5 | Voice & Dubbing UI direction | VieNeu audition, speaker mapping, cue retry and timing warnings match `voice-dubbing.html` | L |
| 1.11 | 1–5 | Resources & Settings UI direction | Hybrid/Offline Lock, revision/license/checksum/readiness and RAM/VRAM estimates match `resources-settings.html` | L |
| 1.12 | 5–6 | Export & Report UI direction | Preflight, SRT/audio/MP4 choices, output path, encoder/fallback and initial run facts match `export-report.html` | L |
| 1.13 | 6–7 | P0 integration, two smoke clips and core freeze | 2–5 min zh and en clips run end-to-end; reopen loses no edits; all P0s triaged/fixed; gate evidence saved and `core-feature-complete` tag may be created | XL |

**Phase verification:**

```powershell
python -m compileall app ui
python -m pytest -m "not hardware and not network" -q
python tools/preflight.py --json artifacts/evidence/day-1-preflight.json
python tools/run_golden.py --case smoke-zh --case smoke-en --profile hybrid --report artifacts/evidence/day-7.json
```

If these helper scripts do not yet exist, their creation is part of Tasks 1.1/1.13; do not substitute manual claims for saved evidence.

**Exit gate:** Day 7 Definition of Core Done passes. Create a gate report before tagging; feature freeze begins.

## Phase 2 — RC1 Stability & Performance (Ngày 8–14)

**Goal:** Make the frozen core reproducible, measurable and resilient; finish with no P0 and a rerunnable RC1 benchmark.

| Task | Day | Description | Acceptance criteria | Size |
|---|---:|---|---|---|
| 2.1 | 8–9 | Deterministic test harness and 6–10 clip golden set | Tests cover IDs, project reopen, mapping, Unicode SRT, TTS failure, timing and export command; dataset covers zh/en clear/noisy/accent/names/numbers/code-switch | XL |
| 2.2 | 9–10 | Cache provenance and selective rerun | Provider/model/prompt/voice/normalizer changes invalidate correctly; single-cue edit invalidates dependents only; unchanged rerun targets ≥90% faster | L |
| 2.3 | 10–11 | Performance/timing instrumentation | Reports RTF, warm-up, peak RAM/VRAM, cache hits, overflow and corrections; Balanced ASR target ≤0.15 RTF; ≥90% cues fit ≤1.12x target | L |
| 2.4 | 11–12 | Offline/cancel/resume/recovery reliability | Offline Lock observes zero HTTP; cancel ack <1s and stop <5s target; interrupted project resumes; failed cue/export preserves valid prior artifacts | XL |
| 2.5 | 12 | Resource and dependency lock | Package/model/binary revisions, license, size and checksum are pinned; missing/incompatible resources fail preflight with action | M |
| 2.6 | 12–13 | Soak, UI QA and prioritized fixes | 10 short runs plus one 20–30 min video; UI p95 target <100ms; all P0 and accuracy/timing P1 fixed; P2 recorded | XL |
| 2.7 | 13–14 | Portable/source package and RC1 gate | Source-run and portable build launch and complete smoke export; no P0; benchmark reruns; create `0.1.0-rc.1` only after gate passes | L |

**Conditional stretch gate:** only if core is green before Day 12, choose one: basic diarization override or Voice Library polish. It must not displace Tasks 2.4–2.7 and is not part of RC1 acceptance.

**Phase verification:**

```powershell
python -m pytest -m "not hardware and not network" -q
python -m pytest -m hardware --run-hardware --report artifacts/evidence/day-14-hardware.json
python tools/run_golden.py --suite milestone --repeat 10 --report artifacts/evidence/day-14-benchmark.json
pyinstaller --clean --noconfirm CapCap.spec
python tools/smoke_package.py --exe dist/CapCap/CapCap.exe --report artifacts/evidence/day-14-package.json
```

**Exit gate:** RC1 has no P0, the test/benchmark command is reproducible, and package/source paths both pass the two primary pipelines.

## Phase 3 — Validation, Package & Report (Ngày 15–21)

**Goal:** Validate RC1, package it safely, and publish a report that states measured results and limitations without adding features.

| Task | Day | Description | Acceptance criteria | Size |
|---|---:|---|---|---|
| 3.1 | 15–16 | Full RC regression and evidence collection | All deterministic/hardware/golden tests rerun; regressions/P0 fixed only; logs/screens/timings stored by run ID | L |
| 3.2 | 17 | Separate zh→vi and en→vi quality analysis | Report ASR, translation, names/numbers, pronunciation, timing, resource use and human corrections per language | L |
| 3.3 | 18 | User guide, troubleshooting and demo | Clean-machine setup/use/recovery documented in Vietnamese; short demo follows actual packaged workflow | M |
| 3.4 | 18–19 | Final Export & Report experience | UI saves output paths, encoder/fallback, resource/provenance manifest and benchmark summary with each project/export | M |
| 3.5 | 19 | License and distribution audit | `THIRD_PARTY_LICENSES`/manifest covers code, model, binary and voice assets; blocked assets excluded; voice consent noted | L |
| 3.6 | 20 | Product report | Objective, architecture, method, results, limits, risks and future direction use measured evidence; no unsupported claims | L |
| 3.7 | 21 | Final acceptance, artifact, checksum and release | Acceptance rerun passes; package opens/exports; checksum and version manifest generated; release/tag created only if gate passes | L |

**Phase verification:**

```powershell
python -m pytest -q
python tools/run_golden.py --suite milestone --report artifacts/evidence/day-21-final.json
python tools/audit_resources.py --manifest artifacts/release/THIRD_PARTY_MANIFEST.json
python tools/smoke_package.py --exe dist/CapCap/CapCap.exe --report artifacts/evidence/day-21-package.json
Get-FileHash -Algorithm SHA256 dist/CapCap-0.1.0.zip
```

**Exit gate:** release artifact, checksum, Vietnamese guide/demo and evidence-backed product report are complete; known limitations and deferred scope are explicit.

## Progress summary

| Phase | Status | Tasks | Completed | Progress |
|---|---|---:|---:|---:|
| 1. Core Feature Complete | In progress | 13 | 6 | 46% |
| 2. RC1 Stability & Performance | Not started | 7 | 0 | 0% |
| 3. Validation, Package & Report | Not started | 7 | 0 | 0% |

## Future milestone—not part of this roadmap

Product Phase 2/3 candidates are diarization/alignment/prosody QA, batch/CLI, advanced Voice Library, FunASR evaluation, translation memory/character profiles, consented voice cloning, optional selected-shot lip-sync, OmniVoice lab, remote worker and provider/plugin registry. Start them only through a new scoped milestone after Day 21 evidence.
