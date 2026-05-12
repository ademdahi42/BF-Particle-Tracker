# BF-Particle-Tracker

DearPyGUI application for microscopy particle tracking in TIFF/OME-TIFF videos.

## What it does

- Loads one or several TIFF/OME-TIFF stacks.
- Displays raw, preprocessed, binary, and enhanced binary images.
- Detects a particle with a binary blob/regionprops workflow.
- Tracks the particle centroid over time.
- Shows live trajectory, histograms, time traces, and stiffness estimates.
- Saves CSV measurements and JSON metadata.

## Launch

Double-click `run_app.bat`, or run:

```bat
.venv_app\Scripts\python.exe main.py
```

## Basic use

1. Load video.
2. Adjust preprocessing and blob parameters while viewing the image panels.
3. Run detection on the current frame.
4. Set as initial detection.
5. Start tracking.
6. Save results.

Full documentation:

- `Particle_Tracking_User_Documentation.html`
- `Particle_Tracking_User_Documentation.pdf`
