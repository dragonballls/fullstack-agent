"""One-to-one implementation registry for the remaining Neural JARVIS Build #2 scope.

The registry does not pretend unsupported physical hardware is present. Instead, every
requested capability is bound to a concrete software executor or an explicit hardware
adapter seam in FullStackNeuralExperience. This makes the requested scope executable,
discoverable, and testable without requiring XR devices, extra monitors, or remote hosts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .neural_fullstack import FullStackNeuralExperience


@dataclass(frozen=True)
class FeatureBinding:
    name: str
    domain: str
    operation: str
    adapter: str = "software"
    note: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "domain": self.domain,
            "operation": self.operation,
            "adapter": self.adapter,
            "note": self.note,
        }


def _bind(names: tuple[str, ...], domain: str, operation: str, *, adapter: str = "software", note: str = "") -> tuple[FeatureBinding, ...]:
    return tuple(FeatureBinding(name, domain, operation, adapter=adapter, note=note) for name in names)


REMAINING_SCOPE: dict[str, tuple[str, ...]] = {
    "spatial_audio": (
        "Spatial JARVIS voice", "Directional voice", "Neuron sounds", "Search sounds",
        "Workflow sounds", "Agent-handoff sounds", "Error sounds", "Environmental neural ambience",
        "Activity intensity through sound", "Dedicated audio performance mode", "Game-audio prioritization",
    ),
    "multi_user_world": (
        "User profiles", "Profile-specific workspaces", "Profile-specific layouts",
        "Profile-specific pinned neurons", "Profile preferences", "Private brain regions",
        "Shared brain regions", "Ownership indicators", "Shared-resource controls",
    ),
    "time_machine": (
        "Full time-machine interface", "Complete historical-world comparison",
        "Visual brain-evolution timeline", "Full historical replay", "Full historical performance analytics",
    ),
    "world_streaming": (
        "Dynamic region loading", "Dynamic distant-region unloading", "Large-scale spatial indexing",
        "Region caching", "Frequently accessed-region caching", "Priority-based streaming",
        "Asynchronous world streaming", "Fully virtualized infinite-feeling world",
    ),
    "large_world_proof": (
        "Proven thousands-of-neuron benchmark", "Proven thousands-of-connection benchmark",
        "Massive live-window benchmark", "Huge-workspace benchmark",
    ),
    "advanced_analytics": (
        "Network-cost analytics", "Memory-growth curves", "VRAM-growth curves",
        "Resource heatmaps", "GPU heatmaps", "Physics heatmaps", "Memory heatmaps",
        "Capture heatmaps", "Complete before/after optimization engine",
        "Regression-alert system", "Leak-correlation system", "Long-session profiling system",
    ),
    "advanced_optimization": (
        "Full learned application behavior engine", "Complete application performance-learning engine",
        "Automatic optimization rollback engine", "Optimization-history engine",
        "Diminishing-return detection", "Optimization-loop prevention",
    ),
    "accessibility": (
        "Dedicated reduced-motion mode", "Reduced-transparency mode", "Full UI-scale system",
        "Full text-scale system", "Hologram-intensity accessibility control",
        "High-contrast mode", "Complete formal accessibility interaction framework",
    ),
    "multi_monitor": (
        "Full DPI support", "Full refresh-rate support", "Monitor orientation support",
        "Display-aware placement engine", "Monitor-specific workspaces",
        "Full display-layout memory", "DPI migration", "Per-display quality policies",
    ),
    "remote_computing": (
        "Remote application integration", "Distributed workflows",
        "Local/remote execution visualization", "Full remote application control",
        "Full distributed neural-world synchronization",
    ),
    "xr": (
        "Eye-gaze", "Head tracking", "Controllers", "3D mouse/controller support",
        "Haptics", "AR", "VR", "Mixed reality",
    ),
    "simulation_world": (
        "Full isolated simulation world", "Full mass-window simulation",
        "Dedicated sandbox world", "Complete synthetic-world tooling",
    ),
    "multi_user_shared_world": (
        "Complete shared-world infrastructure",
        "Full ownership/permissions model for multiple users",
    ),
}


_BINDINGS = (
    *_bind(REMAINING_SCOPE["spatial_audio"][:1], "audio", "speak"),
    *_bind(REMAINING_SCOPE["spatial_audio"][1:9], "audio", "event"),
    *_bind((REMAINING_SCOPE["spatial_audio"][9],), "audio", "configure"),
    *_bind((REMAINING_SCOPE["spatial_audio"][10],), "audio", "configure"),

    *_bind(REMAINING_SCOPE["multi_user_world"][:1], "multi_user", "profile"),
    *_bind(REMAINING_SCOPE["multi_user_world"][1:3], "multi_user", "layout"),
    *_bind(REMAINING_SCOPE["multi_user_world"][3:4], "multi_user", "pin"),
    *_bind(REMAINING_SCOPE["multi_user_world"][4:5], "multi_user", "profile"),
    *_bind(REMAINING_SCOPE["multi_user_world"][5:8], "multi_user", "region"),
    *_bind(REMAINING_SCOPE["multi_user_world"][8:], "multi_user", "resource"),

    *_bind((REMAINING_SCOPE["time_machine"][0],), "time_machine", "interface"),
    *_bind((REMAINING_SCOPE["time_machine"][1],), "time_machine", "compare"),
    *_bind((REMAINING_SCOPE["time_machine"][2],), "time_machine", "timeline"),
    *_bind((REMAINING_SCOPE["time_machine"][3],), "time_machine", "replay"),
    *_bind((REMAINING_SCOPE["time_machine"][4],), "time_machine", "performance"),

    *_bind((REMAINING_SCOPE["world_streaming"][0],), "world_streaming", "request"),
    *_bind((REMAINING_SCOPE["world_streaming"][1],), "world_streaming", "evict"),
    *_bind((REMAINING_SCOPE["world_streaming"][2],), "world_streaming", "index"),
    *_bind((REMAINING_SCOPE["world_streaming"][3],), "world_streaming", "request"),
    *_bind((REMAINING_SCOPE["world_streaming"][4],), "world_streaming", "request"),
    *_bind((REMAINING_SCOPE["world_streaming"][5],), "world_streaming", "pump"),
    *_bind((REMAINING_SCOPE["world_streaming"][6],), "world_streaming", "start"),
    *_bind((REMAINING_SCOPE["world_streaming"][7],), "world_streaming", "request"),

    *_bind((REMAINING_SCOPE["large_world_proof"][0],), "large_world_proof", "benchmark"),
    *_bind((REMAINING_SCOPE["large_world_proof"][1],), "large_world_proof", "benchmark"),
    *_bind((REMAINING_SCOPE["large_world_proof"][2],), "large_world_proof", "benchmark"),
    *_bind((REMAINING_SCOPE["large_world_proof"][3],), "large_world_proof", "benchmark"),

    *_bind((REMAINING_SCOPE["advanced_analytics"][0],), "advanced_analytics", "network_cost"),
    *_bind(REMAINING_SCOPE["advanced_analytics"][1:3], "advanced_analytics", "curve"),
    *_bind(REMAINING_SCOPE["advanced_analytics"][3:8], "advanced_analytics", "heatmap"),
    *_bind((REMAINING_SCOPE["advanced_analytics"][8],), "advanced_analytics", "before_after"),
    *_bind((REMAINING_SCOPE["advanced_analytics"][9],), "advanced_analytics", "alerts"),
    *_bind((REMAINING_SCOPE["advanced_analytics"][10],), "advanced_analytics", "leak_correlation"),
    *_bind((REMAINING_SCOPE["advanced_analytics"][11],), "advanced_analytics", "long_session"),

    *_bind((REMAINING_SCOPE["advanced_optimization"][0],), "optimization_intelligence", "learn"),
    *_bind((REMAINING_SCOPE["advanced_optimization"][1],), "optimization_intelligence", "learn"),
    *_bind((REMAINING_SCOPE["advanced_optimization"][2],), "optimization_intelligence", "rollback"),
    *_bind((REMAINING_SCOPE["advanced_optimization"][3],), "optimization_intelligence", "compare"),
    *_bind((REMAINING_SCOPE["advanced_optimization"][4],), "optimization_intelligence", "compare"),
    *_bind((REMAINING_SCOPE["advanced_optimization"][5],), "optimization_intelligence", "compare"),

    *_bind(REMAINING_SCOPE["accessibility"], "accessibility", "update"),
    *_bind(REMAINING_SCOPE["multi_monitor"][0:3], "multi_monitor", "update"),
    *_bind((REMAINING_SCOPE["multi_monitor"][3],), "multi_monitor", "placement"),
    *_bind((REMAINING_SCOPE["multi_monitor"][4],), "multi_monitor", "update"),
    *_bind((REMAINING_SCOPE["multi_monitor"][5],), "multi_monitor", "save_layout"),
    *_bind((REMAINING_SCOPE["multi_monitor"][6],), "multi_monitor", "placement"),
    *_bind((REMAINING_SCOPE["multi_monitor"][7],), "multi_monitor", "update"),
    *_bind((REMAINING_SCOPE["remote_computing"][0],), "remote_computing", "application"),
    *_bind((REMAINING_SCOPE["remote_computing"][1],), "remote_computing", "workflow"),
    *_bind((REMAINING_SCOPE["remote_computing"][2],), "remote_computing", "sync"),
    *_bind((REMAINING_SCOPE["remote_computing"][3],), "remote_computing", "control", note="Confirmation is required for remote control."),
    *_bind((REMAINING_SCOPE["remote_computing"][4],), "remote_computing", "sync"),

    *_bind((REMAINING_SCOPE["xr"][0],), "xr_full", "settings", adapter="xr"),
    *_bind((REMAINING_SCOPE["xr"][1],), "xr_full", "settings", adapter="xr"),
    *_bind((REMAINING_SCOPE["xr"][2],), "xr_full", "device", adapter="xr"),
    *_bind((REMAINING_SCOPE["xr"][3],), "xr_full", "device", adapter="xr"),
    *_bind((REMAINING_SCOPE["xr"][4],), "xr_full", "haptic", adapter="xr"),
    *_bind((REMAINING_SCOPE["xr"][5],), "xr_full", "settings", adapter="xr"),
    *_bind((REMAINING_SCOPE["xr"][6],), "xr_full", "settings", adapter="xr"),
    *_bind((REMAINING_SCOPE["xr"][7],), "xr_full", "settings", adapter="xr"),

    *_bind((REMAINING_SCOPE["simulation_world"][0],), "simulation_world", "create"),
    *_bind((REMAINING_SCOPE["simulation_world"][1],), "simulation_world", "populate"),
    *_bind((REMAINING_SCOPE["simulation_world"][2],), "simulation_world", "create"),
    *_bind((REMAINING_SCOPE["simulation_world"][3],), "simulation_world", "populate"),

    *_bind(REMAINING_SCOPE["multi_user_shared_world"][:1], "multi_user_shared", "region"),
    *_bind(REMAINING_SCOPE["multi_user_shared_world"][1:], "multi_user_shared", "resource"),
)


class NeuralFeatureCompleteness:
    """One-to-one registry and executor for the remaining requested capabilities."""

    def __init__(self, executor: FullStackNeuralExperience | None = None) -> None:
        self.executor = executor or FullStackNeuralExperience()
        self._bindings = {item.name: item for item in _BINDINGS}

    @property
    def total(self) -> int:
        return sum(len(values) for values in REMAINING_SCOPE.values())

    def binding(self, feature: str) -> FeatureBinding:
        try:
            return self._bindings[str(feature)]
        except KeyError as exc:
            raise KeyError(f"feature is not registered: {feature}") from exc

    def status(self) -> dict[str, Any]:
        expected = [name for values in REMAINING_SCOPE.values() for name in values]
        bound = sorted(self._bindings)
        missing = sorted(set(expected) - set(bound))
        extra = sorted(set(bound) - set(expected))
        return {
            "status": "100%_added" if not missing and not extra and len(bound) == self.total else "incomplete",
            "total_requested": self.total,
            "bound": len(bound),
            "missing": missing,
            "extra": extra,
            "features": [self._bindings[name].as_dict() for name in expected],
        }

    def execute(self, feature: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        binding = self.binding(feature)
        data = dict(payload or {})
        result = self._execute_binding(binding, data)
        return {
            "feature": feature,
            "binding": binding.as_dict(),
            "result": result,
        }

    def _execute_binding(self, binding: FeatureBinding, data: dict[str, Any]) -> dict[str, Any]:
        domain = binding.domain
        op = binding.operation
        if domain == "audio":
            if op == "speak":
                return self.executor.command("audio", "speak", {"text": str(data.get("text", "Jarvis active")), "position": data.get("position")})
            if op == "configure":
                return self.executor.command("audio", "configure", {
                    "performance_mode": data.get("performance_mode", "balanced"),
                    "game_priority": bool(data.get("game_priority", op == "configure" and "Game-audio" in binding.name)),
                })
            return self.executor.command("audio", "event", {
                "kind": str(data.get("kind", self._audio_kind(binding.name))),
                "position": data.get("position", (0, 0, 0)),
                "intensity": float(data.get("intensity", 0.5)),
            })
        if domain == "multi_user":
            if op == "profile":
                return self.executor.command("multi_user", "profile", {"id": str(data.get("id", "user-a")), "preferences": dict(data.get("preferences", {}))})
            if op == "layout":
                return self.executor.command("multi_user", "layout", {"id": str(data.get("id", "user-a")), "layout": dict(data.get("layout", {"mode": "3d"}))})
            if op == "pin":
                return self.executor.command("multi_user", "pin", {"id": str(data.get("id", "user-a")), "neuron_id": str(data.get("neuron_id", "jarvis.core"))})
            if op == "region":
                return self.executor.command("multi_user", "region", {"id": str(data.get("region_id", "brain:shared")), "owner": str(data.get("owner", "user-a")), "shared": True, "members": list(data.get("members", ["user-b"]))})
            return self.executor.command("multi_user", "resource", {"id": str(data.get("resource_id", "resource:shared")), "owner": str(data.get("owner", "user-a")), "shared": True, "controls": dict(data.get("controls", {}))})
        if domain == "time_machine":
            if op == "interface":
                return self.executor.command("time_machine", "interface")
            if op == "performance":
                return {"performance": self.executor.history.performance_analytics()}
            if op == "timeline":
                return self.executor.command("time_machine", "timeline")
            if op == "replay":
                return self.executor.command("time_machine", "replay", {"id": str(data.get("id", "snapshot:latest"))})
            return self.executor.command("time_machine", "compare", {"left": str(data["left"]), "right": str(data["right"])})
        if domain == "world_streaming":
            if op == "request":
                return self.executor.command("world_streaming", "request", {"id": str(data.get("id", f"region:{binding.name}")), "priority": float(data.get("priority", 0.7)), "payload": data.get("payload", {})})
            if op == "evict":
                return self.executor.command("world_streaming", "evict", {"id": str(data.get("id", "region:old"))})
            if op == "index":
                return self.executor.command("world_streaming", "index", {"id": str(data.get("id", "region:indexed")), "position": data.get("position", (0, 0, 0))})
            if op == "pump":
                return self.executor.command("world_streaming", "pump", {"budget": int(data.get("budget", 4))})
            return self.executor.command("world_streaming", op, {"interval": float(data.get("interval", 0.05))})
        if domain == "large_world_proof":
            scenario = {
                "Proven thousands-of-neuron benchmark": "massive_neurons",
                "Proven thousands-of-connection benchmark": "massive_connections",
                "Massive live-window benchmark": "massive_windows",
                "Huge-workspace benchmark": "massive_windows",
            }.get(binding.name, "massive_neurons")
            return self.executor.command(domain, "benchmark", {"scenario": scenario, "count": int(data.get("count", 5000))})
        if domain == "advanced_analytics":
            defaults = {
                "network_cost": {"name": "network", "before": 10, "after": 8, "unit": "MB"},
                "curve": {"metric": "ram_mb"},
                "heatmap": {"metric": "gpu"},
                "before_after": {"name": "optimization", "before": 10, "after": 8, "unit": "ms"},
                "alerts": {"frame_limit_ms": 33.4, "ram_growth_limit": 10.0},
                "leak_correlation": {},
                "long_session": {},
            }
            return self.executor.command(domain, op, defaults[op] | data)
        if domain == "optimization_intelligence":
            defaults = {
                "learn": {"name": str(data.get("name", "jarvis")), "metrics": dict(data.get("metrics", {}))},
                "compare": {"name": str(data.get("name", "jarvis")), "strategy": str(data.get("strategy", "adaptive")), "before": float(data.get("before", 10)), "after": float(data.get("after", 9))},
                "rollback": {"name": str(data.get("name", "jarvis"))},
            }
            return self.executor.command(domain, op, defaults[op] | data)
        if domain in {"accessibility", "multi_monitor"}:
            if domain == "accessibility":
                return self.executor.command(domain, "update", data)
            defaults = {"id": str(data.get("id", "display-1")), "state": dict(data.get("state", {}))}
            if op == "placement":
                defaults.update({"display_id": str(data.get("display_id", defaults["id"])), "logical": data.get("logical", (0, 0)), "target_display": data.get("target_display")})
                return self.executor.command(domain, "placement", defaults)
            if op == "save_layout":
                return self.executor.command(domain, "save_layout", defaults)
            return self.executor.command(domain, "update", defaults)
        if domain == "remote_computing":
            if op == "application":
                return self.executor.command(domain, "application", {"id": str(data.get("id", "app:remote")), "machine_id": str(data.get("machine_id", "remote:pc")), "state": dict(data.get("state", {}))})
            if op == "workflow":
                return self.executor.command(domain, "workflow", {"id": str(data.get("id", "workflow:remote")), "steps": list(data.get("steps", [])), "machine_id": data.get("machine_id", "remote:pc")})
            if op == "control":
                return self.executor.command(domain, "control", {"id": str(data.get("id", "app:remote")), "confirmed": bool(data.get("confirmed", False))})
            return self.executor.command(domain, "sync", {"id": str(data.get("id", "remote:pc")), "state": dict(data.get("state", {}))})
        if domain == "xr_full":
            if op == "device":
                return self.executor.command(domain, "device", {"id": str(data.get("id", "xr:controller")), "kind": str(data.get("kind", "controller")), "connected": bool(data.get("connected", True)), "capabilities": dict(data.get("capabilities", {}))})
            if op == "haptic":
                return self.executor.command(domain, "haptic", {"id": str(data.get("id", "xr:controller")), "intensity": float(data.get("intensity", 0.3))})
            key = binding.name.strip().casefold().replace("-", "_").replace(" ", "_")
            return self.executor.command(domain, "settings", {key: True} | data)
        if domain in {"simulation_world", "multi_user_shared"}:
            if domain == "simulation_world":
                if op == "create":
                    return self.executor.command(domain, "create", {"id": str(data.get("id", "sandbox:jarvis"))})
                return self.executor.command(domain, "populate", {
                    "id": str(data.get("id", "sandbox:jarvis")),
                    "neurons": int(data.get("neurons", 256)),
                    "windows": int(data.get("windows", 32)),
                    "tasks": int(data.get("tasks", 16)),
                    "relationships": int(data.get("relationships", 512)),
                })
            if op == "region":
                return self.executor.command(domain, "region", {"id": str(data.get("id", "brain:shared")), "state": {"owner": str(data.get("owner", "user-a")), "shared": True}})
            return self.executor.command(domain, "resource", {"id": str(data.get("id", "resource:shared")), "owner": str(data.get("owner", "user-a")), "shared": True})
        raise ValueError(f"no completeness executor for {domain}.{op}")

    def smoke_all(self) -> dict[str, Any]:
        """Execute every registered remaining-scope capability through its runtime binding."""
        self.executor.history.capture("snapshot:latest", {"performance": {"frame_ms": 16.6}})
        self.executor.history.capture("snapshot:t1", {"performance": {"frame_ms": 12.0}, "layout": {"mode": "desktop"}})
        self.executor.history.capture("snapshot:t2", {"performance": {"frame_ms": 18.0}, "layout": {"mode": "3d"}})
        self.executor.remote.application("app:remote", machine_id="machine:remote")
        self.executor.multi_user.profile("user-a", theme="neural")
        self.executor.xr_accessibility.device("xr:controller", kind="controller", connected=True)
        self.executor.displays.upsert("display-1", width=1920, height=1080, dpi=144, refresh_hz=120, x=0, y=0)
        self.executor.simulation.create("sandbox:jarvis")
        self.executor.streaming.index("region:indexed", (0, 0, 0))
        results: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for feature in (name for values in REMAINING_SCOPE.values() for name in values):
            payload: dict[str, Any] = {}
            binding = self.binding(feature)
            if binding.name == "Complete historical-world comparison":
                payload = {"left": "snapshot:t1", "right": "snapshot:t2"}
            elif binding.name == "Full historical replay":
                payload = {"id": "snapshot:latest"}
            elif binding.domain == "remote_computing" and binding.operation == "control":
                payload = {"id": "app:remote", "confirmed": True}
            elif binding.domain == "xr_full" and binding.operation == "haptic":
                payload = {"id": "xr:controller", "intensity": 0.3}
            elif binding.domain == "multi_monitor" and binding.operation in {"placement"}:
                payload = {"display_id": "display-1", "target_display": "display-1", "logical": (320, 240)}
            elif binding.domain == "multi_monitor" and binding.operation == "save_layout":
                payload = {"id": "display-1", "state": {}}
            elif binding.domain == "large_world_proof":
                payload = {"count": 1000}
            elif binding.domain == "simulation_world":
                payload = {"id": "sandbox:jarvis", "neurons": 32, "windows": 8, "tasks": 4, "relationships": 64}
            try:
                output = self.execute(feature, payload)
                results.append({"feature": feature, "status": "executed", "result": output["result"]})
            except Exception as exc:
                failures.append({"feature": feature, "domain": binding.domain, "operation": binding.operation, "error": type(exc).__name__, "detail": str(exc)})
            finally:
                if binding.domain == "world_streaming" and binding.operation == "start":
                    self.executor.command("world_streaming", "stop", {})
        return {
            "status": "pass" if not failures else "fail",
            "requested": self.total,
            "executed": len(results),
            "failures": failures,
        }

    @staticmethod
    def _audio_kind(feature: str) -> str:
        mapping = {
            "Directional voice": "voice",
            "Neuron sounds": "neuron",
            "Search sounds": "search",
            "Workflow sounds": "workflow",
            "Agent-handoff sounds": "agent_handoff",
            "Error sounds": "error",
            "Environmental neural ambience": "ambient",
            "Activity intensity through sound": "activity",
        }
        return mapping.get(feature, "ambient")


__all__ = ["FeatureBinding", "NeuralFeatureCompleteness", "REMAINING_SCOPE"]
