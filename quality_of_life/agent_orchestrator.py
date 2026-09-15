"""Low-latency multi-model orchestration above the guarded QOL runtime."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Iterable, Iterator

from .intents import parse_intent
from .orchestration import OrchestrationPlan, RequestProfile, build_plan
from .permissions import Capability
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

    @staticmethod
    def _messages(prompt: str) -> list[dict[str, str]]:
        return [{"role": "user", "content": prompt}]

    def _specialist_requests(self, plan: OrchestrationPlan) -> list[tuple[list[dict[str, str]], RequestProfile]]:
        return [
            (
                self._messages(
                    f"{task.prompt}\n\nUser request:\n{plan.primary.prompt}\n\nReturn concise findings only; do not execute anything."
                ),
                task.profile,
            )
            for task in plan.parallel_tasks
        ]

    def _deterministic_context(self, text: str, confirmed: bool) -> tuple[str, bool, list[str]]:
        """Execute only supported intents through the existing policy-gated runtime."""
        intent = parse_intent(text)
        needs_confirmation = self._needs_confirmation(text) and not confirmed
        if intent.kind == "windows_maintenance":
            request = str(intent.arguments["request"])
            lowered = request.casefold()
            if "diagnos" in lowered and not any(word in lowered for word in ("fix", "repair", "clean")):
                result = self.runtime.dispatch(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.diagnose")
                return str(getattr(result, "message", result)), True, []
            if confirmed:
                result = self.runtime.dispatch(
                    Capability.SYSTEM_MAINTENANCE,
                    "windows_maintenance.handle",
                    request=request,
                    confirmed=True,
                )
                operation_results = getattr(result, "results", ())
                verified = bool(operation_results) and all(
                    getattr(item, "success", False) and getattr(item, "verified", False)
                    for item in operation_results
                )
                return str(getattr(result, "message", result)), verified, []
            return "A maintenance change was requested, but confirmation is required before anything is modified.", False, []
        if intent.kind == "locate_me":
            result = self.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.locate_me")
            return str(result), True, []
        if intent.kind == "screen_read":
            result = self.runtime.dispatch(Capability.SCREEN_READ, "screen.capture")
            return str(result), True, []
        if intent.kind == "place_search":
            query = str(intent.arguments["query"])
            result = self.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.open_place", query=query)
            return str(result), True, []
        if intent.kind == "route":
            query = str(intent.arguments["query"])
            result = self.runtime.dispatch(Capability.LOCATION_READ, "gods_eye.route_to", query=query)
            return str(result), True, []
        if intent.kind == "computer_action":
            if not confirmed:
                return "A computer-control action was requested, but confirmation is required before moving the mouse.", False, []
            result = self.runtime.dispatch(
                Capability.MOUSE_CONTROL,
                "computer.move",
                x=intent.arguments["x"],
                y=intent.arguments["y"],
            )
            return str(result), True, []
        return "", False, []

    @staticmethod
    def _synthesis_prompt(plan: OrchestrationPlan, results: Iterable[ProviderResult], deterministic_context: str = "") -> str:
        findings: list[str] = []
        if deterministic_context:
            findings.append(
                "Deterministic tool result (authoritative; report this faithfully): "
                + deterministic_context
            )
        for index, result in enumerate(results, start=1):
            if result.ok and result.text:
                findings.append(f"Specialist {index}: {result.text}")
            elif result.error:
                findings.append(f"Specialist {index}: unavailable ({result.error})")
        context = "\n\n".join(findings) or "No specialist findings were available."
        return (
            "Act as the primary Jarvis response model. Synthesize the specialist findings below "
            "into one accurate, concise response to the user. Do not claim an action was performed "
            "unless a deterministic tool result is supplied. Preserve safety boundaries and state "
            "when confirmation is required.\n\n"
            f"User request:\n{plan.primary.prompt}\n\n"
            f"Specialist findings:\n{context}"
        )

    def execute(self, text: str, confirmed: bool = False) -> OrchestrationResult:
        started = time.monotonic()
        plan = build_plan(text)
        errors: list[str] = []
        providers: list[str] = []
        deterministic_context, deterministic_verified, deterministic_errors = self._deterministic_context(text, confirmed)
        errors.extend(deterministic_errors)
        parallel_completed = 0
        if plan.parallel_tasks:
            specialist_results = self.router.complete_many(self._specialist_requests(plan), max_parallel=self.max_parallel)
            parallel_completed = sum(1 for result in specialist_results if result.ok and result.text)
            for result in specialist_results:
                if result.target_name:
                    providers.append(result.target_name)
                if result.error:
                    errors.append(result.error)
            synthesis_prompt = self._synthesis_prompt(plan, specialist_results, deterministic_context)
        else:
            synthesis_prompt = self._synthesis_prompt(plan, (), deterministic_context)
        synthesis_text, provider = self.router.complete_profiled(self._messages(synthesis_prompt), plan.primary.profile)
        providers.append(provider)
        needs_confirmation = self._needs_confirmation(text) and not confirmed
        verified = bool(synthesis_text.strip()) and (deterministic_verified or not deterministic_context)
        if needs_confirmation:
            verified = False
        return OrchestrationResult(
            synthesis_text,
            plan.primary.profile.value,
            verified,
            needs_confirmation,
            parallel_completed,
            tuple(dict.fromkeys(providers)),
            int((time.monotonic() - started) * 1000),
            tuple(errors),
        )

    def execute_stream(
        self,
        text: str,
        confirmed: bool = False,
        on_event: Callable[[OrchestrationEvent], None] | None = None,
    ) -> Iterator[OrchestrationEvent]:
        ack = OrchestrationEvent("ack", "Certainly. I'm working on that now.")
        if on_event:
            on_event(ack)
        yield ack
        plan = build_plan(text)
        progress = OrchestrationEvent(
            "progress",
            f"Running {len(plan.parallel_tasks)} specialist checks in parallel." if plan.parallel_tasks else "Using the fastest suitable cloud model.",
        )
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
        event = OrchestrationEvent(
            "result",
            result.text,
            {
                "profile": result.profile,
                "verified": result.verified,
                "needs_confirmation": result.needs_confirmation,
                "parallel_tasks_completed": result.parallel_tasks_completed,
                "providers": result.providers,
                "latency_ms": result.latency_ms,
                "errors": result.errors,
            },
        )
        if on_event:
            on_event(event)
        yield event
