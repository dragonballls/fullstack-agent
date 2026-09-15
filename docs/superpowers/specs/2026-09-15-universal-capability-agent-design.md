# Universal Capability Agent Design

## Goal

Extend `fullstack-agent` into a general-purpose, capability-driven computer agent that can interpret natural-language requests, select the minimum safe set of tools, execute structured operations, verify outcomes, and fail clearly when a requested capability is unavailable.

## Architecture

The existing `quality_of_life/` policy and orchestrator remain the authoritative execution boundary. A new capability catalog provides stable metadata and structured operations for filesystem, applications/software, browser discovery/control, processes/services, networking, system settings, scheduling/notifications, and existing Windows maintenance; it does not expose arbitrary shell execution to model-generated text.

Natural-language planning stays separate from execution: the model may propose typed tool calls, but deterministic validation, permission checks, confirmation gates, input validation, and result verification happen before and after every mutating operation. Existing self-coding, cloud routing, God’s Eye, voice, and maintenance components remain independently testable and are reused through adapters rather than duplicated.

## Capability families

1. **Computer:** mouse, keyboard, screen, clipboard, windows, application launch.
2. **Browser:** detect installed browsers, select by normalized name/alias, launch a requested browser, open structured URLs, and use the existing automation adapter for supported browser operations.
3. **Files:** search, inspect metadata, read/write text, create directories, copy/move/rename, and guarded deletion within explicit paths.
4. **Applications:** enumerate installed applications, inspect versions/uninstall metadata, launch supported applications, and uninstall only through a verified registered uninstaller with explicit confirmation.
5. **Processes/services:** inspect processes and services, stop/restart only through guarded structured operations, protect critical/system/agent processes, and verify state changes.
6. **Windows maintenance:** retain diagnostics, cleanup, startup management, system-file diagnostics, and confirmed repairs already implemented.
7. **Networking:** inspect adapters/connectivity/DNS/proxy state and perform only explicitly permitted repairs through typed operations.
8. **System settings:** inspect and modify supported user-level settings through structured APIs; privileged/system-wide changes require confirmation and appropriate OS privileges.
9. **Scheduling/background:** create, inspect, cancel, and verify bounded background jobs using the existing cancellation model; expose scheduling only through explicit typed actions.
10. **Development/repositories:** preserve self-coding isolation, repository read/write policy, verification, rollback, and cloud-model routing.
11. **Location/vision/voice:** preserve God’s Eye, screen/vision context, and configured cloud voice as optional capabilities.

## Safety and failure rules

- Deny-by-default remains the baseline for capabilities.
- Destructive or externally consequential actions require confirmation unless a caller explicitly supplies an already-authorized confirmation token through the existing policy path.
- Model text can never become an arbitrary PowerShell, CMD, Python, registry script, or shell pipeline.
- Paths are normalized and constrained; destructive filesystem operations require explicit targets and reject ambiguous roots/system locations.
- Application uninstall requires exact application identity matching and post-action verification.
- Browser launches accept a known browser identifier plus a validated HTTP(S) URL, not arbitrary process arguments.
- Protected processes, services, system components, and security software are denied by default.
- Failures are isolated to the requested capability and returned as structured diagnostics.
- Optional dependencies remain optional and must not break package import or unrelated capabilities.
- Secrets are never placed in prompts, audit records, tracked files, or exception messages.

## Verification

Every capability family receives focused unit tests for normal operation, invalid input, permission denial, confirmation gating, and failure handling. Integration tests verify that the catalog, runtime dispatch, and existing QOL/self-coding components coexist. GitHub Actions must remain green on the supported Python matrix and integration workflow. Hosted CI cannot certify physical Windows behavior, so actual desktop/browser/device behavior remains a separate end-user validation gate.

## Scope boundary

“Every task” means every task supported by the operating system, connected services, installed applications, and implemented adapters that the agent has permission to use. The system must never claim capabilities it cannot actually execute or verify.
