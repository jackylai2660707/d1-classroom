param([string]$Python = 'python', [switch]$RunTests)
$ErrorActionPreference = 'Stop'
Get-Command $Python -ErrorAction Stop | Out-Null
& $Python (Join-Path $PSScriptRoot 'preflight.py') --strict-delivery
if ($LASTEXITCODE -ne 0) { throw 'Preflight checks need attention. Read the report in field-results/.' }
if ($RunTests) {
    & (Join-Path $PSScriptRoot 'test.ps1') -Python $Python
    if ($LASTEXITCODE -ne 0) { throw 'Core tests failed.' }
}
Write-Host 'No physical robot was tested. Continue with docs/公司電腦實機測試.md.'
