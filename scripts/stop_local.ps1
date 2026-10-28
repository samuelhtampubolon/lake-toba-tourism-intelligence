# PowerShell Targeted Process Stopper
$ErrorActionPreference = "SilentlyContinue"

$PidFile = "data\server.pid"
if (-not (Test-Path $PidFile)) {
    Write-Host "[!] No data\server.pid file found. Process may not be running." -ForegroundColor Yellow
    exit 0
}

$ProcessId = (Get-Content $PidFile).Trim()
if ($ProcessId) {
    $Proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Proc) {
        Write-Host "[*] Stopping Lake Toba server process (PID: $ProcessId)..." -ForegroundColor Yellow
        Stop-Process -Id $ProcessId -Force
        Write-Host "[+] Server process stopped successfully." -ForegroundColor Green
    } else {
        Write-Host "[!] Process $ProcessId is no longer running." -ForegroundColor Gray
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}
