#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$programs = @(
    @{ Name = 'D1-Classroom-Dev-Discovery'; Path = 'd1-classroom\node_modules\electron\dist\electron.exe' },
    @{ Name = 'D1-Classroom-Release-Discovery'; Path = 'output\D1彩色課程套件\學生工具\D1學生工坊\D1學生工坊.exe' }
)
foreach ($program in $programs) {
    $executable = Join-Path $projectRoot $program.Path
    if (-not (Test-Path -LiteralPath $executable)) { throw "Missing executable: $executable" }
}
foreach ($program in $programs) {
    $executable = Join-Path $projectRoot $program.Path
    if (Get-NetFirewallRule -Name $program.Name -ErrorAction SilentlyContinue) {
        Write-Host "Existing rule kept: $($program.Name)"
        continue
    }
    New-NetFirewallRule -Name $program.Name -DisplayName $program.Name `
        -Direction Inbound -Action Allow -Enabled True -Profile Private `
        -Program $executable -Protocol UDP -RemotePort 8765 -RemoteAddress LocalSubnet | Out-Null
    Write-Host "Allowed private-LAN UDP discovery replies: $executable"
}
Write-Host 'Firewall remains enabled. Use only a trusted private classroom LAN; no network profile was changed.'
