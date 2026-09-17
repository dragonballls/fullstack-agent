"""Persistent Jarvis workspace state shared by visual surfaces and commands."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class WorkspaceType(str, Enum):
    HOME = "home"
    GODS_EYE = "gods-eye"
    CODING = "coding"
    BROWSER = "browser"
    SYSTEM = "system"
    WORKFLOWS = "workflows"


@dataclass(frozen=True)
class WorkspaceState:
    active: WorkspaceType
    command_bar_visible: bool
    input_mode: str
    panels: tuple[str, ...]

    @classmethod
    def default(cls) -> "WorkspaceState":
        return cls(
            active=WorkspaceType.HOME,
            command_bar_visible=True,
            input_mode="text",
            panels=("overview", "activity", "command"),
        )

    def activate(self, workspace: WorkspaceType) -> "WorkspaceState":
        panels = {
            WorkspaceType.HOME: ("overview", "activity", "command"),
            WorkspaceType.GODS_EYE: ("map", "entities", "activity", "command"),
            WorkspaceType.CODING: ("editor", "agent", "activity", "command"),
            WorkspaceType.BROWSER: ("browser", "agent", "activity", "command"),
            WorkspaceType.SYSTEM: ("health", "processes", "activity", "command"),
            WorkspaceType.WORKFLOWS: ("workflows", "queue", "activity", "command"),
        }[workspace]
        return replace(
            self,
            active=workspace,
            command_bar_visible=True,
            input_mode="text",
            panels=panels,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "active": self.active.value,
            "command_bar_visible": self.command_bar_visible,
            "input_mode": self.input_mode,
            "panels": list(self.panels),
        }
