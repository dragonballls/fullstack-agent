$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonW = Join-Path $Root '.venv\Scripts\pythonw.exe'
$Entry = Join-Path $Root 'scripts\jarvis_desktop.pyw'

if (-not (Test-Path -LiteralPath $PythonW)) {
    throw "Jarvis Python runtime is missing: $PythonW"
}
if (-not (Test-Path -LiteralPath $Entry)) {
    throw "Jarvis desktop launcher is missing: $Entry"
}

Start-Process -FilePath $PythonW -ArgumentList @($Entry) -WorkingDirectory $Root
