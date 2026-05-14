# BF-Particle-Tracker Windows installer

This folder contains a simple Windows installer for BF-Particle-Tracker.

## Install

1. Install Python 3.10 or newer from <https://www.python.org/downloads/windows/>.
2. During Python installation, enable **Add python.exe to PATH**.
3. Double-click `BF-Particle-Tracker-Setup.exe`.
4. Launch the app from the Desktop shortcut named `BF-Particle-Tracker`.

The installer creates a local Python environment inside the application folder and installs the packages listed in `requirements.txt`.

If Windows blocks the executable the first time, choose **More info** and then **Run anyway**.
If the executable is not available, `install.bat` is kept as a fallback installer.

## Launch

After installation, use either:

- the Desktop shortcut;
- the Start Menu shortcut;
- `run_app.bat`.

## Create a zip package for sharing

From PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_setup_exe.ps1
powershell -ExecutionPolicy Bypass -File installer\make_release_zip.ps1
```

This creates:

```text
release\BF-Particle-Tracker-windows.zip
```

Send that zip file to another Windows user. They should unzip it, then run `BF-Particle-Tracker-Setup.exe` or `installer\BF-Particle-Tracker-Setup.exe`.

## Uninstall

Run:

```text
installer\uninstall.bat
```

The uninstall script removes Desktop and Start Menu shortcuts. It can also remove the local Python environment if you choose to.
