"""Small background-job manager for proactive maintenance tasks."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class JobHandle:
    name: str
    thread: threading.Thread
    cancel: threading.Event


class BackgroundJobs:
    """Run bounded jobs in daemon threads with explicit cancellation."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobHandle] = {}
        self._lock = threading.Lock()

    def start(self, name: str, task: Callable[[threading.Event], None]) -> JobHandle:
        if not name.strip():
            raise ValueError("job name is required")
        cancel = threading.Event()
        if name in self._jobs and self._jobs[name].thread.is_alive():
            raise RuntimeError(f"job already running: {name}")

        def runner() -> None:
            try:
                task(cancel)
            finally:
                with self._lock:
                    self._jobs.pop(name, None)

        thread = threading.Thread(target=runner, name=f"fullstack-agent-{name}", daemon=True)
        handle = JobHandle(name=name, thread=thread, cancel=cancel)
        with self._lock:
            self._jobs[name] = handle
        thread.start()
        return handle

    def cancel(self, name: str) -> bool:
        with self._lock:
            handle = self._jobs.get(name)
        if handle is None:
            return False
        handle.cancel.set()
        return True

    def active(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(name for name, handle in self._jobs.items() if handle.thread.is_alive()))
