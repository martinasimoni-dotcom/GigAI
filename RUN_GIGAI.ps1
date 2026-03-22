param(
    [ValidateSet("all", "backend", "frontend")]
    [string]$Mode = "all",

    [int]$BackendPort = 8010,

    [int]$OrchestratorPort = 8011,

    [switch]$Reload,

    [switch]$StopExisting
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendPath = Join-Path $projectRoot "frontend"
$startApiScript = Join-Path $projectRoot "start-api.ps1"
$frontendUrl = "http://localhost:3000"
$dashboardApiUrl = "http://localhost:$BackendPort"
$orchestratorApiUrl = "http://localhost:$OrchestratorPort"

function Test-TcpPort {
    param(
        [string]$Host,
        [int]$Port
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($Host, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }

        $client.EndConnect($async)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Start-Backend {
    param(
        [string]$AppName,
        [int]$PortNumber
    )

    Write-Host "Starting $AppName API on http://127.0.0.1:$PortNumber ..." -ForegroundColor Cyan

    $args = @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$startApiScript`"",
        "-App", "$AppName",
        "-Port", "$PortNumber"
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

    if (Test-TcpPort -Host "127.0.0.1" -Port 3000) {
        Write-Host "Frontend already running on $frontendUrl. Opening existing dashboard ..." -ForegroundColor Yellow
        Start-Process $frontendUrl | Out-Null
        return
    }

    Write-Host "Starting frontend on $frontendUrl ..." -ForegroundColor Cyan

    $cmd = @(
        "Set-Location -Path `"$frontendPath`"",
        "if (-not (Test-Path node_modules)) { npm install }",
        "npm run dev"
    ) -join "; "

    Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd) -WorkingDirectory $frontendPath | Out-Null
    Start-Process -FilePath "powershell" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Start-Sleep -Seconds 6; Start-Process `"$frontendUrl`"") -WindowStyle Hidden | Out-Null
}

Write-Host ""
Write-Host "GigAI Main Launcher" -ForegroundColor Green
Write-Host "Mode: $Mode" -ForegroundColor Green
Write-Host ""

switch ($Mode) {
    "backend" {
        Start-Backend -AppName "dashboard" -PortNumber $BackendPort
        Start-Backend -AppName "orchestrator" -PortNumber $OrchestratorPort
    }
    "frontend" {
        Start-Frontend
    }
    default {
        Start-Backend -AppName "dashboard" -PortNumber $BackendPort
        Start-Backend -AppName "orchestrator" -PortNumber $OrchestratorPort
        Start-Sleep -Milliseconds 800
        Start-Frontend
    }
}

Write-Host ""
Write-Host "Started requested services." -ForegroundColor Green
if ($Mode -eq "all" -or $Mode -eq "backend") {
    Write-Host "Dashboard API:    $dashboardApiUrl/docs"
    Write-Host "Orchestrator API: $orchestratorApiUrl/docs"
}
if ($Mode -eq "all" -or $Mode -eq "frontend") {
    Write-Host "Frontend: $frontendUrl"
}
