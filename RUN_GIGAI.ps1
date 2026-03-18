param(
    [ValidateSet("all", "backend", "frontend")]
    [string]$Mode = "all",

    [int]$BackendPort = 8000,

    [switch]$Reload,

    [switch]$StopExisting
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendPath = Join-Path $projectRoot "frontend"
$startApiScript = Join-Path $projectRoot "start-api.ps1"

function Start-Backend {
    Write-Host "Starting backend on http://127.0.0.1:$BackendPort ..." -ForegroundColor Cyan

    $args = @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$startApiScript`"",
        "-App", "dashboard",
        "-Port", "$BackendPort"
    )

    if ($Reload) {
        $args += "-Reload"
    }

    if ($StopExisting) {
        $args += "-StopExisting"
    }

    Start-Process -FilePath "powershell" -ArgumentList $args -WorkingDirectory $projectRoot | Out-Null
}

function Start-Frontend {
    if (-not (Test-Path $frontendPath)) {
        throw "Frontend folder not found: $frontendPath"
    }

    Write-Host "Starting frontend on http://localhost:3000 ..." -ForegroundColor Cyan

    $cmd = @(
        "Set-Location -Path `"$frontendPath`"",
        "if (-not (Test-Path node_modules)) { npm install }",
        "npm run dev"
    ) -join "; "

    Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd) -WorkingDirectory $frontendPath | Out-Null
}

Write-Host ""
Write-Host "GigAI Main Launcher" -ForegroundColor Green
Write-Host "Mode: $Mode" -ForegroundColor Green
Write-Host ""

switch ($Mode) {
    "backend" {
        Start-Backend
    }
    "frontend" {
        Start-Frontend
    }
    default {
        Start-Backend
        Start-Sleep -Milliseconds 800
        Start-Frontend
    }
}

Write-Host ""
Write-Host "Started requested services." -ForegroundColor Green
if ($Mode -eq "all" -or $Mode -eq "backend") {
    Write-Host "Backend:  http://localhost:$BackendPort/docs"
}
if ($Mode -eq "all" -or $Mode -eq "frontend") {
    Write-Host "Frontend: http://localhost:3000"
}