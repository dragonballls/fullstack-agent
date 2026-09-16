# Jarvis background-efficient mode

Jarvis supports a lifecycle contract for desktop hosts that want **minimize** to mean "keep Jarvis alive, but stop unnecessary presentation work".

## Lifecycle

- **Foreground:** full desktop presentation is active.
- **Background:** the desktop host should hide/suspend UI rendering, animations, and nonessential polling. Voice/task routing and any explicitly active hand-control service remain available.
- **Quit:** the host performs a real shutdown; background mode is not a substitute for quitting.

Use `BackgroundModeController` from `quality_of_life.background_mode`:

```python
from quality_of_life import BackgroundModeController

background = BackgroundModeController()

# Register expensive presentation work.
background.register(
    BackgroundComponent(
        "desktop-ui",
        "foreground_only",
        on_background=ui.pause_rendering,
        on_foreground=ui.resume_rendering,
    )
)

# Minimize/restore hooks call these methods.
background.enter_background()
background.enter_foreground()
```

`always` components are deliberately not paused by the controller. A voice listener, task router, hand-control watchdog, or other service that must remain responsive can therefore stay registered with an `always` policy. Hardware capabilities remain independently gated and are never enabled merely because Jarvis is minimized.

## Resource expectations

Background mode is designed for **near-idle overhead**, not literal zero resource use. Keeping Jarvis available for voice input, active hand tracking, and immediate commands necessarily consumes some CPU/RAM. The desktop host gets the largest safe reduction by suspending the UI renderer and all nonessential polling while preserving only interaction-critical services.

This repository contains the integration/lifecycle layer, not the native desktop window implementation. The host application must connect its minimize and restore events to the lifecycle controller.
