"""Opt-in read-only background health monitoring for Windows maintenance."""

from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import time
from typing import Any


@dataclass(frozen=True)
class HealthSnapshot:
    """One read-only maintenance snapshot."""

    collected_at: float
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"collected_at": self.collected_at, "message": self.message}


class HealthMonitor:
    """Periodic diagnostic monitor that never mutates the machine by itself."""

    def __init__(self, facade: Any, interval_seconds: int = 300, enabled: bool = False) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.facade = facade
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest: HealthSnapshot | None = None
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls, facade: Any | None = None) -> "HealthMonitor":
        enabled = os.environ.get("JARVIS_HEALTH_MONITOR", "0").strip().lower() in {"1", "true", "yes", "on"}
        try:
            interval = max(15, int(os.environ.get("JARVIS_HEALTH_INTERVAL_SECONDS", "300")))
        except ValueError:
            interval = 300
        if facade is None:
            from windows_maintenance import MaintenanceFacade
            facade = MaintenanceFacade()
        return cls(facade, interval_seconds=interval, enabled=enabled)

    def snapshot(self) -> dict[str, Any]:
        """Collect one diagnostic snapshot without invoking a mutating operation."""
        response = self.facade.diagnose()
        message = str(getattr(response, "message", response))
        snapshot = HealthSnapshot(time.time(), message)
        with self._lock:
            self._latest = snapshot
        return snapshot.as_dict()

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            return self._latest.as_dict() if self._latest else None

    def recommended_actions(self) -> tuple[str, ...]:
        """Return advisory text from the latest diagnostic without changing system state."""
        current = self.snapshot()
        message = current["message"].strip()
        if not message or message.lower() == "health looks normal":
            return ()
        return (message,)

    def start(self) -> bool:
        """Start the monitor thread only when explicitly enabled."""
        if not self.enabled or self._thread is not None and self._thread.is_alive():
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="jarvis-health-monitor", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=min(self.interval_seconds, 5))
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.snapshot()
            except Exception:
                pass
            self._stop_event.wait(self.interval_seconds)
