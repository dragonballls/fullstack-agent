# OmniRoute Latency Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce Jarvis response latency while preserving or improving multi-AI collaboration, routing quality, deterministic safety, and verification behavior.

**Architecture:** Keep the fast path for simple requests. For complex requests, run independent specialists concurrently, avoid unnecessary planning calls through deterministic dispatch, add latency-aware provider health/fallback, and permit bounded early synthesis only after minimum evidence is available. Preserve all permission, confirmation, and deterministic execution gates.

**Tech Stack:** Python 3, existing unittest/pytest-compatible tests, `concurrent.futures`, OmniRoute-compatible HTTP API, GitHub Actions.

**Spec:** Approved chat design for adaptive low-latency OmniRoute orchestration.

## Global Constraints

- Never bypass deterministic capability and permission controls.
- Never execute model-provided shell/PowerShell/arbitrary executable paths.
- Preserve public interfaces unless a backward-compatible extension is required.
- Keep cloud-only routing; no silent local-model fallback.
- Preserve bounded concurrency with a hard safety cap.
- Do not claim speed/intelligence gains without measured evidence.
- All relevant tests and post-change GitHub Actions checks must pass.

---

### Task 1: Lock down latency-sensitive behavior with tests

**Files:** existing router/orchestrator test modules discovered in repository.

- [ ] Add a failing test showing deterministic intents can bypass model planning.
- [ ] Confirm the test fails against current behavior.
- [ ] Add overlap and worker-cap tests for parallel specialists.
- [ ] Add provider-failure/fallback latency tests.
- [ ] Record baseline mock timings and call counts.

### Task 2: Optimize deterministic dispatch and fast path

**Files:** `quality_of_life/agent_orchestrator.py`, `quality_of_life/orchestration.py` only if needed.

- [ ] Implement deterministic-intent short-circuiting when the existing runtime already completely expresses the request.
- [ ] Preserve typed-plan fallback for unsupported/general requests.
- [ ] Preserve all confirmation and safety semantics.
- [ ] Run targeted and broader QOL tests.

### Task 3: Make provider routing latency-aware

**Files:** `quality_of_life/router.py` and router tests.

- [ ] Add tests for latency/health behavior.
- [ ] Add lightweight in-process provider health/latency memory with no secrets.
- [ ] Prefer healthy/fast targets while retaining deterministic behavior when metrics are absent.
- [ ] Bound degraded-provider impact with short interactive fallback behavior.
- [ ] Run router/concurrency regressions.

### Task 4: Reduce unnecessary waiting in multi-AI synthesis

**Files:** `quality_of_life/router.py`, `quality_of_life/agent_orchestrator.py`, tests.

- [ ] Add tests for partial specialist completion and evidence thresholds.
- [ ] Implement conservative early synthesis only when enough required evidence is present.
- [ ] Ensure missing/failed specialist evidence is never represented as completed findings.
- [ ] Run all multi-AI tests.

### Task 5: Benchmark and protect performance

**Files:** create or extend `tests/test_omniroute_performance.py`; docs as needed.

- [ ] Use deterministic mock providers with controlled delays.
- [ ] Benchmark simple, deterministic-tool, complex multi-AI, and failure scenarios.
- [ ] Assert no regression beyond a small tolerance.
- [ ] Report measured latency/call-count changes and separate these from model-quality claims.

### Task 6: Full regression and delivery

- [ ] Run the complete repository suite and CI-equivalent checks.
- [ ] Review safety, permissions, confirmation, secret handling, and cloud-only routing.
- [ ] Commit to the feature branch.
- [ ] Open PR to `main`.
- [ ] Fix every CI failure before merge.
- [ ] After merge, verify the exact `main` commit's post-merge checks are green before claiming completion.
