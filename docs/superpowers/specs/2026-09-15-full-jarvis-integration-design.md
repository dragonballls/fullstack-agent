# Full Jarvis Integration Design

## Goal

Turn the existing guarded self-coding engine, isolated `quality_of_life/` capability layer, and Jarvis voice configuration into one discoverable, testable fullstack-agent installation without coupling optional capabilities tightly enough to break the base stack.

## Architecture

`CLAUDE.md` and `fullstack-agent.md` remain the agent/installer control plane. `self_coding/` remains responsible only for guarded repository coding passes. `quality_of_life/` remains a separate capability plane containing permissions, registration, orchestration, desktop control, screen capture, browser control, background jobs, and cloud routing. Voice configuration remains documented by `JARVIS_VOICE.md` and is wired by the installer into the existing backtalk setup rather than implemented as a second voice stack.

The integration boundary is explicit: the installer tells the agent when the capabilities exist; the quality-of-life registry exposes capability names; the orchestrator checks policy before dispatch; optional dependencies fail closed and must not prevent the base installer or self-coding code from importing.

## Integration requirements

1. Update the installer control plane so it explicitly discovers `quality_of_life/`, reads its README, validates its optional dependencies, and registers the available tools without replacing existing stack components.
2. Preserve deny-by-default permissions and make confirmation hooks visible to the caller for mutating capabilities.
3. Keep self-coding separate and invoke it only through `self_coding.run` / `SelfCodingAgent`, retaining clean-tree, isolated-branch, verification, commit, and rollback behavior.
4. Keep cloud model routing cloud-only and deterministic; missing credentials or failed providers must produce a clear failure rather than silently selecting a local LLM.
5. Merge and wire `JARVIS_VOICE.md` into installer instructions. ElevenLabs credentials must never be committed, logged, or placed in tracked files; the requested voice must be looked up rather than given an invented ID; voice setup is not successful until a real speech test passes.
6. Ensure optional QOL dependencies do not become mandatory for the basic installer/self-coding path.
7. Expand regression tests around registry/orchestrator integration, optional dependency behavior, voice-document discoverability, installer instructions, and self-coding isolation.
8. Keep the existing cross-platform QOL CI and self-coding CI passing. Add integration checks so a broken import or stale installer reference blocks CI.
9. Do not copy the old Mark-LIII repository wholesale. Reuse only patterns that fit the existing interfaces and safety boundaries.

## Failure handling

A missing optional dependency must result in an explicit capability-unavailable state, not a process-wide import failure. A disabled capability must be rejected before its action executes. A router with missing credentials or exhausted providers must fail with provider-specific diagnostics without exposing secrets. A failed self-coding verification must continue to roll back to the exact baseline.

## Verification

Automated verification must include compile/import checks, unit/regression tests, and the full existing Windows/Linux Python 3.11/3.12/3.13 QOL matrix. Integration verification must confirm the installer references current QOL and voice files. Physical Windows-only behavior such as actual mouse movement, screenshots, browser launches, microphone/speaker output, and camera permissions cannot be truthfully certified by hosted CI and must remain explicitly marked for end-user machine validation.
