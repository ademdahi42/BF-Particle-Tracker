from datetime import datetime
from pathlib import Path
import html
import textwrap

from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "documentation"
ASSETS = DOCS / "assets"
FIGURE_SRC = Path(r"C:\Users\ademd\Documents\Figures Article OT\Figure 2 Tracking")

IMAGE_SOURCES = [
    FIGURE_SRC / "Microscope_1.tif",
    FIGURE_SRC / "Microscope_2.tif",
    FIGURE_SRC / "Microscope_3.tif",
    FIGURE_SRC / "Microscope_4.tif",
    FIGURE_SRC / "Microscope_5.tif",
]
IMAGE_NAMES = [
    "raw_image.png",
    "preprocessed_image.png",
    "binary_image.png",
    "enhanced_binary_image.png",
    "tracking_overlay.png",
]
IMAGE_LABELS = [
    "Raw image",
    "Preprocessed image",
    "Binary image",
    "Enhanced binary image",
    "Tracking overlay",
]

TITLE = "BF-Particle-Tracker"
SUBTITLE = "User guide and image-processing workflow"
DATE_TEXT = datetime.now().strftime("%Y-%m-%d")


SECTIONS = [
    {
        "title": "Overview",
        "body": [
            "This software analyzes microscopy TIFF and OME-TIFF videos of a single particle. It displays the raw frame and each processing stage, detects a binary blob, tracks the blob centroid over time, and exports the trajectory with the experimental metadata needed for later comparison.",
            "The detection workflow is intentionally transparent: preprocessing, thresholding, binary cleanup, region measurement, then frame-to-frame tracking. Each processing view is visible so the user can tune the result before committing to a tracking run.",
        ],
    },
    {
        "title": "Typical workflow",
        "bullets": [
            "Load one or several TIFF/OME-TIFF files. Split acquisitions can be combined into one continuous stack.",
            "Move through the stack with the frame slider and inspect the raw image.",
            "Adjust preprocessing while comparing the raw, preprocessed, binary, and enhanced binary panels.",
            "Run detection on the current frame and set it as the initial reference.",
            "Start tracking, monitor the overlay and plots, then stop if the detection becomes unstable.",
            "Save CSV measurements, JSON metadata, and optional diagnostic images.",
        ],
    },
    {
        "title": "Image-processing steps",
        "terms": [
            ("Raw image", "The selected frame is read from the TIFF stack. If a processing square is enabled, only that crop is passed to the image-processing and tracking pipeline."),
            ("Preprocessing", "Intensity operations improve contrast between the particle and the background. Available operations include grayscale conversion, background correction, smoothing, top-hat filtering, inversion, percentile normalization, gamma correction, and CLAHE."),
            ("Binary segmentation", "The preprocessed image is thresholded. Otsu mode estimates the cutoff automatically; manual mode lets the user choose the cutoff directly."),
            ("Morphological cleanup", "Small particles, holes, and rough boundaries are cleaned using object-size filtering, opening, closing, and hole filling."),
            ("Blob measurement", "Connected regions are measured with region properties. The selected blob provides the centroid, equivalent radius, area, eccentricity, and axis lengths."),
            ("Tracking", "The previous particle position guides the next frame. The trajectory is stored in absolute and relative coordinates, with the initial detection as the reference point."),
        ],
    },
    {
        "title": "Acquisition and calibration",
        "terms": [
            ("Particle ID", "A sample identifier saved with the results. It helps link trajectories to materials, particles, or experimental conditions."),
            ("Particle diameter", "Physical diameter used to convert pixels into micrometers from the detected radius. Changing it rescales positions, radius, sigma, and stiffness outputs."),
            ("Frame interval", "Time between frames. It defines the time axis in exported data and time-series plots."),
            ("Temperature", "Used in the equipartition stiffness calculation through kBT. Higher temperature increases the reported stiffness for the same positional variance."),
            ("Frames to track", "Controls how much of the stack is processed. Longer tracks improve statistics but take more time and are more sensitive to drift or loss of detection."),
            ("Wavenumber, power, note", "Experimental metadata saved in the JSON file. These fields do not change the detection, but they make later comparison between experiments easier."),
        ],
    },
    {
        "title": "Import and processing region",
        "terms": [
            ("Fast lazy import", "Opens large stacks quickly by reading frames only when needed. This makes browsing faster; tracking can still preload the selected frame range for speed."),
            ("Multiple-file import", "Combines split files into a single virtual video when frame dimensions match. This is useful when microscope acquisitions are saved in parts."),
            ("Processing square", "Restricts computation to a square crop. This can speed up analysis and reduce false detections from distant artifacts."),
            ("Square position and size", "Moving the square changes the region analyzed. A smaller square is faster and cleaner, but must remain large enough to contain the particle throughout tracking."),
        ],
    },
    {
        "title": "Preprocessing controls",
        "terms": [
            ("Convert to grayscale", "Uses a single intensity channel for processing. Keep enabled for most bright-field or grayscale microscopy data."),
            ("Background correction", "Removes slow illumination variation. Subtraction highlights local contrast; division compensates shading and uneven illumination."),
            ("Background sigma", "Sets the spatial scale of the estimated background. A larger scale preserves broad particle features; a smaller scale removes more local structure."),
            ("Gaussian smoothing", "Suppresses high-frequency noise before segmentation. Too much smoothing can soften the particle edge."),
            ("Top-hat", "Enhances local objects relative to background. The radius controls the size of features treated as background."),
            ("Invert image", "Swaps dark and bright features. Use when the particle becomes easier to segment after contrast inversion."),
            ("Percentile normalization", "Clips extreme intensities before rescaling. This stabilizes contrast, but very strong clipping can saturate useful detail."),
            ("Gamma correction", "Changes mid-tone contrast. Lower gamma brightens weak structures; higher gamma emphasizes strong bright regions."),
            ("CLAHE", "Applies local adaptive contrast enhancement. It can reveal weak particles, but excessive local contrast may amplify noise."),
        ],
    },
    {
        "title": "Blob and binary controls",
        "terms": [
            ("Blob top-hat radius", "Controls background removal in the blob-specific pipeline. It changes how strongly the particle is isolated before thresholding."),
            ("Invert before top-hat", "Useful when the particle is dark in the raw image but should become bright for segmentation."),
            ("Threshold method", "Otsu is automatic and convenient; manual mode is useful when background, halos, or noise confuse the automatic threshold."),
            ("Manual threshold", "Foreground cutoff used in manual mode. Raising it keeps stronger pixels only; lowering it includes weaker signal and possibly noise."),
            ("Area limits", "Reject objects that are too small or too large. This helps remove dust, fragments, merged blobs, or background artifacts."),
            ("Opening radius", "Removes small protrusions and isolated pixels. Too much opening can erode the particle."),
            ("Closing radius", "Fills small gaps and smooths boundaries. Too much closing can merge nearby regions."),
            ("Hole filling", "Fills internal holes to create a more compact blob, often closer to a disk-like particle."),
            ("Choose by prediction", "During tracking, selects the region nearest to the previous position instead of relying only on size."),
        ],
    },
    {
        "title": "Tracking, plots, and exports",
        "terms": [
            ("Initial detection", "Defines the reference point. Relative x and y trajectories are computed from this initial validated position."),
            ("Maximum displacement", "Rejects jumps that are too far from the previous accepted position. Lower values are stricter; higher values tolerate faster motion."),
            ("Keep radius constant", "Stabilizes the pixel-to-micrometer calibration by avoiding frame-to-frame radius fluctuations."),
            ("Overlay", "Draws the detected center, radius, and trajectory on the image. This is a visual check and does not change the calculations."),
            ("Histograms and time traces", "Show relative x, y, radius, and temporal behavior. They help reveal drift, segmentation failures, and sudden jumps."),
            ("Stiffness estimate", "Computed after tracking from the variance of the detrended relative x trajectory using the equipartition relation."),
            ("CSV export", "Stores frame-by-frame measurements: time, absolute and relative position, radius, detection status, quality, and method."),
            ("JSON export", "Stores metadata and the current settings at save time, so the file reflects the parameters used for interpretation."),
        ],
    },
]

HTML_CSS = """
:root { --ink:#202632; --muted:#667085; --line:#d7dde8; --accent:#1f77b4; --soft:#f5f8fc; }
* { box-sizing:border-box; }
body { margin:0; color:var(--ink); background:white; font-family:Arial, Helvetica, sans-serif; line-height:1.55; }
.hero { padding:44px 56px 34px; border-bottom:1px solid var(--line); background:#f7f9fc; }
.hero h1 { margin:0 0 8px; font-size:34px; letter-spacing:-0.02em; }
.hero p { margin:0; color:var(--muted); font-size:16px; }
.container { max-width:1120px; margin:0 auto; padding:34px 42px 70px; }
.intro { border-left:4px solid var(--accent); background:var(--soft); padding:14px 16px; margin-bottom:24px; }
.stage-grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:12px; margin:24px 0 34px; }
.stage { border:1px solid var(--line); padding:8px; background:#fff; }
.stage img { width:100%; display:block; }
.stage span { display:block; margin-top:7px; color:var(--muted); font-size:12px; }
section { margin:34px 0; }
h2 { font-size:21px; margin:0 0 12px; padding-bottom:7px; border-bottom:1px solid var(--line); }
p { margin:9px 0; }
ul { margin:10px 0 0 22px; padding:0; }
li { margin:6px 0; }
.term { display:grid; grid-template-columns:230px 1fr; gap:18px; padding:10px 0; border-bottom:1px solid #edf1f6; }
.term b { color:#101828; }
.footer { margin-top:42px; color:var(--muted); font-size:12px; border-top:1px solid var(--line); padding-top:16px; }
@media (max-width:900px) { .stage-grid { grid-template-columns:1fr 1fr; } .term { grid-template-columns:1fr; gap:3px; } .container { padding:24px; } }
"""


def convert_images():
    ASSETS.mkdir(parents=True, exist_ok=True)
    paths = []
    for src, name in zip(IMAGE_SOURCES, IMAGE_NAMES):
        out = ASSETS / name
        with Image.open(src) as image:
            image.convert("RGB").save(out)
        paths.append(out)
    return paths


def html_terms(terms):
    return "\n".join(
        f"<div class='term'><b>{html.escape(name)}</b><span>{html.escape(desc)}</span></div>"
        for name, desc in terms
    )


def build_html(image_paths):
    stage_cards = "\n".join(
        f"<div class='stage'><img src='assets/{path.name}' alt='{html.escape(label)}'><span>{html.escape(label)}</span></div>"
        for path, label in zip(image_paths, IMAGE_LABELS)
    )
    sections = []
    for section in SECTIONS:
        parts = [f"<section><h2>{html.escape(section['title'])}</h2>"]
        for paragraph in section.get("body", []):
            parts.append(f"<p>{html.escape(paragraph)}</p>")
        if "bullets" in section:
            parts.append("<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in section["bullets"]) + "</ul>")
        if "terms" in section:
            parts.append(html_terms(section["terms"]))
        parts.append("</section>")
        sections.append("\n".join(parts))

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE} - User Documentation</title>
<style>{HTML_CSS}</style>
</head>
<body>
<header class="hero">
  <h1>{TITLE}</h1>
  <p>{SUBTITLE} &middot; Generated {DATE_TEXT}</p>
</header>
<main class="container">
  <div class="intro">Use this guide as a practical map of the interface. Each section explains what the controls do and how changing them affects the analysis.</div>
  <div class="stage-grid">{stage_cards}</div>
  {''.join(sections)}
  <div class="footer">BF-Particle-Tracker documentation. Keep this file together with the <code>assets</code> folder.</div>
</main>
</body>
</html>
"""
    out = DOCS / "Particle_Tracking_User_Documentation.html"
    out.write_text(doc, encoding="utf-8")
    return out


def wrap(text, chars):
    return textwrap.wrap(text, width=chars)


def add_header(fig, title, subtitle=None):
    fig.text(0.07, 0.955, title, fontsize=18, fontweight="bold", ha="left", va="top", color="#202632")
    if subtitle:
        fig.text(0.07, 0.928, subtitle, fontsize=8.5, ha="left", va="top", color="#667085")
    fig.add_artist(Rectangle((0.07, 0.905), 0.86, 0.002, transform=fig.transFigure, color="#1f77b4", lw=0))


def add_footer(fig, page):
    fig.text(0.07, 0.04, "BF-Particle-Tracker", fontsize=7.5, color="#667085", ha="left")
    fig.text(0.93, 0.04, str(page), fontsize=7.5, color="#667085", ha="right")


def add_card(ax, x, y, w, h, title, body, accent="#1f77b4"):
    ax.add_patch(Rectangle((x, y - h), w, h, facecolor="#ffffff", edgecolor="#d7dde8", lw=0.8))
    ax.add_patch(Rectangle((x, y - 0.018), w, 0.018, facecolor=accent, edgecolor=accent, lw=0))
    ax.text(x + 0.018, y - 0.033, title, fontsize=8.8, fontweight="bold", va="top", ha="left", color="#202632")
    text_y = y - 0.063
    for line in wrap(body, 47):
        ax.text(x + 0.018, text_y, line, fontsize=7.3, va="top", ha="left", color="#344054")
        text_y -= 0.021


def add_workflow_card(ax, x, y, w, h, number, title, body):
    ax.add_patch(Rectangle((x, y - h), w, h, facecolor="#ffffff", edgecolor="#d7dde8", lw=0.8))
    ax.add_patch(Rectangle((x, y - 0.014), 0.014, 0.014, facecolor="#1f77b4", edgecolor="#1f77b4", lw=0))
    ax.text(x + 0.026, y - 0.028, f"{number}. {title}", fontsize=8.0, fontweight="bold", va="top", ha="left", color="#202632")
    text_y = y - 0.058
    for line in wrap(body, 40):
        ax.text(x + 0.026, text_y, line, fontsize=6.9, va="top", ha="left", color="#344054")
        text_y -= 0.020


def page_cover(pdf, image_paths):
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
    add_header(fig, TITLE, f"{SUBTITLE} | Generated {DATE_TEXT}")
    ax = fig.add_axes([0.07, 0.08, 0.86, 0.80])
    ax.axis("off")
    ax.text(
        0.0,
        0.98,
        "A practical guide for loading microscopy videos, tuning visible preprocessing, tracking a particle centroid, and exporting trajectory data with metadata.",
        fontsize=10.5,
        va="top",
        ha="left",
        color="#344054",
        wrap=True,
    )

    # Five-stage visual workflow.
    x0, y0, w, h, gap = 0.0, 0.78, 0.18, 0.18, 0.025
    for i, (path, label) in enumerate(zip(image_paths, IMAGE_LABELS)):
        iax = ax.inset_axes([x0 + i * (w + gap), y0 - h, w, h])
        iax.imshow(Image.open(path))
        iax.set_xticks([])
        iax.set_yticks([])
        for spine in iax.spines.values():
            spine.set_color("#202632")
            spine.set_linewidth(0.8)
        ax.text(x0 + i * (w + gap), y0 - h - 0.025, label, fontsize=7.2, color="#667085", ha="left", va="top")

    ax.text(0.0, 0.48, "Core workflow", fontsize=12, fontweight="bold", ha="left", va="top", color="#202632")
    workflow = [
        (
            "Load video stack",
            "Open one TIFF/OME-TIFF file or combine split files into a single continuous stack.",
        ),
        (
            "Tune preprocessing",
            "Use the four image panels to adjust contrast, background correction, and threshold behavior.",
        ),
        (
            "Segment binary blob",
            "Clean the binary mask until the selected region represents the particle rather than noise.",
        ),
        (
            "Validate initial detection",
            "Choose a reliable frame and set its centroid as the zero-reference for relative motion.",
        ),
        (
            "Track trajectory",
            "Process the selected frame range while checking the overlay, speed, and rejection status.",
        ),
        (
            "Export results",
            "Save frame-by-frame measurements in CSV and the current experiment settings in JSON.",
        ),
    ]
    for i, (item, body) in enumerate(workflow):
        x = (i % 3) * 0.32
        y = 0.40 - (i // 3) * 0.14
        add_workflow_card(ax, x, y, 0.29, 0.115, i + 1, item, body)

    add_footer(fig, 1)
    pdf.savefig(fig)
    plt.close(fig)


def page_processing(pdf):
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
    add_header(fig, "Image-processing pipeline", "From raw frame to cleaned binary region")
    ax = fig.add_axes([0.07, 0.075, 0.86, 0.80])
    ax.axis("off")
    terms = SECTIONS[2]["terms"]
    positions = [(0.0, 0.95), (0.52, 0.95), (0.0, 0.68), (0.52, 0.68), (0.0, 0.41), (0.52, 0.41)]
    for (title, body), (x, y) in zip(terms, positions):
        add_card(ax, x, y, 0.45, 0.20, title, body)
    add_footer(fig, 2)
    pdf.savefig(fig)
    plt.close(fig)


def page_terms(pdf, page, title, subtitle, terms):
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
    add_header(fig, title, subtitle)
    ax = fig.add_axes([0.07, 0.075, 0.86, 0.80])
    ax.axis("off")
    columns = [0.0, 0.52]
    y_positions = [0.95, 0.95]
    col_width = 0.45
    row_h = 0.15
    for i, (name, desc) in enumerate(terms):
        col = i % 2
        if y_positions[col] - row_h < 0.02:
            break
        add_card(ax, columns[col], y_positions[col], col_width, row_h, name, desc)
        y_positions[col] -= row_h + 0.025
    add_footer(fig, page)
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf(image_paths):
    out = DOCS / "Particle_Tracking_User_Documentation.pdf"
    with PdfPages(out) as pdf:
        page_cover(pdf, image_paths)
        page_processing(pdf)
        page_terms(pdf, 3, "Acquisition and import controls", "Metadata, calibration, loading, and processing region", SECTIONS[3]["terms"] + SECTIONS[4]["terms"])
        page_terms(pdf, 4, "Preprocessing controls", "How each image-enhancement control affects segmentation", SECTIONS[5]["terms"])
        page_terms(pdf, 5, "Blob, binary, and tracking controls", "Segmentation cleanup, temporal tracking, plots, and exports", SECTIONS[6]["terms"] + SECTIONS[7]["terms"])
    return out


README_TEXT = """# BF-Particle-Tracker

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
.venv_app\\Scripts\\python.exe main.py
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
"""


def main():
    DOCS.mkdir(exist_ok=True)
    image_paths = convert_images()
    html_path = build_html(image_paths)
    pdf_path = build_pdf(image_paths)
    readme_path = DOCS / "README.md"
    readme_path.write_text(README_TEXT, encoding="utf-8")
    print(f"HTML: {html_path}")
    print(f"PDF:  {pdf_path}")
    print(f"README: {readme_path}")


if __name__ == "__main__":
    main()
