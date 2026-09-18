"""Versioned atomic persistence for the Neural JARVIS world."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Mapping


CURRENT_SCHEMA_VERSION = 1


def default_root() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "Jarvis" / "neural-world"


@dataclass(frozen=True)
class WorldSnapshot:
    schema_version: int
    saved_at: str
    entities: tuple[Mapping[str, object], ...]
    relations: tuple[Mapping[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "saved_at": self.saved_at,
            "entities": [dict(item) for item in self.entities],
            "relations": [dict(item) for item in self.relations],
        }


class NeuralPersistence:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "world.json"
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save(self, entities: list[Mapping[str, object]], relations: list[Mapping[str, object]]) -> None:
        payload = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "saved_at": self._now(),
            "entities": [dict(item) for item in entities if bool(item.get("persistent", True))],
            "relations": [dict(item) for item in relations],
        }
        with self._lock:
            fd, temp_name = tempfile.mkstemp(prefix=".world.", dir=str(self.root))
            temp_path = Path(temp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, self.path)
            finally:
                temp_path.unlink(missing_ok=True)

    def load(self) -> WorldSnapshot | None:
        with self._lock:
            if not self.path.is_file():
                return None
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                return None
            if not isinstance(payload, dict) or int(payload.get("schema_version", 0)) != CURRENT_SCHEMA_VERSION:
                return None
            entities = payload.get("entities", [])
            relations = payload.get("relations", [])
            if not isinstance(entities, list) or not isinstance(relations, list):
                return None
            return WorldSnapshot(
                CURRENT_SCHEMA_VERSION,
                str(payload.get("saved_at", "")),
                tuple(item for item in entities if isinstance(item, dict)),
                tuple(item for item in relations if isinstance(item, dict)),
            )

    def backup(self) -> Path | None:
        with self._lock:
            if not self.path.is_file():
                return None
            backup = self.root / "world.backup.json"
            backup.write_bytes(self.path.read_bytes())
            return backup
