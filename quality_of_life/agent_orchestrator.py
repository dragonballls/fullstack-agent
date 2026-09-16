"""Low-latency multi-model orchestration above the guarded QOL runtime."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Iterable, Iterator

from .capabilities import operation
from .computer_use import ComputerUseAgent, RouterComputerUsePlanner, ScreenObserver
from .intents import parse_intent
from .orchestration import OrchestrationPlan, RequestProfile, build_plan
from .permissions import Capability
from .planner import PlanError, plan_request
from .router import CloudModelRouter, ProviderResult


@dataclass(frozen=True)
class OrchestrationEvent:
    kind: str
    message: str
    data: dict[str, Any] | None = None


@dataclass(frozen=True)
class OrchestrationResult:
    text: str
    profile: str
    verified: bool
    needs_confirmation: bool
    parallel_tasks_completed: int
    providers: tuple[str, ...]
    latency_ms: int
    errors: tuple[str, ...] = ()


_MUTATING_MARKERS = (
    "click", "type ", "press ", "close ", "delete ", "remove ", "stop ",
    "kill ", "launch ", "open ", "install ", "uninstall ", "change ", "disable ",
    "enable ", "repair ", "fix ", "write ", "commit ", "push ", "modify ",
)


class AgentOrchestrator:
    """Coordinate cloud-model calls without bypassing runtime policy."""

    def __init__(self, router: CloudModelRouter, runtime: Any, max_parallel: int | None = None) -> None:
        self.router = router
        self.runtime = runtime
        self.max_parallel = max_parallel

    @staticmethod
    def _needs_confirmation(text: str) -> bool:
        normalized = " ".join(text.lower().split())
        return any(marker in normalized for marker in _MUTATING_MARKERS)

    def _looks_like_computer_goal(self, text: str) -> bool:
        normalized = " ".join(text.casefold().split())
        markers = (
            "computer", "desktop", "application", " app", "game", "roblox", "studio", "minecraft",
            "mouse", "cursor", "click", "double click", "right click", "type into", "press the",
            "launch ", "interact with", "on my screen", "on screen", "window", "menu", "button",
            "play ", "navigate in", "use the ",
        )
        if any(marker.strip() in normalized for marker in markers):
            return True
        if normalized.startswith("open "):
            candidate = normalized[5:].split(" and ", 1)[0].split(" then ", 1)[0].strip()
            if candidate:
                try:
                    apps = self.runtime._tool("applications").list()
                    return any(getattr(app, "name", "").casefold() == candidate for app in apps)
                except Exception:
                    return False
        return False

    @staticmethod
    def _messages(prompt: str) -> list[dict[str, str]]:
        return [{"role": "user", "content": prompt}]

    def _specialist_requests(self, plan: OrchestrationPlan, deterministic_context: str = "") -> list[tuple[list[dict[str, str]], RequestProfile]]:
        context = f"\n\nAuthoritative deterministic result:\n{deterministic_context}" if deterministic_context else ""
        return [
            (
                self._messages(f"{task.prompt}\n\nUser request:\n{plan.primary.prompt}{context}\n\nReturn concise findings only; do not execute anything."),
                task.profile,
            )
            for task in plan.parallel_tasks
        ]

    def _execute_typed_plan(self, text: str, confirmed: bool) -> tuple[str, bool, bool, list[str]]:
        if not hasattr(self.router, "complete"):
            return "", False, False, []
        try:
            plan = plan_request(self.router, text)
        except (PlanError, AttributeError):
            return "", False, False, []
        if not plan.steps:
            return "", False, False, []
        needs_confirmation = self._needs_confirmation(text) and not confirmed
        if needs_confirmation:
            return "This request requires confirmation before I make changes or interact with external applications.", False, True, []
        results: list[str] = []
        errors: list[str] = []
        verified = True
        for step in plan.steps:
            try:
                spec = operation(step.operation)
                result = self.runtime.dispatch(spec.capability, step.operation, **step.arguments)
                results.append(f"{step.operation}: {result}")
            except Exception as exc:
                verified = False
                errors.append(f"{step.operation}: {exc}")
                break
        if not results:
            return "", False, False, errors
        return "\n".join(results), verified, False, errors

    def _deterministic_context(self, text: str, confirmed: bool) -> tuple[str, bool, list[str], bool]:
        """Execute explicitly supported intents through the existing policy-gated runtime."""
        intent = parse_intent(text)
        if intent.kind == "browser_open":
            browser = str(intent.arguments["browser"])
            url = intent.arguments.get("url")
            if not confirmed:
                return f"I can open {browser}, but confirmation is required before controlling a browser.", False, [], True
            if url:
                result = self.runtime.dispatch(Capability.BROWSER_CONTROL, "browser.open_url", url=str(url), browser=browser)
            else:
                result = self.runtime.dispatch(Capability.BROWSER_CONTROL, "browser.start", browser=browser)
            return f"Opened {browser}. {result or ''}".strip(), True, [], False
        if intent.kind == "application_list":
            result = self.runtime.dispatch(Capability.APP_READ, "applications.list")
            return str(result), True, [], False
        if intent.kind == "application_uninstall":
            if not confirmed:
                return "An application uninstall was requested, but confirmation is required before removing software.", False, [], True
            result = self.runtime.dispatch(Capability.APP_WRITE, "applications.uninstall", name=str(intent.arguments["name"]), confirmed=True)
            return f"Uninstall verified: {result}", True, [], False
        if intent.kind == "process_list":
            result = self.runtime.dispatch(Capability.PROCESS_READ, "processes.list")
            return str(result), True, [], False
        if intent.kind == "system_inspect":
            result = self.runtime.dispatch(Capability.SYSTEM_DIAGNOSTICS, "system.inspect")
            return str(result), True, [], False
        if intent.kind == "file_read":
            result = self.runtime.dispatch(Capability.FILE_READ, "files.read", path=str(intent.arguments["path"]))
            return str(result), True, [], False
        if intent.kind == "file_delete":
            if not confirmed:
                return "A file deletion was requested, but confirmation is required before deleting anything.", False, [], True
            result = self.runtime.dispatch(Capability.FILE_DELETE, "files.delete", path=str(intent.arguments["path"]))
            return f"File deletion verified: {result}", True, [], False
        if intent.kind == "windows_maintenance":
            request = str(intent.arguments["request"])
            lowered = request.casefold()
            if "diagnos" in lowered and not any(word in lowered for word in ("fix", "repair", "clean")):
                result = self.runtime.dispatch(Capability.SYSTEM_DIAGNOSTICS, "windows_maintenance.diagnose")
                return str(getattr(result, "message", result)), True, [], False
            if confirmed:
                result = self.runtime.dispatch(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.handle", request=request, confirmed=True)
                operation_results = getattr(result, "results", ())
                verified = bool(operation_results) and all(getattr(item, "success", False) and getattr(item, "verified", False) for item in operation_results)
                return str(getattr(result, "message", result)), verified, [], False
            return "A maintenance change was requested, but confirmation is required before anything is modified.", False, [], True
        if intent.kind == "locate_me":
            result = self.runtime.dispatch(Capability.LOCATION_READ, "locations.current")
            return str(result), True, [], False
        if intent.kind == "save_current_location":
            name = str(intent.arguments["name"])
            if not confirmed:
                return f"I can save your current location as \"{name}\", but I need confirmation first.", False, [], True
            result = self.runtime.dispatch(Capability.LOCATION_WRITE, "locations.save_current", name=name, confirmed=True)
            return f"Saved {name}: {result}", True, [], False
        if intent.kind == "save_place":
            place_query = str(intent.arguments["place"])
            name = str(intent.arguments["name"])
            if not confirmed:
                return f"I can save {place_query} as \"{name}\", but I need confirmation first.", False, [], True
            eye = self.runtime._tool("gods_eye")
            places = eye.search(place_query)
            if not places:
                return "", False, [f"No location found for: {place_query}"], False
            place = places[0]
            result = self.runtime.dispatch(Capability.LOCATION_WRITE, "locations.save", name=name, latitude=place.point.latitude, longitude=place.point.longitude, source=place.provider, confirmed=True)
            return f"Saved {name}: {result}", True, [], False
        if intent.kind == "saved_location":
            name = str(intent.arguments["name"])
            result = self.runtime.dispatch(Capability.LOCATION_READ, "locations.get", name=name)
            if result is None:
                return "", False, [f"No saved location found for: {name}"], False
            return str(result), True, [], False
        if intent.kind == "delete_saved_location":
            name = str(intent.arguments["name"])
            if not confirmed:
                return f"I can delete the saved location \"{name}\", but I need confirmation first.", False, [], True
            result = self.runtime.dispatch(Capability.LOCATION_WRITE, "locations.delete", name=name, confirmed=True)
            return f"Deleted {name}: {result}", True, [], False
        if intent.kind == "screen_read":
            result = self.runtime.dispatch(Capability.SCREEN_READ, "screen.capture")
            return str(result), True, [], False
        if intent.kind == "place_search":
            query = str(intent.arguments["query"])
            if text.casefold().startswith("open "):
                candidate = query.casefold().split(" and ", 1)[0].split(" then ", 1)[0].strip()
                try:
                    apps = self.runtime._tool("applications").list()
                    if any(getattr(app, "name", "").casefold() == candidate for app in apps):
                        return "", False, [], False
                except Exception:
                    pass
            result = self.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.open_place", query=query)
            return str(result), True, [], False
        if intent.kind == "route":
            query = str(intent.arguments["query"])
            if query.casefold().startswith("my "):
                name = query[3:].strip()
                saved = self.runtime.dispatch(Capability.LOCATION_READ, "locations.get", name=name)
                if saved is not None:
                    snapshot = self.runtime.dispatch(Capability.LOCATION_READ, "locations.current")
                    if not snapshot.permitted or snapshot.point is None:
                        return "Current location is unavailable; enable location access before routing.", False, [], False
                    eye = self.runtime._tool("gods_eye")
                    from .gods_eye import Place
                    destination = Place(saved.name, saved.point, None, saved.source)
                    return str(eye.route(snapshot.point, destination)), True, [], False
            result = self.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.route_to", query=query)
            return str(result), True, [], False
        if intent.kind == "computer_action":
            if not confirmed:
                return "A computer-control action was requested, but confirmation is required before moving the mouse.", False, [], True
            result = self.runtime.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=intent.arguments["x"], y=intent.arguments["y"])
            return str(result), True, [], False
        return "", False, [], False

    def _computer_goal_context(self, text: str, confirmed: bool) -> tuple[str, bool, bool, list[str], str | None]:
        if not confirmed:
            return "This goal requires confirmation before Jarvis controls the computer.", False, True, [], None
        try:
            computer = self.runtime._tool("computer")
            screen = self.runtime._tool("screen")
            agent = ComputerUseAgent(
                RouterComputerUsePlanner(self.router),
                computer,
                ScreenObserver(screen),
                max_steps=max(1, min(int(self.max_parallel or 10), 10)),
            )
            result = agent.run(text)
        except Exception as exc:
            return "", False, False, [f"computer goal: {exc}"], None
        if result.completed:
            return f"Computer goal completed and re-observed after {result.steps_executed} action(s).", True, False, list(result.errors), "computer-use"
        return f"Computer goal was not fully verified after {result.steps_executed} action(s).", False, False, list(result.errors), "computer-use"

    def _coding_context(self, text: str, confirmed: bool) -> tuple[str, bool]:
        if not confirmed:
            return "A repository-changing coding request requires confirmation before self-coding can run.", False
        result = self.runtime.dispatch(Capability.REPO_WRITE, "self_coding.run", goal=text)
        branch = str(result)
        return f"Self-coding completed on verified branch: {branch}", bool(branch)

    @staticmethod
    def _synthesis_prompt(plan: OrchestrationPlan, results: Iterable[ProviderResult], deterministic_context: str = "") -> str:
        findings: list[str] = []
        if deterministic_context:
            findings.append("Deterministic result (authoritative; report faithfully): " + deterministic_context)
        for index, result in enumerate(results, start=1):
            if result.ok and result.text:
                findings.append(f"Specialist {index}: {result.text}")
            elif result.error:
                findings.append(f"Specialist {index}: unavailable ({result.error})")
        context = "\n\n".join(findings) or "No specialist findings were available."
        return (
            "Act as the primary Jarvis response model. Synthesize the findings below into one accurate, concise response. "
            "Do not claim an action was performed unless a deterministic tool result is supplied. Preserve safety boundaries.\n\n"
            f"User request:\n{plan.primary.prompt}\n\nSpecialist findings:\n{context}"
        )

    def execute(self, text: str, confirmed: bool = False) -> OrchestrationResult:
        started = time.monotonic()
        plan = build_plan(text)
        errors: list[str] = []
        providers: list[str] = []
        deterministic_context, deterministic_verified, deterministic_errors, needs_confirmation = self._deterministic_context(text, confirmed)
        errors.extend(deterministic_errors)
        if not deterministic_context and not needs_confirmation and self._looks_like_computer_goal(text) and not plan.parallel_tasks:
            computer_context, computer_verified, computer_confirmation, computer_errors, computer_provider = self._computer_goal_context(text, confirmed)
            if computer_context:
                deterministic_context = computer_context
                deterministic_verified = computer_verified
                needs_confirmation = computer_confirmation
                errors.extend(computer_errors)
                if computer_provider:
                    providers.append(computer_provider)
        if not deterministic_context and not needs_confirmation and not plan.parallel_tasks and plan.primary.profile is not RequestProfile.CODING:
            typed_context, typed_verified, typed_confirmation, typed_errors = self._execute_typed_plan(text, confirmed)
            if typed_context:
                deterministic_context, deterministic_verified, needs_confirmation = typed_context, typed_verified, typed_confirmation
            errors.extend(typed_errors)
        parallel_completed = 0
        if plan.primary.profile is RequestProfile.CODING and any(word in text.casefold() for word in ("implement", "fix", "modify", "code")):
            coding_context, coding_verified = self._coding_context(text, confirmed)
            deterministic_context = "\n\n".join(part for part in (deterministic_context, coding_context) if part)
            deterministic_verified = coding_verified
            if not confirmed:
                needs_confirmation = True
        if plan.parallel_tasks:
            specialist_results = self.router.complete_many(self._specialist_requests(plan, deterministic_context), max_parallel=self.max_parallel)
            parallel_completed = sum(1 for result in specialist_results if result.ok and result.text)
            for result in specialist_results:
                if result.target_name:
                    providers.append(result.target_name)
                if result.error:
                    errors.append(result.error)
            synthesis_prompt = self._synthesis_prompt(plan, specialist_results, deterministic_context)
        else:
            synthesis_prompt = self._synthesis_prompt(plan, (), deterministic_context)
        if deterministic_context and (deterministic_verified or needs_confirmation) and not plan.parallel_tasks:
            synthesis_text = deterministic_context
            provider = providers[-1] if providers else "deterministic"
        else:
            synthesis_text, provider = self.router.complete_profiled(self._messages(synthesis_prompt), plan.primary.profile)
        providers.append(provider)
        verified = bool(synthesis_text.strip()) and (deterministic_verified or not deterministic_context)
        if needs_confirmation:
            verified = False
        return OrchestrationResult(synthesis_text, plan.primary.profile.value, verified, needs_confirmation, parallel_completed, tuple(dict.fromkeys(providers)), int((time.monotonic() - started) * 1000), tuple(errors))

    def execute_stream(self, text: str, confirmed: bool = False, on_event: Callable[[OrchestrationEvent], None] | None = None) -> Iterator[OrchestrationEvent]:
        ack = OrchestrationEvent("ack", "Certainly. I'm working on that now.")
        if on_event:
            on_event(ack)
        yield ack
        plan = build_plan(text)
        progress = OrchestrationEvent("progress", f"Running {len(plan.parallel_tasks)} specialist checks in parallel." if plan.parallel_tasks else "Using the fastest suitable cloud model or guarded computer-use loop.")
        if on_event:
            on_event(progress)
        yield progress
        try:
            result = self.execute(text, confirmed=confirmed)
        except Exception as exc:
            event = OrchestrationEvent("result", "The request could not be completed safely.", {"error": str(exc)})
            if on_event:
                on_event(event)
            yield event
            return
        event = OrchestrationEvent("result", result.text, {"profile": result.profile, "verified": result.verified, "needs_confirmation": result.needs_confirmation, "parallel_tasks_completed": result.parallel_tasks_completed, "providers": result.providers, "latency_ms": result.latency_ms, "errors": result.errors})
        if on_event:
            on_event(event)
        yield event