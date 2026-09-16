"""Structured natural-language planning without granting models arbitrary execution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .capabilities import OPERATION_CATALOG, operation


class PlanError(RuntimeError):
    """Raised when a model plan is missing, malformed, or unsupported."""


@dataclass(frozen=True)
class PlanStep:
    operation: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ExecutionPlan:
    steps: tuple[PlanStep, ...]


_SAFE_MODEL_OPERATIONS = tuple(
    spec.name for spec in OPERATION_CATALOG
    if spec.name not in {"background.start", "scheduler.schedule_once", "self_coding.run"}
)

_ACCOUNT_OPERATION_PROVIDER = {
    "google.gmail.send": "google",
    "microsoft.mail.send": "microsoft",
    "youtube.video.upload": "youtube",
    "youtube.video.update": "youtube",
}


def _extract_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise PlanError("Planner returned no JSON object")
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as exc:
            raise PlanError("Planner returned malformed JSON") from exc


def _normalize_account_step(name: str, args: dict[str, Any]) -> PlanStep:
    provider = _ACCOUNT_OPERATION_PROVIDER[name]
    account_id = args.pop("account_id", None)
    label = args.pop("label", None)
    requested_provider = args.pop("provider", provider)
    if str(requested_provider).strip().lower() != provider:
        raise PlanError(f"{name} requires provider={provider}")
    normalized: dict[str, Any] = {"operation": name, "provider": provider, "payload": args}
    if account_id is not None:
        normalized["account_id"] = account_id
    if label is not None:
        normalized["label"] = label
    return PlanStep("accounts.service_action", normalized)


def parse_plan(text: str) -> ExecutionPlan:
    data = _extract_json(text)
    raw_steps = data.get("steps") if isinstance(data, dict) else None
    if not isinstance(raw_steps, list) or not raw_steps or len(raw_steps) > 8:
        raise PlanError("Plan must contain between 1 and 8 steps")
    steps: list[PlanStep] = []
    for raw in raw_steps:
        if not isinstance(raw, dict) or not isinstance(raw.get("operation"), str) or not isinstance(raw.get("arguments", {}), dict):
            raise PlanError("Each plan step must contain an operation and object arguments")
        name = raw["operation"]
        if name not in _SAFE_MODEL_OPERATIONS:
            raise PlanError(f"Unsupported operation: {name}")
        spec = operation(name)
        args = dict(raw.get("arguments", {}))
        if spec.name.endswith(".open_url") and "url" not in args:
            raise PlanError("browser.open_url requires a URL")
        if name in _ACCOUNT_OPERATION_PROVIDER:
            steps.append(_normalize_account_step(name, args))
        else:
            steps.append(PlanStep(name, args))
    return ExecutionPlan(tuple(steps))


def planning_prompt(user_text: str) -> str:
    operations = "\n".join(f"- {spec.name}: {spec.description}" for spec in OPERATION_CATALOG if spec.name in _SAFE_MODEL_OPERATIONS)
    return (
        "Return ONLY a JSON object with a 'steps' array. Each step must contain an operation from the allowlist "
        "and an 'arguments' object. Never output shell commands, PowerShell, Python, JavaScript, registry scripts, "
        "or arbitrary executable paths. Use the minimum number of steps. If the request cannot be expressed by "
        "the allowlist, return {\"steps\": []}. For account write operations, include account_id or label when "
        "multiple accounts may exist; never invent an account identity.\n\n"
        f"Allowed operations:\n{operations}\n\nUser request:\n{user_text}"
    )


def plan_request(router: Any, user_text: str) -> ExecutionPlan:
    response, _provider = router.complete([{"role": "user", "content": planning_prompt(user_text)}])
    return parse_plan(response)
