$ErrorActionPreference = "Stop"
& powershell -ExecutionPolicy Bypass -File "./scripts/publish_audit.ps1"
exit $LASTEXITCODE
