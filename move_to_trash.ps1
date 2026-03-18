param(
    [Parameter(Mandatory = $true, Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Targets,

    [string]$Reason = ""
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$scriptPath = Join-Path $repoRoot "trash_manager.py"

if (-not (Test-Path $scriptPath)) {
    throw "trash_manager.py not found at $scriptPath"
}

if ($Targets.Count -eq 1 -and $Targets[0].Contains(",")) {
    $Targets = $Targets[0].Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}

if (Test-Path $pythonExe) {
    & $pythonExe $scriptPath move @Targets --reason $Reason
    exit $LASTEXITCODE
}

python $scriptPath move @Targets --reason $Reason
exit $LASTEXITCODE
