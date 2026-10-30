param(
    [string]$Python = 'python',
    [switch]$WithPrintables,
    [switch]$WithUiTests
)
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$appRoot = Join-Path $projectRoot 'd1-classroom'
Get-Command node -ErrorAction Stop | Out-Null
Get-Command $Python -ErrorAction Stop | Out-Null
& node -e "if(Number(process.versions.node.split('.')[0])<22){console.error('Node.js 22+ is required.');process.exit(1)}"
if ($LASTEXITCODE -ne 0) { throw 'Install Node.js 22+ before continuing.' }
& $Python -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Workstation Python 3.10+ is required. The robot itself requires exactly CPython 3.10.' }
$requiredPnpm = ((Get-Content -LiteralPath (Join-Path $appRoot 'package.json') -Raw -Encoding UTF8 | ConvertFrom-Json).packageManager -replace '^pnpm@','')
$pnpmCommand = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
$useInstalledPnpm = $false
if ($pnpmCommand) {
    $installedVersion = & $pnpmCommand.Source --version
    $useInstalledPnpm = $LASTEXITCODE -eq 0 -and $installedVersion.Trim() -eq $requiredPnpm
}
function Invoke-D1Pnpm([string[]]$Arguments) {
    if ($useInstalledPnpm) { & $pnpmCommand.Source @Arguments }
    else {
        $npmCommand = Get-Command npx.cmd -ErrorAction Stop
        & $npmCommand.Source --yes "pnpm@$requiredPnpm" @Arguments
    }
    if ($LASTEXITCODE -ne 0) { throw ('pnpm command failed: ' + ($Arguments -join ' ')) }
}
Push-Location $appRoot
try {
    Invoke-D1Pnpm -Arguments @('install','--frozen-lockfile')
    Invoke-D1Pnpm -Arguments @('run','bundle')
    & $Python build/courseware.py
    if ($LASTEXITCODE -ne 0) { throw 'Course website generation failed.' }
} finally { Pop-Location }
if ($WithPrintables) {
    $venvRoot = Join-Path $projectRoot 'local\venv'
    $venvPython = Join-Path $venvRoot 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $Python -m venv $venvRoot
        if ($LASTEXITCODE -ne 0) { throw 'Could not create local/venv.' }
    }
    & $venvPython -m pip install -r (Join-Path $appRoot 'requirements-author.txt')
    if ($LASTEXITCODE -ne 0) { throw 'PDF authoring dependencies failed to install.' }
    Write-Host 'PDF Python: local/venv/Scripts/python.exe (no environment activation required).'
}
if ($WithUiTests) {
    $npmCommand = Get-Command npm.cmd -ErrorAction Stop
    & $npmCommand.Source install --prefix (Join-Path $projectRoot 'local\test-tools') --no-package-lock playwright@1.62.1
    if ($LASTEXITCODE -ne 0) { throw 'UI test dependencies failed to install.' }
    Write-Host 'Set D1_PLAYWRIGHT to local/test-tools/node_modules/playwright before UI tests.'
}
if ($useInstalledPnpm) { Write-Host 'Development source is ready. Run: cd d1-classroom; pnpm run dev' }
else { Write-Host "Development source is ready. Run: cd d1-classroom; npx --yes pnpm@$requiredPnpm run dev" }
Write-Host 'Core checks: powershell -NoProfile -File scripts/test.ps1 (from repository root).'
Write-Host 'No published Release or version manifest was changed; no physical robot was contacted.'
