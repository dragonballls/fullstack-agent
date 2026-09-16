"""Unified capability-aware runtime for Jarvis quality-of-life tools."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from .background import BackgroundJobs
from .background_mode import BackgroundModeController
from .gods_eye import GodsEye, Place
from .gods_eye_launcher import GodsEyeLauncher
from .intents import Intent, parse_intent
from .location import FallbackLocationProvider, IpLocationProvider, NominatimGeocoder, SystemLocationProvider
from .location_memory import SavedLocationStore
from .manifest import default_registry
from .orchestrator import Action, ConfirmationHook, QoLOrchestrator
from .permissions import Capability, CapabilityPolicy
from .router import CloudModelRouter, ProviderTarget
from .account_access import AccountAccessRegistry
from .account_integrations import ServiceProvider


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
        self._background_mode = BackgroundModeController()
        self._register_actions()

    def available_tools(self) -> tuple[str, ...]:
        return self.registry.names()

    def _factory_from_spec(self, name: str) -> Callable[[], Any]:
        if name in self._factories:
            return self._factories[name]
        spec = self.registry.get(name)
        target = spec.resolve()
        if name == "account_access":
            return lambda: target.from_environment()
        if name == "account_manager":
            return lambda: target(account_access=self._tool("account_access"))
        if name in {"computer", "screen", "browser", "clipboard", "windows"}:
            return lambda: target(self.policy)
        if name == "browser_registry":
            return lambda: target()
        if name in {"files", "applications", "processes", "system"}:
            return lambda: target(self.policy)
        if name == "devices":
            def device_confirmation(operation: str) -> bool:
                if self.confirmation is None:
                    return False
                capability = QoLOrchestrator.policy_operation_capability(operation)
                return self.confirmation(capability, operation)
            return lambda: target(self.policy, confirmation=device_confirmation)
        if name == "scheduler":
            return lambda: target(self._tool("background"))
        if name == "gods_eye":
            return lambda: GodsEye(NominatimGeocoder(), FallbackLocationProvider(SystemLocationProvider(), IpLocationProvider()))
        if name == "locations":
            configured = os.environ.get("JARVIS_LOCATION_STORE")
            return lambda: SavedLocationStore(configured)
        if name == "hand_control_runtime":
            return lambda: target()
        if name == "hand_control":
            return lambda: target(enabled=False, controller=self._tool("computer"), device_adapter=self._tool("devices").input_adapter)
        if name == "hand_control_server":
            return lambda: target
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
            publish_main = os.environ.get("JARVIS_SELF_CODING_PUBLISH_MAIN", "1").strip().lower() in {"1", "true", "yes", "on"}
            push_branch = os.environ.get("JARVIS_SELF_CODING_PUSH", "0").strip().lower() in {"1", "true", "yes", "on"}
            return lambda: SelfCodingAgent(SelfCodingConfig(
                repo=Path(configured_repo),
                push_branch=push_branch,
                publish_main=publish_main and not push_branch,
                max_passes=max(1, int(os.environ.get("JARVIS_SELF_CODING_MAX_PASSES", "1"))),
                backend=os.environ.get("JARVIS_SELF_CODING_BACKEND", "auto"),
            ))
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
