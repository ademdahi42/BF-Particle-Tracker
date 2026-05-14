# BF-Particle-Tracker Windows installer

This folder contains Windows installer tools for BF-Particle-Tracker.

## Install

1. Install Python 3.10 or newer from <https://www.python.org/downloads/windows/>.
2. During Python installation, enable **Add python.exe to PATH**.
3. Double-click `BF-Particle-Tracker-Installer.exe` if it is provided in the release.
4. Launch the app from the Desktop shortcut named `BF-Particle-Tracker`.

The installer creates a local Python environment inside the application folder and installs the packages listed in `requirements.txt`.

If Windows blocks the executable the first time, choose **More info** and then **Run anyway**. To remove this warning completely, the installer must be signed with a trusted code-signing certificate.
If the Inno Setup installer is not available, `install.bat` is kept as a fallback installer.

## Launch

After installation, use either:

- the Desktop shortcut;
- the Start Menu shortcut;
- `run_app.bat`.

## Create a zip package for sharing

From PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_inno_installer.ps1
powershell -ExecutionPolicy Bypass -File installer\make_release_zip.ps1
```

This creates:

```text
release\BF-Particle-Tracker-windows.zip
```

Send that zip file to another Windows user. They should unzip it, then run `BF-Particle-Tracker-Installer.exe` if present, or `installer\install.bat` as fallback.

## Build the Inno Setup installer

1. Install Inno Setup 6 from <https://jrsoftware.org/isdl.php>.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_inno_installer.ps1
```

The output is:

```text
release\BF-Particle-Tracker-Installer.exe
```

## About signed installers

Inno Setup creates a standard Windows installer, but Windows SmartScreen may still warn users if the installer is unsigned. To avoid this warning, sign the final `.exe` with a trusted code-signing certificate after building it.

Example signing command:

```powershell
powershell -ExecutionPolicy Bypass -File installer\sign_installer.ps1 `
  -CertificatePath "C:\path\to\certificate.pfx" `
  -CertificatePassword "certificate-password" `
  -TimestampUrl "http://timestamp.digicert.com"
```

The certificate must come from a trusted code-signing authority. A self-signed certificate is useful for local tests, but it will not remove SmartScreen warnings for other users.

## Uninstall

Run:

```text
installer\uninstall.bat
```

The uninstall script removes Desktop and Start Menu shortcuts. It can also remove the local Python environment if you choose to.
