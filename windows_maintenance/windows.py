from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


class WindowsMaintenanceUnavailable(RuntimeError):
    pass


def _require_windows() -> None:
    if os.name != "nt":
        raise WindowsMaintenanceUnavailable("Windows maintenance is only available on Windows")


def _ps(script: str, timeout: int = 30) -> Any:
    _require_windows()
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"PowerShell exited {completed.returncode}")
    value = completed.stdout.strip()
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def system_snapshot() -> dict[str, Any]:
    if os.name != "nt":
        return {"platform": sys.platform, "windows": False}
    checks = {
        "os": "Get-CimInstance Win32_OperatingSystem | Select Caption,Version,LastBootUpTime | ConvertTo-Json -Compress",
        "cpu": "Get-CimInstance Win32_Processor | Select Name,NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress",
        "memory": "Get-CimInstance Win32_OperatingSystem | Select TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress",
        "disks": "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select DeviceID,FreeSpace,Size,HealthStatus | ConvertTo-Json -Compress",
        "gpu": "Get-CimInstance Win32_VideoController | Select Name,DriverVersion,AdapterRAM,Status | ConvertTo-Json -Compress",
        "network": "Get-NetIPConfiguration | Select InterfaceAlias,IPv4Address,IPv6Address,DNSServer,NetProfile.Name | ConvertTo-Json -Compress",
        "updates": "Get-Service wuauserv,bits -ErrorAction SilentlyContinue | Select Name,Status,StartType | ConvertTo-Json -Compress",
        "devices": "Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where Status -ne 'OK' | Select FriendlyName,Class,Status,ProblemCode | ConvertTo-Json -Compress",
        "system_errors": "Get-WinEvent -FilterHashtable @{LogName='System';Level=2;StartTime=(Get-Date).AddDays(-3)} -MaxEvents 20 -ErrorAction SilentlyContinue | Select TimeCreated,ProviderName,Id,Message | ConvertTo-Json -Compress",
    }
    result: dict[str, Any] = {"platform": "windows", "windows": True}
    for name, script in checks.items():
        try:
            result[name] = _ps(script)
        except Exception as exc:
            result[name] = {"error": str(exc)}
    return result


def process_list() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    # Sample CPU twice, then correlate network ownership and GPU engine counters by PID.
    script = r"""
$first = Get-Process | Select-Object Id,ProcessName,Path,CPU,WorkingSet64,Responding,MainWindowHandle,MainWindowTitle
Start-Sleep -Milliseconds 500
$second = Get-Process | Select-Object Id,ProcessName,Path,CPU,WorkingSet64,Responding,MainWindowHandle,MainWindowTitle
$cpu = @{}
foreach($p in $second){
  $old = $first | Where-Object Id -eq $p.Id | Select-Object -First 1
  if($old -and $p.CPU -ne $null -and $old.CPU -ne $null){ $cpu[[int]$p.Id] = [math]::Round([math]::Max(0,(([double]$p.CPU-[double]$old.CPU)/0.5)/[Environment]::ProcessorCount*100),2) }
}
$net = @{}
Get-NetTCPConnection -ErrorAction SilentlyContinue | Group-Object OwningProcess | ForEach-Object { $net[[int]$_.Name] = $_.Count }
$gpu = @{}
try {
  (Get-Counter '\GPU Engine(*)\Utilization Percentage' -ErrorAction Stop).CounterSamples | ForEach-Object {
    if($_.InstanceName -match 'pid_(\d+)_'){ $pid=[int]$Matches[1]; if(-not $gpu.ContainsKey($pid)){$gpu[$pid]=0}; $gpu[$pid] += [double]$_.CookedValue }
  }
} catch {}
$second | ForEach-Object {
  $id=[int]$_.Id
  [pscustomobject]@{
    Id=$id; ProcessName=$_.ProcessName; Path=$_.Path; CPU=$_.CPU; CPUPercent=if($cpu.ContainsKey($id)){$cpu[$id]}else{0}; WorkingSet64=$_.WorkingSet64; Responding=$_.Responding; MainWindowHandle=$_.MainWindowHandle; MainWindowTitle=$_.MainWindowTitle; NetworkConnections=if($net.ContainsKey($id)){$net[$id]}else{0}; GPUPercent=if($gpu.ContainsKey($id)){$gpu[$id]}else{0}
  }
} | ConvertTo-Json -Compress
"""
    data = _ps(script, timeout=45)
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def foreground_pid() -> int | None:
    if os.name != "nt":
        return None
    script = "Add-Type @'\nusing System; using System.Runtime.InteropServices; public static class F { [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow(); [DllImport(\"user32.dll\")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint p); }\n'@; $p=0; [void][F]::GetWindowThreadProcessId([F]::GetForegroundWindow(), [ref]$p); $p"
    value = _ps(script)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def stop_process(pid: int, expected_name: str) -> tuple[bool, str]:
    _require_windows()
    if pid <= 0 or len(expected_name) > 128:
        return False, "invalid process identity"
    name = expected_name.replace("'", "''")
    script = f"$p=Get-Process -Id {int(pid)} -ErrorAction Stop; if($p.ProcessName -ne '{name}'){{throw 'process identity changed'}}; Stop-Process -Id {int(pid)} -Force -ErrorAction Stop; Start-Sleep -Milliseconds 500; [bool](Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue)"
    still_alive = bool(_ps(script, timeout=15))
    return (not still_alive), ("stopped and verified" if not still_alive else "process still exists after stop request")


def startup_entries() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    data = _ps("Get-CimInstance Win32_StartupCommand | Select Name,Command,Location,User | ConvertTo-Json -Compress")
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def disable_user_run_entry(name: str) -> dict[str, Any]:
    _require_windows()
    escaped = name.replace("'", "''")
    script = f"$key='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'; $p=Get-ItemProperty -Path $key -ErrorAction Stop; if(-not ($p.PSObject.Properties.Name -contains '{escaped}')){{throw 'startup entry not found'}}; $old=[string]$p.PSObject.Properties['{escaped}'].Value; Remove-ItemProperty -Path $key -Name '{escaped}' -ErrorAction Stop; [pscustomobject]@{{previous=$old;present=[bool](Get-ItemProperty -Path $key -Name '{escaped}' -ErrorAction SilentlyContinue)}} | ConvertTo-Json -Compress"
    value = _ps(script)
    if not isinstance(value, dict) or value.get("present"):
        raise RuntimeError("startup entry was not removed")
    return value


def restore_user_run_entry(name: str, previous: str) -> bool:
    _require_windows()
    if len(name) > 128 or len(previous) > 4096:
        raise ValueError("startup entry is too large")
    name_e = name.replace("'", "''")
    previous_e = previous.replace("'", "''")
    _ps(f"New-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name '{name_e}' -Value '{previous_e}' -PropertyType String -Force | Out-Null")
    return True


def run_system_file_check(repair: bool = False) -> tuple[bool, str]:
    _require_windows()
    commands = (
        [["DISM.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"], ["sfc.exe", "/scannow"]]
        if repair
        else [["DISM.exe", "/Online", "/Cleanup-Image", "/ScanHealth"], ["sfc.exe", "/verifyonly"]]
    )
    logs: list[str] = []
    for command in commands:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        logs.append(f"{' '.join(command)} -> {completed.returncode}")
        if completed.returncode != 0:
            return False, " ; ".join(logs)
    return True, " ; ".join(logs)


def reset_network() -> tuple[bool, str]:
    _require_windows()
    commands = [["ipconfig.exe", "/flushdns"], ["netsh.exe", "winsock", "reset"]]
    logs: list[str] = []
    for command in commands:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        logs.append(f"{' '.join(command)} -> {completed.returncode}")
        if completed.returncode != 0:
            return False, " ; ".join(logs)
    return True, " ; ".join(logs)
