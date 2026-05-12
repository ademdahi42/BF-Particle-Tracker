# BF-Particle-Tracker

Robust brightfield particle tracking and analysis for microscopy videos.

---

# Introduction

Particle tracking in brightfield microscopy is significantly more challenging than in fluorescence imaging.

Unlike fluorescent particles, brightfield particles rarely appear as simple bright spots. Their appearance strongly depends on:
- focus position,
- illumination conditions,
- numerical aperture,
- particle size,
- refractive index mismatch,
- optical aberrations.

As a result, particles often exhibit:
- dark centers,
- bright halos,
- diffraction rings,
- asymmetric intensity patterns,
- blurred edges,
- strong contrast variations over time.

These effects make classical tracking approaches unstable, especially when relying only on:
- thresholding,
- contour extraction,
- simple centroid detection,
- fixed Canny edge parameters.

In practice, brightfield particle tracking frequently suffers from:
- false detections,
- center localization errors,
- unstable radius estimation,
- sensitivity to noise,
- poor robustness across datasets.

This project aims to provide a more robust and adaptive framework for brightfield particle detection and tracking.

The repository combines:
- Trackpy-based localization,
- adaptive preprocessing,
- radial-gradient refinement,
- local symmetry analysis,
- interactive visualization tools,
- benchmarking pipelines.

The goal is to improve detection stability on challenging microscopy data while remaining flexible and easy to experiment with.

---

# Features

## Detection
- Brightfield particle detection
- Halo/ring detection
- Adaptive radial refinement
- Subpixel localization
- Automatic radius estimation
- Robust detection on blurred particles

## Tracking pipelines
- Hybrid Trackpy + radial refinement
- Pure Trackpy pipeline
- Trackpy + Canny pipeline
- Benchmark comparison tools

## Visualization
- Detection overlays
- Zoom inspection
- Radial intensity profiles
- Gradient visualization
- KDE maps
- Histograms
- Interactive frame navigation

## Analysis
- Trajectory extraction
- Position statistics
- Stiffness analysis
- CSV export
- Publication-ready plotting

---

# Detection Principle

The hybrid detection pipeline works as follows:

```text
Microscopy frame
        ↓
Background correction
        ↓
Trackpy coarse localization
        ↓
Local crop extraction
        ↓
Radial symmetry refinement
        ↓
Subpixel center estimation
        ↓
Radius estimation


  title        = {BF-Particle-Tracker: Robust Brightfield Particle Tracking for Microscopy},
  year         = {2026},
  url          = {https://github.com/YOUR_USERNAME/BF-Particle-Tracker}
}
