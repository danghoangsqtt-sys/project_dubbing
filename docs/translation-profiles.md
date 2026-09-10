# Translation profiles and Offline Lock

CapCap keeps two different Vietnamese fields for every cue: `subtitle_vi` is the faithful, readable subtitle and `dubbing_vi` is a shorter spoken rewrite for TTS. Editing or regenerating one does not overwrite the other.

## Hybrid profile

Hybrid mode first uses the configured OpenAI-compatible translator (Google AI Studio, OpenAI, or local Ollama). If that primary request is unavailable or invalid, CapCap reports a warning and falls back to Google web translation. The provider that actually produced each cue is retained in metadata/provenance.

Subtitle optimization is a real setting. It runs only when enabled and when the configured AI provider completed the primary translation; it never changes cue count/order. The output retains stable IDs and receives QA flags if source numbers or Latin-script proper names/product identifiers are absent.

## Offline Lock

Set `CAPCAP_OFFLINE_LOCK=1` (the Settings UI exposes this in Task 1.11) to block public HTTP(S) provider requests below the UI. Loopback URLs such as `http://localhost:11434/v1` are allowed so a local Ollama server can translate. Offline Lock forces the Ollama route and returns an actionable error when it is missing or fails; it never falls back to Google, OpenAI, or Google AI Studio.

## Dubbing rewrite

When AI dubbing rewrite is enabled, the voice workflow asks the configured translator for a concise spoken variant constrained by cue duration. It validates the result, stores it in `dubbing_vi`, and leaves `subtitle_vi` intact. TTS always prefers a non-empty `dubbing_vi`, including generated rewrites that were not manually edited.

QA flags are review signals, not automatic substitutions. A human should resolve missing names/numbers before final export.
