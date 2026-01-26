#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $repoRoot
Set-Location $repoRoot

$hooksDir = Join-Path $repoRoot ".git\hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

$hookPath = Join-Path $hooksDir "pre-push"
$hookContent = "#!/bin/sh`n" +
"powershell -ExecutionPolicy Bypass -File ./publish_audit.ps1`n" +
"if [ $? -ne 0 ]; then`n" +
"  echo `"Publish audit failed. Push blocked.`"`n" +
"  exit 1`n" +
"fi`n"

Set-Content -Path $hookPath -Value $hookContent -Encoding ASCII
Write-Host "Installed pre-push hook at $hookPath"
