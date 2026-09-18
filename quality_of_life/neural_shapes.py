"""Extensible shape descriptors for Neural JARVIS entities."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

BUILTIN_SHAPES = (
    "droplet", "sphere", "crystal", "cube", "torus",
    "capsule", "ring", "star", "orbital", "core", "heart", "gear", "spiral", "pyramid", "wave", "dna", "molecule", "arrow", "globe", "planet", "cone", "cylinder", "disk", "octahedron", "icosphere",
)


@dataclass(frozen=True)
class ShapeSpec:
    name: str = "droplet"
    family: str = "primitive"
    parameters: Mapping[str, float] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "family": self.family,
            "parameters": dict(self.parameters) if isinstance(self.parameters, Mapping) else {},
        }


def normalize_shape(value: object) -> ShapeSpec:
    if isinstance(value, Mapping):
        name = str(value.get("name", "droplet")).strip()[:120] or "droplet"
        family = str(value.get("family", "primitive")).strip().lower()[:40] or "primitive"
        raw = value.get("parameters", {})
        params: dict[str, float] = {}
        if isinstance(raw, Mapping):
            for key, raw_value in raw.items():
                try:
                    number = float(raw_value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    params[str(key)[:40]] = max(-1000.0, min(1000.0, number))
        if family not in {"primitive", "parametric", "freeform"}:
            raise ValueError("unsupported shape family")
        return ShapeSpec(name=name, family=family, parameters=params)
    name = str(value or "").strip()[:120] or "droplet"
    folded = name.casefold()
    aliases = (
        ("icosphere", "sphere"), ("globe", "sphere"), ("planet", "sphere"), ("ball", "sphere"),
        ("donut", "torus"), ("ring", "ring"), ("box", "cube"), ("cube", "cube"),
        ("neuron", "droplet"), ("cell", "droplet"), ("brain", "droplet"),
        ("cone", "cone"), ("cylinder", "cylinder"), ("tube", "cylinder"),
        ("octahedron", "octahedron"), ("diamond", "crystal"), ("pyramid", "pyramid"),
        ("star", "star"), ("heart", "heart"), ("spiral", "spiral"), ("wave", "wave"),
        ("dna", "dna"), ("molecule", "molecule"),
    )
    for needle, canonical in aliases:
        if needle in folded:
            return ShapeSpec(name=canonical, family="primitive")
    return ShapeSpec(name=name, family="primitive" if folded in BUILTIN_SHAPES else "freeform")



class ShapeRegistry:
    """Persistent library of user-defined, reusable shape recipes."""

    def __init__(self, path: str | object | None = None) -> None:
        from pathlib import Path
        import os
        import json
        import threading
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) if os.name == "nt" else Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        self.path = Path(path) if path is not None else base / "Jarvis" / "neural-world" / "shapes.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._items: dict[str, ShapeSpec] = {}
        self._load()

    @staticmethod
    def _safe_name(name: object) -> str:
        value = str(name or "").strip().casefold()
        if not value or len(value) > 120 or any(ch in value for ch in "\\/:*?\"<>|"):
            raise ValueError("invalid custom shape name")
        return value

    def _load(self) -> None:
        import json
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return
        items = payload.get("shapes", {})
        if not isinstance(items, dict):
            return
        with self._lock:
            for key, value in items.items():
                if not isinstance(value, dict):
                    continue
                try:
                    spec = normalize_shape(value)
                    self._items[self._safe_name(key)] = spec
                except (TypeError, ValueError):
                    continue

    def _save(self) -> None:
        import json
        import os
        import tempfile
        fd, temp_name = tempfile.mkstemp(prefix=".shapes.", dir=str(self.path.parent))
        temp = type(self.path)(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"schema_version": 1, "shapes": {key: spec.as_dict() for key, spec in self._items.items()}}, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)

    def save(self, name: str, shape: object) -> ShapeSpec:
        key = self._safe_name(name)
        spec = normalize_shape(shape)
        if spec.family == "primitive" and spec.name.casefold() not in BUILTIN_SHAPES:
            spec = ShapeSpec(spec.name, "freeform", dict(spec.parameters))
        with self._lock:
            self._items[key] = spec
            self._save()
            return spec

    def get(self, name: str) -> ShapeSpec | None:
        with self._lock:
            return self._items.get(self._safe_name(name))

    def delete(self, name: str) -> bool:
        key = self._safe_name(name)
        with self._lock:
            removed = self._items.pop(key, None) is not None
            if removed:
                self._save()
            return removed

    def catalog(self) -> list[dict[str, object]]:
        with self._lock:
            return [{"name": key, "shape": spec.as_dict()} for key, spec in sorted(self._items.items())]

    def resolve(self, request: object) -> ShapeSpec:
        text = str(request or "").strip()
        if not text:
            return normalize_shape("droplet")
        with self._lock:
            custom = self._items.get(text.casefold())
        return custom or normalize_shape(text)
