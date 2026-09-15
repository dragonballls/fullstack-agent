# Universal Capability Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a general-purpose typed capability layer so natural-language requests can reach safe computer, browser, filesystem, software, process, networking, settings, scheduling, maintenance, location, and development operations without exposing arbitrary shell execution.

**Architecture:** Keep `quality_of_life/permissions.py` and `quality_of_life/orchestrator.py` as the authoritative policy boundary. Add focused adapters and a capability catalog, then connect them through `runtime.py` and the existing assistant orchestrator. Existing self-coding, cloud routing, God’s Eye, voice, browser automation, and Windows maintenance remain separate implementations behind typed interfaces.

**Tech Stack:** Python 3.11–3.13, unittest/pytest as already used by the repository, Windows standard-library APIs where practical, existing QOL adapters, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-universal-capability-agent-design.md`

## Global Constraints

- Deny-by-default permissions remain authoritative.
- Destructive or externally consequential actions require confirmation.
- Model-generated text must never become arbitrary shell or scripting input.
- Optional dependencies must not break unrelated imports.
- Existing self-coding isolation, verification, rollback, and cloud-only routing remain intact.
- Never claim an operation succeeded without verification.
- Never log or persist secrets.
- Hosted CI cannot certify physical desktop/device behavior.

---

### Task 1: Add capability families and operation metadata

**Files:**
- Modify: `quality_of_life/permissions.py`
- Create: `quality_of_life/capabilities.py`
- Test: `tests/test_capability_catalog.py`

**Interfaces:**
- Produces stable capability family names, typed operation metadata, and mutation/confirmation classification.

- [ ] Write failing tests for stable family names and mutation metadata.
- [ ] Run the focused tests and verify the new assertions fail.
- [ ] Add the capability families and immutable operation descriptors.
- [ ] Keep existing enum values backward compatible.
- [ ] Run focused tests and compile checks.
- [ ] Commit.

### Task 2: Build browser discovery and selection

**Files:**
- Create: `quality_of_life/browser_registry.py`
- Modify: `quality_of_life/browser.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Test: `tests/test_browser_registry.py`

**Interfaces:**
- `BrowserInstallation`: normalized browser id, display name, executable path, family, and availability.
- `BrowserRegistry.discover() -> tuple[BrowserInstallation, ...]`.
- `BrowserRegistry.resolve(name: str) -> BrowserInstallation`.
- `BrowserController.open_url(url: str, browser: str | None = None)`.

- [ ] Test aliases including Edge, Chrome, Opera, Opera GX, Firefox, Brave, and normalized spellings.
- [ ] Test mocked registry/known-path discovery without touching the host.
- [ ] Test unknown/unavailable browser failure and HTTP(S)-only URL validation.
- [ ] Implement deterministic Windows discovery and cache invalidation on launch failure.
- [ ] Preserve existing Playwright behavior and do not silently change the default browser.
- [ ] Run browser-focused and existing QOL tests.
- [ ] Commit.

### Task 3: Add guarded filesystem operations

**Files:**
- Create: `quality_of_life/files.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Test: `tests/test_files_capability.py`

**Interfaces:**
- Read-only metadata/search operations are separate from mutations.
- Mutations require explicit normalized targets and policy confirmation.
- Deletion rejects ambiguous roots and protected system locations.

- [ ] Write tests for read, create, move, copy, rename, and guarded delete.
- [ ] Test traversal/path normalization and protected-location rejection.
- [ ] Implement bounded filesystem adapter using `pathlib`/standard library.
- [ ] Add post-operation verification and structured failures.
- [ ] Run focused tests and full QOL regression tests.
- [ ] Commit.

### Task 4: Add installed-application inventory and uninstall

**Files:**
- Create: `quality_of_life/applications.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Test: `tests/test_applications_capability.py`

**Interfaces:**
- `InstalledApplication` contains normalized identity, publisher, version, uninstall command metadata, and source.
- Inventory reads Windows uninstall registry locations without executing commands.
- `uninstall(name_or_id, confirmed=False)` requires exact/unique identity resolution, confirmation, safe registered-uninstaller selection, and post-action verification.

- [ ] Test inventory parsing from mocked registry data.
- [ ] Test ambiguous matches are rejected.
- [ ] Test protected/system components are rejected.
- [ ] Test uninstall cannot execute before confirmation.
- [ ] Test command construction uses structured executable/argument data and rejects unsafe installer metadata.
- [ ] Implement MSI/registered-uninstaller handling with no arbitrary model-supplied command strings.
- [ ] Run focused tests and Windows maintenance/QOL suites.
- [ ] Commit.

### Task 5: Add process and service control

**Files:**
- Create: `quality_of_life/processes.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Test: `tests/test_process_capability.py`

**Interfaces:**
- Read-only process/service inventory.
- Guarded stop/restart operations with identity checks, protected-process policy, confirmation, and post-action verification.

- [ ] Test protected-process rejection and stale PID identity rejection.
- [ ] Test service/process inventory parsing with injected providers.
- [ ] Implement minimal structured controls and verification.
- [ ] Run focused and full regression tests.
- [ ] Commit.

### Task 6: Add networking and supported system settings

**Files:**
- Create: `quality_of_life/system.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Test: `tests/test_system_capability.py`

**Interfaces:**
- Read adapter/network/DNS/proxy state.
- Support only explicitly modeled user/system settings.
- Privileged or externally consequential changes remain confirmation-gated.

- [ ] Test read-only inspection with injected providers.
- [ ] Test invalid setting names and unsafe values.
- [ ] Implement bounded adapters without arbitrary registry/script execution.
- [ ] Verify changes when supported; return unavailable when verification is impossible.
- [ ] Run focused and full regression tests.
- [ ] Commit.

### Task 7: Add scheduling/notifications and capability discovery

**Files:**
- Modify: `quality_of_life/background.py`
- Create: `quality_of_life/scheduler.py`
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/runtime.py`
- Test: `tests/test_scheduler_capability.py`

**Interfaces:**
- Typed bounded jobs with cancellation, status, and optional user-visible notification hooks.
- No arbitrary persistent startup task creation through model text.

- [ ] Test job lifecycle and cancellation-token compatibility.
- [ ] Test scheduling input bounds and confirmation requirements.
- [ ] Implement scheduler on top of existing background primitives.
- [ ] Run focused and full regression tests.
- [ ] Commit.

### Task 8: Connect natural-language requests to typed capabilities

**Files:**
- Modify: `quality_of_life/agent_orchestrator.py`
- Modify: `quality_of_life/runtime.py`
- Create/Modify: `quality_of_life/planner.py`
- Test: `tests/test_universal_agent_routing.py`

**Interfaces:**
- Planner output is a typed operation plan, not executable shell text.
- Runtime validates every operation against capability policy and confirmation before dispatch.
- Verification results are returned to the assistant response.

- [ ] Add tests for browser selection, file actions, app uninstall, process actions, and maintenance requests.
- [ ] Test that ambiguous/destructive requests become confirmation requests rather than execution.
- [ ] Test that unsupported requests report unavailable capability instead of hallucinating success.
- [ ] Implement typed plan normalization and dispatch.
- [ ] Preserve selective multi-AI routing; do not fan out trivial requests unnecessarily.
- [ ] Run full regression and integration tests.
- [ ] Commit.

### Task 9: Add integration/readiness gate

**Files:**
- Modify: `.github/workflows/integration-tests.yml`
- Create/Modify: `tests/test_universal_integration.py`

- [ ] Verify every registered capability has an import-safe factory and policy mapping.
- [ ] Verify no capability adapter introduces forbidden arbitrary-shell execution.
- [ ] Compile all Python modules.
- [ ] Run complete test suite.
- [ ] Run Windows-specific maintenance suite.
- [ ] Commit only after all local checks pass.

### Task 10: Exact-head CI verification and completion gate

- [ ] Fetch current branch head.
- [ ] Confirm every required workflow run has the exact current head SHA.
- [ ] Inspect failed jobs/logs if any and fix them before proceeding.
- [ ] Rerun failed jobs where appropriate.
- [ ] Confirm QOL matrix, integration, self-coding, and Windows maintenance workflows are green on the exact final head.
- [ ] Review the final diff for accidental unrelated changes.
- [ ] Only then report 100% for the implemented scope.
