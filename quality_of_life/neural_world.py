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
        ):
            node = self.upsert(
                entity_id, EntityKind.SUBSYSTEM, label, source="jarvis",
                parent_id=core.id, energy=0.6, scale=1.35,
            )
            self.relate(core.id, node.id, "subsystem", 0.95)

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
        domain_name = str(domain)
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
        }.get(domain_name)
        if required is not None:
            self.host.controller.runtime.policy.check(required)
        if domain_name == "fullstack":
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
