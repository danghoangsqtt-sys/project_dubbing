# CapCap — System Rules

<architecture_rules>

## Architecture rules

1. Dependency direction: UI → controller/worker adapter → workflow → domain/service/protocol → concrete engine/external tool. Reverse imports and circular dependencies are forbidden.
2. Qt widgets live only on the main thread. Long inference, HTTP, file conversion and FFmpeg operations run in a worker or subprocess and communicate through queued signals.
3. `ProjectState`/canonical segments are authoritative; widgets render copies/view models and issue commands.
4. `original_text`, `subtitle_vi` and `dubbing_vi` are separate persisted fields. No implicit destructive synchronization.
5. One heavy GPU stage at a time. Every acquisition releases in `finally`; telemetry records peak use.
6. Engines implement capability contracts; fallback is explicit, logged and visible in UI.
7. Project writes are UTF-8, versioned and atomic. Migration never overwrites the only recoverable copy.
8. Cache is content/provenance addressed and dependency-aware; a cached failure/silence is invalid.
9. Offline Lock is enforced below the UI at provider/resource boundaries.
10. Export is a single final video encode and success requires ffprobe validation.

</architecture_rules>

<coding_rules>

## Python coding rules

- Target Python 3.11; use type hints on changed public boundaries.
- Use `pathlib.Path` or validated absolute paths. Never construct shell strings from user paths.
- Call subprocesses with argument lists, `shell=False`, bounded timeouts/cancellation and checked exit codes.
- Prefer small pure functions for segment validation, signatures, timing and command generation.
- Copy/normalize inputs at workflow boundaries; do not mutate a dictionary shared across threads.
- Exceptions at engine boundaries become typed/actionable stage failures. If a broad catch is required for containment, log traceback internally and preserve a safe user message.
- Code identifiers/comments are English; user-visible text/documentation are Vietnamese.
- Any new provider, model or voice field must be included in provenance/cache invalidation tests.
- Do not change a dirty user-owned file outside the active task; inspect and merge carefully.

## Testing rules

- Add pytest with separate deterministic and hardware/integration markers.
- Deterministic tests must not download models, call cloud services or require the GPU.
- Use `tmp_path`; monkeypatch the name looked up by the code; block outbound HTTP by default.
- Minimum milestone gate is risk-based, not an invented coverage percentage: every P0 rule has an automated test or a recorded hardware acceptance case.
- Parametrize zh/en, Unicode, empty/error, reorder/missing-ID and cache-signature cases.
- Hardware benchmark output must record CPU/GPU/RAM, dependency/model revisions, input hashes and configuration.

</coding_rules>

<comment_standards>

## Comment standards

Comments explain intent, invariants, side effects or upstream compatibility—not obvious syntax.

```python
# Good: Mix-only controls are excluded so a volume edit does not regenerate every TTS cue.
signature = build_voice_signature(segments, voice_name=voice)

# Bad: Build signature.
signature = build_voice_signature(segments, voice_name=voice)
```

Use `TODO(owner): reason — issue/task` only for accepted backlog. Delete commented-out code and use Git history.

</comment_standards>

<versioning>

## Versioning

Use Semantic Versioning. Current milestone: `0.1.0`; development may use `0.1.0-alpha`, Day 7 `0.1.0-beta.1`, Day 14 `0.1.0-rc.1`, Day 21 `0.1.0` when all gates pass.

</versioning>

<git_conventions>

## Git conventions

Use Conventional Commits: `<type>(<scope>): <subject>`. Scopes: `ui`, `state`, `asr`, `translate`, `tts`, `media`, `resources`, `export`, `test`, `docs`, `build`.

- One coherent task per commit; include tests/evidence with the change.
- Never rewrite or discard unrelated user changes.
- Do not commit secrets, downloaded model weights, generated videos, caches or private reference voices.
- Tag milestone gates only after verification evidence is saved.

</git_conventions>

<changelog_standards>

## Changelog standards

Follow Keep a Changelog headings in order: Added, Changed, Deprecated, Removed, Fixed, Security. Record user-visible behavior, migrations, model/runtime changes and known limits; do not duplicate commit logs.

</changelog_standards>

<quality_gates>

## Quality gates

### Every task

- Acceptance criteria pass with command/evidence recorded.
- Relevant deterministic tests pass; hardware work includes its environment manifest.
- No new secret/network/privacy breach; no regression to independent text fields or stable IDs.
- UI changes match root `design.md`, remain responsive and show actionable stage status.
- Documentation/cache/schema contracts are updated when a boundary changes.

### End of Day 7

- Two 2–5 minute clips (zh and en) run through SRT and dubbed MP4.
- Save/reopen preserves edits; SRT works with forced TTS failure.
- P0 mapping/optimization/provenance issues are fixed; feature freeze begins.

### End of Day 14

- No open P0; deterministic suite and benchmark rerun from documented commands.
- 6–10 clip golden set, 10 short runs and 20–30 minute soak evidence saved.
- Portable/source build smoke-tested; dependency/model/resource revisions pinned.

### End of Day 21

- RC regression passes; package, checksum, guide, demo and measured report exist.
- Third-party code/model/voice manifest is complete.
- No unsupported speed/quality claims; limitations and deferred features are explicit.

</quality_gates>

<do_not>

## Forbidden patterns

- Do not hardcode credentials, tokens or provider selection.
- Do not allow network access under Offline Lock.
- Do not block Qt's main thread or touch widgets from workers.
- Do not call `QThread.terminate()` as routine cancellation.
- Do not run heavy ASR and TTS GPU models concurrently on this target.
- Do not hardcode `optimize_subtitles=False` across entry points.
- Do not collapse source/subtitle/dubbing text into one mutable field.
- Do not reuse cache across changed provider/model/prompt/voice/normalizer provenance.
- Do not accept empty audio or unprobed media export as success.
- Do not integrate competitor code without compatible license and clean attribution.
- Do not add lip-sync, OmniVoice production or major refactors during the frozen milestone.

</do_not>
