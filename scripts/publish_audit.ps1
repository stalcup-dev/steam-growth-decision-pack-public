$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

$files = git ls-files
if (-not $files) {
    Write-Host "No tracked files found. Is this a git repo?"
    exit 1
}

$rules = @(
    @{ Pattern = '^src/'; Reason = 'src/ is not allowed in public repo' },
    @{ Pattern = '^notebooks/'; Reason = 'notebooks/ is not allowed in public repo' },
    @{ Pattern = '^tests/'; Reason = 'tests/ is not allowed in public repo' },
    @{ Pattern = '\\.parquet$'; Reason = '.parquet files are not allowed' },
    @{ Pattern = '\\.zip$'; Reason = '.zip files are not allowed' },
    @{ Pattern = '^data/raw/'; Reason = 'data/raw is not allowed' },
    @{ Pattern = '^data/processed/'; Reason = 'data/processed is not allowed' },
    @{ Pattern = '^reports/.*audit'; Reason = 'reports/*audit* is not allowed' },
    @{ Pattern = '^reports/.*summary'; Reason = 'reports/*summary* is not allowed' },
    @{ Pattern = '^reports/.*stable'; Reason = 'reports/*stable* is not allowed' },
    @{ Pattern = '^reports/.*raw'; Reason = 'reports/*raw* is not allowed' }
)

$violations = @()
foreach ($file in $files) {
    foreach ($rule in $rules) {
        if ($file -match $rule.Pattern) {
            $violations += [PSCustomObject]@{
                File = $file
                Reason = $rule.Reason
            }
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Host "Publish audit failed:"
    $violations | Sort-Object File, Reason | Format-Table -AutoSize
    exit 1
}

Write-Host "OK to publish ✅"
