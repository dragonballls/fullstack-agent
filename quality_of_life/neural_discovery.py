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
        self._seen_pages: set[str] = set()
        self._seen_accounts: set[str] = set()
        self._seen_services: set[str] = set()

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
            active = "RUNNING" in state.casefold()
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
                metadata={"provider": provider[:80], "authorized": True},
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

    def sync_extended(self) -> dict[str, int]:
        return {
            "applications": self.sync_applications(),
            "processes": self.sync_processes(),
            "browser_pages": self.sync_browser_pages(),
            "accounts": self.sync_accounts(),
            "services": self.sync_services(),
        }

    def sync(self) -> dict[str, int]:
        result = self.sync_extended()
        return {
            "applications": result["applications"],
            "processes": result["processes"],
        }
