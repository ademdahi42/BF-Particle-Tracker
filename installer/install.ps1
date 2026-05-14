$ErrorActionPreference = "Stop"

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $InstallerDir
$AppName = "BF-Particle-Tracker"
$VenvDir = Join-Path $ProjectRoot ".venv_app"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$Launcher = Join-Path $ProjectRoot "run_app.bat"
$Icon = Join-Path $ProjectRoot "assets\app_icon.ico"

function Find-PythonCommand {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.11") },
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "python"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $command = $candidate.Command
        $baseArgs = $candidate.Args
        $versionArgs = $baseArgs + @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)")

        try {
            & $command @versionArgs 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            continue
        }
    }

    throw "Python 3.10 or newer was not found. Install Python from https://www.python.org/downloads/windows/ and enable 'Add python.exe to PATH'."
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)] $PythonCandidate,
        [Parameter(ValueFromRemainingArguments = $true)] [string[]] $PythonArgs
    )

    & $PythonCandidate.Command @($PythonCandidate.Args + $PythonArgs)
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($PythonCandidate.Command) $($PythonCandidate.Args -join ' ') $($PythonArgs -join ' ')"
    }
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

Write-Host "Installing Python packages..."
& $PythonExe -m pip install --upgrade pip setuptools wheel
& $PythonExe -m pip install -r $Requirements

Write-Host "Checking application imports..."
& $PythonExe -m py_compile (Join-Path $ProjectRoot "main.py") (Join-Path $ProjectRoot "gui.py") (Join-Path $ProjectRoot "processing.py")

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
