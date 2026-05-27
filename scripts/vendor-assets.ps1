# Vendor third-party viewer JS into src/engram/viz/assets/.
#
# Run once at bootstrap. Re-run to update versions. Files are committed to
# the repo so end users do not need internet access at runtime.

[CmdletBinding()]
param(
    [string]$VisNetworkVersion = '9.1.9'
)

$ErrorActionPreference = 'Stop'
$repoRoot   = Split-Path -Parent $PSScriptRoot
$assetsDir  = Join-Path $repoRoot 'src\engram\viz\assets'
New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null

$targets = @(
    @{
        Url  = "https://unpkg.com/vis-network@$VisNetworkVersion/standalone/umd/vis-network.min.js"
        Path = Join-Path $assetsDir 'vis-network.min.js'
    }
)

foreach ($t in $targets) {
    Write-Host ("Downloading {0}" -f $t.Url) -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $t.Url -OutFile $t.Path -UseBasicParsing
        $sizeKb = [Math]::Round((Get-Item $t.Path).Length / 1KB, 1)
        Write-Host ("  -> {0} ({1} KB)" -f $t.Path, $sizeKb) -ForegroundColor Green
    } catch {
        Write-Warning ("Failed to download {0}: {1}" -f $t.Url, $_.Exception.Message)
        Write-Warning 'The viewer will still build but will need internet on first open.'
    }
}

Write-Host ''
Write-Host 'Vendor step complete.' -ForegroundColor Green
