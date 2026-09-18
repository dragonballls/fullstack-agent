"""Bounded sequence-based event stream for Neural JARVIS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
import threading
from typing import Any, Mapping


@dataclass(frozen=True)
class NeuralEvent:
    sequence: int
    kind: str
    entity_id: str | None
    payload: Mapping[str, object]
    created_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "kind": self.kind,
            "entity_id": self.entity_id,
            "payload": dict(self.payload),
            "created_at": self.created_at,
        }


class NeuralEventBus:
    def __init__(self, *, max_events: int = 10000) -> None:
        if max_events < 100:
            raise ValueError("max_events must be at least 100")
        self.max_events = max_events
        self._lock = threading.RLock()
        self._sequence = count(1)
        self._events: list[NeuralEvent] = []
        self._subscribers: list[Any] = []

    def publish(self, kind: str, *, entity_id: str | None = None, payload: Mapping[str, object] | None = None) -> NeuralEvent:
        with self._lock:
            event = NeuralEvent(next(self._sequence), str(kind)[:120], entity_id, dict(payload or {}), datetime.now(timezone.utc).isoformat())
            self._events.append(event)
            if len(self._events) > self.max_events:
                del self._events[:len(self._events) - self.max_events]
            subscribers = tuple(self._subscribers)
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                pass
        return event

    def subscribe(self, callback: Any) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Any) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def since(self, sequence: int = 0, *, limit: int = 500) -> list[dict[str, object]]:
        cap = max(1, min(2000, int(limit)))
        with self._lock:
            return [event.as_dict() for event in self._events if event.sequence > max(0, int(sequence))][-cap:]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
