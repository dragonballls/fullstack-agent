# Jarvis Phone & Device Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable multi-phone device subsystem for real Android devices, with Phone Link as an adapter, shared hand/computer input, and guarded automation.

**Architecture:** Keep provider-neutral device contracts under `quality_of_life/devices/`. Map device operations into the existing capability catalog/policy. Add a Windows/Phone Link adapter interface without requiring Phone Link or a live phone in CI; fake providers provide deterministic integration tests.

**Tech Stack:** Python 3.11–3.13, dataclasses, typing Protocols, unittest, existing quality-of-life capability/permission/scheduler infrastructure.

**Spec:** `docs/superpowers/specs/2026-09-15-jarvis-phone-devices-design.md`

## Global Constraints
- No Android emulator dependency.
- Real-phone behavior is provider-capability-driven and must fail explicitly when unsupported.
- Phone mutations are deny-by-default through the existing capability policy and confirmation gates.
- CI must remain free of live-device dependencies.
- Existing computer/hand control remains the common input path.
- Production `main` is not modified by this implementation branch.

---

### Task 1: Device domain models

**Files:**
- Create: `quality_of_life/devices/__init__.py`
- Create: `quality_of_life/devices/models.py`
- Test: `tests/test_phone_devices_models.py`

### Task 2: Provider protocol and fake provider

**Files:**
- Create: `quality_of_life/devices/provider.py`
- Create: `quality_of_life/devices/fake_provider.py`
- Test: `tests/test_phone_device_provider.py`

### Task 3: Device registry and active-device context

**Files:**
- Create: `quality_of_life/devices/registry.py`
- Test: `tests/test_phone_device_registry.py`

### Task 4: Permission/capability integration

**Files:**
- Modify: `quality_of_life/permissions.py`
- Modify: `quality_of_life/capabilities.py`
- Create: `tests/test_phone_device_permissions.py`

### Task 5: Device control facade and automation hooks

**Files:**
- Create: `quality_of_life/devices/facade.py`
- Create: `quality_of_life/devices/automation.py`
- Test: `tests/test_phone_device_facade.py`
- Test: `tests/test_phone_device_automation.py`

### Task 6: Hand-control and computer-control routing

**Files:**
- Modify: `quality_of_life/hand_control_runtime.py`
- Modify: `quality_of_life/computer_use.py`
- Create: `quality_of_life/devices/input_adapter.py`
- Test: `tests/test_phone_device_input.py`

### Task 7: Phone Link adapter boundary

**Files:**
- Create: `quality_of_life/devices/phone_link.py`
- Create: `tests/test_phone_link_adapter.py`
- Modify: `quality_of_life/devices/__init__.py`

### Task 8: Runtime wiring and documentation

**Files:**
- Modify: `quality_of_life/runtime.py`
- Modify: `quality_of_life/router.py`
- Modify: `quality_of_life/README.md`
- Create: `quality_of_life/README_DEVICES.md`
- Test: `tests/test_phone_device_integration.py`

### Task 9: Full regression, packaging, and safety gates

- Run all phone-device tests together.
- Run the complete unittest suite.
- Run every existing CI workflow on the test branch.
- Inspect every job and artifact, including the Android companion build.
- Fix only demonstrated failures and rerun the affected gate plus the full suite.

### Task 10: Final test-copy review

- Compare changed files against the test branch base and verify there are no unrelated changes.
- Confirm no production `main` ref changed during implementation.
- Confirm all declared acceptance criteria in the spec have test coverage or an explicit platform limitation.
- Promote only after all gates are green.
