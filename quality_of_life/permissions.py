"""Capability policy used by quality-of-life tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CapabilityDenied(PermissionError):
    """Raised when a tool operation is outside the configured capability set."""


class Capability(str, Enum):
    SCREEN_READ = "screen.read"
    LOCATION_READ = "location.read"
    MOUSE_CONTROL = "mouse.control"
    KEYBOARD_CONTROL = "keyboard.control"
    CLIPBOARD = "clipboard"
    WINDOW_CONTROL = "window.control"
    APP_LAUNCH = "app.launch"
    BROWSER_CONTROL = "browser.control"
    REPO_READ = "repo.read"
    REPO_WRITE = "repo.write"
    BACKGROUND_JOBS = "background.jobs"
    CLOUD_ROUTING = "cloud.routing"
    SYSTEM_MAINTENANCE = "system.maintenance"


@dataclass(frozen=True)
class CapabilityPolicy:
    """Small deny-by-default policy shared by all quality-of-life tools."""

    allowed: frozenset[Capability] = frozenset()
    require_confirmation: frozenset[Capability] = frozenset({
        Capability.MOUSE_CONTROL,
        Capability.KEYBOARD_CONTROL,
        Capability.WINDOW_CONTROL,
        Capability.APP_LAUNCH,
        Capability.BROWSER_CONTROL,
        Capability.REPO_WRITE,
        Capability.BACKGROUND_JOBS,
        Capability.SYSTEM_MAINTENANCE,
    })

    def check(self, capability: Capability) -> None:
        if capability not in self.allowed:
            raise CapabilityDenied(f"Capability is not enabled: {capability.value}")

    def needs_confirmation(self, capability: Capability) -> bool:
        return capability in self.require_confirmation
