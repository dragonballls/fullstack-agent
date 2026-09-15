from __future__ import annotations

from . import windows
from .models import MaintenanceAction, OperationResult, RiskClass
from .policy import MaintenancePolicy


class RepairManager:
    """Guarded Windows repair operations; high-risk changes require explicit confirmation."""

    def __init__(self, policy: MaintenancePolicy | None = None) -> None:
        self.policy = policy or MaintenancePolicy()

    def system_file_scan(self) -> OperationResult:
        action = MaintenanceAction("system.file_scan", "windows", risk=RiskClass.READ_ONLY, reason="Check component-store and system-file health without repairing.")
        try:
            success, detail = windows.run_system_file_check(repair=False)
            return OperationResult(action.operation, action.target_id, success, verified=success, detail=detail)
        except Exception as exc:
            return OperationResult(action.operation, action.target_id, False, error=str(exc))

    def system_file_repair(self, confirmed: bool = False) -> OperationResult:
        action = MaintenanceAction("system.file_repair", "windows", risk=RiskClass.HIGH_RISK, reason="Repair Windows component and system files.")
        decision = self.policy.evaluate(action, explicit_user_request=True, confirmed=confirmed)
        if not decision.allowed:
            return OperationResult(action.operation, action.target_id, False, error=decision.reason)
        try:
            success, detail = windows.run_system_file_check(repair=True)
            return OperationResult(action.operation, action.target_id, success, changed=success, verified=success, error=None if success else detail, detail=detail)
        except Exception as exc:
            return OperationResult(action.operation, action.target_id, False, error=str(exc))

    def network_reset(self, confirmed: bool = False) -> OperationResult:
        action = MaintenanceAction("network.reset", "windows", risk=RiskClass.HIGH_RISK, reason="Flush DNS and reset Winsock.")
        decision = self.policy.evaluate(action, explicit_user_request=True, confirmed=confirmed)
        if not decision.allowed:
            return OperationResult(action.operation, action.target_id, False, error=decision.reason)
        try:
            success, detail = windows.reset_network()
            return OperationResult(action.operation, action.target_id, success, changed=success, verified=success, error=None if success else detail, detail=detail)
        except Exception as exc:
            return OperationResult(action.operation, action.target_id, False, error=str(exc))
