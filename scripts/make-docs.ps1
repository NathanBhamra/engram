# Build and serve the Engram documentation site locally.

[CmdletBinding()]
param([switch]$Build)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$activate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $activate) { . $activate }

if ($Build) {
    mkdocs build --strict
} else {
    mkdocs serve
}
