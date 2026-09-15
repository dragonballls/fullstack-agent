from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    REVERSIBLE_LOW_RISK = "REVERSIBLE_LOW_RISK"
    REVERSIBLE_MEDIUM_RISK = "REVERSIBLE_MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"


@dataclass(frozen=True)
class MaintenanceAction:
    operation: str
    target_id: str
    arguments: dict[str, Any] = field(default_factory=dict)
    risk: RiskClass = RiskClass.READ_ONLY
    reason: str = ""


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_confirmation: bool = False


@dataclass(frozen=True)
class DiagnosticFinding:
    category: str
    severity: str
    title: str
    detail: str
    confidence: str = "observed"
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationResult:
    operation: str
    target_id: str
    success: bool
    changed: bool = False
    verified: bool = False
    rollback_available: bool = False
    error: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class MaintenanceRecord:
    correlation_id: str
    operation: str
    target_id: str
    previous_state: dict[str, Any] = field(default_factory=dict)
    resulting_state: dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    rollback_available: bool = False


@dataclass(frozen=True)
class DiagnosticReport:
    findings: tuple[DiagnosticFinding, ...] = ()
    failures: tuple[str, ...] = ()
    completed_checks: int = 0

    def summary(self) -> str:
        if not self.findings and not self.failures:
            return f"Completed {self.completed_checks} Windows health checks with no findings."
        return f"Collected {len(self.findings)} findings across {self.completed_checks} completed Windows health checks."
