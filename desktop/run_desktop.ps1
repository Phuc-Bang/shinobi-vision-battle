$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = $root
$env:SDL_VIDEO_CENTERED = "1"

$venvPython = ".\desktop\.venv\Scripts\python.exe"
if (!(Test-Path $venvPython)) {
    Write-Host "Creating desktop virtual environment..."
    python -m venv ".\desktop\.venv"
}

$pythonExe = $venvPython

$requiredAssets = @(
    ".\frontend\assets\images\background\arena.png",
    ".\frontend\assets\images\sprites\naruto\idle.png",
    ".\frontend\assets\images\sprites\mizuki\idle.png",
    ".\frontend\assets\images\ui\skill_rasengan.png"
)

$missing = $requiredAssets | Where-Object { -not (Test-Path $_) }
if ($missing.Count -gt 0) {
    Write-Host "Missing required assets:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    throw "Assets not found. Please verify project files."
}

& $pythonExe -c "import cv2, mediapipe, numpy, pygame, absl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing desktop dependencies..."
    & $pythonExe -m pip install -r ".\desktop\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install desktop dependencies."
    }
}

& $pythonExe ".\desktop\main.py"
