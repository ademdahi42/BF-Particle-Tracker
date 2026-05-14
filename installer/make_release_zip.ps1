$ErrorActionPreference = "Stop"

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $InstallerDir
$ReleaseDir = Join-Path $ProjectRoot "release"
$PackageRoot = Join-Path $ReleaseDir "BF-Particle-Tracker"
$ZipPath = Join-Path $ReleaseDir "BF-Particle-Tracker-windows.zip"
$InnoInstallerExe = Join-Path $ReleaseDir "BF-Particle-Tracker-Installer.exe"

if (Test-Path $PackageRoot) {
    Remove-Item -LiteralPath $PackageRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null

$items = @(
    "main.py",
    "gui.py",
    "processing.py",
    "requirements.txt",
    "README.md",
    "run_app.bat",
    "assets",
    "documentation",
    "installer"
)

foreach ($item in $items) {
    $source = Join-Path $ProjectRoot $item
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination $PackageRoot -Recurse -Force
    }
}

if (Test-Path $InnoInstallerExe) {
    Copy-Item -LiteralPath $InnoInstallerExe -Destination (Join-Path $PackageRoot "BF-Particle-Tracker-Installer.exe") -Force
}

Get-ChildItem -LiteralPath $PackageRoot -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $PackageRoot -Recurse -Directory -Filter ".venv_app" | Remove-Item -Recurse -Force

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -LiteralPath $PackageRoot -DestinationPath $ZipPath -Force

Write-Host "Release package created:"
Write-Host $ZipPath
