#Requires -Version 5.1
<#
.SYNOPSIS
    Installs the GigAI Revit plugin to the Revit 2026 add-ins folder.
.DESCRIPTION
    Copies the compiled DLL and the .addin manifest to:
    %APPDATA%\Autodesk\Revit\Addins\2026\
    Build the project first with: dotnet build --configuration Release
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$revitAddinsDir = Join-Path $env:APPDATA "Autodesk\Revit\Addins\2026"
$buildOutput    = Join-Path $PSScriptRoot "GigAi.RevitPlugin\bin\Release\net48"
$addinManifest  = Join-Path $PSScriptRoot "GigAi.addin"

# Ensure the target folder exists
if (-not (Test-Path $revitAddinsDir)) {
    New-Item -ItemType Directory -Path $revitAddinsDir -Force | Out-Null
    Write-Host "Created: $revitAddinsDir"
}

# Verify build output exists
if (-not (Test-Path $buildOutput)) {
    Write-Error "Build output not found at: $buildOutput`nRun 'dotnet build --configuration Release' first."
}

# Files to copy from the build output
$filesToCopy = @(
    "GigAi.RevitPlugin.dll",
    "Newtonsoft.Json.dll"
)

foreach ($file in $filesToCopy) {
    $src = Join-Path $buildOutput $file
    if (Test-Path $src) {
        Copy-Item $src $revitAddinsDir -Force
        Write-Host "Copied: $file"
    } else {
        Write-Warning "Not found (skipped): $file"
    }
}

# Copy the .addin manifest
Copy-Item $addinManifest $revitAddinsDir -Force
Write-Host "Copied: GigAi.addin"

Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Plugin folder: $revitAddinsDir"
Write-Host "Backend URL:   http://localhost:8000  (hardcoded)"
Write-Host ""
Write-Host "Start (or restart) Revit 2026 to load the GigAI tab."
