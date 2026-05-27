# Engram pre-commit check: lint, format, type-check, test.
#
# Run from any directory inside the repo. Exits non-zero on the first failure.

[CmdletBinding()]
param(
    [switch]$NoCoverage
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$activate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $activate) { . $activate }

Write-Host '== ruff check ==' -ForegroundColor Cyan
ruff check .

Write-Host '== black --check ==' -ForegroundColor Cyan
black --check .

Write-Host '== mypy ==' -ForegroundColor Cyan
mypy src/engram

Write-Host '== pytest ==' -ForegroundColor Cyan
if ($NoCoverage) { pytest -q } else { pytest --cov=engram --cov-report=term-missing -q }

Write-Host ''
Write-Host 'All checks passed.' -ForegroundColor Green
