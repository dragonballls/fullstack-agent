"""Guarded process and Windows-service inspection/control."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .permissions import Capability, CapabilityPolicy


class ProcessControlError(RuntimeError):
    """Raised for unsafe or unverifiable process/service operations."""


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    executable: str | None = None


@dataclass(frozen=True)
class ServiceInfo:
    name: str
    display_name: str
    state: str


class ProcessManager:
    def __init__(self, policy: CapabilityPolicy, process_provider: Callable[[], Iterable[ProcessInfo]] | None = None) -> None:
        self.policy = policy
        self._provider = process_provider or self._default_processes

    @staticmethod
    def _default_processes() -> tuple[ProcessInfo, ...]:
        try:
            import psutil  # type: ignore
        except ImportError:
            return ()
        results: list[ProcessInfo] = []
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                info = proc.info
                results.append(ProcessInfo(int(info["pid"]), str(info.get("name") or ""), info.get("exe")))
            except (psutil.Error, OSError, ValueError):
                continue
        return tuple(sorted(results, key=lambda item: (item.name.casefold(), item.pid)))

    def list_processes(self) -> tuple[ProcessInfo, ...]:
        self.policy.check(Capability.PROCESS_READ)
        return tuple(self._provider())

    @staticmethod
    def _protected(info: ProcessInfo) -> bool:
        name = info.name.casefold()
        return name in {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe", "explorer.exe"}

    def stop(self, pid: int, confirmed: bool = False) -> bool:
        self.policy.check(Capability.PROCESS_CONTROL)
        if not confirmed:
            raise PermissionError("Confirmation is required before stopping a process")
        if pid <= 0:
            raise ValueError("Invalid process id")
        matches = [proc for proc in self.list_processes() if proc.pid == pid]
        if len(matches) != 1:
            raise ProcessControlError("Process identity could not be verified")
        target = matches[0]
        if self._protected(target):
            raise ProcessControlError("Protected process cannot be stopped")
        try:
            import psutil  # type: ignore
            proc = psutil.Process(target.pid)
            if target.executable and proc.exe() != target.executable:
                raise ProcessControlError("Process identity changed before stop")
            proc.terminate()
            proc.wait(timeout=5)
        except ImportError as exc:
            raise ProcessControlError("Process control requires psutil") from exc
        except Exception as exc:
            raise ProcessControlError(f"Unable to stop process {target.name} ({target.pid})") from exc
        return not any(proc.pid == pid for proc in self.list_processes())


class ServiceManager:
    _NAME = re.compile(r"^[A-Za-z0-9_.-]{1,256}$")

    def __init__(self, policy: CapabilityPolicy, runner: Callable[..., subprocess.CompletedProcess[str]] | None = None) -> None:
        self.policy = policy
        self._runner = runner or subprocess.run

    def list_services(self) -> tuple[ServiceInfo, ...]:
        self.policy.check(Capability.SERVICE_READ)
        if not hasattr(__import__("os"), "name") or __import__("os").name != "nt":
            return ()
        result = self._runner(["sc.exe", "query", "type=", "service", "state=", "all"], capture_output=True, text=True, check=False)
        services: list[ServiceInfo] = []
        current_name = ""
        current_display = ""
        current_state = ""
        for line in result.stdout.splitlines():
            text = line.strip()
            if text.startswith("SERVICE_NAME:"):
                if current_name:
                    services.append(ServiceInfo(current_name, current_display, current_state))
                current_name = text.split(":", 1)[1].strip()
                current_display = ""
                current_state = ""
            elif text.startswith("DISPLAY_NAME:"):
                current_display = text.split(":", 1)[1].strip()
            elif text.startswith("STATE") and ":" in text:
                current_state = text.split(":", 1)[1].strip()
        if current_name:
            services.append(ServiceInfo(current_name, current_display, current_state))
        return tuple(services)

    def restart(self, name: str, confirmed: bool = False) -> bool:
        self.policy.check(Capability.SERVICE_CONTROL)
        if not confirmed:
            raise PermissionError("Confirmation is required before restarting a service")
        if not self._NAME.fullmatch(name.strip()):
            raise ValueError("Invalid service name")
        if name.casefold() in {"eventlog", "windefend", "wininit", "plugplay"}:
            raise ProcessControlError("Protected service cannot be restarted by this capability")
        stop = self._runner(["sc.exe", "stop", name], capture_output=True, text=True, check=False)
        if stop.returncode != 0:
            raise ProcessControlError("Service stop request failed")
        start = self._runner(["sc.exe", "start", name], capture_output=True, text=True, check=False)
        if start.returncode != 0:
            raise ProcessControlError("Service start request failed")
        return True
