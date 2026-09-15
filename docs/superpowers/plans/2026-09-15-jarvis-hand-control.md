# Jarvis Hand Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, failure-isolated webcam hand-control subsystem that translates stable gestures into the existing guarded Jarvis computer-control capabilities.

**Architecture:** Local normalized hand samples feed a deterministic interpreter with confidence/debounce/cooldown gates. A bridge sends only approved events through existing computer-control policy, while a lifecycle adapter isolates camera/tracker failures and lazy-loads optional dependencies.

**Tech Stack:** Python 3.11–3.13, existing `quality_of_life` modules, pytest, optional MediaPipe/browser tracker integration behind an adapter boundary.

**Spec:** `docs/superpowers/specs/2026-09-15-jarvis-hand-control-design.md`

## Global Constraints

- Core Jarvis startup must not require a webcam, browser, or optional tracking dependency.
- Gesture-generated input remains inside existing capability/permission/policy interfaces.
- Hand control stays disabled until explicitly enabled and must have immediate stop controls.
- No arbitrary shell execution or unbounded keyboard injection.
- Existing voice, browser, location-memory, self-coding, and startup behavior remains unchanged.
- All existing CI must remain green.

### Task 1: Read existing computer-control interfaces

**Files:** existing `quality_of_life/capabilities.py`, `permissions.py`, `runtime.py`, `agent_orchestrator.py`, related tests.

**Interfaces:** determine exact existing mouse/click/scroll authorization and invocation names.

- [ ] Read the listed files and locate the smallest existing capability and runtime seams.
- [ ] Run the existing focused computer-control tests as the baseline.

### Task 2: Add gesture models/interpreter with TDD

**Files:** Create `quality_of_life/hand_control.py`; Test `tests/test_hand_control.py`.

**Interfaces:** `HandSample`, `HandEvent`, `HandGestureInterpreter.interpret(sample, timestamp) -> tuple[HandEvent, ...]`.

- [ ] Write failing tests for cursor movement, pinch click, drag, scroll, pause/resume, emergency stop, confidence rejection, and cooldown/debounce.
- [ ] Verify those tests fail for the intended missing feature.
- [ ] Implement the minimal interpreter and models.
- [ ] Re-run focused tests until green.

### Task 3: Guarded bridge

**Files:** modify the smallest existing runtime/capability module; create `tests/test_hand_control_integration.py`.

**Interfaces:** `HandControlBridge.dispatch(event)` uses existing capability/policy checks and never shells out directly.

- [ ] Write and verify failing integration tests.
- [ ] Implement the bridge against existing QOL interfaces.
- [ ] Run focused and related computer-control tests until green.

### Task 4: Isolated lifecycle

**Files:** Create `quality_of_life/hand_control_runtime.py`; Test `tests/test_hand_control_runtime.py`; registry changes only if required.

**Interfaces:** `HandControlRuntime.start()`, `.stop()`, `.enabled`, and typed unavailable/degraded status.

- [ ] Write failing tests for no camera, denied permission, missing optional dependency, disabled-by-default, and idempotent lifecycle.
- [ ] Implement lazy/isolated startup and error containment.
- [ ] Run focused runtime/registry tests.

### Task 5: Tracker adapter

**Files:** Create `quality_of_life/hand_tracking.py`; Test `tests/test_hand_tracking.py`.

**Interfaces:** tracker adapter produces normalized `HandSample` objects; missing hardware/dependencies become typed availability states.

- [ ] Write deterministic adapter-contract tests.
- [ ] Implement an optional adapter that can consume the existing barehands/MediaPipe approach without importing it from core startup.
- [ ] Verify core QOL imports without the optional tracker installed.

### Task 6: End-to-end wiring/docs

**Files:** minimal changes to `quality_of_life/agent_orchestrator.py`; focused QOL documentation; Test `tests/test_hand_control_e2e.py`.

**Interfaces:** enable → tracker sample → interpreter → guarded bridge → stop/pause.

- [ ] Write a failing end-to-end test.
- [ ] Implement only necessary wiring.
- [ ] Document camera permissions, gestures, enable/disable, and degraded mode.
- [ ] Run all hand-control tests and the full repository suite.

### Task 7: CI/merge gate

- [ ] Run the documented full local suite where available; otherwise use repository CI as the authoritative execution environment.
- [ ] Open a PR into `main` only after the branch is internally consistent.
- [ ] Require all existing QOL, integration, self-coding, and Windows maintenance checks to pass.
- [ ] Merge only on all-green required checks.
- [ ] Recheck post-merge `main` before declaring completion.
