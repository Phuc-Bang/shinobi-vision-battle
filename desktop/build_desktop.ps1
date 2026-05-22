$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPython = ".\desktop\.venv\Scripts\python.exe"
if (!(Test-Path $venvPython)) {
    Write-Host "Creating desktop virtual environment..."
    python -m venv ".\desktop\.venv"
}

$pythonExe = $venvPython

Write-Host "Using Python: $pythonExe"
& $pythonExe -m pip install -r ".\desktop\requirements.txt"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install desktop dependencies."
}

Write-Host "Building ShinobiVisionBattle desktop app..."
& $pythonExe -m PyInstaller ".\desktop\shinobi_desktop.spec" --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$exePath = Join-Path $root "dist\ShinobiVisionBattle\ShinobiVisionBattle.exe"
if (!(Test-Path $exePath)) {
    throw "Build finished but exe was not found: $exePath"
}

Write-Host "Build complete: $exePath"
