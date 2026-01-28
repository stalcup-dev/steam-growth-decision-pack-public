$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

function Get-GitPaths {
    param([string[]]$GitArgs)

    $out = & git @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }

    return ($out -split "`n") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
}

function Test-AllowedPath {
    param([string]$Path)

    $p = $Path -replace "\\", "/"
    $allowedExact = @(
        "README.md",
        "scripts/build_readme_assets.py",
        "scripts/build_tail_validation.py",
        "assets/lift_decay.png",
        "assets/lift_curve_by_discount_tier.png",
        "assets/decay_by_discount_tier.png",
        "examples/worked_example.md",
        "client_preview_onepager.md",
        "decision_memo.md",
        "playbook_table_public.csv",
        "PUBLIC_VS_PRIVATE.md",
        "SERVICE_OFFER_PUBLIC.md",
        "docs/DATA_REQUEST_CLIENT.md",
        "docs/REVENUE_ROI_PACK.md",
        "FAQ.md",
        "REPO_STATE.md",
        ".github/workflows/publish-audit.yml",
        ".github/ISSUE_TEMPLATE/decision-pack.yml",
        "publish_audit.ps1",
        "scripts/publish_audit.ps1",
        "setup_hooks.ps1",
        "scripts/setup_hooks.ps1",
        ".gitignore",
        "LICENSE"
    )
$allowedGlobs = @(
        "reports/figures/*.png"
    )

    if ($allowedExact -contains $p) { return $true }

    foreach ($g in $allowedGlobs) {
        if ($p -like $g) { return $true }
    }

    return $false
}

Write-Host "Publish Audit (ALLOWLIST MODE) - scanning tracked + staged files..."

$tracked = Get-GitPaths -GitArgs @("ls-files")
$staged = Get-GitPaths -GitArgs @("diff", "--cached", "--name-only")

$all = @($tracked + $staged) | Sort-Object -Unique

if ($all.Count -eq 0) {
    Write-Host "No files detected. (Nothing to validate)"
    exit 0
}

$blocked = @()

foreach ($f in $all) {
    if (-not (Test-AllowedPath -Path $f)) {
        $blocked += $f
    }
}

if ($blocked.Count -gt 0) {
    Write-Host ""
    Write-Host "Publish Audit FAILED - non-allowlisted files detected:"
    $blocked | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    Write-Host "Fix: unstage/remove these files, or explicitly add to allowlist if truly public-safe."
    exit 1
}

Write-Host "Publish Audit PASSED - all files are allowlisted."
exit 0




