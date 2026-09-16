# Jarvis Background-Efficient Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Jarvis's presentation layer low-overhead while preserving always-on voice wake listening and any explicitly active hand-control session.

**Architecture:** A thread-safe lifecycle controller marks presentation work as foreground-only. A background runtime keeps voice listening alive and treats hand control as an independent service, so minimizing changes presentation state without disabling user-authorized capabilities. The repository exposes this as a host integration contract because the actual native desktop shell is outside this source-layer repository.

**Tech Stack:** Python 3.11–3.13, unittest, threading, existing Jarvis quality-of-life runtime.

**Spec:** `docs/superpowers/specs/2026-09-16-jarvis-background-efficient-mode-design.md`

## Global Constraints

- Minimize must not stop voice wake listening.
- Minimize must not stop an active hand-control session.
- Foreground-only UI work may be suspended while minimized.
- Voice wake processing remains local; cloud requests occur only after wake handling.
- Hand control remains explicit and independently stoppable.
- Quit/stop must stop background services cleanly.
- Missing optional voice dependencies fail closed rather than taking down Jarvis core.
- CI must pass on Ubuntu and Windows with Python 3.11, 3.12, and 3.13.

---

### Task 1: Lifecycle controller
- [x] Implement `quality_of_life/background_mode.py` and lifecycle regression tests.

### Task 2: Voice lifecycle
- [x] Add idempotent start/stop lifecycle to `LocalWakeWordListener` with regression coverage.

### Task 3: Background service coordinator
- [x] Implement `JarvisBackgroundRuntime` and export it for desktop-host integration.
- [x] Verify minimize does not stop active hand control or voice.

### Task 4: Documentation and release verification
- [x] Add the design/spec and host integration documentation.
- [ ] Verify the full cross-platform release/test gate and merge only after green.
