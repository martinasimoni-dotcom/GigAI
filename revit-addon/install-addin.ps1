param(
    [string]$RevitVersion = "2024",
    [string]$Configuration = "Debug",
    [string]$TargetFramework = "net48",
    [switch]$ConfigureUserEnvironment,
    [string]$ApiUrl = "http://127.0.0.1:8011",
    [string]$ProjectId = "project_alpha",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

$projectDir = Join-Path $PSScriptRoot "GigAi.RevitAddin"
$dllSource = Join-Path $projectDir "bin\$Configuration\$TargetFramework\GigAi.RevitAddin.dll"
$templatePath = Join-Path $projectDir "GigAi.RevitAddin.addin.template"
$resolvedProjectRoot = if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    Split-Path -Parent $PSScriptRoot
} else {
    $ProjectRoot
}

if (-not (Test-Path $dllSource)) {
    throw "Build output not found: $dllSource. Build the project first."
}

if (-not (Test-Path $templatePath)) {
    throw "Manifest template not found: $templatePath"
}

$addinDir = Join-Path $env:APPDATA "Autodesk\Revit\Addins\$RevitVersion"
New-Item -ItemType Directory -Force -Path $addinDir | Out-Null

$dllTarget = Join-Path $addinDir "GigAi.RevitAddin.dll"
$usedVersionedTarget = $false
try {
    Copy-Item -Path $dllSource -Destination $dllTarget -Force
}
catch {
    # If the canonical DLL is locked (usually because Revit is open),
    # install to a versioned filename and repoint the addin manifest.
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $versionedTarget = Join-Path $addinDir "GigAi.RevitAddin.$timestamp.dll"
    try {
        Copy-Item -Path $dllSource -Destination $versionedTarget -Force
        $dllTarget = $versionedTarget
        $usedVersionedTarget = $true
    }
    catch {
        throw "Could not copy DLL to '$dllTarget' (or fallback '$versionedTarget'). Close Revit and run installer again."
    }
}

$manifestContent = Get-Content -Raw -Path $templatePath
$manifestContent = $manifestContent.Replace("__ASSEMBLY_PATH__", $dllTarget)

$manifestPath = Join-Path $addinDir "GigAi.RevitAddin.addin"
Set-Content -Path $manifestPath -Value $manifestContent -Encoding UTF8

if ($ConfigureUserEnvironment) {
    [System.Environment]::SetEnvironmentVariable("GIGAI_API_URL", $ApiUrl, "User")
    [System.Environment]::SetEnvironmentVariable("GIGAI_PROJECT_ID", $ProjectId, "User")
    [System.Environment]::SetEnvironmentVariable("GIGAI_PROJECT_ROOT", $resolvedProjectRoot, "User")
}

Write-Host "Installed:"
Write-Host "  DLL: $dllTarget"
Write-Host "  Manifest: $manifestPath"
if ($ConfigureUserEnvironment) {
    Write-Host "  User env: GIGAI_API_URL=$ApiUrl"
    Write-Host "  User env: GIGAI_PROJECT_ID=$ProjectId"
    Write-Host "  User env: GIGAI_PROJECT_ROOT=$resolvedProjectRoot"
}
Write-Host ""
if ($usedVersionedTarget) {
    Write-Host "Detected locked previous DLL. Installed to versioned filename and updated manifest."
}
Write-Host "Restart Revit to load the add-in."
