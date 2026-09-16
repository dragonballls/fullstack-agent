# Jarvis Background-Efficient Mode Design

**Goal:** Allow Jarvis desktop hosts to hide/minimize the UI into a low-overhead background state while keeping voice commands and explicitly enabled hand control available.

## Behavior

- `minimize -> background` is a lifecycle state transition, not process termination.
- In background state, UI rendering and other registered high-cost presentation work must be suspended by the host.
- Core command routing remains available.
- A running voice listener remains available.
- A running hand-control session remains available; no gesture processing is disabled solely because the UI is minimized.
- Hand tracking remains opt-in and stops when hand control is stopped.
- `restore -> foreground` resumes suspended presentation work without recreating the core runtime.
- `quit -> stopped` remains a true shutdown and must stop background-capable services.

## Resource policy

The source layer cannot force a particular desktop framework to consume zero CPU/RAM. Instead it defines an explicit lifecycle contract and callback registry so the desktop host can suspend expensive UI work while retaining only the services needed for interaction.

A component is registered as either:

- `always`: remain active in background (voice, task routing, active hand control, safety watchdogs).
- `foreground_only`: suspend in background (UI rendering, animations, nonessential polling).

Transitions are idempotent and thread-safe.

## Safety

- Background mode never implicitly enables camera, microphone, mouse control, or other capabilities.
- Stopping background mode must release registered background resources cleanly.
- Hand-control watchdog behavior is unchanged.
- Lifecycle callbacks are best-effort and failures are isolated so one optional component cannot crash Jarvis core.

## Verification

Headless tests cover transition state, callback ordering, idempotency, failure isolation, and preservation of active voice/hand-control services. The existing six-leg Windows/Ubuntu Python matrix remains authoritative for repository-level regression coverage.
