# Lake Toba Tourism Intelligence - PowerShell Setup Script
$ErrorActionPreference = "Stop"

Write-Host "=== Lake Toba Tourism Intelligence Setup ===" -ForegroundColor Cyan

# 1. Verify Python
$PythonExe = (Get-Command py -ErrorAction SilentlyContinue)
if (-not $PythonExe) {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue)
}
if (-not $PythonExe) {
    Write-Error "Python was not found. Please install Python 3.12 or 3.13."
    exit 1
}

Write-Host "[*] Found Python: $PythonExe" -ForegroundColor Green

# 2. Virtual Environment
if (-not (Test-Path ".venv")) {
    Write-Host "[*] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    py -3.13 -m venv .venv
}

$VenvPython = ".\.venv\Scripts\python.exe"

# 3. Dependencies
Write-Host "[*] Installing verified dependencies from requirements.txt..." -ForegroundColor Yellow
& $VenvPython -m pip install -r requirements.txt

# 4. Initialize Database & Seed Baseline Destinations
Write-Host "[*] Initializing SQLite database schema and destinations..." -ForegroundColor Yellow
& $VenvPython -c "from app.database import init_db, SessionLocal; from app.services.demo_data_service import seed_destinations_and_segments; init_db(); db = SessionLocal(); seed_destinations_and_segments(db); db.close(); print('[+] Database initialized successfully.')"

Write-Host "`n[SUCCESS] Setup complete!" -ForegroundColor Green
Write-Host "Next step: Run administrator bootstrap command:" -ForegroundColor Cyan
Write-Host "    .\.venv\Scripts\python.exe scripts\cli.py bootstrap-admin" -ForegroundColor White
Write-Host "Then start the local server:" -ForegroundColor Cyan
Write-Host "    .\scripts\run_local.ps1" -ForegroundColor White
