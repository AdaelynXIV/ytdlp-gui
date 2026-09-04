param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw "Python was not found. Create .venv or install Python first."
    }
    $python = $pythonCommand.Source
}

Push-Location $PSScriptRoot
try {
    & $python -m pip install yt-dlp curl-cffi imageio-ffmpeg requests packaging
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime dependency installation failed"
    }

    & $python -c "import PyInstaller"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing PyInstaller..."
        & $python -m pip install --upgrade pyinstaller
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller installation failed"
        }
    }

    $arguments = @(
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean"
    )

    if ($Clean) {
        Remove-Item -Recurse -Force "build", "dist" -ErrorAction SilentlyContinue
    }

    foreach ($output in @("dist\YTDLP-GUI.exe", "dist\YTDLP-Updater.exe")) {
        if (Test-Path $output) {
            try {
                Remove-Item -Force $output -ErrorAction Stop
            }
            catch {
                throw "Cannot replace $output. Close the running application and try again."
            }
        }
    }

    foreach ($spec in @("YTDLP-GUI.spec", "updater.spec")) {
        & $python @arguments $spec
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed for $spec"
        }
    }

    $application = Join-Path $PSScriptRoot "dist\YTDLP-GUI.exe"
    $updater = Join-Path $PSScriptRoot "dist\YTDLP-Updater.exe"
    if (-not (Test-Path $application) -or -not (Test-Path $updater)) {
        throw "Build completed without producing both executables"
    }

    Write-Host "Build complete:" -ForegroundColor Green
    Write-Host $application
    Write-Host $updater
}
finally {
    Pop-Location
}
