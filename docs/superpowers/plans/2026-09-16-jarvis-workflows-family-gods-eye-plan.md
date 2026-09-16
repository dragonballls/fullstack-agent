# Jarvis Workflows and Family God’s Eye Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task when subagents are unavailable.

**Goal:** Add persistent named workflows and an optional authorized family-location overlay for God’s Eye, while fixing the existing native Windows visualizer smoke failure and preserving the existing guarded Jarvis runtime.

**Architecture:** Add two lazy, isolated services under `quality_of_life`: `WorkflowService` for local JSON-backed named routines and `FamilyLocationService` plus a provider-neutral adapter contract for authorized family locations. Both services use existing capability/catalog boundaries; workflows execute only cataloged operations through `JarvisRuntime.dispatch`, while family locations are read-only and provider data is normalized before reaching God’s Eye. The Windows packaging change is isolated to the embedded visualizer startup path and its smoke test.

**Tech Stack:** Python 3.11–3.13, standard-library JSON/dataclasses/threading/http handling, existing `unittest`, existing `JarvisRuntime`, `CapabilityPolicy`, operation catalog, God’s Eye map contract, PyInstaller/Windows GitHub Actions.

**Spec:**
- `docs/superpowers/specs/2026-09-16-persistent-workflows-design.md`
- `docs/superpowers/specs/2026-09-16-gods-eye-family-location-design.md`
- Existing approved packaging design `docs/superpowers/specs/2026-09-16-jarvis-single-exe-fullstack-design.md`

## Global Constraints

- Capabilities remain deny-by-default and existing confirmation requirements remain authoritative.
- Stored workflows may reference cataloged operation names only; no raw shell/PowerShell/executable text is accepted.
- Workflow persistence stores no credentials, browser profiles, access tokens, or sensitive tool-return data.
- Family location data is accepted only from an authorized/permitted source; no Life360 scraping, private-endpoint reverse engineering, authentication bypass, or impersonation.
- Missing/paused/stale family location data is represented explicitly and is never fabricated as live.
- No third-party dependency is required for baseline import or unit tests.
- Existing ordinary chat, voice, hands, self-coding, browser controls, God’s Eye current-location behavior, and packaging contracts remain unchanged unless a test proves the targeted fix is required.
- TDD is mandatory: each production behavior gets a failing test first and is re-run through the existing CI matrix.

---

### Task 1: Create failing workflow model/store tests

**Files:**
- Create: `tests/test_workflows.py`

**Interfaces:**
- Consumes: future `quality_of_life.workflows.Workflow`, `WorkflowStep`, `WorkflowRunSummary`, `WorkflowStore`.
- Produces: executable specifications for model round-trip, normalization, atomic persistence, malformed-store rejection, validation, unknown-operation rejection, deterministic resolution, and safe run-result persistence.

- [ ] **Step 1: Write failing tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from quality_of_life.workflows import Workflow, WorkflowRunSummary, WorkflowStep, WorkflowStore


class WorkflowStoreTests(unittest.TestCase):
    def test_round_trip_survives_a_new_store_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflows.json"
            first = WorkflowStore(path)
            workflow = Workflow.new(
                "Morning Setup",
                aliases=("morning", "start my day"),
                steps=(WorkflowStep("applications.list", {}),),
            )
            first.create(workflow)
            second = WorkflowStore(path)
            loaded = second.get(workflow.id)
            self.assertEqual(loaded.name, "Morning Setup")
            self.assertEqual(loaded.aliases, ("morning", "start my day"))
            self.assertEqual(loaded.steps[0].operation, "applications.list")

    def test_name_and_alias_resolution_is_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(Path(tmp) / "workflows.json")
            workflow = Workflow.new("  Morning   Setup  ", aliases=("  Start Day ",), steps=(WorkflowStep("applications.list", {}),))
            store.create(workflow)
            self.assertEqual(store.resolve("RUN MY   MORNING SETUP").id, workflow.id)
            self.assertEqual(store.resolve("do start day").id, workflow.id)

    def test_malformed_store_is_rejected_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflows.json"
            path.write_text("[]", encoding="utf-8")
            store = WorkflowStore(path)
            with self.assertRaises(ValueError):
                store.list()
            self.assertEqual(path.read_text(encoding="utf-8"), "[]")

    def test_unknown_operation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(Path(tmp) / "workflows.json")
            workflow = Workflow.new("Bad", steps=(WorkflowStep("not.a.real.operation", {}),))
            with self.assertRaises(ValueError):
                store.create(workflow)

    def test_ambiguous_resolution_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(Path(tmp) / "workflows.json")
            store.create(Workflow.new("Work", aliases=("daily",), steps=(WorkflowStep("applications.list", {}),)))
            store.create(Workflow.new("Study", aliases=("daily",), steps=(WorkflowStep("applications.list", {}),)))
            self.assertIsNone(store.resolve("daily"))

    def test_run_summary_does_not_persist_arguments_or_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowStore(Path(tmp) / "workflows.json")
            workflow = Workflow.new("Safe", steps=(WorkflowStep("applications.list", {}),))
            store.create(workflow)
            store.record_run(workflow.id, WorkflowRunSummary.completed(run_id="r1", completed_steps=1))
            raw = Path(tmp, "workflows.json").read_text(encoding="utf-8")
            self.assertNotIn("OPENAI_API_KEY", raw)
            self.assertNotIn("arguments", raw)
            self.assertIn('"completed_steps": 1', raw)
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_workflows -v`
Expected: FAIL because `quality_of_life.workflows` does not exist.

- [ ] **Step 3: Commit the failing tests**

```text
test: define persistent workflow storage contract
```

---

### Task 2: Implement workflow model/store and turn tests green

**Files:**
- Create: `quality_of_life/workflows.py`

**Interfaces:**
- Produces: `WorkflowStep`, `WorkflowRunSummary`, `Workflow`, and `WorkflowStore`.
- `WorkflowStore.create(workflow)`, `.replace(workflow)`, `.delete(workflow_id)`, `.get(workflow_id)`, `.list()`, `.resolve(text)`, `.record_run(workflow_id, summary)`.
- Workflow IDs are UUID strings; name/alias matching uses case-folded whitespace normalization.
- Persistence writes a complete temporary JSON document beside the store and atomically replaces the target.
- Validation calls `quality_of_life.capabilities.operation()` for every step and rejects malformed arguments and non-JSON values before writing.

- [ ] **Step 1: Implement the minimal model/store required by the failing tests**

- [ ] **Step 2: Run GREEN**

Run: `python -m unittest tests.test_workflows -v`
Expected: PASS.

- [ ] **Step 3: Run existing regression suite**

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: all prior tests remain green.

- [ ] **Step 4: Commit**

```text
feat: add persistent named workflow store
```

---

### Task 3: Add workflow runtime/orchestrator integration with failing tests first

**Files:**
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/agent_orchestrator.py`
- Create/Modify: `tests/test_workflow_orchestration.py`

**Interfaces:**
- `JarvisRuntime._tool("workflows")` lazily returns `WorkflowStore` using `JARVIS_WORKFLOW_STORE` when configured.
- Agent orchestration detects only the approved invocation prefixes (`run my`, `do my`, `run`, `do`, `start`) and only resolves a stored workflow when the remaining phrase exactly matches one name/alias.
- A resolved workflow executes sequentially via `runtime.dispatch(capability, operation, ..., confirmation=...)`, never by invoking a tool directly.
- Confirmation denial produces `needs_confirmation=True`; required-step failure stops execution; `continue_on_error=True` continues and remains unverified if any required action fails.

- [ ] **Step 1: Write failing tests for recognized/unknown workflow requests, execution order, fail-fast, continuation, capability denial, and confirmation behavior.**

```python

def test_run_named_workflow_executes_steps_in_order():
    calls = []
    runtime = FakeRuntime(calls, allowed={Capability.APP_READ, Capability.SYSTEM_DIAGNOSTICS})
    workflow = Workflow.new("Morning", steps=(WorkflowStep("applications.list", {}), WorkflowStep("system.inspect", {})))
    store = InMemoryWorkflowStore(workflow)
    result = execute_workflow_request(runtime, store, "run my morning", confirmed=False)
    assert result.verified
    assert calls == ["applications.list", "system.inspect"]


def test_mutating_workflow_stops_for_confirmation():
    runtime = FakeRuntime([], allowed={Capability.APP_LAUNCH})
    workflow = Workflow.new("Launch", steps=(WorkflowStep("computer.open_app", {"command": "example"}),))
    result = execute_workflow_request(runtime, InMemoryWorkflowStore(workflow), "do launch", confirmed=False)
    assert result.needs_confirmation
    assert runtime.calls == []
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_workflow_orchestration -v`
Expected: FAIL because the workflow execution/resolution path does not exist.

- [ ] **Step 3: Implement minimal integration using the existing operation catalog and `runtime.dispatch` boundary.**

- [ ] **Step 4: Run GREEN and regression tests**

Run: `python -m unittest tests.test_workflow_orchestration -v`
Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: execute persistent workflows through guarded runtime
```

---

### Task 4: Create failing family-location provider/model tests

**Files:**
- Create: `tests/test_family_locations.py`

**Interfaces:**
- Future `FamilyLocation`, `FamilyLocationProvider`, `FamilyLocationService`, `FollowState`.
- Tests use deterministic fixtures and never call Life360 or another live service.

- [ ] **Step 1: Write failing tests**

```python
import unittest
from datetime import datetime, timezone

from quality_of_life.family_locations import FamilyLocationService, Life360LocationAdapter


class FamilyLocationTests(unittest.TestCase):
    def test_normalizes_authorized_provider_payload(self):
        adapter = Life360LocationAdapter()
        locations = adapter.normalize({
            "members": [{
                "id": "member-1",
                "name": "Alex",
                "latitude": 34.1,
                "longitude": -117.9,
                "accuracy_m": 12,
                "updated_at": "2026-09-16T20:00:00+00:00",
                "sharing": "on",
            }]
        })
        self.assertEqual(locations[0].member_id, "member-1")
        self.assertEqual(locations[0].name, "Alex")
        self.assertEqual(locations[0].latitude, 34.1)

    def test_rejects_malformed_or_missing_coordinates(self):
        with self.assertRaises(ValueError):
            Life360LocationAdapter().normalize({"members": [{"id": "x", "name": "X"}]})

    def test_stale_location_is_explicitly_marked(self):
        location = FamilyLocationService.stale_from_fixture(
            "x", "Alex", 34.1, -117.9, observed_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        self.assertTrue(location.stale)

    def test_follow_only_moves_to_newer_update(self):
        service = FamilyLocationService()
        first = service.apply([])
        self.assertEqual(first, 0)
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_family_locations -v`
Expected: FAIL because the provider/model module does not exist.

- [ ] **Step 3: Commit failing tests**

```text
test: define authorized family location contract
```

---

### Task 5: Implement family-location normalization/follow state and God’s Eye integration

**Files:**
- Create: `quality_of_life/family_locations.py`
- Modify: `quality_of_life/permissions.py`
- Modify: `quality_of_life/capabilities.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/intents.py`
- Create/Modify: `tests/test_family_locations.py`
- Create/Modify: `tests/test_runtime_family_locations.py`

**Interfaces:**
- `FamilyLocation` is immutable, JSON-safe, and carries member id/name, coordinates, optional accuracy, source, observed-at, sharing state, and stale state.
- `FamilyLocationProvider.fetch()` returns normalized authorized locations; the base provider contract is dependency-free.
- `Life360LocationAdapter` parses only a caller-supplied authorized payload/bridge response; it does not fetch or scrape Life360 itself.
- `FamilyLocationService.refresh()`, `.members()`, `.get(name)`, `.follow(name)`, `.stop_follow()`, `.following()`, `.apply(locations)`.
- Read operations use a dedicated `FAMILY_LOCATION_READ` capability; provider setup/write operations remain behind existing account/confirmation mechanisms.
- The God’s Eye map state exposes family markers/follow target through a structured surface contract without altering existing current-location behavior.
- Deterministic intents include `where is <name>`, `show <name> on God’s Eye`, `show my family`, `follow <name>`, and `stop following`; ambiguous names return an ambiguity result instead of guessing.

- [ ] **Step 1: Extend failing tests to cover capability policy, runtime dispatch, intent parsing, ambiguity, follow transitions, stale state, and provider outage handling.**

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_family_locations tests.test_runtime_family_locations -v`
Expected: FAIL on missing capability/service integration.

- [ ] **Step 3: Implement minimal provider/model/service integration.**

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_family_locations tests.test_runtime_family_locations -v`
Expected: PASS.

- [ ] **Step 5: Run the complete regression suite**

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: PASS with no existing regression failures.

- [ ] **Step 6: Commit**

```text
feat: add authorized family locations to Gods Eye
```

---

### Task 6: Add documentation/configuration tests for both features

**Files:**
- Modify: `quality_of_life/README.md`
- Modify: `README.md`
- Create: `tests/test_feature_registration.py`

**Interfaces:**
- Documentation describes the workflow commands, `JARVIS_WORKFLOW_STORE`, family-location authorization boundary, stale-data behavior, and supported Life360 bridge contract without promising an unsupported direct API.
- Registration test verifies the new workflow/family tools and operations are present while existing tools remain present.

- [ ] **Step 1: Write the failing registration test.**

```python

def test_new_services_are_registered_without_removing_existing_tools():
    runtime = JarvisRuntime(CapabilityPolicy())
    names = runtime.available_tools()
    assert "workflows" in names
    assert "family_locations" in names
    assert "gods_eye" in names
    assert "computer" in names
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_feature_registration -v`
Expected: FAIL because the new services are not registered yet.

- [ ] **Step 3: Implement registration/documentation and run GREEN.**

- [ ] **Step 4: Commit**

```text
docs: document workflows and family Gods Eye integration
```

---

### Task 7: Diagnose and fix the native Windows visualizer smoke failure with tests first

**Files:**
- Modify: `scripts/jarvis_desktop.py`
- Modify: `.github/workflows/jarvis-release-gate.yml`
- Modify/Create: `tests/test_fullstack_components.py`

**Interfaces:**
- Preserve the existing `VisualizerAdapter` public behavior and loopback-only port 8790 contract.
- Make packaged startup resolve the bundled visualizer assets using the frozen executable’s actual `_MEIPASS` layout, validate `server.py` and `/faces/board/` before the HTTP server thread is declared ready, and avoid double-starting the visualizer from `main()`/`FullstackJarvisHost.start()`.
- Keep smoke mode deterministic and headless; no desktop UI interaction is required.
- Diagnostics must print the executable exit code, embedded visualizer path existence, and startup exception without exposing credentials.

- [ ] **Step 1: Add a failing regression test that models the packaged asset lookup and single-start lifecycle.**

```python

def test_main_starts_visualizer_exactly_once():
    visualizer = FakeVisualizer()
    controller = FakeController()
    host = FullstackJarvisHost(controller, visualizer=visualizer, voice=FakeVoice(), hands=FakeHands())
    host.start()
    self.assertEqual(visualizer.starts, 1)
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_fullstack_components -v`
Expected: FAIL against the current duplicate-start/lifecycle contract where applicable.

- [ ] **Step 3: Implement the smallest startup correction and add a smoke preflight that directly validates the bundled file path before polling HTTP.**

- [ ] **Step 4: Run GREEN and complete regression.**

Run: `python -m unittest tests.test_fullstack_components -v`
Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```text
fix: harden packaged Fullstack visualizer startup
```

---

### Task 8: Run CI checkpoints and repair any discovered regressions

**Files:**
- Modify only files implicated by failing tests/CI.

- [ ] **Step 1: Push/commit the feature branch changes.**
- [ ] **Step 2: Verify all six regression jobs pass on Python 3.11/3.12/3.13 across Ubuntu/Windows.**
- [ ] **Step 3: Verify Windows-maintenance tests remain green.**
- [ ] **Step 4: If any failure appears, reproduce it with a focused failing test before changing production code, then repeat the CI checkpoint.**
- [ ] **Step 5: Do not proceed to EXE release until the regression matrix is green.**

---

### Task 9: Build and smoke-test the native Jarvis.exe

**Files:**
- No production-file changes unless the release gate identifies a new reproducible failure.

- [ ] **Step 1: Trigger `.github/workflows/jarvis-release-gate.yml` on the verified branch/PR.**
- [ ] **Step 2: Verify Fullstack component fetch, dependency installation, PyInstaller build, and EXE size checks.**
- [ ] **Step 3: Verify the smoke test receives HTTP 200 from `http://127.0.0.1:8790/faces/board/` and the executable remains alive.**
- [ ] **Step 4: If smoke fails, inspect the captured desktop log/process/socket diagnostics, add the smallest regression test that reproduces the cause, fix it, and rerun the full gate.**
- [ ] **Step 5: Verify the raw `Jarvis.exe` artifact is uploaded only after the smoke gate passes.**

---

### Task 10: Final verification and completion review

**Files:**
- Modify only if verification exposes an issue.

- [ ] **Step 1: Compare the feature branch against `main` and inspect every changed file for unrelated changes.**
- [ ] **Step 2: Run the full Python regression suite one final time.**
- [ ] **Step 3: Run module compilation and Windows-maintenance unit tests one final time.**
- [ ] **Step 4: Verify the native Windows release gate is green, including the embedded visualizer smoke test.**
- [ ] **Step 5: Verify workflow persistence across two separate store instances and safe confirmation/capability behavior.**
- [ ] **Step 6: Verify family-location fixture normalization, ambiguity handling, stale reporting, and follow-state behavior without any live Life360 account.**
- [ ] **Step 7: Confirm no secrets, tokens, cookies, raw credentials, or raw shell commands are persisted by either feature.**
- [ ] **Step 8: Only after all checks are green, prepare the branch for merge/release; never label the work complete while any required gate is failing.**
