# Migrate Today's Jarvis Work Into fullstack-agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the verified same-day Jarvis engineering work from `dragonballls/Jarvis` into `dragonballls/fullstack-agent` without replacing or regressing the upstream Fullstack Agent architecture, while producing the real Fullstack Agent-style single Windows EXE.

**Architecture:** `fullstack-agent` is the sole source of truth and destination. Existing upstream components remain first-class: `ai-memory-vault`, `backtalk`, `ai-visualizer`, and `barehands`. Jarvis additions are integrated behind those contracts: one guarded Jarvis/OmniRoute brain and tool executor, guarded self-coding, workflow orchestration, Windows maintenance, account/provider infrastructure, computer/hand control, God's Eye/location adapters, voice integration, startup/update, and Windows release verification.

**Tech Stack:** Python 3.12+, existing upstream Fullstack Agent components, current Jarvis Python modules, PyInstaller one-file/windowed, pywebview, GitHub Actions on Windows, existing test suite.

**Spec:** `docs/superpowers/specs/2026-09-16-jarvis-single-exe-fullstack-design.md`

## Global Constraints

- `dragonballls/fullstack-agent` is the only repository modified by this migration.
- Preserve the upstream Fullstack Agent face/voice/hands stack and AGPL-3.0-or-later licensing.
- Do not replace the existing Fullstack Agent application with the obsolete 640x118 Tk launcher.
- Keep one authoritative Jarvis planner/tool executor; do not add a competing Claude brain.
- Preserve confirmation gates, capability policy, cancellation, emergency stop, credential broker, and self-coding safeguards.
- Do not copy secrets, tokens, local machine state, or generated artifacts from the old Jarvis repository.
- Prefer feature-level ports and adapters over wholesale file replacement.
- Every migrated subsystem must have focused regression coverage before integration.
- The final Windows distribution must be a real Fullstack Agent-style `Jarvis.exe`; ZIP files may be CI transport artifacts only.

---

### Task 1: Inventory and map the source changes

**Files:**
- Create: `docs/superpowers/migration/jarvis-source-inventory.md`
- Test: existing GitHub workflow/test metadata

**Interfaces:**
- Produces a source-to-destination mapping for every same-day Jarvis change, including source commit, source paths, destination paths, collision strategy, and verification evidence.

- [ ] **Step 1: Enumerate same-day Jarvis commits and changed files**
- [ ] **Step 2: Classify each change as shared infrastructure, feature, test, packaging, or obsolete Jarvis-only UI**
- [ ] **Step 3: Record destination mapping into the inventory**
- [ ] **Step 4: Mark files requiring adaptation rather than copying**
- [ ] **Step 5: Review the inventory for omissions and duplicate implementations**
- [ ] **Step 6: Commit the inventory**

### Task 2: Establish a migration branch and protect the upstream baseline

**Files:**
- Modify: branch/ref only; no production source replacement
- Create: `docs/superpowers/migration/BASELINE.md`

**Interfaces:**
- Branch `migrate/jarvis-work-into-fullstack-agent` starts exactly from current `fullstack-agent/main`.

- [ ] **Step 1: Create the migration branch from current `main`**
- [ ] **Step 2: Record the source baseline commit and destination baseline commit**
- [ ] **Step 3: Ensure no source secrets or machine artifacts are present**
- [ ] **Step 4: Commit the baseline record**

### Task 3: Port core self-coding and workflow orchestration

**Files:**
- Modify/create: existing `self_coding/`, `agent/`, workflow/orchestration modules mapped by Task 1
- Test: corresponding `tests/` modules

**Interfaces:**
- Preserve dependency-aware planning, isolated workspaces/branches, verification, rollback, and guarded execution.

- [ ] **Step 1: Write failing regression tests for each missing migrated contract**
- [ ] **Step 2: Port the smallest implementation units**
- [ ] **Step 3: Run focused tests and fix failures**
- [ ] **Step 4: Run the full Python regression suite**
- [ ] **Step 5: Commit the subsystem**

### Task 4: Port provider routing, voice, and cloud-AI infrastructure

**Files:**
- Modify/create: provider, voice, credentials, routing, and account modules mapped by Task 1
- Test: corresponding provider/voice/account tests

**Interfaces:**
- Preserve cloud-first routing, provider configuration, voice contracts, credential isolation, and single-brain execution.

- [ ] **Step 1: Write failing adapter/contract tests**
- [ ] **Step 2: Port provider and voice implementations**
- [ ] **Step 3: Verify degraded behavior without optional credentials/hardware**
- [ ] **Step 4: Run focused and full regression tests**
- [ ] **Step 5: Commit the subsystem**

### Task 5: Port quality-of-life, guarded computer control, hand control, and Windows maintenance

**Files:**
- Modify/create: `quality_of_life/`, `windows_maintenance/`, hand-control and computer-use modules mapped by Task 1
- Test: corresponding safety and adapter tests

**Interfaces:**
- Preserve deny-by-default mutations, explicit activation, fails-closed tracking loss, emergency stop, safe process cleanup, startup controls, and Windows maintenance verification.

- [ ] **Step 1: Write failing integration/safety tests for missing contracts**
- [ ] **Step 2: Port adapters and runtime implementations without copying machine-specific state**
- [ ] **Step 3: Run focused safety tests**
- [ ] **Step 4: Run the complete regression suite**
- [ ] **Step 5: Commit the subsystem**

### Task 6: Port location/God's Eye and family-location adapters

**Files:**
- Modify/create: location, God's Eye, family-location/Life360 adapter modules mapped by Task 1
- Test: corresponding parser, security, and integration tests

**Interfaces:**
- Preserve consent-based shared-link handling, redaction, authentication boundaries, cached normalized locations, and explicit follow/tracking requests.

- [ ] **Step 1: Write failing contract tests**
- [ ] **Step 2: Port the adapter/service layer**
- [ ] **Step 3: Verify unsupported/private-api paths fail explicitly**
- [ ] **Step 4: Run focused and full regression tests**
- [ ] **Step 5: Commit the subsystem**

### Task 7: Replace the obsolete launcher with the actual Fullstack Agent host

**Files:**
- Modify: `scripts/jarvis_desktop.py`
- Modify: `scripts/jarvis_desktop.pyw`
- Create/modify: fullstack host, visualizer, voice bridge, and asset adapters
- Test: `tests/test_single_exe_contract.py`, `tests/test_jarvis_fullstack_host.py`, `tests/test_fullstack_assets.py`, `tests/test_jarvis_voice_bridge.py`

**Interfaces:**
- `FullstackJarvisHost.start() -> None`
- `FullstackJarvisHost.stop() -> None`
- `build_runtime() -> JarvisRuntime`
- `embedded_path(relative: str) -> Path`
- `JarvisVoiceBridge.start() -> None`
- `JarvisVoiceBridge.stop() -> None`
- `JarvisVoiceBridge.handle_transcript(text: str) -> None`

- [ ] **Step 1: Add failing tests that reject the obsolete Tk launcher**
- [ ] **Step 2: Add failing lifecycle tests for the fullstack host**
- [ ] **Step 3: Implement native visualizer hosting with embedded upstream assets**
- [ ] **Step 4: Connect upstream voice to the existing guarded Jarvis brain**
- [ ] **Step 5: Integrate optional hand-control presentation and explicit activation**
- [ ] **Step 6: Remove the obsolete compact-window fallback from packaged runtime paths**
- [ ] **Step 7: Run focused host/asset/voice tests**
- [ ] **Step 8: Run complete regression tests**
- [ ] **Step 9: Commit the fullstack host**

### Task 8: Build a deterministic, pinned single-EXE distribution

**Files:**
- Create: `scripts/fetch-fullstack-components.py`
- Modify: `.github/workflows/jarvis-release-gate.yml`
- Modify: Windows packaging files
- Create: `scripts/verify_jarvis_exe.py`
- Test: `tests/test_fullstack_components.py`, `tests/test_release_asset_contract.py`

**Interfaces:**
- `fetch_components(destination: Path) -> dict[str, str]`
- `verify_exe(path: Path) -> None`

- [ ] **Step 1: Lock pinned upstream component revisions**
- [ ] **Step 2: Write failing component-manifest tests**
- [ ] **Step 3: Implement safe pinned acquisition and path validation**
- [ ] **Step 4: Add the embedded vendor tree to PyInstaller build inputs**
- [ ] **Step 5: Add voice/audio hidden-import and data collection rules**
- [ ] **Step 6: Write failing release-asset tests**
- [ ] **Step 7: Implement one-file/windowed EXE verification**
- [ ] **Step 8: Run packaging tests and source compilation checks**
- [ ] **Step 9: Commit the distribution system**

### Task 9: Make startup, auto-update, and Windows lifecycle production-safe

**Files:**
- Modify: launcher/update/startup modules mapped by Task 1
- Test: startup/update/lifecycle regression tests

**Interfaces:**
- Startup remains invisible to normal users, uses no persistent PowerShell console, updates only clean repositories, and restarts safely after a verified update.

- [ ] **Step 1: Write failing tests for update-loop, singleton, and startup semantics**
- [ ] **Step 2: Port and reconcile the verified updater behavior**
- [ ] **Step 3: Verify normal operation creates no visible PowerShell window**
- [ ] **Step 4: Run lifecycle tests**
- [ ] **Step 5: Commit the lifecycle subsystem**

### Task 10: Create the complete release gate and verify the migrated repository

**Files:**
- Modify: `.github/workflows/jarvis-release-gate.yml`
- Modify: relevant CI workflows
- Test: all repository tests plus Windows packaged checks

**Interfaces:**
- Release gate verifies source tests, imports, dependency consistency, embedded Fullstack assets, packaged process startup, GUI path, release asset type/name, and extracted-bundle reruns.

- [ ] **Step 1: Add the obsolete-launcher regression gate to CI**
- [ ] **Step 2: Run backend/source tests**
- [ ] **Step 3: Run packaging and Windows verification**
- [ ] **Step 4: Inspect every failed step rather than rerunning blindly**
- [ ] **Step 5: Fix failures and rerun affected gates**
- [ ] **Step 6: Verify the final artifact is a direct `Jarvis.exe` distribution**
- [ ] **Step 7: Verify no Jarvis-only repository dependency remains**
- [ ] **Step 8: Commit final release-gate changes**

### Task 11: Final migration reconciliation and post-merge validation

**Files:**
- Modify: documentation and release metadata as needed
- Test: complete CI and packaged Windows validation

- [ ] **Step 1: Compare migrated destination against the Task 1 inventory**
- [ ] **Step 2: Search for obsolete 640x118/Tk launcher references**
- [ ] **Step 3: Search for cross-repository runtime dependencies on `dragonballls/Jarvis`**
- [ ] **Step 4: Search for secrets, tokens, and machine-local paths**
- [ ] **Step 5: Run all workflows on the migration head**
- [ ] **Step 6: Merge only after all required checks pass**
- [ ] **Step 7: Verify `main` and final Windows artifact from the merged commit**
- [ ] **Step 8: Record final verification evidence**
