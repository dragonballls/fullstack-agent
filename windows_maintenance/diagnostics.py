from __future__ import annotations

from . import windows
from .models import DiagnosticFinding, DiagnosticReport


class DiagnosticCollector:
    """Collect broad Windows health signals without letting one failure abort the scan."""

    def collect(self) -> DiagnosticReport:
        if not windows.os.name == "nt":
            return DiagnosticReport((DiagnosticFinding("platform", "info", "Windows maintenance unavailable", "This capability activates on Windows hosts."),), (), 1)
        snapshot = windows.system_snapshot()
        findings: list[DiagnosticFinding] = []
        failures: list[str] = []
        completed = 0
        for category, value in snapshot.items():
            if category in {"platform", "windows"}:
                continue
            completed += 1
            if isinstance(value, dict) and "error" in value:
                failures.append(f"{category}: {value['error']}")
                continue
            if category == "cpu" and isinstance(value, dict) and isinstance(value.get("LoadPercentage"), int):
                load = value["LoadPercentage"]
                if load >= 90:
                    findings.append(DiagnosticFinding("cpu", "high", "CPU load is very high", f"Current reported CPU load is {load}%.", data=value))
            if category == "memory" and isinstance(value, dict):
                total = int(value.get("TotalVisibleMemorySize") or 0)
                free = int(value.get("FreePhysicalMemory") or 0)
                if total and (1 - free / total) >= 0.90:
                    findings.append(DiagnosticFinding("memory", "high", "Memory pressure is high", f"About {(1-free/total)*100:.0f}% of physical memory is in use.", data=value))
            if category == "disks":
                rows = value if isinstance(value, list) else [value]
                for row in rows:
                    if isinstance(row, dict) and row.get("Size") and row.get("FreeSpace") is not None:
                        free_ratio = float(row["FreeSpace"]) / float(row["Size"])
                        if free_ratio < 0.10:
                            findings.append(DiagnosticFinding("disk", "high", f"Low disk space on {row.get('DeviceID', 'drive')}", f"Only about {free_ratio*100:.0f}% free.", data=row))
            if category == "devices" and value:
                count = len(value) if isinstance(value, list) else 1
                findings.append(DiagnosticFinding("device", "medium", "Device Manager reports problem devices", f"{count} present device(s) report a non-OK status.", data={"count": count, "devices": value}))
            if category == "system_errors" and value:
                count = len(value) if isinstance(value, list) else 1
                findings.append(DiagnosticFinding("events", "medium", "Recent System errors were found", f"Found {count} recent error event(s) in the System log.", data={"events": value}))
        return DiagnosticReport(tuple(findings), tuple(failures), completed)
