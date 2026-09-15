from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import DiagnosticCollector
from .models import DiagnosticReport, MaintenanceAction, OperationResult, RiskClass
from .policy import MaintenancePolicy
from .processes import ProcessManager
from .repairs import RepairManager
from .startup import StartupManager
from .audit import AuditLog


@dataclass(frozen=True)
class MaintenanceResponse:
    intent: str
    report: DiagnosticReport | None = None
    results: tuple[OperationResult, ...] = ()
    message: str = ""


def is_maintenance_request(text: str) -> bool:
    lowered = text.casefold()
    markers = (
        "diagnose my pc", "diagnose my computer", "diagnose my windows",
        "fix my pc", "fix my computer", "repair windows", "repair my pc",
        "optimize my pc", "clean up background", "background apps", "wasting resources",
        "using my cpu", "using my ram", "using my gpu", "using my network",
        "startup", "start with windows", "launch at startup", "stop steam",
    )
    return any(marker in lowered for marker in markers)


class MaintenanceFacade:
    """Translate common maintenance requests into bounded, policy-checked operations."""

    def __init__(self, policy: MaintenancePolicy | None = None) -> None:
        self.policy = policy or MaintenancePolicy()
        self.diagnostics = DiagnosticCollector()
        self.processes = ProcessManager(self.policy)
        self.startup = StartupManager(self.policy)
        self.repairs = RepairManager(self.policy)
        self.audit = AuditLog()

    def diagnose(self) -> MaintenanceResponse:
        report = self.diagnostics.collect()
        return MaintenanceResponse("diagnose", report=report, message=self._report_message(report))

    def handle(self, request: str, confirmed: bool = False) -> MaintenanceResponse:
        text = request.strip()
        lowered = text.casefold()
        if "diagnos" in lowered and not any(word in lowered for word in ("fix", "repair", "clean")):
            return self.diagnose()

        results: list[OperationResult] = []
        notes: list[str] = []
        report = self.diagnostics.collect() if is_maintenance_request(text) else None

        if any(phrase in lowered for phrase in ("what is using", "using my cpu", "using my ram", "using my gpu", "background apps", "wasting resources", "clean up background")):
            foreground = None
            try:
                from . import windows
                foreground = windows.foreground_pid()
            except Exception:
                pass
            candidates = self.processes.candidates(foreground=foreground)
            if candidates:
                top = ", ".join(f"{c.get('ProcessName')} ({c.get('memory_mb')} MB)" for c in candidates[:8])
                notes.append(f"Potentially idle user applications: {top}.")
            else:
                notes.append("No eligible high-memory or unresponsive user applications were identified.")

        if "stop steam" in lowered:
            match = next((p for p in self.processes.list_processes() if str(p.get("ProcessName", "")).casefold() == "steam"), None)
            if match:
                results.append(self.processes.stop(int(match.get("Id", 0)), "steam"))
            else:
                notes.append("Steam is not currently running.")

        if "steam" in lowered and any(x in lowered for x in ("startup", "start with windows", "launch at startup")):
            results.append(self.startup.disable("Steam"))

        if any(x in lowered for x in ("repair windows", "repair my pc", "fix my pc", "fix my computer")):
            results.append(self.repairs.system_file_repair(confirmed=confirmed))
            if not confirmed:
                notes.append("Windows file repair was not run because it is high-risk and requires explicit confirmation.")

        if "network" in lowered and any(x in lowered for x in ("reset", "repair", "fix")):
            results.append(self.repairs.network_reset(confirmed=confirmed))
            if not confirmed:
                notes.append("Network reset was not run because it is high-risk and requires explicit confirmation.")

        for result in results:
            self.audit.record(result.operation, result.target_id, verified=result.verified, rollback_available=result.rollback_available)
        message_parts = ([self._report_message(report)] if report else []) + notes
        message_parts.extend(f"{r.operation} on {r.target_id}: {'verified' if r.success and r.verified else 'not changed/failed'} — {r.detail or r.error or ''}".strip() for r in results)
        return MaintenanceResponse(text, report, tuple(results), "\n".join(message_parts) or "No maintenance operation matched this request.")

    @staticmethod
    def _report_message(report: DiagnosticReport) -> str:
        lines = [report.summary()]
        lines.extend(f"{f.severity}: {f.title} — {f.detail}" for f in report.findings[:8])
        if report.failures:
            lines.append(f"{len(report.failures)} health checks failed without aborting the remaining checks.")
        return "\n".join(lines)
