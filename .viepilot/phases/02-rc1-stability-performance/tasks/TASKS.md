# Phase 2 Task Cards

## 2.1 Golden/test harness

Build rights-cleared metadata and deterministic tests for zh/en, Unicode, IDs, reopen, provider mapping/errors, TTS failure, timing and export commands. Network/model downloads are disabled in unit tests.

## 2.2 Cache/selective rerun

Prove full provenance invalidation and downstream-only cue invalidation; measure cold versus unchanged rerun.

## 2.3 Performance/timing

Record machine and model facts with every run. Compare under identical settings; present targets and observed values separately.

## 2.4 Reliability

Test zero-network Offline Lock, cooperative cancel, resume after interruption, atomic recovery and valid-artifact preservation.

## 2.5 Resource lock

Pin packages/model revisions/binaries, build the license/checksum/readiness manifest and test missing/incompatible states.

## 2.6 Soak/UI QA/fixes

Run 10 short iterations and a 20–30 minute case; fix P0 and direct accuracy/timing/usability P1 only; backlog P2.

## 2.7 Package/RC1

Build source/portable paths and smoke both. Create RC tag only after report shows no P0 and rerunnable evidence.
