param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'd1-classroom')
try {
    Get-Command node -ErrorAction Stop | Out-Null
    Get-Command $Python -ErrorAction Stop | Out-Null
    Write-Host 'Running JavaScript core tests...'
    $env:D1_PYTHON = $Python
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $testFiles = @(Get-ChildItem -LiteralPath tests -Filter '*.test.cjs' | ForEach-Object FullName)
    & node --test @testFiles
    if ($LASTEXITCODE -ne 0) { throw 'JavaScript tests failed.' }
    Write-Host 'Running Python fake SDK tests...'
    & $Python -m unittest discover -s tests -p '*_test.py'
    if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }
    Write-Host 'Running release immutability tests...'
    & $Python (Join-Path $PSScriptRoot 'test_prepare_release.py')
    if ($LASTEXITCODE -ne 0) { throw 'Release preparation tests failed.' }
    Write-Host 'PASS: all core tests completed. No physical robot was tested.'
} finally {
    Pop-Location
}
