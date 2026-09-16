"""Optional tracker contract and browser-sample adapter for hand control.

The core package never imports a camera SDK. The browser tracker can send
normalized hand samples to the loopback bridge, and this adapter validates them
without knowing which camera/model produced them.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Any

from .hand_control import HandSample


class HandTrackingUnavailable(RuntimeError):
    """Raised only when a concrete optional tracker cannot be started."""


@dataclass(frozen=True)
class TrackingStatus:
    state: str
    detail: str = ""

    @property
    def available(self) -> bool:
        return self.state == "available"


def sample_from_payload(payload: Mapping[str, Any]) -> HandSample:
    """Validate a tracker payload without importing a camera/ML dependency."""
    try:
        sample = HandSample(
            x=float(payload["x"]),
            y=float(payload["y"]),
            pinch=bool(payload["pinch"]),
            fingers=int(payload["fingers"]),
            confidence=float(payload["confidence"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid hand tracking payload") from exc
    if not (
        0.0 <= sample.x <= 1.0
        and 0.0 <= sample.y <= 1.0
        and 0 <= sample.fingers <= 5
        and math.isfinite(sample.confidence)
    ):
        raise ValueError("hand tracking values are outside their allowed ranges")
    return sample


class BrowserHandTrackingAdapter:
    """Contract object for the local browser/MediaPipe tracker."""

    name = "browser-mediapipe"

    def status(self, *, camera_permission: bool = True) -> TrackingStatus:
        if not camera_permission:
            return TrackingStatus("degraded", "camera permission denied")
        return TrackingStatus("available", "browser supplies normalized samples")

    def sample(self, payload: Mapping[str, Any]) -> HandSample:
        return sample_from_payload(payload)
