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


ConfirmationHook = Callable[[Capability, str], bool]


class QoLOrchestrator:
    """Dispatch registered actions only after capability and confirmation checks."""

    def __init__(self, policy: CapabilityPolicy) -> None:
        self.policy = policy
        self._actions: dict[tuple[Capability, str], Action] = {}

    def register(self, action: Action) -> None:
        key = (action.capability, action.operation)
        if key in self._actions:
            raise ValueError(f"action already registered: {action.capability.value}/{action.operation}")
        self._actions[key] = action

    def run(
        self,
        capability: Capability,
        operation: str,
        *args: Any,
        confirmation: ConfirmationHook | None = None,
        **kwargs: Any,
    ) -> Any:
        self.policy.check(capability)
        if self.policy.needs_confirmation(capability):
            if confirmation is None:
                raise PermissionError(f"Confirmation is required: {capability.value}/{operation}")
            if not confirmation(capability, operation):
                raise PermissionError(f"Confirmation was denied: {capability.value}/{operation}")
        try:
            action = self._actions[(capability, operation)]
        except KeyError as exc:
            raise KeyError(f"action not registered: {capability.value}/{operation}") from exc
        return action.execute(*args, **kwargs)
