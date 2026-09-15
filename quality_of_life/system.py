"""Read-only system inspection and a small allowlisted settings adapter."""

from __future__ import annotations

import os
import platform
import socket
from dataclasses import dataclass
from typing import Any, Callable

from .permissions import Capability, CapabilityPolicy


class SystemCapabilityError(RuntimeError):
    """Raised for unsupported or unsafe system-setting operations."""


@dataclass(frozen=True)
class SystemSnapshot:
    platform: str
    release: str
    hostname: str
    python: str
    cpu_count: int
    network_hostname: str


class SystemController:
    _SETTINGS = {
        "show_file_extensions": (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "HideFileExt"),
        "show_hidden_files": (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Hidden"),
    }

    def __init__(self, policy: CapabilityPolicy, registry: Any | None = None) -> None:
        self.policy = policy
        self.registry = registry

    def inspect(self) -> SystemSnapshot:
        self.policy.check(Capability.SYSTEM_DIAGNOSTICS)
        return SystemSnapshot(platform.system(), platform.release(), socket.gethostname(), platform.python_version(), os.cpu_count() or 1, socket.getfqdn())

    def get_setting(self, name: str) -> int:
        self.policy.check(Capability.SYSTEM_DIAGNOSTICS)
        if name not in self._SETTINGS:
            raise SystemCapabilityError(f"Unsupported system setting: {name}")
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._SETTINGS[name][0]) as key:
                return int(winreg.QueryValueEx(key, self._SETTINGS[name][1])[0])
        except (ImportError, OSError, ValueError) as exc:
            raise SystemCapabilityError("Setting is unavailable on this system") from exc

    def set_setting(self, name: str, value: int, confirmed: bool = False) -> int:
        self.policy.check(Capability.SYSTEM_SETTINGS)
        if not confirmed:
            raise PermissionError("Confirmation is required before changing system settings")
        if name not in self._SETTINGS or value not in {0, 1}:
            raise SystemCapabilityError("Unsupported setting or value")
        try:
            import winreg
            path, key_name = self._SETTINGS[name]
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
                winreg.SetValueEx(key, key_name, 0, winreg.REG_DWORD, value)
                actual = int(winreg.QueryValueEx(key, key_name)[0])
            if actual != value:
                raise SystemCapabilityError("Setting change could not be verified")
            return actual
        except (ImportError, OSError, ValueError) as exc:
            raise SystemCapabilityError("Setting change is unavailable on this system") from exc

    def network(self) -> dict[str, Any]:
        self.policy.check(Capability.SYSTEM_DIAGNOSTICS)
        result: dict[str, Any] = {"hostname": socket.gethostname(), "fqdn": socket.getfqdn()}
        try:
            result["addresses"] = sorted({item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None) if item[4]})
        except OSError:
            result["addresses"] = []
        return result
