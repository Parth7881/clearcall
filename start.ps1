param([int]$Port = 8000, [string]$DataDir = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($DataDir) { $env:CLEARCALL_DATA_DIR = $DataDir }
$pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
    else { throw 'Install Python 3.10 or newer, then run start.ps1 again.' }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $pythonExe -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your internet connection and try again.' }
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
    throw 'The built frontend is missing. Run npm ci and npm run build in the frontend folder.'
}
Write-Host "Clearcall is ready at http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host 'Open that address in your browser. Press Ctrl+C here to stop.'
& $pythonExe -m uvicorn app.main:create_app --factory --app-dir backend --host 127.0.0.1 --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Server stopped with an error. If the port is busy, run ./start.ps1 -Port 8001.' }
