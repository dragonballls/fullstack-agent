# Jarvis Single-EXE Fullstack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship one Windows `Jarvis.exe` that opens the original Fullstack Agent-style living face and voice experience while retaining the existing guarded Jarvis cloud brain, computer control, self-coding, accounts, and maintenance systems.

**Architecture:** `Jarvis.exe -> desktop supervisor -> JarvisRuntime/AgentOrchestrator` plus embedded upstream `ai-visualizer`, `backtalk` ears/mouth, and optional `barehands` assets. The upstream face/voice contracts are preserved, but the upstream Claude brain is not used; spoken requests are routed through the existing Jarvis OmniRoute brain so there is still one authoritative planner/tool executor.

**Tech Stack:** Python 3.12, PyInstaller one-file/windowed, pywebview, existing Jarvis runtime, upstream backtalk STT/TTS modules, upstream ai-visualizer static server contract, existing hand-control runtime, GitHub Actions on Windows.

**Spec:** `docs/superpowers/specs/2026-09-16-jarvis-single-exe-fullstack-design.md`

## Global Constraints

- No `640x118` Tk fallback may remain on the packaged runtime path.
- `JarvisRuntime` and `AgentOrchestrator` remain the only Jarvis brain/tool execution path.
- Upstream Fullstack Agent components are pinned by commit in the build workflow.
- Normal distribution is one `Jarvis.exe`; a ZIP may exist only as an Actions transport artifact.
- Secrets never enter tracked files, bundle configuration, logs, or test output.
- Mutating Jarvis capabilities remain deny-by-default and confirmation-gated.
- Missing optional microphone/webcam/browser capabilities must degrade explicitly, never silently switch to the obsolete tiny UI.
- Hosted CI must verify source compilation, imports, packaging, process startup, embedded face serving, and the release asset contract.

---

### Task 1: Lock the regression tests around the wrong launcher and the required fullstack contract

**Files:**
- Create: `tests/test_single_exe_contract.py`
- Modify: `.github/workflows/jarvis-release-gate.yml`

**Interfaces:**
- Produces source-level assertions that `scripts/jarvis_desktop.py` no longer builds the obsolete Tk chat bar, that the launcher exposes a fullstack supervisor entry point, and that the Windows release workflow builds a direct `.exe` release asset.

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SingleExeContractTests(unittest.TestCase):
    def test_desktop_host_is_not_the_obsolete_tk_chat_bar(self):
        text = (ROOT / "scripts/jarvis_desktop.py").read_text(encoding="utf-8")
        self.assertNotIn('self.root.geometry("640x118")', text)
        self.assertNotIn('value="Jarvis is ready."', text)
        self.assertIn("Fullstack", text)

    def test_release_workflow_publishes_exe_directly(self):
        text = (ROOT / ".github/workflows/jarvis-release-gate.yml").read_text(encoding="utf-8")
        self.assertIn("Jarvis.exe", text)
        self.assertIn("jaredrhod/ai-visualizer", text)
        self.assertIn("jaredrhod/backtalk", text)
        self.assertIn("jaredrhod/barehands", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m unittest tests.test_single_exe_contract -v`

Expected: FAIL because the current host contains the 640x118 Tk bar and the release workflow does not embed upstream components.

- [ ] **Step 3: Commit the test-only regression gate**

```bash
git add tests/test_single_exe_contract.py
 git commit -m "test: lock single-exe fullstack contract"
```

### Task 2: Add reproducible pinned upstream-component acquisition to the Windows build

**Files:**
- Create: `scripts/fetch-fullstack-components.py`
- Modify: `.github/workflows/jarvis-release-gate.yml`
- Create: `tests/test_fullstack_components.py`

**Interfaces:**
- `fetch_components(destination: Path) -> dict[str, str]` downloads pinned source archives for `backtalk`, `ai-visualizer`, `barehands`, and `ai-memory-vault` and returns the resolved commit mapping.
- The workflow places the resulting sources under `build_vendor/` before PyInstaller runs.

- [ ] **Step 1: Write the failing acquisition test**

```python
from pathlib import Path
import unittest
from scripts.fetch_fullstack_components import COMPONENTS, validate_component_manifest


class FullstackComponentTests(unittest.TestCase):
    def test_all_required_components_have_pinned_revisions(self):
        self.assertEqual(set(COMPONENTS), {
            "backtalk", "ai-visualizer", "barehands", "ai-memory-vault"
        })
        for meta in COMPONENTS.values():
            self.assertRegex(meta["repo"], r"^jaredrhod/")
            self.assertRegex(meta["commit"], r"^[0-9a-f]{40}$")

    def test_manifest_has_windows_runtime_inputs(self):
        result = validate_component_manifest(COMPONENTS)
        self.assertEqual(result, [])
```

- [ ] **Step 2: Run and verify failure until implementation exists**

Run: `python -m unittest tests.test_fullstack_components -v`

Expected: FAIL with an import error.

- [ ] **Step 3: Implement pinned acquisition**

Use the currently verified upstream revisions:

```python
COMPONENTS = {
    "backtalk": {
        "repo": "jaredrhod/backtalk",
        "commit": "84b3a6cd321060cabb74aad6ebe794621cf99bd3",
    },
    "ai-visualizer": {
        "repo": "jaredrhod/ai-visualizer",
        "commit": "6921e1d4b06bdd4a34c5264882d5257c4d5f70fd",
    },
    "barehands": {
        "repo": "jaredrhod/barehands",
        "commit": "eb23bed2d772f9d5a24de26fb92f46c3c76d69cf",
    },
    "ai-memory-vault": {
        "repo": "jaredrhod/ai-memory-vault",
        "commit": "659bba9c8b351c937dd393b3042801d1ff1b502c",
    },
}
```

Download each `https://github.com/<repo>/archive/<commit>.zip`, verify the ZIP contains the requested top-level files, and extract into a stable directory such as `build_vendor/<name>`. Fail closed when the download or revision is wrong; do not float to an unpinned branch during a release.

- [ ] **Step 4: Add the workflow acquisition step before dependency installation/build**

The Windows job must run:

```text
python scripts/fetch-fullstack-components.py build_vendor
```

Then install the union of the existing Jarvis requirements and the Windows voice requirements declared by upstream `backtalk/pyproject.toml`.

- [ ] **Step 5: Run the acquisition tests**

Run: `python -m unittest tests.test_fullstack_components -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch-fullstack-components.py tests/test_fullstack_components.py .github/workflows/jarvis-release-gate.yml
 git commit -m "build: pin upstream fullstack components"
```

### Task 3: Replace the obsolete Tk host with the fullstack supervisor and native visualizer

**Files:**
- Modify: `scripts/jarvis_desktop.py`
- Modify: `scripts/jarvis_desktop.pyw`
- Create: `tests/test_jarvis_fullstack_host.py`

**Interfaces:**
- `FullstackJarvisHost` owns lifecycle for the visualizer, voice bridge, and optional hands while delegating all agent requests to `JarvisRuntime`.
- `FullstackJarvisHost.start() -> None` initializes services idempotently.
- `FullstackJarvisHost.stop() -> None` shuts services down without leaving worker threads/processes behind.
- `build_runtime() -> JarvisRuntime` remains the existing guarded runtime constructor.

- [ ] **Step 1: Add failing lifecycle tests with injected fakes**

```python
from unittest import TestCase
from unittest.mock import Mock
from scripts.jarvis_desktop import FullstackJarvisHost


class FullstackJarvisHostTests(TestCase):
    def test_start_initializes_visualizer_and_voice_once(self):
        visualizer = Mock()
        voice = Mock()
        hands = Mock()
        host = FullstackJarvisHost(Mock(), visualizer=visualizer, voice=voice, hands=hands)
        host.start()
        host.start()
        visualizer.start.assert_called_once()
        voice.start.assert_called_once()
        hands.start.assert_called_once()

    def test_stop_is_idempotent(self):
        host = FullstackJarvisHost(Mock(), visualizer=Mock(), voice=Mock(), hands=Mock())
        host.start()
        host.stop()
        host.stop()
        self.assertTrue(host.stopped)
```

- [ ] **Step 2: Run and confirm failure**

Run: `python -m unittest tests.test_jarvis_fullstack_host -v`

Expected: FAIL because the current module has no fullstack supervisor.

- [ ] **Step 3: Implement the supervisor without a second brain**

The host must keep `JarvisDesktopController.execute_request()` wired to the existing `AgentOrchestrator`. It may pass transcript text into that controller, but must not instantiate Claude Agent SDK or another planner.

Add a `NativeVisualizerAdapter` that imports the embedded upstream `ai-visualizer/server.py`, serves it on a loopback-only port, and exposes a `pywebview` native window pointed at the configured face path. Do not show the root HTML in a system browser for normal startup.

- [ ] **Step 4: Implement graceful startup/degraded behavior**

The visualizer must open even when microphone initialization is unavailable. The voice bridge must report a clear degraded state to the visualizer instead of replacing the native window with Tk.

- [ ] **Step 5: Run targeted host tests**

Run: `python -m unittest tests.test_jarvis_fullstack_host tests.test_single_exe_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/jarvis_desktop.py scripts/jarvis_desktop.pyw tests/test_jarvis_fullstack_host.py
 git commit -m "feat: restore fullstack native Jarvis host"
```

### Task 4: Connect upstream backtalk ears/mouth to Jarvis without reintroducing Claude as the brain

**Files:**
- Create: `scripts/jarvis_voice_bridge.py`
- Modify: `quality_of_life/jarvis_voice.py`
- Create: `tests/test_jarvis_voice_bridge.py`
- Modify: `quality_of_life/requirements.txt`

**Interfaces:**
- `JarvisVoiceBridge.start() -> None` warms STT/TTS and starts the configured listening mode.
- `JarvisVoiceBridge.stop() -> None` stops capture/playback cleanly.
- `JarvisVoiceBridge.handle_transcript(text: str) -> None` routes accepted speech into the existing `JarvisDesktopController`/`AgentOrchestrator`.
- Signal-bus writes use the same `.voice_state`, `.voice_waveform`, and `.voice_loading_pid` contract consumed by the upstream visualizer.

- [ ] **Step 1: Write failing tests around single brain routing and signal states**

```python
from unittest import TestCase
from unittest.mock import Mock
from scripts.jarvis_voice_bridge import JarvisVoiceBridge


class JarvisVoiceBridgeTests(TestCase):
    def test_transcript_uses_existing_jarvis_controller(self):
        controller = Mock()
        bridge = JarvisVoiceBridge(controller=controller, ears=Mock(), mouth=Mock())
        bridge.handle_transcript("open calculator")
        controller.execute_request.assert_called_once_with("open calculator", confirmed=False)

    def test_stop_is_idempotent(self):
        bridge = JarvisVoiceBridge(controller=Mock(), ears=Mock(), mouth=Mock())
        bridge.stop()
        bridge.stop()
        self.assertTrue(bridge.stopped)
```

- [ ] **Step 2: Run and verify the tests fail before implementation**

Run: `python -m unittest tests.test_jarvis_voice_bridge -v`

Expected: FAIL because the bridge does not exist.

- [ ] **Step 3: Implement the bridge using embedded upstream `backtalk.ears` and `backtalk.mouth`**

Use the upstream local STT/TTS implementation and its signal helpers, but never import `backtalk.brain` or `claude_agent_sdk`. The bridge's brain callback is the current Jarvis controller only.

Use the configured `JARVIS_VOICE_*` settings and preserve permission/confirmation behavior: when the orchestrator reports `needs_confirmation`, the bridge asks through the existing confirmation path instead of auto-approving.

For Windows packaging, include the upstream audio dependencies from `backtalk/pyproject.toml`: `faster-whisper`, `kokoro`, `numpy`, `pynput`, `sounddevice`, `soundfile`, and `webrtcvad-wheels`, plus their transitive requirements.

- [ ] **Step 4: Add PyInstaller collection rules for voice dependencies**

Collect the packages that otherwise commonly fail hidden-import discovery, including `faster_whisper`, `ctranslate2`, `kokoro`, `phonemizer`, and `webrtcvad`.

- [ ] **Step 5: Run voice-bridge and regression tests**

Run: `python -m unittest tests.test_jarvis_voice_bridge -v`

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/jarvis_voice_bridge.py quality_of_life/jarvis_voice.py quality_of_life/requirements.txt tests/test_jarvis_voice_bridge.py
 git commit -m "feat: connect fullstack voice to Jarvis brain"
```

### Task 5: Embed face assets and expose optional hands inside the same executable

**Files:**
- Create: `scripts/fullstack_assets.py`
- Modify: `scripts/jarvis_desktop.py`
- Create: `tests/test_fullstack_assets.py`

**Interfaces:**
- `embedded_path(relative: str) -> Path` resolves a bundled resource correctly in both source and PyInstaller one-file modes.
- `NativeHandsAdapter.start() -> None` uses the existing guarded hand-control runtime where available and never activates webcam input implicitly.
- `NativeHandsAdapter.stop() -> None` is idempotent.

- [ ] **Step 1: Add failing resource-resolution tests**

```python
from pathlib import Path
from unittest import TestCase
from scripts.fullstack_assets import embedded_path


class FullstackAssetTests(TestCase):
    def test_face_index_exists_in_vendor_layout(self):
        p = embedded_path("ai-visualizer/index.html")
        self.assertTrue(p.name == "index.html")
```

- [ ] **Step 2: Implement PyInstaller/source path resolution**

Use `sys._MEIPASS` when present and the source-tree vendor path otherwise. Do not write vendor files next to the user's executable.

- [ ] **Step 3: Integrate optional hands through the existing policy-controlled runtime**

Expose the hand-control start/stop/status operations already registered in `JarvisRuntime`. The original barehands visual assets may be used for presentation, but activation remains explicit; loss of camera tracking fails closed.

- [ ] **Step 4: Run targeted tests**

Run: `python -m unittest tests.test_fullstack_assets tests.test_jarvis_fullstack_host -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/fullstack_assets.py scripts/jarvis_desktop.py tests/test_fullstack_assets.py
 git commit -m "feat: embed fullstack face and hands assets"
```

### Task 6: Make the Windows release truly one-file and direct-download

**Files:**
- Modify: `.github/workflows/jarvis-release-gate.yml`
- Modify: `JARVIS_DOWNLOAD.md`
- Modify: `README.md`
- Create: `scripts/verify_jarvis_exe.py`
- Create: `tests/test_release_asset_contract.py`

**Interfaces:**
- `verify_exe(path: Path) -> None` fails when the executable is missing, trivially small, or unable to complete its noninteractive startup probe.

- [ ] **Step 1: Write failing release-asset tests**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseAssetContractTests(unittest.TestCase):
    def test_documentation_calls_jarvis_exe_the_primary_windows_download(self):
        text = (ROOT / "JARVIS_DOWNLOAD.md").read_text(encoding="utf-8")
        self.assertIn("Jarvis.exe", text)
        self.assertIn("single", text.lower())

    def test_workflow_runs_the_exe_after_build(self):
        text = (ROOT / ".github/workflows/jarvis-release-gate.yml").read_text(encoding="utf-8")
        self.assertIn("Jarvis.exe", text)
        self.assertIn("Smoke-test packaged executable startup", text)
```

- [ ] **Step 2: Implement the release workflow**

Build with `--onefile --windowed --name Jarvis` and vendor assets explicitly. Add a Windows smoke probe that starts the executable, waits for the native visualizer window/server readiness signal, checks the process has not exited, and then terminates it cleanly.

The workflow may upload a ZIP to Actions because GitHub artifact transport requires it, but the tagged release step must publish the raw `Jarvis.exe` file as the primary user-facing asset. Do not publish `Jarvis-Windows.zip` as the main download.

- [ ] **Step 3: Add executable verification output**

The verifier should check the file header/type and run the existing source-level startup probe; it must never execute arbitrary network code during static verification.

- [ ] **Step 4: Update documentation**

State plainly that normal Windows use is `Jarvis.exe`, that the executable contains the fullstack presentation/runtime code, and that account credentials and user hardware permissions remain machine-specific.

- [ ] **Step 5: Run the release-contract tests**

Run: `python -m unittest tests.test_release_asset_contract tests.test_single_exe_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/jarvis-release-gate.yml scripts/verify_jarvis_exe.py tests/test_release_asset_contract.py JARVIS_DOWNLOAD.md README.md
 git commit -m "release: publish verified single-file Jarvis executable"
```

### Task 7: Run the complete verification matrix before claiming completion

**Files:**
- No new files.

- [ ] **Step 1: Run all Python compilation checks**

```text
python -m compileall quality_of_life self_coding windows_maintenance scripts tests readiness.py
```

Expected: PASS with no syntax errors.

- [ ] **Step 2: Run the complete unittest suite**

```text
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s windows_maintenance/tests -p 'test_*.py' -v
```

Expected: every test PASS.

- [ ] **Step 3: Run the exact Windows packaging commands in CI**

Build the one-file executable from a clean checkout with the pinned upstream sources. Do not accept a source-only success as a release success.

- [ ] **Step 4: Smoke-test the produced executable on `windows-latest`**

Verify process startup, embedded visualizer readiness, nonzero lifetime after initialization, and clean shutdown.

- [ ] **Step 5: Re-run the released artifact contract after packaging**

Confirm the tagged release contains `Jarvis.exe` directly and that no user-facing Windows download points back to the old source ZIP or minimal launcher.

- [ ] **Step 6: Only then mark the release gate complete**

The completion statement must distinguish repository/release verification from machine-specific features that hosted CI cannot prove, such as the user's microphone, speakers, camera, cloud credentials, or account permissions.
