"""Capability-aware dispatcher joining the quality-of-life tools together."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .permissions import Capability, CapabilityPolicy


@dataclass(frozen=True)
class Action:
    capability: Capability
    operation: str
    execute: Callable[..., Any]


class QoLOrchestrator:
    """Dispatch explicitly registered actions after capability checks."""

    def __init__(self, policy: CapabilityPolicy) -> None:
        self.policy = policy
        self._actions: dict[tuple[Capability, str], Action] = {}

    def register(self, action: Action) -> None:
        key = (action.capability, action.operation)
        if key in self._actions:
            raise ValueError(f"action already registered: {action.capability.value}/{action.operation}")
        self._actions[key] = action

    def run(self, capability: Capability, operation: str, *args: Any, **kwargs: Any) -> Any:
        self.policy.check(capability)
        try:
            action = self._actions[(capability, operation)]
        except KeyError as exc:
            raise KeyError(f"action not registered: {capability.value}/{operation}") from exc
        return action.execute(*args, **kwargs)
