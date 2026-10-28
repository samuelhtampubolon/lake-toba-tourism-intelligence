# PowerShell Local Startup Script (Loopback 127.0.0.1)
param (
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$HostIP = "127.0.0.1"

$VenvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found. Please run .\scripts\setup.ps1 first."
    exit 1
}

# Check if port is occupied
$Occupied = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($Occupied) {
    Write-Error "Port $Port is already occupied by PID $($Occupied.OwningProcess). Specify an alternate port using: .\scripts\run_local.ps1 -Port 8080"
    exit 1
}

New-Item -ItemType Directory -Force -Path "data" | Out-Null

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Lake Toba Tourism Intelligence Local Server" -ForegroundColor Green
Write-Host " Bound URL:    http://${HostIP}:${Port}" -ForegroundColor White
Write-Host " Environment:  Local Development (Loopback Only)" -ForegroundColor Yellow
Write-Host " Database:     data/lake_toba.sqlite" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

# Start process and record PID for targeted termination
$Process = Start-Process -FilePath $VenvPython -ArgumentList "-m uvicorn app.main:app --host $HostIP --port $Port" -PassThru
$Process.Id | Out-File "data\server.pid" -Force

Write-Host "[+] Server started successfully with PID: $($Process.Id)" -ForegroundColor Green
Write-Host "[+] Target stop script: .\scripts\stop_local.ps1" -ForegroundColor Gray
