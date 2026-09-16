"""Optional desktop features for persistent workflows and authorized family God’s Eye."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from quality_of_life.family_locations import FamilyLocationService, configured_life360_provider
from quality_of_life.permissions import Capability
from quality_of_life.planner import PlanError, plan_request
from quality_of_life.workflows import Workflow, WorkflowService, WorkflowStep, WorkflowStore
from scripts.jarvis_desktop import JarvisDesktopController


@dataclass(frozen=True)
class DesktopFeatureResult:
    text: str
    verified: bool
    needs_confirmation: bool = False
    errors: tuple[str, ...] = ()
    completed_steps: int = 0
    map_state: dict[str, object] | None = None


def _family_command(text: str) -> tuple[str, str | None] | None:
    value = " ".join(text.strip().split())
    match = re.match(r"^where is (.+)$", value, re.IGNORECASE)
    if match:
        return "where", match.group(1).strip()
    match = re.match(r"^show (.+) on God[’']?s Eye$", value, re.IGNORECASE)
    if match:
        return "show", match.group(1).strip()
    if re.match(r"^show my family$", value, re.IGNORECASE):
        return "show_all", None
    match = re.match(r"^follow (.+)$", value, re.IGNORECASE)
    if match:
        return "follow", match.group(1).strip()
    if re.match(r"^(?:stop following|stop following my family)$", value, re.IGNORECASE):
        return "stop", None
    return None


class JarvisExtendedController(JarvisDesktopController):
    """User-facing controller that adds the two approved persistent features."""

    def __init__(self, runtime: Any | None = None, workflow_store: WorkflowStore | None = None, family_service: FamilyLocationService | None = None) -> None:
        super().__init__(runtime=runtime)
        self.workflow_store = workflow_store or WorkflowStore()
        self.family_service = family_service or FamilyLocationService(configured_life360_provider())
        self._last_request: str | None = None

    @staticmethod
    def run_workflow_request(runtime: Any, store: WorkflowStore, text: str, *, confirmed: bool = False) -> DesktopFeatureResult | None:
        workflow = store.resolve(text)
        if workflow is None:
            return None
        result = WorkflowService.execute(runtime, workflow, confirmed=confirmed, store=store)
        if result.needs_confirmation:
            message = f"Workflow '{workflow.name}' requires confirmation before its protected actions can run."
        elif result.verified:
            message = f"Workflow '{workflow.name}' completed successfully ({result.completed_steps} step(s))."
        else:
            message = f"Workflow '{workflow.name}' stopped after {result.completed_steps} completed step(s)."
        return DesktopFeatureResult(message, result.verified, result.needs_confirmation, result.errors, result.completed_steps)

    def _remember_previous(self, name: str) -> DesktopFeatureResult:
        if not self._last_request:
            return DesktopFeatureResult("There is no previous task to remember yet.", False)
        try:
            plan = plan_request(self.runtime._tool("cloud_router"), self._last_request)
        except (PlanError, RuntimeError, AttributeError) as exc:
            return DesktopFeatureResult(f"I couldn't turn the previous task into a safe workflow: {type(exc).__name__}.", False, errors=(str(exc)[:500],))
        if not plan.steps:
            return DesktopFeatureResult("The previous task could not be represented by Jarvis's approved operations, so I did not save it.", False)
        try:
            steps = tuple(WorkflowStep(step.operation, step.arguments) for step in plan.steps)
            workflow = Workflow.new(name, steps=steps)
            self.workflow_store.create(workflow)
        except (ValueError, KeyError) as exc:
            return DesktopFeatureResult(f"I couldn't save that workflow: {exc}", False, errors=(str(exc)[:500],))
        return DesktopFeatureResult(f"Saved '{workflow.name}'. You can run it later by saying 'do my {workflow.name}'.", True)

    def _launch_family_window(self, member_id: str | None = None) -> None:
        env = os.environ.copy()
        env["JARVIS_FAMILY_WINDOW"] = "1"
        env["JARVIS_FAMILY_FOCUS"] = member_id or ""
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if getattr(sys, "frozen", False):
            argv = [sys.executable]
        else:
            argv = [sys.executable, str(Path(__file__).with_name("jarvis_desktop.pyw"))]
        subprocess.Popen(argv, env=env, creationflags=creationflags, close_fds=True)

    def _family_request(self, text: str) -> DesktopFeatureResult | None:
        command = _family_command(text)
        if command is None:
            return None
        kind, reference = command
        if self.family_service.provider is None:
            return DesktopFeatureResult("Family location sharing is not configured. Configure an authorized Life360 bridge before requesting family locations.", False) if kind == "show_all" else None
        self.runtime.policy.check(Capability.FAMILY_LOCATION_READ)
        if kind == "stop":
            self.family_service.stop_follow()
            return DesktopFeatureResult("Family follow mode stopped.", True, map_state=self.family_service.map_state())
        try:
            self.family_service.refresh()
            if kind == "show_all":
                self._launch_family_window()
                return DesktopFeatureResult("Showing the authorized family members in God’s Eye.", True, map_state=self.family_service.map_state())
            member = self.family_service.get(reference or "")
            if kind == "follow":
                member = self.family_service.follow(member.member_id)
                self._launch_family_window(member.member_id)
                return DesktopFeatureResult(f"Following {member.name} in God’s Eye. Last update: {member.observed_at.isoformat()}.", True, map_state=self.family_service.map_state())
            self._launch_family_window(member.member_id)
            state = "sharing paused" if not member.available else ("stale" if member.stale else "current")
            return DesktopFeatureResult(f"{member.name} is {state}. Last authorized update: {member.observed_at.isoformat()}.", True, map_state=self.family_service.map_state())
        except (RuntimeError, LookupError, ValueError) as exc:
            return DesktopFeatureResult(f"Family location data is unavailable: {type(exc).__name__}.", False, errors=(str(exc)[:500],))

    def execute_request(self, text: str, confirmed: bool = False) -> Any:
        value = text.strip()
        if not value:
            return super().execute_request(value, confirmed=confirmed)
        remember = re.match(r"^(?:remember|save) (?:that|this) as (.+)$", value, re.IGNORECASE)
        if remember:
            return self._remember_previous(remember.group(1).strip())
        workflow_result = self.run_workflow_request(self.runtime, self.workflow_store, value, confirmed=confirmed)
        if workflow_result is not None:
            return workflow_result
        family_result = self._family_request(value)
        if family_result is not None:
            return family_result
        result = super().execute_request(value, confirmed=confirmed)
        if not bool(getattr(result, "needs_confirmation", False)) and bool(getattr(result, "text", "")):
            self._last_request = value
        return result


def run_family_window() -> int:
    from quality_of_life.family_gods_eye import FamilyGodsEyeSurface

    service = FamilyLocationService(configured_life360_provider())
    focus = os.environ.get("JARVIS_FAMILY_FOCUS", "").strip() or None
    return FamilyGodsEyeSurface(service).show(focus)


def is_family_window_request() -> bool:
    return os.environ.get("JARVIS_FAMILY_WINDOW", "0").strip().lower() in {"1", "true", "yes", "on"}
