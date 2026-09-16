"""Always-on/background-efficient service coordinator for Jarvis desktop hosts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .background_mode import BackgroundComponent, BackgroundModeController
from .hand_control_runtime import HandControlRuntime
from .voice_listener import LocalWakeWordListener, WakeEvent


class JarvisBackgroundRuntime:
    """Coordinate low-overhead background services without keeping a UI hot.

    The desktop host owns the actual window. It should provide the optional UI
    callbacks and call ``minimize``/``restore`` from its window lifecycle. Voice
    listening remains alive for the application's lifetime; active hand control
    is independent of presentation state and remains alive while minimized.
    """

    def __init__(
        self,
        *,
        on_wake: Callable[[WakeEvent], None] | None = None,
        on_ui_background: Callable[[], None] | None = None,
        on_ui_foreground: Callable[[], None] | None = None,
        voice_listener: LocalWakeWordListener | None = None,
        hand_control: HandControlRuntime | None = None,
        lifecycle: BackgroundModeController | None = None,
    ) -> None:
        self.lifecycle = lifecycle or BackgroundModeController()
        self.voice_listener = voice_listener or LocalWakeWordListener(on_wake=on_wake)
        self.hand_control = hand_control or HandControlRuntime(open_browser=True)
        self.lifecycle.register(
            BackgroundComponent(
                "desktop-ui",
                "foreground_only",
                on_background=on_ui_background,
                on_foreground=on_ui_foreground,
            )
        )

    def start(self) -> None:
        """Start the always-on voice service."""
        self.voice_listener.start()

    def stop(self) -> None:
        """Stop background services and disable active hand control."""
        try:
            self.hand_control.stop()
        finally:
            self.voice_listener.stop()

    def minimize(self) -> bool:
        """Enter low-overhead presentation mode without stopping services."""
        return self.lifecycle.enter_background()

    def restore(self) -> bool:
        """Restore the foreground presentation mode."""
        return self.lifecycle.enter_foreground()

    def status(self) -> dict[str, Any]:
        """Return one combined lifecycle/service snapshot."""
        return {
            "lifecycle": self.lifecycle.status(),
            "voice": {
                "running": self.voice_listener.running,
                "last_error": self.voice_listener.last_error,
            },
            "hand_control": self.hand_control.status(),
        }
