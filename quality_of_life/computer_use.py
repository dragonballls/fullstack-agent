"""Bounded goal-based computer-use coordination over existing guarded adapters."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Iterable


_ALLOWED_ACTIONS = {"move", "click", "scroll", "type_text", "hotkey", "wait", "open_app"}


@dataclass(frozen=True)
class ComputerUseAction:
    kind: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ComputerUseResult:
    completed: bool
    steps_executed: int
    observations: int
    last_observation: Any
    errors: tuple[str, ...] = ()


class ComputerUseAgent:
    """Translate a high-level goal into a bounded observe/act/verify loop.

    Planning is deliberately injected so a caller can use a cloud text or vision
    model without granting that model direct execution authority.
    """

    def __init__(
        self,
        planner: Callable[[str, Any], Iterable[ComputerUseAction]],
        computer: Any,
        observer: Any,
        max_steps: int = 10,
        max_wait_seconds: float = 5.0,
    ) -> None:
        if max_steps < 1 or max_steps > 20:
            raise ValueError("max_steps must be between 1 and 20")
        if max_wait_seconds <= 0 or max_wait_seconds > 5:
            raise ValueError("max_wait_seconds must be between 0 and 5 seconds")
        self.planner = planner
        self.computer = computer
        self.observer = observer
        self.max_steps = max_steps
        self.max_wait_seconds = max_wait_seconds

    @staticmethod
    def _validate(action: ComputerUseAction) -> ComputerUseAction:
        if action.kind not in _ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported computer-use action: {action.kind}")
        args = dict(action.arguments)
        if action.kind in {"move", "click"}:
            if action.kind == "move":
                if not all(isinstance(args.get(key), int) for key in ("x", "y")):
                    raise ValueError("move requires integer x and y")
                if not 0 <= args["x"] <= 10000 or not 0 <= args["y"] <= 10000:
                    raise ValueError("move coordinates are out of bounds")
            else:
                if not isinstance(args.get("button", "left"), str):
                    raise ValueError("click button must be text")
                clicks = args.get("clicks", 1)
                if not isinstance(clicks, int) or not 1 <= clicks <= 3:
                    raise ValueError("clicks must be between 1 and 3")
        elif action.kind == "scroll":
            amount = args.get("amount")
            if not isinstance(amount, int) or not -20 <= amount <= 20:
                raise ValueError("scroll amount must be between -20 and 20")
        elif action.kind == "type_text":
            text = args.get("text")
            if not isinstance(text, str) or len(text) > 4000:
                raise ValueError("type_text requires up to 4000 characters")
        elif action.kind == "hotkey":
            keys = args.get("keys")
            if not isinstance(keys, (list, tuple)) or not 1 <= len(keys) <= 5 or not all(isinstance(key, str) for key in keys):
                raise ValueError("hotkey requires 1-5 text keys")
        elif action.kind == "wait":
            seconds = args.get("seconds", 0.25)
            if not isinstance(seconds, (int, float)) or not 0 <= seconds <= 5:
                raise ValueError("wait must be between 0 and 5 seconds")
        elif action.kind == "open_app":
            name = args.get("name")
            if not isinstance(name, str) or not name.strip() or len(name) > 200:
                raise ValueError("open_app requires a known application name")
        return ComputerUseAction(action.kind, args)

    def _execute(self, action: ComputerUseAction) -> Any:
        args = action.arguments
        if action.kind == "move":
            return self.computer.move(args["x"], args["y"])
        if action.kind == "click":
            return self.computer.click(args.get("button", "left"), args.get("clicks", 1))
        if action.kind == "scroll":
            return self.computer.scroll(args["amount"])
        if action.kind == "type_text":
            return self.computer.type_text(args["text"])
        if action.kind == "hotkey":
            return self.computer.hotkey(*args["keys"])
        if action.kind == "wait":
            time.sleep(min(float(args.get("seconds", 0.25)), self.max_wait_seconds))
            return None
        if action.kind == "open_app":
            opener = getattr(self.computer, "open_known_app", None)
            if opener is None:
                raise ValueError("computer adapter does not support known-application launch")
            return opener(args["name"])
        raise ValueError(f"Unsupported computer-use action: {action.kind}")

    def run(self, goal: str) -> ComputerUseResult:
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("goal cannot be empty")
        observation = self.observer.observe()
        observation_count = 1
        raw_plan = list(self.planner(normalized_goal, observation))
        if not raw_plan:
            raise ValueError("planner returned no actions")
        if len(raw_plan) > self.max_steps:
            raise ValueError("planner returned more actions than the configured step limit")
        errors: list[str] = []
        executed = 0
        for raw_action in raw_plan:
            action = self._validate(raw_action)
            try:
                self._execute(action)
                executed += 1
                observation = self.observer.observe()
                observation_count += 1
            except Exception as exc:
                errors.append(f"{action.kind}: {exc}")
                return ComputerUseResult(False, executed, observation_count, observation, tuple(errors))
        return ComputerUseResult(True, executed, observation_count, observation, tuple(errors))
