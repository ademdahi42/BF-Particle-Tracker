$ErrorActionPreference = "Stop"

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $InstallerDir
$PythonExe = Join-Path $ProjectRoot ".venv_app\Scripts\python.exe"
$Launcher = Join-Path $InstallerDir "setup_launcher.py"
$Icon = Join-Path $ProjectRoot "assets\app_icon.ico"
$DistDir = Join-Path $ProjectRoot "release"
$BuildDir = Join-Path $ProjectRoot "release\build_setup"
$SpecDir = Join-Path $ProjectRoot "release"
$SetupExe = Join-Path $DistDir "BF-Particle-Tracker-Setup.exe"
$InstallerSetupExe = Join-Path $InstallerDir "BF-Particle-Tracker-Setup.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Local environment not found. Run installer\install.bat once on this development PC first."
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

Write-Host "Installing PyInstaller in the local development environment..."
& $PythonExe -m pip install pyinstaller

Write-Host "Building setup executable..."
& $PythonExe -m PyInstaller `
    --onefile `
    --console `
    --clean `
    --name "BF-Particle-Tracker-Setup" `
    --icon "$Icon" `
    --distpath "$DistDir" `
    --workpath "$BuildDir" `
    --specpath "$SpecDir" `
    "$Launcher"

if (-not (Test-Path $SetupExe)) {
    throw "Setup executable was not created: $SetupExe"
}

Copy-Item -LiteralPath $SetupExe -Destination $InstallerSetupExe -Force

Write-Host ""
Write-Host "Setup executable created:"
Write-Host $SetupExe
Write-Host "Installer copy updated:"
Write-Host $InstallerSetupExe
