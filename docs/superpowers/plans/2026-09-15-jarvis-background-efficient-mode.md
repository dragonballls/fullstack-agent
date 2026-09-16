# Jarvis Background-Efficient Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a thread-safe lifecycle contract that lets Jarvis desktop hosts suspend expensive UI work when minimized while keeping active voice, task routing, hand control, and safety services alive.

**Architecture:** Add a small `BackgroundModeController` in the quality-of-life layer. Components register with explicit `always` or `foreground_only` policies and receive `enter_background` / `enter_foreground` callbacks. Extend `JarvisRuntime` with background/foreground/status methods and register the controller lazily, without changing existing capability gates or enabling any hardware capability automatically.

**Tech Stack:** Python 3.11–3.13, standard library threading/dataclasses/enums, unittest, existing JarvisRuntime.

**Spec:** `docs/superpowers/specs/2026-09-15-jarvis-background-efficient-mode-design.md`

## Global Constraints

- Do not enable microphone/camera/mouse control implicitly.
- Background mode must not terminate the process or recreate the core runtime.
- Active hand control and voice listeners remain available in background state.
- Foreground-only presentation work must be suspendable by the desktop host.
- Lifecycle callbacks must be isolated so optional callback failures do not crash Jarvis core.
- Keep the existing six-leg Ubuntu/Windows Python 3.11–3.13 release gate green.

---

### Task 1: Lifecycle controller tests

**Files:**
- Create: `tests/test_background_mode.py`

**Interfaces:**
- Consumes: planned `BackgroundModeController` API.
- Produces: regression coverage for state transitions and callback isolation.

- [ ] **Step 1: Write the failing test**

```python
from quality_of_life.background_mode import BackgroundMode, BackgroundModeController, BackgroundComponent


def test_minimize_suspends_foreground_only_but_keeps_always_component_active():
    events = []
    controller = BackgroundModeController()
    controller.register(BackgroundComponent("ui", "foreground_only", lambda: events.append("ui-bg"), lambda: events.append("ui-fg")))
    controller.register(BackgroundComponent("voice", "always", lambda: events.append("voice-bg"), lambda: events.append("voice-fg")))

    assert controller.enter_background() is True
    assert controller.state is BackgroundMode.BACKGROUND
    assert events == ["ui-bg"]

    assert controller.enter_foreground() is True
    assert controller.state is BackgroundMode.FOREGROUND
    assert events == ["ui-bg", "ui-fg"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_background_mode -v`
Expected: FAIL because `quality_of_life.background_mode` does not exist.

- [ ] **Step 3: Add the minimal controller implementation**

Create `BackgroundMode`, `BackgroundComponent`, and `BackgroundModeController` with idempotent transitions.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_background_mode -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quality_of_life/background_mode.py tests/test_background_mode.py
git commit -m "feat: add background-efficient lifecycle controller"
```

### Task 2: Failure isolation and status contract

**Files:**
- Modify: `tests/test_background_mode.py`
- Modify: `quality_of_life/background_mode.py`

**Interfaces:**
- Consumes: `BackgroundModeController` from Task 1.
- Produces: `status()` and failure-isolated lifecycle callbacks.

- [ ] **Step 1: Add failing tests**

```python
def test_callback_failure_does_not_abort_other_components():
    events = []
    controller = BackgroundModeController()
    controller.register(BackgroundComponent("bad", "foreground_only", lambda: (_ for _ in ()).throw(RuntimeError("boom"))))
    controller.register(BackgroundComponent("good", "foreground_only", lambda: events.append("good")))

    assert controller.enter_background() is True
    assert events == ["good"]
    assert controller.status()["state"] == "background"
    assert controller.status()["degraded"] == ["bad"]


def test_repeated_transitions_are_idempotent():
    calls = []
    controller = BackgroundModeController()
    controller.register(BackgroundComponent("ui", "foreground_only", lambda: calls.append("bg"), lambda: calls.append("fg")))

    assert controller.enter_background() is True
    assert controller.enter_background() is False
    assert controller.enter_foreground() is True
    assert controller.enter_foreground() is False
    assert calls == ["bg", "fg"]
```

- [ ] **Step 2: Run tests to verify the new cases fail**

Run: `python -m unittest tests.test_background_mode -v`
Expected: FAIL on the new status/idempotency behavior before the implementation changes.

- [ ] **Step 3: Implement error capture and status**

Store failed component names in `degraded`, return `state`, `registered`, and `degraded`, and keep iterating after a callback exception.

- [ ] **Step 4: Run tests to verify green**

Run: `python -m unittest tests.test_background_mode -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quality_of_life/background_mode.py tests/test_background_mode.py
git commit -m "test: harden background mode lifecycle"
```

### Task 3: Integrate with JarvisRuntime

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `tests/test_qol_runtime.py`

**Interfaces:**
- Consumes: `BackgroundModeController` from Task 2.
- Produces: `JarvisRuntime.enter_background()`, `JarvisRuntime.enter_foreground()`, and `JarvisRuntime.background_status()`.

- [ ] **Step 1: Add failing runtime tests**

```python
def test_runtime_background_methods_are_safe_and_idempotent():
    runtime = make_runtime()
    assert runtime.enter_background() is True
    assert runtime.background_status()["state"] == "background"
    assert runtime.enter_background() is False
    assert runtime.enter_foreground() is True
    assert runtime.background_status()["state"] == "foreground"
```

- [ ] **Step 2: Run the targeted test**

Run: `python -m unittest tests.test_qol_runtime -v`
Expected: FAIL because the runtime methods are not yet present.

- [ ] **Step 3: Implement lazy controller integration**

Instantiate `BackgroundModeController` in `JarvisRuntime.__init__`, expose the three methods, and register the controller in the existing runtime lifecycle without touching capability policy.

- [ ] **Step 4: Run targeted runtime tests**

Run: `python -m unittest tests.test_qol_runtime -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quality_of_life/runtime.py tests/test_qol_runtime.py
git commit -m "feat: expose Jarvis background lifecycle through runtime"
```

### Task 4: Preserve voice/hand services and document desktop-host integration

**Files:**
- Modify: `quality_of_life/README_HAND_CONTROL.md`
- Modify: `JARVIS_VOICE.md`
- Modify: `JARVIS_ORCHESTRATION.md`
- Create: `docs/jarvis-background-mode.md`

**Interfaces:**
- Consumes: runtime background lifecycle methods.
- Produces: host integration contract stating that minimized mode hides/suspends presentation while active voice/hand services remain alive.

- [ ] **Step 1: Document the exact lifecycle**

Add the contract: minimize invokes `enter_background`; restore invokes `enter_foreground`; quit remains a true shutdown. Explicitly state that the source repository does not contain the native desktop window implementation, so the host must call the lifecycle methods from its minimize/restore events.

- [ ] **Step 2: Add regression assertions for documentation-visible guarantees**

Extend integration documentation tests only where an existing test pattern already verifies required documents.

- [ ] **Step 3: Run targeted voice/hand/integration tests**

Run: `python -m unittest tests.test_hand_control_jarvis tests.test_hand_control_runtime tests.test_voice_listener tests.test_voice_activation tests.test_integration_contract -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add JARVIS_VOICE.md JARVIS_ORCHESTRATION.md quality_of_life/README_HAND_CONTROL.md docs/jarvis-background-mode.md
git commit -m "docs: define minimized background runtime contract"
```

### Task 5: Full verification

**Files:**
- No source changes unless verification identifies a regression.

- [ ] **Step 1: Run complete local suite**

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: PASS with zero failures/errors.

- [ ] **Step 2: Compile all modules**

Run: `python -m compileall quality_of_life self_coding windows_maintenance tests readiness.py`
Expected: PASS.

- [ ] **Step 3: Run Windows-maintenance tests**

Run: `python -m unittest discover -s windows_maintenance/tests -p 'test_*.py' -v`
Expected: PASS.

- [ ] **Step 4: Push branch and inspect GitHub Actions**

Run the existing release gate on the branch and require all six Ubuntu/Windows Python 3.11–3.13 jobs plus portable bundle smoke test to succeed.

- [ ] **Step 5: Open a PR and merge only after all required checks are green**

Use the existing GitHub PR flow with `main` as the base. Do not claim the desktop-host minimize event itself is physically validated by CI.
