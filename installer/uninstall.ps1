$ErrorActionPreference = "Stop"

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $InstallerDir
$AppName = "BF-Particle-Tracker"
$VenvDir = Join-Path $ProjectRoot ".venv_app"

Write-Host "Removing shortcuts for $AppName..."

$DesktopShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"
if (Test-Path $DesktopShortcutPath) {
    Remove-Item -LiteralPath $DesktopShortcutPath -Force
}

$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$AppName"
if (Test-Path $StartMenuDir) {
    Remove-Item -LiteralPath $StartMenuDir -Recurse -Force
}

$answer = Read-Host "Remove the local Python environment from this app folder too? [y/N]"
if ($answer -match "^[Yy]") {
    $resolvedProject = (Resolve-Path -LiteralPath $ProjectRoot).Path
    $resolvedVenv = (Resolve-Path -LiteralPath $VenvDir -ErrorAction SilentlyContinue)
    if ($resolvedVenv -and $resolvedVenv.Path.StartsWith($resolvedProject, [System.StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolvedVenv.Path -Recurse -Force
        Write-Host "Removed $($resolvedVenv.Path)"
    }
}

Write-Host "Uninstall finished. Project files were kept in:"
Write-Host $ProjectRoot
