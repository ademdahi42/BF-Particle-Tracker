# BF-Particle-Tracker

![BF-Particle-Tracker image-processing workflow](assets/readme_workflow.png)

BF-Particle-Tracker is a DearPyGUI application for brightfield microscopy particle tracking in TIFF and OME-TIFF videos.

The app is designed for an interactive workflow: load a video stack, tune preprocessing, inspect raw/preprocessed/binary/segmented images, validate the initial detection, track the particle trajectory, then export CSV results and JSON metadata.

## Launch

Double-click `run_app.bat`, or run:

```bat
.venv_app\Scripts\python.exe main.py
```

## Windows Installation

For a new Windows user:

1. Unzip the app folder.
2. Run `installer\install.bat`.
3. Launch `BF-Particle-Tracker` from the Desktop shortcut.

To create a clean zip package for sharing, run:

```bat
powershell -ExecutionPolicy Bypass -File installer\make_release_zip.ps1
```

The package is created in:

```text
release\BF-Particle-Tracker-windows.zip
```

## Main Workflow

1. Load one or several TIFF/OME-TIFF videos.
2. Adjust preprocessing while comparing raw, preprocessed, binary, and enhanced binary views.
3. Run detection on the current frame.
4. Set the detection as the initial reference.
5. Start tracking.
6. Review trajectory, histograms, and stiffness estimate.
7. Save CSV results and JSON metadata.

## Documentation

Full user documentation is available in:

- `documentation\Particle_Tracking_User_Documentation.html`
- `documentation\Particle_Tracking_User_Documentation.pdf`

## Requirements

The installer creates a local Python environment and installs the packages listed in `requirements.txt`.
