param(
    [string]$Version
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Read-Host "Enter the new version (for example, 1.0.1)"
}

$Version = $Version.Trim().TrimStart("v")
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must use the format MAJOR.MINOR.PATCH, for example 1.0.1"
}

$Tag = "v$Version"
$configPath = Join-Path $PSScriptRoot "config.py"
$config = Get-Content $configPath -Raw
$versionMatch = [regex]::Match($config, 'APP_VERSION\s*=\s*"[^"]+"')
if (-not $versionMatch.Success) {
    throw "APP_VERSION was not found in config.py"
}

$updatedConfig = [regex]::Replace(
    $config,
    'APP_VERSION\s*=\s*"[^"]+"',
    "APP_VERSION = `"$Version`"",
    1
)

$existingTag = & git tag --list $Tag
if ($existingTag -eq $Tag) {
    throw "Tag $Tag already exists"
}

[System.IO.File]::WriteAllText(
    $configPath,
    $updatedConfig,
    [System.Text.UTF8Encoding]::new($false)
)
& git add .
& git commit -m "Release $Tag"
if ($LASTEXITCODE -ne 0) {
    throw "Git commit failed"
}

& git tag -a $Tag -m "Release $Tag"
if ($LASTEXITCODE -ne 0) {
    throw "Git tag creation failed"
}
& git push origin main
if ($LASTEXITCODE -ne 0) {
    throw "Branch push failed"
}
& git push origin $Tag
if ($LASTEXITCODE -ne 0) {
    throw "Tag push failed"
}

Write-Host "Release $Tag pushed successfully. GitHub Actions will build the release." -ForegroundColor Green
