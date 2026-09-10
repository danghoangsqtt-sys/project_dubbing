# Launcher UI contract

The production Launcher follows root `design.md` and the approved `launcher.html`. It is a readiness and resume surface, not a one-click processing screen.

- Vietnamese create/open actions are the primary entry points.
- Device, Hybrid profile and resource readiness are separate cards. Every color has a text label.
- Hardware probing runs outside the Qt GUI thread and returns through a queued signal.
- Recent projects are read without migration or mutation. Cards report language, cue count, last completed stage and a conservative progress value.
- Missing source paths are removed from recent history. Cached thumbnails are used immediately; FFmpeg thumbnail generation does not block Launcher painting.
- A local MP4, MKV, AVI, MOV or WEBM can be dropped anywhere on the window. Drop and file-picker paths converge on the same resource gate and preparation flow.
- Data cleanup remains destructive, visibly styled and confirmation-gated. It removes generated projects/cache, not source video or model packs.

The Launcher does not claim lip-sync or full offline readiness. “Hybrid” states that only text may leave the machine; Offline Lock is configured in Resources & Settings.
