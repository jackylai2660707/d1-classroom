param(
    [switch]$IncludeReferences,
    [switch]$Replace,
    [switch]$VerifyOnly,
    [string]$Manifest = '',
    [string]$AssetDirectory = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Manifest) { $Manifest = Join-Path $projectRoot 'releases\v2.0.0.json' }
$release = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($release.schemaVersion -ne 1 -or $release.repository -ne 'jackylai2660707/d1-classroom') { throw 'Unexpected release manifest.' }
if (-not $AssetDirectory) { $AssetDirectory = Join-Path $projectRoot 'downloads' }
$AssetDirectory = [System.IO.Path]::GetFullPath($AssetDirectory)
New-Item -ItemType Directory -Path $AssetDirectory -Force | Out-Null
$selected = @($release.assets | Where-Object { $_.role -ne 'references' -or $IncludeReferences })
function Get-D1FileHash([string]$Path) {
    $stream = [System.IO.File]::OpenRead($Path)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}

foreach ($asset in $selected) {
    if ($asset.name -notmatch '^[A-Za-z0-9._-]+\.zip$' -or $asset.sha256 -notmatch '^[a-f0-9]{64}$') { throw 'Invalid release asset entry.' }
    $archive = Join-Path $AssetDirectory $asset.name
    if (-not (Test-Path -LiteralPath $archive)) {
        if ($VerifyOnly) { throw "Missing asset: $archive" }
        Get-Command gh -ErrorAction Stop | Out-Null
        & gh release download $release.tag --repo $release.repository --pattern $asset.name --dir $AssetDirectory
        if ($LASTEXITCODE -ne 0) { throw 'Release download failed. Run gh auth login and check private repository access.' }
    }
    $file = Get-Item -LiteralPath $archive
    if ($file.Length -ne [long]$asset.bytes -or (Get-D1FileHash $archive) -ne $asset.sha256) {
        throw "SHA-256 or size mismatch: $archive. Move this file aside and download again."
    }
    Write-Host ('Verified ' + $asset.name)
}
if ($VerifyOnly) { return }

Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($asset in $selected) {
    $archive = Join-Path $AssetDirectory $asset.name
    if ($asset.role -eq 'setup') {
        $destination = Join-Path $projectRoot 'output\D1機器狗初始化包.zip'
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $archive -Destination $destination -Force
        continue
    }
    if ($asset.role -eq 'classroom') {
        $destinationRoot = Join-Path $projectRoot 'output'
        $destination = Join-Path $destinationRoot 'D1彩色課程套件'
        $archivePrefix = 'D1彩色課程套件/'
        $backupRoot = Join-Path $destinationRoot '.previous-releases'
    } elseif ($asset.role -eq 'references') {
        $destinationRoot = Join-Path $projectRoot 'references'
        $destination = $destinationRoot
        $archivePrefix = 'references/'
        $backupRoot = Join-Path $projectRoot 'local\reference-backups'
    } else { throw 'Unknown release asset role.' }
    $entries = [System.IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($entry in $entries.Entries) {
            $name = $entry.FullName.Replace('\', '/')
            if (-not $name.StartsWith($archivePrefix, [StringComparison]::Ordinal) -or $name -match '(^|/)\.\.(/|$)' -or $name -match '[:\x00]') { throw "Unsafe ZIP member: $name" }
        }
    } finally { $entries.Dispose() }
    if ($asset.role -eq 'classroom' -and (Test-Path -LiteralPath $destination)) {
        if (-not $Replace) {
            Write-Host 'Existing classroom kept. Use -Replace to archive it and restore the release.'
            continue
        }
        $resolved = (Resolve-Path -LiteralPath $destination).ProviderPath
        if ($resolved -ne [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'output\D1彩色課程套件'))) { throw 'Unexpected classroom destination.' }
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        Move-Item -LiteralPath $resolved -Destination (Join-Path $backupRoot ([guid]::NewGuid().ToString('N')))
    }
    # References may already contain a local collection. Never overwrite those files.
    if ($asset.role -eq 'references' -and @(Get-ChildItem -LiteralPath $destinationRoot -Force | Where-Object { $_.Name -ne 'README.md' }).Count -gt 0) {
        Write-Host 'Existing references kept; verified archive remains in downloads/.'
        continue
    }
    New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
    $zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($entry in $zip.Entries) {
            if (-not $entry.Name) { continue }
            $relative = $entry.FullName.Replace('\','/').Substring($archivePrefix.Length)
            if (-not $relative -or ($asset.role -eq 'references' -and $relative -eq 'README.md')) { continue }
            $targetRoot = if ($asset.role -eq 'classroom') { $destination } else { $destinationRoot }
            $target = [System.IO.Path]::GetFullPath((Join-Path $targetRoot $relative))
            if (-not $target.StartsWith([System.IO.Path]::GetFullPath($targetRoot) + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe extraction target.' }
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $false)
        }
    } finally { $zip.Dispose() }
    Write-Host ('Restored ' + $destination)
}
Write-Host 'Ready: output/D1彩色課程套件/使用說明.html. Run scripts/preflight.ps1 before robot testing.'
