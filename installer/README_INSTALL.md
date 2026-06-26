# BF-Particle-Tracker Script Installer

BF-Particle-Tracker is distributed as a normal project folder with a script-based Windows installer. This avoids unsigned `.exe` installers, which are often blocked on managed lab computers.

## Install

1. Install Python 3.12 64-bit from <https://www.python.org/downloads/windows/>.
2. During Python installation, enable **Add python.exe to PATH**.
3. Unzip the BF-Particle-Tracker folder.
4. Double-click:

```text
installer\install.bat
```

The script creates a local `.venv_app` environment inside the app folder and installs the packages listed in `requirements.txt`.

## If Windows Blocks The Batch Files

Windows may block `.bat` files that came from a downloaded zip or a Git clone. If you see a security warning, unblock the app folder, then run the installer again:

```powershell
cd "C:\path\to\BF-Particle-Tracker"
Get-ChildItem -Recurse | Unblock-File
```

You can also right-click the downloaded zip before extracting it, choose **Properties**, check **Unblock**, then extract it again.

## Python Version

Use Python 3.10, 3.11, or 3.12 64-bit. Python 3.12 is recommended. The installer rejects newer Python versions because this app pins scientific packages that may not install cleanly there.

## Launch

After installation, use one of these:

- the Desktop shortcut named `BF-Particle-Tracker`;
- the Start Menu shortcut;
- `run_app.bat`.

## Create A Zip Package For Sharing

From PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File installer\make_release_zip.ps1
```

This creates:

```text
release\BF-Particle-Tracker-windows.zip
```

Send that zip file to another Windows user. They should unzip it, then run `installer\install.bat`.

## Uninstall

Run:

```text
installer\uninstall.bat
```

The uninstall script removes Desktop and Start Menu shortcuts. It can also remove the local Python environment if you choose to.
