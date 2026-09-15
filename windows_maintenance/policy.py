from __future__ import annotations

from dataclasses import dataclass
from .models import MaintenanceAction, PolicyDecision, RiskClass


PROTECTED_PROCESS_NAMES = frozenset({
    "system", "system idle process", "registry", "smss", "csrss", "wininit", "services",
    "lsass", "winlogon", "svchost", "fontdrvhost", "dwm", "explorer", "securityhealthservice",
    "msmpeng", "antimalware service executable", "searchindexer", "sihost", "ctfmon",
})
PROTECTED_NAME_MARKERS = ("jarvis", "fullstack-agent", "claude", "powershell", "cmd", "conhost")
PROTECTED_PATH_MARKERS = ("\\windows\\system32\\", "\\windows\\syswow64\\", "\\windows\\winsxs\\")


@dataclass(frozen=True)
class MaintenancePolicy:
    allow_low_risk: bool = True
    allow_medium_risk: bool = True
    allow_high_risk: bool = False

    def evaluate(self, action: MaintenanceAction, explicit_user_request: bool, confirmed: bool = False) -> PolicyDecision:
        if action.risk is RiskClass.READ_ONLY:
            return PolicyDecision(True, "read-only")
        if not explicit_user_request:
            return PolicyDecision(False, "mutation requires explicit user intent")
        if action.risk is RiskClass.REVERSIBLE_LOW_RISK and self.allow_low_risk:
            return PolicyDecision(True, "low-risk action authorized")
        if action.risk is RiskClass.REVERSIBLE_MEDIUM_RISK and self.allow_medium_risk:
            return PolicyDecision(True, "medium-risk action authorized")
        if action.risk is RiskClass.HIGH_RISK:
            if not self.allow_high_risk:
                return PolicyDecision(False, "high-risk action is disabled by default", True)
            if not confirmed:
                return PolicyDecision(False, "high-risk action requires explicit confirmation", True)
            return PolicyDecision(True, "high-risk action explicitly confirmed")
        return PolicyDecision(False, "operation denied by maintenance policy")

    @staticmethod
    def is_protected_process(name: str, path: str | None = None) -> bool:
        normalized = (name or "").casefold()
        path_value = (path or "").replace("/", "\\").casefold()
        if normalized in PROTECTED_PROCESS_NAMES:
            return True
        if any(marker in normalized for marker in PROTECTED_NAME_MARKERS):
            return True
        return any(marker in path_value for marker in PROTECTED_PATH_MARKERS)

    @staticmethod
    def startup_source_allowed(source: str) -> bool:
        return source == "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
