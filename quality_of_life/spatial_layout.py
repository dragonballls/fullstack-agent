"""Persistent spatial state for windows inside the Neural JARVIS world."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import os
import tempfile
import threading
from typing import Mapping


@dataclass
class SpatialWindowState:
    key: str
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: float = 1.0
    visible: bool = True
    pinned: bool = False
    mode: str = "flat"
    shape: dict[str, object] | None = None
    workspace: str = "default"
    z_priority: int = 0

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["position"] = list(self.position)
        payload["rotation"] = list(self.rotation)
        payload["angular_velocity"] = list(self.angular_velocity)
        return payload


class SpatialLayoutStore:
    """Thread-safe atomic store for arbitrary spatial window states."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) if os.name == "nt" else Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            path = base / "Jarvis" / "neural-world" / "spatial-layout.json"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._states: dict[str, SpatialWindowState] = {}
        self._load()

    @staticmethod
    def _vector(value: object, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            return fallback
        try:
            return tuple(float(item) for item in value)  # type: ignore[return-value]
        except (TypeError, ValueError):
            return fallback

    @classmethod
    def _normalize(cls, raw: Mapping[str, object]) -> SpatialWindowState:
        key = str(raw.get("key", "")).strip()
        if not key or len(key) > 256:
            raise ValueError("spatial window key must be non-empty and <= 256 characters")
        mode = str(raw.get("mode", "flat")).strip().lower()
        if mode not in {"flat", "portal", "mirror", "desktop"}:
            raise ValueError("unsupported spatial window mode")
        workspace = str(raw.get("workspace", "default")).strip()[:120] or "default"
        raw_shape = raw.get("shape")
        shape = dict(raw_shape) if isinstance(raw_shape, Mapping) else {"name": "rectangle", "family": "primitive", "parameters": {}}
        return SpatialWindowState(
            key=key,
            position=cls._vector(raw.get("position"), (0.0, 0.0, 0.0)),
            rotation=cls._vector(raw.get("rotation"), (0.0, 0.0, 0.0)),
            angular_velocity=cls._vector(raw.get("angular_velocity"), (0.0, 0.0, 0.0)),
            scale=max(0.05, min(100.0, float(raw.get("scale", 1.0)))),
            visible=bool(raw.get("visible", True)),
            pinned=bool(raw.get("pinned", False)),
            mode=mode,
            shape=shape,
            workspace=workspace,
            z_priority=max(-1_000_000, min(1_000_000, int(raw.get("z_priority", 0)))),
        )

    def _load(self) -> None:
        with self._lock:
            if not self.path.is_file():
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    return
                entries = raw.get("windows", {})
                if not isinstance(entries, dict):
                    return
                loaded: dict[str, SpatialWindowState] = {}
                for key, value in entries.items():
                    if not isinstance(value, dict):
                        continue
                    try:
                        loaded[str(key)] = self._normalize({"key": key, **value})
                    except (TypeError, ValueError):
                        continue
                self._states = loaded
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                self._states = {}

    def _save(self) -> None:
        payload = {"schema_version": 1, "windows": {key: state.as_dict() for key, state in self._states.items()}}
        fd, temp_name = tempfile.mkstemp(prefix=".spatial.", dir=str(self.path.parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        finally:
            temp_path.unlink(missing_ok=True)

    def get(self, key: str) -> SpatialWindowState | None:
        with self._lock:
            return self._states.get(str(key))

    def upsert(self, key: str, **kwargs: object) -> SpatialWindowState:
        with self._lock:
            current = self._states.get(str(key))
            raw = current.as_dict() if current is not None else {"key": str(key)}
            raw.update(kwargs)
            state = self._normalize(raw)
            self._states[state.key] = state
            self._save()
            return state

    def remove(self, key: str) -> bool:
        with self._lock:
            removed = self._states.pop(str(key), None) is not None
            if removed:
                self._save()
            return removed

    def list(self) -> list[SpatialWindowState]:
        with self._lock:
            return sorted(self._states.values(), key=lambda item: (item.workspace.casefold(), -item.z_priority, item.key.casefold()))
