param(
    [string]$BindAddress = "127.0.0.1",
    [int]$Port = 8010,
    [switch]$Reload,
    [switch]$StopExisting,
    [switch]$DisableAutoPortFallback,
    [ValidateSet("dashboard", "orchestrator")]
    [string]$App = "dashboard"
)

function Test-PortBindable {
    param(
        [string]$Address,
        [int]$PortNumber
    )

    try {
        $ipAddress = [System.Net.IPAddress]::Parse($Address)
    } catch {
        return $false
    }

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new($ipAddress, $PortNumber)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            try { $listener.Stop() } catch { }
        }
    }
}

function Get-PortOwnerPids {
    param(
        [string]$Address,
        [int]$PortNumber
    )

    $ownerPids = @()

    $listeners = Get-NetTCPConnection -LocalPort $PortNumber -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        $matchingListeners = @()
        foreach ($listener in $listeners) {
            if (
                $listener.LocalAddress -eq $Address -or
                $listener.LocalAddress -eq "0.0.0.0" -or
                $listener.LocalAddress -eq "::" -or
                ($Address -eq "127.0.0.1" -and $listener.LocalAddress -eq "::1")
            ) {
                $matchingListeners += $listener
            }
        }

        if ($matchingListeners.Count -gt 0) {
            $ownerPids = @($matchingListeners | Select-Object -ExpandProperty OwningProcess -Unique)
        }
    }

    if ($ownerPids.Count -eq 0) {
        # Fallback: parse netstat output for environments where Get-NetTCPConnection
        # misses a listener but the port is still not bindable.
        $netstatLines = netstat -ano -p tcp | Select-String -Pattern (":$PortNumber\s")
        foreach ($line in $netstatLines) {
            $text = ($line.ToString()).Trim()
            if ($text -notmatch "LISTENING") {
                continue
            }

            $parts = $text -split "\s+"
            if ($parts.Count -lt 5) {
                continue
            }

            $localEndpoint = $parts[1]
            $pidCandidate = $parts[-1]

            if ($localEndpoint -notmatch ":$PortNumber$") {
                continue
            }

            if (
                $localEndpoint -like "$Address`:$PortNumber" -or
                $localEndpoint -like "0.0.0.0`:$PortNumber" -or
                $localEndpoint -like "[::]:$PortNumber" -or
                ($Address -eq "127.0.0.1" -and $localEndpoint -like "[::1]:$PortNumber")
            ) {
                if ($pidCandidate -match "^\d+$") {
                    $ownerPids += [int]$pidCandidate
                }
            }
        }

        if ($ownerPids.Count -gt 0) {
            $ownerPids = @($ownerPids | Select-Object -Unique)
        }
    }

    return $ownerPids
}

function Get-NextBindablePort {
    param(
        [string]$Address,
        [int]$StartPort,
        [int]$MaxAttempts = 20
    )

    for ($offset = 1; $offset -le $MaxAttempts; $offset++) {
        $candidate = $StartPort + $offset
        if (Test-PortBindable -Address $Address -PortNumber $candidate) {
            return $candidate
        }
    }

    return $null
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

$pythonExe = $env:GIGAI_PYTHON
if ([string]::IsNullOrWhiteSpace($pythonExe)) {
    if (Test-Path $venvPython) {
        $pythonExe = $venvPython
    } else {
        $pythonExe = "python"
    }
}

$target = if ($App -eq "orchestrator") { "gigai.main:app" } else { "gigai.dashboard.dashboard_api:create_dashboard_app" }
$argsList = @("-m", "uvicorn", $target)

if ($App -eq "dashboard") {
    $argsList += "--factory"
}

if ($App -eq "dashboard" -or $App -eq "orchestrator") {
    $argsList += @("--app-dir", "src")
}

$effectivePort = $Port

if ($Reload) {
    $argsList += "--reload"
}

Push-Location $projectRoot
try {
    $isBindable = Test-PortBindable -Address $BindAddress -PortNumber $effectivePort
    if (-not $isBindable) {
        $ownerPids = @(Get-PortOwnerPids -Address $BindAddress -PortNumber $effectivePort)

        if ($StopExisting -and $ownerPids.Count -gt 0) {
            foreach ($ownerPid in $ownerPids) {
                Write-Host "Port $effectivePort is in use by PID $ownerPid. Stopping it because -StopExisting was provided."
                try {
                    Stop-Process -Id $ownerPid -Force -ErrorAction Stop
                    Start-Sleep -Milliseconds 300
                } catch {
                    Write-Warning "Unable to stop PID $ownerPid ($($_.Exception.Message)). Will re-check port availability."
                }
            }

            $isBindable = Test-PortBindable -Address $BindAddress -PortNumber $effectivePort
        }

        if (-not $isBindable) {
            if (-not $DisableAutoPortFallback) {
                $fallbackPort = Get-NextBindablePort -Address $BindAddress -StartPort $effectivePort
                if ($null -ne $fallbackPort) {
                    Write-Warning "Port $effectivePort is unavailable. Falling back to available port $fallbackPort."
                    $effectivePort = $fallbackPort
                    $isBindable = $true
                }
            }

            if (-not $isBindable) {
                if ($ownerPids.Count -gt 0) {
                    $pidText = ($ownerPids -join ", ")
                    Write-Error (
                        "Port $effectivePort is already in use by PID(s) $pidText. " +
                        "Use -StopExisting to stop that process, or choose another port (for example -Port 8011)."
                    )
                } else {
                    Write-Error (
                        "Port $effectivePort is not bindable on $BindAddress, but no owning process could be resolved. " +
                        "Try another port (for example -Port 8011) or run terminal as Administrator."
                    )
                }
                exit 1
            } else {
                Write-Host "Port check resolved. Continuing startup on $BindAddress`:$effectivePort."
            }
        }
    }

    $argsList += @("--host", $BindAddress, "--port", "$effectivePort")

    Write-Host "Starting GigAI $App API at http://$BindAddress`:$effectivePort using $pythonExe"
    & $pythonExe @argsList
}
finally {
    Pop-Location
}
