$ErrorActionPreference = "Stop"

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $InstallerDir
$InnoScript = Join-Path $InstallerDir "BF-Particle-Tracker.iss"
$OutputExe = Join-Path $InstallerDir "output\BF-Particle-Tracker-Installer.exe"
$ReleaseExe = Join-Path $ProjectRoot "release\BF-Particle-Tracker-Installer.exe"

function Find-Iscc {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php, then run this script again."
}

if (-not (Test-Path $InnoScript)) {
    throw "Missing Inno Setup script: $InnoScript"
}

$Iscc = Find-Iscc
Write-Host "Using Inno Setup compiler:"
Write-Host $Iscc

& $Iscc $InnoScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed."
}

if (-not (Test-Path $OutputExe)) {
    throw "Installer was not created: $OutputExe"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ReleaseExe) | Out-Null
Copy-Item -LiteralPath $OutputExe -Destination $ReleaseExe -Force

Write-Host ""
Write-Host "Installer created:"
Write-Host $OutputExe
Write-Host "Release copy:"
Write-Host $ReleaseExe
