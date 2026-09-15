"""Capability registry for the quality-of-life layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    factory: Callable[..., Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown quality-of-life tool: {name}") from exc


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec("computer", "Windows mouse, keyboard, scrolling, and app launch", "quality_of_life.computer.ComputerController"))
    registry.register(ToolSpec("screen", "Screen capture for computer-aware reasoning", "quality_of_life.screen.ScreenCapture"))
    registry.register(ToolSpec("browser", "Optional Playwright browser automation", "quality_of_life.browser.BrowserController"))
    registry.register(ToolSpec("background", "Bounded cancellable background jobs", "quality_of_life.background.BackgroundJobs"))
    registry.register(ToolSpec("cloud_router", "Ordered cloud-provider failover", "quality_of_life.router.CloudModelRouter"))
    return registry
