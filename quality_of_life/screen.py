"""Screen capture helpers for computer-aware agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .permissions import Capability, CapabilityPolicy


class ScreenCaptureUnavailable(RuntimeError):
    """Raised when screen-capture dependencies are unavailable."""


class ScreenCapture:
    def __init__(self, policy: CapabilityPolicy, mss_module: Any | None = None) -> None:
        self.policy = policy
        try:
            if mss_module is None:
                import mss  # type: ignore
                mss_module = mss
        except ImportError as exc:
            raise ScreenCaptureUnavailable("Install quality_of_life optional dependencies to enable screenshots.") from exc
        self._mss = mss_module

    def capture(self, output: Path | None = None) -> bytes:
        self.policy.check(Capability.SCREEN_READ)
        with self._mss.mss() as session:
            monitor = session.monitors[1]
            shot = session.grab(monitor)
            raw = bytes(shot.rgb)
            if output is not None:
                try:
                    from PIL import Image  # type: ignore
                except ImportError as exc:
                    raise ScreenCaptureUnavailable("Pillow is required when saving screenshots.") from exc
                image = Image.frombytes("RGB", shot.size, raw)
                output.parent.mkdir(parents=True, exist_ok=True)
                image.save(output)
            return raw
