# BF-Particle-Tracker

![BF-Particle-Tracker icon](assets/app_icon.png)

DearPyGUI application for microscopy particle tracking in TIFF/OME-TIFF videos.

## Launch

Double-click `run_app.bat`, or run:

```bat
.venv_app\Scripts\python.exe main.py
```

## Windows installation

For a new Windows user:

1. Unzip the app folder.
2. Run `installer\install.bat`.
3. Launch `BF-Particle-Tracker` from the Desktop shortcut.

To create a clean zip package for sharing, run:

```bat
powershell -ExecutionPolicy Bypass -File installer\make_release_zip.ps1
```

The package is created in `release\BF-Particle-Tracker-windows.zip`.

## Main workflow

1. Load one or several TIFF/OME-TIFF videos.
2. Adjust preprocessing while comparing raw, preprocessed, binary, and enhanced binary views.
3. Run detection on the current frame.
4. Set the detection as the initial reference.
5. Start tracking.
6. Review trajectory, histograms, and stiffness estimate.
7. Save CSV results and JSON metadata.

Full user documentation is available in:

- `documentation\Particle_Tracking_User_Documentation.html`
- `documentation\Particle_Tracking_User_Documentation.pdf`
