"""Deterministic gesture interpreter and guarded desktop-input bridge."""
from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any


@dataclass(frozen=True)
class HandSample:
    x: float
    y: float
    pinch: bool
    fingers: int
    confidence: float


@dataclass(frozen=True)
class HandEvent:
    kind: str
    x: float | None = None
    y: float | None = None
    amount: int = 0
    button: str = "left"


class HandGestureInterpreter:
    """Translate stable normalized hand poses into bounded input events."""

    def __init__(
        self,
        *,
        min_confidence: float = 0.80,
        move_deadzone: float = 0.008,
        click_cooldown_s: float = 0.35,
        drag_hold_s: float = 0.30,
        pose_debounce_frames: int = 3,
        resume_frames: int = 5,
    ) -> None:
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        if move_deadzone < 0 or click_cooldown_s < 0 or drag_hold_s < 0:
            raise ValueError("timing/dead-zone values cannot be negative")
        if pose_debounce_frames < 1 or resume_frames < 1:
            raise ValueError("frame thresholds must be positive")
        self.min_confidence = min_confidence
        self.move_deadzone = move_deadzone
        self.click_cooldown_s = click_cooldown_s
        self.drag_hold_s = drag_hold_s
        self.pose_debounce_frames = pose_debounce_frames
        self.resume_frames = resume_frames
        self._enabled = True
        self._previous: HandSample | None = None
        self._pinch_started_at: float | None = None
        self._last_click = float("-inf")
        self._dragging = False
        self._fist_frames = 0
        self._resume_frames = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self) -> None:
        self._enabled = False
        self._previous = None
        self._pinch_started_at = None
        self._dragging = False
        self._fist_frames = 0
        self._resume_frames = 0

    def enable(self) -> None:
        self._enabled = True
        self._previous = None
        self._pinch_started_at = None
        self._dragging = False
        self._fist_frames = 0
        self._resume_frames = 0

    @staticmethod
    def _valid(sample: HandSample) -> bool:
        return (
            0.0 <= sample.x <= 1.0
            and 0.0 <= sample.y <= 1.0
            and 0 <= sample.fingers <= 5
            and math.isfinite(sample.confidence)
        )

    def interpret(self, sample: HandSample, *, timestamp: float | None = None) -> tuple[HandEvent, ...]:
        now = time.monotonic() if timestamp is None else timestamp
        if not self._valid(sample) or sample.confidence < self.min_confidence:
            return ()

        previous = self._previous
        self._previous = sample

        if not self._enabled:
            if sample.fingers == 5 and not sample.pinch:
                self._resume_frames += 1
                if self._resume_frames >= self.resume_frames:
                    self.enable()
                    return (HandEvent(kind="resume"),)
            else:
                self._resume_frames = 0
            return ()

        self._resume_frames = 0

        if sample.fingers == 0:
            self._fist_frames += 1
            if self._fist_frames >= self.pose_debounce_frames:
                self.disable()
                return (HandEvent(kind="pause"),)
            return ()
        self._fist_frames = 0

        events: list[HandEvent] = []
        if sample.fingers == 1:
            moved = (
                previous is None
                or abs(sample.x - previous.x) >= self.move_deadzone
                or abs(sample.y - previous.y) >= self.move_deadzone
            )
            if moved:
                events.append(HandEvent(kind="move", x=sample.x, y=sample.y))

        if sample.fingers == 2 and previous is not None:
            dy = sample.y - previous.y
            if abs(dy) >= self.move_deadzone:
                amount = max(-5, min(5, round(-dy * 20)))
                if amount:
                    events.append(HandEvent(kind="scroll", amount=amount))

        if sample.pinch and not (previous and previous.pinch):
            self._pinch_started_at = now
        elif not sample.pinch and previous and previous.pinch:
            started = self._pinch_started_at
            duration = 0.0 if started is None else max(0.0, now - started)
            if self._dragging:
                self._dragging = False
                self._pinch_started_at = None
                events.append(HandEvent(kind="drag_end"))
            elif now - self._last_click >= self.click_cooldown_s:
                self._pinch_started_at = None
                self._last_click = now
                events.append(HandEvent(kind="click"))
            elif duration >= self.drag_hold_s:
                self._pinch_started_at = None
        elif sample.pinch and self._pinch_started_at is not None and not self._dragging:
            if now - self._pinch_started_at >= self.drag_hold_s:
                self._dragging = True
                events.append(HandEvent(kind="drag_start"))

        return tuple(events)


class HandControlBridge:
    """Map approved hand events through desktop or physical-device input."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        controller: Any | None = None,
        device_adapter: Any | None = None,
        target_device_id: str | None = None,
    ) -> None:
        self.enabled = enabled
        self.controller = controller
        self.device_adapter = device_adapter
        self.target_device_id = target_device_id

    def set_device_target(self, device_id: str | None) -> None:
        self.target_device_id = device_id

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False
        if self.controller is not None and hasattr(self.controller, "pyautogui"):
            try:
                self.controller.pyautogui.mouseUp(button="left")
            except Exception:
                pass

    @staticmethod
    def _screen_coordinates(x: float, y: float, width: int, height: int) -> tuple[int, int]:
        if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
            raise ValueError("hand coordinates must be normalized to 0..1")
        return round(x * max(width - 1, 0)), round(y * max(height - 1, 0))

    def dispatch(self, event: HandEvent) -> bool:
        if event.kind == "resume":
            self.enable()
            return True
        if event.kind == "pause":
            self.disable()
            return True
        if not self.enabled:
            return False
        if self.target_device_id is not None:
            if self.device_adapter is None:
                return False
            result = self.device_adapter.route_hand_event(
                self.target_device_id, event, confirmed=True
            )
            return bool(getattr(result, "ok", False))
        if self.controller is None:
            return False
        if event.kind == "move":
            width, height = self.controller.pyautogui.size()
            x, y = self._screen_coordinates(float(event.x), float(event.y), int(width), int(height))
            self.controller.move(x, y)
            return True
        if event.kind == "click":
            self.controller.click(button=event.button)
            return True
        if event.kind == "scroll":
            self.controller.scroll(event.amount)
            return True
        if event.kind == "drag_start":
            self.controller.pyautogui.mouseDown(button=event.button)
            return True
        if event.kind == "drag_end":
            self.controller.pyautogui.mouseUp(button=event.button)
            return True
        return False
