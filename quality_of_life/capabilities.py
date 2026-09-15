"""Stable catalog of typed capabilities exposed by the agent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .permissions import Capability


class OperationRisk(str, Enum):
    READ = "read"
    MUTATE = "mutate"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"


@dataclass(frozen=True)
class OperationSpec:
    name: str
    capability: Capability
    risk: OperationRisk
    description: str


OPERATION_CATALOG: tuple[OperationSpec, ...] = (
    OperationSpec("computer.move", Capability.MOUSE_CONTROL, OperationRisk.MUTATE, "Move the pointer"),
    OperationSpec("computer.click", Capability.MOUSE_CONTROL, OperationRisk.MUTATE, "Click at the current pointer position"),
    OperationSpec("computer.type_text", Capability.KEYBOARD_CONTROL, OperationRisk.EXTERNAL, "Type text into the focused application"),
    OperationSpec("computer.open_app", Capability.APP_LAUNCH, OperationRisk.EXTERNAL, "Launch a known application"),
    OperationSpec("screen.capture", Capability.SCREEN_READ, OperationRisk.READ, "Capture the current screen"),
    OperationSpec("browser.open_url", Capability.BROWSER_CONTROL, OperationRisk.EXTERNAL, "Open a validated web URL"),
    OperationSpec("files.search", Capability.FILE_READ, OperationRisk.READ, "Search within permitted filesystem locations"),
    OperationSpec("files.read", Capability.FILE_READ, OperationRisk.READ, "Read a text file"),
    OperationSpec("files.write", Capability.FILE_WRITE, OperationRisk.MUTATE, "Write a text file"),
    OperationSpec("files.copy", Capability.FILE_WRITE, OperationRisk.MUTATE, "Copy a file or directory"),
    OperationSpec("files.move", Capability.FILE_WRITE, OperationRisk.MUTATE, "Move a file or directory"),
    OperationSpec("files.delete", Capability.FILE_DELETE, OperationRisk.DESTRUCTIVE, "Delete an explicitly selected path"),
    OperationSpec("applications.list", Capability.APP_READ, OperationRisk.READ, "List installed applications"),
    OperationSpec("applications.uninstall", Capability.APP_WRITE, OperationRisk.DESTRUCTIVE, "Uninstall a uniquely selected application"),
    OperationSpec("processes.list", Capability.PROCESS_READ, OperationRisk.READ, "Inspect running processes"),
    OperationSpec("processes.stop", Capability.PROCESS_CONTROL, OperationRisk.MUTATE, "Stop a selected process"),
    OperationSpec("services.list", Capability.SERVICE_READ, OperationRisk.READ, "Inspect Windows services"),
    OperationSpec("services.restart", Capability.SERVICE_CONTROL, OperationRisk.MUTATE, "Restart a selected service"),
    OperationSpec("system.inspect", Capability.SYSTEM_DIAGNOSTICS, OperationRisk.READ, "Inspect supported system state"),
    OperationSpec("system.change_setting", Capability.SYSTEM_SETTINGS, OperationRisk.MUTATE, "Change a supported setting"),
    OperationSpec("background.start", Capability.BACKGROUND_JOBS, OperationRisk.MUTATE, "Start a bounded background job"),
    OperationSpec("background.cancel", Capability.BACKGROUND_JOBS, OperationRisk.MUTATE, "Cancel a background job"),
    OperationSpec("self_coding.run", Capability.REPO_WRITE, OperationRisk.EXTERNAL, "Run guarded repository coding"),
    OperationSpec("windows_maintenance.diagnose", Capability.SYSTEM_DIAGNOSTICS, OperationRisk.READ, "Diagnose Windows state"),
    OperationSpec("windows_maintenance.handle", Capability.SYSTEM_MAINTENANCE, OperationRisk.DESTRUCTIVE, "Perform a guarded Windows maintenance action"),
)


def operation(name: str) -> OperationSpec:
    for spec in OPERATION_CATALOG:
        if spec.name == name:
            return spec
    raise KeyError(f"unknown capability operation: {name}")


def operations_for(capability: Capability) -> tuple[OperationSpec, ...]:
    return tuple(spec for spec in OPERATION_CATALOG if spec.capability is capability)
