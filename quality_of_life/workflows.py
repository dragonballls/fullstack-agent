"""Persistent named workflows for deterministic, capability-gated Jarvis routines."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from .capabilities import operation


_MAX_WORKFLOWS = 256
_MAX_STEPS = 32
_MAX_NAME = 120
_MAX_ALIAS = 120


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: str) -> str:
    normalized = " ".join(str(value).casefold().split())
    if not normalized:
        raise ValueError("workflow name cannot be empty")
    return normalized


def _json_safe(value: Any) -> None:
    try:
        json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("workflow arguments must be JSON-compatible") from exc


def _safe_error(exc: Exception) -> str:
    message = str(exc).replace("OPENAI_API_KEY", "[secret]")
    return message[:500]


@dataclass(frozen=True)
class WorkflowStep:
    operation: str
    arguments: dict[str, Any]
    continue_on_error: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("workflow step operation is required")
        if not isinstance(self.arguments, dict):
            raise ValueError("workflow step arguments must be an object")
        try:
            operation(self.operation.strip())
        except KeyError as exc:
            raise ValueError(f"unknown workflow operation: {self.operation.strip()}") from exc
        _json_safe(self.arguments)
        object.__setattr__(self, "operation", self.operation.strip())
        object.__setattr__(self, "arguments", dict(self.arguments))
        object.__setattr__(self, "continue_on_error", bool(self.continue_on_error))

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "arguments": self.arguments,
            "continue_on_error": self.continue_on_error,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkflowStep":
        if not isinstance(value, dict):
            raise ValueError("workflow step must be an object")
        return cls(
            operation=value.get("operation", ""),
            arguments=value.get("arguments", {}),
            continue_on_error=value.get("continue_on_error", False),
        )


@dataclass(frozen=True)
class WorkflowRunSummary:
    run_id: str
    started_at: str
    ended_at: str
    success: bool
    completed_steps: int
    errors: tuple[str, ...] = ()
    needs_confirmation: bool = False

    @classmethod
    def completed(cls, *, run_id: str, completed_steps: int) -> "WorkflowRunSummary":
        now = _now()
        return cls(run_id, now, now, True, int(completed_steps))

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "success": self.success,
            "completed_steps": self.completed_steps,
            "errors": list(self.errors),
            "needs_confirmation": self.needs_confirmation,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkflowRunSummary":
        return cls(
            run_id=str(value.get("run_id", "")),
            started_at=str(value.get("started_at", "")),
            ended_at=str(value.get("ended_at", "")),
            success=bool(value.get("success", False)),
            completed_steps=max(0, int(value.get("completed_steps", 0))),
            errors=tuple(str(item)[:500] for item in value.get("errors", ()) if isinstance(item, str))[:8],
            needs_confirmation=bool(value.get("needs_confirmation", False)),
        )


@dataclass(frozen=True)
class Workflow:
    id: str
    name: str
    aliases: tuple[str, ...]
    steps: tuple[WorkflowStep, ...]
    enabled: bool
    created_at: str
    updated_at: str
    last_run: WorkflowRunSummary | None = None

    @classmethod
    def new(
        cls,
        name: str,
        *,
        aliases: tuple[str, ...] = (),
        steps: tuple[WorkflowStep, ...],
        enabled: bool = True,
    ) -> "Workflow":
        display_name = " ".join(str(name).split())
        created = _now()
        return cls(str(uuid4()), display_name, tuple(aliases), tuple(steps), bool(enabled), created, created, None)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("workflow name cannot be empty")
        if len(self.name) > _MAX_NAME:
            raise ValueError("workflow name is too long")
        if not self.steps:
            raise ValueError("workflow must contain at least one step")
        if len(self.steps) > _MAX_STEPS:
            raise ValueError("workflow contains too many steps")
        if not self.id.strip():
            raise ValueError("workflow id cannot be empty")
        names = {_normalize(self.name)}
        normalized_aliases: list[str] = []
        for alias in self.aliases:
            normalized = " ".join(str(alias).split())
            if not normalized or len(normalized) > _MAX_ALIAS:
                raise ValueError("workflow alias is empty or too long")
            key = _normalize(normalized)
            if key not in names:
                normalized_aliases.append(normalized)
                names.add(key)
        object.__setattr__(self, "aliases", tuple(normalized_aliases))
        for step in self.steps:
            if not isinstance(step, WorkflowStep):
                raise ValueError("workflow steps must be WorkflowStep values")
        if not isinstance(self.enabled, bool):
            raise ValueError("workflow enabled flag must be boolean")
        _json_safe(self.as_definition_dict())

    def matches(self, phrase: str) -> bool:
        candidate = _normalize(phrase)
        return candidate in {_normalize(self.name), *(_normalize(alias) for alias in self.aliases)}

    def as_definition_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": list(self.aliases),
            "steps": [step.as_dict() for step in self.steps],
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run": self.last_run.as_dict() if self.last_run else None,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Workflow":
        if not isinstance(value, dict):
            raise ValueError("workflow must be an object")
        raw_steps = value.get("steps", [])
        if not isinstance(raw_steps, list):
            raise ValueError("workflow steps must be an array")
        raw_aliases = value.get("aliases", ())
        if not isinstance(raw_aliases, (list, tuple)):
            raise ValueError("workflow aliases must be an array")
        last_run = value.get("last_run")
        return cls(
            id=str(value.get("id", "")),
            name=str(value.get("name", "")),
            aliases=tuple(str(item) for item in raw_aliases if isinstance(item, str)),
            steps=tuple(WorkflowStep.from_dict(item) for item in raw_steps),
            enabled=bool(value.get("enabled", True)),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
            last_run=WorkflowRunSummary.from_dict(last_run) if isinstance(last_run, dict) else None,
        )


class WorkflowStore:
    """Atomic local JSON persistence for user-defined workflows."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or __import__("os").environ.get("JARVIS_WORKFLOW_STORE")
        self.path = Path(configured) if configured else Path.home() / ".jarvis" / "workflows.json"

    def _read(self) -> dict[str, Workflow]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("workflow store could not be read") from exc
        if not isinstance(payload, dict):
            raise ValueError("workflow store must contain an object")
        result: dict[str, Workflow] = {}
        for key, value in payload.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError("workflow store contains invalid entries")
            workflow = Workflow.from_dict(value)
            if workflow.id != key:
                raise ValueError("workflow store id/key mismatch")
            result[key] = workflow
        return result

    def _write(self, workflows: dict[str, Workflow]) -> None:
        if len(workflows) > _MAX_WORKFLOWS:
            raise ValueError("workflow store contains too many workflows")
        payload = {key: value.as_definition_dict() for key, value in sorted(workflows.items())}
        encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        try:
            temporary.replace(self.path)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def create(self, workflow: Workflow) -> Workflow:
        workflow.validate()
        workflows = self._read()
        if workflow.id in workflows:
            raise ValueError(f"workflow already exists: {workflow.id}")
        if any(_normalize(existing.name) == _normalize(workflow.name) for existing in workflows.values()):
            raise ValueError(f"workflow name already exists: {workflow.name}")
        workflows[workflow.id] = workflow
        self._write(workflows)
        return workflow

    def replace(self, workflow: Workflow) -> Workflow:
        workflow.validate()
        workflows = self._read()
        if workflow.id not in workflows:
            raise KeyError(f"workflow not found: {workflow.id}")
        workflows[workflow.id] = workflow
        self._write(workflows)
        return workflow

    def delete(self, workflow_id: str) -> bool:
        workflows = self._read()
        if workflow_id not in workflows:
            return False
        del workflows[workflow_id]
        self._write(workflows)
        return True

    def get(self, workflow_id: str) -> Workflow | None:
        return self._read().get(workflow_id)

    def list(self) -> tuple[Workflow, ...]:
        return tuple(self._read().values())

    @staticmethod
    def _command_phrase(text: str) -> str | None:
        normalized = " ".join(text.casefold().split())
        match = re.match(r"^(?:run|do|start)(?:\s+my)?\s+(.+)$", normalized)
        return match.group(1).strip() if match else None

    def resolve(self, text: str) -> Workflow | None:
        phrase = self._command_phrase(text)
        if phrase is None:
            return None
        matches = [workflow for workflow in self._read().values() if workflow.enabled and workflow.matches(phrase)]
        return matches[0] if len(matches) == 1 else None

    def record_run(self, workflow_id: str, summary: WorkflowRunSummary) -> Workflow:
        workflows = self._read()
        try:
            workflow = workflows[workflow_id]
        except KeyError as exc:
            raise KeyError(f"workflow not found: {workflow_id}") from exc
        updated = replace(workflow, updated_at=_now(), last_run=summary)
        workflows[workflow_id] = updated
        self._write(workflows)
        return updated


@dataclass(frozen=True)
class WorkflowExecutionResult:
    run_id: str
    verified: bool
    needs_confirmation: bool
    completed_steps: int
    outputs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class WorkflowService:
    """Execute stored workflow steps exclusively through the runtime dispatcher."""

    @staticmethod
    def execute(runtime: Any, workflow: Workflow, *, confirmed: bool = False, store: WorkflowStore | None = None) -> WorkflowExecutionResult:
        run_id = str(uuid4())
        started = _now()
        errors: list[str] = []
        outputs: list[str] = []
        completed = 0
        needs_confirmation = False
        verified = True

        for step in workflow.steps:
            spec = operation(step.operation)
            protected = runtime.policy.needs_confirmation(spec.capability)
            if protected and not confirmed:
                needs_confirmation = True
                verified = False
                errors.append(f"confirmation required: {step.operation}")
                break
            try:
                if protected and confirmed:
                    result = runtime.orchestrator.run(
                        spec.capability,
                        step.operation,
                        confirmation=lambda _capability, _operation: True,
                        **dict(step.arguments),
                    )
                else:
                    result = runtime.dispatch(spec.capability, step.operation, **dict(step.arguments))
                outputs.append(f"{step.operation}: {result}")
                completed += 1
            except PermissionError as exc:
                verified = False
                errors.append(f"{step.operation}: {_safe_error(exc)}")
                if "confirmation" in str(exc).casefold() and not confirmed:
                    needs_confirmation = True
                if not step.continue_on_error:
                    break
            except Exception as exc:
                verified = False
                errors.append(f"{step.operation}: {_safe_error(exc)}")
                if not step.continue_on_error:
                    break

        summary = WorkflowRunSummary(
            run_id=run_id,
            started_at=started,
            ended_at=_now(),
            success=bool(verified and completed == len(workflow.steps)),
            completed_steps=completed,
            errors=tuple(errors[:8]),
            needs_confirmation=needs_confirmation,
        )
        if store is not None:
            store.record_run(workflow.id, summary)
        return WorkflowExecutionResult(run_id, summary.success, needs_confirmation, completed, tuple(outputs[:32]), summary.errors)
