$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Exe = Join-Path $Root 'dist\Jarvis.exe'

if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Jarvis.exe is missing: $Exe. Build it with scripts\build-jarvis-exe.ps1 or use the verified GitHub Release Jarvis.exe."
}

Start-Process -FilePath $Exe -WorkingDirectory $Root
