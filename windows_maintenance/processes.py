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

    def candidates(
        self,
        foreground: int | None = None,
        min_memory_mb: int = 250,
        min_cpu_percent: float = 15.0,
        min_gpu_percent: float = 10.0,
        min_network_connections: int = 20,
    ) -> list[dict[str, object]]:
        rows = self.list_processes()
        result: list[dict[str, object]] = []
        for row in rows:
            try:
                pid = int(row.get("Id") or 0)
                name = str(row.get("ProcessName") or "")
                path = str(row.get("Path") or "")
                memory_mb = float(row.get("WorkingSet64") or 0) / 1024 / 1024
                cpu = float(row.get("CPUPercent") or 0)
                gpu = float(row.get("GPUPercent") or 0)
                network = int(row.get("NetworkConnections") or 0)
            except (TypeError, ValueError):
                continue
            if pid <= 0 or not name or pid == foreground:
                continue
            if self.policy.is_protected_process(name, path):
                continue
            signals: list[str] = []
            if memory_mb >= min_memory_mb:
                signals.append(f"{memory_mb:.0f} MB RAM")
            if cpu >= min_cpu_percent:
                signals.append(f"{cpu:.1f}% CPU")
            if gpu >= min_gpu_percent:
                signals.append(f"{gpu:.1f}% GPU")
            if network >= min_network_connections:
                signals.append(f"{network} network connections")
            if not bool(row.get("Responding", True)):
                signals.append("not responding")
            if signals:
                result.append({**row, "reason": ", ".join(signals), "memory_mb": round(memory_mb, 1)})
        return sorted(result, key=lambda item: (float(item.get("CPUPercent", 0)) + float(item.get("GPUPercent", 0)) + float(item.get("memory_mb", 0)) / 50), reverse=True)

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
