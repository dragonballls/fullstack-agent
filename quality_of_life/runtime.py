"""Unified capability-aware runtime for Jarvis quality-of-life tools."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from .background import BackgroundJobs
from .gods_eye import GodsEye, Place
from .gods_eye_launcher import GodsEyeLauncher
from .intents import Intent, parse_intent
from .location import FallbackLocationProvider, IpLocationProvider, NominatimGeocoder, SystemLocationProvider
from .manifest import default_registry
from .orchestrator import Action, ConfirmationHook, QoLOrchestrator
from .permissions import Capability, CapabilityPolicy
from .router import CloudModelRouter, ProviderTarget


class JarvisRuntime:
    """Lazy tool host that keeps capability and confirmation checks centralized."""

    def __init__(self, policy: CapabilityPolicy, confirmation: ConfirmationHook | None = None, factories: dict[str, Callable[[], Any]] | None = None, gods_eye_launcher: GodsEyeLauncher | None = None) -> None:
        self.policy = policy
        self.confirmation = confirmation
        self.registry = default_registry()
        self._factories = dict(factories or {})
        self._instances: dict[str, Any] = {}
        self.gods_eye_launcher = gods_eye_launcher or GodsEyeLauncher()
        self.orchestrator = QoLOrchestrator(policy)
        self._agent_orchestrator: Any | None = None
        self._health_monitor: Any | None = None
        self._register_actions()

    def available_tools(self) -> tuple[str, ...]:
        return self.registry.names()

    def _factory_from_spec(self, name: str) -> Callable[[], Any]:
        if name in self._factories:
            return self._factories[name]
        spec = self.registry.get(name)
        target = spec.resolve()
        if name in {"computer", "screen", "browser", "clipboard", "windows"}:
            return lambda: target(self.policy)
        if name == "browser_registry":
            return lambda: target()
        if name == "files":
            return lambda: target(self.policy)
        if name == "applications":
            return lambda: target(self.policy)
        if name == "processes":
            return lambda: target(self.policy)
        if name == "system":
            return lambda: target(self.policy)
        if name == "scheduler":
            return lambda: target(self._tool("background"))
        if name == "gods_eye":
            return lambda: GodsEye(NominatimGeocoder(), FallbackLocationProvider(SystemLocationProvider(), IpLocationProvider()))
        if name == "background":
            return lambda: BackgroundJobs()
        if name == "cloud_router":
            explicit_base_url = os.environ.get("JARVIS_CLOUD_BASE_URL")
            if explicit_base_url:
                key_env = os.environ.get("JARVIS_CLOUD_API_KEY_ENV", "OPENAI_API_KEY")
                model = os.environ.get("JARVIS_CLOUD_MODEL")
                if not model:
                    raise RuntimeError("cloud router is not configured; set JARVIS_CLOUD_MODEL")
                target_config = ProviderTarget("primary", explicit_base_url, key_env, model)
            elif os.environ.get("JARVIS_OMNIROUTE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}:
                target_config = CloudModelRouter.omniroute_target()
            else:
                raise RuntimeError("cloud router is not configured; enable OmniRoute or set JARVIS_CLOUD_BASE_URL and JARVIS_CLOUD_MODEL")
            return lambda: CloudModelRouter((target_config,))
        if name == "self_coding":
            from self_coding import SelfCodingAgent, SelfCodingConfig
            configured_repo = os.environ.get("JARVIS_SELF_CODING_REPO")
            if not configured_repo:
                raise RuntimeError("self-coding is not configured; set JARVIS_SELF_CODING_REPO")
            return lambda: SelfCodingAgent(SelfCodingConfig(repo=Path(configured_repo), push_branch=os.environ.get("JARVIS_SELF_CODING_PUSH", "0").strip().lower() in {"1", "true", "yes", "on"}, max_passes=max(1, int(os.environ.get("JARVIS_SELF_CODING_MAX_PASSES", "1"))), backend=os.environ.get("JARVIS_SELF_CODING_BACKEND", "auto")))
        if name == "windows_maintenance":
            from windows_maintenance import MaintenanceFacade
            return lambda: MaintenanceFacade()
        raise RuntimeError(f"No runtime factory is configured for: {name}")

    def _tool(self, name: str) -> Any:
        if name not in self._instances:
            self._instances[name] = self._factory_from_spec(name)()
        return self._instances[name]

    def _assistant_orchestrator(self) -> Any:
        if self._agent_orchestrator is None:
            from .agent_orchestrator import AgentOrchestrator
            self._agent_orchestrator = AgentOrchestrator(self._tool("cloud_router"), self)
        return self._agent_orchestrator

    def _maintenance_facade(self) -> Any:
        return self._tool("windows_maintenance")

    def health_monitor(self) -> Any:
        if self._health_monitor is None:
            from .health_monitor import HealthMonitor
            self._health_monitor = HealthMonitor.from_environment(self._maintenance_facade())
        return self._health_monitor

    def start_health_monitor(self) -> bool:
        return self.health_monitor().start()

    def stop_health_monitor(self) -> None:
        if self._health_monitor is not None:
            self._health_monitor.stop()

    def health_snapshot(self) -> dict[str, Any]:
        return self.health_monitor().snapshot()

    def _register_actions(self) -> None:
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.move", lambda x, y: self._tool("computer").move(x, y)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.click", lambda button="left", clicks=1: self._tool("computer").click(button, clicks)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.scroll", lambda amount: self._tool("computer").scroll(amount)))
        self.orchestrator.register(Action(Capability.KEYBOARD_CONTROL, "computer.type_text", lambda text: self._tool("computer").type_text(text)))
        self.orchestrator.register(Action(Capability.KEYBOARD_CONTROL, "computer.hotkey", lambda *keys: self._tool("computer").hotkey(*keys)))
        self.orchestrator.register(Action(Capability.APP_LAUNCH, "computer.open_app", lambda command, *args: self._tool("computer").open_app(command, *args)))
        self.orchestrator.register(Action(Capability.SCREEN_READ, "screen.capture", lambda output=None: self._tool("screen").capture(output)))
        self.orchestrator.register(Action(Capability.CLIPBOARD, "clipboard.read", lambda: self._tool("clipboard").read()))
        self.orchestrator.register(Action(Capability.CLIPBOARD, "clipboard.write", lambda text: self._tool("clipboard").write(text)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.list", lambda: self._tool("windows").list_windows()))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.focus", lambda identifier: self._tool("windows").focus_window(identifier)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.minimize", lambda identifier: self._tool("windows").minimize_window(identifier)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.maximize", lambda identifier: self._tool("windows").maximize_window(identifier)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.close", lambda identifier: self._tool("windows").close_window(identifier)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.start", lambda browser=None: self._tool("browser").start(browser)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.open_url", lambda url, browser=None: self._tool("browser").open_url(url, browser=browser)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.navigate", lambda url: self._tool("browser").navigate(url)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.click", lambda selector: self._tool("browser").click(selector)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.fill", lambda selector, text: self._tool("browser").fill(selector, text)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.read_text", lambda selector="body": self._tool("browser").read_text(selector)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.pages", lambda: self._tool("browser").pages()))
        self.orchestrator.register(Action(Capability.FILE_READ, "files.info", lambda path: self._tool("files").info(path)))
        self.orchestrator.register(Action(Capability.FILE_READ, "files.search", lambda pattern, root=None, limit=100: self._tool("files").search(pattern, root, limit)))
        self.orchestrator.register(Action(Capability.FILE_READ, "files.read", lambda path, max_bytes=5_000_000: self._tool("files").read_text(path, max_bytes)))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "files.write", lambda path, text: self._tool("files").write_text(path, text)))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "files.copy", lambda source, destination: self._tool("files").copy(source, destination)))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "files.move", lambda source, destination: self._tool("files").move(source, destination)))
        self.orchestrator.register(Action(Capability.FILE_DELETE, "files.delete", lambda path: self._tool("files").delete(path)))
        self.orchestrator.register(Action(Capability.APP_READ, "applications.list", lambda: self._tool("applications").list()))
        self.orchestrator.register(Action(Capability.APP_WRITE, "applications.uninstall", lambda name, confirmed=False: self._tool("applications").uninstall(name, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.PROCESS_READ, "processes.list", lambda: self._tool("processes").list_processes()))
        self.orchestrator.register(Action(Capability.PROCESS_CONTROL, "processes.stop", lambda pid, confirmed=False: self._tool("processes").stop(pid, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SERVICE_READ, "services.list", lambda: self._tool("processes").list_services()))
        self.orchestrator.register(Action(Capability.SERVICE_CONTROL, "services.restart", lambda name, confirmed=False: self._tool("processes").restart_service(name, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "system.inspect", lambda: self._tool("system").inspect()))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "system.network", lambda: self._tool("system").network()))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "system.get_setting", lambda name: self._tool("system").get_setting(name)))
        self.orchestrator.register(Action(Capability.SYSTEM_SETTINGS, "system.change_setting", lambda name, value, confirmed=False: self._tool("system").set_setting(name, value, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.start", lambda name, task: self._tool("background").start(name, task)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.cancel", lambda name: self._tool("background").cancel(name)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.active", lambda: self._tool("background").active()))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "scheduler.schedule_once", lambda name, run_at, task: self._tool("scheduler").schedule_once(name, run_at, task)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "scheduler.cancel", lambda name: self._tool("scheduler").cancel(name)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "scheduler.active", lambda: self._tool("scheduler").active()))
        self.orchestrator.register(Action(Capability.CLOUD_ROUTING, "cloud_router.complete", lambda messages: self._tool("cloud_router").complete(messages)))
        self.orchestrator.register(Action(Capability.REPO_WRITE, "self_coding.run", lambda goal: self._tool("self_coding").run(goal)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.search", lambda query: self._tool("gods_eye").search(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.locate_me", lambda: self._tool("gods_eye").locate_me()))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.open_place", lambda query: self._open_place(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.route_to", lambda query: self._route_to(query)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "windows_maintenance.diagnose", lambda: self._tool("windows_maintenance").diagnose()))
        self.orchestrator.register(Action(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.handle", lambda request, confirmed=False: self._tool("windows_maintenance").handle(request, confirmed=confirmed)))

    def _first_place(self, query: str) -> tuple[GodsEye, Place]:
        eye = self._tool("gods_eye")
        places = eye.search(query)
        if not places:
            raise LookupError(f"No location found for: {query}")
        return eye, places[0]

    def _open_place(self, query: str) -> dict[str, object]:
        eye, place = self._first_place(query)
        return eye.open_place(place)

    def _route_to(self, query: str) -> dict[str, object]:
        eye, place = self._first_place(query)
        snapshot = eye.locate_me()
        if not snapshot.permitted or snapshot.point is None:
            raise PermissionError("Current location is unavailable; enable location access before routing")
        return eye.route(snapshot.point, place)

    def dispatch(self, capability: Capability, operation: str, *args: Any, **kwargs: Any) -> Any:
        return self.orchestrator.run(capability, operation, *args, confirmation=self.confirmation, **kwargs)

    def handle_assistant_request(self, text: str, confirmed: bool = False) -> dict[str, Any]:
        result = self._assistant_orchestrator().execute(text, confirmed=confirmed)
        return {"text": result.text, "profile": result.profile, "verified": result.verified, "needs_confirmation": result.needs_confirmation, "parallel_tasks_completed": result.parallel_tasks_completed, "providers": result.providers, "latency_ms": result.latency_ms, "errors": result.errors}

    def handle_assistant_stream(self, text: str, confirmed: bool = False) -> Iterator[Any]:
        yield from self._assistant_orchestrator().execute_stream(text, confirmed=confirmed)

    def handle_text(self, text: str) -> Any:
        intent: Intent = parse_intent(text)
        if intent.kind == "browser_open":
            browser = str(intent.arguments["browser"])
            url = intent.arguments.get("url")
            if url:
                return {"intent": intent, "result": self.dispatch(Capability.BROWSER_CONTROL, "browser.open_url", url=str(url), browser=browser)}
            return {"intent": intent, "result": self.dispatch(Capability.BROWSER_CONTROL, "browser.start", browser=browser)}
        if intent.kind == "application_list":
            return {"intent": intent, "result": self.dispatch(Capability.APP_READ, "applications.list")}
        if intent.kind == "application_uninstall":
            return {"intent": intent, "result": self.dispatch(Capability.APP_WRITE, "applications.uninstall", name=str(intent.arguments["name"]))}
        if intent.kind == "process_list":
            return {"intent": intent, "result": self.dispatch(Capability.PROCESS_READ, "processes.list")}
        if intent.kind == "system_inspect":
            return {"intent": intent, "result": self.dispatch(Capability.SYSTEM_DIAGNOSTICS, "system.inspect")}
        if intent.kind == "file_read":
            return {"intent": intent, "result": self.dispatch(Capability.FILE_READ, "files.read", path=str(intent.arguments["path"]))}
        if intent.kind == "file_delete":
            return {"intent": intent, "result": self.dispatch(Capability.FILE_DELETE, "files.delete", path=str(intent.arguments["path"]))}
        if intent.kind == "place_search":
            query = str(intent.arguments["query"])
            result = self.dispatch(Capability.LOCATION_READ, "gods_eye.open_place", query=query)
            self.gods_eye_launcher.launch_query(query)
            return {"intent": intent, "result": result, "opened": True}
        if intent.kind == "locate_me":
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_READ, "gods_eye.locate_me")}
        if intent.kind == "route":
            query = str(intent.arguments["query"])
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_READ, "gods_eye.route_to", query=query)}
        if intent.kind == "screen_read":
            return {"intent": intent, "result": self.dispatch(Capability.SCREEN_READ, "screen.capture")}
        if intent.kind == "computer_action":
            return {"intent": intent, "result": self.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=intent.arguments["x"], y=intent.arguments["y"])}
        if intent.kind == "windows_maintenance":
            request = str(intent.arguments["request"])
            if "diagnos" in request.casefold() and not any(word in request.casefold() for word in ("fix", "repair", "clean")):
                return {"intent": intent, "result": self.dispatch(Capability.SYSTEM_DIAGNOSTICS, "windows_maintenance.diagnose")}
            return {"intent": intent, "result": self.dispatch(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.handle", request=request)}
        return intent
