"""Explicit, user-controlled observation state for Neural JARVIS."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time


@dataclass(frozen=True)
class ObservationState:
    enabled: bool = False
    focus: str = "auto"
    reason: str = ""
    started_at: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "focus": self.focus,
            "reason": self.reason,
            "started_at": self.started_at,
        }


class NeuralObservationController:
    ALLOWED_FOCUS = frozenset({
        "auto", "network", "earth", "activity", "coding", "browser", "system",
    })

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = ObservationState()

    def start(self, focus: str = "auto", reason: str = "") -> dict[str, object]:
        focus = str(focus).strip().lower() or "auto"
        if focus not in self.ALLOWED_FOCUS:
            raise ValueError("unsupported observation focus")
        with self._lock:
            self._state = ObservationState(True, focus, str(reason)[:300], time.time())
            return self._state.as_dict()

    def stop(self) -> dict[str, object]:
        with self._lock:
            self._state = ObservationState()
            return self._state.as_dict()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self._state.as_dict()
