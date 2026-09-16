$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Exe = Join-Path $Root 'dist\Jarvis.exe'

if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Jarvis.exe is missing: $Exe. Download the verified Jarvis-Windows artifact or build it with scripts\build-jarvis-exe.ps1."
}

Start-Process -FilePath $Exe -WorkingDirectory $Root
