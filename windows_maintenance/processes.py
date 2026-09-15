from __future__ import annotations

from . import windows
from .models import MaintenanceAction, OperationResult, RiskClass
from .policy import MaintenancePolicy


class ProcessManager:
    """Inspect Windows processes and stop only verified, unprotected user processes."""

    def __init__(self, policy: MaintenancePolicy | None = None) -> None:
        self.policy = policy or MaintenancePolicy()

    def list_processes(self) -> list[dict[str, object]]:
        return windows.process_list()

    def candidates(self, foreground: int | None = None, min_memory_mb: int = 250) -> list[dict[str, object]]:
        rows = self.list_processes()
        result: list[dict[str, object]] = []
        for row in rows:
            try:
                pid = int(row.get("Id") or 0)
                name = str(row.get("ProcessName") or "")
                path = str(row.get("Path") or "")
                memory_mb = float(row.get("WorkingSet64") or 0) / 1024 / 1024
            except (TypeError, ValueError):
                continue
            if pid <= 0 or not name or pid == foreground:
                continue
            if self.policy.is_protected_process(name, path):
                continue
            if not bool(row.get("Responding", True)):
                # Hung user applications are useful cleanup candidates but remain user-process-only.
                result.append({**row, "reason": "not responding", "memory_mb": round(memory_mb, 1)})
            elif memory_mb >= min_memory_mb:
                result.append({**row, "reason": "high memory use", "memory_mb": round(memory_mb, 1)})
        return sorted(result, key=lambda item: float(item.get("memory_mb", 0)), reverse=True)

    def stop(self, pid: int, expected_name: str) -> OperationResult:
        action = MaintenanceAction("process.stop", f"{expected_name}.exe", {"pid": pid}, RiskClass.REVERSIBLE_LOW_RISK, "Stop a user-requested background application.")
        decision = self.policy.evaluate(action, explicit_user_request=True)
        if not decision.allowed:
            return OperationResult(action.operation, action.target_id, False, error=decision.reason)
        try:
            success, detail = windows.stop_process(pid, expected_name)
            return OperationResult(action.operation, action.target_id, success, changed=success, verified=success, error=None if success else detail, detail=detail)
        except Exception as exc:
            return OperationResult(action.operation, action.target_id, False, error=str(exc))
