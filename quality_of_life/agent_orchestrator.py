"""Low-latency multi-model orchestration above the guarded QOL runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator

from .orchestration import OrchestrationPlan, RequestProfile, build_plan
from .router import CloudModelRouter, ProviderResult


@dataclass(frozen=True)
class OrchestrationEvent:
    """One streaming-safe orchestration status event."""

    kind: str
    message: str
    data: dict[str, Any] | None = None


@dataclass(frozen=True)
class OrchestrationResult:
    """Verified output and execution metadata returned to the caller."""

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
    """Coordinate the minimum number of cloud-model calls without bypassing runtime policy."""

    def __init__(
        self,
        router: CloudModelRouter,
        runtime: Any,
        max_parallel: int | None = None,
    ) -> None:
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

    @staticmethod
    def _synthesis_prompt(plan: OrchestrationPlan, results: Iterable[ProviderResult]) -> str:
        findings: list[str] = []
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
        """Execute one request using a fast path or bounded parallel specialist path."""
        started = __import__("time").monotonic()
        plan = build_plan(text)
        errors: list[str] = []
        providers: list[str] = []
        parallel_completed = 0

        if plan.parallel_tasks:
            specialist_results = self.router.complete_many(
                self._specialist_requests(plan),
                max_parallel=self.max_parallel,
            )
            parallel_completed = sum(1 for result in specialist_results if result.ok and result.text)
            for result in specialist_results:
                if result.target_name:
                    providers.append(result.target_name)
                if result.error:
                    errors.append(result.error)
            synthesis_text, provider = self.router.complete_profiled(
                self._messages(self._synthesis_prompt(plan, specialist_results)),
                plan.primary.profile,
            )
            providers.append(provider)
        else:
            synthesis_text, provider = self.router.complete_profiled(
                self._messages(plan.primary.prompt),
                plan.primary.profile,
            )
            providers.append(provider)

        needs_confirmation = self._needs_confirmation(text) and not confirmed
        verified = bool(synthesis_text.strip()) and not any(error.startswith("verification:") for error in errors)
        return OrchestrationResult(
            text=synthesis_text,
            profile=plan.primary.profile.value,
            verified=verified,
            needs_confirmation=needs_confirmation,
            parallel_tasks_completed=parallel_completed,
            providers=tuple(dict.fromkeys(providers)),
            latency_ms=int((__import__("time").monotonic() - started) * 1000),
            errors=tuple(errors),
        )

    def execute_stream(
        self,
        text: str,
        confirmed: bool = False,
        on_event: Callable[[OrchestrationEvent], None] | None = None,
    ) -> Iterator[OrchestrationEvent]:
        """Yield immediate acknowledgement, progress, and final verified result."""
        ack = OrchestrationEvent("ack", "Certainly. I'm working on that now.")
        if on_event:
            on_event(ack)
        yield ack

        plan = build_plan(text)
        if plan.parallel_tasks:
            progress = OrchestrationEvent("progress", f"Running {len(plan.parallel_tasks)} specialist checks in parallel.")
        else:
            progress = OrchestrationEvent("progress", "Using the fastest suitable cloud model.")
        if on_event:
            on_event(progress)
        yield progress

        try:
            result = self.execute(text, confirmed=confirmed)
        except Exception as exc:
            failure = OrchestrationEvent("result", "The request could not be completed safely.", {"error": str(exc)})
            if on_event:
                on_event(failure)
            yield failure
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
