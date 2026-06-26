$ErrorActionPreference = "Stop"

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $InstallerDir
$AppName = "BF-Particle-Tracker"
$VenvDir = Join-Path $ProjectRoot ".venv_app"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$Launcher = Join-Path $ProjectRoot "run_app.bat"
$Icon = Join-Path $ProjectRoot "assets\app_icon.ico"
$SupportedPythonMessage = "Python 3.10, 3.11, or 3.12 64-bit is required. This app pins scientific packages that are not compatible with newer Python versions in this installer."

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)] [string] $Command,
        [Parameter(Mandatory = $true)] [string[]] $CommandArgs
    )

    & $Command @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($CommandArgs -join ' ')"
    }
}

function Find-PythonCommand {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.12") },
        @{ Command = "py"; Args = @("-3.11") },
        @{ Command = "py"; Args = @("-3.10") },
        @{ Command = "python"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $command = $candidate.Command
        $baseArgs = $candidate.Args
        $versionArgs = $baseArgs + @("-c", "import sys; raise SystemExit(0 if ((3, 10) <= sys.version_info[:2] < (3, 13) and sys.maxsize > 2**32) else 1)")

        try {
            & $command @versionArgs 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            continue
        }
    }

    throw "$SupportedPythonMessage Install Python 3.12 from https://www.python.org/downloads/windows/ and enable 'Add python.exe to PATH'."
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)] $PythonCandidate,
        [Parameter(ValueFromRemainingArguments = $true)] [string[]] $PythonArgs
    )

    Invoke-CheckedCommand $PythonCandidate.Command @($PythonCandidate.Args + $PythonArgs)
}

function Test-VenvPython {
    param(
        [Parameter(Mandatory = $true)] [string] $PythonExe
    )

    & $PythonExe -c "import sys; raise SystemExit(0 if ((3, 10) <= sys.version_info[:2] < (3, 13) and sys.maxsize > 2**32) else 1)" 1>$null 2>$null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path $Requirements)) {
    throw "Missing requirements.txt in $ProjectRoot"
}

Write-Host "Installing $AppName"
Write-Host "Project folder: $ProjectRoot"

$PythonCommand = Find-PythonCommand
Write-Host "Using Python command: $($PythonCommand.Command) $($PythonCommand.Args -join ' ')"

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating local Python environment..."
    Invoke-Python $PythonCommand -m venv "$VenvDir"
} else {
    Write-Host "Local Python environment already exists."
}

$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "The local Python executable was not created correctly: $PythonExe"
}
if (-not (Test-VenvPython $PythonExe)) {
    throw "The existing local Python environment uses an unsupported Python version. Delete '$VenvDir', install Python 3.12 64-bit, then run this installer again. $SupportedPythonMessage"
}

Write-Host "Installing Python packages..."
Invoke-CheckedCommand $PythonExe @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
Invoke-CheckedCommand $PythonExe @("-m", "pip", "install", "-r", $Requirements)

Write-Host "Checking application imports..."
Invoke-CheckedCommand $PythonExe @("-m", "py_compile", (Join-Path $ProjectRoot "main.py"), (Join-Path $ProjectRoot "gui.py"), (Join-Path $ProjectRoot "processing.py"))
Invoke-CheckedCommand $PythonExe @("-c", "import dearpygui.dearpygui; import numpy; import scipy; import skimage; import tifffile; import trackpy; import cv2; import pandas; import matplotlib")

Write-Host "Creating shortcuts..."
$Shell = New-Object -ComObject WScript.Shell

$DesktopShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"
$DesktopShortcut = $Shell.CreateShortcut($DesktopShortcutPath)
$DesktopShortcut.TargetPath = $Launcher
$DesktopShortcut.WorkingDirectory = $ProjectRoot
if (Test-Path $Icon) {
    $DesktopShortcut.IconLocation = $Icon
}
$DesktopShortcut.Save()

$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$AppName"
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
$StartMenuShortcutPath = Join-Path $StartMenuDir "$AppName.lnk"
$StartMenuShortcut = $Shell.CreateShortcut($StartMenuShortcutPath)
$StartMenuShortcut.TargetPath = $Launcher
$StartMenuShortcut.WorkingDirectory = $ProjectRoot
if (Test-Path $Icon) {
    $StartMenuShortcut.IconLocation = $Icon
}
$StartMenuShortcut.Save()

Write-Host ""
Write-Host "$AppName is ready."
Write-Host "Launch it with the Desktop shortcut or run:"
Write-Host $Launcher
