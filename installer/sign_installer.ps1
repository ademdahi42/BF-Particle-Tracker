param(
    [Parameter(Mandatory = $true)]
    [string] $CertificatePath,

    [Parameter(Mandatory = $true)]
    [string] $TimestampUrl,

    [string] $CertificatePassword = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$InstallerExe = Join-Path $ProjectRoot "release\BF-Particle-Tracker-Installer.exe"

if (-not (Test-Path $InstallerExe)) {
    throw "Installer not found. Build it first with installer\build_inno_installer.ps1"
}

if (-not (Test-Path $CertificatePath)) {
    throw "Certificate not found: $CertificatePath"
}

$signtool = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if (-not $signtool) {
    $kits = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like "*\x64\signtool.exe" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1

    if ($kits) {
        $signtoolPath = $kits.FullName
    } else {
        throw "signtool.exe was not found. Install the Windows SDK or add signtool to PATH."
    }
} else {
    $signtoolPath = $signtool.Source
}

$args = @(
    "sign",
    "/f", $CertificatePath,
    "/fd", "SHA256",
    "/tr", $TimestampUrl,
    "/td", "SHA256"
)

if ($CertificatePassword) {
    $args += @("/p", $CertificatePassword)
}

$args += $InstallerExe

& $signtoolPath @args
if ($LASTEXITCODE -ne 0) {
    throw "Code signing failed."
}

Write-Host "Signed installer:"
Write-Host $InstallerExe
