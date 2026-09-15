"""Optional, guarded Windows maintenance capability layer."""

from .diagnostics import DiagnosticCollector
from .facade import MaintenanceFacade, MaintenanceResponse, is_maintenance_request
from .models import DiagnosticFinding, DiagnosticReport, MaintenanceAction, OperationResult, RiskClass
from .policy import MaintenancePolicy
from .processes import ProcessManager
from .repairs import RepairManager
from .startup import StartupManager

__all__ = [
    "DiagnosticCollector", "MaintenanceFacade", "MaintenanceResponse", "MaintenancePolicy",
    "DiagnosticFinding", "DiagnosticReport", "MaintenanceAction", "OperationResult", "RiskClass",
    "ProcessManager", "RepairManager", "StartupManager", "is_maintenance_request",
]
