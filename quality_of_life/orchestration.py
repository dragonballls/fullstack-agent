"""Deterministic request classification and low-latency orchestration planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RequestProfile(str, Enum):
    """Execution profile used to choose the smallest suitable AI workflow."""

    FAST = "fast"
    SMART = "smart"
    CODING = "coding"
    VISION = "vision"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class SpecialistTask:
    """One independent read-only analysis task that can run in parallel."""

    kind: str
    prompt: str
    profile: RequestProfile


@dataclass(frozen=True)
class PrimaryCall:
    """The primary synthesis call for an orchestration plan."""

    profile: RequestProfile
    prompt: str


@dataclass(frozen=True)
class OrchestrationPlan:
    """Immutable plan produced without contacting an AI provider."""

    primary: PrimaryCall
    parallel_tasks: tuple[SpecialistTask, ...] = ()


def classify_request(text: str) -> RequestProfile:
    """Classify a request conservatively without making a network/model call."""
    normalized = " ".join(text.lower().split())
    coding_markers = (
        "code", "coding", "pytest", "test", "bug", "debug", "repository", "repo",
        "commit", "pull request", "implement", "program", "function", "class",
    )
    maintenance_markers = (
        "my pc", "my computer", "windows", "diagnose", "repair", "fix my pc",
        "system health", "startup", "processes", "drivers", "disk space", "slow computer",
    )
    vision_markers = (
        "look at my screen", "look at the screen", "see my screen", "what is on my screen",
        "screenshot", "screen", "image", "visually", "vision",
    )
    smart_markers = (
        "research", "compare", "analyze", "architecture", "plan", "deep", "complex",
        "figure out", "investigate", "reason",
    )
    if any(marker in normalized for marker in maintenance_markers):
        return RequestProfile.MAINTENANCE
    if any(marker in normalized for marker in coding_markers):
        return RequestProfile.CODING
    if any(marker in normalized for marker in vision_markers):
        return RequestProfile.VISION
    if any(marker in normalized for marker in smart_markers):
        return RequestProfile.SMART
    return RequestProfile.FAST


def build_plan(text: str, profile: RequestProfile | None = None) -> OrchestrationPlan:
    """Build the minimum sufficient call graph for a request."""
    selected = profile or classify_request(text)
    primary = PrimaryCall(selected, text.strip())
    if selected is RequestProfile.MAINTENANCE:
        return OrchestrationPlan(
            primary=primary,
            parallel_tasks=(
                SpecialistTask(
                    "pc_diagnostics",
                    "Inspect the Windows PC maintenance request and identify likely diagnostic dimensions without making changes.",
                    RequestProfile.MAINTENANCE,
                ),
                SpecialistTask(
                    "process_snapshot",
                    "Analyze the request specifically for process/resource and background-app considerations; do not recommend unsafe termination.",
                    RequestProfile.MAINTENANCE,
                ),
            ),
        )
    if selected is RequestProfile.VISION:
        return OrchestrationPlan(
            primary=primary,
            parallel_tasks=(
                SpecialistTask(
                    "screen_context",
                    "Analyze the requested screen-understanding task and identify what visual context is required.",
                    RequestProfile.VISION,
                ),
                SpecialistTask(
                    "action_context",
                    "Analyze whether the visible UI likely requires a guarded computer action or can be answered read-only.",
                    RequestProfile.VISION,
                ),
            ),
        )
    if selected is RequestProfile.CODING:
        return OrchestrationPlan(
            primary=primary,
            parallel_tasks=(
                SpecialistTask(
                    "implementation_review",
                    "Analyze the coding task for implementation scope and likely regression risks.",
                    RequestProfile.CODING,
                ),
                SpecialistTask(
                    "test_review",
                    "Analyze the coding task for tests and verification needed to establish correctness.",
                    RequestProfile.CODING,
                ),
            ),
        )
    if selected is RequestProfile.SMART:
        return OrchestrationPlan(
            primary=primary,
            parallel_tasks=(
                SpecialistTask(
                    "independent_reasoning",
                    "Produce an independent analysis of the request and identify important constraints.",
                    RequestProfile.SMART,
                ),
                SpecialistTask(
                    "risk_review",
                    "Independently identify ambiguity, failure modes, and safer alternatives for the request.",
                    RequestProfile.SMART,
                ),
            ),
        )
    return OrchestrationPlan(primary=primary)
