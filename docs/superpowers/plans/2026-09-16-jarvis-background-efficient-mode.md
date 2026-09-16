# Jarvis Background-Efficient Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Jarvis's presentation layer low-overhead while preserving always-on voice wake listening and any explicitly active hand-control session.

**Architecture:** A thread-safe lifecycle controller marks presentation work as foreground-only. A background runtime keeps voice listening alive and treats hand control as an independent service, so minimizing changes presentation state without disabling user-authorized capabilities. The repository exposes this as a host integration contract because the actual native desktop shell is outside this source-layer repository.

**Tech Stack:** Python 3.11–3.13, unittest, threading, existing Jarvis quality-of-life runtime.

**Spec:** `docs/superpowers/specs/2026-09-16-jarvis-background-efficient-mode-design.md`

## Global Constraints

- Minimize must not stop voice wake listening.
- Minimize must not stop an active hand-control session.
- Foreground-only UI work may be suspended while minimized.
- Voice wake processing remains local; cloud requests occur only after wake handling.
- Hand control remains explicit and independently stoppable.
- Quit/stop must stop background services cleanly.
- Missing optional voice dependencies fail closed rather than taking down Jarvis core.
- CI must pass on Ubuntu and Windows with Python 3.11, 3.12, and 3.13.

---

### Task 1: Lifecycle controller

**Files:**
- Create: `quality_of_life/background_mode.py`
- Test: `tests/test_background_mode.py`

**Interfaces:**
- Consumes: host lifecycle events.
- Produces: `BackgroundModeController.enter_background()`, `enter_foreground()`, and `status()`.

- [x] Define `BackgroundMode` and `BackgroundComponent` with `always` and `foreground_only` policies.
- [x] Add idempotent background/foreground transitions.
- [x] Isolate callback failures and report degraded components.
- [x] Cover lifecycle transitions and failure isolation with unittest.

### Task 2: Voice lifecycle

**Files:**
- Modify: `quality_of_life/voice_listener.py`
- Test: `tests/test_voice_listener.py`

**Interfaces:**
- Consumes: existing `LocalWakeWordListener.run_forever()`.
- Produces: `start()`, `stop()`, `running`, and `last_error`.

- [x] Add one daemon listener thread with idempotent start.
- [x] Add stop event and bounded thread join.
- [x] Preserve local wake detection and no-network listener behavior.
- [x] Add lifecycle regression coverage.

### Task 3: Background service coordinator

**Files:**
- Create: `quality_of_life/background_runtime.py`
- Modify: `quality_of_life/__init__.py`
- Test: `tests/test_background_mode.py`

**Interfaces:**
- Consumes: `BackgroundModeController`, `LocalWakeWordListener`, `HandControlRuntime`.
- Produces: `JarvisBackgroundRuntime.start()`, `stop()`, `minimize()`, `restore()`, and `status()`.

- [x] Keep voice service alive through minimize.
- [x] Keep hand-control service untouched by minimize.
- [x] Stop both services cleanly on application shutdown.
- [x] Export the coordinator for desktop-host integration.
- [x] Add an end-to-end lifecycle unit test with mocked services.

### Task 4: Documentation and release verification

**Files:**
- Create: `docs/superpowers/specs/2026-09-16-jarvis-background-efficient-mode-design.md`
- Modify: `JARVIS_DOWNLOAD.md`
- Modify: `JARVIS_SETUP.md`

**Interfaces:**
- Consumes: runtime integration contract.
- Produces: documented minimize/restore/quit semantics.

- [ ] Document that the source-layer repository exposes host lifecycle hooks rather than pretending to contain a native desktop shell.
- [ ] Document resource expectations: minimized mode is low-overhead, not literally zero-resource.
- [ ] Run the full cross-platform release/test gate before merge.
