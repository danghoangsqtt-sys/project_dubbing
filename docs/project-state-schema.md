# CapCap project state schema

CapCap stores each local project as versioned UTF-8 JSON. Schema version 2 makes the project file the authoritative owner of canonical segments while retaining JSON artifacts for compatibility, inspection, and stage outputs.

## Project schema version 2

`project.json` contains:

- `schema_version`: current project schema version (`2`).
- Project identity and source: `project_id`, `project_root`, `input_video`, `source_fingerprint`.
- Language/profile controls: `input_language`, `target_language`, `mode`, `translator_ai`, `translator_style`.
- `segments`: ordered canonical segment records.
- `steps`, `settings`, and `artifacts`: resumable stage state and artifact paths.
- `provenance`: project-level producer and input-signature records keyed by stage.
- `migration_history`: schema transitions applied to the project.
- `extensions`: unknown legacy top-level data retained during migration.
- `created_at` and `updated_at`: UTC ISO-8601 timestamps.

Files created before `schema_version` existed are treated as schema version 1. A project from a newer unsupported schema is rejected instead of being silently downgraded.

## Canonical segment schema version 2

Each segment persists these independent fields:

| Field | Meaning |
|---|---|
| `id` | Stable non-empty string ID. Existing numeric IDs are preserved as strings; only missing IDs receive deterministic `seg-000001` values. |
| `start`, `end` | Seconds with `0 <= start < end`. |
| `source_language` | Explicit source language when known. |
| `original_text` | Source/ASR text; translation never overwrites it. |
| `subtitle_vi` | Faithful Vietnamese subtitle text. |
| `dubbing_vi` | Independently editable Vietnamese spoken text. |
| `speaker_id`, `voice_profile_id` | Speaker identity and selected voice mapping. |
| `confidence`, `qa_flags` | Confidence and review issues. |
| `provenance` | Per-stage provider/engine/model/revision/prompt/schema/signature facts. |
| `voice_file`, `status`, `metadata` | Generated cue audio, workflow status, and compatible supplemental data. |

During the brownfield transition, Python accessors named `raw_translation`, `refined_translation`, `final_text`, and `tts_text` remain available. New JSON writes use only canonical names. Legacy flat fields that have no canonical equivalent are retained under `metadata.legacy_fields`.

## Migration and recovery

When `ProjectService.load_project()` opens a schema-v1 project, it:

1. Parses and validates the legacy object.
2. Recovers canonical segments from `translation_final`, `translation_refined`, `translation_raw`, or `transcript_segments` when the old project file does not own segments.
3. Creates `project.json.schema-v1.bak` with the exact original bytes. An existing backup is never overwritten.
4. Writes schema v2 through a sibling temporary file, flushes and synchronizes it, then replaces `project.json` atomically.

If migration cannot prove a safe mapping—for example duplicate IDs, reordered explicit IDs, invalid timing, or a future schema—it raises an actionable exception and leaves the backup/original available.

All JSON artifacts written through `ProjectService` use the same atomic write primitive. Artifact paths are constrained to the project directory.

## Provenance and cache signatures

Translation signatures include stable segment ID/timing/source text, language, polish/optimization/style configuration, provider, engine, model, model revision, prompt version, schema version, normalizer version, and configured fallback identity.

Voice signatures include stable segment ID/timing/dubbing text, voice profile, timing mode, TTS provider/engine/model/revision, rewrite prompt version, schema version, normalizer version, and pronunciation-dictionary signature. Original/dub mix volumes and background selection are deliberately excluded because they belong to the later mix stage and must not regenerate TTS.

API keys, tokens, media contents, and secret endpoint credentials are never part of persisted provenance or signatures.
