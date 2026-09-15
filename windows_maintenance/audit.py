from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from .models import MaintenanceRecord


class AuditLog:
    """In-memory maintenance audit records; persistence is opt-in by the caller."""

    def __init__(self) -> None:
        self._records: list[MaintenanceRecord] = []

    def record(self, operation: str, target_id: str, previous_state: dict[str, object] | None = None, resulting_state: dict[str, object] | None = None, verified: bool = False, rollback_available: bool = False) -> MaintenanceRecord:
        record = MaintenanceRecord(
            correlation_id=str(uuid.uuid4()),
            operation=operation,
            target_id=target_id,
            previous_state=previous_state or {},
            resulting_state=resulting_state or {},
            verified=verified,
            rollback_available=rollback_available,
        )
        self._records.append(record)
        return record

    def records(self) -> tuple[MaintenanceRecord, ...]:
        return tuple(self._records)
