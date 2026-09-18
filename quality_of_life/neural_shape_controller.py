"""Persistent, reversible 3D shape/transform controller for the Neural JARVIS world.

The controller deliberately operates on the existing NeuralWorld and SpatialLayoutStore
rather than replacing either. Every mutation records the first observed state of its target,
so "revert" restores the pre-change state and "revert everything" restores all touched
targets while removing objects created by the controller.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import os
import tempfile
import threading
import uuid
from typing import Any, Mapping, Sequence

from .neural_shapes import ShapeSpec, normalize_shape


def _base_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _vec3(value: object, default: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return default
    try:
        return tuple(float(v) for v in value)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return default


def parse_rotation_speed(value: object, unit: str | None = None) -> float:
    """Normalize common human units to radians/second."""
    number = float(value)
    if unit:
        u = str(unit).strip().casefold().replace("°", "deg")
        if "rpm" in u:
            return number * 6.283185307179586 / 60.0
        if "rps" in u:
            return number * 6.283185307179586
        if "deg" in u:
            return number * 3.141592653589793 / 180.0
    return number


@dataclass
class ShapeHistoryEntry:
    target_id: str
    original_entity: dict[str, Any] | None = None
    original_layout: dict[str, Any] | None = None
    generated: bool = False
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "original_entity": self.original_entity,
            "original_layout": self.original_layout,
            "generated": self.generated,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class NeuralShapeController:
    """Universal shape + motion layer with first-state snapshots and full rollback."""

    def __init__(self, world: Any, layout: Any, path: str | Path | None = None) -> None:
        self.world = world
        self.layout = layout
        self.path = Path(path) if path is not None else _base_dir() / "Jarvis" / "neural-world" / "shape-history.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._history: dict[str, ShapeHistoryEntry] = {}
        self._load()

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return
        items = payload.get("history", {}) if isinstance(payload, dict) else {}
        if not isinstance(items, dict):
            return
        with self._lock:
            for target_id, raw in items.items():
                if not isinstance(raw, dict):
                    continue
                self._history[str(target_id)] = ShapeHistoryEntry(
                    target_id=str(raw.get("target_id", target_id)),
                    original_entity=dict(raw["original_entity"]) if isinstance(raw.get("original_entity"), dict) else None,
                    original_layout=dict(raw["original_layout"]) if isinstance(raw.get("original_layout"), dict) else None,
                    generated=bool(raw.get("generated", False)),
                    created_at=str(raw.get("created_at", "")),
                    updated_at=str(raw.get("updated_at", "")),
                )

    def _save(self) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=".shape-history.", dir=str(self.path.parent))
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    {"schema_version": 1, "history": {key: value.as_dict() for key, value in self._history.items()}},
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
        finally:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _normalize_motion(rotation_speed: object = 0.0, rotation_axis: object = "y") -> tuple[float, float, float]:
        speed = float(rotation_speed or 0.0)
        axis = str(rotation_axis or "y").strip().casefold()
        axes = {"x": (speed, 0.0, 0.0), "y": (0.0, speed, 0.0), "z": (0.0, 0.0, speed)}
        if axis in {"xyz", "all", "free"}:
            return (speed, speed, speed)
        return axes.get(axis, (0.0, speed, 0.0))

    def _snapshot_once(self, target_id: str, *, generated: bool = False) -> ShapeHistoryEntry:
        with self._lock:
            existing = self._history.get(target_id)
            if existing is not None:
                return existing
            entity = None
            layout = None
            if not generated:
                with self.world._lock:
                    node = self.world._entities.get(target_id)
                    if node is not None:
                        entity = node.as_dict()
            if not generated and target_id.startswith("window:"):
                state = self.layout.get(target_id)
                if state is not None:
                    layout = state.as_dict()
            entry = ShapeHistoryEntry(
                target_id=target_id,
                original_entity=entity,
                original_layout=layout,
                generated=generated,
                created_at=_now(),
                updated_at=_now(),
            )
            self._history[target_id] = entry
            self._save()
            return entry

    @staticmethod
    def shape_description(shape: object) -> ShapeSpec:
        return normalize_shape(shape)

    def create(
        self,
        label: str,
        shape: object,
        *,
        position: Sequence[float] = (0.0, 0.0, 0.0),
        scale: float = 1.0,
        rotation_speed: float = 0.0,
        rotation_axis: str = "y",
        parent_id: str | None = "jarvis.core",
        metadata: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        from .neural_world import EntityKind, LifecycleState
        spec = self.shape_description(shape)
        safe_label = str(label or spec.name or "Generated Object").strip()[:240] or "Generated Object"
        object_id = "generated:" + uuid.uuid4().hex
        angular_velocity = self._normalize_motion(rotation_speed, rotation_axis)
        meta = dict(metadata or {})
        meta["shape_transform"] = {
            "rotation": [0.0, 0.0, 0.0],
            "angular_velocity": list(angular_velocity),
            "generated_by": "neural_shape_controller",
            "created_at": _now(),
        }
        node = self.world.upsert(
            object_id,
            EntityKind.TEMPORARY,
            safe_label,
            source="jarvis.neural_shape",
            status="active",
            lifecycle=LifecycleState.ACTIVE,
            position=_vec3(position, (0.0, 0.0, 0.0)),
            scale=max(0.1, min(8.0, float(scale))),
            energy=0.78,
            persistent=True,
            parent_id=parent_id,
            shape=spec.as_dict(),
            metadata=meta,
        )
        self._snapshot_once(object_id, generated=True)
        with self.world._lock:
            self.world.events.publish(
                "entity.shape.generated",
                entity_id=node.id,
                payload={"shape": node.shape, "angular_velocity": list(angular_velocity)},
            )
        return {
            "ok": True,
            "created": True,
            "id": node.id,
            "label": node.label,
            "shape": dict(node.shape),
            "angular_velocity": list(angular_velocity),
        }

    def apply(
        self,
        target_id: str,
        shape: object,
        *,
        rotation_speed: float = 0.0,
        rotation_axis: str = "y",
        rotation: Sequence[float] = (0.0, 0.0, 0.0),
    ) -> dict[str, object]:
        target = str(target_id).strip()
        if not target:
            raise ValueError("target id is required")
        spec = self.shape_description(shape)
        angular_velocity = self._normalize_motion(rotation_speed, rotation_axis)
        entry = self._snapshot_once(target)
        with self.world._lock:
            node = self.world._entities.get(target)
            if node is None:
                raise KeyError("unknown neural target")
            node.shape = spec.as_dict()
            transform = dict(node.metadata.get("shape_transform", {})) if isinstance(node.metadata.get("shape_transform"), Mapping) else {}
            transform["rotation"] = list(_vec3(rotation))
            transform["angular_velocity"] = list(angular_velocity)
            transform["updated_at"] = _now()
            node.metadata["shape_transform"] = transform
            node.updated_at = _now()
            payload = {"shape": dict(node.shape), "shape_transform": transform}
            self.world.events.publish("entity.shape.changed", entity_id=node.id, payload=payload)
        if target.startswith("window:"):
            self.layout.upsert(
                target,
                shape=spec.as_dict(),
                rotation=list(_vec3(rotation)),
                angular_velocity=list(angular_velocity),
            )
        return {"ok": True, "id": target, "shape": dict(spec.as_dict()), "angular_velocity": list(angular_velocity), "history_saved": True}

    def apply_to_scope(self, scope: str, shape: object, **kwargs: object) -> dict[str, object]:
        """Apply one shape to a logical scope such as the whole neural brain."""
        normalized = str(scope or "").strip().casefold()
        if normalized not in {"brain", "brain structure", "neural mesh", "whole brain", "everything neural"}:
            return self.apply(scope, shape, **kwargs)
        targets: list[str] = []
        with self.world._lock:
            for node in self.world._entities.values():
                if node.id.startswith("generated:"):
                    continue
                if node.kind.value in {"core", "subsystem", "temporary"}:
                    continue
                targets.append(node.id)
        changed = 0
        for target_id in targets:
            try:
                self.apply(target_id, shape, **kwargs)
                changed += 1
            except (KeyError, ValueError, OSError):
                continue
        return {"ok": True, "scope": "brain", "changed": changed, "shape": self.shape_description(shape).as_dict()}

    def _restore_entry(self, entry: ShapeHistoryEntry) -> bool:
        target = entry.target_id
        if entry.generated and entry.original_entity is None:
            try:
                self.world.retire(target, remove=True)
            except Exception:
                return False
            if target.startswith("window:"):
                try:
                    self.layout.remove(target)
                except Exception:
                    pass
            return True
        restored = False
        if entry.original_entity is not None:
            raw = entry.original_entity
            try:
                self.world.upsert(
                    str(raw["id"]), str(raw["kind"]), str(raw["label"]),
                    source=str(raw.get("source", "restored")),
                    status=str(raw.get("status", "idle")),
                    lifecycle=str(raw.get("lifecycle", "mature")),
                    position=_vec3(raw.get("position")),
                    scale=float(raw.get("scale", 1.0)),
                    energy=float(raw.get("energy", 0.35)),
                    visible=bool(raw.get("visible", True)),
                    persistent=bool(raw.get("persistent", True)),
                    parent_id=raw.get("parent_id"),
                    shape=raw.get("shape", "droplet"),
                    metadata=raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else None,
                )
                restored = True
            except (KeyError, TypeError, ValueError, MemoryError):
                pass
        if entry.original_layout is not None:
            raw_layout = dict(entry.original_layout)
            raw_layout.pop("key", None)
            try:
                self.layout.upsert(target, **raw_layout)
                restored = True
            except (TypeError, ValueError, OSError):
                pass
        return restored

    def revert(self, target_id: str) -> dict[str, object]:
        target = str(target_id).strip()
        with self._lock:
            entry = self._history.get(target)
        if entry is None:
            raise KeyError("no original state has been recorded for this target")
        ok = self._restore_entry(entry)
        with self._lock:
            if ok:
                self._history.pop(target, None)
                self._save()
        return {"ok": ok, "id": target, "reverted": ok}

    def remove(self, target_id: str) -> dict[str, object]:
        """Remove generated objects, otherwise restore the original pre-shape state."""
        return self.revert(target_id)

    def revert_all(self) -> dict[str, object]:
        with self._lock:
            entries = list(self._history.values())
        restored = 0
        failed: list[str] = []
        for entry in reversed(entries):
            try:
                if self._restore_entry(entry):
                    restored += 1
                else:
                    failed.append(entry.target_id)
            except Exception:
                failed.append(entry.target_id)
        with self._lock:
            for entry in entries:
                self._history.pop(entry.target_id, None)
            self._save()
        return {"ok": not failed, "reverted": restored, "failed": failed, "remaining_history": len(self._history)}

    def history(self) -> list[dict[str, object]]:
        with self._lock:
            return [entry.as_dict() for entry in self._history.values()]

    def resolve_targets(self, query: str) -> list[str]:
        value = str(query or "").strip()
        lowered = value.casefold()
        if lowered in {"brain", "brain structure", "neural mesh", "whole brain", "everything neural"}:
            return [lowered]
        with self.world._lock:
            items = list(self.world._entities.values())
        needle = lowered
        exact = [item.id for item in items if item.label.casefold() == needle or item.id.casefold() == needle]
        if exact:
            return exact
        contains = [item.id for item in items if needle in item.label.casefold() or needle in item.id.casefold() or needle in item.kind.value.casefold()]
        return [item.id for item in contains[:12]]

    def describe(self, target_id: str) -> dict[str, object]:
        target = str(target_id)
        with self.world._lock:
            node = self.world._entities.get(target)
            if node is not None:
                return node.as_dict()
        if target.startswith("window:"):
            state = self.layout.get(target)
            if state is not None:
                return state.as_dict()
        raise KeyError(target)
