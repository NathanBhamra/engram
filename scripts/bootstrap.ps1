# Engram bootstrap (Windows / PowerShell).
#
# One-command setup: creates a virtualenv, installs Engram in editable mode
# with the dev and docs extras, vendors viewer JS, applies the initial
# schema, and runs the test suite to verify the install.

[CmdletBinding()]
param(
    [switch]$NoVendor,
    [switch]$NoTest
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Find-Python {
    $candidates = @(
        'python',
        'py -3.13', 'py -3.12', 'py -3.11',
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($cand in $candidates) {
        $parts = $cand -split ' '
        try {
            $out = & $parts[0] @($parts[1..($parts.Count - 1)] + '--version') 2>$null
            if ($LASTEXITCODE -eq 0 -and $out -match 'Python 3\.(1[1-9]|[2-9]\d)') {
                return ,$parts
            }
        } catch { }
    }
    throw 'Could not find Python 3.11+. Install via your company portal or python.org.'
}

Write-Host '== Locating Python 3.11+ ==' -ForegroundColor Cyan
$py = Find-Python
Write-Host ("Using: {0}" -f ($py -join ' '))

Write-Host '== Creating .venv ==' -ForegroundColor Cyan
& $py[0] @($py[1..($py.Count - 1)] + @('-m', 'venv', '.venv'))

$activate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
. $activate

Write-Host '== Upgrading pip ==' -ForegroundColor Cyan
python -m pip install --upgrade pip wheel setuptools

Write-Host '== Installing engram[dev,docs] in editable mode ==' -ForegroundColor Cyan
pip install -e '.[dev,docs]'

if (-not $NoVendor) {
    Write-Host '== Vendoring viewer assets ==' -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot 'vendor-assets.ps1')
}

Write-Host '== Verifying install ==' -ForegroundColor Cyan
engram --version

if (-not $NoTest) {
    Write-Host '== Running tests ==' -ForegroundColor Cyan
    pytest -q
}

Write-Host ''
Write-Host 'Engram is ready.' -ForegroundColor Green
Write-Host 'Activate the venv in new shells with:  .\.venv\Scripts\Activate.ps1'
