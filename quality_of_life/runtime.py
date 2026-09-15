"""Unified capability-aware runtime for Jarvis quality-of-life tools."""

from __future__ import annotations

import os
from collections.abc import Callable
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

    def __init__(
        self,
        policy: CapabilityPolicy,
        confirmation: ConfirmationHook | None = None,
        factories: dict[str, Callable[[], Any]] | None = None,
        gods_eye_launcher: GodsEyeLauncher | None = None,
    ) -> None:
        """Initialize policy, lazy factories, God’s Eye, and the guarded action registry."""
        self.policy = policy
        self.confirmation = confirmation
        self.registry = default_registry()
        self._factories = dict(factories or {})
        self._instances: dict[str, Any] = {}
        self.gods_eye_launcher = gods_eye_launcher or GodsEyeLauncher()
        self.orchestrator = QoLOrchestrator(policy)
        self._register_actions()

    def available_tools(self) -> tuple[str, ...]:
        """Return the names of tools exposed by the runtime registry."""
        return self.registry.names()

    def _factory_from_spec(self, name: str) -> Callable[[], Any]:
        """Resolve a tool name into a lazy factory while preserving security policy boundaries."""
        if name in self._factories:
            return self._factories[name]
        spec = self.registry.get(name)
        target = spec.resolve()
        if name in {"computer", "screen", "browser", "clipboard", "windows"}:
            return lambda: target(self.policy)
        if name == "gods_eye":
            return lambda: GodsEye(
                NominatimGeocoder(),
                FallbackLocationProvider(SystemLocationProvider(), IpLocationProvider()),
            )
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
                raise RuntimeError(
                    "cloud router is not configured; enable OmniRoute or set JARVIS_CLOUD_BASE_URL and JARVIS_CLOUD_MODEL"
                )
            return lambda: CloudModelRouter((target_config,))
        if name == "windows_maintenance":
            from windows_maintenance import MaintenanceFacade
            return lambda: MaintenanceFacade()
        raise RuntimeError(f"No runtime factory is configured for: {name}")

    def _tool(self, name: str) -> Any:
        """Return a cached tool instance, constructing it lazily on first use."""
        if name not in self._instances:
            self._instances[name] = self._factory_from_spec(name)()
        return self._instances[name]

    def _register_actions(self) -> None:
        """Register all capability-gated runtime operations with the orchestrator."""
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
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.open_url", lambda url: self._tool("browser").open_url(url)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.start", lambda name, task: self._tool("background").start(name, task)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.cancel", lambda name: self._tool("background").cancel(name)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.active", lambda: self._tool("background").active()))
        self.orchestrator.register(Action(Capability.CLOUD_ROUTING, "cloud_router.complete", lambda messages: self._tool("cloud_router").complete(messages)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.search", lambda query: self._tool("gods_eye").search(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.locate_me", lambda: self._tool("gods_eye").locate_me()))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.open_place", lambda query: self._open_place(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.route_to", lambda query: self._route_to(query)))
        self.orchestrator.register(Action(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.handle", lambda request, confirmed=False: self._tool("windows_maintenance").handle(request, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.diagnose", lambda: self._tool("windows_maintenance").diagnose()))

    def _first_place(self, query: str) -> tuple[GodsEye, Place]:
        """Resolve the first God’s Eye place matching a user query."""
        eye = self._tool("gods_eye")
        places = eye.search(query)
        if not places:
            raise LookupError(f"No location found for: {query}")
        return eye, places[0]

    def _open_place(self, query: str) -> dict[str, object]:
        """Resolve a place and return the God’s Eye representation for it."""
        eye, place = self._first_place(query)
        return eye.open_place(place)

    def _route_to(self, query: str) -> dict[str, object]:
        """Resolve a destination and generate a route from the permitted current location."""
        eye, place = self._first_place(query)
        snapshot = eye.locate_me()
        if not snapshot.permitted or snapshot.point is None:
            raise PermissionError("Current location is unavailable; enable location access before routing")
        return eye.route(snapshot.point, place)

    def dispatch(self, capability: Capability, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Run one registered operation through capability and confirmation checks."""
        return self.orchestrator.run(capability, operation, *args, confirmation=self.confirmation, **kwargs)

    def handle_text(self, text: str) -> Any:
        """Turn a conservative spoken/text intent into the appropriate guarded operation."""
        intent: Intent = parse_intent(text)
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
            return {"intent": intent, "result": self.dispatch(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.handle", request=request)}
        return intent
