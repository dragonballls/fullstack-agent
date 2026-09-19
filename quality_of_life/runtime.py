"""Unified capability-aware runtime for Jarvis quality-of-life tools."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from .background import BackgroundJobs
from .background_mode import BackgroundModeController
from .activity import ActivityStore
from .gods_eye import GodsEye, Place
from .gods_eye_launcher import GodsEyeLauncher
from .intents import Intent, parse_intent
from .location import FallbackLocationProvider, IpLocationProvider, NominatimGeocoder, SystemLocationProvider
from .location_memory import SavedLocationStore
from .manifest import default_registry
from .orchestrator import Action, ConfirmationHook, QoLOrchestrator
from .permissions import Capability, CapabilityPolicy
from .router import CloudModelRouter, ProviderTarget
from .prism_gateway import PrismGateway
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
        self._activity = ActivityStore()
        self._neural_event_sink: Callable[..., Any] | None = None
        self._neural_world_service: Any | None = None
        self._neural_observation: Any | None = None
        self._register_actions()

    def set_neural_world_service(self, world: Any | None) -> None:
        self._neural_world_service = world

    def neural_entity_search(self, query: str = "", **filters: object) -> list[dict[str, object]]:
        world = self._neural_world_service
        if world is None:
            return []
        return world.search(query, **filters)

    def set_neural_selection(self, entity_id: str | None) -> None:
        self._neural_selection = str(entity_id).strip() if entity_id else None

    def neural_current_selection(self) -> str | None:
        return getattr(self, "_neural_selection", None)

    def neural_shape_library(self) -> list[dict[str, object]]:
        world = self._neural_world_service
        return world.neural_shape_library() if world is not None else []

    def neural_shape_save(self, name: str, shape: object) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_save(name, shape)

    def neural_shape_delete(self, name: str) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_delete(name)

    def neural_entity_shape_set(self, entity_id: str, shape: object) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_apply(entity_id, shape)

    def neural_shape_create(self, label: str, shape: object, **kwargs: object) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_create(label, shape, **kwargs)

    def neural_shape_apply(self, target: str, shape: object, **kwargs: object) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_apply(target, shape, **kwargs)

    def neural_shape_revert(self, target: str) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_revert(target)

    def neural_shape_remove(self, target: str) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_remove(target)

    def neural_shape_revert_all(self) -> dict[str, object]:
        world = self._neural_world_service
        if world is None:
            raise RuntimeError("neural world is unavailable")
        return world.neural_shape_revert_all()

    def neural_task_started(self, title: str) -> str | None:
        world = self._neural_world_service
        if world is None:
            return None
        import uuid
        from .neural_world import EntityKind, LifecycleState
        task_id = "task:" + uuid.uuid4().hex
        node = world.upsert(
            task_id, EntityKind.TASK, str(title)[:300], source="jarvis.orchestrator",
            status="queued", lifecycle=LifecycleState.NEWBORN, energy=1.0, scale=1.05,
            persistent=False, parent_id="jarvis.core",
            metadata={"started_by": "jarvis", "observable": True},
        )
        try:
            world.relate("jarvis.core", task_id, "executing", 0.9)
        except KeyError:
            pass
        return task_id

    def neural_task_update(self, task_id: str | None, *, status: str, step: str, progress: int | None = None) -> None:
        if not task_id or self._neural_world_service is None:
            return
        world = self._neural_world_service
        from .neural_world import LifecycleState
        lifecycle = LifecycleState.ACTIVE if status in {"queued", "running"} else LifecycleState.WAITING if status == "waiting" else LifecycleState.FAILED if status == "failed" else LifecycleState.RETIRED if status in {"cancelled", "succeeded"} else LifecycleState.ACTIVE
        with world._lock:
            entity = world._entities.get(task_id)
            if entity is None:
                return
            entity.status = str(step)[:120]
            entity.lifecycle = lifecycle
            entity.energy = max(0.0, min(1.0, (progress if progress is not None else 60) / 100.0))
            entity.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        world.events.publish("task.progress", entity_id=task_id, payload={"status": status, "step": str(step)[:240], "progress": progress})

    def neural_task_finished(self, task_id: str | None, *, success: bool, message: str = "") -> None:
        if not task_id or self._neural_world_service is None:
            return
        world = self._neural_world_service
        from .neural_world import LifecycleState
        with world._lock:
            entity = world._entities.get(task_id)
            if entity is None:
                return
            entity.lifecycle = LifecycleState.MATURE if success else LifecycleState.FAILED
            entity.status = "succeeded" if success else "failed"
            entity.energy = 0.18 if success else 0.0
            entity.visible = True
            entity.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        world.events.publish("task.finished", entity_id=task_id, payload={"success": bool(success), "message": str(message)[:500]})

    def set_neural_event_sink(self, sink: Callable[..., Any] | None) -> None:
        self._neural_event_sink = sink

    def publish_neural_observation(self, stage: str, message: str, **details: object) -> None:
        controller = self._neural_observation
        if controller is None or not controller.snapshot().get("enabled", False):
            return
        sink = self._neural_event_sink
        if sink is None:
            return
        payload = {
            "stage": str(stage)[:100],
            "message": str(message)[:500],
            **{str(key)[:50]: str(value)[:240] for key, value in details.items()},
        }
        try:
            sink("observation." + payload["stage"], payload=payload)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("neural observation sink failed (%s)", type(exc).__name__)

    def neural_observation_start(self, focus: str = "auto", reason: str = "") -> dict[str, object]:
        if self._neural_observation is None:
            from .neural_observation import NeuralObservationController
            self._neural_observation = NeuralObservationController()
        return self._neural_observation.start(focus, reason)

    def neural_observation_stop(self) -> dict[str, object]:
        if self._neural_observation is None:
            return {"enabled": False, "focus": "auto", "reason": "", "started_at": None}
        return self._neural_observation.stop()

    def neural_observation_state(self) -> dict[str, object]:
        if self._neural_observation is None:
            return {"enabled": False, "focus": "auto", "reason": "", "started_at": None}
        return self._neural_observation.snapshot()

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
        if name in {"computer", "screen", "browser", "clipboard", "windows", "spatial_windows"}:
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
                return lambda: CloudModelRouter((target_config,))
            if os.environ.get("JARVIS_OMNIROUTE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}:
                targets = [CloudModelRouter.omniroute_target()]
                if PrismGateway.enabled() and PrismGateway().configured:
                    targets.insert(0, CloudModelRouter.prism_target())
                return lambda: CloudModelRouter(tuple(targets))
            raise RuntimeError("cloud router is not configured; enable OmniRoute or set JARVIS_CLOUD_BASE_URL and JARVIS_CLOUD_MODEL")
        if name == "self_coding":
            from self_coding import SelfCodingAgent, SelfCodingConfig
            configured_repo = os.environ.get("JARVIS_SELF_CODING_REPO")
            if not configured_repo:
                raise RuntimeError("self-coding is not configured; set JARVIS_SELF_CODING_REPO")
            # Self-coding is preview-first: main publication requires an explicit approve action.
            publish_main = os.environ.get("JARVIS_SELF_CODING_PUBLISH_MAIN", "0").strip().lower() in {"1", "true", "yes", "on"}
            push_branch = os.environ.get("JARVIS_SELF_CODING_PUSH", "0").strip().lower() in {"1", "true", "yes", "on"}
            configured_state = os.environ.get("JARVIS_SELF_CODING_STATE_DIR")
            return lambda: SelfCodingAgent(SelfCodingConfig(
                repo=Path(configured_repo),
                push_branch=push_branch,
                publish_main=publish_main and not push_branch,
                max_passes=max(1, int(os.environ.get("JARVIS_SELF_CODING_MAX_PASSES", "1"))),
                backend=os.environ.get("JARVIS_SELF_CODING_BACKEND", "auto"),
                state_dir=Path(configured_state) if configured_state else None,
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

    def background_mode(self) -> BackgroundModeController:
        """Return the lifecycle controller used by a desktop host."""
        return self._background_mode

    def enter_background(self) -> bool:
        """Enter low-overhead background presentation mode without stopping Jarvis core."""
        return self._background_mode.enter_background()

    def enter_foreground(self) -> bool:
        """Restore foreground presentation mode without recreating Jarvis core."""
        return self._background_mode.enter_foreground()

    def background_status(self) -> dict[str, object]:
        """Return the current background lifecycle state and degraded components."""
        return self._background_mode.status()

    def activity_store(self) -> ActivityStore:
        """Return the bounded process-local activity store."""
        return self._activity

    def activity_snapshot(self, limit: int = 20) -> list[dict[str, object]]:
        """Return JSON-safe activity records for workspace surfaces."""
        return [record.as_dict() for record in self._activity.list(limit)]

    def activity_cancel(self, activity_id: str) -> dict[str, object]:
        """Request cooperative cancellation without terminating the executor."""
        return self._activity.request_cancel(activity_id).as_dict()

    def _register_actions(self) -> None:
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.move", lambda x, y: self._tool("computer").move(x, y)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.click", lambda button="left", clicks=1: self._tool("computer").click(button, clicks)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.scroll", lambda amount: self._tool("computer").scroll(amount)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "hand_control.start", self._start_hand_control))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "hand_control.stop", self._stop_hand_control))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "hand_control.status", lambda: self._tool("hand_control_runtime").status()))
        self.orchestrator.register(Action(Capability.KEYBOARD_CONTROL, "computer.type_text", lambda text: self._tool("computer").type_text(text)))
        self.orchestrator.register(Action(Capability.KEYBOARD_CONTROL, "computer.hotkey", lambda *keys: self._tool("computer").hotkey(*keys)))
        self.orchestrator.register(Action(Capability.APP_LAUNCH, "computer.open_app", lambda command, *args: self._tool("computer").open_app(command, *args)))
        self.orchestrator.register(Action(Capability.APP_LAUNCH, "spatial.open_application", lambda application, embed=True, confirmed=False, wait_seconds=10.0: self.open_application_spatial(application, embed=embed, confirmed=confirmed, wait_seconds=wait_seconds)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "spatial.window_list", lambda: self._tool("spatial_windows").list_windows()))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "spatial.window_embed", lambda identifier, x=24, y=24, width=960, height=640, confirmed=False: self._tool("spatial_windows").embed(identifier, x=x, y=y, width=width, height=height, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "spatial.window_unembed", lambda identifier, confirmed=False: self._tool("spatial_windows").unembed(identifier, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SCREEN_READ, "screen.capture", lambda output=None: self._tool("screen").capture(output)))
        self.orchestrator.register(Action(Capability.CLIPBOARD, "clipboard.read", lambda: self._tool("clipboard").read()))
        self.orchestrator.register(Action(Capability.CLIPBOARD, "clipboard.write", lambda text: self._tool("clipboard").write(text)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.list", lambda: self._tool("windows").list_windows()))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.focus", lambda identifier: self._tool("windows").focus_window(identifier)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.geometry", lambda identifier: self._tool("spatial_windows").rect(identifier).as_dict()))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.move_resize", lambda identifier, x, y, width, height, confirmed=False: self._tool("spatial_windows").move_resize(identifier, x, y, width, height, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.show", lambda identifier, confirmed=False: self._tool("spatial_windows").set_visible(identifier, True, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.hide", lambda identifier, confirmed=False: self._tool("spatial_windows").set_visible(identifier, False, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.restore", lambda identifier, confirmed=False: self._tool("spatial_windows").restore(identifier, confirmed=confirmed)))
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
        self.orchestrator.register(Action(Capability.APP_WRITE, "applications.install", lambda package_id, confirmed=False: self._tool("applications").install(package_id, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.APP_WRITE, "applications.update", lambda package_id, confirmed=False: self._tool("applications").update(package_id, confirmed=confirmed)))
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
        self.orchestrator.register(Action(Capability.ACCOUNT_READ, "accounts.list", lambda: self._tool("account_manager").list_accounts()))
        self.orchestrator.register(Action(Capability.ACCOUNT_READ, "accounts.select", lambda provider, account_id=None, label=None: self._select_account(provider, account_id=account_id, label=label)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.connect", lambda provider, login_hint=None: self._connect_account(provider, login_hint=login_hint)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.refresh", lambda provider, account_id=None, label=None: self._refresh_account(provider, account_id=account_id, label=label)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.disconnect", lambda provider, account_id=None, label=None: self._disconnect_account(provider, account_id=account_id, label=label)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.service_action", lambda operation, provider, account_id=None, label=None, payload=None, confirmed=False: self._service_account_action(operation, provider, account_id=account_id, label=label, payload=payload, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.github_fork", lambda repository, account_id="primary", organization=None: self._github_fork(repository, account_id=account_id, organization=organization)))
        self.orchestrator.register(Action(Capability.REPO_WRITE, "self_coding.run", lambda goal: self._tool("self_coding").run(goal)))
        self.orchestrator.register(Action(Capability.REPO_WRITE, "self_coding.approve", lambda push=True: self._tool("self_coding").approve(push=bool(push))))
        self.orchestrator.register(Action(Capability.REPO_WRITE, "self_coding.undo", lambda push=True: self._tool("self_coding").undo(push=bool(push))))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "self_coding.status", lambda: self._tool("self_coding").status()))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.search", lambda query: self._tool("gods_eye").search(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.locate_me", lambda: self._tool("gods_eye").locate_me()))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.open_place", lambda query: self._open_place(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.route_to", lambda query: self._route_to(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "locations.current", lambda: self._tool("gods_eye").locate_me()))
        self.orchestrator.register(Action(Capability.LOCATION_WRITE, "locations.save", lambda name, latitude, longitude, address=None, accuracy_m=None, source="user", confirmed=False: self._save_location(name, latitude, longitude, address=address, accuracy_m=accuracy_m, source=source, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.LOCATION_WRITE, "locations.save_current", lambda name, address=None, confirmed=False: self._save_current_location(name, address=address, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "locations.get", lambda name: self._tool("locations").get(name)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "locations.list", lambda: self._tool("locations").list()))
        self.orchestrator.register(Action(Capability.LOCATION_WRITE, "locations.delete", lambda name, confirmed=False: self._delete_saved_location(name, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "windows_maintenance.diagnose", lambda: self._tool("windows_maintenance").diagnose()))
        self.orchestrator.register(Action(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.handle", lambda request, confirmed=False: self._tool("windows_maintenance").handle(request, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.list", lambda: self._tool("devices").list()))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.refresh", lambda: self._tool("devices").refresh()))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.state", lambda device_id: self._tool("devices").state(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.select", lambda device_id: self._tool("devices").select(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.active", lambda: self._tool("devices").active()))
        self.orchestrator.register(Action(Capability.DEVICE_SCREEN, "devices.screen", lambda device_id: self._tool("devices").screen(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_SCREEN, "devices.screen_all", lambda: self._tool("devices").screen_all()))
        self.orchestrator.register(Action(Capability.DEVICE_INPUT, "devices.input", lambda device_id, kind, **kwargs: self._tool("devices").input(device_id, kind, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_NOTIFICATIONS, "devices.notifications", lambda device_id: self._tool("devices").notifications(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_FILES, "devices.files", lambda device_id, direction, path, **kwargs: self._tool("devices").transfer(device_id, direction, path, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_APPS, "devices.apps", lambda device_id, app_id, **kwargs: self._tool("devices").open_app(device_id, app_id, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_AUTOMATION, "devices.automate", lambda device_id, steps, **kwargs: self._tool("devices").automate(device_id, steps, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_INPUT, "devices.hand_target", lambda device_id: self._set_hand_target(device_id)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.advanced.inspect", lambda: self._neural_advanced_command("inspect", "inspect")))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "neural.workspace.compose", lambda operation, payload=None: self._neural_advanced_command("workspace", operation, payload)))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "neural.cross_application.transfer", lambda kind, source, destination, payload_ref=None: self._neural_advanced_command("cross_application", "transfer", {"kind": kind, "source": source, "destination": destination, "payload_ref": payload_ref})))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "neural.browser.research_wall", lambda id, pages, columns=3: self._neural_advanced_command("browser", "research_wall", {"id": id, "pages": pages, "columns": columns})))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.performance.sample", lambda **metrics: self._neural_advanced_command("performance", "sample", metrics)))
        self.orchestrator.register(Action(Capability.SYSTEM_SETTINGS, "neural.display.update", lambda id, state=None: self._neural_advanced_command("display", "update", {"id": id, "state": state or {}})))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "neural.history.snapshot", lambda id, world: self._neural_advanced_command("history", "snapshot", {"id": id, "world": world})))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.planning.dry_run", lambda actions, known_good=None: self._neural_advanced_command("planning", "dry_run", {"actions": actions, "known_good": known_good})))
        self.orchestrator.register(Action(Capability.SYSTEM_MAINTENANCE, "neural.reliability.reset", lambda region=None: self._neural_advanced_command("reliability", "reset", {"region": region})))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.audio.event", lambda kind, source="jarvis", position=None, intensity=0.5, priority=0.5: self._neural_advanced_command("audio", "event", {"kind": kind, "source": source, "position": position, "intensity": intensity, "priority": priority})))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "neural.multiuser.region", lambda id, owner, shared=False, members=None: self._neural_advanced_command("multi_user", "region", {"id": id, "owner": owner, "shared": shared, "members": members or []})))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.remote.region", lambda id, state=None: self._neural_advanced_command("remote", "upsert", {"id": id, "state": state or {}})))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.streaming.region", lambda id, priority=0.5: self._neural_advanced_command("streaming", "request", {"id": id, "priority": priority})))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.simulation.run", lambda scenario="cpu_stress", count=1000: self._neural_advanced_command("simulation", "benchmark", {"scenario": scenario, "count": count})))
        self.orchestrator.register(Action(Capability.SYSTEM_SETTINGS, "neural.accessibility.update", lambda **settings: self._neural_advanced_command("accessibility", "update", settings)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.fullstack.command", lambda domain, operation, payload=None, confirmed=False: self._neural_fullstack_execute(domain, operation, payload, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.shape.create", lambda label, shape, position=(0.0, 0.0, 0.0), scale=1.0, rotation_speed=0.0, rotation_unit=None, rotation_axis="y": self.neural_shape_create(label, shape, position=position, scale=scale, rotation_speed=rotation_speed, rotation_unit=rotation_unit, rotation_axis=rotation_axis)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.shape.apply", lambda target, shape, rotation_speed=0.0, rotation_unit=None, rotation_axis="y": self.neural_shape_apply(target, shape, rotation_speed=rotation_speed, rotation_unit=rotation_unit, rotation_axis=rotation_axis)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.shape.remove", lambda target: self.neural_shape_remove(target)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.shape.revert", lambda target: self.neural_shape_revert(target)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.shape.revert_all", lambda: self.neural_shape_revert_all()))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.master.status", lambda: self._neural_advanced_command("master", "status", {})))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.master.execute", lambda feature, payload=None, confirmed=False: self._neural_master_execute(feature, payload, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "neural.master.smoke", lambda limit=None: self._neural_advanced_command("master", "smoke", {"limit": limit} if limit is not None else {})))

    def _neural_domain_capability(self, domain: str, operation: str = "") -> Capability:
        name = str(domain).strip().casefold()
        op = str(operation).strip().casefold()
        if name in {"spatial_windows", "desktop_3d"}:
            return Capability.WINDOW_CONTROL
        if name == "cross_application":
            return Capability.CLIPBOARD if "clipboard" in op else Capability.FILE_WRITE
        if name == "browser":
            return Capability.BROWSER_CONTROL
        if name in {"hardware_display", "multi_monitor", "accessibility", "accessibility_full"}:
            return Capability.SYSTEM_SETTINGS
        if name == "memory_history":
            return Capability.FILE_WRITE
        if name == "reliability":
            return Capability.SYSTEM_MAINTENANCE
        if name in {"multi_user", "multi_user_shared"}:
            return Capability.ACCOUNT_WRITE
        if name in {"remote", "remote_computing"} and ("control" in op or "sync" in op):
            return Capability.SYSTEM_MAINTENANCE
        if name in {"xr", "xr_full"} and op == "haptic":
            return Capability.DEVICE_INPUT
        if name == "xr":
            return Capability.SYSTEM_SETTINGS
        return Capability.SYSTEM_DIAGNOSTICS

    def _neural_fullstack_execute(self, domain: str, operation: str, payload: Mapping[str, Any] | None = None, *, confirmed: bool = False) -> dict[str, object]:
        capability = self._neural_domain_capability(domain, operation)
        self.policy.check(capability)
        if self.policy.needs_confirmation(capability) and not confirmed:
            if self.confirmation is None or not self.confirmation(capability, "neural.fullstack.command"):
                raise PermissionError(f"Confirmation is required: {capability.value}/neural.fullstack.command")
        return self._neural_advanced_command("fullstack", "route", {"domain": domain, "operation": operation, "payload": dict(payload or {})})

    def _neural_master_capability(self, feature: str) -> Capability:
        from .neural_advanced import MASTER_SCOPE
        name = str(feature).strip()
        category = next((key for key, values in MASTER_SCOPE.items() if name in values), None)
        if category in {"spatial_windows", "desktop_3d"}:
            return Capability.WINDOW_CONTROL
        if category == "cross_application":
            return Capability.CLIPBOARD if "clipboard" in name.casefold() else Capability.FILE_WRITE
        if category == "browser":
            return Capability.BROWSER_CONTROL
        if category == "hardware_display" or category == "multi_monitor" or category in {"accessibility", "accessibility_full"}:
            return Capability.SYSTEM_SETTINGS
        if category == "memory_history":
            return Capability.FILE_WRITE
        if category == "reliability":
            return Capability.SYSTEM_MAINTENANCE
        if category == "remote_computing" and ("control" in name.casefold() or "synchronization" in name.casefold()):
            return Capability.SYSTEM_MAINTENANCE
        if category == "multi_user" or category == "multi_user_shared":
            return Capability.ACCOUNT_WRITE
        if category in {"optimization_intelligence"}:
            return Capability.SYSTEM_SETTINGS
        if category in {"xr", "xr_full"} and "haptic" in name.casefold():
            return Capability.DEVICE_INPUT
        if category in {"audio", "games", "time_machine", "world_streaming", "large_world_proof", "advanced_analytics", "performance", "performance_intelligence", "search_navigation", "lifecycle", "planning", "testing", "developer_tools", "remote", "simulation", "simulation_world", "core_neural"}:
            return Capability.SYSTEM_DIAGNOSTICS
        if category == "xr":
            return Capability.SYSTEM_SETTINGS
        return Capability.SYSTEM_DIAGNOSTICS

    def _neural_master_execute(self, feature: str, payload: Mapping[str, Any] | None = None, *, confirmed: bool = False) -> dict[str, object]:
        capability = self._neural_master_capability(feature)
        self.policy.check(capability)
        if self.policy.needs_confirmation(capability) and not confirmed:
            if self.confirmation is None or not self.confirmation(capability, "neural.master.execute"):
                raise PermissionError(f"Confirmation is required: {capability.value}/neural.master.execute")
        return self._neural_advanced_command("master", "execute", {"feature": feature, "payload": dict(payload or {})})

    def _neural_advanced_command(self, domain: str, operation: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        world = self._neural_world_service
        if world is None or not hasattr(world, "neural_advanced_command"):
            raise RuntimeError("advanced neural world is unavailable")
        return world.neural_advanced_command(domain, operation, payload or {})

    def open_application_spatial(self, application: str, *, confirmed: bool = False, embed: bool = True, wait_seconds: float = 10.0) -> dict[str, object]:
        self.policy.check(Capability.APP_LAUNCH)
        if embed and not confirmed:
            raise PermissionError("confirmation is required to open an application in spatial mode")
        if self.policy.needs_confirmation(Capability.APP_LAUNCH) and not confirmed:
            raise PermissionError("application launch requires confirmation")
        computer = self._tool("computer")
        spatial = self._tool("spatial_windows")
        baseline = {int(item["handle"]) for item in spatial.list_windows() if item.get("handle") is not None}
        launched = None
        requested = str(application).strip()
        if not requested:
            raise ValueError("application is required")
        try:
            resolved = self._tool("applications").resolve(requested)
            computer.open_known_app(resolved.name)
            title_hint = resolved.name.casefold()
        except Exception:
            launched = computer.open_app(requested)
            title_hint = requested.casefold()
        deadline = __import__("time").monotonic() + max(0.0, min(60.0, float(wait_seconds)))
        selected = None
        while __import__("time").monotonic() < deadline:
            for item in spatial.list_windows():
                handle = int(item.get("handle", 0) or 0)
                if not handle or handle in baseline:
                    continue
                title = str(item.get("title", ""))
                pid = int(item.get("process_id", 0) or 0)
                launched_pid = int(getattr(launched, "pid", 0) or 0)
                if (launched_pid and pid == launched_pid) or (title_hint and title_hint in title.casefold()):
                    selected = item
                    break
            if selected is not None:
                break
            __import__("time").sleep(0.25)
        result: dict[str, object] = {
            "launched": launched is not None or selected is not None,
            "pid": int(getattr(launched, "pid", 0) or 0),
            "embedded": False,
            "window": selected,
        }
        if selected is None or not embed:
            return result
        if self.policy.needs_confirmation(Capability.WINDOW_CONTROL) and not confirmed:
            result["embedding_error"] = "window-control confirmation required"
            return result
        try:
            rect = selected.get("rect", {}) if isinstance(selected, dict) else {}
            result["embedding"] = spatial.embed(
                int(selected["handle"]),
                x=24, y=24,
                width=min(1280, int(rect.get("width", 960) or 960)),
                height=min(900, int(rect.get("height", 640) or 640)),
                confirmed=confirmed,
            )
            result["embedded"] = True
        except (RuntimeError, LookupError, ValueError, PermissionError) as exc:
            result["embedding_error"] = type(exc).__name__
        return result

    def _start_hand_control(self) -> dict[str, object]:
        runtime = self._tool("hand_control_runtime")
        started = runtime.start()
        return {"enabled": bool(started and runtime.enabled), "url": runtime.url, "started": bool(started)}

    def _stop_hand_control(self) -> dict[str, object]:
        runtime = self._tool("hand_control_runtime")
        runtime.stop()
        return {"enabled": False, "url": runtime.url, "stopped": True}

    def _set_hand_target(self, device_id: str | None) -> Any:
        if device_id is not None and self._tool("devices").registry.provider_for(device_id) is None:
            raise LookupError(f"No device found for: {device_id}")
        self._tool("hand_control").set_device_target(device_id)
        return {"target_device_id": device_id}

    def _account_provider(self, provider: str | ServiceProvider) -> ServiceProvider:
        if isinstance(provider, ServiceProvider):
            return provider
        try:
            return ServiceProvider(str(provider).strip().lower())
        except ValueError as exc:
            raise ValueError(f"unsupported account provider: {provider}") from exc

    def _select_account(self, provider: str | ServiceProvider, *, account_id: str | None = None, label: str | None = None) -> dict[str, str]:
        identity = self._tool("account_manager").select_account(self._account_provider(provider), account_id=account_id, label=label)
        return {"provider": identity.provider.value, "account_id": identity.account_id, "label": identity.label, "state": identity.state.value}

    def _connect_account(self, provider: str | ServiceProvider, *, login_hint: str | None = None) -> dict[str, str]:
        connection = self._tool("account_manager").connect_account(self._account_provider(provider), login_hint=login_hint)
        identity = connection.identity
        return {"provider": identity.provider.value, "account_id": identity.account_id, "label": identity.label, "state": connection.authorization_state}

    def _refresh_account(self, provider: str | ServiceProvider, *, account_id: str | None = None, label: str | None = None) -> dict[str, str]:
        identity = self._tool("account_manager").refresh_account(self._account_provider(provider), account_id=account_id, label=label)
        return {"provider": identity.provider.value, "account_id": identity.account_id, "label": identity.label, "state": identity.state.value, "refreshed": "true"}

    def _disconnect_account(self, provider: str | ServiceProvider, *, account_id: str | None = None, label: str | None = None) -> dict[str, str]:
        normalized = self._account_provider(provider)
        selected = self._tool("account_manager").select_account(normalized, account_id=account_id, label=label)
        self._tool("account_manager").disconnect_account(normalized, account_id=selected.account_id)
        return {"provider": normalized.value, "account_id": selected.account_id, "disconnected": "true"}

    def _service_account_action(self, operation: str, provider: str | ServiceProvider, *, account_id: str | None = None, label: str | None = None, payload: dict[str, Any] | None = None, confirmed: bool = False) -> Any:
        return self._tool("account_manager").service_action(operation, provider=self._account_provider(provider), account_id=account_id, label=label, payload=payload, confirmed=confirmed)

    def _github_fork(self, repository: str, *, account_id: str = "primary", organization: str | None = None) -> dict[str, str]:
        from .account_access import GitHubRepositoryClient
        return GitHubRepositoryClient().fork_repository(repository, account_id=account_id, access=self._tool("account_access"), confirmed=True, organization=organization)

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

    def _save_location(self, name: str, latitude: float, longitude: float, *, address: str | None = None, accuracy_m: float | None = None, source: str = "user", confirmed: bool = False) -> Any:
        if not confirmed:
            raise PermissionError("Saving a location requires confirmation")
        from .gods_eye import GeoPoint
        return self._tool("locations").save(name, GeoPoint(float(latitude), float(longitude)), address=address, accuracy_m=accuracy_m, source=source)

    def _save_current_location(self, name: str, *, address: str | None = None, confirmed: bool = False) -> Any:
        if not confirmed:
            raise PermissionError("Saving the current location requires confirmation")
        snapshot = self._tool("gods_eye").locate_me()
        return self._tool("locations").save_current(name, snapshot, address=address)

    def _delete_saved_location(self, name: str, *, confirmed: bool = False) -> bool:
        if not confirmed:
            raise PermissionError("Deleting a saved location requires confirmation")
        return self._tool("locations").delete(name)

    def _resolve_device(self, reference: str) -> str:
        value = reference.strip()
        if not value:
            raise ValueError("device reference must not be empty")
        devices = list(self._tool("devices").list())
        exact = [d for d in devices if d.device_id == value]
        if exact:
            return exact[0].device_id
        matches = [d for d in devices if d.label.casefold() == value.casefold()]
        if len(matches) == 1:
            return matches[0].device_id
        if len(matches) > 1:
            raise ValueError(f"Multiple devices match: {reference}")
        raise LookupError(f"No device found for: {reference}")

    def dispatch(self, capability: Capability, operation: str, *args: Any, **kwargs: Any) -> Any:
        return self.orchestrator.run(capability, operation, *args, confirmation=self.confirmation, **kwargs)

    def handle_assistant_request(self, text: str, confirmed: bool = False) -> dict[str, Any]:
        result = self._assistant_orchestrator().execute(text, confirmed=confirmed)
        return {"text": result.text, "profile": result.profile, "verified": result.verified, "needs_confirmation": result.needs_confirmation, "parallel_tasks_completed": result.parallel_tasks_completed, "providers": result.providers, "latency_ms": result.latency_ms, "errors": result.errors}

    def handle_assistant_stream(self, text: str, confirmed: bool = False) -> Iterator[Any]:
        yield from self._assistant_orchestrator().execute_stream(text, confirmed=confirmed)

    def handle_text(self, text: str) -> Any:
        intent: Intent = parse_intent(text)
        if intent.kind == "hand_control_start":
            return {"intent": intent, "result": self.dispatch(Capability.MOUSE_CONTROL, "hand_control.start")}
        if intent.kind == "hand_control_stop":
            return {"intent": intent, "result": self.dispatch(Capability.MOUSE_CONTROL, "hand_control.stop")}
        if intent.kind == "device_hand_target":
            reference = intent.arguments.get("device")
            device_id = self._resolve_device(str(reference)) if reference else None
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_INPUT, "devices.hand_target", device_id)}
        if intent.kind == "device_list":
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_READ, "devices.list")}
        if intent.kind == "device_refresh":
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_READ, "devices.refresh")}
        if intent.kind == "device_select":
            device_id = self._resolve_device(str(intent.arguments["device"]))
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_READ, "devices.select", device_id)}
        if intent.kind == "device_screen_all":
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_SCREEN, "devices.screen_all")}
        if intent.kind == "device_screen":
            reference = intent.arguments.get("device")
            if reference:
                device_id = self._resolve_device(str(reference))
            else:
                active = self.dispatch(Capability.DEVICE_READ, "devices.active")
                if not active.ok:
                    return {"intent": intent, "result": active}
                device_id = active.data["state"].device_id
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_SCREEN, "devices.screen", device_id)}
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
        if intent.kind == "save_current_location":
            name = str(intent.arguments["name"])
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_WRITE, "locations.save_current", name=name)}
        if intent.kind == "save_place":
            place_query = str(intent.arguments["place"])
            name = str(intent.arguments["name"])
            place = self._first_place(place_query)[1]
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_WRITE, "locations.save", name=name, latitude=place.point.latitude, longitude=place.point.longitude, source=place.provider)}
        if intent.kind == "saved_location":
            saved = self.dispatch(Capability.LOCATION_READ, "locations.get", name=str(intent.arguments["name"]))
            if saved is None:
                raise LookupError(f"No saved location found for: {intent.arguments['name']}")
            return {"intent": intent, "result": saved}
        if intent.kind == "delete_saved_location":
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_WRITE, "locations.delete", name=str(intent.arguments["name"]))}
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
