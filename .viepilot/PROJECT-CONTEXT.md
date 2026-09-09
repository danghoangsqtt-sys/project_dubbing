<!-- crystallize_version: 0.8.0 -->
# CapCap — Project Context and Requirements

<domain_knowledge>

## What this system does

CapCap is a local-first Windows video localization studio for one primary user. It accepts Chinese or English media, produces editable Vietnamese subtitles and a separately editable Vietnamese dubbing script, synthesizes Vietnamese speech, mixes it with the source background, and exports validated SRT/audio/MP4 artifacts.

## Key concepts

| Term | Definition |
|---|---|
| Project | Versioned local state linking one source video, settings, segments, artifacts and run evidence. |
| Segment/cue | Stable timed unit that carries source text, two Vietnamese outputs, speaker, QA and provenance. |
| `original_text` | ASR/source content; translation never overwrites it. |
| `subtitle_vi` | Faithful and readable Vietnamese subtitle. |
| `dubbing_vi` | Natural Vietnamese spoken rewrite fitted to the available time. |
| Offline Lock | Execution policy that prevents all outbound network requests. |
| Hybrid | Default policy: local media/ASR/TTS/mix/export with an explicitly configured translation provider. |
| Quality gate | User review checkpoint before downstream generation/export. |
| Provenance | Engine/provider, model/revision, prompt/schema version and input signature that produced an artifact. |
| Selective rerun | Recompute only edited cues and dependent downstream artifacts. |

## Users and jobs

- Primary persona: the project owner, working alone on one Windows workstation.
- Primary job: turn a Chinese or English video into accurate Vietnamese subtitles and usable Vietnamese dubbing quickly, while retaining manual control.
- Trust need: know whether work is local or online, what resource is running, what failed, and whether reopening loses edits.

## Business rules

1. Source language is explicitly `zh` or `en` for production runs; auto detection is opt-in.
2. Segment IDs/count/order must remain stable. A provider response that loses or duplicates IDs is rejected/retried, never silently accepted.
3. Names, numbers and glossary terms are preserved or flagged for review.
4. `subtitle_vi` and `dubbing_vi` are independent. Editing one must not overwrite the other.
5. TTS reads edited `dubbing_vi`/`tts_text` first, then uses a documented fallback only if it is empty.
6. SRT is exportable even if TTS, mixing or MP4 export fails.
7. Timing fit uses rewrite/re-synthesis before bounded time-stretch; milestone speed range is 0.92–1.12x.
8. Silent, corrupt or missing audio is failure, never a successful cache entry.
9. Heavy GPU stages are serialized; release/unload a model before the next heavy stage when needed.
10. Offline Lock produces zero outbound network calls. Hybrid never hides which provider received text.
11. Project state is saved atomically and migrations preserve confirmed manual edits.
12. Voice cloning is explicit, consented and licensed; it is not automatic for every speaker.
13. Lip-sync is not required for usable dubbing and is outside the 21-day release.

## Data relationships

One project references one input media fingerprint and many stable segments. Each segment owns source, subtitle, dubbing, speaker/voice, timing and QA/provenance records. Stage artifacts reference the signature of their upstream inputs. Export and report manifests reference all final artifacts and machine/runtime metadata.

</domain_knowledge>

<product_vision>

## Product vision and phased scope

### Project scope

Deliver a personally usable CapCap on the owner's RTX 3060 12 GB / 32 GB RAM workstation in 21 days: core complete by Day 7, stable RC1 by Day 14, and a reproducible package plus evidence-backed report by Day 21.

### 21-day delivery phases

| Delivery phase | Days | Goal | Included capability |
|---|---:|---|---|
| Phase 1 — Core Feature Complete | 1–7 | Both zh→vi and en→vi run end-to-end | Environment/preflight, schema/provenance, ASR, translation + separate dubbing rewrite, SRT, VieNeu, timing/mix/export, save/reopen, six UI surfaces, two smoke clips |
| Phase 2 — RC1 Stability & Performance | 8–14 | No P0; tests and benchmark reproducible | Golden set, deterministic tests, cache/selective rerun, Offline Lock/cancel/resume, resource telemetry, soak test, dependency/model pinning, portable build |
| Phase 3 — Validation, Package & Report | 15–21 | Release artifact and honest measured report | RC regression, zh/en quality analysis, documentation/demo, license manifest, package/checksum, final acceptance/tag |

### Product horizon assignment

The brainstorm's product phases are longer than this delivery milestone:

| Product horizon | Assignment |
|---|---|
| Product Phase 1 — Offline usable and foundation quality | Core subset is scheduled across Delivery Phases 1–3. Full local Ollama/model-manager polish continues after evidence if unfinished. |
| Product Phase 2 — Alignment, multi-speaker and productivity | Cache/selective rerun and basic timing are included; diarization/Voice Library may be the single Week 2 stretch goal only after core is green. Remaining items are future milestone. |
| Product Phase 3 — Advanced quality | Entirely deferred after Day 21. |

### Anti-goals and explicit non-scope

- Production OmniVoice, whole-video lip-sync, FunASR production, remote worker expansion or plugin registry.
- Automatic voice cloning for every character or studio-grade multi-speaker dubbing.
- Full UI monolith rewrite, web application, mobile/tablet or multi-user cloud collaboration.
- Integrating entire competitor repositories into CapCap; only clean-room design patterns are adopted.
- Quality/speed claims without benchmarks on the target machine.
- New features after Day 7 without an explicit change gate; Week 3 accepts only regressions/P0 fixes.

</product_vision>

## Functional requirements

| ID | Priority | Requirement | Acceptance evidence | Delivery task |
|---|---|---|---|---|
| FR-001 | P0 | Import/probe local video and create/reopen a project without losing confirmed edits. | Reopen test and ffprobe facts match source. | 1.1, 1.2 |
| FR-002 | P0 | Explicit zh/en Faster-Whisper transcription with editable text/timestamps. | Both golden smoke clips produce stable editable cues. | 1.3 |
| FR-003 | P0 | Generate separate `subtitle_vi` and `dubbing_vi`; wire dubbing rewrite through runtime/UI. | Editing either field leaves the other unchanged; TTS reads dubbing. | 1.2, 1.4, 1.9 |
| FR-004 | P0 | Preserve segment IDs/order, names, numbers and glossary or flag failures. | 100% segment mapping; ≥99.5% preserve-or-flag on golden set. | 1.4, 2.1 |
| FR-005 | P0 | `optimize_subtitles` follows user/project policy and is not hardcoded false in local/remote paths. | Tests cover enabled/disabled behavior at all entry points. | 1.4 |
| FR-006 | P0 | Export UTF-8 SRT independently from voice generation. | SRT passes parser/Unicode test when TTS is forced to fail. | 1.5 |
| FR-007 | P0 | VieNeu v3 Turbo supports audition, cue synthesis, retry, failure validation and separate dubbing text. | Valid audio or actionable per-cue error; silence is rejected. | 1.6, 1.10 |
| FR-008 | P0 | Timing flow rewrites/re-synthesizes before time-stretch and flags unresolved overflow. | ≥90% cues fit without speed above 1.12x target on benchmark. | 1.6, 2.3 |
| FR-009 | P0 | Mix background and dubbing; preview a range; export MP4 with NVENC and libx264 fallback. | ffprobe-valid playable output on both configured paths; one final encode. | 1.5, 1.12 |
| FR-010 | P0 | Every stage exposes queued/running/review/done/error, progress, cancel and resume. | UI state test; cancel acknowledged <1s, worker stops <5s target. | 1.8, 2.4 |
| FR-011 | P0 | Offline Lock blocks all network-capable providers. | Test suite observes zero outbound requests. | 1.11, 2.4 |
| FR-012 | P1 | Resource Manager displays model/binary revision, license, size, checksum, RAM/VRAM estimate and readiness. | Missing/incompatible resource blocks stage before execution. | 1.11, 2.5 |
| FR-013 | P1 | Cache signature captures full provenance and selective invalidation. | Unchanged rerun ≥90% faster target; one cue edit invalidates only dependents. | 1.2, 2.2 |
| FR-014 | P1 | Golden suite covers Chinese/English, clear/noisy/accent/multi-speaker, names/numbers/code-switch. | 6–10 clips with expected facts and rerunnable command. | 2.1 |
| FR-015 | P1 | Save run evidence and a product report. | Metrics, logs, manifests and limitations included in final report. | 2.3, 3.2, 3.5 |

## Non-functional requirements

| ID | Category | Target |
|---|---|---|
| NFR-001 | Privacy | Offline Lock: 0 outbound network requests. |
| NFR-002 | Stability | 10 short-pipeline runs and at least one 20–30 minute soak in Week 2 without P0; aspirational 60-minute/10-run criterion is reported honestly if time/data permits. |
| NFR-003 | Resources | Peak VRAM ≤10.5 GB and peak RAM ≤24 GB target on RTX 3060/32 GB. |
| NFR-004 | Responsiveness | UI event response p95 <100 ms during background work. |
| NFR-005 | Cancellation | Acknowledge cancel <1 second; worker stop <5 seconds when engine supports cooperative cancellation. |
| NFR-006 | ASR speed | Balanced Faster-Whisper RTF ≤0.15 target on the declared golden set and target machine. |
| NFR-007 | Rerun speed | Unchanged rerun ≥90% faster than cold run. |
| NFR-008 | Integrity | Segment ID/count/order valid 100%; atomic state save; no confirmed-edit loss. |
| NFR-009 | Packaging | Source-run and portable build smoke-tested on Windows with pinned dependency/model manifest. |
| NFR-010 | Accessibility | Text contrast ≥4.5:1; status never encoded by color alone; cue actions keyboard reachable. |

## UI Pages → Component Map

UI Direction read status: **complete**. Inventory contains exactly six pages plus hub. Design.MD status: **exported** to root `design.md`.

| Page | Target component(s) | Key acceptance | Assignment | Status |
|---|---|---|---|---|
| `launcher.html` | `ui/views/launcher.py` | Create/open project; probe/readiness visible | Phase 1, Task 1.7 | assigned (Phase 1, Task 1.7) |
| `workspace.html` | `ui/views/main_window.py`, `ui/views/start_panel.py`, `ui/views/preview_panel.py` | Stage rail, preview, progress, cancel/resume | Phase 1, Task 1.8 | assigned (Phase 1, Task 1.8) |
| `transcript-translation.html` | `ui/widgets/subtitle_editor_dialog.py`, `ui/controllers/subtitle_controller.py` | Three separate fields and issue filters | Phase 1, Task 1.9 | assigned (Phase 1, Task 1.9) |
| `voice-dubbing.html` | `ui/views/start_panel.py`, `ui/widgets/voice_clone_dialog.py`, `app/workflows/voice_workflow.py` | VieNeu audition, speaker mapping, timing warnings | Phase 1, Task 1.10 | assigned (Phase 1, Task 1.10) |
| `resources-settings.html` | `ui/views/resource_manager.py`, settings in `ui/main_window.py` | Profile/Offline Lock/readiness/license/VRAM | Phase 1, Task 1.11 | assigned (Phase 1, Task 1.11) |
| `export-report.html` | `ui/controllers/preview_controller.py`, `app/workflows/export_workflow.py` | Preflight, SRT/MP4, path/encoder/metrics | Phase 1, Task 1.12; Phase 3, Task 3.4 | assigned (Phase 1, Task 1.12) |

<conventions>

## Project conventions

- Python modules/functions/variables: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- Segment keys use canonical English identifiers; UI copy and user documentation use Vietnamese.
- Stage IDs are stable machine identifiers: `extraction`, `transcription`, `translation`, `rewrite_dubbing`, `generate_tts`, `mix`, `build_subtitle`, `export`.
- Adapters implement explicit protocols and declare capabilities; unsupported capability fails visibly.
- DTO/request boundaries use immutable dataclasses or copied dictionaries; widgets do not own domain state.
- Provider/model versions and artifact signatures are data, not implicit global settings.

## Preferred patterns

- Ports/adapters around engines; orchestration in workflows; persistence in services/state.
- Worker-object/QThread + queued signals for background operations.
- Atomic JSON writes and schema migrations with backup/recovery.
- Cue-level idempotence and dependency-aware cache invalidation.
- Preflight before expensive work and ffprobe after export.
- Capability flags and explicit fallback with user-visible reason.

## Anti-patterns

- Hardcoded `optimize_subtitles=False` at call sites.
- Falling back from `dubbing_vi` to subtitle without a visible/recorded rule.
- Network access while Offline Lock is active.
- Widget access from background threads or heavy work on Qt main thread.
- Multiple heavy GPU models running concurrently without admission control.
- Whole-project cache bust after a one-cue edit; cache reuse without provenance.
- Silent success for empty audio, missing model, provider mapping error or invalid export.

</conventions>

<constraints>

## Must have

- Windows source-run and a reproducible portable build for the owner's machine.
- Chinese/English explicit source selection; Vietnamese subtitle and dubbing outputs.
- Review checkpoints and manual edits preserved across reopen/rerun.
- VieNeu default, NVENC preference with CPU fallback, Offline Lock option.
- Tests and measured evidence sufficient for the Day 7/14/21 gates.

## Must not

- Add lip-sync/OmniVoice production or redesign the whole UI during this milestone.
- Depend on unlicensed/unknown model or voice assets in the delivered package.
- merge GPL competitor code into the Apache core.
- Log secrets or send media/text to a provider without an explicit profile/action.
- Claim measured quality or performance before the benchmark report exists.

## Hardware/software constraints

- Target GPU: NVIDIA GeForce RTX 3060, 12 GB dedicated VRAM.
- Target memory: 32 GB RAM; operational target ≤24 GB peak.
- CPU model is unknown and must be captured by benchmark tooling.
- Python baseline: 3.11; Windows 10/11; CUDA/CTranslate2 combination must be pinned and smoke-tested.
- One developer/primary user; 21 calendar days; feature freeze at end of Day 7.

## Security requirements

- Secrets only in user environment/settings; redact them from logs/reports.
- Remote API is optional, local-bind by default and token-protected when enabled.
- Validate untrusted paths/media/JSON and set request/payload/time bounds.
- Resource packs include source, revision, license and checksum.

</constraints>

<external_dependencies>

## Libraries and runtimes

| Dependency | Version policy | Purpose |
|---|---|---|
| Python | 3.11.x pinned environment | Application runtime |
| PySide6 | Pin in milestone lock | Desktop UI/QThread/signals |
| Faster-Whisper | Pin package + model revision | Local zh/en ASR |
| CTranslate2 | `>=4.6.3,<5` initially; lock tested build | GPU inference runtime |
| VieNeu | Pin package/model revision | Default Vietnamese TTS |
| FFmpeg/ffprobe | Bundled/versioned binary | Media probe, mix and export |
| PyInstaller | Pin build environment | Windows portable build |
| pytest | Add/pin in dev requirements | Deterministic verification |

## Optional services

| Service | Mode | Rule |
|---|---|---|
| OpenAI-compatible translation provider | Hybrid only | Explicit configuration, redacted logs, provenance in output |
| Google AI Studio / OpenAI / Ollama | Candidate adapters | Benchmark/configure one primary and one fallback; do not couple domain model |
| Google Web fallback | Compatibility | Disabled by Offline Lock; not relied on for deterministic acceptance |

</external_dependencies>

## ViePilot active profile (FEAT-009)

| Field | Value |
|---|---|
| Profile ID | `personal` |
| Binding | `.viepilot/META.md` |
| Source | `~/.viepilot/profiles/personal.md` |
| Applied context | Vietnamese UI, local-first privacy, accuracy/speed, Advanced technical settings, strict third-party attribution |

## Phase assignment completeness

All 21-day features and all six UI pages are assigned to Roadmap Phases 1–3. Product Phase 2/3 features outside the milestone are explicitly listed under anti-goals/future horizon, not left unassigned. Open questions (CPU, provider, media mix, cloning/lip-sync depth) are converted to benchmark assumptions or deferred scope and do not block execution.
