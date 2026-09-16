$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Entry = Join-Path $Root 'scripts\jarvis_desktop.pyw'
$Output = Join-Path $Root 'dist\Jarvis.exe'

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Jarvis Python runtime is missing: $Python"
}
if (-not (Test-Path -LiteralPath $Entry)) {
    throw "Jarvis desktop entrypoint is missing: $Entry"
}

& $Python -m pip install -r (Join-Path $Root 'quality_of_life\requirements.txt')
& $Python -m pip install pyinstaller
& $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name Jarvis --paths $Root --collect-submodules quality_of_life --collect-submodules self_coding --collect-submodules windows_maintenance $Entry

if (-not (Test-Path -LiteralPath $Output)) {
    throw "Jarvis.exe was not produced: $Output"
}

Write-Host "Built $Output"
