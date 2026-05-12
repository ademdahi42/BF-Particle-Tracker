import numpy as np
from scipy.ndimage import binary_fill_holes, gaussian_filter

try:
    import trackpy as tp
except Exception:
    tp = None

try:
    from skimage.exposure import equalize_adapthist
except Exception:
    equalize_adapthist = None

try:
    from skimage.filters import threshold_otsu
    from skimage.measure import label, regionprops
    from skimage.morphology import (
        binary_closing,
        binary_opening,
        disk,
        remove_small_holes,
        remove_small_objects,
    )
except Exception:
    threshold_otsu = None
    label = None
    regionprops = None
    binary_closing = None
    binary_opening = None
    disk = None
    remove_small_holes = None
    remove_small_objects = None


def normalize01(image):
    image = np.asarray(image, dtype=np.float32)
    image = image - np.nanmin(image)
    max_value = np.nanmax(image)
    if max_value <= 1e-8:
        return np.zeros_like(image, dtype=np.float32)
    return (image / max_value).astype(np.float32)


def to_grayscale(frame):
    frame = np.asarray(frame, dtype=np.float32)

    if frame.ndim == 2:
        return frame

    if frame.ndim == 3 and frame.shape[-1] in (3, 4):
        return (
            0.2126 * frame[..., 0]
            + 0.7152 * frame[..., 1]
            + 0.0722 * frame[..., 2]
        ).astype(np.float32)

    raise ValueError(f"Unsupported frame shape: {frame.shape}")


def percentile_normalize(image, low, high):
    low_value = np.percentile(image, low)
    high_value = np.percentile(image, high)

    if high_value <= low_value:
        return normalize01(image)

    image = np.clip(image, low_value, high_value)
    image = (image - low_value) / (high_value - low_value + 1e-8)
    return image.astype(np.float32)


def fast_tophat(image, radius):
    """Fast top-hat-like background removal for interactive GUI use."""
    sigma = max(1.0, float(radius) / 3.0)
    background = gaussian_filter(image, sigma=sigma)
    return normalize01(image - background)


def preprocess_frame(frame, params):
    """Apply the visible preprocessing pipeline and return a float32 image in [0, 1]."""
    if params.get("convert_to_grayscale", True):
        image = to_grayscale(frame)
    else:
        image = np.asarray(frame, dtype=np.float32)
        if image.ndim == 3:
            image = image[..., 0]

    image = normalize01(image)

    if params.get("background_correction", False):
        background = gaussian_filter(
            image,
            sigma=float(params.get("background_sigma", 60.0)),
        )
        method = params.get("background_method", "subtract")
        if method == "divide":
            image = image / (background + 1e-8)
        else:
            image = image - background
        image = normalize01(image)

    if params.get("gaussian_smoothing", False):
        image = gaussian_filter(
            image,
            sigma=float(params.get("gaussian_sigma", 1.0)),
        )

    if params.get("tophat", False):
        radius = max(1, int(params.get("tophat_radius", 80)))
        image = fast_tophat(image, radius)

    if params.get("invert_image", False):
        image = 1.0 - normalize01(image)

    if params.get("percentile_normalization", True):
        image = percentile_normalize(
            image,
            float(params.get("percentile_low", 1.0)),
            float(params.get("percentile_high", 99.0)),
        )
    else:
        image = normalize01(image)

    if params.get("gamma_correction", False):
        gamma = max(1e-6, float(params.get("gamma_value", 0.7)))
        image = np.power(normalize01(image), gamma)

    if params.get("clahe", False):
        if equalize_adapthist is None:
            raise RuntimeError("CLAHE requires skimage.exposure.equalize_adapthist.")
        image = equalize_adapthist(
            normalize01(image),
            clip_limit=float(params.get("clahe_clip_limit", 0.01)),
        )

    return normalize01(image).astype(np.float32)


def draw_blob_overlay(enhanced_binary, x, y, radius):
    display = np.stack(
        [enhanced_binary.astype(np.float32)] * 3,
        axis=-1,
    )

    yy, xx = np.indices(enhanced_binary.shape)
    # Draw the centroid as a cross so it remains readable on filled blobs.
    cross_half_length = 7.0
    cross_half_width = 1.0
    center_mask = (np.abs(xx - x) <= cross_half_width) & (np.abs(yy - y) <= cross_half_length)
    center_mask |= (np.abs(yy - y) <= cross_half_width) & (np.abs(xx - x) <= cross_half_length)
    circle_mask = np.abs(np.sqrt((xx - x) ** 2 + (yy - y) ** 2) - radius) <= 1.5

    display[center_mask | circle_mask, 0] = 0.35
    display[center_mask | circle_mask, 1] = 0.67
    display[center_mask | circle_mask, 2] = 1.0
    return display.astype(np.float32)


def empty_enhanced_debug(binary, reason):
    empty = np.zeros_like(binary, dtype=np.float32)
    return {
        "enhanced_binary": empty,
        "enhanced_display": np.stack([empty, empty, empty], axis=-1),
        "blob_centroid_x": np.nan,
        "blob_centroid_y": np.nan,
        "blob_radius": np.nan,
        "blob_area": 0.0,
        "blob_eccentricity": np.nan,
        "selected_region": None,
        "reason": reason,
    }


def enhance_binary_image(binary, params):
    """Clean a binary mask and keep a single region with regionprops metadata."""
    if regionprops is None:
        raise RuntimeError("Binary enhancement requires scikit-image measure/morphology.")

    enhanced = np.asarray(binary, dtype=bool)
    min_size = max(1, int(params.get("binary_min_object_size", 200)))
    hole_area = max(0, int(params.get("binary_hole_area", 200)))
    opening_radius = max(0, int(params.get("binary_opening_radius", 1)))
    closing_radius = max(0, int(params.get("binary_closing_radius", 3)))

    enhanced = remove_small_objects(enhanced, min_size=min_size)

    if hole_area > 0:
        enhanced = remove_small_holes(enhanced, area_threshold=hole_area)

    if opening_radius > 0:
        enhanced = binary_opening(enhanced, footprint=disk(opening_radius))

    if closing_radius > 0:
        enhanced = binary_closing(enhanced, footprint=disk(closing_radius))

    if params.get("fill_binary_holes", True):
        enhanced = binary_fill_holes(enhanced)

    labeled = label(enhanced)
    regions = regionprops(labeled)

    if len(regions) == 0:
        return empty_enhanced_debug(enhanced, "no_blob_found")

    selected = max(regions, key=lambda region: region.area)

    if params.get("keep_largest_blob_only", True):
        enhanced = labeled == selected.label
        labeled = label(enhanced)
        selected = regionprops(labeled)[0]

    y, x = selected.centroid
    radius = float(selected.equivalent_diameter / 2.0)
    enhanced_binary = enhanced.astype(np.float32)
    enhanced_display = draw_blob_overlay(enhanced_binary, float(x), float(y), radius)

    return {
        "enhanced_binary": enhanced_binary,
        "enhanced_display": enhanced_display,
        "blob_centroid_x": float(x),
        "blob_centroid_y": float(y),
        "blob_radius": radius,
        "blob_area": float(selected.area),
        "blob_eccentricity": float(selected.eccentricity),
        "blob_equivalent_diameter": float(selected.equivalent_diameter),
        "blob_major_axis_length": float(selected.major_axis_length),
        "blob_minor_axis_length": float(selected.minor_axis_length),
        "blob_bbox": tuple(int(v) for v in selected.bbox),
        "selected_region": selected,
        "reason": "ok",
    }


def compute_stiffness_equipartition(x_px, pixel_size_um, temperature_K):
    mad_threshold = 3.0
    x_px = np.asarray(x_px, dtype=float)
    x_px = x_px[np.isfinite(x_px)]

    if len(x_px) < 50:
        return {
            "kx_pN_per_um": np.nan,
            "sigma_um": np.nan,
            "n_points": int(len(x_px)),
            "warning": "not enough data",
        }

    x_um = x_px * float(pixel_size_um)
    t = np.arange(len(x_um), dtype=float)
    p = np.polyfit(t, x_um, 1)
    drift = np.polyval(p, t)

    residuals = x_um - drift
    centered_residuals = residuals - np.median(residuals)
    mad = np.median(np.abs(centered_residuals))
    robust_sigma = 1.4826 * mad
    n_outliers_mad = 0

    if robust_sigma > 0 and np.isfinite(robust_sigma):
        keep = np.abs(centered_residuals) <= mad_threshold * robust_sigma
        n_outliers_mad = int(np.count_nonzero(~keep))
        x_um = x_um[keep]

    if len(x_um) < 50:
        return {
            "kx_pN_per_um": np.nan,
            "sigma_um": np.nan,
            "n_points": int(len(x_um)),
            "n_outliers_mad": n_outliers_mad,
            "warning": "not enough data after MAD filter",
        }

    t = np.arange(len(x_um), dtype=float)
    p = np.polyfit(t, x_um, 1)
    drift = np.polyval(p, t)
    x_detrended = x_um - drift
    x_centered = x_detrended - np.mean(x_detrended)
    var_x = float(np.var(x_centered, ddof=1))

    if var_x <= 0 or not np.isfinite(var_x):
        return {
            "kx_pN_per_um": np.nan,
            "sigma_um": np.nan,
            "n_points": int(len(x_centered)),
            "n_outliers_mad": n_outliers_mad,
            "warning": "invalid variance",
        }

    kB = 1.380649e-23
    kBT_pN_um = kB * float(temperature_K) * 1e18
    kx = float(kBT_pN_um / var_x)
    sigma = float(np.sqrt(var_x))

    print("Var(x) =", var_x)
    print("Sigma =", sigma)
    print("kx =", kx)
    print("MAD outliers =", n_outliers_mad)

    return {
        "kx_pN_per_um": kx,
        "sigma_um": sigma,
        "n_points": int(len(x_centered)),
        "n_outliers_mad": n_outliers_mad,
        "warning": None,
    }


def preprocess_blob_image(frame, params, prediction=None):
    """ImageJ-like binary blob pipeline: top-hat, threshold, morphology, regionprops."""
    if threshold_otsu is None or regionprops is None:
        raise RuntimeError("Blob preprocessing requires scikit-image filters/measure/morphology.")

    image = normalize01(to_grayscale(frame))

    if params.get("blob_invert_before_tophat", False):
        image = 1.0 - image

    radius = max(1, int(params.get("blob_tophat_radius", 80)))
    preprocessed = fast_tophat(image, radius)

    preprocessed = percentile_normalize(
        preprocessed,
        float(params.get("percentile_low", 1.0)),
        float(params.get("percentile_high", 99.0)),
    )

    threshold_method = params.get("threshold_method", "otsu")
    if threshold_method == "manual":
        threshold_value = float(params.get("blob_threshold_manual", 0.5))
    else:
        threshold_value = float(threshold_otsu(preprocessed))

    binary = preprocessed >= threshold_value

    min_area = max(1, int(params.get("min_area", 20)))
    max_area = float(params.get("max_area", 1e9))
    opening_radius = max(0, int(params.get("opening_radius", 0)))
    closing_radius = max(0, int(params.get("closing_radius", 0)))
    holes_area = max(0, int(params.get("remove_small_holes_area", 0)))

    binary = remove_small_objects(binary, min_size=min_area)

    if opening_radius > 0:
        binary = binary_opening(binary, footprint=disk(opening_radius))

    if closing_radius > 0:
        binary = binary_closing(binary, footprint=disk(closing_radius))

    if holes_area > 0:
        binary = remove_small_holes(binary, area_threshold=holes_area)

    enhanced_debug = enhance_binary_image(binary, params)
    enhanced_binary = enhanced_debug["enhanced_binary"].astype(bool)

    labeled = label(enhanced_binary)
    regions = regionprops(labeled, intensity_image=preprocessed)
    regions = [region for region in regions if min_area <= region.area <= max_area]

    if len(regions) == 0:
        debug = {
            "preprocessed": preprocessed.astype(np.float32),
            "binary": binary.astype(np.float32),
            "enhanced_binary": enhanced_debug["enhanced_binary"],
            "enhanced_display": enhanced_debug["enhanced_display"],
            "labeled": labeled,
            "selected_region": None,
            "threshold_value": threshold_value,
            **{
                key: value
                for key, value in enhanced_debug.items()
                if key.startswith("blob_")
            },
            "reason": enhanced_debug.get("reason", "no_blob_region"),
        }
        return None, debug

    if (
        prediction is not None
        and params.get("blob_choose_by_prediction", True)
        and "x" in prediction
        and "y" in prediction
    ):
        selected = min(
            regions,
            key=lambda region: (
                (region.centroid[1] - float(prediction["x"])) ** 2
                + (region.centroid[0] - float(prediction["y"])) ** 2
            ),
        )
    else:
        expected_area = np.pi * (float(params.get("detect_diameter", 91)) / 2.0) ** 2

        def region_score(region):
            area_error = abs(float(region.area) - expected_area) / max(expected_area, 1.0)
            return float(region.area) - 0.25 * expected_area * area_error

        selected = max(regions, key=region_score)

    y, x = selected.centroid
    result = {
        "x": float(x),
        "y": float(y),
        "radius": float(selected.equivalent_diameter / 2.0),
        "area": float(selected.area),
        "eccentricity": float(selected.eccentricity),
        "major_axis_length": float(selected.major_axis_length),
        "minor_axis_length": float(selected.minor_axis_length),
        "bbox": tuple(int(v) for v in selected.bbox),
        "method": "blob_binary_regionprops",
        "accepted": True,
        "reason": "ok",
        "quality_score": float(selected.area),
    }

    debug = {
        "preprocessed": preprocessed.astype(np.float32),
        "binary": binary.astype(np.float32),
        "enhanced_binary": enhanced_debug["enhanced_binary"],
        "enhanced_display": enhanced_debug["enhanced_display"],
        "labeled": labeled,
        "selected_region": selected,
        "threshold_value": threshold_value,
        "blob_centroid_x": float(x),
        "blob_centroid_y": float(y),
        "blob_radius": float(selected.equivalent_diameter / 2.0),
        "blob_area": float(selected.area),
        "blob_eccentricity": float(selected.eccentricity),
        "reason": "ok",
    }
    return result, debug


def detect_particle_trackpy(frame, params, prediction=None):
    """Detect one particle with Trackpy only, useful as a simple tracking baseline."""
    if tp is None:
        return None, {
            "preprocessed": normalize01(to_grayscale(frame)),
            "binary": np.zeros_like(to_grayscale(frame), dtype=np.float32),
            "enhanced_display": np.zeros((*to_grayscale(frame).shape, 3), dtype=np.float32),
            "reason": "trackpy_not_available",
        }

    image = preprocess_frame(frame, params)
    diameter = max(3, int(round(float(params.get("detect_diameter", 91)))))
    if diameter % 2 == 0:
        diameter += 1

    try:
        features = tp.locate(
            image,
            diameter=diameter,
            minmass=float(params.get("trackpy_minmass", 0.0)),
            percentile=float(params.get("trackpy_percentile", 64.0)),
        )
    except Exception as exc:
        return None, {
            "preprocessed": image,
            "binary": np.zeros_like(image, dtype=np.float32),
            "enhanced_display": np.zeros((*image.shape, 3), dtype=np.float32),
            "reason": f"trackpy_error_{exc}",
        }

    if features is None or len(features) == 0:
        return None, {
            "preprocessed": image,
            "binary": np.zeros_like(image, dtype=np.float32),
            "enhanced_display": np.zeros((*image.shape, 3), dtype=np.float32),
            "reason": "no_trackpy_feature",
        }

    if (
        prediction is not None
        and "x" in prediction
        and "y" in prediction
    ):
        dx = features["x"].to_numpy(dtype=float) - float(prediction["x"])
        dy = features["y"].to_numpy(dtype=float) - float(prediction["y"])
        selected = features.iloc[int(np.argmin(dx * dx + dy * dy))]
    elif "mass" in features:
        selected = features.sort_values("mass", ascending=False).iloc[0]
    else:
        selected = features.iloc[0]

    x = float(selected["x"])
    y = float(selected["y"])
    radius = float(diameter / 2.0)
    mass = float(selected["mass"]) if "mass" in selected else np.nan

    result = {
        "x": x,
        "y": y,
        "radius": radius,
        "area": np.nan,
        "eccentricity": np.nan,
        "major_axis_length": np.nan,
        "minor_axis_length": np.nan,
        "bbox": (),
        "method": "trackpy_only",
        "accepted": True,
        "reason": "ok",
        "quality_score": mass if np.isfinite(mass) else 1.0,
        "trackpy_mass": mass,
        "trackpy_size": float(selected["size"]) if "size" in selected else np.nan,
        "trackpy_ecc": float(selected["ecc"]) if "ecc" in selected else np.nan,
        "trackpy_signal": float(selected["signal"]) if "signal" in selected else np.nan,
    }

    debug = {
        "preprocessed": image.astype(np.float32),
        "binary": np.zeros_like(image, dtype=np.float32),
        "enhanced_display": draw_blob_overlay(
            np.zeros_like(image, dtype=np.float32),
            x,
            y,
            radius,
        ),
        "selected_region": None,
        "threshold_value": np.nan,
        "reason": "ok",
    }
    return result, debug
