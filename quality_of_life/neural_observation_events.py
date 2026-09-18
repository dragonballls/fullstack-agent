"""Safe high-level observable breadcrumbs for Neural JARVIS."""

from __future__ import annotations

from typing import Any
import logging

LOGGER = logging.getLogger(__name__)


def publish_observation(runtime: Any, stage: str, message: str, **details: object) -> None:
    publisher = getattr(runtime, "publish_neural_observation", None)
    if not callable(publisher):
        return
    try:
        publisher(stage, message, **details)
    except Exception as exc:
        LOGGER.warning("neural observation publish failed (%s)", type(exc).__name__)
