"""Unified capability-aware runtime for Jarvis quality-of-life tools."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from .background import BackgroundJobs
from .gods_eye import GodsEye, Place
from .location import NominatimGeocoder, SystemLocationProvider
from .manifest import default_registry
from .orchestrator import Action, ConfirmationHook, QoLOrchestrator
from .permissions import Capability, CapabilityPolicy


class JarvisRuntime:
    """Lazy tool host that keeps capability and confirmation checks centralized."""

    def __init__(
        self,
        policy: CapabilityPolicy,
        confirmation: ConfirmationHook | None = None,
        factories: dict[str, Callable[[], Any]] | None = None,
    ) -> None:
        self.policy = policy
        self.confirmation = confirmation
        self.registry = default_registry()
        self._factories = dict(factories or {})
        self._instances: dict[str, Any] = {}
        self.orchestrator = QoLOrchestrator(policy)
        self._register_actions()

    def available_tools(self) -> tuple[str, ...]:
        return self.registry.names()

    def _factory_from_spec(self, name: str) -> Callable[[], Any]:
        if name in self._factories:
            return self._factories[name]
        spec = self.registry.get(name)
        module_name, attribute = spec.factory.rsplit(".", 1)
        target = getattr(importlib.import_module(module_name), attribute)
        if name in {"computer", "screen", "browser", "clipboard", "windows"}:
            return lambda: target(self.policy)
        if name == "gods_eye":
            return lambda: GodsEye(NominatimGeocoder(), SystemLocationProvider())
        if name == "background":
            return lambda: BackgroundJobs()
        raise RuntimeError(f"No runtime factory is configured for: {name}")

    def _tool(self, name: str) -> Any:
        if name not in self._instances:
            self._instances[name] = self._factory_from_spec(name)()
        return self._instances[name]

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
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.open_url", lambda url: self._tool("browser").open_url(url)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.search", lambda query: self._tool("gods_eye").search(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.locate_me", lambda: self._tool("gods_eye").locate_me()))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.open_place", lambda query: self._open_place(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.route_to", lambda query: self._route_to(query)))

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
