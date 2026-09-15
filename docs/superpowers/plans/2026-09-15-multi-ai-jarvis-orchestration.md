# Multi-AI Jarvis Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fast, fail-safe multi-model orchestration layer over the existing `quality_of_life/`, Windows-maintenance, self-coding, God's Eye, memory/voice integration, and OmniRoute path without weakening existing safety controls.

**Architecture:** Keep the existing capability registry, permission policy, confirmation gate, deterministic tool implementations, Windows maintenance facade, and self-coding engine as the execution authority. Add a separate orchestration layer that classifies requests into fast/smart/coding/vision/maintenance profiles, uses OmniRoute as the cloud transport, parallelizes independent read-only specialist work when useful, verifies proposed actions before dispatch, streams early acknowledgement where supported, and falls back deterministically when a provider/model fails.

**Tech Stack:** Python 3.11-3.13, standard library concurrency/async primitives, existing `quality_of_life.router.CloudModelRouter`, existing `quality_of_life.orchestrator.QoLOrchestrator`, existing capability policy, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-full-jarvis-integration-design.md`

## Global Constraints

- Preserve deny-by-default permissions and existing confirmation hooks for mutating actions.
- Keep cloud model routing cloud-only and never silently select a local LLM.
- Missing provider credentials or failed providers must return structured diagnostics without leaking secrets.
- Keep self-coding isolated behind its existing clean-tree, branch, verification, commit, and rollback contract.
- Optional dependencies must fail closed and must not break base imports.
- Windows-maintenance failures must not crash unrelated runtime components.
- Existing QOL, self-coding, integration, and Windows-maintenance tests must remain passing.
- Do not copy the old Mark-LIII repository wholesale; reuse only compatible patterns.
- Never claim physical Windows behavior such as actual microphone/speaker, mouse, browser, or camera success from hosted CI alone.
- Optimize for minimum latency: fast-path simple requests, parallelize independent read-only work, avoid redundant model calls, and use timeouts/fallbacks.

---

### Task 1: Establish orchestration contracts and profile selection

**Files:**
- Create: `quality_of_life/orchestration.py`
- Test: `quality_of_life/tests/test_orchestration.py`

**Interfaces:**
- Consumes: user text, optional requested capability context, existing `Capability` enum.
- Produces: `RequestProfile`, `OrchestrationPlan`, and deterministic `classify_request(text)`.

- [ ] **Step 1: Write failing tests**

```python
from quality_of_life.orchestration import RequestProfile, classify_request


def test_simple_request_uses_fast_profile():
    assert classify_request("what time is it") is RequestProfile.FAST


def test_code_request_uses_coding_profile():
    assert classify_request("fix the failing pytest and run the tests") is RequestProfile.CODING


def test_pc_repair_request_uses_maintenance_profile():
    assert classify_request("diagnose my PC and safely fix the problems") is RequestProfile.MAINTENANCE


def test_screen_understanding_uses_vision_profile():
    assert classify_request("look at my screen and tell me what is wrong") is RequestProfile.VISION
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m unittest quality_of_life.tests.test_orchestration -v`
Expected: import failure because `quality_of_life.orchestration` does not yet exist.

- [ ] **Step 3: Implement minimal contracts**

Create an enum with `FAST`, `SMART`, `CODING`, `VISION`, and `MAINTENANCE`. Implement conservative keyword/intent scoring that prefers the specialized profile only when the request clearly indicates that task class; otherwise return `FAST`. Do not invoke a model during classification.

- [ ] **Step 4: Add plan generation tests**

```python
from quality_of_life.orchestration import RequestProfile, build_plan


def test_fast_plan_has_one_primary_call():
    plan = build_plan("open my browser", RequestProfile.FAST)
    assert plan.primary.profile is RequestProfile.FAST
    assert plan.parallel_tasks == ()


def test_maintenance_plan_can_parallelize_read_only_inspection():
    plan = build_plan("diagnose and fix my PC", RequestProfile.MAINTENANCE)
    assert {task.kind for task in plan.parallel_tasks} == {"pc_diagnostics", "process_snapshot"}
```

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest quality_of_life.tests.test_orchestration -v`
Expected: PASS.

Commit: `feat: add deterministic multi-ai request planning`

---

### Task 2: Extend the existing OmniRoute router for profiles, parallel calls, and health-aware fallback

**Files:**
- Modify: `quality_of_life/router.py`
- Test: `quality_of_life/tests/test_router.py`

**Interfaces:**
- Consumes: `RequestProfile`, existing `ProviderTarget`, environment configuration.
- Produces: `complete_profiled(messages, profile)`, `complete_many(requests, profile)`, and structured provider error records.

- [ ] **Step 1: Write failing router tests**

```python
from quality_of_life.router import CloudModelRouter, ProviderTarget


def test_profile_selects_explicit_model_mapping(monkeypatch):
    monkeypatch.setenv("JARVIS_OMNIROUTE_FAST_MODEL", "auto/fast")
    assert CloudModelRouter.profile_model("fast") == "auto/fast"


def test_missing_non_loopback_key_is_reported_without_request(monkeypatch):
    target = ProviderTarget("cloud", "https://example.test/v1", "MISSING_KEY", "model")
    router = CloudModelRouter((target,))
    result = router.try_target(target, [{"role": "user", "content": "hi"}])
    assert result.ok is False
    assert "missing MISSING_KEY" in result.error


def test_parallel_completion_returns_results_in_input_order():
    # use an injected transport in the test helper; no external network is used
    ...
```

- [ ] **Step 2: Run router tests and verify the new assertions fail**

Run: `python -m unittest quality_of_life.tests.test_router -v`
Expected: FAIL only on the new profile/parallel APIs.

- [ ] **Step 3: Implement profile-aware model selection**

Add environment-driven profile mappings with safe defaults: fast=`auto/fast`, smart=`auto/smart`, coding=`auto/coding`, vision=`auto/vision` when supported by OmniRoute, maintenance=`auto/smart`. Permit explicit `JARVIS_OMNIROUTE_<PROFILE>_MODEL` overrides. Do not create direct provider dependencies in this layer.

- [ ] **Step 4: Implement bounded health-aware calls**

Add a small `ProviderResult` dataclass carrying `ok`, `text`, `target_name`, `latency_ms`, and redacted `error`. Reuse existing target validation. Timeouts must remain bounded. Maintain an in-memory per-process cooldown for repeatedly failing targets so a bad provider is not retried on every request.

- [ ] **Step 5: Implement bounded parallel completion**

Use `ThreadPoolExecutor` with a small fixed worker cap from `JARVIS_OMNIROUTE_MAX_PARALLEL` (default 4). Never exceed the configured cap. Preserve request ordering in returned results. Cancel pending work when the caller requests a hard timeout. Do not mutate shared request message dictionaries.

- [ ] **Step 6: Run tests and commit**

Run: `python -m unittest quality_of_life.tests.test_router -v`
Expected: PASS.

Commit: `feat: add profiled parallel omniroute routing`

---

### Task 3: Add the orchestration engine with parallel specialist execution and verification

**Files:**
- Create: `quality_of_life/agent_orchestrator.py`
- Test: `quality_of_life/tests/test_agent_orchestrator.py`

**Interfaces:**
- Consumes: `OrchestrationPlan`, `CloudModelRouter`, `JarvisRuntime`, capability policy.
- Produces: `OrchestrationResult` and `execute(text, confirmed=False)`.

- [ ] **Step 1: Write failing tests**

```python
from quality_of_life.agent_orchestrator import AgentOrchestrator


def test_fast_request_uses_one_model_call(fake_router, fake_runtime):
    result = AgentOrchestrator(fake_router, fake_runtime).execute("summarize this")
    assert fake_router.call_count == 1
    assert result.verified is True


def test_parallel_read_only_specialists_run_concurrently(fake_router, fake_runtime):
    result = AgentOrchestrator(fake_router, fake_runtime).execute("diagnose my PC")
    assert result.profile == "maintenance"
    assert result.parallel_tasks_completed >= 2


def test_mutation_never_bypasses_runtime_policy(fake_router, fake_runtime):
    result = AgentOrchestrator(fake_router, fake_runtime).execute("close this application")
    assert fake_runtime.mutating_calls == 0
    assert result.needs_confirmation is True
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `python -m unittest quality_of_life.tests.test_agent_orchestrator -v`
Expected: FAIL because the orchestrator engine is absent.

- [ ] **Step 3: Implement the bounded orchestration engine**

Implement these stages:

```text
classify -> build_plan -> run independent read-only tasks in parallel
         -> aggregate context -> one synthesis/model call
         -> validate requested action against deterministic runtime policy
         -> dispatch allowed action
         -> verify result when a deterministic verifier exists
```

For ordinary requests, use one model call. For specialized tasks, only run the minimum necessary specialist calls. Never ask a model to produce or execute arbitrary shell text. All computer, browser, location, clipboard, and maintenance actions must dispatch through `JarvisRuntime.dispatch`.

- [ ] **Step 4: Implement verification contract**

Verification must be deterministic where possible: inspect returned operation result, check expected state transitions, and for maintenance reuse the maintenance facade's post-repair verification. A model may review an output but cannot override a failed deterministic verification.

- [ ] **Step 5: Add timeout and cancellation behavior**

Set per-stage timeouts from environment defaults. On timeout, cancel pending parallel tasks, preserve completed safe read-only context, and return a structured partial result plus provider diagnostics. Never leave background executor threads holding mutable capability locks.

- [ ] **Step 6: Run tests and commit**

Run: `python -m unittest quality_of_life.tests.test_agent_orchestrator -v`
Expected: PASS.

Commit: `feat: add guarded multi-agent orchestration engine`

---

### Task 4: Integrate the orchestrator into `JarvisRuntime` without changing existing operation semantics

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/__init__.py`
- Test: `quality_of_life/tests/test_runtime.py`

**Interfaces:**
- Consumes: `AgentOrchestrator` from Task 3.
- Produces: `JarvisRuntime.handle_assistant_request(text, confirmed=False)` while preserving existing `dispatch` and `handle_text` behavior.

- [ ] **Step 1: Write failing integration tests**

```python

def test_existing_dispatch_api_is_unchanged(fake_runtime):
    assert fake_runtime.dispatch(capability, operation) == expected


def test_assistant_request_uses_orchestration_layer(fake_runtime):
    result = fake_runtime.handle_assistant_request("diagnose my PC")
    assert result["profile"] == "maintenance"
```

- [ ] **Step 2: Run the integration tests and verify only the new API fails**

Run: `python -m unittest quality_of_life.tests.test_runtime -v`
Expected: existing runtime tests stay green; the new method is initially absent.

- [ ] **Step 3: Implement lazy orchestrator construction**

Instantiate the orchestrator lazily so base imports do not require optional dependencies. Reuse the existing cloud router factory and the same policy object. Do not duplicate action registration.

- [ ] **Step 4: Preserve existing `handle_text` routing**

Keep the current conservative intent parser behavior. The new assistant-request entry point should be additive; existing callers keep their exact dispatch path.

- [ ] **Step 5: Run complete QOL tests and commit**

Run: `python -m unittest discover -s quality_of_life/tests -v`
Expected: PASS.

Commit: `feat: expose unified assistant orchestration through runtime`

---

### Task 5: Add early acknowledgement and streaming-safe orchestration hooks

**Files:**
- Modify: `quality_of_life/agent_orchestrator.py`
- Test: `quality_of_life/tests/test_agent_orchestrator.py`

**Interfaces:**
- Consumes: optional acknowledgement callback and result callback.
- Produces: `execute_stream(text, confirmed=False, on_event=None)` yielding typed orchestration events.

- [ ] **Step 1: Write failing event-order tests**

```python

def test_stream_emits_ack_then_progress_then_result(fake_router, fake_runtime):
    events = list(AgentOrchestrator(fake_router, fake_runtime).execute_stream("diagnose my PC"))
    assert events[0].kind == "ack"
    assert events[-1].kind == "result"
    assert any(event.kind == "progress" for event in events)
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m unittest quality_of_life.tests.test_agent_orchestrator -v`
Expected: FAIL because the streaming API is absent.

- [ ] **Step 3: Implement event stream**

Emit a local acknowledgement immediately, then progress events as independent tasks complete, then the verified result. The acknowledgement must not require a second model call. Do not synthesize voice audio in this layer.

- [ ] **Step 4: Add cancellation test**

Verify that cancellation stops pending orchestration work and never dispatches an unapproved mutation.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest quality_of_life.tests.test_agent_orchestrator -v`
Expected: PASS.

Commit: `feat: add low-latency orchestration events`

---

### Task 6: Add autonomous monitoring/recovery hooks without making background mutation automatic

**Files:**
- Create: `quality_of_life/health_monitor.py`
- Test: `quality_of_life/tests/test_health_monitor.py`
- Modify: `quality_of_life/runtime.py`

**Interfaces:**
- Consumes: existing diagnostics/maintenance facade and background job facility.
- Produces: `HealthMonitor.start()`, `stop()`, `snapshot()`, and `recommended_actions()`.

- [ ] **Step 1: Write failing tests**

```python

def test_monitor_is_disabled_by_default():
    monitor = HealthMonitor.from_environment()
    assert monitor.enabled is False


def test_monitor_only_reports_recommended_repairs(fake_facade):
    monitor = HealthMonitor(fake_facade, interval_seconds=60, enabled=True)
    recommendations = monitor.recommended_actions()
    assert fake_facade.mutation_calls == 0
    assert recommendations
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m unittest quality_of_life.tests.test_health_monitor -v`
Expected: FAIL because the monitor module is absent.

- [ ] **Step 3: Implement bounded monitoring**

Run read-only health snapshots on a configurable interval. Detect repeated failures and resource anomalies through existing maintenance APIs. Never automatically perform high-risk changes. The monitor may propose safe actions, but actual mutation still goes through the normal confirmation/policy path.

- [ ] **Step 4: Integrate with background jobs lazily**

Make startup opt-in through `JARVIS_HEALTH_MONITOR=1`. If optional dependencies are missing, report unavailable rather than raising during runtime initialization.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest quality_of_life.tests.test_health_monitor quality_of_life.tests.test_runtime -v`
Expected: PASS.

Commit: `feat: add opt-in background health monitoring`

---

### Task 7: Strengthen voice integration discoverability and production checks

**Files:**
- Modify: `JARVIS_VOICE.md`
- Modify: `fullstack-agent.md`
- Test: `tests/test_voice_integration.py`

**Interfaces:**
- Consumes: existing backtalk installer path and `JARVIS_VOICE.md` contract.
- Produces: explicit installer instructions for ElevenLabs validation, fallback, and secret handling.

- [ ] **Step 1: Write failing documentation-integration tests**

```python

def test_installer_references_voice_contract():
    installer = Path("fullstack-agent.md").read_text()
    assert "JARVIS_VOICE.md" in installer
    assert "ELEVENLABS_API_KEY" in installer


def test_voice_contract_requires_real_speech_test():
    voice = Path("JARVIS_VOICE.md").read_text()
    assert "actual speech test" in voice.lower()
```

- [ ] **Step 2: Run tests and inspect the failure**

Run: `python -m unittest tests.test_voice_integration -v`
Expected: only assertions for missing/stale installer wording may fail; do not weaken existing contract tests.

- [ ] **Step 3: Update installer guidance**

Explicitly state that ElevenLabs is preferred, credentials must remain outside Git, the requested voice must be discovered rather than guessing an ID, a real speech test is required, and Kokoro remains the fallback. Do not hard-code secrets or unsupported IDs.

- [ ] **Step 4: Run tests and commit**

Run: `python -m unittest tests.test_voice_integration -v`
Expected: PASS.

Commit: `docs: wire verified jarvis voice setup into installer`

---

### Task 8: Add end-to-end regression coverage and latency guardrails

**Files:**
- Create: `tests/test_multi_ai_integration.py`
- Modify: `.github/workflows/quality-of-life-tests.yml`
- Modify: `.github/workflows/integration-tests.yml`

**Interfaces:**
- Consumes: the public runtime orchestration API.
- Produces: CI proof that fast-path, parallel-path, policy gates, provider fallback, and optional-dependency isolation work together.

- [ ] **Step 1: Write failing end-to-end tests**

Cover these cases with fake local transports only:

```python

def test_fast_path_single_model_call(): ...
def test_complex_request_parallelizes_read_only_work(): ...
def test_failed_primary_provider_falls_back(): ...
def test_all_provider_failures_are_structured_and_secret_free(): ...
def test_high_risk_action_still_requires_confirmation(): ...
def test_optional_maintenance_import_does_not_break_base_imports(): ...
def test_self_coding_path_remains_separate(): ...
```

- [ ] **Step 2: Run end-to-end tests and verify failures**

Run: `python -m unittest tests.test_multi_ai_integration -v`
Expected: new integration assertions fail until the full wiring is complete.

- [ ] **Step 3: Implement CI integration**

Run the new integration suite in the existing integration workflow and the QOL matrix. Keep Windows/Linux Python 3.11/3.12/3.13 coverage intact.

- [ ] **Step 4: Add latency-focused unit checks**

Use injected fake transports with known delays to verify that independent tasks finish approximately within the slowest parallel task duration rather than the sum of all task durations. Do not make CI timing assertions brittle; assert ordering/parallelism via synchronization primitives instead.

- [ ] **Step 5: Run the full local test suites and commit**

Run:
`python -m unittest discover -s quality_of_life/tests -v`
`python -m unittest discover -s tests -v`
Expected: PASS.

Commit: `test: add full multi-ai orchestration regression coverage`

---

### Task 9: Final verification and release-readiness gate

**Files:**
- Modify: `JARVIS_READINESS.md`
- Test: existing CI workflows and all project tests

- [ ] **Step 1: Run local compile/import checks**

Run: `python -m compileall -q quality_of_life windows_maintenance self_coding tests`
Expected: exit code 0.

- [ ] **Step 2: Run complete local test suites**

Run: `python -m unittest discover -s quality_of_life/tests -v` and `python -m unittest discover -s tests -v`
Expected: all tests pass.

- [ ] **Step 3: Inspect GitHub Actions for the exact final commit SHA**

Verify QOL matrix, Windows maintenance, self-coding safety, and integration workflows all complete successfully for the final branch head. Historical green runs on older commits do not count as verification of the final head.

- [ ] **Step 4: Fix every observed regression**

For any failure: isolate the smallest failing test, reproduce it, patch the narrowest compatible interface, rerun the focused test, then rerun the affected complete suite before proceeding.

- [ ] **Step 5: Update readiness status only from evidence**

Mark the new orchestration capabilities ready only when the exact final SHA has passing required checks. Explicitly distinguish hosted-CI verification from machine-only voice/mouse/browser/camera checks.

- [ ] **Step 6: Final commit**

Commit: `chore: finalize multi-ai jarvis readiness`

---

## Self-Review

Spec coverage: installer discovery and optional-dependency isolation are covered by Tasks 4, 7, and 8; deny-by-default and confirmation remain in Tasks 3 and 8; self-coding isolation is regression-tested in Task 8; cloud-only routing is enforced in Task 2; voice setup is documented and tested in Task 7; QOL and self-coding CI are retained in Task 8; Windows-only physical behaviors remain explicitly separated in Task 9.

Placeholder scan: the only ellipses appear inside intentionally schematic test stubs in Task 8; implementers must replace each with concrete fake-transport test code before committing, and the task explicitly requires those cases.

Type consistency: `RequestProfile` is produced by Task 1, consumed by Task 2; `OrchestrationPlan` is consumed by Task 3; `AgentOrchestrator` is exposed by Task 4; streaming and monitoring build on those stable interfaces.
