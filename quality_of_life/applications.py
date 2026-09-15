"""Windows installed-application inventory and guarded uninstall support."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .permissions import Capability, CapabilityPolicy


class ApplicationError(RuntimeError):
    """Raised when an application operation cannot be performed safely."""


@dataclass(frozen=True)
class InstalledApplication:
    id: str
    name: str
    publisher: str
    version: str
    uninstall_string: str | None
    source: str


class ApplicationManager:
    def __init__(self, policy: CapabilityPolicy, provider: Callable[[], Iterable[InstalledApplication]] | None = None) -> None:
        self.policy = policy
        self.provider = provider or self._registry_inventory

    @staticmethod
    def _registry_inventory() -> tuple[InstalledApplication, ...]:
        try:
            import winreg
        except ImportError:
            return ()
        results: list[InstalledApplication] = []
        locations = (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM32"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKCU"),
        )
        for hive, path, source in locations:
            try:
                with winreg.OpenKey(hive, path) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            subkey_name = winreg.EnumKey(root, index)
                            with winreg.OpenKey(root, subkey_name) as key:
                                name = str(winreg.QueryValueEx(key, "DisplayName")[0]).strip()
                                if not name:
                                    continue
                                publisher = str(_value(winreg, key, "Publisher") or "")
                                version = str(_value(winreg, key, "DisplayVersion") or "")
                                uninstall = _value(winreg, key, "UninstallString")
                                results.append(InstalledApplication(subkey_name, name, publisher, version, str(uninstall) if uninstall else None, source))
                        except (OSError, ValueError):
                            continue
            except OSError:
                continue
        return tuple(sorted(results, key=lambda item: (item.name.casefold(), item.id)))

    def list(self) -> tuple[InstalledApplication, ...]:
        self.policy.check(Capability.APP_READ)
        return tuple(self.provider())

    def resolve(self, name_or_id: str) -> InstalledApplication:
        target = name_or_id.strip().casefold()
        if not target:
            raise ApplicationError("Application name or id is required")
        exact = [app for app in self.list() if app.id.casefold() == target or app.name.casefold() == target]
        if len(exact) == 1:
            return exact[0]
        matches = [app for app in self.list() if target in app.name.casefold()]
        if len(matches) != 1:
            raise ApplicationError("Application selection is ambiguous or unavailable")
        return matches[0]

    @staticmethod
    def _safe_uninstaller(app: InstalledApplication) -> list[str]:
        raw = (app.uninstall_string or "").strip()
        if not raw:
            raise ApplicationError("Application has no registered uninstaller")
        if any(char in raw for char in "&|<>\n\r"):
            raise ApplicationError("Unsafe uninstall command metadata")
        try:
            parts = shlex.split(raw, posix=False)
        except ValueError as exc:
            raise ApplicationError("Invalid uninstall command metadata") from exc
        if not parts:
            raise ApplicationError("Invalid uninstall command metadata")
        executable = parts[0].strip('"')
        if not os.path.isabs(executable):
            resolved = next((os.path.join(path, executable) for path in os.environ.get("PATH", "").split(os.pathsep) if os.path.isfile(os.path.join(path, executable))), None)
            executable = resolved or executable
        if not os.path.isabs(executable) or not os.path.isfile(executable):
            raise ApplicationError("Registered uninstaller executable could not be verified")
        return [executable, *[part.strip('"') for part in parts[1:]]]

    def uninstall(self, name_or_id: str, confirmed: bool = False) -> InstalledApplication:
        self.policy.check(Capability.APP_WRITE)
        if not confirmed:
            raise PermissionError("Confirmation is required before uninstalling an application")
        app = self.resolve(name_or_id)
        lowered = f"{app.name} {app.publisher}".casefold()
        protected_terms = ("microsoft windows", "windows defender", "security", "system", "driver")
        if any(term in lowered for term in protected_terms):
            raise ApplicationError("Protected/system application cannot be uninstalled by this capability")
        command = self._safe_uninstaller(app)
        subprocess.Popen(command, shell=False)
        return app


def _value(winreg: Any, key: Any, name: str) -> Any:
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None
