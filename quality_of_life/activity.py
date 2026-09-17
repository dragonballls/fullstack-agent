"""Bounded process-local activity lifecycle shared by Jarvis workspaces."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
import re
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from uuid import uuid4


class ActivityStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL = {ActivityStatus.SUCCEEDED, ActivityStatus.FAILED, ActivityStatus.CANCELLED}
_ALLOWED: dict[ActivityStatus, set[ActivityStatus]] = {
    ActivityStatus.QUEUED: {
        ActivityStatus.RUNNING,
        ActivityStatus.WAITING,
        ActivityStatus.SUCCEEDED,
        ActivityStatus.FAILED,
        ActivityStatus.CANCELLED,
    },
    ActivityStatus.RUNNING: {
        ActivityStatus.RUNNING,
        ActivityStatus.WAITING,
        ActivityStatus.SUCCEEDED,
        ActivityStatus.FAILED,
        ActivityStatus.CANCELLED,
    },
    ActivityStatus.WAITING: {
        ActivityStatus.RUNNING,
        ActivityStatus.WAITING,
        ActivityStatus.SUCCEEDED,
        ActivityStatus.FAILED,
        ActivityStatus.CANCELLED,
    },
    ActivityStatus.SUCCEEDED: set(),
    ActivityStatus.FAILED: set(),
    ActivityStatus.CANCELLED: set(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ActivityRecord:
    id: str
    title: str
    status: ActivityStatus
    progress: int | None
    step: str
    created_at: str
    updated_at: str
    error: str | None
    cancel_requested: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "progress": self.progress,
            "step": self.step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "cancel_requested": self.cancel_requested,
        }


class ActivityStore:
    """Thread-safe bounded store; it does not execute or terminate activities."""

    def __init__(self, max_records: int = 100) -> None:
        if max_records < 1:
            raise ValueError("max_records must be at least 1")
        self.max_records = max_records
        self._records: OrderedDict[str, ActivityRecord] = OrderedDict()
        self._lock = RLock()

    def create(self, title: str) -> ActivityRecord:
        normalized = str(title or "").strip()
        if not normalized:
            raise ValueError("activity title cannot be empty")
        timestamp = _now().isoformat()
        record = ActivityRecord(
            id=uuid4().hex,
            title=normalized,
            status=ActivityStatus.QUEUED,
            progress=None,
            step="",
            created_at=timestamp,
            updated_at=timestamp,
            error=None,
        )
        with self._lock:
            self._records[record.id] = record
            self._trim()
        return record

    def get(self, activity_id: str) -> ActivityRecord | None:
        with self._lock:
            return self._records.get(activity_id)

    def list(self, limit: int = 50) -> tuple[ActivityRecord, ...]:
        if limit < 1:
            return ()
        with self._lock:
            records = tuple(reversed(self._records.values()))
        return records[:limit]

    def update(
        self,
        activity_id: str,
        *,
        status: ActivityStatus,
        progress: int | None = None,
        step: str = "",
        error: str | None = None,
    ) -> ActivityRecord:
        with self._lock:
            current = self._require(activity_id)
            status = ActivityStatus(status)
            if status not in _ALLOWED[current.status]:
                raise ValueError(f"invalid activity transition: {current.status.value} -> {status.value}")
            updated = replace(
                current,
                status=status,
                progress=self._normalize_progress(progress),
                step=str(step or "").strip(),
                error=self._safe_error(error) if status == ActivityStatus.FAILED else None,
                updated_at=_now().isoformat(),
            )
            self._records[activity_id] = updated
            return updated

    def request_cancel(self, activity_id: str) -> ActivityRecord:
        with self._lock:
            current = self._require(activity_id)
            if current.status in _TERMINAL:
                raise ValueError("cannot request cancellation for a terminal activity")
            if current.cancel_requested:
                return current
            updated = replace(current, cancel_requested=True, updated_at=_now().isoformat())
            self._records[activity_id] = updated
            return updated

    def acknowledge_cancel(self, activity_id: str) -> ActivityRecord:
        with self._lock:
            current = self._require(activity_id)
            if current.status in _TERMINAL and current.status != ActivityStatus.CANCELLED:
                raise ValueError("cannot acknowledge cancellation for a completed activity")
            if current.status == ActivityStatus.CANCELLED:
                return current
            if not current.cancel_requested:
                raise ValueError("cancellation was not requested")
            updated = replace(
                current,
                status=ActivityStatus.CANCELLED,
                updated_at=_now().isoformat(),
            )
            self._records[activity_id] = updated
            return updated

    def _require(self, activity_id: str) -> ActivityRecord:
        try:
            return self._records[activity_id]
        except KeyError as exc:
            raise KeyError(f"unknown activity: {activity_id}") from exc

    def _trim(self) -> None:
        while len(self._records) > self.max_records:
            self._records.popitem(last=False)

    @staticmethod
    def _normalize_progress(progress: int | None) -> int | None:
        if progress is None:
            return None
        return max(0, min(100, int(progress)))

    @staticmethod
    def _safe_error(error: str | None) -> str | None:
        if error is None:
            return None
        text = str(error).replace("\\", "/")
        text = re.sub(r"(?i)(token|api[_-]?key|authorization|password)\\s*[=:]\\s*(?:Bearer\\s+)?([^\\s,;]+)", r"\\1=[redacted]", text)
        return text[:500]
