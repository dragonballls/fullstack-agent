from __future__ import annotations

from . import windows
from .models import MaintenanceAction, OperationResult, RiskClass
from .policy import MaintenancePolicy


RUN_KEY = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"


class StartupManager:
    """Inspect and safely disable reversible current-user startup entries."""

    def __init__(self, policy: MaintenancePolicy | None = None) -> None:
        self.policy = policy or MaintenancePolicy()

    def list_entries(self) -> list[dict[str, object]]:
        return windows.startup_entries()

    def disable(self, name: str, command: str | None = None) -> OperationResult:
        action = MaintenanceAction("startup.disable", name, {"command": command or ""}, RiskClass.REVERSIBLE_MEDIUM_RISK, "Prevent an explicitly requested user application from auto-starting.")
        decision = self.policy.evaluate(action, explicit_user_request=True)
        if not decision.allowed:
            return OperationResult(action.operation, action.target_id, False, error=decision.reason)
        try:
            entries = self.list_entries()
            match = next((e for e in entries if str(e.get("Name", "")).casefold() == name.casefold()), None)
            if not match:
                return OperationResult(action.operation, action.target_id, False, error="startup entry not found")
            location = str(match.get("Location", ""))
            normalized = location.replace("/", "\\")
            if RUN_KEY.casefold() not in normalized.casefold():
                return OperationResult(action.operation, action.target_id, False, error="startup entry is not in the supported reversible user Run key")
            previous = windows.disable_user_run_entry(name)
            return OperationResult(action.operation, action.target_id, True, changed=True, verified=True, rollback_available=True, detail="startup entry removed from the current-user Run key")
        except Exception as exc:
            return OperationResult(action.operation, action.target_id, False, error=str(exc))

    def restore(self, name: str, previous_command: str) -> OperationResult:
        action = MaintenanceAction("startup.restore", name, {"previous_command": previous_command}, RiskClass.REVERSIBLE_MEDIUM_RISK, "Restore an earlier user startup entry.")
        decision = self.policy.evaluate(action, explicit_user_request=True)
        if not decision.allowed:
            return OperationResult(action.operation, action.target_id, False, error=decision.reason)
        try:
            windows.restore_user_run_entry(name, previous_command)
            return OperationResult(action.operation, action.target_id, True, changed=True, verified=True, rollback_available=True, detail="startup entry restored")
        except Exception as exc:
            return OperationResult(action.operation, action.target_id, False, error=str(exc))
