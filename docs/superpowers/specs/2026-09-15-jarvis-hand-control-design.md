# Jarvis Hand Control Design

## Goal
Add an optional webcam hand-control subsystem that lets Jarvis translate reliable hand gestures into guarded mouse/keyboard actions without making camera access a dependency of the core assistant.

## Architecture
A local tracking adapter emits normalized samples; a deterministic interpreter applies confidence, debounce, dwell, and cooldown gates; a bridge maps only approved gesture events into the existing guarded computer-control capability path; a lifecycle manager keeps camera/tracker failures isolated.

The first release supports cursor movement, left click, drag, scroll, pause/resume, and emergency stop. Right click remains configurable rather than relying on an ambiguous default gesture. The camera/tracker is optional and imports lazily so core Jarvis still starts without a webcam or optional packages.

## Reliability and safety
- Hand control is disabled until explicitly enabled.
- Missing camera, denied permission, unsupported tracker, or disconnected device is a non-fatal degraded state.
- Gesture actions require a confidence threshold and temporal debounce/cooldown.
- Pause/resume and emergency-stop gestures suppress further generated computer input immediately.
- Gesture events cannot bypass existing capability, permission, confirmation, or policy gates.
- No arbitrary shell execution or unbounded keyboard injection.
- Existing voice, browser, location-memory, self-coding, and startup behavior remain unchanged.

## Acceptance criteria
- Hand-control unit/integration tests are deterministic and headless.
- The core QOL package remains importable with no optional camera dependency installed.
- The new runtime can report unavailable/disabled states without raising through Jarvis startup.
- Existing repository tests and Windows/Linux CI remain green.
- User documentation explains camera permissions, supported gestures, enable/disable behavior, and degraded mode.
