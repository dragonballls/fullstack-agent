# Full Jarvis Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the existing guarded self-coding, quality-of-life capability layer, and Jarvis voice setup into the installer/agent control plane while preserving optionality and preventing regressions.

**Architecture:** Keep `self_coding/` and `quality_of_life/` as independent subsystems with explicit interfaces. Add only thin integration in `CLAUDE.md`, `fullstack-agent.md`, tests, and CI; do not replace the underlying stack or copy the old Mark-LIII architecture.

**Tech Stack:** Python 3.11–3.13, unittest, GitHub Actions, existing `quality_of_life` adapters, existing `self_coding` runner, existing backtalk/ai-visualizer/barehands installer flow.

**Spec:** `docs/superpowers/specs/2026-09-15-full-jarvis-integration-design.md`

## Global Constraints

- `quality_of_life/` remains optional and isolated from the base stack.
- Mutating QOL capabilities remain deny-by-default and must pass a capability check.
- Cloud routing must not introduce or require a local LLM.
- ElevenLabs secrets must never be committed, logged, or written into tracked files.
- Self-coding keeps clean-tree, isolated-branch, verify-before-commit, and rollback guarantees.
- Existing user-built files remain protected by the installer's adoption rules.
- Hosted CI cannot certify physical microphone, speaker, camera, mouse, browser, or desktop behavior on the user's machine.

---

### Task 1: Wire the installer/agent control plane to Quality of Life

**Files:**
- Modify: `CLAUDE.md`
- Modify: `fullstack-agent.md`
- Test: `tests/test_integration_contract.py`

**Interfaces:**
- Consumes: `quality_of_life/README.md`, `quality_of_life/manifest.py`, `quality_of_life/orchestrator.py`.
- Produces: documented and test-enforced discovery rules for the QOL subsystem and its deny-by-default operation model.

- [ ] **Step 1: Write failing integration-contract tests**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IntegrationContractTests(unittest.TestCase):
    def test_installer_mentions_quality_of_life(self):
        text = (ROOT / "fullstack-agent.md").read_text(encoding="utf-8")
        self.assertIn("quality_of_life/README.md", text)
        self.assertIn("quality_of_life/manifest.py", text)
        self.assertIn("deny-by-default", text)

    def test_agent_rules_mention_quality_of_life(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("quality_of_life/", text)
        self.assertIn("permission", text.lower())
        self.assertIn("self_coding", text)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m unittest tests.test_integration_contract -v`

Expected: FAIL because the current installer rules do not yet name the QOL subsystem or its registry.

- [ ] **Step 3: Add minimal control-plane instructions**

Add to `CLAUDE.md` a concise rule that the toolbox contains an optional `quality_of_life/` capability layer; the agent must read `quality_of_life/README.md` and `manifest.py` before using it; capabilities are deny-by-default; mutating actions require the policy/confirmation path; missing optional dependencies must not block the base stack.

Add to `fullstack-agent.md` a setup phase that, after the existing stack components are wired, checks for `quality_of_life/`, validates that its Python modules compile, records that it is optional, and makes the available capabilities discoverable to the resulting HOME `CLAUDE.md` without overwriting existing user rules.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `python -m unittest tests.test_integration_contract -v`

Expected: PASS.

- [ ] **Step 5: Commit the control-plane integration**

```bash
git add CLAUDE.md fullstack-agent.md tests/test_integration_contract.py
git commit -m "feat: wire quality-of-life capabilities into agent rules"
```

---

### Task 2: Make QOL registration and orchestration integration explicit

**Files:**
- Modify: `quality_of_life/__init__.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/orchestrator.py`
- Test: `tests/test_quality_of_life.py`

**Interfaces:**
- Consumes: `Capability`, `CapabilityPolicy`, `Action`, and existing tool registry entries.
- Produces: a single import-safe QOL entry point that exposes the registry/orchestrator types without importing optional hardware libraries during package import.

- [ ] **Step 1: Write failing registration tests**

```python
from quality_of_life.manifest import default_registry
from quality_of_life.orchestrator import Action, QoLOrchestrator
from quality_of_life.permissions import Capability, CapabilityDenied, CapabilityPolicy


def test_default_registry_names_are_stable():
    names = default_registry().names()
    assert names == ("background", "browser", "cloud_router", "computer", "screen")


def test_orchestrator_rejects_disabled_mutation_before_execution():
    called = False

    def action():
        nonlocal called
        called = True

    orchestrator = QoLOrchestrator(CapabilityPolicy())
    orchestrator.register(Action(Capability.MOUSE_CONTROL, "click", action))
    try:
        orchestrator.run(Capability.MOUSE_CONTROL, "click")
    except CapabilityDenied:
        pass
    else:
        raise AssertionError("disabled capability was executed")
    assert not called
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_quality_of_life.py -q`

Expected: FAIL until registry/orchestrator exports and behavior are covered by the integration contract.

- [ ] **Step 3: Implement the minimal interface**

Export `Capability`, `Action`, `QoLOrchestrator`, `ToolRegistry`, and `default_registry` from `quality_of_life/__init__.py` without importing `computer.py`, `screen.py`, or `browser.py` at module import time.

Keep `default_registry()` as metadata-only registration. The registry entries remain strings or factories that are resolved only when the capability is actually requested, so missing PyAutoGUI, MSS/Pillow, or Playwright cannot crash a normal `import quality_of_life`.

Keep `QoLOrchestrator.run()` policy-first: call `policy.check()` before resolving or invoking the registered operation.

- [ ] **Step 4: Run the focused tests and the compile check**

Run: `python -m pytest tests/test_quality_of_life.py -q`

Run: `python -m compileall quality_of_life tests`

Expected: all tests PASS and compile completes without errors.

- [ ] **Step 5: Commit**

```bash
git add quality_of_life/__init__.py quality_of_life/manifest.py quality_of_life/orchestrator.py tests/test_quality_of_life.py
git commit -m "feat: formalize quality-of-life capability registry"
```

---

### Task 3: Harden optional desktop, screen, and browser adapters

**Files:**
- Modify: `quality_of_life/computer.py`
- Modify: `quality_of_life/screen.py`
- Modify: `quality_of_life/browser.py`
- Test: `tests/test_quality_of_life_optional.py`

**Interfaces:**
- Consumes: existing `CapabilityPolicy` and adapter classes.
- Produces: deterministic unavailable states, input validation, and clean shutdown behavior for optional dependencies.

- [ ] **Step 1: Write failing adapter tests**

```python
import unittest
from unittest.mock import Mock

from quality_of_life.browser import BrowserController, BrowserControlUnavailable
from quality_of_life.computer import ComputerController
from quality_of_life.permissions import Capability, CapabilityPolicy
from quality_of_life.screen import ScreenCapture


class OptionalAdapterTests(unittest.TestCase):
    def test_computer_rejects_invalid_click_count(self):
        fake = Mock()
        controller = ComputerController.__new__(ComputerController)
        controller.policy = CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL}))
        controller.pyautogui = fake
        with self.assertRaises(ValueError):
            controller.click(clicks=4)
        fake.click.assert_not_called()

    def test_screen_save_uses_requested_path(self):
        # Adapter behavior is exercised with an injected fake mss module.
        shot = Mock()
        shot.rgb = b"rgb"
        shot.size = (1, 1)
        session = Mock()
        session.__enter__.return_value = session
        session.__exit__.return_value = False
        session.monitors = [None, {"left": 0, "top": 0, "width": 1, "height": 1}]
        session.grab.return_value = shot
        fake_mss = Mock()
        fake_mss.mss.return_value = session
        capture = ScreenCapture(
            CapabilityPolicy(allowed=frozenset({Capability.SCREEN_READ})),
            mss_module=fake_mss,
        )
        self.assertEqual(capture.capture(), b"rgb")
        session.grab.assert_called_once()
```

- [ ] **Step 2: Run the focused test and verify it fails where behavior is missing**

Run: `python -m unittest tests.test_quality_of_life_optional -v`

Expected: any newly specified edge case fails before implementation.

- [ ] **Step 3: Implement narrow fixes only**

Ensure `ComputerController` never invokes PyAutoGUI before capability validation or argument validation. Keep `shell=False` for app launches.

Ensure `ScreenCapture` checks the capability before invoking MSS and keeps saving optional; do not make Pillow an import-time dependency.

Ensure `BrowserController` accepts only HTTP(S) URLs, never silently falls back to an existing unrelated browser profile, and closes both browser and Playwright handles idempotently.

- [ ] **Step 4: Run optional-adapter tests and the full QOL suite**

Run: `python -m unittest tests.test_quality_of_life_optional -v`

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quality_of_life/computer.py quality_of_life/screen.py quality_of_life/browser.py tests/test_quality_of_life_optional.py
git commit -m "fix: harden optional quality-of-life adapters"
```

---

### Task 4: Integrate cloud routing without introducing local-model fallback

**Files:**
- Modify: `quality_of_life/router.py`
- Test: `tests/test_quality_of_life_router.py`

**Interfaces:**
- Consumes: `ProviderTarget` and `CloudModelRouter`.
- Produces: deterministic cloud-only provider failover with secret-safe diagnostics.

- [ ] **Step 1: Write failing router tests**

```python
import os
import unittest
from unittest.mock import patch

from quality_of_life.router import CloudModelRouter, ProviderTarget


class RouterTests(unittest.TestCase):
    def test_missing_keys_report_names_not_secret_values(self):
        router = CloudModelRouter((ProviderTarget("one", "https://one.invalid", "ONE_KEY", "m1"),))
        with self.assertRaisesRegex(RuntimeError, "one: missing ONE_KEY"):
            router.complete([{"role": "user", "content": "hi"}])

    def test_router_never_mentions_local_backend_as_implicit_fallback(self):
        source = open("quality_of_life/router.py", encoding="utf-8").read()
        self.assertNotIn("ollama", source.lower())
```

- [ ] **Step 2: Run the focused router tests**

Run: `python -m unittest tests.test_quality_of_life_router -v`

Expected: FAIL only where the new assertions require changes.

- [ ] **Step 3: Implement deterministic diagnostics**

Keep provider order exactly as configured. Catch transport, timeout, malformed response, and HTTP failures while preserving the provider name in the aggregated error. Never include the actual API-key value. Do not add local backends or silent environment guessing.

- [ ] **Step 4: Run router and full regression tests**

Run: `python -m unittest tests.test_quality_of_life_router -v`

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quality_of_life/router.py tests/test_quality_of_life_router.py
git commit -m "fix: keep cloud routing deterministic and secret-safe"
```

---

### Task 5: Finish Jarvis voice discoverability and installer wiring

**Files:**
- Modify: `fullstack-agent.md`
- Modify: `README.md`
- Test: `tests/test_voice_contract.py`

**Interfaces:**
- Consumes: `JARVIS_VOICE.md` and the existing backtalk installer flow.
- Produces: installer instructions that always consult the voice contract before declaring voice setup complete.

- [ ] **Step 1: Write failing voice-contract tests**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VoiceContractTests(unittest.TestCase):
    def test_voice_contract_exists_and_is_secret_safe(self):
        contract = (ROOT / "JARVIS_VOICE.md").read_text(encoding="utf-8")
        self.assertIn("ElevenLabs", contract)
        self.assertIn("ELEVENLABS_API_KEY", contract)
        self.assertIn("Never print the API key", contract)
        self.assertIn("real speech test", contract)

    def test_installer_requires_voice_contract(self):
        installer = (ROOT / "fullstack-agent.md").read_text(encoding="utf-8")
        self.assertIn("JARVIS_VOICE.md", installer)
        self.assertIn("real speech test", installer)
```

- [ ] **Step 2: Run the focused test**

Run: `python -m unittest tests.test_voice_contract -v`

Expected: FAIL until the installer explicitly references the voice contract.

- [ ] **Step 3: Wire the contract**

Before the existing backtalk setup step, instruct the installer to read `JARVIS_VOICE.md`. Preserve the existing user choice between built-in and ElevenLabs rather than silently forcing a paid service. When ElevenLabs is selected, require credential verification, voice-library lookup, an actual speech test, and secure key handling. Keep the fallback behavior documented by the contract.

Update README text so the integrated Jarvis voice path is discoverable without claiming free/unlimited ElevenLabs service.

- [ ] **Step 4: Run voice and full tests**

Run: `python -m unittest tests.test_voice_contract -v`

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fullstack-agent.md README.md tests/test_voice_contract.py
 git commit -m "feat: wire Jarvis voice contract into setup"
```

---

### Task 6: Add end-to-end integration CI gate

**Files:**
- Create: `.github/workflows/integration-tests.yml`
- Test: `tests/test_integration_contract.py`, `tests/test_quality_of_life.py`, `tests/test_self_coding.py`

**Interfaces:**
- Consumes: all integrated subsystems.
- Produces: a GitHub gate that blocks changes when package compilation, integration contracts, QOL regressions, or self-coding safety tests fail.

- [ ] **Step 1: Add the workflow**

```yaml
name: Integration tests

on:
  push:
  pull_request:

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - name: Install QOL dependencies
        run: python -m pip install -r quality_of_life/requirements.txt
      - name: Compile all Python modules
        run: python -m compileall quality_of_life self_coding tests
      - name: Run complete regression suite
        run: python -m unittest discover -s tests -p 'test_*.py' -v
```

- [ ] **Step 2: Run the workflow locally through the same commands**

Run: `python -m pip install -r quality_of_life/requirements.txt`

Run: `python -m compileall quality_of_life self_coding tests`

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: PASS.

- [ ] **Step 3: Commit the CI gate**

```bash
git add .github/workflows/integration-tests.yml
git commit -m "ci: add full integration regression gate"
```

- [ ] **Step 4: Verify the GitHub workflow**

Inspect the new workflow run for the exact commit. Expected: success with no failed or skipped test steps.

---

### Task 7: Final repository verification and merge protection

**Files:**
- Modify: `README.md` only if the final integrated capability list is stale.

**Interfaces:**
- Consumes: all previous task outputs and GitHub CI statuses.
- Produces: a verified `main` branch with no known failing automated checks and a clearly documented boundary for local-machine validation.

- [ ] **Step 1: Compare the final tree and previous baseline**

Use GitHub compare to verify all intended integration files are present and no unrelated deletions occurred.

- [ ] **Step 2: Run the existing QOL matrix**

Confirm the workflow covering Windows/Linux with Python 3.11, 3.12, and 3.13 remains green.

- [ ] **Step 3: Run the self-coding safety workflow**

Confirm the self-coding workflow remains green after integration changes.

- [ ] **Step 4: Check the final commit status**

Require a green combined status for the final integration commit before calling the repository integration complete.

- [ ] **Step 5: Record the remaining local-only validation boundary**

Document that actual screen capture, mouse/keyboard input, browser GUI launch, microphone/speaker output, and camera permission behavior need one validation run on the user's Windows machine. Do not claim those physical behaviors passed based only on hosted CI.
