# Jarvis Background-Efficient Mode Design

**Status:** Implemented in `feature/jarvis-background-efficient-mode`

## Purpose

When the Jarvis desktop host is minimized, the visible presentation layer should stop unnecessary render/poll work while essential interaction services remain alive. This is a resource-reduction mode, not a process suspension and not a promise of zero CPU or RAM.

## Required behavior

1. **Minimize:** enter `background` presentation state.
2. **Foreground-only work:** the host may suspend expensive UI rendering, animations, timers, and polling by registering them as `foreground_only` components.
3. **Voice:** the local wake listener remains alive and owns exactly one listener thread per process.
4. **Hand control:** an explicitly active hand-control runtime is not stopped by minimize. It remains independently controlled and can still be stopped through its existing safety controls.
5. **Restore:** return to `foreground` and resume registered foreground-only components.
6. **Quit:** stop background services and active hand control through the host's normal shutdown path.
7. **Failure isolation:** a failed foreground callback is recorded as degraded and must not stop other lifecycle components.
8. **Optional dependencies:** missing voice dependencies fail closed and do not crash Jarvis core.

## Repository boundary

`dragonballls/fullstack-agent` is the Jarvis integration/source layer. It does not contain the final native desktop shell/window implementation. `JarvisBackgroundRuntime` therefore provides explicit host callbacks rather than inventing a shell-specific event loop. A desktop host should connect window minimize/restore/close events to `minimize()`, `restore()`, and `stop()`.

## Resource policy

Background mode removes presentation work selected by the host. It cannot make active voice recognition, network request handling, or hand tracking consume zero resources. Hand-control camera/tracking work is active only when hand control itself is enabled; when disabled, the camera tracker is not required by this lifecycle layer.

## Safety

Minimize never grants new capabilities. Voice wake remains locally gated; computer/browser/system mutations continue through the existing policy and confirmation mechanisms. Hand control retains its existing disabled-by-default activation, tracking-loss watchdog, emergency pause, and explicit stop behavior.

## Verification

Unit tests cover idempotent minimize/restore transitions, failure isolation, voice listener start/stop lifecycle, and preservation of an active hand-control service during minimize. The repository's existing Ubuntu/Windows and Python 3.11–3.13 CI matrix is the release gate for the source layer.
