"""Windows installed-application inventory and guarded install/update/uninstall support."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
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
    _PACKAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

    def __init__(self, policy: CapabilityPolicy, provider: Callable[[], Iterable[InstalledApplication]] | None = None, launcher: Callable[[list[str]], Any] | None = None, runner: Callable[..., subprocess.CompletedProcess[str]] | None = None) -> None:
        self.policy = policy
        self.provider = provider or self._registry_inventory
        self._launcher = launcher or (lambda command: subprocess.Popen(command, shell=False))
        self._runner = runner or subprocess.run

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
        inventory = self.list()
        exact = [app for app in inventory if app.id.casefold() == target or app.name.casefold() == target]
        if len(exact) == 1:
            return exact[0]
        matches = [app for app in inventory if target in app.name.casefold()]
        if len(matches) != 1:
            raise ApplicationError("Application selection is ambiguous or unavailable")
        return matches[0]

    @classmethod
    def _validate_package_id(cls, package_id: str) -> str:
        value = package_id.strip()
        if not cls._PACKAGE_ID.fullmatch(value):
            raise ApplicationError("Invalid package id")
        return value

    def _winget(self, action: str, package_id: str) -> bool:
        package_id = self._validate_package_id(package_id)
        result = self._runner(["winget", action, "--id", package_id, "--exact", "--accept-source-agreements", "--accept-package-agreements"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise ApplicationError(f"winget {action} failed")
        verify = self._runner(["winget", "list", "--id", package_id, "--exact"], capture_output=True, text=True, check=False)
        if action == "uninstall":
            return verify.returncode != 0 or package_id.casefold() not in verify.stdout.casefold()
        return verify.returncode == 0 and package_id.casefold() in verify.stdout.casefold()

    def install(self, package_id: str, confirmed: bool = False) -> bool:
        self.policy.check(Capability.APP_WRITE)
        if not confirmed:
            raise PermissionError("Confirmation is required before installing software")
        return self._winget("install", package_id)

    def update(self, package_id: str, confirmed: bool = False) -> bool:
        self.policy.check(Capability.APP_WRITE)
        if not confirmed:
            raise PermissionError("Confirmation is required before updating software")
        return self._winget("upgrade", package_id)

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
            executable = next((os.path.join(path, executable) for path in os.environ.get("PATH", "").split(os.pathsep) if os.path.isfile(os.path.join(path, executable))), executable)
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
        process = self._launcher(command)
        if hasattr(process, "poll") and process.poll() is not None and process.returncode not in (0, None):
            raise ApplicationError("Registered uninstaller exited unsuccessfully")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if not any(item.id == app.id or item.name.casefold() == app.name.casefold() for item in self.provider()):
                return app
            time.sleep(0.25)
        raise ApplicationError("Uninstaller started but removal could not be verified within 30 seconds")


def _value(winreg: Any, key: Any, name: str) -> Any:
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None
