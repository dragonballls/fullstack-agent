# General Goal-Based Computer Use Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Jarvis translate natural-language PC goals into bounded observe/act/verify loops using existing guarded capabilities.

**Architecture:** Add a small computer-use coordinator that accepts a goal, observes available computer context, consumes a structured action plan, executes only allowlisted computer actions through existing capability boundaries, then re-observes after actions. Keep model planning separate from deterministic execution and never permit shell/PowerShell/arbitrary executable actions.

**Tech Stack:** Python 3, existing quality_of_life runtime, unittest, existing screen/computer/browser/application abstractions.

**Spec:** Approved goal-based computer-control design from chat.

## Global Constraints

- Preserve existing capability permissions and confirmation gates.
- No arbitrary shell, PowerShell, scripting, or executable-path actions from model output.
- Keep actions bounded by step count and per-action argument limits.
- Preserve existing public interfaces unless backward-compatible additions are required.
- Use existing computer/screen/application/browser adapters rather than duplicating execution logic.
- Do not claim universal application control where no adapter or observable interface exists.
- All relevant tests and exact-head CI checks must pass before merge.

---

### Task 1: Define the computer-use contract with failing tests

**Files:**
- Create: `tests/test_computer_use_goal.py`

- [ ] Add tests for structured allowlisted actions, observe-before/after behavior, unknown-action rejection, and maximum step bounds.
- [ ] Run the targeted tests and confirm they fail because the new module does not yet exist.

### Task 2: Implement the bounded goal-action coordinator

**Files:**
- Create: `quality_of_life/computer_use.py`
- Test: `tests/test_computer_use_goal.py`

- [ ] Implement typed `ComputerUseAction` and `ComputerUseResult` contracts.
- [ ] Implement `ComputerUseAgent.run()` with observe → validate → execute → observe.
- [ ] Support only safe primitives: click, move, scroll, type_text, hotkey, wait, and open_app through an application resolver.
- [ ] Enforce step limits and argument validation.
- [ ] Keep execution delegated to the injected computer/runtime adapter.

### Task 3: Integrate the coordinator with Jarvis runtime

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/capabilities.py`
- Modify: `quality_of_life/agent_orchestrator.py`
- Modify: `quality_of_life/intents.py` only if required for backwards-compatible goal routing.

- [ ] Register a `computer.goal` capability that remains permission-gated.
- [ ] Route ambiguous/general PC goals to the coordinator while preserving exact deterministic intents as the fast path.
- [ ] Keep confirmations required for computer mutations.
- [ ] Ensure the model provides structured action plans, never raw commands.

### Task 4: Add visual context and verification hooks

**Files:**
- Modify: `quality_of_life/computer_use.py`
- Test: `tests/test_computer_use_goal.py`

- [ ] Use the existing screen capture interface as the observation source where available.
- [ ] Add an observation summary hook that can be supplied to a vision-capable planner without forcing image handling into the core executor.
- [ ] Require post-action observation for completion unless the configured action is explicitly non-observable.
- [ ] Surface incomplete verification rather than claiming success.

### Task 5: Regression and delivery

- [ ] Run targeted new tests.
- [ ] Run complete QOL, integration, and self-coding suites.
- [ ] Review capability/permission and secret-handling boundaries.
- [ ] Open PR to `main`.
- [ ] Fix every CI failure before merge.
- [ ] Verify the exact merged `main` commit is green before claiming completion.
