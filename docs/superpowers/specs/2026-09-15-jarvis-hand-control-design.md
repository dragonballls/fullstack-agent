# Jarvis Hand Control Design

## Goal
Add an optional webcam hand-control subsystem that lets Jarvis translate reliable hand gestures into guarded mouse/keyboard actions without making camera access a dependency of the core assistant.

## Existing foundation
The repository documents `barehands` as a webcam hand-tracking component using Google MediaPipe and Chrome. The new Jarvis integration should reuse the concept and gesture vocabulary while keeping Jarvis's control path authoritative.

## Architecture
1. **Tracker adapter:** a local camera/tracking adapter produces normalized hand landmarks/gesture candidates. The first implementation may consume the existing barehands-compatible tracker protocol rather than duplicating a second tracker implementation.
2. **Gesture interpreter:** converts landmarks/events into a small explicit command set: cursor move, left click, right click, drag, scroll, pause/resume, and emergency stop. It applies confidence, debounce, dwell, and cooldown gates so noisy frames do not create repeated input.
3. **Computer-control bridge:** maps only approved gesture commands to the existing quality-of-life computer capability layer. No arbitrary shell, script, or unbounded keyboard injection is introduced.
4. **Lifecycle manager:** starts/stops camera tracking independently, reports unavailable camera/dependency states without crashing Jarvis, and provides a hard disable path.
5. **Configuration:** hand control is opt-in and disabled by default until enabled. Configuration remains outside code and secrets.

## Safety / reliability requirements
- Core Jarvis must still start when a webcam is missing, denied, disconnected, or unsupported.
- Camera permission failure is a normal degraded state, not a fatal error.
- Gesture actions require confidence and debouncing; accidental repeated clicks must be prevented.
- A pause gesture and explicit software disable must stop gesture-generated input immediately.
- Emergency stop must take precedence over other gesture actions.
- Existing computer-use policy/confirmation gates remain authoritative for mutating actions.
- The tracker must not bypass the existing capability/permission layer.
- Tests must cover tracker failure, noisy input, cooldowns, pause/resume, and correct action routing.
- No changes to existing self-coding, voice, browser, location-memory, or core startup behavior unless strictly required for integration.

## First stable gesture set
- Point/index hand position: cursor movement.
- Quick pinch: left click.
- Secondary configurable pinch/gesture: right click.
- Pinch + movement while held: drag.
- Two-finger vertical movement: scroll.
- Open-palm hold: pause/resume hand control.
- Fist/emergency gesture: immediate hand-input stop.

## Acceptance criteria
- Unit and integration tests pass for the new subsystem.
- Existing repository test suites remain green.
- Windows and Linux CI paths remain green where the repository already tests them.
- Optional camera dependencies cannot prevent normal Jarvis startup.
- Documentation explains setup, permissions, supported gestures, disable controls, and degraded-mode behavior.
