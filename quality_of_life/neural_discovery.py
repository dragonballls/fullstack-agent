"""Automatic discovery of newly visible Windows entities for Neural JARVIS."""

from __future__ import annotations

from typing import Any
import time


class NeuralDiscovery:
    """Turn authorized runtime inventories into stable neural entities."""

    def __init__(self, world: Any, runtime: Any) -> None:
        self.world = world
        self.runtime = runtime
        self._seen_apps: set[str] = set()
        self._seen_processes: set[str] = set()
        self._seen_pages: set[str] = set()
        self._seen_accounts: set[str] = set()
        self._seen_services: set[str] = set()
        self._last_net: tuple[int, int, float] | None = None

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
            label = str(getattr(app, "name", "") or "").strip() or app_id
            seen.add(app_id)
            node = self.world.upsert(
                app_id, EntityKind.APPLICATION,
                label,
                source="windows.applications",
                status="installed",
                lifecycle=LifecycleState.MATURE,
            folded = str(getattr(app, "name", "")).casefold()
            subsystem = "jarvis.browser" if any(token in folded for token in ("opera", "edge", "chrome", "firefox", "browser")) else "jarvis.system"
            node = self.world.upsert(
                app_id, EntityKind.APPLICATION,
                label,
                source="windows.applications",
                status="installed",
                lifecycle=LifecycleState.MATURE,
                energy=0.35, scale=0.9,
                parent_id=subsystem,
                metadata={
                    "publisher": str(getattr(app, "publisher", ""))[:200],
                    "version": str(getattr(app, "version", ""))[:80],
                    "inventory_source": str(getattr(app, "source", ""))[:80],
                    "auto_layout": True,
                },
            )
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
                parent_id="jarvis.system",
                metadata={"pid": int(proc.pid), "executable": str(proc.executable or "")[:500], "auto_layout": True},
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

    def sync_browser_pages(self) -> int:
        from .neural_world import EntityKind, LifecycleState
        try:
            pages = self.runtime._tool("browser").pages()
        except Exception:
            return 0
        seen: set[str] = set()
        count = 0
        for index, url in enumerate(pages or ()):
            page_url = str(url).strip()
            if not page_url:
                continue
            entity_id = "browser:" + __import__("hashlib").sha256(page_url.encode("utf-8")).hexdigest()[:20]
            seen.add(entity_id)
            node = self.world.upsert(
                entity_id, EntityKind.PAGE, page_url[:220], source="browser",
                status="open", lifecycle=LifecycleState.ACTIVE,
                energy=0.5, scale=0.75,
                parent_id="jarvis.browser",
                metadata={"url": page_url[:1000], "index": index, "auto_layout": True},
            )
            try:
                self.world.relate("jarvis.browser", node.id, "open_page", 0.65)
            except KeyError:
                pass
            count += 1
        for stale in self._seen_pages - seen:
            self.world.retire(stale, remove=False)
        self._seen_pages = seen
        return count

    def sync_services(self) -> int:
        from .neural_world import EntityKind, LifecycleState
        try:
            services = self.runtime._tool("processes").list_services()
        except Exception:
            return 0
        count = 0
        seen: set[str] = set()
        for service in services or ():
            service_name = str(getattr(service, "name", "")).strip()
            if not service_name:
                continue
            entity_id = "service:" + service_name.casefold()
            seen.add(entity_id)
            state = str(getattr(service, "state", "unknown"))
            active = "running" in state.casefold()
            node = self.world.upsert(
                entity_id,
                EntityKind.SERVICE,
                str(getattr(service, "display_name", service_name))[:220],
                source="windows.services",
                status=state[:120],
                lifecycle=LifecycleState.ACTIVE if active else LifecycleState.DORMANT,
                energy=0.48 if active else 0.18,
                scale=0.72,
                parent_id="jarvis.system",
                metadata={
                    "service_name": service_name[:120],
                    "display_name": str(getattr(service, "display_name", service_name))[:220],
                    "auto_layout": True,
                },
            )
            try:
                self.world.relate("jarvis.system", node.id, "runs_service", 0.35 if active else 0.16)
            except KeyError:
                pass
            count += 1
        for stale in self._seen_services - seen:
            self.world.retire(stale, remove=False)
        self._seen_services = seen
        return count

    def sync_accounts(self) -> int:
        from .neural_world import EntityKind, LifecycleState
        try:
            accounts = self.runtime._tool("account_manager").list_accounts()
        except Exception:
            return 0
        seen: set[str] = set()
        count = 0
        for account in accounts or ():
            provider = str(getattr(account, "provider", "unknown"))
            account_id = str(getattr(account, "account_id", getattr(account, "id", "")))
            if not account_id:
                continue
            entity_id = "account:" + provider.casefold() + ":" + account_id.casefold()
            seen.add(entity_id)
            node = self.world.upsert(
                entity_id, EntityKind.ACCOUNT,
                str(getattr(account, "label", account_id))[:180],
                source="accounts", status=str(getattr(account, "state", "authorized"))[:80],
                lifecycle=LifecycleState.MATURE, energy=0.4, scale=0.8,
                parent_id="jarvis.core",
                metadata={"provider": provider[:80], "authorized": True, "auto_layout": True},
            )
            try:
                self.world.relate("jarvis.core", node.id, "authorized_account", 0.45)
            except KeyError:
                pass
            count += 1
        for stale in self._seen_accounts - seen:
            self.world.retire(stale, remove=False)
        self._seen_accounts = seen
        return count

    def sync_telemetry(self) -> int:
        from pathlib import Path
        from .neural_world import EntityKind, LifecycleState
        try:
            import psutil
        except ImportError:
            return 0
        now = time.monotonic()
        cpu = float(psutil.cpu_percent(interval=None))
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        try:
            root = Path.home().anchor or str(Path.home())
            disk = psutil.disk_usage(root)
        except Exception:
            disk = None
        sent_rate = recv_rate = 0.0
        try:
            net = psutil.net_io_counters()
            current_sent, current_recv = int(net.bytes_sent), int(net.bytes_recv)
            if self._last_net is not None:
                old_sent, old_recv, old_time = self._last_net
                elapsed = max(0.25, now - old_time)
                sent_rate = max(0.0, (current_sent-old_sent)/elapsed)
                recv_rate = max(0.0, (current_recv-old_recv)/elapsed)
            self._last_net = (current_sent, current_recv, now)
        except Exception:
            pass
        metrics = (
            ("telemetry:cpu", "CPU Utilization", cpu, "percent"),
            ("telemetry:memory", "Memory Utilization", float(memory.percent), "percent"),
            ("telemetry:swap", "Swap Utilization", float(swap.percent), "percent"),
            ("telemetry:disk", "System Disk Utilization", float(disk.percent) if disk else 0.0, "percent"),
            ("telemetry:network-up", "Network Upload", sent_rate, "bytes_per_second"),
            ("telemetry:network-down", "Network Download", recv_rate, "bytes_per_second"),
        )
        for entity_id, label, value, metric in metrics:
            if metric == "bytes_per_second":
                status = f"{value/1_000_000:.2f} MB/s"
                energy = max(0.08, min(0.98, value/25_000_000))
            else:
                status = f"{value:.1f}%"
                energy = max(0.08, min(0.98, value/100.0))
            self.world.upsert(
                entity_id,
                EntityKind.PERFORMANCE,
                label,
                source="system.telemetry",
                status=status,
                lifecycle=LifecycleState.ACTIVE,
                energy=energy,
                scale=0.82,
                parent_id="jarvis.system",
                metadata={"metric": metric, "value": value, "read_only": True, "auto_layout": True},
            )
        return len(metrics)

    def sync_extended(self) -> dict[str, int]:
        return {
            "applications": self.sync_applications(),
            "processes": self.sync_processes(),
            "browser_pages": self.sync_browser_pages(),
            "accounts": self.sync_accounts(),
            "services": self.sync_services(),
            "telemetry": self.sync_telemetry(),
        }

    def sync(self) -> dict[str, int]:
        result = self.sync_extended()
        return {
            "applications": result["applications"],
            "processes": result["processes"],
            "telemetry": result.get("telemetry", 0),
        }
