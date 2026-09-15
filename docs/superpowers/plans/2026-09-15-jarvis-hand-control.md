# Jarvis Hand Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, failure-isolated webcam hand-control subsystem that translates stable gestures into the existing guarded Jarvis computer-control capabilities.

**Architecture:** A local tracker adapter emits normalized hand events; a deterministic interpreter applies confidence/debounce/cooldown gates; a bridge maps only approved gestures into the existing computer-control layer; a lifecycle manager makes camera/dependency failures non-fatal. Hand control stays optional and does not become a core startup dependency.

**Tech Stack:** Python 3.11–3.13, existing `quality_of_life` capability/policy interfaces, pytest; optional browser/MediaPipe tracker integration kept behind an adapter boundary.

**Spec:** `docs/superpowers/specs/2026-09-15-jarvis-hand-control-design.md`

## Global Constraints

- Core Jarvis startup must not require a webcam, browser, or optional tracking dependency.
- Gesture-generated input must remain inside the existing capability/permission/policy path.
- Hand control must be explicitly enableable and immediately disableable.
- No arbitrary shell execution or unbounded keyboard injection may be introduced.
- Existing voice, browser, location-memory, self-coding, and startup behavior must remain unchanged.
- Existing tests and Windows/Linux CI must remain green.

### Task 1: Inspect existing computer-control interfaces

**Files:**
- Read: `quality_of_life/capabilities.py`
- Read: `quality_of_life/permissions.py`
- Read: `quality_of_life/runtime.py`
- Read: `quality_of_life/agent_orchestrator.py`
- Read: relevant existing computer-control tests

**Interfaces:**
- Consumes: existing capability names, runtime method signatures, permission checks, and test conventions.
- Produces: exact integration seams used by later tasks.

- [ ] **Step 1:** Read the listed modules and locate the smallest existing API for mouse movement, click, drag, scroll, and capability authorization.
- [ ] **Step 2:** Record the exact method/class names in the implementation branch notes before adding code.
- [ ] **Step 3:** Run the current focused computer-control tests to establish a green baseline.

### Task 2: Add deterministic gesture-domain models and interpreter

**Files:**
- Create: `quality_of_life/hand_control.py`
- Test: `tests/test_hand_control.py`

**Interfaces:**
- Consumes: normalized tracker samples defined as small immutable Python data objects.
- Produces: `HandGesture`, `HandEvent`, and `HandGestureInterpreter.interpret(sample, timestamp) -> tuple[HandEvent, ...]`.

- [ ] **Step 1:** Write failing tests for cursor motion, quick pinch click, held pinch drag, vertical scroll, pause/resume, emergency stop, confidence rejection, and cooldown/debounce.
- [ ] **Step 2:** Run `pytest tests/test_hand_control.py -v` and confirm failures are due to missing hand-control behavior.
- [ ] **Step 3:** Implement only the minimal immutable models and interpreter required by the failing tests.
- [ ] **Step 4:** Re-run the focused tests until green.
- [ ] **Step 5:** Refactor only without changing behavior; re-run the focused suite.

### Task 3: Add guarded computer-control bridge

**Files:**
- Modify: the smallest existing QOL runtime/capability module identified in Task 1.
- Test: `tests/test_hand_control_integration.py`

**Interfaces:**
- Consumes: `HandEvent` from `quality_of_life.hand_control`.
- Produces: `HandControlBridge.dispatch(event)` with no direct shell execution and with existing capability/policy checks enforced.

- [ ] **Step 1:** Write failing integration tests proving allowed movement/click/scroll events reach the existing runtime operation while disabled or unauthorized events do not execute.
- [ ] **Step 2:** Run `pytest tests/test_hand_control_integration.py -v` and verify expected failures.
- [ ] **Step 3:** Implement the bridge using existing QOL interfaces rather than duplicating mouse/keyboard mechanisms.
- [ ] **Step 4:** Re-run the focused integration tests until green.
- [ ] **Step 5:** Run the related existing computer-control tests to confirm no regression.

### Task 4: Add isolated lifecycle/configuration

**Files:**
- Create: `quality_of_life/hand_control_runtime.py`
- Modify: `quality_of_life/manifest.py` only if capability registration is required by existing conventions.
- Test: `tests/test_hand_control_runtime.py`

**Interfaces:**
- Consumes: tracker adapter protocol and `HandControlBridge`.
- Produces: `HandControlRuntime.start()`, `.stop()`, `.enabled`, and graceful unavailable/degraded status.

- [ ] **Step 1:** Write failing tests for missing camera, denied permissions, absent optional tracker dependency, start/stop idempotence, and disabled-by-default behavior.
- [ ] **Step 2:** Verify the new tests fail for the intended missing lifecycle behavior.
- [ ] **Step 3:** Implement the lifecycle manager so tracker errors are contained and reported as unavailable without raising through core Jarvis startup.
- [ ] **Step 4:** Add configuration defaults that keep hand control disabled unless explicitly enabled.
- [ ] **Step 5:** Re-run focused runtime tests and relevant manifest/registry tests.

### Task 5: Add tracker adapter boundary

**Files:**
- Create: `quality_of_life/hand_tracking.py`
- Test: `tests/test_hand_tracking.py`
- Modify: dependency/config files only if an optional dependency is already compatible with repository conventions.

**Interfaces:**
- Consumes: camera/tracker frames from the selected local tracker implementation.
- Produces: normalized samples accepted by `HandGestureInterpreter`; failures become typed availability errors.

- [ ] **Step 1:** Write failing adapter-contract tests with deterministic fixture frames and unavailable-camera cases.
- [ ] **Step 2:** Verify the tests fail because the adapter contract is absent.
- [ ] **Step 3:** Implement an adapter that does not make the dependency mandatory for importing Jarvis; prefer consuming the existing barehands-compatible tracker boundary rather than copying its application UI.
- [ ] **Step 4:** Re-run adapter tests and import the core QOL package without the optional tracker installed.

### Task 6: Wire end-to-end and document operation

**Files:**
- Modify: `quality_of_life/agent_orchestrator.py` only where needed to expose lifecycle/commands.
- Create or modify: focused QOL documentation for camera permissions, gestures, pause/stop controls, and degraded behavior.
- Test: `tests/test_hand_control_e2e.py`

**Interfaces:**
- Consumes: runtime, bridge, interpreter, and tracker adapter.
- Produces: end-to-end enable → sample → gesture event → guarded computer action flow.

- [ ] **Step 1:** Write a failing end-to-end test covering enable, accepted gesture, guarded dispatch, pause, and stop.
- [ ] **Step 2:** Implement the smallest wiring needed to pass the test.
- [ ] **Step 3:** Add user-facing documentation with explicit permissions and disable controls.
- [ ] **Step 4:** Re-run all hand-control tests plus the full repository test suite.

### Task 7: Full CI verification and PR gate

**Files:**
- Modify only tests/docs/config discovered necessary by previous tasks.

- [ ] **Step 1:** Run the repository's full local test command documented by the project.
- [ ] **Step 2:** Confirm optional-dependency imports and headless CI paths succeed.
- [ ] **Step 3:** Push the feature branch and open a PR into `main`.
- [ ] **Step 4:** Wait for all required QOL, integration, self-coding, and Windows maintenance workflows to finish.
- [ ] **Step 5:** Inspect every job result; merge only when every required job is successful and no required check is failing.
- [ ] **Step 6:** Recheck post-merge `main` workflow results against the merge commit before declaring completion.
