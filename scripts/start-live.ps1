$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install requirements.txt first. See README.md.'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) {
    throw 'Build the dashboard first: cd frontend; npm ci; npm run build'
}
$env:WIFI_SENSING_SOURCE = 'native_rssi'
$env:SIMULATION_MODE = 'false'
$env:WIFI_SENSING_HOST = '127.0.0.1'
$env:WIFI_SENSING_ALERTS = '1'
$env:WIFI_SENSING_LOCK_CALIBRATION = '1'
$env:WIFI_SENSING_ENGINE_VERSION = 'v2'
Write-Host 'WiFi Sensing live hardware: http://127.0.0.1:8000'
Write-Host 'Keep the room quiet for the initial 20-second calibration.'
& $pythonPath -B server.py
