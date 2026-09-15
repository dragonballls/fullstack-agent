"""Bounded goal-based computer-use coordination over existing guarded adapters."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import time
from typing import Any, Callable, Iterable

from .orchestration import RequestProfile

_ALLOWED_ACTIONS = {"move", "click", "scroll", "type_text", "hotkey", "wait", "open_app", "done"}


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


class ScreenObserver:
    """Capture bounded visual context for a vision-capable planner."""

    def __init__(self, screen: Any) -> None:
        self.screen = screen

    def observe(self) -> dict[str, Any]:
        try:
            raw = self.screen.capture_png()
            return {"screen_available": True, "image_data_url": "data:image/png;base64," + base64.b64encode(raw).decode("ascii")}
        except Exception as exc:
            return {"screen_available": False, "error": str(exc)}


class RouterComputerUsePlanner:
    """Convert a cloud vision-model response into one structured action."""

    def __init__(self, router: Any, max_output_chars: int = 4000) -> None:
        self.router = router
        self.max_output_chars = max_output_chars

    @staticmethod
    def _prompt(goal: str) -> str:
        return (
            'You are Jarvis\'s computer-use planner. Return ONLY a JSON object of the form '
            '{"action":"move|click|scroll|type_text|hotkey|wait|open_app|done","arguments":{...}}. '
            "Choose exactly one next action. Never output shell commands, PowerShell, scripts, arbitrary executable paths, "
            "registry edits, or unsupported actions. Use done only when the user's goal is visibly complete. "
            "Coordinates must refer to the supplied screenshot. Keep the action minimal.\n\n"
            f"User goal: {goal}"
        )

    def __call__(self, goal: str, observation: Any) -> Iterable[ComputerUseAction]:
        summary = {k: v for k, v in observation.items() if k != "image_data_url"} if isinstance(observation, dict) else observation
        content: list[dict[str, Any]] = [{"type": "text", "text": self._prompt(goal) + "\n\nCurrent observation:\n" + json.dumps(summary, ensure_ascii=True)}]
        image_url = observation.get("image_data_url") if isinstance(observation, dict) else None
        if isinstance(image_url, str) and image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        response, _provider = self.router.complete_profiled([{"role": "user", "content": content}], RequestProfile.VISION)
        cleaned = response[: self.max_output_chars].strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").removeprefix("json").removesuffix("```").strip()
        data = json.loads(cleaned)
        if not isinstance(data, dict) or not isinstance(data.get("action"), str):
            raise ValueError("vision planner returned an invalid action object")
        return (ComputerUseAction(data["action"], dict(data.get("arguments") or {})),)


class ComputerUseAgent:
    """Run a model-produced, allowlisted computer plan with continuous re-planning."""

    def __init__(self, planner: Callable[[str, Any], Iterable[ComputerUseAction]], computer: Any, observer: Any, max_steps: int = 10, max_wait_seconds: float = 5.0) -> None:
        if not 1 <= max_steps <= 20:
            raise ValueError("max_steps must be between 1 and 20")
        if not 0 < max_wait_seconds <= 5:
            raise ValueError("max_wait_seconds must be between 0 and 5 seconds")
        self.planner, self.computer, self.observer = planner, computer, observer
        self.max_steps, self.max_wait_seconds = max_steps, max_wait_seconds

    @staticmethod
    def validate(action: ComputerUseAction) -> ComputerUseAction:
        if action.kind not in _ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported computer-use action: {action.kind}")
        a = dict(action.arguments)
        if action.kind == "move":
            if not all(isinstance(a.get(k), int) for k in ("x", "y")) or not (0 <= a["x"] <= 10000 and 0 <= a["y"] <= 10000):
                raise ValueError("move requires bounded integer x and y")
        elif action.kind == "click":
            if a.get("button", "left") not in {"left", "middle", "right"} or not isinstance(a.get("clicks", 1), int) or not 1 <= a.get("clicks", 1) <= 3:
                raise ValueError("invalid click arguments")
        elif action.kind == "scroll":
            if not isinstance(a.get("amount"), int) or not -20 <= a["amount"] <= 20:
                raise ValueError("scroll amount is out of bounds")
        elif action.kind == "type_text":
            if not isinstance(a.get("text"), str) or len(a["text"]) > 4000:
                raise ValueError("type_text exceeds the safety limit")
        elif action.kind == "hotkey":
            keys = a.get("keys")
            if not isinstance(keys, (list, tuple)) or not 1 <= len(keys) <= 5 or not all(isinstance(k, str) and k for k in keys):
                raise ValueError("hotkey requires 1-5 keys")
        elif action.kind == "wait":
            if not isinstance(a.get("seconds", 0.25), (int, float)) or not 0 <= float(a.get("seconds", 0.25)) <= 5:
                raise ValueError("wait is out of bounds")
        elif action.kind == "open_app":
            if not isinstance(a.get("name"), str) or not a["name"].strip() or len(a["name"]) > 200:
                raise ValueError("open_app requires a known application name")
        return ComputerUseAction(action.kind, a)

    def _execute(self, action: ComputerUseAction) -> Any:
        a = action.arguments
        if action.kind == "move": return self.computer.move(a["x"], a["y"])
        if action.kind == "click": return self.computer.click(a.get("button", "left"), a.get("clicks", 1))
        if action.kind == "scroll": return self.computer.scroll(a["amount"])
        if action.kind == "type_text": return self.computer.type_text(a["text"])
        if action.kind == "hotkey": return self.computer.hotkey(*a["keys"])
        if action.kind == "wait": time.sleep(min(float(a.get("seconds", 0.25)), self.max_wait_seconds)); return None
        if action.kind == "open_app": return self.computer.open_known_app(a["name"])
        return None

    def run(self, goal: str) -> ComputerUseResult:
        if not goal.strip():
            raise ValueError("goal cannot be empty")
        observation = self.observer.observe()
        observations = 1
        for step in range(1, self.max_steps + 1):
            planned = tuple(self.planner(goal.strip(), observation))
            if not planned:
                return ComputerUseResult(False, step - 1, observations, observation, ("planner returned no action",))
            action = self.validate(planned[0])
            if action.kind == "done":
                return ComputerUseResult(True, step - 1, observations, observation)
            try:
                self._execute(action)
            except Exception as exc:
                return ComputerUseResult(False, step - 1, observations, observation, (f"{action.kind}: {exc}",))
            observation = self.observer.observe()
            observations += 1
        return ComputerUseResult(False, self.max_steps, observations, observation, ("maximum computer-use steps reached",))
