param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$InitializerArguments
)
$ErrorActionPreference = 'Stop'
$portableRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
try {
    $manifestPath = Join-Path $portableRoot 'PORTABLE-MANIFEST.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Incomplete portable folder. Extract the whole ZIP first.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($entry in $manifest.files) {
        $target = [IO.Path]::GetFullPath((Join-Path $portableRoot $entry.path))
        if (-not $target.StartsWith($portableRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Portable manifest path is outside the package.'
        }
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Missing portable file: $($entry.path)" }
        $stream = [IO.File]::OpenRead($target)
        $hasher = [Security.Cryptography.SHA256]::Create()
        try { $actual = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
        finally { $stream.Dispose(); $hasher.Dispose() }
        if ($actual -ne $entry.sha256) { throw "Damaged portable file: $($entry.path)" }
    }
    $python = Join-Path $portableRoot 'runtime\python\python.exe'
    $initializer = Join-Path $portableRoot 'scripts\initialize-robot.py'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    & $python -I $initializer @InitializerArguments
    exit $LASTEXITCODE
} catch {
    Write-Host ('Portable initialization stopped: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
