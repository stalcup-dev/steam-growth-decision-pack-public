$ErrorActionPreference = "Stop"
& powershell -ExecutionPolicy Bypass -File "./scripts/setup_hooks.ps1"
exit $LASTEXITCODE
