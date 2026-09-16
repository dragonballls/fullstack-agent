# Jarvis Windows Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight native Windows chat-bar host that starts the existing Jarvis runtime and routes user requests through the existing policy-aware `AgentOrchestrator`.

**Architecture:** `jarvis_desktop.pyw -> JarvisRuntime -> AgentOrchestrator -> OmniRoute`, with Tkinter used only for the presentation shell. No second tool executor, no unrestricted shell runner, and no bypass around capability or confirmation checks. The host should be launchable with `pythonw.exe` so a normal launch does not leave a PowerShell console open.

**Tech Stack:** Python 3.12-tested runtime, standard-library Tkinter/threading/pathlib, existing `quality_of_life.JarvisRuntime`, existing `AgentOrchestrator`, GitHub Actions unittest/release gate.

**Spec:** `docs/superpowers/specs/2026-09-16-jarvis-universal-tool-broker-design.md`

## Global Constraints

- Use the existing `JarvisRuntime` and `AgentOrchestrator`; do not duplicate capability execution.
- Keep the existing deny-by-default capability policy authoritative.
- Require explicit confirmation before a mutating request is re-executed with `confirmed=True`.
- Never display or persist API keys, OAuth tokens, or other secrets.
- Keep the launcher standard-library-only; optional voice/browser dependencies remain optional.
- Use `pythonw.exe` for normal Windows launching so no console window is required.
- Existing `main` tests and release gate must remain green.

---

### Task 1: Add launcher contract tests

**Files:**
- Create: `tests/test_jarvis_desktop.py`
- Create: `scripts/jarvis_desktop.pyw`

**Interfaces:**
- `build_runtime()` returns a configured `JarvisRuntime` using `CapabilityPolicy()`.
- `JarvisDesktopController.execute_request(text, confirmed=False)` returns the existing `OrchestrationResult` or an error-safe result.
- `JarvisDesktopController.close()` releases the controller without leaving worker threads active.

- [ ] **Step 1: Write failing tests for runtime construction and confirmation forwarding**

```python
from unittest import TestCase
from unittest.mock import Mock

from scripts.jarvis_desktop import JarvisDesktopController, build_runtime


class JarvisDesktopTests(TestCase):
    def test_build_runtime_uses_guarded_runtime(self):
        runtime = build_runtime()
        self.assertIsNotNone(runtime.policy)
        self.assertIn("computer", runtime.available_tools())

    def test_execute_request_forwards_confirmation(self):
        runtime = Mock()
        runtime._assistant_orchestrator.return_value.execute.return_value = "result"
        controller = JarvisDesktopController(runtime=runtime)
        controller.execute_request("open calculator", confirmed=True)
        runtime._assistant_orchestrator.return_value.execute.assert_called_once_with("open calculator", confirmed=True)
        controller.close()
```

- [ ] **Step 2: Run the targeted tests and verify the expected missing-import failure**

Run: `python -m unittest tests.test_jarvis_desktop -v`
Expected: FAIL because the launcher module and controller do not yet exist.

- [ ] **Step 3: Implement the smallest runtime/controller shell**

```python
from quality_of_life.permissions import CapabilityPolicy
from quality_of_life.runtime import JarvisRuntime


def build_runtime():
    return JarvisRuntime(CapabilityPolicy())


class JarvisDesktopController:
    def __init__(self, runtime=None):
        self.runtime = runtime or build_runtime()
        self.orchestrator = self.runtime._assistant_orchestrator()

    def execute_request(self, text, confirmed=False):
        return self.orchestrator.execute(text, confirmed=confirmed)

    def close(self):
        self.runtime.stop_health_monitor()
```

- [ ] **Step 4: Run targeted tests**

Run: `python -m unittest tests.test_jarvis_desktop -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/jarvis_desktop.pyw tests/test_jarvis_desktop.py
git commit -m "feat: add guarded Jarvis desktop launcher"
```

### Task 2: Add the minimal Windows chat bar

**Files:**
- Modify: `scripts/jarvis_desktop.pyw`
- Modify: `tests/test_jarvis_desktop.py`

**Interfaces:**
- `JarvisDesktopApp(root, controller)` builds a compact chat bar.
- `submit()` queues work on a daemon worker thread and returns UI updates to Tk on the main thread.
- `confirm_and_retry()` replays only the pending request with `confirmed=True` after an explicit user confirmation dialog.

- [ ] **Step 1: Add a non-GUI contract test for confirmation state**

```python
from types import SimpleNamespace

    def test_request_result_with_confirmation_does_not_auto_retry(self):
        controller = Mock()
        controller.execute_request.return_value = SimpleNamespace(needs_confirmation=True, text="confirm required")
        result = controller.execute_request("remove app", confirmed=False)
        self.assertTrue(result.needs_confirmation)
        controller.execute_request.assert_called_once_with("remove app", confirmed=False)
```

- [ ] **Step 2: Implement asynchronous submit and bounded UI updates**

Use `threading.Thread(..., daemon=True)` for model/tool execution and `root.after(0, ...)` for UI updates. Disable the send button while a request is running and re-enable it on completion or error.

- [ ] **Step 3: Render confirmation prompts without auto-approval**

When `OrchestrationResult.needs_confirmation` is true, store the exact original request and show a native confirmation dialog. Only the affirmative button calls `execute_request(original_text, confirmed=True)`.

- [ ] **Step 4: Keep the interface minimal**

The window should contain only a compact response label, one single-line input field, and a send button. Escape closes the window; Enter submits. Do not add dashboard panels.

- [ ] **Step 5: Run targeted tests**

Run: `python -m unittest tests.test_jarvis_desktop -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/jarvis_desktop.pyw tests/test_jarvis_desktop.py
git commit -m "feat: add minimal Jarvis chat bar"
```

### Task 3: Add Windows no-console launch wrapper and documentation

**Files:**
- Create: `scripts/start-jarvis.ps1`
- Modify: `JARVIS_SETUP.md`
- Modify: `JARVIS_DOWNLOAD.md`
- Modify: `README.md`

**Interfaces:**
- `scripts/start-jarvis.ps1` locates the repository-relative `.venv\Scripts\pythonw.exe` and starts `scripts\jarvis_desktop.pyw` without opening a persistent PowerShell console.

- [ ] **Step 1: Write the wrapper**

```powershell
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonW = Join-Path $Root '.venv\Scripts\pythonw.exe'
$Entry = Join-Path $Root 'scripts\jarvis_desktop.pyw'
if (-not (Test-Path $PythonW)) { throw "Jarvis Python runtime is missing: $PythonW" }
if (-not (Test-Path $Entry)) { throw "Jarvis launcher is missing: $Entry" }
Start-Process -FilePath $PythonW -ArgumentList @($Entry) -WorkingDirectory $Root
```

- [ ] **Step 2: Document the supported launch command**

State that this launcher is the supported Windows entrypoint for the Jarvis profile and that `start.bat` remains upstream-only. Document `python readiness.py` as the pre-launch diagnostic.

- [ ] **Step 3: Run static validation**

Run: `python -m py_compile scripts/jarvis_desktop.pyw tests/test_jarvis_desktop.py`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/start-jarvis.ps1 JARVIS_SETUP.md JARVIS_DOWNLOAD.md README.md
git commit -m "docs: define supported Jarvis Windows launch path"
```

### Task 4: Run the full release gate and merge

**Files:**
- No new source files beyond the launcher changes.

- [ ] **Step 1: Run the complete regression suite locally where possible**

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s windows_maintenance/tests -p 'test_*.py' -v
```

Expected: all tests pass.

- [ ] **Step 2: Push the feature branch and let GitHub Actions run**

The required gate is the repository's `Jarvis full release gate`; do not merge while it is failing.

- [ ] **Step 3: Verify the feature branch workflows are green**

Check the Windows/source-bundle path plus integration, quality-of-life, and self-coding workflows.

- [ ] **Step 4: Merge to `main` only after the release gate is green**

Use a normal pull request merge; do not force-update `main`.

- [ ] **Step 5: Verify the merged `main` commit**

Confirm the merge commit's combined CI status is green and that the release gate includes the launcher tests.
