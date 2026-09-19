$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Entry = Join-Path $Root 'scripts\jarvis_desktop.pyw'
$Output = Join-Path $Root 'dist\Jarvis.exe'
$Vendor = Join-Path $Root 'build_vendor'
$BuildInfo = Join-Path $Root 'quality_of_life\build_info.py'

$commit = (& git -C $Root rev-parse HEAD 2>$null).Trim()
if (-not $commit) { $commit = 'dev' }
Set-Content -LiteralPath $BuildInfo -Encoding UTF8 -Value @(
    '"""Build identity embedded into the frozen Jarvis executable."""'
    ('BUILD_COMMIT = "{0}"' -f $commit)
)

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Jarvis Python runtime is missing: $Python"
}
if (-not (Test-Path -LiteralPath $Entry)) {
    throw "Jarvis desktop entrypoint is missing: $Entry"
}

& $Python scripts/fetch-fullstack-components.py $Vendor
& $Python scripts/prepare_omniroute_runtime.py (Join-Path $Vendor 'omniroute_runtime')
& $Python -m pip install -r (Join-Path $Root 'quality_of_life\requirements.txt')
& $Python -m pip install pyinstaller faster-whisper kokoro pynput sounddevice soundfile webrtcvad-wheels numpy httpx
& $Python -m pip check

& $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name Jarvis --paths $Root --paths (Join-Path $Vendor 'backtalk\source') --add-data "$(Join-Path $Vendor 'ai-visualizer\source');ai-visualizer/source" --add-data "$(Join-Path $Vendor 'barehands\source');barehands/source" --add-data "$(Join-Path $Vendor 'ai-memory-vault\source');ai-memory-vault/source" --add-data "$(Join-Path $Vendor 'omniroute_runtime\runtime-manifest.txt');omniroute_runtime" --add-binary "$(Join-Path $Vendor 'omniroute_runtime\node.exe');omniroute_runtime" --add-data "$(Join-Path $Vendor 'omniroute_runtime\node_modules');omniroute_runtime/node_modules" --collect-submodules quality_of_life --collect-submodules self_coding --collect-submodules windows_maintenance --collect-submodules backtalk --collect-all faster_whisper --collect-all kokoro --collect-submodules webrtcvad --hidden-import sounddevice --hidden-import soundfile --hidden-import pynput $Entry

if (-not (Test-Path -LiteralPath $Output)) {
    throw "Jarvis.exe was not produced: $Output"
}
if ((Get-Item -LiteralPath $Output).Length -lt 5000000) {
    throw "Jarvis.exe is unexpectedly small; fullstack assets/dependencies may not be embedded"
}

Write-Host "Built $Output"
