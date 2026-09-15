# Jarvis Readiness Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe first-run readiness gate that makes Jarvis operationally self-diagnosing without pretending optional credentials, permissions, or hardware are configured.

**Architecture:** Introduce a small pure-Python readiness module that checks installed/runtime prerequisites and configuration presence, returns structured pass/warn/fail results, and exposes one aggregate report. Keep checks side-effect-light: never print or persist secrets, never request permissions automatically, and never modify existing capability policy. Add an executable readiness entry point and regression tests; use the existing CI matrix as the final verification gate.

**Tech Stack:** Python 3.11-3.13, stdlib `unittest`, existing `quality_of_life` modules, GitHub Actions.

**Spec:** Approved in chat: close the remaining setup/real-machine readiness gaps while preserving working subsystems and guarded permissions.

## Global Constraints

- Preserve deny-by-default capability policy and confirmation requirements.
- Cloud-only model routing; do not add or restore Ollama/local LLM dependencies.
- Never print, commit, or persist API keys/secrets.
- Readiness checks may report missing configuration, permissions, hardware, or optional dependencies but must not claim they are configured when they are not.
- Do not make existing memory, voice, face, hands, self-coding, or God’s Eye paths depend on the readiness gate.
- Existing regression and integration suites must remain green.

---

### Task 1: Readiness result model and pure checks

**Files:**
- Create: `quality_of_life/readiness.py`
- Test: `tests/test_readiness.py`

**Interfaces:**
- Produces `CheckStatus`, `ReadinessCheck`, `ReadinessReport`, and `check_readiness(...)`.
- Checks cover Python runtime, Git availability, cloud-provider environment variable presence (names only), ElevenLabs configuration presence, God’s Eye package availability, browser automation dependency availability, and self-coding CLI availability.

- [ ] **Step 1: Write failing unit tests** for missing/present environment configuration, dependency detection, and aggregate status.
- [ ] **Step 2: Run the focused tests and verify the expected failures.**
- [ ] **Step 3: Implement the minimal readiness models and checks.**
- [ ] **Step 4: Run the focused tests and verify they pass.**
- [ ] **Step 5: Refactor only while preserving green tests.**

### Task 2: Human-readable readiness command

**Files:**
- Modify: `quality_of_life/readiness.py`
- Create: `readiness.py`
- Test: `tests/test_readiness.py`

**Interfaces:**
- Produces `python readiness.py` CLI output with status labels and non-secret remediation hints.
- Exit code is non-zero only for required runtime failures; optional integrations are clearly labeled instead of blocking the base stack.

- [ ] **Step 1: Add failing CLI formatting/exit-code tests.**
- [ ] **Step 2: Run tests and confirm failure.**
- [ ] **Step 3: Implement CLI formatting and exit semantics.**
- [ ] **Step 4: Run focused tests and compile checks.**

### Task 3: Documentation and verification

**Files:**
- Modify: `README.md`
- Modify: `TROUBLESHOOTING.md`
- Test: existing `tests/` suite

- [ ] **Step 1: Document the readiness command and the meaning of required vs optional checks.**
- [ ] **Step 2: Run the complete unittest discovery suite.**
- [ ] **Step 3: Run `compileall` for `quality_of_life` and `tests`.**
- [ ] **Step 4: Push the branch and require all configured GitHub Actions checks to pass before merge.**
- [ ] **Step 5: Re-check the merged `main` commit and workflow conclusions before reporting final status.**
