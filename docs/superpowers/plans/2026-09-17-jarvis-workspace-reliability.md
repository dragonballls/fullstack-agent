# Jarvis Workspace and Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the approved Jarvis workspace/reliability scope on `feat/jarvis-advanced-workspace`, preserve the existing Fullstack agent architecture, expose all supported features through persistent workspace surfaces and command access, and verify the packaged Windows release on the exact final commit.

**Architecture:** Extend the existing desktop API and guarded runtime instead of replacing them. Add a small process-local activity contract and provider-neutral location status surface; workspace views consume these adapters while existing visualizer, voice, hands, self-coding, permissions, workflows, browser, system, and updater remain authoritative.

**Tech Stack:** Python 3.x, unittest, pywebview, existing `quality_of_life` runtime/orchestrator, existing Windows PyInstaller release workflow, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-jarvis-workspace-reliability-design.md`

## Global Constraints

- The existing `JarvisWebApi` contract remains intact.
- The persistent command input remains available in every workspace.
- The existing visualizer remains the underlying visual/voice interaction surface.
- Existing capability policy and confirmation gates remain authoritative.
- Location is shown only from authorized provider results; no location is fabricated.
- Optional integrations fail independently and leave the command surface usable.
- Windows remains the primary packaged target and the no-console desktop entrypoint remains usable.
- No direct Life360 fake implementation or authorization bypass is added.
- No destructive system automation is made autonomous.

---

### Task 1: Activity model and bounded store

**Files:**
- Create: `quality_of_life/activity.py`
- Modify: `tests/test_activity.py`

**Interfaces:**
- Produces `ActivityStatus`, `ActivityRecord`, and `ActivityStore`.
- `ActivityStore.create(title: str) -> ActivityRecord`
- `ActivityStore.update(activity_id: str, *, status: ActivityStatus, progress: int | None = None, step: str = "", error: str | None = None) -> ActivityRecord`
- `ActivityStore.get(activity_id: str) -> ActivityRecord | None`
- `ActivityStore.list(limit: int = 50) -> tuple[ActivityRecord, ...]`
- `ActivityStore.request_cancel(activity_id: str) -> ActivityRecord`
- `ActivityStore.acknowledge_cancel(activity_id: str) -> ActivityRecord`

- [ ] **Step 1: Write failing activity lifecycle tests.**
Include tests asserting: created records start `queued`; running/succeeded/failed/cancelled transitions retain one stable ID; progress is clamped to 0..100; failure stores only the supplied sanitized summary; cancellation request alone does not change execution status; acknowledgement changes it to `cancelled`.

- [ ] **Step 2: Run the activity tests and confirm they fail because the module/contracts are absent.**
Run: `python -m unittest tests.test_activity -v`
Expected: import failure for `quality_of_life.activity`.

- [ ] **Step 3: Implement the minimal dataclasses/store.**
Use a thread-safe bounded `OrderedDict`/dict+deque store with a configurable default maximum of 100 records; reject unknown IDs with `KeyError`; reject invalid status transitions with `ValueError`; use UTC timestamps.

- [ ] **Step 4: Run the activity tests and confirm green.**
Run: `python -m unittest tests.test_activity -v`
Expected: all activity tests pass.

- [ ] **Step 5: Commit the self-contained activity unit.**
Commit message: `feat: add guarded activity contract`.

### Task 2: Activity integration into the runtime

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `tests/test_runtime_activity.py`

**Interfaces:**
- `JarvisRuntime.activity_store() -> ActivityStore`
- `JarvisRuntime.activity_snapshot(limit: int = 20) -> list[dict[str, object]]`
- `JarvisRuntime.activity_cancel(activity_id: str) -> dict[str, object]`

- [ ] **Step 1: Write failing runtime integration tests.**
Assert the runtime owns one activity store for its lifetime, exposes JSON-safe snapshots, and cancellation requests do not claim cancellation acknowledgement until an activity executor acknowledges it.

- [ ] **Step 2: Run the focused tests and verify failure.**
Run: `python -m unittest tests.test_runtime_activity -v`
Expected: missing runtime activity methods.

- [ ] **Step 3: Add the smallest runtime integration.**
Instantiate `ActivityStore` in `JarvisRuntime`; return serialized records with stable IDs/status/progress/step/timestamps/error; delegate cancel to the store.

- [ ] **Step 4: Re-run focused runtime tests.**
Run: `python -m unittest tests.test_runtime_activity -v`
Expected: PASS.

- [ ] **Step 5: Run the existing runtime tests.**
Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: existing suite remains green.

- [ ] **Step 6: Commit.**
Commit message: `feat: expose runtime activity state`.

### Task 3: Guarded provider-neutral God’s Eye status

**Files:**
- Create: `quality_of_life/location_providers.py`
- Modify: `quality_of_life/workspace_ui.py`
- Modify: `tests/test_location_providers.py`
- Modify: `tests/test_workspace_ui.py`

**Interfaces:**
- `ProviderKind = Literal["device", "phone", "family"]`
- `ProviderState` with provider kind, availability, authorized, live, source, and sanitized detail.
- `LocationProviderRegistry.register(kind: ProviderKind, provider: object) -> None`
- `LocationProviderRegistry.status(kind: ProviderKind) -> ProviderState`
- `LocationProviderRegistry.snapshot() -> tuple[ProviderState, ...]`

The existing guarded `locations.current` runtime action remains the first device provider. Phone/family are optional slots; no fake coordinates are created.

- [ ] **Step 1: Write failing provider contract tests.**
Assert unavailable slots remain unavailable; provider exceptions are sanitized; live is false unless the provider explicitly reports it; no coordinates are invented; registry snapshots contain device/phone/family independently.

- [ ] **Step 2: Run focused tests and confirm failure.**
Run: `python -m unittest tests.test_location_providers -v`
Expected: missing provider module/contracts.

- [ ] **Step 3: Implement provider-neutral state/registry.**
Support callable/provider objects returning mappings; normalize only documented fields; sanitize exception details to exception type and fixed safe status text; never synthesize location values.

- [ ] **Step 4: Wire God’s Eye workspace status to the registry while preserving the existing `Capability.LOCATION_READ` dispatch.**
Keep the existing `gods_eye_status()` method as the compatibility path and add a provider snapshot method rather than changing `submit_text` or the command API.

- [ ] **Step 5: Add failing/green workspace tests for provider state and privacy-safe errors.**
Run: `python -m unittest tests.test_location_providers tests.test_workspace_ui -v`
Expected: PASS after implementation.

- [ ] **Step 6: Commit.**
Commit message: `feat: add guarded gods-eye provider surface`.

### Task 4: Workspace activity rendering and feature access

**Files:**
- Modify: `quality_of_life/workspace_ui.py`
- Modify: `tests/test_workspace_ui.py`

**Interfaces:**
- Extend `WorkspaceWebApi` with `activity_snapshot()`, `activity_cancel()`, and `gods_eye_providers()`.
- Browser/Coding/System/Workflows views must display backing availability/activity rather than claiming execution they do not own.

- [ ] **Step 1: Write failing UI contract tests.**
Assert all six workspaces expose the shared command link, workspace state includes activity/command panels, activity/status endpoints exist, and workspace provider failures render an unavailable state without removing the command surface.

- [ ] **Step 2: Run tests to verify red.**
Run: `python -m unittest tests.test_workspace_ui -v`
Expected: missing bridge methods/markup.

- [ ] **Step 3: Implement minimal activity/provider bindings.**
Add small bridge methods that read runtime activity snapshots and provider snapshots. Add an activity card/list and status badges in the existing shell. Preserve `pointer-events:none` on passive overlay surfaces so the visualizer remains interactive.

- [ ] **Step 4: Add command chips for existing capabilities without adding new privileged execution paths.**
Use the existing `submit_text` path for commands such as opening God’s Eye, checking system status, showing workflows, and starting coding/browser requests. Do not directly execute protected runtime actions from JavaScript.

- [ ] **Step 5: Run focused UI tests and the complete suite.**
Run:
```
python -m unittest tests.test_workspace_ui -v
python -m unittest discover -s tests -p 'test_*.py' -v
```
Expected: all pass.

- [ ] **Step 6: Commit.**
Commit message: `feat: surface activities across jarvis workspaces`.

### Task 5: Optional-component startup isolation

**Files:**
- Modify: `scripts/jarvis_desktop.py`
- Modify: `scripts/jarvis_runtime_resilience.py`
- Modify: `tests/test_jarvis_desktop.py`
- Modify: `tests/test_jarvis_runtime_resilience.py`

**Interfaces:**
- Preserve existing component adapter APIs.
- Add one narrow startup helper if needed to initialize an optional component independently and log a sanitized failure.

- [ ] **Step 1: Write failing regression tests.**
Cover voice start failure, hands start failure, updater start failure, visualizer start success, and command API construction. Assert optional failures do not prevent `FullstackJarvisHost.started` from becoming true and do not remove `JarvisWebApi.submit_text`.

- [ ] **Step 2: Run focused tests and verify the new failure behavior is not yet represented.**
Run: `python -m unittest tests.test_jarvis_desktop tests.test_jarvis_runtime_resilience -v`
Expected: the new assertions fail only where the requested isolation/helper behavior is absent.

- [ ] **Step 3: Implement minimal boundary isolation.**
Do not change capability permissions, updater verification, visualizer startup ordering, or the no-console entrypoint. Contain optional initialization exceptions at the boundary and retain the existing logger.

- [ ] **Step 4: Run focused tests plus the full suite.**
Run:
```
python -m unittest tests.test_jarvis_desktop tests.test_jarvis_runtime_resilience -v
python -m unittest discover -s tests -p 'test_*.py' -v
```
Expected: PASS.

- [ ] **Step 5: Commit.**
Commit message: `fix: isolate optional jarvis desktop components`.

### Task 6: Release and packaged Windows verification contract

**Files:**
- Modify: `.github/workflows/jarvis-release-gate.yml`
- Create: `tests/test_release_contract.py`

- [ ] **Step 1: Write failing release-contract tests.**
Assert the workflow contains: full regression matrix, Python compile step, complete unittest step, Windows native build, embedded visualizer smoke, packaged host smoke, attestation generation, and attestation verification before publish.

- [ ] **Step 2: Run the release contract tests and confirm any missing contract is reported.**
Run: `python -m unittest tests.test_release_contract -v`

- [ ] **Step 3: Implement only missing release assertions/configuration.**
Do not duplicate existing attestation steps. Keep publication skipped for PRs as currently designed.

- [ ] **Step 4: Run focused release tests and complete local suite.**
Run:
```
python -m unittest tests.test_release_contract -v
python -m unittest discover -s tests -p 'test_*.py' -v
```
Expected: PASS.

- [ ] **Step 5: Commit.**
Commit message: `test: lock jarvis release acceptance contract`.

### Task 7: Final exact-head verification

**Files:**
- No production changes unless a verification failure identifies a root cause.

**Interfaces:**
- Verify the exact Git commit, all tests, workflow jobs, packaged executable artifact, and release attestation.

- [ ] **Step 1: Run local complete test suite.**
Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: zero failures/errors.

- [ ] **Step 2: Push/verify the branch head and inspect all GitHub Actions runs for that exact SHA.**
Require Quality-of-life, Integration, Self-coding safety, and Jarvis full release gate conclusions of `success`.

- [ ] **Step 3: Inspect native Windows job steps.**
Require successful dependency verification, build identity, embedded imports, single-file build, visualizer smoke, packaged host smoke, and attestation generation.

- [ ] **Step 4: Verify the final PR state.**
Confirm PR #37 is mergeable and the final head SHA is the SHA whose checks were verified.

- [ ] **Step 5: If any verification fails, return to root-cause investigation and TDD before changing code.**
Do not declare completion from a previous SHA or partial results.

- [ ] **Step 6: Only after every acceptance criterion is evidenced, report the exact verified state.**
