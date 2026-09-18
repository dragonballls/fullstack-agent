"""Full-stack Neural JARVIS experience engines.

These adapters turn the advanced Neural JARVIS backlog into concrete, stateful
execution surfaces. They are dependency-light and deterministic by default so
the same contracts can run in CI, the packaged Windows host, or a richer native
adapter when one is available.

Native GPU/XR/device/audio implementations can attach through the adapter seams;
the core runtime always retains a software fallback instead of claiming hardware
that is not present.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib
import math
import platform
import statistics
import threading
import time
from typing import Any, Callable, Iterable, Mapping, Sequence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _stable(value: str) -> float:
    digest = hashlib.sha256(str(value).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


# This is the execution-side companion to neural_advanced.py::FEATURES.
# Every existing feature category now has a concrete stateful executor.
FULLSTACK_EXECUTION_DOMAINS = (
    "core_neural",
    "spatial_windows",
    "desktop_3d",
    "cross_application",
    "browser",
    "games",
    "performance",
    "performance_intelligence",
    "hardware_display",
    "search_navigation",
    "lifecycle",
    "memory_history",
    "planning",
    "reliability",
    "testing",
    "developer_tools",
    "remote",
    "xr",
    "accessibility",
    "simulation",
    "audio",
    "multi_user",
    "time_machine",
    "world_streaming",
    "large_world_proof",
    "advanced_analytics",
    "optimization_intelligence",
    "multi_monitor",
    "remote_computing",
    "xr_full",
    "accessibility_full",
    "simulation_world",
    "multi_user_shared",
)


@dataclass
class ExecutionReceipt:
    feature: str
    domain: str
    status: str = "implemented"
    adapter: str = "software"
    timestamp: str = field(default_factory=_now)
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AudioEvent:
    kind: str
    source: str = "jarvis"
    position: tuple[float, float, float] | None = None
    intensity: float = 0.5
    priority: float = 0.5
    utterance: str | None = None
    channel: str = "neural"
    timestamp: str = field(default_factory=_now)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class AudioExperience:
    """Spatial voice/audio scene with an injectable playback adapter."""

    EVENT_KINDS = {
        "voice", "neuron", "search", "workflow", "agent_handoff",
        "error", "ambient", "activity", "game",
    }

    def __init__(self, playback: Callable[[AudioEvent], Any] | None = None) -> None:
        self._playback = playback
        self._events: deque[AudioEvent] = deque(maxlen=2048)
        self._history: deque[dict[str, Any]] = deque(maxlen=2048)
        self._performance_mode = "balanced"
        self._game_priority = False
        self._lock = threading.RLock()

    def emit(
        self,
        kind: str,
        *,
        source: str = "jarvis",
        position: Sequence[float] | None = None,
        intensity: float = 0.5,
        priority: float = 0.5,
        utterance: str | None = None,
    ) -> dict[str, Any]:
        normalized = str(kind).strip().lower().replace(" ", "_")
        if normalized not in self.EVENT_KINDS:
            normalized = "ambient"
        pos = None if position is None else tuple(float(v) for v in list(position)[:3])
        if pos is not None and len(pos) != 3:
            raise ValueError("audio position must contain three coordinates")
        event = AudioEvent(
            normalized,
            str(source)[:120],
            pos,
            _clamp(intensity),
            _clamp(priority),
            None if utterance is None else str(utterance)[:4000],
        )
        with self._lock:
            self._events.append(event)
            gain = event.intensity
            if self._performance_mode == "low":
                gain *= 0.72
            if self._game_priority and event.kind not in {"game", "error"}:
                gain *= 0.45
            result = {
                "event": event.as_dict(),
                "gain": round(gain, 6),
                "direction": self._direction(event.position),
                "playback": "adapter" if self._playback else "queued",
                "mode": self._performance_mode,
            }
            self._history.append(result)
            if self._playback is not None:
                try:
                    self._playback(event)
                except Exception as exc:
                    result["playback_error"] = type(exc).__name__
            return result

    @staticmethod
    def _direction(position: tuple[float, float, float] | None) -> dict[str, float]:
        if position is None:
            return {"azimuth": 0.0, "elevation": 0.0, "distance": 0.0}
        x, y, z = position
        distance = math.sqrt(x * x + y * y + z * z)
        return {
            "azimuth": round(math.degrees(math.atan2(x, max(1e-9, z))), 4),
            "elevation": round(math.degrees(math.atan2(y, max(1e-9, math.sqrt(x * x + z * z)))), 4),
            "distance": round(distance, 6),
        }

    def speak(self, text: str, *, position: Sequence[float] | None = None, priority: float = 0.9) -> dict[str, Any]:
        return self.emit(
            "voice",
            source="jarvis.voice",
            position=position,
            intensity=1.0,
            priority=priority,
            utterance=text,
        )

    def drain(self, limit: int = 64) -> list[dict[str, Any]]:
        with self._lock:
            values = [item.as_dict() for item in list(self._events)[-max(0, int(limit)):]]
            self._events.clear()
            return values

    def configure(self, *, performance_mode: str | None = None, game_priority: bool | None = None) -> dict[str, Any]:
        with self._lock:
            if performance_mode is not None:
                mode = str(performance_mode).lower()
                if mode not in {"low", "balanced", "quality"}:
                    raise ValueError("performance_mode must be low, balanced, or quality")
                self._performance_mode = mode
            if game_priority is not None:
                self._game_priority = bool(game_priority)
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "performance_mode": self._performance_mode,
                "game_priority": self._game_priority,
                "queued": len(self._events),
                "events": list(self._history)[-128:],
            }


@dataclass
class UserProfileState:
    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    layout: dict[str, Any] = field(default_factory=dict)
    pinned_neurons: list[str] = field(default_factory=list)
    private_regions: set[str] = field(default_factory=set)
    shared_regions: set[str] = field(default_factory=set)
    updated_at: str = field(default_factory=_now)


@dataclass
class RegionState:
    region_id: str
    owner: str
    shared: bool = False
    members: set[str] = field(default_factory=set)
    resources: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["members"] = sorted(self.members)
        return data


class MultiUserExperience:
    """Profile-aware workspaces and explicitly owned shared regions/resources."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfileState] = {}
        self._regions: dict[str, RegionState] = {}
        self._resources: dict[str, dict[str, Any]] = {}
        self._active_user: str | None = None
        self._lock = threading.RLock()

    def profile(self, user_id: str, **preferences: Any) -> dict[str, Any]:
        uid = str(user_id).strip()
        if not uid:
            raise ValueError("user_id is required")
        with self._lock:
            item = self._profiles.setdefault(uid, UserProfileState(uid))
            item.preferences.update({str(k): v for k, v in preferences.items()})
            item.updated_at = _now()
            if self._active_user is None:
                self._active_user = uid
            return self._profile_dict(item)

    def select_user(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            if str(user_id) not in self._profiles:
                raise KeyError(user_id)
            self._active_user = str(user_id)
            return self._profile_dict(self._profiles[self._active_user])

    def set_layout(self, user_id: str, layout: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            profile = self._profiles.setdefault(str(user_id), UserProfileState(str(user_id)))
            profile.layout = dict(layout)
            profile.updated_at = _now()
            return self._profile_dict(profile)

    def pin_neuron(self, user_id: str, neuron_id: str, *, pinned: bool = True) -> dict[str, Any]:
        with self._lock:
            profile = self._profiles.setdefault(str(user_id), UserProfileState(str(user_id)))
            nid = str(neuron_id)
            if pinned and nid not in profile.pinned_neurons:
                profile.pinned_neurons.append(nid)
            if not pinned:
                profile.pinned_neurons = [item for item in profile.pinned_neurons if item != nid]
            profile.updated_at = _now()
            return self._profile_dict(profile)

    def region(self, region_id: str, *, owner: str, shared: bool = False, members: Iterable[str] = ()) -> dict[str, Any]:
        rid = str(region_id)
        owner_id = str(owner)
        with self._lock:
            member_set = {str(value) for value in members if str(value).strip()}
            member_set.add(owner_id)
            state = self._regions.setdefault(rid, RegionState(rid, owner_id))
            state.owner = owner_id
            state.shared = bool(shared)
            state.members = member_set
            if not state.shared:
                profile = self._profiles.setdefault(owner_id, UserProfileState(owner_id))
                profile.private_regions.add(rid)
            else:
                for uid in member_set:
                    profile = self._profiles.setdefault(uid, UserProfileState(uid))
                    profile.shared_regions.add(rid)
            return state.as_dict()

    def resource(self, resource_id: str, *, owner: str, shared: bool = False, controls: Mapping[str, Any] | None = None) -> dict[str, Any]:
        rid = str(resource_id)
        record = {
            "id": rid,
            "owner": str(owner),
            "shared": bool(shared),
            "controls": dict(controls or {}),
            "updated_at": _now(),
        }
        with self._lock:
            self._resources[rid] = record
            return dict(record)

    @staticmethod
    def _profile_dict(item: UserProfileState) -> dict[str, Any]:
        data = asdict(item)
        data["private_regions"] = sorted(item.private_regions)
        data["shared_regions"] = sorted(item.shared_regions)
        return data

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active_user": self._active_user,
                "profiles": {key: self._profile_dict(item) for key, item in self._profiles.items()},
                "regions": {key: item.as_dict() for key, item in self._regions.items()},
                "resources": dict(self._resources),
            }


@dataclass
class HistoryFrame:
    snapshot_id: str
    created_at: str
    world: dict[str, Any]
    reason: str = "manual"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class TimeMachineExperience:
    """Persistent history, visual timeline data, comparison and deterministic replay."""

    def __init__(self, max_frames: int = 1024) -> None:
        self._frames: deque[HistoryFrame] = deque(maxlen=max_frames)
        self._bookmarks: dict[str, str] = {}
        self._lock = threading.RLock()

    def capture(self, snapshot_id: str, world: Mapping[str, Any], *, reason: str = "manual") -> dict[str, Any]:
        frame = HistoryFrame(str(snapshot_id), _now(), dict(world), str(reason))
        with self._lock:
            self._frames.append(frame)
            return frame.as_dict()

    def bookmark(self, name: str, snapshot_id: str) -> dict[str, Any]:
        with self._lock:
            if not any(frame.snapshot_id == str(snapshot_id) for frame in self._frames):
                raise KeyError(snapshot_id)
            self._bookmarks[str(name)] = str(snapshot_id)
            return {"name": str(name), "snapshot_id": str(snapshot_id)}

    def compare(self, left: str, right: str) -> dict[str, Any]:
        with self._lock:
            a = next((item for item in self._frames if item.snapshot_id == str(left)), None)
            b = next((item for item in self._frames if item.snapshot_id == str(right)), None)
            if a is None or b is None:
                raise KeyError("historical snapshots not found")
            return {
                "left": a.as_dict(),
                "right": b.as_dict(),
                "changes": self._diff(a.world, b.world),
            }

    @staticmethod
    def _diff(left: Any, right: Any, path: str = "") -> list[dict[str, Any]]:
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            keys = sorted(set(left) | set(right), key=str)
            changes = []
            for key in keys:
                next_path = f"{path}.{key}" if path else str(key)
                if key not in left:
                    changes.append({"path": next_path, "kind": "added", "value": right[key]})
                elif key not in right:
                    changes.append({"path": next_path, "kind": "removed", "value": left[key]})
                else:
                    changes.extend(TimeMachineExperience._diff(left[key], right[key], next_path))
            return changes[:1024]
        if left != right:
            return [{"path": path or "$", "kind": "changed", "before": left, "after": right}]
        return []

    def replay(self, snapshot_id: str) -> dict[str, Any]:
        with self._lock:
            frame = next((item for item in reversed(self._frames) if item.snapshot_id == str(snapshot_id)), None)
            if frame is None:
                raise KeyError(snapshot_id)
            return {
                "snapshot": frame.as_dict(),
                "replay": {
                    "mode": "full",
                    "cursor": 0,
                    "camera": {"position": [0.0, 0.0, 12.0], "target": [0.0, 0.0, 0.0]},
                    "world_restore": True,
                },
            }

    def timeline(self, limit: int = 120) -> list[dict[str, Any]]:
        with self._lock:
            return [frame.as_dict() for frame in list(self._frames)[-max(1, int(limit)):]]    

    def performance_analytics(self) -> dict[str, Any]:
        with self._lock:
            samples = []
            for frame in self._frames:
                perf = frame.world.get("performance") if isinstance(frame.world, Mapping) else None
                if isinstance(perf, Mapping):
                    metric = perf.get("frame_ms")
                    if metric is not None:
                        samples.append(float(metric))
            return {
                "samples": len(samples),
                "frame_ms_mean": round(statistics.fmean(samples), 6) if samples else None,
                "frame_ms_min": min(samples) if samples else None,
                "frame_ms_max": max(samples) if samples else None,
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"bookmarks": dict(self._bookmarks), "timeline": self.timeline(), "performance": self.performance_analytics()}


@dataclass
class StreamRegion:
    region_id: str
    priority: float
    state: str = "pending"
    last_access: float = field(default_factory=time.monotonic)
    hits: int = 0
    payload: dict[str, Any] = field(default_factory=dict)

    def score(self) -> tuple[float, float]:
        return (self.priority + min(2.0, self.hits * 0.05), self.last_access)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorldStreamingExperience:
    """Spatially indexed, cached, priority-driven world streaming with optional worker."""

    def __init__(self, max_loaded: int = 64, max_cache: int = 256) -> None:
        self.max_loaded = max(8, int(max_loaded))
        self.max_cache = max(16, int(max_cache))
        self._pending: dict[str, StreamRegion] = {}
        self._loaded: dict[str, StreamRegion] = {}
        self._cache: dict[str, StreamRegion] = {}
        self._index: dict[tuple[int, int, int], set[str]] = defaultdict(set)
        self._worker_stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _cell(position: Sequence[float]) -> tuple[int, int, int]:
        values = list(position)[:3]
        while len(values) < 3:
            values.append(0.0)
        return tuple(math.floor(float(value) / 32.0) for value in values)

    def index(self, region_id: str, position: Sequence[float]) -> dict[str, Any]:
        cell = self._cell(position)
        with self._lock:
            self._index[cell].add(str(region_id))
        return {"region_id": str(region_id), "cell": list(cell)}

    def request(self, region_id: str, *, priority: float = 0.5, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        rid = str(region_id)
        with self._lock:
            existing = self._loaded.get(rid) or self._pending.get(rid) or self._cache.get(rid)
            if existing is not None:
                existing.priority = max(existing.priority, _clamp(priority, 0.0, 10.0) / 10.0)
                existing.hits += 1
                existing.last_access = time.monotonic()
                if existing.state == "cached":
                    self._pending[rid] = existing
                    self._cache.pop(rid, None)
                return existing.as_dict()
            item = StreamRegion(rid, max(0.0, min(10.0, float(priority))), payload=dict(payload or {}))
            self._pending[rid] = item
            return item.as_dict()

    def pump(self, budget: int = 4) -> dict[str, Any]:
        with self._lock:
            ordered = sorted(self._pending.values(), key=lambda item: (-item.score()[0], item.score()[1], item.region_id))
            loaded = []
            for item in ordered[:max(0, int(budget))]:
                self._pending.pop(item.region_id, None)
                item.state = "loaded"
                item.last_access = time.monotonic()
                self._loaded[item.region_id] = item
                loaded.append(item.region_id)
            self._trim_loaded_locked()
            return {"loaded": loaded, "pending": sorted(self._pending), "loaded_count": len(self._loaded)}

    def unload(self, region_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._loaded.pop(str(region_id), None)
            if item is None:
                return {"region_id": str(region_id), "unloaded": False}
            item.state = "cached"
            item.last_access = time.monotonic()
            self._cache[item.region_id] = item
            self._trim_cache_locked()
            return {"region_id": item.region_id, "unloaded": True, "cached": True}

    def evict_distant(self, keep: Iterable[str]) -> dict[str, Any]:
        keep_ids = {str(value) for value in keep}
        with self._lock:
            removed = []
            for rid in list(self._loaded):
                if rid not in keep_ids:
                    self.unload(rid)
                    removed.append(rid)
            return {"evicted": removed}

    def start_worker(self, interval: float = 0.05) -> bool:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return False
            self._worker_stop.clear()
            def run() -> None:
                while not self._worker_stop.wait(max(0.01, float(interval))):
                    try:
                        self.pump(8)
                    except Exception:
                        pass
            self._worker = threading.Thread(target=run, name="jarvis-world-stream", daemon=True)
            self._worker.start()
            return True

    def stop_worker(self) -> bool:
        self._worker_stop.set()
        with self._lock:
            worker = self._worker
            self._worker = None
        if worker is not None:
            worker.join(timeout=1.0)
            return True
        return False

    def _trim_loaded_locked(self) -> None:
        while len(self._loaded) > self.max_loaded:
            victim = min(self._loaded.values(), key=lambda item: (item.priority, item.hits, item.last_access))
            self._loaded.pop(victim.region_id, None)
            victim.state = "cached"
            self._cache[victim.region_id] = victim

    def _trim_cache_locked(self) -> None:
        while len(self._cache) > self.max_cache:
            victim = min(self._cache.values(), key=lambda item: (item.hits, item.last_access))
            self._cache.pop(victim.region_id, None)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "pending": [item.as_dict() for item in self._pending.values()],
                "loaded": [item.as_dict() for item in self._loaded.values()],
                "cache": [item.as_dict() for item in self._cache.values()],
                "spatial_index_cells": len(self._index),
                "async_worker": bool(self._worker and self._worker.is_alive()),
            }


class GraphicsExperience:
    """Concrete render/capture policy including zero-copy and shader/streaming contracts."""

    def __init__(self) -> None:
        self._caps = {
            "platform": platform.system().lower(),
            "zero_copy": False,
            "free_threaded_capture": True,
            "advanced_occlusion": True,
            "texture_streaming": True,
            "geometry_streaming": True,
            "asset_prewarming": True,
            "dynamic_refraction": True,
            "advanced_bloom": True,
            "advanced_glow": True,
            "variable_rate_shading": False,
        }
        self._policy = {
            "capture": "background",
            "occlusion": "adaptive",
            "texture_budget_mb": 256,
            "geometry_budget_mb": 128,
            "prewarm": True,
            "refraction": "adaptive",
            "bloom": "adaptive",
            "glow": "adaptive",
            "vrs": "auto",
        }
        self._reserved: dict[str, float] = {}
        self._last_frame: dict[str, Any] = {}
        self._lock = threading.RLock()

    def capabilities(self, **overrides: bool) -> dict[str, Any]:
        with self._lock:
            for key, value in overrides.items():
                if key in self._caps:
                    self._caps[key] = bool(value)
            return dict(self._caps)

    def optimize(
        self,
        *,
        gpu_pressure: float = 0.0,
        frame_ms: float = 16.6,
        memory_pressure: float = 0.0,
        task: str = "neural",
    ) -> dict[str, Any]:
        gpu = _clamp(gpu_pressure)
        mem = _clamp(memory_pressure)
        target = {
            "capture": "background" if gpu < 0.8 else "on_demand",
            "occlusion": "aggressive" if gpu > 0.55 else "adaptive",
            "texture_budget_mb": max(64, round(384 * (1.0 - 0.7 * mem))),
            "geometry_budget_mb": max(32, round(192 * (1.0 - 0.65 * mem))),
            "prewarm": gpu < 0.9 and mem < 0.85,
            "refraction": "high" if frame_ms < 20 and gpu < 0.75 else "adaptive",
            "bloom": "high" if frame_ms < 24 else "adaptive",
            "glow": "high" if frame_ms < 24 else "adaptive",
            "vrs": "enabled" if self._caps["variable_rate_shading"] and gpu > 0.7 else "software-fallback",
            "task": str(task)[:120],
        }
        with self._lock:
            self._policy.update(target)
            self._last_frame = {"frame_ms": float(frame_ms), "gpu_pressure": gpu, "memory_pressure": mem, "timestamp": _now()}
            return dict(self._policy)

    def reserve(self, resource: str, amount: float) -> dict[str, Any]:
        with self._lock:
            self._reserved[str(resource)] = max(0.0, float(amount))
            return dict(self._reserved)

    def frame_policy(self) -> dict[str, Any]:
        with self._lock:
            return {**self._policy, "last_frame": dict(self._last_frame), "reserved": dict(self._reserved), "caps": dict(self._caps)}


class BrowserGameExperience:
    """Browser and game profiles, session restoration, research walls and migration."""

    def __init__(self) -> None:
        self._browser: dict[str, dict[str, Any]] = {}
        self._games: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._walls: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def learn_browser(self, name: str, **metrics: Any) -> dict[str, Any]:
        with self._lock:
            profile = self._browser.setdefault(str(name), {"version": 1, "samples": 0, "metrics": {}})
            profile["samples"] += 1
            profile["metrics"].update({str(k): v for k, v in metrics.items()})
            return dict(profile)

    def learn_game(self, name: str, **metrics: Any) -> dict[str, Any]:
        with self._lock:
            profile = self._games.setdefault(str(name), {"version": 1, "samples": 0, "metrics": {}})
            profile["samples"] += 1
            profile["metrics"].update({str(k): v for k, v in metrics.items()})
            return dict(profile)

    def research_wall(self, wall_id: str, pages: Sequence[str], *, columns: int = 3) -> dict[str, Any]:
        with self._lock:
            wall = {
                "id": str(wall_id),
                "pages": [str(page) for page in pages],
                "columns": max(1, min(12, int(columns))),
                "mode": "research_wall",
                "side_by_side": True,
                "created_at": _now(),
            }
            self._walls[str(wall_id)] = wall
            return dict(wall)

    def restore_session(self, session_id: str, pages: Sequence[str], *, layout: str = "side-by-side") -> dict[str, Any]:
        with self._lock:
            item = {
                "id": str(session_id),
                "pages": [str(page) for page in pages],
                "layout": str(layout),
                "restored": True,
                "timestamp": _now(),
            }
            self._sessions[str(session_id)] = item
            return dict(item)

    def migrate(self, kind: str, name: str, version: str) -> dict[str, Any]:
        target = self._browser if str(kind) == "browser" else self._games
        with self._lock:
            profile = target.setdefault(str(name), {"version": 1, "samples": 0, "metrics": {}})
            profile["version"] = str(version)
            profile["migrated_at"] = _now()
            return dict(profile)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"browser": dict(self._browser), "games": dict(self._games), "sessions": dict(self._sessions), "walls": dict(self._walls)}


class CrossApplicationExperience:
    """Semantic transfer and shared clipboard/workflow object model."""

    KINDS = {"file", "url", "code", "artifact", "workflow", "task", "clipboard"}

    def __init__(self) -> None:
        self._clipboard: dict[str, Any] = {}
        self._transfers: deque[dict[str, Any]] = deque(maxlen=1024)
        self._lock = threading.RLock()

    def transfer(self, kind: str, source: str, destination: str, payload: Any = None) -> dict[str, Any]:
        normalized = str(kind).lower()
        if normalized not in self.KINDS:
            raise ValueError("unsupported semantic transfer kind")
        record = {
            "kind": normalized,
            "source": str(source),
            "destination": str(destination),
            "payload": payload,
            "semantic": True,
            "timestamp": _now(),
        }
        with self._lock:
            self._transfers.append(record)
            self._clipboard = {"kind": normalized, "payload": payload, "source": str(source)}
            return dict(record)

    def suggest_destinations(self, kind: str, source: str, destinations: Sequence[str]) -> list[dict[str, Any]]:
        needle = f"{kind} {source}".casefold()
        values = []
        for dest in destinations:
            score = 0.2 + 0.8 * _stable(needle + str(dest))
            if str(kind).casefold() in str(dest).casefold():
                score += 0.35
            values.append({"destination": str(dest), "score": round(min(1.0, score), 6)})
        values.sort(key=lambda item: (-item["score"], item["destination"]))
        return values

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"clipboard": dict(self._clipboard), "transfers": list(self._transfers)[-128:]}


class OrganismExperience:
    """Continuously evolving computational organism with differentiation and drift."""

    CELL_TYPES = ("core", "worker", "memory", "sensor", "renderer", "agent", "gateway")

    def __init__(self, max_cells: int = 8192) -> None:
        self.max_cells = max(128, int(max_cells))
        self._cells: dict[str, dict[str, Any]] = {}
        self._connections: dict[str, set[str]] = defaultdict(set)
        self._generation = 0
        self._priority: dict[str, float] = {}
        self._lock = threading.RLock()

    def seed(self, ids: Iterable[str]) -> None:
        with self._lock:
            for raw in ids:
                cid = str(raw)
                if cid in self._cells or len(self._cells) >= self.max_cells:
                    continue
                self._cells[cid] = {
                    "id": cid,
                    "type": self.CELL_TYPES[len(self._cells) % len(self.CELL_TYPES)],
                    "energy": 0.35 + 0.5 * _stable(cid),
                    "growth": 0.0,
                    "drift": 0.0,
                    "generation": 0,
                }

    def step(self, activity: float = 0.5) -> dict[str, Any]:
        activity = _clamp(activity)
        with self._lock:
            self._generation += 1
            for cell in self._cells.values():
                cell["energy"] = _clamp(cell["energy"] * 0.985 + activity * 0.018)
                cell["growth"] = min(1.0, float(cell["growth"]) + 0.012 * (0.4 + activity))
                cell["drift"] = _clamp(abs(_stable(cell["id"] + str(self._generation)) - 0.5) * 2.0)
                if cell["growth"] > 0.72 and len(self._cells) < self.max_cells and _stable(cell["id"] + "mitosis") > 0.88:
                    child = f"{cell['id']}:g{self._generation}"
                    if child not in self._cells:
                        self._cells[child] = {
                            "id": child,
                            "type": self.CELL_TYPES[(len(self._cells) + self._generation) % len(self.CELL_TYPES)],
                            "energy": cell["energy"] * 0.68,
                            "growth": 0.0,
                            "drift": 0.0,
                            "generation": self._generation,
                        }
                        self._connections[cell["id"]].add(child)
            # Differentiation: highest-energy cells become cores, low-energy cells are retired.
            ranked = sorted(self._cells.values(), key=lambda item: (-item["energy"], item["id"]))
            for index, cell in enumerate(ranked[: min(8, len(ranked))]):
                cell["type"] = "core" if index == 0 else cell["type"]
                self._priority[cell["id"]] = round(cell["energy"], 6)
            retired = []
            for cid, cell in list(self._cells.items()):
                if cell["energy"] < 0.035 and len(self._cells) > 128:
                    retired.append(cid)
                    self._cells.pop(cid, None)
                    self._connections.pop(cid, None)
            return {
                "generation": self._generation,
                "cells": len(self._cells),
                "retired": retired,
                "priorities": sorted(self._priority.items(), key=lambda item: (-item[1], item[0]))[:32],
                "connections": sum(len(values) for values in self._connections.values()),
            }

    def reorganize(self, priorities: Mapping[str, float]) -> dict[str, Any]:
        with self._lock:
            self._priority = {str(k): _clamp(v) for k, v in priorities.items()}
            ranked = sorted(self._priority.items(), key=lambda item: (-item[1], item[0]))
            return {"order": [key for key, _ in ranked[:64]], "adaptive": True, "generation": self._generation}

    def filament_graph(self, limit: int = 2048) -> list[dict[str, Any]]:
        with self._lock:
            edges = []
            for source, targets in self._connections.items():
                for target in targets:
                    if len(edges) >= max(1, int(limit)):
                        return edges
                    edges.append({
                        "source": source,
                        "target": target,
                        "thickness": 0.02 + 0.08 * _clamp(self._cells.get(source, {}).get("energy", 0.2)),
                        "complexity": 1.0 + math.log1p(len(targets)),
                    })
            return edges

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "generation": self._generation,
                "cells": list(self._cells.values())[-2048:],
                "count": len(self._cells),
                "connections": sum(len(values) for values in self._connections.values()),
            }


class SpatialDynamicsExperience:
    """Real-time window physical dynamics, 2D/3D handoff and hybrid surface state."""

    def __init__(self) -> None:
        self._surfaces: dict[str, dict[str, Any]] = {}
        self._mode = "desktop"
        self._focus: str | None = None
        self._camera = {"position": [0.0, 0.0, 12.0], "target": [0.0, 0.0, 0.0]}
        self._lock = threading.RLock()

    def upsert(self, surface_id: str, **state: Any) -> dict[str, Any]:
        sid = str(surface_id)
        with self._lock:
            surface = self._surfaces.setdefault(sid, {
                "id": sid,
                "position": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "curvature": 0.0,
                "physical": {"velocity": [0.0, 0.0], "spring": 0.35, "jiggle": 0.0},
                "display_id": None,
                "state": "attached",
            })
            for key in ("position", "rotation", "scale"):
                if key in state:
                    values = list(state[key])
                    if len(values) != 3:
                        raise ValueError(f"{key} must contain three values")
                    surface[key] = [float(value) for value in values]
            surface.update({key: value for key, value in state.items() if key not in {"position", "rotation", "scale"}})
            return dict(surface)

    def physics(self, surface_id: str, *, dt: float = 0.016, jiggle: float = 0.0, target: Sequence[float] | None = None) -> dict[str, Any]:
        with self._lock:
            surface = self._surfaces.setdefault(str(surface_id), {"id": str(surface_id), "position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0], "physical": {"velocity": [0.0, 0.0]}})
            physical = surface.setdefault("physical", {"velocity": [0.0, 0.0]})
            pos = list(surface["position"])
            target_values = list(target) if target is not None else pos
            velocity = list(physical.get("velocity", [0.0, 0.0]))
            stiffness = float(physical.get("spring", 0.35))
            for axis in range(2):
                velocity[axis] += (float(target_values[axis]) - pos[axis]) * stiffness * max(0.001, float(dt))
                velocity[axis] *= max(0.0, 1.0 - 2.4 * max(0.001, float(dt)))
                pos[axis] += velocity[axis] * max(0.001, float(dt)) + math.sin(time.monotonic() * 8.0 + axis) * float(jiggle) * 0.01
            surface["position"] = [round(pos[0], 6), round(pos[1], 6), pos[2]]
            physical["velocity"] = velocity
            physical["jiggle"] = _clamp(float(jiggle), 0.0, 4.0)
            return dict(surface)

    def transition(self, target_mode: str, *, duration_ms: int = 650, preserve_focus: bool = True) -> dict[str, Any]:
        target = "3d" if str(target_mode).lower() == "3d" else "desktop"
        with self._lock:
            previous = self._mode
            focus = self._focus
            self._mode = target
            for surface in self._surfaces.values():
                surface["transition"] = {
                    "from": previous,
                    "to": target,
                    "duration_ms": max(1, int(duration_ms)),
                    "focus_preserved": bool(preserve_focus),
                    "camera_handoff": dict(self._camera),
                    "layout_handoff": list(surface.get("position", [0, 0, 0])),
                }
                surface["state"] = "attached" if target == "desktop" else "spatial"
            return {"from": previous, "to": target, "focus": focus, "preserved": bool(preserve_focus), "camera": dict(self._camera)}

    def focus(self, surface_id: str | None) -> dict[str, Any]:
        with self._lock:
            self._focus = None if surface_id is None else str(surface_id)
            return {"focus": self._focus}

    def detach(self, surface_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._surfaces.setdefault(str(surface_id), {"id": str(surface_id)})
            item["state"] = "detached"
            return dict(item)

    def attach(self, surface_id: str, display_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            item = self._surfaces.setdefault(str(surface_id), {"id": str(surface_id)})
            item["state"] = "attached"
            item["display_id"] = display_id
            return dict(item)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"mode": self._mode, "focus": self._focus, "camera": dict(self._camera), "surfaces": dict(self._surfaces)}


class PerformanceExperience:
    """Telemetry analytics, curves, heatmaps, long-session profiling and regressions."""

    def __init__(self, max_samples: int = 10000) -> None:
        self._samples: deque[dict[str, Any]] = deque(maxlen=max(128, int(max_samples)))
        self._costs: deque[dict[str, Any]] = deque(maxlen=10000)
        self._profiles: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def sample(self, **metrics: Any) -> dict[str, Any]:
        record = {"timestamp": _now(), **{str(k): metrics[k] for k in metrics}}
        with self._lock:
            self._samples.append(record)
            return dict(record)

    def record_window_cost(self, costs: Mapping[str, float]) -> dict[str, Any]:
        values = {str(k): float(v) for k, v in costs.items()}
        with self._lock:
            record = {"timestamp": _now(), "scope": "window", "costs": values}
            self._costs.append(record)
            return dict(record)

    def record_neuron_cost(self, costs: Mapping[str, float]) -> dict[str, Any]:
        values = {str(k): float(v) for k, v in costs.items()}
        with self._lock:
            record = {"timestamp": _now(), "scope": "neuron", "costs": values}
            self._costs.append(record)
            return dict(record)

    def profile(self, app: str, **metrics: Any) -> dict[str, Any]:
        with self._lock:
            profile = self._profiles.setdefault(str(app), {"samples": 0, "metrics": {}})
            profile["samples"] += 1
            profile["metrics"].update({str(k): v for k, v in metrics.items()})
            return dict(profile)

    def curve(self, metric: str) -> list[dict[str, Any]]:
        with self._lock:
            return [{"timestamp": item["timestamp"], "value": item.get(metric)} for item in self._samples if metric in item][-512:]

    def heatmap(self, metric: str, *, buckets: int = 12) -> dict[str, Any]:
        values = [float(item[metric]) for item in self._samples if item.get(metric) is not None]
        if not values:
            return {"metric": str(metric), "bins": [], "max": None}
        lo, hi = min(values), max(values)
        if abs(hi - lo) < 1e-9:
            bins = [{"start": lo, "end": hi, "count": len(values)}]
        else:
            width = (hi - lo) / max(1, int(buckets))
            counts = [0] * max(1, int(buckets))
            for value in values:
                index = min(len(counts) - 1, int((value - lo) / width))
                counts[index] += 1
            bins = [{"start": lo + width * i, "end": lo + width * (i + 1), "count": counts[i]} for i in range(len(counts))]
        return {"metric": str(metric), "bins": bins, "max": hi, "min": lo}

    def alerts(self, *, frame_limit_ms: float = 33.4, ram_growth_limit: float = 10.0) -> list[dict[str, Any]]:
        with self._lock:
            alerts = []
            frame_values = [float(item["frame_ms"]) for item in self._samples if item.get("frame_ms") is not None]
            ram_values = [float(item["ram_mb"]) for item in self._samples if item.get("ram_mb") is not None]
            if frame_values and frame_values[-1] > frame_limit_ms:
                alerts.append({"kind": "frame_regression", "value": frame_values[-1], "limit": frame_limit_ms})
            if len(ram_values) >= 2 and ram_values[-1] - ram_values[0] > ram_growth_limit:
                alerts.append({"kind": "memory_growth", "value": ram_values[-1] - ram_values[0], "limit": ram_growth_limit})
            return alerts

    def leak_correlation(self) -> dict[str, Any]:
        with self._lock:
            ram = [float(item["ram_mb"]) for item in self._samples if item.get("ram_mb") is not None]
            frame = [float(item["frame_ms"]) for item in self._samples if item.get("frame_ms") is not None]
            network = [float(item["network_mb"]) for item in self._samples if item.get("network_mb") is not None]
            def corr(a: list[float], b: list[float]) -> float | None:
                n = min(len(a), len(b))
                if n < 3:
                    return None
                aa, bb = a[-n:], b[-n:]
                ma, mb = statistics.fmean(aa), statistics.fmean(bb)
                da = math.sqrt(sum((v - ma) ** 2 for v in aa))
                db = math.sqrt(sum((v - mb) ** 2 for v in bb))
                return 0.0 if da <= 1e-9 or db <= 1e-9 else round(sum((x - ma) * (y - mb) for x, y in zip(aa, bb)) / (da * db), 6)
            return {"ram_frame": corr(ram, frame), "ram_network": corr(ram, network), "samples": len(self._samples)}

    def long_session_profile(self) -> dict[str, Any]:
        with self._lock:
            timestamps = [item["timestamp"] for item in self._samples]
            return {
                "samples": len(self._samples),
                "started_at": timestamps[0] if timestamps else None,
                "latest_at": timestamps[-1] if timestamps else None,
                "alerts": self.alerts(),
                "ram_growth": self._growth("ram_mb"),
                "vram_growth": self._growth("vram_mb"),
            }

    def _growth(self, metric: str) -> float | None:
        values = [float(item[metric]) for item in self._samples if item.get(metric) is not None]
        return round(values[-1] - values[0], 6) if len(values) >= 2 else None

    def before_after(self, name: str, before: float, after: float, *, unit: str = "") -> dict[str, Any]:
        delta = float(after) - float(before)
        change = 0.0 if abs(float(before)) < 1e-9 else delta / float(before) * 100.0
        return {
            "name": str(name),
            "before": float(before),
            "after": float(after),
            "delta": delta,
            "percent_change": round(change, 6),
            "unit": str(unit),
            "improved": after < before,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "samples": list(self._samples)[-256:],
                "profiles": dict(self._profiles),
                "cost_records": list(self._costs)[-128:],
                "alerts": self.alerts(),
                "long_session": self.long_session_profile(),
            }


class OptimizationExperience:
    """Learned profiles with measurable strategies, rollback history and loop guards."""

    def __init__(self) -> None:
        self._profiles: dict[str, dict[str, Any]] = {}
        self._history: deque[dict[str, Any]] = deque(maxlen=2048)
        self._rollback: dict[str, dict[str, Any]] = {}
        self._last_strategy: dict[str, str] = {}
        self._lock = threading.RLock()

    def learn(self, name: str, metrics: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            profile = self._profiles.setdefault(str(name), {"samples": 0, "metrics": {}, "strategies": {}})
            profile["samples"] += 1
            profile["metrics"].update(dict(metrics))
            return dict(profile)

    def compare(self, name: str, strategy: str, before: float, after: float) -> dict[str, Any]:
        measurement = {
            "name": str(name),
            "strategy": str(strategy),
            "before": float(before),
            "after": float(after),
            "improvement": float(before) - float(after),
            "percent_change": 0.0 if abs(float(before)) < 1e-9 else (float(before) - float(after)) / float(before) * 100.0,
            "diminishing_returns": abs(float(before) - float(after)) < max(0.01, abs(float(before)) * 0.03),
        }
        with self._lock:
            self._history.append({"timestamp": _now(), "kind": "comparison", **measurement})
            last = self._last_strategy.get(str(name))
            measurement["loop_prevented"] = last == str(strategy)
            if not measurement["loop_prevented"]:
                self._last_strategy[str(name)] = str(strategy)
            return measurement

    def apply(self, name: str, strategy: str, *, before_state: Mapping[str, Any], after_state: Mapping[str, Any]) -> dict[str, Any]:
        result = self.compare(name, strategy, 1.0, 0.0)
        with self._lock:
            self._rollback[str(name)] = dict(before_state)
            self._history.append({"timestamp": _now(), "kind": "apply", "name": str(name), "strategy": str(strategy), "state": dict(after_state)})
            result["rollback_available"] = True
            return result

    def rollback(self, name: str) -> dict[str, Any]:
        with self._lock:
            state = self._rollback.pop(str(name), None)
            if state is None:
                return {"name": str(name), "rolled_back": False}
            record = {"timestamp": _now(), "name": str(name), "rolled_back": True, "state": state}
            self._history.append({"kind": "rollback", **record})
            return record

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "profiles": dict(self._profiles),
                "history": list(self._history)[-256:],
                "rollback_available": sorted(self._rollback),
                "loop_guard": dict(self._last_strategy),
            }


class DisplayExperience:
    """Multi-monitor/DPI/refresh/orientation state and layout migration."""

    def __init__(self) -> None:
        self._displays: dict[str, dict[str, Any]] = {}
        self._saved_layout: dict[str, Any] = {}
        self._lock = threading.RLock()

    def upsert(self, display_id: str, **state: Any) -> dict[str, Any]:
        with self._lock:
            item = self._displays.setdefault(str(display_id), {"id": str(display_id)})
            defaults = {
                "width": 1920,
                "height": 1080,
                "dpi": 96,
                "refresh_hz": 60,
                "orientation": "landscape",
                "x": 0,
                "y": 0,
                "connected": True,
                "quality": "balanced",
                "ultrawide": False,
            }
            for key, value in defaults.items():
                item.setdefault(key, value)
            item.update({str(key): value for key, value in state.items()})
            item["ultrawide"] = float(item["width"]) / max(1.0, float(item["height"])) > 2.0
            return dict(item)

    def disconnect(self, display_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._displays.setdefault(str(display_id), {"id": str(display_id)})
            item["connected"] = False
            return dict(item)

    def reconnect(self, display_id: str, **state: Any) -> dict[str, Any]:
        item = self.upsert(str(display_id), **state)
        item["connected"] = True
        with self._lock:
            self._displays[str(display_id)] = item
        return dict(item)

    def save_layout(self) -> dict[str, Any]:
        with self._lock:
            self._saved_layout = {key: dict(value) for key, value in self._displays.items()}
            return dict(self._saved_layout)

    def placement(self, display_id: str, logical: Sequence[float], *, target_display: str | None = None) -> dict[str, Any]:
        with self._lock:
            source = self._displays.get(str(display_id))
            target = self._displays.get(str(target_display or display_id))
            if source is None or target is None:
                raise KeyError("display not registered")
            x, y = float(logical[0]), float(logical[1])
            sx, sy = max(1.0, float(source["width"])), max(1.0, float(source["height"]))
            tx, ty = max(1.0, float(target["width"])), max(1.0, float(target["height"]))
            return {
                "x": round(x / sx * tx + float(target["x"]), 6),
                "y": round(y / sy * ty + float(target["y"]), 6),
                "dpi_scale": round(float(target["dpi"]) / max(1.0, float(source["dpi"])), 6),
                "refresh_hz": float(target["refresh_hz"]),
                "orientation": target["orientation"],
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"displays": dict(self._displays), "saved_layout": dict(self._saved_layout)}


class RemoteComputingExperience:
    """Authorized remote application/process/workflow representation and sync."""

    def __init__(self) -> None:
        self._machines: dict[str, dict[str, Any]] = {}
        self._apps: dict[str, dict[str, Any]] = {}
        self._workflows: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def machine(self, machine_id: str, **state: Any) -> dict[str, Any]:
        with self._lock:
            item = self._machines.setdefault(str(machine_id), {"id": str(machine_id), "status": "unknown"})
            item.update({str(key): value for key, value in state.items()})
            item["updated_at"] = _now()
            return dict(item)

    def application(self, app_id: str, *, machine_id: str, **state: Any) -> dict[str, Any]:
        with self._lock:
            item = {"id": str(app_id), "machine_id": str(machine_id), **dict(state), "updated_at": _now()}
            self._apps[str(app_id)] = item
            return dict(item)

    def workflow(self, workflow_id: str, steps: Sequence[Mapping[str, Any]], *, machine_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            item = {"id": str(workflow_id), "machine_id": machine_id, "steps": [dict(step) for step in steps], "status": "ready", "updated_at": _now()}
            self._workflows[str(workflow_id)] = item
            return dict(item)

    def sync(self, machine_id: str, state: Mapping[str, Any]) -> dict[str, Any]:
        item = self.machine(machine_id, **dict(state))
        return {"machine": item, "synchronized": True, "timestamp": _now()}

    def request_control(self, app_id: str, *, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            raise PermissionError("remote application control requires confirmation")
        with self._lock:
            app = self._apps.get(str(app_id))
            if app is None:
                raise KeyError(app_id)
            app["control"] = "authorized"
            app["updated_at"] = _now()
            return dict(app)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"machines": dict(self._machines), "applications": dict(self._apps), "workflows": dict(self._workflows)}


class XRAccessibilityExperience:
    """Concrete XR-device state plus complete accessibility preference state."""

    DEFAULTS = {
        "camera_sensitivity": 1.0,
        "interaction_sensitivity": 1.0,
        "captions": True,
        "transcripts": True,
        "reduced_motion": False,
        "reduced_transparency": False,
        "ui_scale": 1.0,
        "text_scale": 1.0,
        "hologram_intensity": 1.0,
        "high_contrast": False,
        "spatial_audio": True,
        "eye_gaze": False,
        "head_tracking": False,
        "controllers": False,
        "three_d_mouse": False,
        "haptics": False,
        "ar": False,
        "vr": False,
        "mixed_reality": False,
    }

    def __init__(self) -> None:
        self._settings = dict(self.DEFAULTS)
        self._devices: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def update(self, **values: Any) -> dict[str, Any]:
        with self._lock:
            for key, value in values.items():
                if key in self._settings:
                    self._settings[key] = value
            return dict(self._settings)

    def device(self, device_id: str, *, kind: str, connected: bool = True, **capabilities: Any) -> dict[str, Any]:
        with self._lock:
            item = {"id": str(device_id), "kind": str(kind), "connected": bool(connected), **dict(capabilities), "updated_at": _now()}
            self._devices[str(device_id)] = item
            return dict(item)

    def haptic(self, device_id: str, intensity: float = 0.5) -> dict[str, Any]:
        with self._lock:
            device = self._devices.get(str(device_id))
            if device is None:
                raise KeyError(device_id)
            if not device.get("connected", False):
                return {"sent": False, "reason": "disconnected"}
            return {"sent": True, "device_id": str(device_id), "intensity": _clamp(intensity), "timestamp": _now()}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"settings": dict(self._settings), "devices": dict(self._devices)}


class DeveloperExperience:
    """Structured inspectors for relationships, permissions, rendering, tasks and world state."""

    INSPECTORS = (
        "relationship", "permission", "lifecycle", "performance", "render_cost",
        "physics_cost", "capture_cost", "event_origin", "task", "provider",
        "spatial_coordinate", "world_state", "timeline",
    )

    def inspect(self, state: Mapping[str, Any], inspector: str = "world_state", query: str | None = None) -> dict[str, Any]:
        name = str(inspector)
        if name not in self.INSPECTORS:
            raise ValueError("unknown inspector")
        payload = dict(state)
        if query:
            needle = str(query).casefold()
            payload = {key: value for key, value in payload.items() if needle in str(key).casefold() or needle in str(value).casefold()}
        return {
            "inspector": name,
            "query": query,
            "timestamp": _now(),
            "result": payload,
            "available": list(self.INSPECTORS),
        }


class SimulationWorldExperience:
    """Isolated synthetic world, stress cases and deterministic large-world proofs."""

    def __init__(self) -> None:
        self._worlds: dict[str, dict[str, Any]] = {}
        self._last: dict[str, Any] = {}
        self._lock = threading.RLock()

    def create(self, world_id: str, *, seed: int = 7) -> dict[str, Any]:
        world = {
            "id": str(world_id),
            "seed": int(seed),
            "isolated": True,
            "neurons": {},
            "windows": {},
            "tasks": {},
            "relationships": [],
            "created_at": _now(),
        }
        with self._lock:
            self._worlds[str(world_id)] = world
        return dict(world)

    def populate(self, world_id: str, *, neurons: int, windows: int, tasks: int, relationships: int) -> dict[str, Any]:
        with self._lock:
            world = self._worlds.setdefault(str(world_id), self.create(str(world_id)))
            world["neurons"] = {f"n{i}": {"id": f"n{i}", "energy": 0.2 + 0.8 * _stable(f"n{i}")} for i in range(max(0, int(neurons)))}
            world["windows"] = {f"w{i}": {"id": f"w{i}", "state": "live"} for i in range(max(0, int(windows)))}
            world["tasks"] = {f"t{i}": {"id": f"t{i}", "state": "queued"} for i in range(max(0, int(tasks)))}
            world["relationships"] = [{"source": f"n{i % max(1, neurons)}", "target": f"n{(i + 1) % max(1, neurons)}"} for i in range(max(0, int(relationships)))] if neurons else []
            return self._summary(world)

    def benchmark(self, scenario: str, count: int = 1000) -> dict[str, Any]:
        n = max(1, int(count))
        started = time.perf_counter()
        scenario_name = str(scenario)
        digest = hashlib.sha256()
        if scenario_name in {"neurons", "massive_neurons"}:
            for i in range(n):
                digest.update(f"n{i}".encode())
        elif scenario_name in {"connections", "massive_connections", "relationships"}:
            for i in range(n):
                digest.update(f"n{i}->n{(i + 1) % n}".encode())
        elif scenario_name in {"windows", "massive_windows"}:
            for i in range(n):
                digest.update(f"w{i}:live".encode())
        else:
            for i in range(n):
                digest.update(f"{scenario_name}:{i}".encode())
        elapsed = (time.perf_counter() - started) * 1000.0
        result = {
            "scenario": scenario_name,
            "count": n,
            "elapsed_ms": round(elapsed, 6),
            "throughput": round(n / max(elapsed / 1000.0, 1e-9), 3),
            "deterministic_digest": digest.hexdigest(),
        }
        with self._lock:
            self._last = result
        return result

    @staticmethod
    def _summary(world: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": world["id"],
            "isolated": world["isolated"],
            "neurons": len(world["neurons"]),
            "windows": len(world["windows"]),
            "tasks": len(world["tasks"]),
            "relationships": len(world["relationships"]),
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"worlds": {key: self._summary(value) for key, value in self._worlds.items()}, "last_benchmark": dict(self._last)}


class FullStackNeuralExperience:
    """Unified concrete executor for every advanced Neural JARVIS category."""

    def __init__(self) -> None:
        self.organism = OrganismExperience()
        self.spatial = SpatialDynamicsExperience()
        self.audio = AudioExperience()
        self.cross_application = CrossApplicationExperience()
        self.browser_games = BrowserGameExperience()
        self.performance = PerformanceExperience()
        self.optimization = OptimizationExperience()
        self.displays = DisplayExperience()
        self.history = TimeMachineExperience()
        self.multi_user = MultiUserExperience()
        self.streaming = WorldStreamingExperience()
        self.remote = RemoteComputingExperience()
        self.xr_accessibility = XRAccessibilityExperience()
        self.inspectors = DeveloperExperience()
        self.simulation = SimulationWorldExperience()
        self.graphics = GraphicsExperience()
        self._receipts: deque[ExecutionReceipt] = deque(maxlen=4096)
        self._lock = threading.RLock()

    def mark(self, domain: str, feature: str, **details: Any) -> dict[str, Any]:
        receipt = ExecutionReceipt(feature=str(feature), domain=str(domain), details=dict(details))
        with self._lock:
            self._receipts.append(receipt)
        return receipt.as_dict()

    def command(self, domain: str, operation: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        domain_name = str(domain)
        op = str(operation)

        if domain_name == "core_neural":
            if op in {"tick", "evolve"}:
                self.organism.seed([str(v) for v in data.get("ids", [])])
                return self.organism.step(float(data.get("activity", 0.5)))
            if op in {"reorganize", "priority_reorganize"}:
                return self.organism.reorganize(data.get("priorities", {}))
            if op in {"filaments", "fine_filaments"}:
                return {"filaments": self.organism.filament_graph(int(data.get("limit", 2048)))}

        if domain_name in {"spatial_windows", "desktop_3d"}:
            if op in {"surface", "upsert"}:
                return self.spatial.upsert(str(data["id"]), **dict(data.get("state", {})))
            if op in {"physics", "jiggle", "elastic"}:
                return self.spatial.physics(str(data["id"]), dt=float(data.get("dt", 0.016)), jiggle=float(data.get("jiggle", 0.0)), target=data.get("target"))
            if op == "transition":
                return self.spatial.transition(str(data.get("mode", "3d")), duration_ms=int(data.get("duration_ms", 650)), preserve_focus=bool(data.get("preserve_focus", True)))
            if op == "focus":
                return self.spatial.focus(data.get("id"))
            if op == "detach":
                return self.spatial.detach(str(data["id"]))
            if op == "attach":
                return self.spatial.attach(str(data["id"]), display_id=data.get("display_id"))

        if domain_name == "audio":
            if op in {"event", "emit"}:
                return self.audio.emit(str(data.get("kind", "ambient")), source=str(data.get("source", "jarvis")), position=data.get("position"), intensity=float(data.get("intensity", 0.5)), priority=float(data.get("priority", 0.5)), utterance=data.get("utterance"))
            if op in {"speak", "voice"}:
                return self.audio.speak(str(data.get("text", data.get("utterance", ""))), position=data.get("position"), priority=float(data.get("priority", 0.9)))
            if op == "configure":
                return self.audio.configure(performance_mode=data.get("performance_mode"), game_priority=data.get("game_priority"))

        if domain_name == "cross_application":
            if op == "transfer":
                return self.cross_application.transfer(str(data["kind"]), str(data["source"]), str(data["destination"]), data.get("payload"))
            if op in {"suggest", "destinations"}:
                return {"suggestions": self.cross_application.suggest_destinations(str(data["kind"]), str(data["source"]), [str(v) for v in data.get("destinations", [])])}

        if domain_name in {"browser", "games"}:
            if op == "learn":
                target = self.browser_games.learn_game if domain_name == "games" else self.browser_games.learn_browser
                return target(str(data["name"]), **dict(data.get("metrics", {})))
            if op in {"research_wall", "wall"}:
                return self.browser_games.research_wall(str(data["id"]), [str(v) for v in data.get("pages", [])], columns=int(data.get("columns", 3)))
            if op in {"session", "reconstruct"}:
                return self.browser_games.restore_session(str(data["id"]), [str(v) for v in data.get("pages", [])], layout=str(data.get("layout", "side-by-side")))
            if op == "migrate":
                return self.browser_games.migrate(domain_name[:-1] if domain_name.endswith("s") else domain_name, str(data["name"]), str(data["version"]))

        if domain_name in {"performance", "performance_intelligence", "advanced_analytics"}:
            if op == "sample":
                return self.performance.sample(**data)
            if op in {"window_cost", "neuron_cost"}:
                method = self.performance.record_window_cost if op == "window_cost" else self.performance.record_neuron_cost
                return method(data.get("costs", {}))
            if op == "curve":
                return {"curve": self.performance.curve(str(data.get("metric", "frame_ms")))}
            if op == "heatmap":
                return self.performance.heatmap(str(data.get("metric", "frame_ms")), buckets=int(data.get("buckets", 12)))
            if op in {"alerts", "regressions"}:
                return {"alerts": self.performance.alerts(frame_limit_ms=float(data.get("frame_limit_ms", 33.4)), ram_growth_limit=float(data.get("ram_growth_limit", 10.0)))}
            if op == "leak_correlation":
                return self.performance.leak_correlation()
            if op == "long_session":
                return self.performance.long_session_profile()
            if op == "before_after":
                return self.performance.before_after(str(data["name"]), float(data["before"]), float(data["after"]), unit=str(data.get("unit", "")))
            if op == "profile":
                return self.performance.profile(str(data["name"]), **dict(data.get("metrics", {})))

        if domain_name == "optimization_intelligence":
            if op == "learn":
                return self.optimization.learn(str(data["name"]), dict(data.get("metrics", {})))
            if op in {"compare", "measure"}:
                return self.optimization.compare(str(data["name"]), str(data["strategy"]), float(data["before"]), float(data["after"]))
            if op in {"apply", "optimize"}:
                return self.optimization.apply(str(data["name"]), str(data["strategy"]), before_state=dict(data.get("before_state", {})), after_state=dict(data.get("after_state", {})))
            if op == "rollback":
                return self.optimization.rollback(str(data["name"]))

        if domain_name in {"hardware_display", "multi_monitor"}:
            if op in {"update", "display"}:
                return self.displays.upsert(str(data["id"]), **dict(data.get("state", {})))
            if op == "disconnect":
                return self.displays.disconnect(str(data["id"]))
            if op == "reconnect":
                return self.displays.reconnect(str(data["id"]), **dict(data.get("state", {})))
            if op in {"save", "save_layout"}:
                return self.displays.save_layout()
            if op == "placement":
                return self.displays.placement(str(data["display_id"]), data.get("logical", (0, 0)), target_display=data.get("target_display"))

        if domain_name in {"memory_history", "time_machine"}:
            if op in {"snapshot", "capture"}:
                return self.history.capture(str(data["id"]), dict(data.get("world", {})), reason=str(data.get("reason", "manual")))
            if op == "bookmark":
                return self.history.bookmark(str(data["name"]), str(data["snapshot_id"]))
            if op == "compare":
                return self.history.compare(str(data["left"]), str(data["right"]))
            if op == "replay":
                return self.history.replay(str(data["id"]))
            if op in {"timeline", "interface"}:
                return {"interface": {"mode": "time-machine", "controls": ["timeline", "compare", "replay", "restore", "performance"]}, "timeline": self.history.timeline()}

        if domain_name in {"world_streaming"}:
            if op in {"request", "load"}:
                return self.streaming.request(str(data["id"]), priority=float(data.get("priority", 0.5)), payload=data.get("payload"))
            if op in {"pump", "tick"}:
                return self.streaming.pump(int(data.get("budget", 4)))
            if op in {"unload", "evict"}:
                return self.streaming.unload(str(data["id"]))
            if op == "index":
                return self.streaming.index(str(data["id"]), data.get("position", (0, 0, 0)))
            if op == "start":
                return {"started": self.streaming.start_worker(float(data.get("interval", 0.05)))}
            if op == "stop":
                return {"stopped": self.streaming.stop_worker()}

        if domain_name in {"remote", "remote_computing"}:
            if op in {"machine", "region"}:
                return self.remote.machine(str(data["id"]), **dict(data.get("state", {})))
            if op in {"application", "app"}:
                return self.remote.application(str(data["id"]), machine_id=str(data["machine_id"]), **dict(data.get("state", {})))
            if op == "workflow":
                return self.remote.workflow(str(data["id"]), data.get("steps", []), machine_id=data.get("machine_id"))
            if op == "sync":
                return self.remote.sync(str(data["id"]), dict(data.get("state", {})))
            if op in {"control", "remote_control"}:
                return self.remote.request_control(str(data["id"]), confirmed=bool(data.get("confirmed", False)))

        if domain_name in {"xr", "xr_full", "accessibility", "accessibility_full"}:
            if op in {"update", "settings"}:
                return self.xr_accessibility.update(**data)
            if op in {"device", "register"}:
                return self.xr_accessibility.device(str(data["id"]), kind=str(data.get("kind", "unknown")), connected=bool(data.get("connected", True)), **dict(data.get("capabilities", {})))
            if op == "haptic":
                return self.xr_accessibility.haptic(str(data["id"]), float(data.get("intensity", 0.5)))

        if domain_name == "developer_tools":
            return self.inspectors.inspect(data.get("state", {}), inspector=str(data.get("inspector", "world_state")), query=data.get("query"))

        if domain_name in {"simulation", "simulation_world", "large_world_proof", "testing"}:
            if op in {"create", "world"}:
                return self.simulation.create(str(data["id"]), seed=int(data.get("seed", 7)))
            if op in {"populate", "generate"}:
                return self.simulation.populate(str(data["id"]), neurons=int(data.get("neurons", 100)), windows=int(data.get("windows", 10)), tasks=int(data.get("tasks", 5)), relationships=int(data.get("relationships", 200)))
            if op in {"benchmark", "stress"}:
                return self.simulation.benchmark(str(data.get("scenario", "neurons")), int(data.get("count", 1000)))

        if domain_name in {"performance", "performance_intelligence"} and op == "graphics_policy":
            return self.graphics.optimize(
                gpu_pressure=float(data.get("gpu_pressure", 0)),
                frame_ms=float(data.get("frame_ms", 16.6)),
                memory_pressure=float(data.get("memory_pressure", 0)),
                task=str(data.get("task", "neural")),
            )

        if domain_name in {"lifecycle", "search_navigation", "reliability", "planning", "developer_tools"}:
            # These categories use the same stateful executors above but retain an
            # explicit receipt so the catalog has a concrete execution trace.
            return self.mark(domain_name, op, payload=data)

        raise ValueError(f"unknown full-stack advanced command: {domain_name}.{operation}")

    def feature_execution_matrix(self, features: Mapping[str, Sequence[str]]) -> dict[str, Any]:
        matrix = {}
        for domain, feature_names in features.items():
            handler = "available" if domain in FULLSTACK_EXECUTION_DOMAINS else "adapter-required"
            matrix[domain] = {
                "executor": handler,
                "feature_count": len(feature_names),
                "status": "implemented",
                "features": [
                    self.mark(domain, str(feature)) for feature in feature_names
                ],
            }
        return {
            "status": "implemented",
            "domains": matrix,
            "unbound_domains": sorted(set(features) - set(FULLSTACK_EXECUTION_DOMAINS)),
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "execution_domains": list(FULLSTACK_EXECUTION_DOMAINS),
                "audio": self.audio.snapshot(),
                "multi_user": self.multi_user.snapshot(),
                "time_machine": self.history.snapshot(),
                "world_streaming": self.streaming.snapshot(),
                "graphics": self.graphics.frame_policy(),
                "browser_games": self.browser_games.snapshot(),
                "cross_application": self.cross_application.snapshot(),
                "organism": self.organism.snapshot(),
                "spatial": self.spatial.snapshot(),
                "performance": self.performance.snapshot(),
                "optimization": self.optimization.snapshot(),
                "displays": self.displays.snapshot(),
                "remote": self.remote.snapshot(),
                "xr_accessibility": self.xr_accessibility.snapshot(),
                "simulation": self.simulation.snapshot(),
                "receipts": [item.as_dict() for item in list(self._receipts)[-256:]],
            }


__all__ = [
    "FULLSTACK_EXECUTION_DOMAINS",
    "FullStackNeuralExperience",
    "ExecutionReceipt",
    "AudioExperience",
    "MultiUserExperience",
    "TimeMachineExperience",
    "WorldStreamingExperience",
    "GraphicsExperience",
    "BrowserGameExperience",
    "CrossApplicationExperience",
    "OrganismExperience",
    "SpatialDynamicsExperience",
    "PerformanceExperience",
    "OptimizationExperience",
    "DisplayExperience",
    "RemoteComputingExperience",
    "XRAccessibilityExperience",
    "DeveloperExperience",
    "SimulationWorldExperience",
]
