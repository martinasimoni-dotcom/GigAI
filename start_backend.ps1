Write-Host "============================================" -ForegroundColor Cyan
Write-Host " GIGAI Backend Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "[1/3] Killing any process on port 8000..." -ForegroundColor Yellow
$pids = netstat -aon | Select-String ":8000 " | ForEach-Object {
    ($_ -split '\s+')[-1]
} | Sort-Object -Unique
foreach ($p in $pids) {
    if ($p -match '^\d+$' -and $p -ne '0') {
        Write-Host "  Killing PID $p" -ForegroundColor Red
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2

Write-Host "[2/3] Activating virtual environment..." -ForegroundColor Yellow
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

Write-Host "[3/3] Starting backend on port 8000 (no reload)..." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Set-Location "$PSScriptRoot\backend"
python -u main.py
