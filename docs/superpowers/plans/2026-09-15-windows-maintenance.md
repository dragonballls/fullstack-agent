# Windows Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guarded, optional Windows maintenance subsystem to fullstack-agent for PC health diagnostics, safe background-process cleanup, reversible startup prevention, and explicitly confirmed high-risk repairs.

**Architecture:** Keep `windows_maintenance/` independent of the existing `quality_of_life/` and `self_coding/` packages. The facade turns natural-language requests into typed operations; policy decides whether an operation is safe; Windows adapters perform only bounded commands; every mutation verifies its result. Existing QOL registration is extended only with lazy metadata so missing Windows-only dependencies never break imports.

**Tech Stack:** Python 3.11–3.13, standard library, PowerShell/CIM on Windows, unittest/pytest through existing CI, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-windows-maintenance-design.md`

## Global Constraints

- Windows-specific behavior must be guarded by `os.name == "nt"`.
- Diagnostics are read-only and must isolate individual check failures.
- Mutations require explicit user intent and policy approval; high-risk actions additionally require confirmation.
- Protected processes and protected system paths are never candidates for termination.
- Startup management is limited to reversible current-user Run entries.
- No arbitrary PowerShell or shell text may be accepted as a maintenance action.
- Existing QOL, God’s Eye, OmniRoute, voice, and self-coding code must remain importable and testable.
- No secrets are persisted by the maintenance package.

---

### Task 1: Add the isolated maintenance contracts and Windows adapter

**Files:**
- Create: `windows_maintenance/__init__.py`
- Create: `windows_maintenance/models.py`
- Create: `windows_maintenance/policy.py`
- Create: `windows_maintenance/windows.py`

- [ ] **Step 1: Write failing tests for contracts and non-Windows behavior**
- [ ] **Step 2: Run focused tests and verify failure**
- [ ] **Step 3: Implement typed models, deny-by-default policy, and bounded PowerShell/process/startup primitives**
- [ ] **Step 4: Run focused tests and verify pass**
- [ ] **Step 5: Commit `feat: add guarded Windows maintenance core`**

### Task 2: Add diagnostics and process/startup managers

**Files:**
- Create: `windows_maintenance/diagnostics.py`
- Create: `windows_maintenance/processes.py`
- Create: `windows_maintenance/startup.py`
- Create: `windows_maintenance/repairs.py`

- [ ] **Step 1: Add tests for protected-process filtering, resource candidates, and startup allowlist**
- [ ] **Step 2: Run focused tests and verify failure where implementation is absent**
- [ ] **Step 3: Implement managers with verification and per-operation error containment**
- [ ] **Step 4: Run focused tests and verify pass**
- [ ] **Step 5: Commit `feat: add Windows diagnostics and safe maintenance operations`**

### Task 3: Add natural-language facade and audit records

**Files:**
- Create: `windows_maintenance/audit.py`
- Create: `windows_maintenance/facade.py`

- [ ] **Step 1: Test diagnostic, cleanup, startup, and high-risk confirmation flows**
- [ ] **Step 2: Run focused tests and verify failure where behavior is absent**
- [ ] **Step 3: Implement structured intent detection and guarded execution**
- [ ] **Step 4: Run full maintenance test suite and verify pass**
- [ ] **Step 5: Commit `feat: expose Windows maintenance facade`**

### Task 4: Wire lazy discovery into the existing QOL layer

**Files:**
- Modify: `quality_of_life/manifest.py`
- Modify: `quality_of_life/intents.py`
- Modify: `quality_of_life/README.md`
- Modify: `CLAUDE.md`
- Modify: `fullstack-agent.md`
- Test: `tests/test_windows_maintenance_integration.py`

- [ ] **Step 1: Add integration-contract tests**
- [ ] **Step 2: Run focused tests and verify failure**
- [ ] **Step 3: Register the maintenance tool lazily, add maintenance intent recognition, and document deny-by-default behavior**
- [ ] **Step 4: Run all existing integration/QOL/self-coding tests plus maintenance tests**
- [ ] **Step 5: Commit `feat: integrate Windows maintenance into Jarvis control plane`**

### Task 5: Add CI coverage and final verification gate

**Files:**
- Create: `.github/workflows/windows-maintenance.yml`

- [ ] **Step 1: Add platform-aware CI that runs portable unit tests on Linux and Windows adapter tests only on Windows**
- [ ] **Step 2: Validate the same test commands locally where possible**
- [ ] **Step 3: Push branch, inspect all workflow jobs, and fix every failure**
- [ ] **Step 4: Run the final complete regression set and keep the PR draft until green**
- [ ] **Step 5: Commit only verified changes and request merge after all checks pass**
