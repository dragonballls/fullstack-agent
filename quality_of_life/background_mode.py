"""Lifecycle contract for low-overhead Jarvis background operation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading
from typing import Callable


class BackgroundMode(str, Enum):
    """Effective presentation lifecycle state."""

    FOREGROUND = "foreground"
    BACKGROUND = "background"


@dataclass(frozen=True)
class BackgroundComponent:
    """A component whose work is either always-on or foreground-only."""

    name: str
    policy: str
    on_background: Callable[[], None] | None = None
    on_foreground: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        if self.policy not in {"always", "foreground_only"}:
            raise ValueError("policy must be 'always' or 'foreground_only'")


class BackgroundModeController:
    """Thread-safe, failure-isolated lifecycle controller for desktop hosts.

    The controller never starts or stops hardware capabilities itself.  Hosts
    register expensive presentation components as ``foreground_only`` and
    leave voice, task routing, active hand control, and safety watchdogs
    unregistered (or registered as ``always``).  Entering background therefore
    suspends only the presentation work selected by the host.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = BackgroundMode.FOREGROUND
        self._components: dict[str, BackgroundComponent] = {}
        self._degraded: set[str] = set()

    @property
    def state(self) -> BackgroundMode:
        with self._lock:
            return self._state

    def register(self, component: BackgroundComponent) -> None:
        """Register or replace one named lifecycle component."""
        with self._lock:
            self._components[component.name] = component
            self._degraded.discard(component.name)
            state = self._state

        if state is BackgroundMode.BACKGROUND and component.policy == "foreground_only":
            self._invoke(component, "background")

    def unregister(self, name: str) -> None:
        """Remove a lifecycle component without changing system state."""
        with self._lock:
            self._components.pop(name, None)
            self._degraded.discard(name)

    def enter_background(self) -> bool:
        """Transition to background and suspend foreground-only components."""
        with self._lock:
            if self._state is BackgroundMode.BACKGROUND:
                return False
            self._state = BackgroundMode.BACKGROUND
            components = tuple(self._components.values())
            self._degraded.clear()

        for component in components:
            if component.policy == "foreground_only":
                self._invoke(component, "background")
        return True

    def enter_foreground(self) -> bool:
        """Transition to foreground and resume foreground-only components."""
        with self._lock:
            if self._state is BackgroundMode.FOREGROUND:
                return False
            self._state = BackgroundMode.FOREGROUND
            components = tuple(self._components.values())
            self._degraded.clear()

        for component in components:
            if component.policy == "foreground_only":
                self._invoke(component, "foreground")
        return True

    def status(self) -> dict[str, object]:
        """Return a serializable lifecycle snapshot for a UI or health endpoint."""
        with self._lock:
            return {
                "state": self._state.value,
                "registered": sorted(self._components),
                "degraded": sorted(self._degraded),
            }

    def _invoke(self, component: BackgroundComponent, phase: str) -> None:
        callback = component.on_background if phase == "background" else component.on_foreground
        if callback is None:
            return
        try:
            callback()
        except Exception:
            with self._lock:
                self._degraded.add(component.name)
