"""Core data model and guarded bridge for the Neural JARVIS spatial world."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import math
import threading
import time
from typing import Any, Mapping

from .neural_discovery import NeuralDiscovery
from .neural_events import NeuralEventBus
from .neural_persistence import NeuralPersistence
from .neural_shapes import ShapeRegistry, normalize_shape
from .neural_performance import AdaptivePerformanceController
from .neural_fullstack import FullStackNeuralExperience
from .spatial_layout import SpatialLayoutStore
from .permissions import Capability
from .neural_advanced import NeuralAdvancedRuntime


class EntityKind(str, Enum):
    CORE = "core"
    SUBSYSTEM = "subsystem"
    FILE = "file"
    FOLDER = "folder"
    DRIVE = "drive"
    APPLICATION = "application"
    WINDOW = "window"
    BROWSER = "browser"
    BROWSER_TAB = "browser_tab"
    PAGE = "page"
    REPOSITORY = "repository"
    BRANCH = "branch"
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    BUILD = "build"
    ARTIFACT = "artifact"
    TEST = "test"
    AGENT = "agent"
    WORKFLOW = "workflow"
    TASK = "task"
    MEMORY = "memory"
    DEVICE = "device"
    ACCOUNT = "account"
    SERVICE = "service"
    LOCATION = "location"
    PROCESS = "process"
    PERFORMANCE = "performance"
    NOTIFICATION = "notification"
    SEARCH_RESULT = "search_result"
    TEMPORARY = "temporary"


class LifecycleState(str, Enum):
    NEWBORN = "newborn"
    ACTIVE = "active"
    MATURE = "mature"
    DORMANT = "dormant"
    WAITING = "waiting"
    FAILED = "failed"
    RESTRICTED = "restricted"
    RETIRING = "retiring"
    RETIRED = "retired"


@dataclass
class NeuralEntity:
    id: str
    kind: EntityKind
    label: str
    source: str
    status: str = "idle"
    lifecycle: LifecycleState = LifecycleState.MATURE
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: float = 1.0
    energy: float = 0.35
    visible: bool = True
    persistent: bool = True
    parent_id: str | None = None
    shape: dict[str, object] = field(default_factory=lambda: normalize_shape("droplet").as_dict())
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id, "kind": self.kind.value, "label": self.label,
            "source": self.source, "status": self.status,
            "lifecycle": self.lifecycle.value, "position": list(self.position),
            "scale": self.scale, "energy": self.energy, "visible": self.visible,
            "persistent": self.persistent, "parent_id": self.parent_id,
            "shape": dict(self.shape), "metadata": dict(self.metadata), "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class NeuralRelation:
    source: str
    target: str
    relation_type: str
    strength: float = 0.5

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source, "target": self.target,
            "relation_type": self.relation_type,
            "strength": max(0.0, min(1.0, float(self.strength))),
        }


@dataclass
class PerformanceSnapshot:
    cpu_percent: float | None
    memory_percent: float | None
    process_count: int | None
    quality: str
    mode: str

    def as_dict(self) -> dict[str, object]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "process_count": self.process_count,
            "quality": self.quality,
            "mode": self.mode,
        }


_UNSET = object()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_position(entity_id: str) -> tuple[float, float, float]:
    digest = hashlib.sha256(entity_id.encode("utf-8")).digest()
    a = int.from_bytes(digest[0:4], "big") / 0xFFFFFFFF
    b = int.from_bytes(digest[4:8], "big") / 0xFFFFFFFF
    c = int.from_bytes(digest[8:12], "big") / 0xFFFFFFFF
    radius = 4.0 + a * 10.0
    theta = b * math.tau
    phi = (c - 0.5) * 0.9
    return (
        math.cos(theta) * math.cos(phi) * radius,
        math.sin(phi) * radius * 0.65,
        math.sin(theta) * math.cos(phi) * radius,
    )


class NeuralWorld:
    """Thread-safe graph with deterministic placement and bounded snapshots."""

    def __init__(self, *, max_entities: int = 50_000, event_bus: NeuralEventBus | None = None, persistence: NeuralPersistence | None = None) -> None:
        if max_entities < 100:
            raise ValueError("max_entities must be at least 100")
        self.max_entities = max_entities
        self._lock = threading.RLock()
        self._entities: dict[str, NeuralEntity] = {}
        self._relations: dict[tuple[str, str, str], NeuralRelation] = {}
        self.events = event_bus or NeuralEventBus()
        self.persistence = persistence
        self.shape_registry = ShapeRegistry()
        self._bootstrap()
        self._load_persisted()
        self.advanced = NeuralAdvancedRuntime()

    def _bootstrap(self) -> None:
        core = self.upsert(
            "jarvis.core", EntityKind.CORE, "JARVIS CORE", source="jarvis",
            energy=1.0, scale=2.0, position=(0.0, 0.0, 0.0),
        )
        for entity_id, label in (
            ("jarvis.browser", "Browser"), ("jarvis.coding", "Coding"),
            ("jarvis.system", "System"), ("jarvis.gods-eye", "God's Eye"),
            ("jarvis.workflows", "Workflows"), ("jarvis.memory", "Memory"),
            ("jarvis.agents", "Agents"), ("jarvis.devices", "Devices"),
            ("jarvis.neural-command", "Neural Command"),
        ):
            is_command = entity_id == "jarvis.neural-command"
            node = self.upsert(
                entity_id,
                EntityKind.SUBSYSTEM,
                label,
                source="jarvis",
                parent_id=core.id,
                energy=0.96 if is_command else 0.6,
                scale=0.62 if is_command else 1.35,
                position=(0.0, -2.15, 0.85) if is_command else None,
                shape="orbital" if is_command else _UNSET,
                metadata={"ui_surface": "neural_command", "always_visible": True} if is_command else None,
            )
            self.relate(core.id, node.id, "neural-command-surface" if is_command else "subsystem", 0.98 if is_command else 0.95)

    def upsert(
        self, entity_id: str, kind: EntityKind | str, label: str, *,
        source: str, status: str = "idle",
        lifecycle: LifecycleState | str = LifecycleState.MATURE,
        position: tuple[float, float, float] | None = None,
        scale: float = 1.0, energy: float = 0.35, visible: bool = True,
        persistent: bool = True, parent_id: object = _UNSET,
        shape: object = _UNSET, metadata: Mapping[str, object] | None = None,
    ) -> NeuralEntity:
        safe_id = str(entity_id).strip()
        if not safe_id or len(safe_id) > 256:
            raise ValueError("entity id must be non-empty and <= 256 characters")
        if not str(label).strip():
            raise ValueError("entity label must be non-empty")
        with self._lock:
            if len(self._entities) >= self.max_entities and safe_id not in self._entities:
                raise MemoryError("neural world entity budget exhausted")
            now = _now()
            existing = self._entities.get(safe_id)
            if existing is not None:
                before = existing.as_dict()
                existing.label = str(label)[:500]
                existing.source = str(source)[:200]
                existing.status = str(status)[:120]
                existing.lifecycle = lifecycle if isinstance(lifecycle, LifecycleState) else LifecycleState(str(lifecycle))
                existing.position = tuple(float(v) for v in (position or existing.position))  # type: ignore[assignment]
                existing.scale = max(0.1, min(8.0, float(scale)))
                existing.energy = max(0.0, min(1.0, float(energy)))
                existing.visible = bool(visible)
                existing.persistent = bool(persistent)
                if parent_id is not _UNSET:
                    existing.parent_id = str(parent_id) if parent_id is not None else None
                if shape is not _UNSET:
                    existing.shape = normalize_shape(shape).as_dict()
                if metadata is not None:
                    existing.metadata = dict(metadata)
                existing.updated_at = now
                after = existing.as_dict()
                if before != after:
                    self.events.publish("entity.updated", entity_id=existing.id, payload=after)
                return existing
            node = NeuralEntity(
                id=safe_id, kind=kind if isinstance(kind, EntityKind) else EntityKind(str(kind)), label=str(label)[:500],
                source=str(source)[:200], status=str(status)[:120],
                lifecycle=lifecycle if isinstance(lifecycle, LifecycleState) else LifecycleState(str(lifecycle)),
                position=position or _stable_position(safe_id),
                scale=max(0.1, min(8.0, float(scale))),
                energy=max(0.0, min(1.0, float(energy))),
                visible=bool(visible), persistent=bool(persistent),
                parent_id=None if parent_id is _UNSET else (str(parent_id) if parent_id is not None else None),
                shape=normalize_shape("droplet" if shape is _UNSET else shape).as_dict(),
                metadata=dict(metadata or {}),
                created_at=now, updated_at=now,
            )
            self._entities[safe_id] = node
            self.events.publish("entity.created", entity_id=node.id, payload={"kind": node.kind.value, "label": node.label, "lifecycle": node.lifecycle.value, "shape": node.shape})
            return node

    def neural_advanced_command(self, domain: str, operation: str, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        data = dict(payload or {})
        op = str(operation)
        if domain == "core":
            if op == "reorganize": return self.advanced.liquid.reorganize_core(dict(data.get("priorities", {})))
            if op == "mitosis": return {"events": self.advanced.liquid.mitosis(str(data["id"]), count=int(data.get("count", 2)))}
            if op == "apoptosis": return {"events": self.advanced.liquid.apoptosis_sequence(str(data["id"]), steps=int(data.get("steps", 6))), "state": self.advanced.liquid.apoptosis(str(data["id"]))}
            if op == "reconnect": return self.advanced.liquid.reconnect(str(data["source"]), str(data["target"]), strength=float(data.get("strength", .9)))
            if op == "satellite": return self.advanced.liquid.create_satellite(str(data["id"]), orbit=float(data.get("orbit", .65)))
            if op == "magnetic": return self.advanced.liquid.magnetic_relationship(str(data["source"]), str(data["target"]), polarity=float(data.get("polarity", 1)), strength=float(data.get("strength", .8)))
            if op == "growth": return {"events": self.advanced.liquid.growth_sequence(str(data["id"]), steps=int(data.get("steps", 5)))}
        if domain == "fluid":
            if op == "tick": return self.advanced.liquid.step(float(data.get("dt", .016)), activity=float(data.get("activity", .5)), cohesion=float(data.get("cohesion", .72)), elasticity=float(data.get("elasticity", .35)), turbulence=float(data.get("turbulence", .16)))
        if domain == "workspace":
            return self.advanced.command_workspace(op, data)
        if domain == "cross_application":
            if op == "suggest":
                return {"suggestions": self.advanced.cross_app.suggest(str(data["kind"]), str(data["source"]), destinations=[str(v) for v in data.get("destinations", [])])}
            if op == "transfer":
                return self.advanced.cross_app.transfer(str(data["kind"]), str(data["source"]), str(data["destination"]), str(data.get("payload_ref")) if data.get("payload_ref") else None)
        if domain == "performance":
            if op == "sample": return self.advanced.performance.sample(**data)
            if op == "cost": return self.advanced.performance.cost(windows=data.get("windows"), neurons=data.get("neurons"))
            if op == "compare": return self.advanced.performance.compare(str(data["name"]), float(data["before"]), float(data["after"]))
            if op == "policy": return self.advanced.performance.optimization_policy(**{key: float(value) for key, value in data.items() if key in {"gpu_pressure", "cpu_pressure", "ram_pressure", "battery", "thermal"}})
        if domain == "display":
            if op == "update": return self.advanced.displays.upsert(str(data["id"]), **dict(data.get("state", {})))
            if op == "disconnect": return self.advanced.displays.disconnect(str(data["id"]))
            if op == "reconnect": return self.advanced.displays.reconnect(str(data["id"]), **dict(data.get("state", {})))
            if op == "save": return self.advanced.displays.save_arrangement()
        if domain in {"browser", "game"}:
            if op == "learn": return self.advanced.profile_learning(domain, str(data["name"]), **dict(data.get("metrics", {})))
            if op == "migrate": return self.advanced.browser_games.migrate_profile(domain, str(data["name"]), str(data["version"]))
            if domain == "browser" and op == "research_wall": return self.advanced.browser_games.research_wall(str(data["id"]), [str(v) for v in data.get("pages", [])], columns=int(data.get("columns", 3)))
            if domain == "browser" and op == "reconstruct": return self.advanced.browser_games.reconstruct_browser_session(str(data["id"]), [str(v) for v in data.get("pages", [])], layout=str(data.get("layout", "side-by-side")))
        if domain == "history":
            if op == "bookmark": return self.advanced.history.bookmark(str(data["name"]), dict(data.get("payload", {})))
            if op == "snapshot": return self.advanced.history.save_snapshot(str(data["id"]), dict(data.get("world", {})))
            if op == "decay": return self.advanced.history.decay_relationships(float(data.get("half_life_seconds", 86400)))
            if op == "prune": return self.advanced.history.prune(int(data.get("keep_recent", 128)))
            if op == "time_machine": return self.advanced.time_machine(compare=(str(data.get("left")), str(data.get("right"))) if data.get("left") and data.get("right") else None, replay_id=str(data.get("replay_id")) if data.get("replay_id") else None)
        if domain == "planning":
            if op == "dry_run": return self.advanced.planner.dry_run(list(data.get("actions", [])), known_good=data.get("known_good"))
            if op == "restore": return self.advanced.planner.restore(str(data["simulation_id"])) or {"restored": False}
        if domain == "reliability":
            if op == "sleep": return self.advanced.reliability.sleep()
            if op == "wake": return self.advanced.reliability.wake()
            if op == "monitor_change": return self.advanced.reliability.monitor_changed()
            if op in {"reset", "region_reset"}: return self.advanced.reliability.reset(str(data.get("region")) if data.get("region") else None)
            if op == "migrate": return self.advanced.reliability.migrate(dict(data.get("payload", {})), int(data.get("from_version", 1)))
        if domain == "inspect":
            return self.advanced.inspect()
        if domain == "remote":
            if op == "upsert": return self.advanced.remote.upsert(str(data["id"]), **dict(data.get("state", {})))
            if op == "reconnect": return self.advanced.remote.reconnect(str(data["id"]))
        if domain == "accessibility":
            return self.advanced.xr_accessibility.update(**data)
        if domain == "audio":
            if op == "event": return self.advanced.audio.emit(str(data["kind"]), source=str(data.get("source", "jarvis")), position=data.get("position"), intensity=float(data.get("intensity", .5)), priority=float(data.get("priority", .5)))
            if op == "policy": return self.advanced.audio.policy(game_active=bool(data.get("game_active", False)), performance_pressure=float(data.get("performance_pressure", 0)))
        if domain == "multi_user":
            if op == "profile": return self.advanced.multi_user.profile(str(data["id"]), **dict(data.get("preferences", {})))
            if op == "region": return self.advanced.multi_user.region(str(data["id"]), owner=str(data["owner"]), shared=bool(data.get("shared", False)), members=[str(v) for v in data.get("members", [])])
            if op == "resource": return self.advanced.multi_user.resource(str(data["id"]), owner=str(data["owner"]), shared=bool(data.get("shared", False)), controls=dict(data.get("controls", {})))
        if domain == "streaming":
            if op == "request": return self.advanced.streaming.request(str(data["id"]), priority=float(data.get("priority", .5)))
            if op == "pump": return self.advanced.streaming.pump(int(data.get("budget", 4)))
            if op == "unload": return self.advanced.streaming.unload(str(data["id"]))
        if domain == "simulation":
            if op == "generate": return self.advanced.simulation.generate(**{key: int(value) for key, value in data.items() if key in {"neurons", "windows", "tasks", "relationships"}})
            if op == "benchmark": return self.advanced.simulation_run(str(data.get("scenario", "cpu_stress")), count=int(data.get("count", 1000)))
        if domain == "master":
            if op == "status": return self.advanced.master_scope_status()
            if op == "execute": return self.advanced.execute_master_feature(str(data["feature"]), dict(data.get("payload", {})))
            if op == "smoke": return self.advanced.master_smoke_test(limit=int(data["limit"]) if data.get("limit") is not None else None)
        if domain == "completeness":
            if op == "status":
                return self.advanced.completeness.status()
            if op == "smoke":
                return self.advanced.completeness.smoke_all()
            if op == "execute":
                return self.advanced.completeness.execute(str(data["feature"]), dict(data.get("payload", {})))
        if domain == "fullstack":
            return self.advanced.fullstack.command(str(data.get("domain", "core_neural")), op, data.get("payload", data))
        raise ValueError(f"unknown advanced command: {domain}.{operation}")

    def retire(self, entity_id: str, *, remove: bool = False) -> bool:
        with self._lock:
            node = self._entities.get(entity_id)
            if node is None:
                return False
            node.lifecycle = LifecycleState.RETIRED
            node.status = "retired"
            node.energy = 0.0
            node.visible = False
            node.updated_at = _now()
            self.events.publish('entity.retired', entity_id=node.id, payload={'remove': bool(remove), 'lifecycle': node.lifecycle.value})
            if remove:
                self._entities.pop(entity_id, None)
                for key in tuple(self._relations):
                    if entity_id in key[:2]:
                        self._relations.pop(key, None)
            return True

    def relate(self, source: str, target: str, relation_type: str, strength: float = 0.5) -> NeuralRelation:
        with self._lock:
            if source not in self._entities or target not in self._entities:
                raise KeyError("relation endpoints must exist")
            key = (source, target, str(relation_type)[:120])
            normalized = max(0.0, min(1.0, float(strength)))
            prior = self._relations.get(key)
            relation = NeuralRelation(source, target, key[2], normalized)
            self._relations[key] = relation
            if prior is None:
                self.events.publish("relation.created", entity_id=source, payload=relation.as_dict())
            elif abs(prior.strength - relation.strength) >= 0.02:
                self.events.publish("relation.updated", entity_id=source, payload=relation.as_dict())
            return relation

    def search(self, query: str = "", *, kind: str | None = None,
               source: str | None = None, status: str | None = None,
               lifecycle: str | None = None, connected_to: str | None = None,
               updated_within_seconds: int | None = None,
               limit: int = 100) -> list[dict[str, object]]:
        needle = " ".join(str(query).casefold().split())
        lifecycle_value = str(lifecycle).casefold() if lifecycle else None
        cutoff = None
        if updated_within_seconds is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - max(1, min(31_536_000, int(updated_within_seconds)))
        if not any((needle, kind, source, status, lifecycle_value, connected_to, cutoff is not None)):
            raise ValueError("search query or filter must not be empty")
        with self._lock:
            connected_ids: set[str] | None = None
            if connected_to:
                wanted = str(connected_to).casefold()
                connected_ids = set()
                for entity_id, node in self._entities.items():
                    if wanted in entity_id.casefold() or wanted in node.label.casefold():
                        connected_ids.add(entity_id)
                if not connected_ids:
                    return []
                connected_ids = {
                    rel.target if rel.source in connected_ids else rel.source
                    for rel in self._relations.values()
                    if rel.source in connected_ids or rel.target in connected_ids
                }
            scored: list[tuple[int, NeuralEntity]] = []
            for node in self._entities.values():
                if connected_ids is not None and node.id not in connected_ids:
                    continue
                if kind and node.kind.value != str(kind):
                    continue
                if source and node.source != str(source):
                    continue
                if status and node.status != str(status):
                    continue
                if lifecycle and node.lifecycle.value != lifecycle_value:
                    continue
                if cutoff is not None:
                    try:
                        if datetime.fromisoformat(node.updated_at.replace("Z", "+00:00")).timestamp() < cutoff:
                            continue
                    except (TypeError, ValueError):
                        continue
                if needle:
                    haystack = " ".join((node.id, node.label, node.source, str(node.metadata))).casefold()
                    if needle not in haystack:
                        continue
                    score = 100 if node.label.casefold() == needle else 50 if needle in node.label.casefold() else 10
                else:
                    score = 0
                scored.append((score, node))
            scored.sort(key=lambda item: (-item[0], item[1].label.casefold(), item[1].id))
            return [node.as_dict() for _, node in scored[:max(1, min(500, int(limit)))]]

    def trace(self, start: str, target: str, *, max_hops: int = 8) -> list[dict[str, object]]:
        with self._lock:
            if start not in self._entities or target not in self._entities:
                raise KeyError("trace endpoints must exist")
            queue: deque[tuple[str, list[dict[str, object]]]] = deque([(start, [])])
            visited = {start}
            while queue:
                current, path = queue.popleft()
                if current == target:
                    return path
                if len(path) >= max_hops:
                    continue
                for relation in self._relations.values():
                    nxt = relation.target if relation.source == current else relation.source if relation.target == current else None
                    if nxt is None or nxt in visited:
                        continue
                    visited.add(nxt)
                    queue.append((nxt, path + [{
                        "from": current, "to": nxt,
                        "relation_type": relation.relation_type,
                        "strength": relation.strength,
                    }]))
        return []

    def save(self) -> bool:
        """Persist persistent entities and relationships when configured."""
        if self.persistence is None:
            return False
        with self._lock:
            entities = [node.as_dict() for node in self._entities.values() if node.persistent]
            relations = [relation.as_dict() for relation in self._relations.values()]
        self.persistence.save(entities, relations)
        self.events.publish("world.saved", payload={"entities": len(entities), "relations": len(relations)})
        return True

    def event_snapshot(self, sequence: int = 0, limit: int = 500) -> list[dict[str, object]]:
        return self.events.since(sequence, limit=limit)

    def _load_persisted(self) -> None:
        if self.persistence is None:
            return
        snapshot = self.persistence.load()
        if snapshot is None:
            return
        with self._lock:
            for item in snapshot.entities:
                try:
                    self.upsert(
                        str(item["id"]), str(item["kind"]), str(item["label"]),
                        source=str(item.get("source", "persisted")),
                        status=str(item.get("status", "idle")),
                        lifecycle=str(item.get("lifecycle", LifecycleState.MATURE.value)),
                        position=tuple(float(v) for v in item.get("position", (0, 0, 0))),
                        scale=float(item.get("scale", 1.0)),
                        energy=float(item.get("energy", 0.35)),
                        visible=bool(item.get("visible", True)),
                        persistent=bool(item.get("persistent", True)),
                        parent_id=str(item["parent_id"]) if item.get("parent_id") else None,
                        shape=item.get("shape", "droplet"),
                        metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else None,
                    )
                except (KeyError, TypeError, ValueError, MemoryError):
                    continue
            for item in snapshot.relations:
                try:
                    self.relate(
                        str(item["source"]),
                        str(item["target"]),
                        str(item["relation_type"]),
                        float(item.get("strength", 0.5)),
                    )
                except (KeyError, TypeError, ValueError):
                    continue
        self.events.clear()

    def snapshot(self, *, limit: int = 1800) -> dict[str, object]:
        limit = max(1, min(5000, int(limit)))
        with self._lock:
            nodes = sorted(
                (node for node in self._entities.values() if node.visible),
                key=lambda node: (node.kind is not EntityKind.CORE, -node.energy, node.label.casefold()),
            )[:limit]
            allowed = {node.id for node in nodes}
            relations = [
                relation.as_dict() for relation in self._relations.values()
                if relation.source in allowed and relation.target in allowed
            ]
            return {
                "schema_version": 1, "generated_at": _now(),
                "entities": [node.as_dict() for node in nodes],
                "relations": relations,
                "counts": {
                    "entities": len(self._entities), "visible": len(nodes),
                    "relations": len(self._relations),
                },
            }


class PerformanceGovernor:
    """Compatibility wrapper around the adaptive rendering controller."""

    def __init__(self) -> None:
        self._controller = AdaptivePerformanceController()

    def set_mode(self, mode: str) -> str:
        return self._controller.set_mode(mode)

    def sample(self) -> PerformanceSnapshot:
        payload = self._controller.snapshot()
        return PerformanceSnapshot(
            payload.get("cpu_percent"),
            payload.get("memory_percent"),
            None,
            str(payload.get("quality", "balanced")),
            str(payload.get("mode", "foreground")),
        )

    def detail(self) -> dict[str, object]:
        return self._controller.snapshot()

def _safe_window_dict(window: Mapping[str, object]) -> dict[str, object]:
    allowed = ("handle", "title", "process_id", "rect", "visible", "minimized", "presentation", "embedded")
    return {key: window.get(key) for key in allowed if key in window}


class NeuralWorldBridgeMixin:
    def neural_world_snapshot(self, limit: int = 1800) -> dict[str, object]:
        now = time.monotonic()
        if now - self._last_discovery >= 8.0:
            try:
                self._discovery.sync_extended()
            except Exception:
                pass
            self._last_discovery = now
        snapshot = self._neural_world.snapshot(limit=limit)
        try:
            self._refresh_real_windows()
            snapshot["windows"] = []
            for item in self._spatial_windows.list_windows():
                safe = _safe_window_dict(item)
                try:
                    safe["embedded"] = bool(self._spatial_windows.embedding_state(int(item["handle"])).get("embedded", False))
                except Exception:
                    safe["embedded"] = False
                snapshot["windows"].append(safe)
        except (PermissionError, RuntimeError, OSError):
            snapshot["windows"] = []
        snapshot["performance"] = self._performance.detail()
        snapshot["advanced"] = self._advanced.observe_snapshot(snapshot)
        return snapshot

    def gods_eye_globe(self) -> dict[str, object]:
        from .gods_eye_globe import globe_payload
        return globe_payload(self.host.controller.runtime)

    def gods_eye_globe_search(self, query: str) -> dict[str, object]:
        places = self.host.controller.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.search", query=str(query))
        locators = []
        for index, place in enumerate(places or []):
            point = getattr(place, "point", None)
            if point is None:
                continue
            locators.append({
                "id": "search:" + str(index),
                "label": str(getattr(place, "name", "Place"))[:120],
                "latitude": float(point.latitude),
                "longitude": float(point.longitude),
                "kind": "search",
                "authorized": True,
                "accuracy_m": None,
                "source": str(getattr(place, "provider", ""))[:80],
            })
        return {"schema_version": 1, "locators": locators[:50]}

    def neural_observation_start(self, focus: str = "auto", reason: str = "") -> dict[str, object]:
        return self.host.controller.runtime.neural_observation_start(focus, reason)

    def neural_observation_stop(self) -> dict[str, object]:
        return self.host.controller.runtime.neural_observation_stop()

    def neural_observation_state(self) -> dict[str, object]:
        return self.host.controller.runtime.neural_observation_state()

    def neural_shape_catalog(self) -> list[str]:
        from .neural_shapes import BUILTIN_SHAPES
        return list(BUILTIN_SHAPES) + [item["name"] for item in self._shape_registry.catalog()]

    def neural_shape_library(self) -> list[dict[str, object]]:
        from .neural_shapes import BUILTIN_SHAPES
        return [{"name": name, "builtin": True} for name in BUILTIN_SHAPES] + [
            {"name": item["name"], "builtin": False, "shape": item["shape"]} for item in self._shape_registry.catalog()
        ]

    def neural_shape_save(self, name: str, shape: object) -> dict[str, object]:
        spec = self._shape_registry.save(name, shape)
        return {"name": str(name).strip(), "shape": spec.as_dict(), "saved": True}

    def neural_shape_delete(self, name: str) -> dict[str, object]:
        return {"name": str(name).strip(), "deleted": self._shape_registry.delete(name)}

    def neural_shape_set(self, entity_id: str, shape: object) -> dict[str, object]:
        with self._neural_world._lock:
            entity = self._neural_world._entities.get(str(entity_id))
            if entity is None:
                raise KeyError("unknown neural entity")
            normalized = self._shape_registry.resolve(shape).as_dict()
            entity.shape = normalized
            entity.updated_at = _now()
            if entity.kind is EntityKind.WINDOW and entity.id.startswith("window:"):
                handle = entity.id.split(":", 1)[1]
                try:
                    self._layout.upsert("window:" + handle, shape=normalized)
                except (TypeError, ValueError, OSError):
                    pass
            self._neural_world.events.publish("entity.shape.changed", entity_id=entity.id, payload={"shape": normalized})
            return {"id": entity.id, "shape": normalized}

    def neural_search(self, query: str = "", kind: str | None = None, source: str | None = None, status: str | None = None, lifecycle: str | None = None, connected_to: str | None = None, updated_within_seconds: int | None = None, limit: int = 100) -> list[dict[str, object]]:
        return self._neural_world.search(query, kind=kind, source=source, status=status, lifecycle=lifecycle, connected_to=connected_to, updated_within_seconds=updated_within_seconds, limit=limit)

    def neural_trace(self, start: str, target: str, max_hops: int = 8) -> list[dict[str, object]]:
        return self._neural_world.trace(start, target, max_hops=max_hops)

    def neural_discover(self) -> dict[str, int]:
        result = self._discovery.sync()
        self._last_discovery = time.monotonic()
        return result

    def neural_events(self, sequence: int = 0, limit: int = 500) -> list[dict[str, object]]:
        return self._neural_world.event_snapshot(sequence, limit)

    def neural_world_save(self) -> dict[str, object]:
        return {"ok": self._neural_world.save()}

    def neural_performance(self) -> dict[str, object]:
        return self._performance.sample().as_dict()

    def neural_set_performance_mode(self, mode: str) -> dict[str, object]:
        normalized = self._performance.set_mode(mode)
        try:
            if normalized == "background":
                self.host.controller.runtime.enter_background()
            else:
                self.host.controller.runtime.enter_foreground()
        except Exception:
            pass
        return self._performance.sample().as_dict()

    def spatial_set_host_handle(self, host_handle: int) -> dict[str, object]:
        setter = getattr(self._spatial_windows, "set_host_handle", None)
        if not callable(setter):
            raise RuntimeError("native spatial hosting is unavailable")
        return {"ok": True, "host_handle": setter(int(host_handle))}

    def spatial_window_embedding_state(self, handle: int) -> dict[str, object]:
        return self._spatial_windows.embedding_state(int(handle))

    def spatial_window_embed(self, handle: int, x: int = 24, y: int = 24, width: int = 960, height: int = 640) -> dict[str, object]:
        return self._spatial_windows.embed(int(handle), x=int(x), y=int(y), width=int(width), height=int(height), confirmed=True)

    def spatial_window_unembed(self, handle: int) -> dict[str, object]:
        return self._spatial_windows.unembed(int(handle), confirmed=True)

    def neural_window_state(self, key: str) -> dict[str, object] | None:
        state = self._layout.get(str(key))
        return state.as_dict() if state is not None else None

    def neural_window_set_state(self, key: str, payload: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(payload, Mapping):
            raise TypeError("spatial state payload must be an object")
        state = self._layout.upsert(str(key), **dict(payload))
        self._neural_world.events.publish("window.layout.changed", entity_id=str(key), payload=state.as_dict())
        return state.as_dict()

    def neural_window_list_states(self) -> list[dict[str, object]]:
        return [state.as_dict() for state in self._layout.list()]

    def spatial_windows_catalog(self) -> list[dict[str, object]]:
        try:
            self._refresh_real_windows()
            results = []
            for item in self._spatial_windows.list_windows():
                safe = _safe_window_dict(item)
                try:
                    safe["embedded"] = bool(self._spatial_windows.embedding_state(int(item["handle"])).get("embedded", False))
                except Exception:
                    safe["embedded"] = False
                results.append(safe)
            return results
        except (PermissionError, RuntimeError, OSError):
            return []

    def spatial_window_focus(self, handle: int) -> dict[str, object]:
        self._spatial_windows.focus(int(handle), confirmed=True)
        return {"ok": True, "handle": int(handle)}

    def spatial_window_move_resize(self, handle: int, x: int, y: int, width: int, height: int) -> dict[str, object]:
        self._spatial_windows.move_resize(int(handle), int(x), int(y), int(width), int(height), confirmed=True)
        return {"ok": True, "handle": int(handle), "x": int(x), "y": int(y), "width": int(width), "height": int(height)}

    def spatial_window_visibility(self, handle: int, visible: bool) -> dict[str, object]:
        self._spatial_windows.set_visible(int(handle), bool(visible), confirmed=True)
        return {"ok": True, "handle": int(handle), "visible": bool(visible)}

    def spatial_unembed_all(self) -> dict[str, object]:
        method = getattr(self._spatial_windows, "unembed_all", None)
        if not callable(method):
            return {"ok": False, "results": []}
        return {"ok": True, "results": method(confirmed=True)}

    def spatial_window_capture(self, handle: int, max_width: int = 720) -> dict[str, object]:
        return {"ok": True, "handle": int(handle), "png_base64": self._spatial_windows.capture_png(int(handle), max_width=max_width)}

    def neural_advanced_snapshot(self) -> dict[str, object]:
        return self._advanced.snapshot()

    def neural_advanced_feature_status(self) -> dict[str, object]:
        return self._advanced.feature_status()

    def neural_advanced_tick(self, dt: float = 0.016, activity: float = 0.5) -> dict[str, object]:
        return self._advanced.tick(dt, activity=activity)

    def neural_workspace_command(self, operation: str, payload: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("workspace", operation, payload)

    def neural_cross_application_suggest(self, kind: str, source: str, destinations: list[str]) -> list[dict[str, object]]:
        return self._advanced.cross_app.suggest(kind, source, destinations=destinations)

    def neural_cross_application_transfer(self, kind: str, source: str, destination: str, payload_ref: str = "") -> dict[str, object]:
        return self.neural_advanced_command("cross_application", "transfer", {"kind": kind, "source": source, "destination": destination, "payload_ref": payload_ref or None})

    def neural_performance_sample(self, metrics: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("performance", "sample", dict(metrics))

    def neural_performance_analytics(self) -> dict[str, object]:
        return self._advanced.performance.analytics()

    def neural_profile_learn(self, kind: str, name: str, metrics: Mapping[str, object]) -> dict[str, object]:
        return self._advanced.profile_learning(kind, name, **dict(metrics))

    def neural_display_update(self, display_id: str, state: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("display", "update", {"id": display_id, "state": dict(state)})

    def neural_display_save_layout(self) -> dict[str, object]:
        return self.neural_advanced_command("display", "save", {})

    def neural_history_bookmark(self, name: str, payload: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("history", "bookmark", {"name": name, "payload": dict(payload)})

    def neural_history_snapshot(self, snapshot_id: str, world: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("history", "snapshot", {"id": snapshot_id, "world": dict(world)})

    def neural_time_machine(self, compare_left: str = "", compare_right: str = "", replay_id: str = "") -> dict[str, object]:
        return self.neural_advanced_command("history", "time_machine", {"left": compare_left, "right": compare_right, "replay_id": replay_id})

    def neural_dry_run(self, actions: list[Mapping[str, object]], known_good: Mapping[str, object] | None = None) -> dict[str, object]:
        return self.neural_advanced_command("planning", "dry_run", {"actions": actions, "known_good": known_good})

    def neural_inspect(self) -> dict[str, object]:
        return self._advanced.inspect()

    def neural_simulation_run(self, scenario: str, count: int = 1000) -> dict[str, object]:
        return self.neural_advanced_command("simulation", "benchmark", {"scenario": scenario, "count": count})

    def neural_reliability_event(self, event: str, region: str = "") -> dict[str, object]:
        if event == "sleep": return self._advanced.reliability.sleep()
        if event == "wake": return self._advanced.reliability.wake()
        if event == "monitor_change": return self._advanced.reliability.monitor_changed()
        if event in {"reset", "region_reset"}: return self._advanced.reliability.reset(region or None)
        raise ValueError("unknown reliability event")

    def neural_accessibility_update(self, settings: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("accessibility", "update", dict(settings))

    def neural_audio_event(self, kind: str, source: str = "jarvis", position: list[float] | None = None, intensity: float = 0.5, priority: float = 0.5) -> dict[str, object]:
        return self.neural_advanced_command("audio", "event", {"kind": kind, "source": source, "position": position, "intensity": intensity, "priority": priority})

    def neural_audio_policy(self, game_active: bool = False, performance_pressure: float = 0.0) -> dict[str, object]:
        return self.neural_advanced_command("audio", "policy", {"game_active": game_active, "performance_pressure": performance_pressure})

    def neural_multiuser_profile(self, user_id: str, preferences: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("multi_user", "profile", {"id": user_id, "preferences": dict(preferences)})

    def neural_multiuser_region(self, region_id: str, owner: str, shared: bool = False, members: list[str] | None = None) -> dict[str, object]:
        return self.neural_advanced_command("multi_user", "region", {"id": region_id, "owner": owner, "shared": shared, "members": members or []})

    def neural_remote_region(self, region_id: str, state: Mapping[str, object]) -> dict[str, object]:
        return self.neural_advanced_command("remote", "upsert", {"id": region_id, "state": dict(state)})

    def neural_stream_region(self, region_id: str, priority: float = 0.5) -> dict[str, object]:
        return self.neural_advanced_command("streaming", "request", {"id": region_id, "priority": priority})

    def neural_stream_pump(self, budget: int = 4) -> dict[str, object]:
        return self.neural_advanced_command("streaming", "pump", {"budget": budget})

    def neural_advanced_snapshot_from_world(self) -> dict[str, object]:
        return self._advanced.snapshot()


    def neural_advanced_command(self, domain: str, operation: str, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        data = dict(payload or {})
        required = {
            "workspace": Capability.WINDOW_CONTROL,
            "core": Capability.SYSTEM_DIAGNOSTICS,
            "performance": Capability.SYSTEM_DIAGNOSTICS,
            "audio": Capability.SYSTEM_DIAGNOSTICS,
            "streaming": Capability.SYSTEM_DIAGNOSTICS,
            "remote": Capability.SYSTEM_DIAGNOSTICS,
            "simulation": Capability.SYSTEM_DIAGNOSTICS,
            "planning": Capability.SYSTEM_DIAGNOSTICS,
            "fluid": Capability.SYSTEM_DIAGNOSTICS,
            "cross_application": Capability.FILE_WRITE,
            "browser": Capability.BROWSER_CONTROL,
            "game": Capability.APP_WRITE,
            "display": Capability.SYSTEM_SETTINGS,
            "history": Capability.FILE_WRITE,
            "reliability": Capability.SYSTEM_MAINTENANCE,
            "accessibility": Capability.SYSTEM_SETTINGS,
            "multi_user": Capability.ACCOUNT_WRITE,
            "fullstack": Capability.SYSTEM_DIAGNOSTICS,
        }.get(str(domain))
        if required is not None:
            self.host.controller.runtime.policy.check(required)
        if str(domain) == "fullstack":
            nested = str(data.get("domain", "core_neural"))
            nested_operation = str(data.get("operation", ""))
            nested_required = {
                "spatial_windows": Capability.WINDOW_CONTROL,
                "desktop_3d": Capability.WINDOW_CONTROL,
                "cross_application": Capability.FILE_WRITE,
                "browser": Capability.BROWSER_CONTROL,
                "games": Capability.APP_WRITE,
                "performance": Capability.SYSTEM_DIAGNOSTICS,
                "performance_intelligence": Capability.SYSTEM_DIAGNOSTICS,
                "advanced_analytics": Capability.SYSTEM_DIAGNOSTICS,
                "optimization_intelligence": Capability.SYSTEM_DIAGNOSTICS,
                "hardware_display": Capability.SYSTEM_SETTINGS,
                "multi_monitor": Capability.SYSTEM_SETTINGS,
                "memory_history": Capability.FILE_WRITE,
                "time_machine": Capability.FILE_WRITE,
                "world_streaming": Capability.SYSTEM_DIAGNOSTICS,
                "remote": Capability.SYSTEM_DIAGNOSTICS,
                "remote_computing": Capability.PROCESS_CONTROL if nested_operation in {"control", "remote_control"} else Capability.SYSTEM_DIAGNOSTICS,
                "xr": Capability.SYSTEM_SETTINGS,
                "xr_full": Capability.SYSTEM_SETTINGS,
                "accessibility": Capability.SYSTEM_SETTINGS,
                "accessibility_full": Capability.SYSTEM_SETTINGS,
                "multi_user": Capability.ACCOUNT_WRITE,
                "multi_user_shared": Capability.ACCOUNT_WRITE,
                "simulation": Capability.SYSTEM_DIAGNOSTICS,
                "simulation_world": Capability.SYSTEM_DIAGNOSTICS,
                "large_world_proof": Capability.SYSTEM_DIAGNOSTICS,
                "testing": Capability.SYSTEM_DIAGNOSTICS,
                "developer_tools": Capability.SYSTEM_DIAGNOSTICS,
                "core_neural": Capability.SYSTEM_DIAGNOSTICS,
                "lifecycle": Capability.SYSTEM_DIAGNOSTICS,
                "search_navigation": Capability.SYSTEM_DIAGNOSTICS,
                "reliability": Capability.SYSTEM_MAINTENANCE,
            }.get(nested)
            if nested_required is not None:
                self.host.controller.runtime.policy.check(nested_required)
        return self._neural_world.neural_advanced_command(domain, operation, data)

    def _refresh_real_windows(self) -> None:
        for window in self._spatial_windows.list_windows():
            handle = str(window.get("handle"))
            title = str(window.get("title") or "Window")
            node = self._neural_world.upsert(
                f"window:{handle}", EntityKind.WINDOW, title, source="windows",
                status="active", lifecycle=LifecycleState.ACTIVE,
                energy=0.65, scale=0.9, metadata=_safe_window_dict(window),
            )
            title_folded = title.casefold()
            subsystem = "jarvis.browser" if any(x in title_folded for x in ("opera", "edge", "chrome", "firefox", "browser")) else "jarvis.system"
            self._neural_world.relate(subsystem, node.id, "hosts_window", 0.55)


def install(desktop_module: Any) -> None:
    from .spatial_windows import SpatialWindowManager, SpatialWindowUnavailable
    base_api = desktop_module.JarvisWebApi

    class NeuralWorldWebApi(NeuralWorldBridgeMixin, base_api):
        def __init__(self, host: Any) -> None:
            super().__init__(host)
            self._neural_world = NeuralWorld(persistence=NeuralPersistence())
            self._advanced = self._neural_world.advanced
            self._performance = PerformanceGovernor()
            self._layout = SpatialLayoutStore()
            self._shape_registry = self._neural_world.shape_registry
            self._discovery = NeuralDiscovery(self._neural_world, host.controller.runtime)
            self._last_discovery = 0.0
            try:
                host.controller.runtime.set_neural_world_service(self._neural_world)
                host.controller.runtime.set_neural_event_sink(self._neural_world.events.publish)
            except Exception:
                pass
            try:
                policy = host.controller.runtime.policy
            except Exception:
                from .permissions import CapabilityPolicy
                policy = CapabilityPolicy()
            try:
                self._spatial_windows = SpatialWindowManager(policy)
            except SpatialWindowUnavailable:
                self._spatial_windows = _UnavailableSpatialWindows()

    desktop_module.JarvisWebApi = NeuralWorldWebApi


class _UnavailableSpatialWindows:
    def list_windows(self) -> list[dict[str, object]]:
        return []
    def embedding_state(self, *_args: Any, **_kwargs: Any) -> dict[str, object]:
        return {"embedded": False}
    def embed(self, *_args: Any, **_kwargs: Any) -> dict[str, object]:
        raise RuntimeError("native spatial windows unavailable")
    def unembed(self, *_args: Any, **_kwargs: Any) -> dict[str, object]:
        raise RuntimeError("native spatial windows unavailable")
    def unembed_all(self, *_args: Any, **_kwargs: Any) -> list[dict[str, object]]:
        return []
    def focus(self, *_args: Any, **_kwargs: Any) -> bool:
        raise RuntimeError("native spatial windows unavailable")
    def move_resize(self, *_args: Any, **_kwargs: Any) -> bool:
        raise RuntimeError("native spatial windows unavailable")
    def set_visible(self, *_args: Any, **_kwargs: Any) -> bool:
        raise RuntimeError("native spatial windows unavailable")
    def capture_png(self, *_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("native spatial windows unavailable")
