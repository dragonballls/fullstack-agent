"""Bounded in-process scheduling built on the existing background job manager."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from .background import BackgroundJobs, JobHandle


@dataclass(frozen=True)
class ScheduledJob:
    name: str
    run_at: datetime
    handle: JobHandle


class Scheduler:
    def __init__(self, background: BackgroundJobs | None = None) -> None:
        self.background = background or BackgroundJobs()
        self._scheduled: dict[str, ScheduledJob] = {}
        self._lock = threading.Lock()

    def schedule_once(self, name: str, run_at: datetime, task: Callable[[threading.Event], None]) -> ScheduledJob:
        if not name.strip():
            raise ValueError("job name is required")
        if run_at.tzinfo is None:
            raise ValueError("run_at must be timezone-aware")
        now = datetime.now(timezone.utc)
        target = run_at.astimezone(timezone.utc)
        if target < now:
            raise ValueError("run_at must be in the future")
        if target > now + timedelta(days=365):
            raise ValueError("schedule is limited to one year")

        def delayed(cancel: threading.Event) -> None:
            remaining = (target - datetime.now(timezone.utc)).total_seconds()
            if remaining > 0 and cancel.wait(remaining):
                return
            if not cancel.is_set():
                task(cancel)

        handle = self.background.start(name, delayed)
        scheduled = ScheduledJob(name, target, handle)
        with self._lock:
            self._scheduled[name] = scheduled
        return scheduled

    def cancel(self, name: str) -> bool:
        result = self.background.cancel(name)
        if result:
            with self._lock:
                self._scheduled.pop(name, None)
        return result

    def active(self) -> tuple[ScheduledJob, ...]:
        with self._lock:
            return tuple(sorted((job for job in self._scheduled.values() if job.name in self.background.active()), key=lambda job: job.run_at))
