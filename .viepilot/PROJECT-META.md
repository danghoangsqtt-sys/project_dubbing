# CapCap — Project Metadata

## Project

| Field | Value |
|---|---|
| Name | CapCap |
| Description | Windows desktop studio translating Chinese/English video into Vietnamese subtitles and dubbing |
| Milestone | Personal Usable v0.1 — 21-day delivery |
| Inception year | 2026 |
| License | Apache-2.0; retain upstream and third-party attribution |
| Organization | Personal / Cá nhân |
| Website | Not configured |

## Repository

| Field | Value |
|---|---|
| Personal repository | https://github.com/danghoangsqtt-sys/project_dubbing.git |
| Issues | https://github.com/danghoangsqtt-sys/project_dubbing/issues |
| Upstream | https://github.com/notepower2k1/CapCap |
| Primary branch | `main` |
| CI/CD | Not configured; local Windows verification is authoritative for this milestone |

## Lead developer

| Field | Value |
|---|---|
| Name | `@dhsystem.sys` |
| Email | `danghoang.sqtt@gmail.com` |
| GitHub | [@danghoangsqtt-sys](https://github.com/danghoangsqtt-sys) |
| Role | Project lead, core developer, primary user |

## Python package structure

Java/Maven coordinates are not applicable. Python import roots are intentionally retained to avoid a 21-day full rewrite.

| Root | Responsibility |
|---|---|
| `ui/` | PySide6 views, controllers, dialogs, worker adapters |
| `app/core/` | Domain models, project state, engine contracts |
| `app/services/` | Project/resource/voice services and cache signatures |
| `app/workflows/` | Prepare, voice, export orchestration |
| `app/engines/` | ASR/TTS/translation/media adapters |
| `docs/` | User, technical and brainstorm documentation |
| `.viepilot/` | Executable project context and milestone state |

Artifact identifier: `capcap`. Optional reverse-domain identifier for future packaging: `io.github.danghoangsqttsys.capcap`.

## File headers and attribution

New original Python modules may use:

```python
"""CapCap module purpose.

Copyright 2026 CapCap contributors.
Licensed under the Apache License, Version 2.0.
"""
```

Do not mass-add headers to existing upstream files. Preserve original notices. Third-party code, models, binaries and voice assets require a manifest containing source, version/revision, checksum, license and distribution status.
