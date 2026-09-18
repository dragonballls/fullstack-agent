"""Automatic discovery of newly visible Windows entities for Neural JARVIS."""

from __future__ import annotations

from typing import Any


class NeuralDiscovery:
    """Turn authorized runtime inventories into stable neural entities."""

    def __init__(self, world: Any, runtime: Any) -> None:
        self.world = world
        self.runtime = runtime
        self._seen_apps: set[str] = set()
        self._seen_processes: set[str] = set()

    @staticmethod
    def _app_id(app: Any) -> str:
        return "app:" + str(getattr(app, "id", getattr(app, "name", "unknown"))).strip().casefold()

    def sync_applications(self) -> int:
        from .neural_world import EntityKind, LifecycleState
        try:
            apps = self.runtime._tool("applications").list()
        except Exception:
            return 0
        count = 0
        seen: set[str] = set()
        for app in apps or ():
            app_id = self._app_id(app)
            seen.add(app_id)
            node = self.world.upsert(
                app_id, EntityKind.APPLICATION,
                str(getattr(app, "name", app_id)),
                source="windows.applications",
                status="installed",
                lifecycle=LifecycleState.MATURE,
                energy=0.35, scale=0.9,
                metadata={
                    "publisher": str(getattr(app, "publisher", ""))[:200],
                    "version": str(getattr(app, "version", ""))[:80],
                    "inventory_source": str(getattr(app, "source", ""))[:80],
                },
            )
            folded = str(getattr(app, "name", "")).casefold()
            subsystem = "jarvis.browser" if any(token in folded for token in ("opera", "edge", "chrome", "firefox", "browser")) else "jarvis.system"
            try:
                self.world.relate(subsystem, node.id, "installed_application", 0.45)
            except KeyError:
                pass
            count += 1
        for stale in self._seen_apps - seen:
            self.world.retire(stale, remove=False)
        self._seen_apps = seen
        return count

    def sync_processes(self) -> int:
        from .neural_world import EntityKind, LifecycleState
        try:
            processes = self.runtime._tool("processes").list_processes()
        except Exception:
            return 0
        count = 0
        seen: set[str] = set()
        for proc in processes or ():
            process_id = f"process:{int(proc.pid)}"
            seen.add(process_id)
            node = self.world.upsert(
                process_id,
                EntityKind.PROCESS,
                str(proc.name or f"PID {proc.pid}"),
                source="windows.processes",
                status="running",
                lifecycle=LifecycleState.ACTIVE,
                energy=0.25, scale=0.6,
                metadata={"pid": int(proc.pid), "executable": str(proc.executable or "")[:500]},
            )
            try:
                self.world.relate("jarvis.system", node.id, "runs_process", 0.3)
            except KeyError:
                pass
            count += 1
        for stale in self._seen_processes - seen:
            self.world.retire(stale, remove=False)
        self._seen_processes = seen
        return count

    def sync(self) -> dict[str, int]:
        return {
            "applications": self.sync_applications(),
            "processes": self.sync_processes(),
        }
