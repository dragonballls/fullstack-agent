$ErrorActionPreference = 'Stop'

Add-Type @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class JarvisWindowProbe {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int width, int height, bool repaint);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    public const int SW_MINIMIZE = 6;
    public const int SW_RESTORE = 9;
    public const uint WM_CLOSE = 0x0010;

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }

    public sealed class WindowInfo {
        public IntPtr Handle;
        public uint ProcessId;
        public string Title = "";
        public string ClassName = "";
        public bool Visible;
        public RECT Rect;
    }

    public static List<WindowInfo> ForProcess(uint pid) {
        var result = new List<WindowInfo>();
        EnumWindows((hWnd, _) => {
            uint owner;
            GetWindowThreadProcessId(hWnd, out owner);
            if (owner != pid) return true;
            var title = new StringBuilder(512);
            var cls = new StringBuilder(256);
            GetWindowText(hWnd, title, title.Capacity);
            GetClassName(hWnd, cls, cls.Capacity);
            RECT rect;
            GetWindowRect(hWnd, out rect);
            result.Add(new WindowInfo { Handle = hWnd, ProcessId = owner, Title = title.ToString(), ClassName = cls.ToString(), Visible = IsWindowVisible(hWnd), Rect = rect });
            return true;
        }, IntPtr.Zero);
        return result;
    }
}
'@

$env:JARVIS_DISABLE_VOICE = '1'
$env:JARVIS_ENABLE_HANDS = '0'
$env:JARVIS_AUTO_UPDATE = '0'
$env:JARVIS_UI_SMOKE = '1'
Remove-Item Env:JARVIS_SMOKE -ErrorAction SilentlyContinue
Remove-Item Env:JARVIS_SMOKE_VOICE -ErrorAction SilentlyContinue
Remove-Item Env:JARVIS_SMOKE_WEBVIEW -ErrorAction SilentlyContinue

$headlessCi = ($env:GITHUB_ACTIONS -eq 'true') -and ($env:JARVIS_ALLOW_HEADLESS_GUI -eq '1')
$process = $null
$window = $null
try {
    $log = Join-Path $env:LOCALAPPDATA 'Jarvis\logs\desktop.log'
    if (Test-Path -LiteralPath $log) {
        Remove-Item -LiteralPath $log -Force -ErrorAction SilentlyContinue
    }
    $process = Start-Process -FilePath 'dist/Jarvis.exe' -PassThru -WorkingDirectory (Resolve-Path '.')
    Write-Host ("Jarvis.exe started. PID={0}" -f $process.Id)

    if ($headlessCi) {
        # GitHub-hosted Windows jobs do not provide an interactive user desktop,
        # so user32 cannot expose a trustworthy visible HWND there. Instead,
        # verify the real frozen EXE stays alive, reaches create_window(), and
        # remains healthy long enough to prove the native host path initialized.
        $log = Join-Path $env:LOCALAPPDATA 'Jarvis\logs\desktop.log'
        $deadline = (Get-Date).AddSeconds(45)
        $created = $false
        while ((Get-Date) -lt $deadline) {
            if ($process.HasExited) {
                throw "Jarvis.exe exited before native host initialization completed with code $($process.ExitCode)"
            }
            if (Test-Path -LiteralPath $log) {
                $contents = Get-Content -LiteralPath $log -Raw
                if ($contents -match 'headless frozen Jarvis native window object created;') {
                    $created = $true
                    break
                }
            }
            Start-Sleep -Milliseconds 500
        }
        if (-not $created) {
            throw 'Frozen Jarvis.exe did not reach real pywebview native-window object creation within 45 seconds'
        }
        if ($process.HasExited) {
            throw "Jarvis.exe exited after native window-object creation with code $($process.ExitCode)"
        }
        $floatingMarker = 'floating command bar window object created; pid=\d+ hotkey=' + [regex]::Escape('Ctrl+Alt+Shift+F12')
        if ($contents -notmatch $floatingMarker) {
            throw 'Frozen Jarvis.exe did not create the floating command bar window object'
        }
        Write-Host 'Headless hosted-runner GUI smoke passed: frozen EXE validated the production native-window contract and created the floating command bar window.'
        return
    }

    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) {
            throw "Jarvis.exe exited before native GUI became ready with code $($process.ExitCode)"
        }
        $windows = [JarvisWindowProbe]::ForProcess([uint32]$process.Id)
        $window = $windows | Where-Object { $_.Visible -and $_.Title -eq 'Jarvis' } | Select-Object -First 1
        if ($null -ne $window) { break }
        Start-Sleep -Milliseconds 500
    }
    if ($null -eq $window) {
        $seen = [JarvisWindowProbe]::ForProcess([uint32]$process.Id) | ForEach-Object { "title='$($_.Title)' class='$($_.ClassName)' visible=$($_.Visible) rect=$($_.Rect.Left),$($_.Rect.Top),$($_.Rect.Right),$($_.Rect.Bottom)" }
        throw "The packaged EXE never created a visible native window titled 'Jarvis'. Windows seen: $($seen -join '; ')"
    }

    if ($window.ClassName -eq 'ConsoleWindowClass') {
        throw 'Jarvis GUI test found a console window instead of the application window'
    }

    $rect = $window.Rect
    $initialWidth = $rect.Right - $rect.Left
    $initialHeight = $rect.Bottom - $rect.Top
    if ($initialWidth -lt 400 -or $initialHeight -lt 300) {
        throw "Jarvis native window is unexpectedly small: ${initialWidth}x${initialHeight}"
    }

    Write-Host ("Native window found: handle={0} title='{1}' class='{2}' size={3}x{4}" -f $window.Handle, $window.Title, $window.ClassName, $initialWidth, $initialHeight)

    if (-not [JarvisWindowProbe]::MoveWindow($window.Handle, 120, 120, 1000, 700, $true)) {
        throw 'MoveWindow failed'
    }
    Start-Sleep -Milliseconds 500
    $afterMove = [JarvisWindowProbe]::ForProcess([uint32]$process.Id) | Where-Object { $_.Handle -eq $window.Handle } | Select-Object -First 1
    if ($null -eq $afterMove) { throw 'Jarvis window disappeared after move' }
    $movedWidth = $afterMove.Rect.Right - $afterMove.Rect.Left
    $movedHeight = $afterMove.Rect.Bottom - $afterMove.Rect.Top
    if ([math]::Abs($afterMove.Rect.Left - 120) -gt 20 -or [math]::Abs($afterMove.Rect.Top - 120) -gt 20) {
        throw "Jarvis window did not move to the requested position; actual=$($afterMove.Rect.Left),$($afterMove.Rect.Top)"
    }
    if ($movedWidth -lt 900 -or $movedHeight -lt 600) {
        throw "Jarvis window did not retain usable size after move: ${movedWidth}x${movedHeight}"
    }

    [void][JarvisWindowProbe]::ShowWindow($window.Handle, [JarvisWindowProbe]::SW_MINIMIZE)
    Start-Sleep -Milliseconds 500
    $minimized = [JarvisWindowProbe]::ForProcess([uint32]$process.Id) | Where-Object { $_.Handle -eq $window.Handle } | Select-Object -First 1
    if ($null -eq $minimized) { throw 'Jarvis window disappeared after minimize' }
    if ($minimized.Visible) { throw 'Jarvis native window did not minimize' }

    [void][JarvisWindowProbe]::ShowWindow($window.Handle, [JarvisWindowProbe]::SW_RESTORE)
    Start-Sleep -Milliseconds 500
    $restored = [JarvisWindowProbe]::ForProcess([uint32]$process.Id) | Where-Object { $_.Handle -eq $window.Handle } | Select-Object -First 1
    if ($null -eq $restored -or -not $restored.Visible) { throw 'Jarvis native window did not restore' }

    Write-Host 'Jarvis native GUI interaction checks passed: create, visible, move, resize, minimize, restore.'

    [void][JarvisWindowProbe]::SendMessage($window.Handle, [JarvisWindowProbe]::WM_CLOSE, [IntPtr]::Zero, [IntPtr]::Zero)
    $exitDeadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $exitDeadline) {
        if ($process.HasExited) { break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $process.HasExited) {
        throw 'Jarvis.exe did not exit after a native window close request'
    }
    if ($process.ExitCode -ne 0) {
        throw "Jarvis.exe exited after clean GUI close with code $($process.ExitCode)"
    }
    Write-Host 'Jarvis native GUI close and process shutdown passed.'
}
catch {
    Write-Host '=== Native GUI smoke diagnostics ==='
    if ($null -ne $process) {
        Write-Host ("PID={0} HasExited={1} ExitCode={2}" -f $process.Id, $process.HasExited, $process.ExitCode)
        try {
            [JarvisWindowProbe]::ForProcess([uint32]$process.Id) | ForEach-Object {
                Write-Host ("Window handle={0} title='{1}' class='{2}' visible={3} rect={4},{5},{6},{7}" -f $_.Handle, $_.Title, $_.ClassName, $_.Visible, $_.Rect.Left, $_.Rect.Top, $_.Rect.Right, $_.Rect.Bottom)
            }
        } catch { Write-Host "Window enumeration failed: $($_.Exception.Message)" }
    }
    $log = Join-Path $env:LOCALAPPDATA 'Jarvis\logs\desktop.log'
    if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Raw | Write-Host } else { Write-Host ("Log not found: {0}" -f $log) }
    throw
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}
