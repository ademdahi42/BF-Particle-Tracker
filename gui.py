import csv
import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import dearpygui.dearpygui as dpg
import numpy as np
import tifffile

try:
    import cv2
except Exception:
    cv2 = None

from processing import (
    compute_stiffness_equipartition,
    preprocess_blob_image,
    preprocess_frame,
)


APP_DIR = Path(__file__).resolve().parent
APP_ICON_PATH = APP_DIR / "assets" / "app_icon.ico"

selected_file = None
video_stack = None
current_frame = None
current_preprocessed = None
current_binary = None
current_enhanced_binary = None
current_blob_result = None
current_blob_debug = None
initial_detection = None
initial_frame_index = 0
tracking_records = []
tracking_stop_requested = False
tracking_is_running = False
video_generation = 0
square_selection_active = False
square_preview_visible = False
main_view_mode = "overlay"
display_cache = {}
playback_active = False
last_kde_update_time = 0.0

RAW_TEXTURE_TAG = "raw_frame_texture"
PREPROCESSED_TEXTURE_TAG = "preprocessed_frame_texture"
BINARY_TEXTURE_TAG = "binary_frame_texture"
ENHANCED_BINARY_TEXTURE_TAG = "enhanced_binary_frame_texture"
MAIN_TEXTURE_TAG = "main_view_texture"
RAW_IMAGE_TAG = "raw_frame_image"
PREPROCESSED_IMAGE_TAG = "preprocessed_frame_image"
BINARY_IMAGE_TAG = "binary_frame_image"
ENHANCED_BINARY_IMAGE_TAG = "enhanced_binary_frame_image"
MAIN_IMAGE_TAG = "main_view_image"
KDE_COLORMAP_TAG = "kde_scientific_blue"

INPUT_WIDTH = 95
TEXT_INPUT_WIDTH = 220
PARAMETER_PANEL_WIDTH = 230
MIN_WINDOW_WIDTH = 1050
PANEL_GAP = 18
IMAGE_DISPLAY_WIDTH = 280
IMAGE_DISPLAY_HEIGHT = 180
USER_SETTINGS_PATH = Path(__file__).with_name("app_user_settings.json")

# Dashboard style tokens. Change colors and sizing here when refreshing the UI.
COLOR_BG = (18, 21, 27, 255)
COLOR_PANEL = (29, 34, 43, 255)
COLOR_PANEL_SOFT = (36, 43, 54, 255)
COLOR_TEXT = (236, 240, 245, 255)
COLOR_TEXT_MUTED = (162, 172, 186, 255)
COLOR_ACCENT = (55, 145, 255, 255)
COLOR_ACCENT_HOVER = (82, 164, 255, 255)
COLOR_SUCCESS = (65, 190, 135, 255)
COLOR_WARNING = (230, 170, 70, 255)
COLOR_ERROR = (235, 95, 95, 255)
CARD_PAD = 12
ITEM_SPACING = 9
TITLE_FONT_SIZE = 19
BODY_FONT_SIZE = 16

THEME_PRIMARY_BUTTON = "theme_primary_button"
THEME_SECONDARY_BUTTON = "theme_secondary_button"
THEME_DANGER_BUTTON = "theme_danger_button"
THEME_SUCCESS_TEXT = "theme_success_text"
THEME_WARNING_TEXT = "theme_warning_text"
THEME_ERROR_TEXT = "theme_error_text"
THEME_MUTED_TEXT = "theme_muted_text"
TITLE_FONT_TAG = "title_font"
BODY_FONT_TAG = "body_font"


def load_user_settings():
    try:
        with open(USER_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


user_settings = load_user_settings()


def setting_default(tag, fallback):
    return user_settings.get(tag, fallback)


def save_user_settings():
    tags = [
        "particle_id_input",
        "particle_diameter_um_input",
        "dt_ms_input",
        "temperature_k_input",
        "lazy_import_mode_input",
        "process_all_frames_input",
        "n_frames_to_process_input",
        "wavenumber_input",
        "power_input",
        "note_input",
        "save_folder_input",
        "save_base_name_input",
        "use_processing_square_input",
        "square_x_input",
        "square_y_input",
        "square_size_input",
        "convert_to_grayscale_input",
        "background_correction_input",
        "background_sigma_input",
        "background_method_input",
        "gaussian_smoothing_input",
        "gaussian_sigma_input",
        "tophat_input",
        "tophat_radius_input",
        "invert_image_input",
        "percentile_normalization_input",
        "percentile_low_input",
        "percentile_high_input",
        "gamma_correction_input",
        "gamma_value_input",
        "clahe_input",
        "clahe_clip_limit_input",
        "auto_update_preprocessing_input",
        "show_detection_overlay_input",
        "use_blob_detection_input",
        "blob_tophat_radius_input",
        "blob_invert_before_tophat_input",
        "threshold_method_input",
        "blob_threshold_manual_input",
        "min_area_input",
        "max_area_input",
        "opening_radius_input",
        "closing_radius_input",
        "remove_small_holes_area_input",
        "blob_choose_by_prediction_input",
        "detect_diameter_input",
        "binary_min_object_size_input",
        "binary_hole_area_input",
        "binary_opening_radius_input",
        "binary_closing_radius_input",
        "fill_binary_holes_input",
        "keep_largest_blob_only_input",
        "keep_radius_constant_input",
        "max_displacement_px_input",
    ]
    settings = {}
    for tag in tags:
        if dpg.does_item_exist(tag):
            settings[tag] = dpg.get_value(tag)

    tmp_path = USER_SETTINGS_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    tmp_path.replace(USER_SETTINGS_PATH)


def set_status(message, level="info"):
    if dpg.does_item_exist("status_text"):
        dpg.set_value("status_text", message)
        if level == "error" and dpg.does_item_exist(THEME_ERROR_TEXT):
            dpg.bind_item_theme("status_text", THEME_ERROR_TEXT)
        elif level == "warning" and dpg.does_item_exist(THEME_WARNING_TEXT):
            dpg.bind_item_theme("status_text", THEME_WARNING_TEXT)
        elif level == "success" and dpg.does_item_exist(THEME_SUCCESS_TEXT):
            dpg.bind_item_theme("status_text", THEME_SUCCESS_TEXT)
        elif dpg.does_item_exist(THEME_MUTED_TEXT):
            dpg.bind_item_theme("status_text", THEME_MUTED_TEXT)


def native_open_video_dialog():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select video file",
        filetypes=[
            ("TIFF files", "*.ome.tif *.ome.tiff *.tif *.tiff"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return path


def native_open_multiple_video_dialog():
    root = tk.Tk()
    root.withdraw()
    paths = filedialog.askopenfilenames(
        title="Select video files to combine",
        filetypes=[
            ("TIFF files", "*.ome.tif *.ome.tiff *.tif *.tiff"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return list(paths)


def native_choose_output_folder():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askdirectory(title="Select output folder")
    root.destroy()
    return path


def format_duration(seconds):
    if seconds is None or not np.isfinite(seconds):
        return "--:--"
    seconds = max(0, int(round(seconds)))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def update_tracking_metrics(processed_frames, total_frames, start_time):
    elapsed = max(time.perf_counter() - start_time, 1e-9)
    fps = processed_frames / elapsed if processed_frames > 0 else 0.0
    remaining = max(total_frames - processed_frames, 0)
    eta_s = remaining / fps if fps > 0 else np.nan
    if dpg.does_item_exist("tracking_metrics_text"):
        dpg.set_value(
            "tracking_metrics_text",
            f"Frames: {processed_frames}/{total_frames} | {fps:.2f} frames/s | remaining: {format_duration(eta_s)}",
        )


def normalize_image(image):
    image = np.asarray(image, dtype=np.float32)
    image = image - np.nanmin(image)
    max_value = np.nanmax(image)
    if max_value <= 1e-8:
        return np.zeros_like(image, dtype=np.float32)
    return image / max_value


def image_to_rgba(image):
    image = np.asarray(image, dtype=np.float32)

    if image.ndim == 2:
        image = normalize_image(image)
        rgb = np.stack([image, image, image], axis=-1)
    elif image.ndim == 3 and image.shape[-1] >= 3:
        rgb = normalize_image(image[..., :3])
    else:
        raise ValueError(f"Unsupported frame shape: {image.shape}")

    alpha = np.ones((rgb.shape[0], rgb.shape[1], 1), dtype=np.float32)
    return np.concatenate([rgb.astype(np.float32), alpha], axis=-1)


def draw_detection_overlay(image, result):
    rgba = image_to_rgba(image)

    if result is None:
        return rgba

    x = result.get("x", np.nan)
    y = result.get("y", np.nan)
    radius = result.get("radius", np.nan)

    if not (np.isfinite(x) and np.isfinite(y) and np.isfinite(radius)):
        return rgba

    if cv2 is None:
        height, width = rgba.shape[:2]
        yy, xx = np.indices((height, width))
        circle_mask = np.abs(np.sqrt((xx - x) ** 2 + (yy - y) ** 2) - radius) <= 1.2
        cross_mask = (np.abs(xx - x) <= 0.8) & (np.abs(yy - y) <= 6)
        cross_mask |= (np.abs(yy - y) <= 0.8) & (np.abs(xx - x) <= 6)
        rgba[circle_mask, :3] = (0.35, 0.67, 1.0)
        rgba[cross_mask, :3] = (0.25, 0.65, 1.0)
        return rgba.astype(np.float32)

    base = np.clip(rgba[..., :3] * 255.0, 0, 255).astype(np.uint8)
    overlay = base.copy()
    center = (int(round(x)), int(round(y)))
    radius_i = max(1, int(round(radius)))
    overlay_blue = (65, 165, 255)
    cv2.circle(overlay, center, radius_i, overlay_blue, 2, lineType=cv2.LINE_AA)
    cross = 7
    cv2.line(overlay, (center[0] - cross, center[1]), (center[0] + cross, center[1]), overlay_blue, 1, lineType=cv2.LINE_AA)
    cv2.line(overlay, (center[0], center[1] - cross), (center[0], center[1] + cross), overlay_blue, 1, lineType=cv2.LINE_AA)
    blended = cv2.addWeighted(overlay, 0.58, base, 0.42, 0)
    rgba[..., :3] = blended.astype(np.float32) / 255.0
    return rgba.astype(np.float32)


def draw_trajectory_overlay(image, result=None, records=None, show_detection=True):
    rgba = draw_detection_overlay(image, result) if show_detection else image_to_rgba(image)

    if not records or len(records) < 2:
        return rgba

    height, width = rgba.shape[:2]
    valid_records = [
        record for record in records
        if record is not None
        and np.isfinite(record.get("x", np.nan))
        and np.isfinite(record.get("y", np.nan))
    ]

    if len(valid_records) < 2:
        return rgba

    if cv2 is not None:
        base = np.clip(rgba[..., :3] * 255.0, 0, 255).astype(np.uint8)
        trail = base.copy()
        n_records = max(1, len(valid_records) - 1)
        for index, record in enumerate(valid_records):
            x = int(round(float(record["x"])))
            y = int(round(float(record["y"])))
            alpha = 0.12 + 0.58 * (index / n_records)
            color = (65, 165, 255)
            point_layer = trail.copy()
            cv2.circle(point_layer, (x, y), 2, color, -1, lineType=cv2.LINE_AA)
            trail = cv2.addWeighted(point_layer, alpha, trail, 1.0 - alpha, 0)
        rgba[..., :3] = trail.astype(np.float32) / 255.0
    else:
        n_records = max(1, len(valid_records) - 1)
        for index, record in enumerate(valid_records):
            x = int(np.clip(round(float(record["x"])), 0, width - 1))
            y = int(np.clip(round(float(record["y"])), 0, height - 1))
            alpha = 0.12 + 0.58 * (index / n_records)
            color = np.array([0.25, 0.65, 1.0], dtype=np.float32)
            rgba[y, x, :3] = alpha * color + (1.0 - alpha) * rgba[y, x, :3]

    return rgba.astype(np.float32)


def coerce_tiff_to_frame_stack(array, axes=None):
    array = np.asarray(array)

    if axes is not None and len(axes) != array.ndim:
        axes = None

    if axes is not None:
        axes = list(axes.upper())

        for axis_index in range(array.ndim - 1, -1, -1):
            if array.shape[axis_index] == 1 and axes[axis_index] not in ("Y", "X"):
                array = np.squeeze(array, axis=axis_index)
                axes.pop(axis_index)

        if "Y" in axes and "X" in axes:
            y_axis = axes.index("Y")
            x_axis = axes.index("X")
            channel_axis = None

            for candidate_axis, candidate_label in enumerate(axes):
                if candidate_label in ("C", "S") and array.shape[candidate_axis] in (3, 4):
                    channel_axis = candidate_axis
                    break

            image_axes = [y_axis, x_axis]
            if channel_axis is not None:
                image_axes.append(channel_axis)

            frame_axes = [i for i in range(array.ndim) if i not in image_axes]
            ordered_axes = frame_axes + image_axes
            array = np.transpose(array, ordered_axes)

            image_dims = len(image_axes)
            frame_shape = array.shape[-image_dims:]
            frame_count = int(np.prod(array.shape[:-image_dims])) if array.ndim > image_dims else 1
            return array.reshape((frame_count, *frame_shape))

    array = np.squeeze(array)

    if array.ndim == 2:
        return array[np.newaxis, ...]

    if array.ndim == 3:
        if array.shape[-1] in (3, 4):
            return array[np.newaxis, ...]
        return array

    if array.ndim >= 4 and array.shape[-1] in (3, 4):
        frame_shape = array.shape[-3:]
        frame_count = int(np.prod(array.shape[:-3]))
        return array.reshape((frame_count, *frame_shape))

    if array.ndim >= 4:
        frame_shape = array.shape[-2:]
        frame_count = int(np.prod(array.shape[:-2]))
        return array.reshape((frame_count, *frame_shape))

    raise ValueError(f"Unsupported TIFF shape: {array.shape}")


def load_tiff_video_stack(path):
    first_error = None

    with tifffile.TiffFile(path) as tif:
        try:
            series = tif.series[0]
            axes = getattr(series, "axes", None)
            array = series.asarray()
            return coerce_tiff_to_frame_stack(array, axes)
        except Exception as exc:
            first_error = exc

        try:
            array = tif.asarray()
            return coerce_tiff_to_frame_stack(array, None)
        except Exception as exc:
            raise ValueError(f"{first_error}; fallback failed: {exc}") from exc


class LazyTiffVideoStack:
    """Virtual TIFF stack: fast open, frame-by-frame reads, optional RAM preload."""

    def __init__(self, paths):
        if not paths:
            raise ValueError("No files selected.")

        self.sources = []
        self.shape = None
        frame_shape = None
        total_frames = 0

        try:
            for path in paths:
                source = self._open_source(path)
                if frame_shape is None:
                    frame_shape = source["frame_shape"]
                elif source["frame_shape"] != frame_shape:
                    raise ValueError(
                        (
                            "Selected files do not have the same frame shape. "
                            f"Expected {frame_shape}, got {source['frame_shape']} for {Path(path).name}."
                        )
                    )
                source["start"] = total_frames
                total_frames += source["n_frames"]
                source["stop"] = total_frames
                self.sources.append(source)
        except Exception:
            self.close()
            raise

        self.shape = (total_frames, *frame_shape)

    def _open_source(self, path):
        tif = tifffile.TiffFile(path)
        try:
            series = tif.series[0]
            pages = series.pages
            if len(pages) > 1:
                first_frame = pages[0].asarray()
                return {
                    "path": path,
                    "tif": tif,
                    "series": series,
                    "pages": pages,
                    "array": None,
                    "n_frames": len(pages),
                    "frame_shape": np.asarray(first_frame).shape,
                }

            # Some TIFFs store the whole stack in one page. Fallback remains
            # functional, but that specific file cannot be opened lazily.
            array = load_tiff_video_stack(path)
            return {
                "path": path,
                "tif": tif,
                "series": series,
                "pages": None,
                "array": array,
                "n_frames": len(array),
                "frame_shape": array.shape[1:],
            }
        except Exception:
            tif.close()
            raise

    def __len__(self):
        return int(self.shape[0])

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            if step != 1:
                return np.stack([self[i] for i in range(start, stop, step)], axis=0)
            return self.preload_range(start, stop)

        index = int(index)
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError(index)

        for source in self.sources:
            if source["start"] <= index < source["stop"]:
                local_index = index - source["start"]
                if source["array"] is not None:
                    return source["array"][local_index]
                return source["pages"][local_index].asarray()

        raise IndexError(index)

    def preload_range(self, start, stop):
        start = max(0, int(start))
        stop = min(len(self), int(stop))
        if stop <= start:
            return np.empty((0, *self.shape[1:]), dtype=np.float32)
        return np.stack([self[i] for i in range(start, stop)], axis=0)

    def close(self):
        for source in getattr(self, "sources", []):
            try:
                source["tif"].close()
            except Exception:
                pass


def open_video_stack_with_mode(paths, use_lazy_import=True):
    if use_lazy_import:
        try:
            return LazyTiffVideoStack(paths), "lazy"
        except Exception as exc:
            print(f"Lazy TIFF loading failed, falling back to full load: {exc}")
            return load_and_combine_tiff_video_stacks(paths), "full_fallback"

    return load_and_combine_tiff_video_stacks(paths), "full"


def close_loaded_video_stack():
    global video_stack
    if hasattr(video_stack, "close"):
        try:
            video_stack.close()
        except Exception:
            pass


def get_video_frame(frame_index):
    return video_stack[int(frame_index)]


def preload_video_range(start, stop):
    if hasattr(video_stack, "preload_range"):
        return video_stack.preload_range(start, stop)
    return np.asarray(video_stack[start:stop])


def load_and_combine_tiff_video_stacks(paths):
    if not paths:
        raise ValueError("No files selected.")

    stacks = []
    frame_shape = None

    for path in paths:
        stack = load_tiff_video_stack(path)
        if frame_shape is None:
            frame_shape = stack.shape[1:]
        elif stack.shape[1:] != frame_shape:
            raise ValueError(
                (
                    "Selected files do not have the same frame shape. "
                    f"Expected {frame_shape}, got {stack.shape[1:]} for {Path(path).name}."
                )
            )
        stacks.append(stack)

    if len(stacks) == 1:
        return stacks[0]

    return np.concatenate(stacks, axis=0)


def get_current_frame_index():
    return int(dpg.get_value("frame_slider"))


def get_preprocessing_parameters():
    return {
        "convert_to_grayscale": dpg.get_value("convert_to_grayscale_input"),
        "background_correction": dpg.get_value("background_correction_input"),
        "background_sigma": dpg.get_value("background_sigma_input"),
        "background_method": dpg.get_value("background_method_input"),
        "gaussian_smoothing": dpg.get_value("gaussian_smoothing_input"),
        "gaussian_sigma": dpg.get_value("gaussian_sigma_input"),
        "tophat": dpg.get_value("tophat_input"),
        "tophat_radius": dpg.get_value("tophat_radius_input"),
        "invert_image": dpg.get_value("invert_image_input"),
        "percentile_normalization": dpg.get_value("percentile_normalization_input"),
        "percentile_low": dpg.get_value("percentile_low_input"),
        "percentile_high": dpg.get_value("percentile_high_input"),
        "gamma_correction": dpg.get_value("gamma_correction_input"),
        "gamma_value": dpg.get_value("gamma_value_input"),
        "clahe": dpg.get_value("clahe_input"),
        "clahe_clip_limit": dpg.get_value("clahe_clip_limit_input"),
        "show_detection_overlay": dpg.get_value("show_detection_overlay_input"),
        "use_blob_detection": dpg.get_value("use_blob_detection_input"),
        "blob_tophat_radius": dpg.get_value("blob_tophat_radius_input"),
        "blob_invert_before_tophat": dpg.get_value("blob_invert_before_tophat_input"),
        "threshold_method": dpg.get_value("threshold_method_input"),
        "blob_threshold_manual": dpg.get_value("blob_threshold_manual_input"),
        "min_area": dpg.get_value("min_area_input"),
        "max_area": dpg.get_value("max_area_input"),
        "opening_radius": dpg.get_value("opening_radius_input"),
        "closing_radius": dpg.get_value("closing_radius_input"),
        "remove_small_holes_area": dpg.get_value("remove_small_holes_area_input"),
        "blob_choose_by_prediction": dpg.get_value("blob_choose_by_prediction_input"),
        "detect_diameter": dpg.get_value("detect_diameter_input"),
        "binary_min_object_size": dpg.get_value("binary_min_object_size_input"),
        "binary_hole_area": dpg.get_value("binary_hole_area_input"),
        "binary_opening_radius": dpg.get_value("binary_opening_radius_input"),
        "binary_closing_radius": dpg.get_value("binary_closing_radius_input"),
        "fill_binary_holes": dpg.get_value("fill_binary_holes_input"),
        "keep_largest_blob_only": dpg.get_value("keep_largest_blob_only_input"),
        "particle_id": dpg.get_value("particle_id_input"),
        "particle_diameter_um": dpg.get_value("particle_diameter_um_input"),
        "dt_ms": dpg.get_value("dt_ms_input"),
        "dt": dpg.get_value("dt_ms_input") / 1000.0,
        "temperature_k": dpg.get_value("temperature_k_input"),
        "process_all_frames": dpg.get_value("process_all_frames_input"),
        "n_frames_to_process": dpg.get_value("n_frames_to_process_input"),
        "wavenumber_cm1": dpg.get_value("wavenumber_input"),
        "power_mw": dpg.get_value("power_input"),
        "note": dpg.get_value("note_input"),
        "save_folder": dpg.get_value("save_folder_input"),
        "save_base_name": dpg.get_value("save_base_name_input"),
        "use_processing_square": dpg.get_value("use_processing_square_input"),
        "square_x": dpg.get_value("square_x_input"),
        "square_y": dpg.get_value("square_y_input"),
        "square_size": dpg.get_value("square_size_input"),
        "max_displacement_px": dpg.get_value("max_displacement_px_input"),
        "keep_radius_constant": dpg.get_value("keep_radius_constant_input"),
    }


def get_acquisition_calibration_parameters():
    return {
        "particle_id": dpg.get_value("particle_id_input"),
        "particle_diameter_um": dpg.get_value("particle_diameter_um_input"),
        "dt_ms": dpg.get_value("dt_ms_input"),
        "dt": dpg.get_value("dt_ms_input") / 1000.0,
        "temperature_k": dpg.get_value("temperature_k_input"),
        "process_all_frames": dpg.get_value("process_all_frames_input"),
        "n_frames_to_process": dpg.get_value("n_frames_to_process_input"),
        "wavenumber_cm1": dpg.get_value("wavenumber_input"),
        "power_mw": dpg.get_value("power_input"),
        "note": dpg.get_value("note_input"),
    }


def get_processing_square_from_params(frame, params):
    if frame is None or not params.get("use_processing_square", False):
        return None

    return get_square_from_params(frame, params)


def get_square_from_params(frame, params):
    if frame is None:
        return None

    height, width = np.asarray(frame).shape[:2]
    size = int(params.get("square_size", min(width, height)))
    size = max(1, min(size, width, height))
    x = int(params.get("square_x", 0))
    y = int(params.get("square_y", 0))

    x = max(0, min(x, width - size))
    y = max(0, min(y, height - size))
    return {"x": x, "y": y, "size": size, "width": size, "height": size}


def crop_frame_with_processing_square(frame, params):
    square = get_processing_square_from_params(frame, params)
    if square is None:
        return frame, None
    y0 = square["y"]
    y1 = square["y"] + square["size"]
    x0 = square["x"]
    x1 = square["x"] + square["size"]
    return np.asarray(frame)[y0:y1, x0:x1, ...], square


def display_frame_result_records(frame, result=None, records=None, params=None):
    if params is None:
        params = get_preprocessing_parameters()
    display_frame, square = crop_frame_with_processing_square(frame, params)
    return display_frame, result, records, square


def update_texture(texture_tag, image):
    if np.asarray(image).ndim == 3 and np.asarray(image).shape[-1] == 4:
        rgba = np.asarray(image, dtype=np.float32)
    else:
        rgba = image_to_rgba(image)
    height, width = rgba.shape[:2]
    display_cache[texture_tag] = rgba

    image_tags = {
        RAW_TEXTURE_TAG: RAW_IMAGE_TAG,
        PREPROCESSED_TEXTURE_TAG: PREPROCESSED_IMAGE_TAG,
        BINARY_TEXTURE_TAG: BINARY_IMAGE_TAG,
        ENHANCED_BINARY_TEXTURE_TAG: ENHANCED_BINARY_IMAGE_TAG,
    }
    parent_tags = {
        RAW_TEXTURE_TAG: "raw_image_panel",
        PREPROCESSED_TEXTURE_TAG: "preprocessed_image_panel",
        BINARY_TEXTURE_TAG: "binary_image_panel",
        ENHANCED_BINARY_TEXTURE_TAG: "enhanced_binary_image_panel",
    }
    image_tag = image_tags[texture_tag]
    parent_tag = parent_tags[texture_tag]

    # DearPyGUI textures have fixed dimensions. Recreate the image item first so
    # the old texture is no longer referenced when loading a new video size.
    if dpg.does_item_exist(image_tag):
        dpg.delete_item(image_tag)

    if dpg.does_item_exist(texture_tag):
        dpg.delete_item(texture_tag)

    dpg.add_dynamic_texture(
        width,
        height,
        rgba.ravel(),
        tag=texture_tag,
        parent="texture_registry",
    )

    if dpg.does_item_exist(parent_tag):
        scale = min(
            IMAGE_DISPLAY_WIDTH / max(width, 1),
            IMAGE_DISPLAY_HEIGHT / max(height, 1),
        )
        display_width = max(1, int(width * scale))
        display_height = max(1, int(height * scale))
        dpg.add_image(
            texture_tag,
            tag=image_tag,
            parent=parent_tag,
            width=display_width,
            height=display_height,
        )
    update_main_view_from_cache()


def main_view_texture_for_mode(mode=None):
    mode = mode or main_view_mode
    return {
        "overlay": RAW_TEXTURE_TAG,
        "raw": RAW_TEXTURE_TAG,
        "preprocessed": PREPROCESSED_TEXTURE_TAG,
        "binary": BINARY_TEXTURE_TAG,
        "enhanced": ENHANCED_BINARY_TEXTURE_TAG,
    }.get(mode, RAW_TEXTURE_TAG)


def update_main_view_from_cache():
    source_tag = main_view_texture_for_mode()
    rgba = display_cache.get(source_tag)
    if rgba is None or not dpg.does_item_exist("main_image_panel"):
        return

    height, width = rgba.shape[:2]
    if dpg.does_item_exist(MAIN_IMAGE_TAG):
        dpg.delete_item(MAIN_IMAGE_TAG)
    if dpg.does_item_exist(MAIN_TEXTURE_TAG):
        dpg.delete_item(MAIN_TEXTURE_TAG)

    dpg.add_dynamic_texture(width, height, rgba.ravel(), tag=MAIN_TEXTURE_TAG, parent="texture_registry")
    panel_width = max(300, dpg.get_item_width("main_image_panel") - 20)
    panel_height = max(260, dpg.get_item_height("main_image_panel") - 20)
    scale = min(panel_width / max(width, 1), panel_height / max(height, 1))
    dpg.add_image(
        MAIN_TEXTURE_TAG,
        tag=MAIN_IMAGE_TAG,
        parent="main_image_panel",
        width=max(1, int(width * scale)),
        height=max(1, int(height * scale)),
    )


def set_main_view_callback(sender=None, app_data=None, user_data=None):
    global main_view_mode
    main_view_mode = user_data or "overlay"
    if dpg.does_item_exist("main_view_text"):
        dpg.set_value("main_view_text", f"Current view: {main_view_mode.title()}")
    update_main_view_from_cache()


def debug_view_callback(sender=None, app_data=None):
    if dpg.does_item_exist("debug_grid_group"):
        dpg.configure_item("debug_grid_group", show=bool(app_data))


def refresh_raw_image():
    if current_frame is None:
        return
    params = get_preprocessing_parameters()
    display_frame, display_result, display_records, square = display_frame_result_records(
        current_frame,
        current_blob_result,
        tracking_records,
        params,
    )
    raw_display = draw_trajectory_overlay(
        display_frame,
        display_result,
        display_records,
        show_detection=params.get("show_detection_overlay", True),
    )
    if square_preview_visible and not params.get("use_processing_square", False):
        preview_square = get_square_from_params(current_frame, params)
        raw_display = draw_square_preview_overlay(raw_display, preview_square)
    update_texture(
        RAW_TEXTURE_TAG,
        raw_display,
    )


def apply_preprocessing_callback(sender=None, app_data=None):
    global current_preprocessed, current_binary, current_enhanced_binary
    global current_blob_result, current_blob_debug

    if current_frame is None:
        set_status("Load a video first.")
        return

    try:
        params = get_preprocessing_parameters()
        processing_frame, square = crop_frame_with_processing_square(current_frame, params)
        current_blob_result = None
        current_blob_debug = None
        current_binary = np.zeros_like(np.asarray(processing_frame)[..., 0] if np.asarray(processing_frame).ndim == 3 else processing_frame, dtype=np.float32)
        current_enhanced_binary = np.zeros_like(current_binary, dtype=np.float32)

        if params.get("use_blob_detection", False):
            current_blob_result, current_blob_debug = preprocess_blob_image(processing_frame, params)
            if current_blob_result is not None and square is not None:
                current_blob_result["square_x"] = square["x"]
                current_blob_result["square_y"] = square["y"]
                current_blob_result["square_size"] = square["size"]
            current_preprocessed = current_blob_debug["preprocessed"]
            current_binary = current_blob_debug["binary"]
            current_enhanced_binary = (
                current_blob_debug["enhanced_display"]
                if params.get("show_detection_overlay", True)
                else current_blob_debug["enhanced_binary"]
            )
        else:
            current_preprocessed = preprocess_frame(processing_frame, params)

        update_texture(
            RAW_TEXTURE_TAG,
            draw_trajectory_overlay(
                processing_frame,
                current_blob_result,
                tracking_records,
                show_detection=params.get("show_detection_overlay", True),
            ),
        )
        preprocessed_display = (
            draw_detection_overlay(current_preprocessed, current_blob_result)
            if params.get("show_detection_overlay", True)
            else current_preprocessed
        )
        update_texture(PREPROCESSED_TEXTURE_TAG, preprocessed_display)
        update_texture(BINARY_TEXTURE_TAG, current_binary)
        update_texture(ENHANCED_BINARY_TEXTURE_TAG, current_enhanced_binary)

        if current_blob_result is not None:
            set_status(
                (
                    "Blob detected | "
                    f"x={current_blob_result['x']:.2f}, "
                    f"y={current_blob_result['y']:.2f}, "
                    f"r={current_blob_result['radius']:.2f}, "
                    f"area={current_blob_result['area']:.0f}, "
                    f"ecc={current_blob_result['eccentricity']:.3f}"
                    + (f" | square x={square['x']} y={square['y']} size={square['size']}" if square else "")
                )
            )
        elif params.get("use_blob_detection", False):
            reason = current_blob_debug.get("reason", "unknown") if current_blob_debug else "unknown"
            set_status("No blob found in enhanced binary image" if reason == "no_blob_found" else f"Blob detection: no region selected. Reason: {reason}")
        else:
            set_status("Preprocessing applied.")
    except Exception as exc:
        set_status(f"Preprocessing error: {exc}")


def detect_blob_on_frame(frame, params, prediction=None):
    processing_frame, square = crop_frame_with_processing_square(frame, params)
    result, debug = preprocess_blob_image(processing_frame, params, prediction=prediction)
    if result is None:
        return None, debug
    if square is not None:
        result["square_x"] = square["x"]
        result["square_y"] = square["y"]
        result["square_size"] = square["size"]
    result["method"] = "blob_binary_regionprops"
    result["quality_score"] = result.get("area", 0.0)
    result["accepted"] = True
    return result, debug


def run_single_detection_callback():
    global current_preprocessed, current_blob_result, current_blob_debug

    if current_frame is None:
        set_status("Load a video first.")
        return

    params = get_preprocessing_parameters()
    params["use_blob_detection"] = True
    result, debug = detect_blob_on_frame(current_frame, params)
    _, square = crop_frame_with_processing_square(current_frame, params)
    current_blob_result = result
    current_blob_debug = debug

    if result is None:
        current_preprocessed = debug.get("preprocessed", current_frame)
        update_texture(PREPROCESSED_TEXTURE_TAG, current_preprocessed)
        update_texture(BINARY_TEXTURE_TAG, debug.get("binary", np.zeros_like(current_preprocessed)))
        enhanced_key = "enhanced_display" if params.get("show_detection_overlay", True) else "enhanced_binary"
        update_texture(ENHANCED_BINARY_TEXTURE_TAG, debug.get(enhanced_key, np.zeros_like(current_preprocessed)))
        set_status(f"No blob found. Reason: {debug.get('reason', 'unknown')}")
        return

    dpg.set_value("use_blob_detection_input", True)
    apply_preprocessing_callback()
    set_status(
        (
            "Detection done | "
            f"x={result['x']:.2f}, y={result['y']:.2f}, "
            f"r={result['radius']:.2f}, area={result['area']:.0f}, "
            f"ecc={result['eccentricity']:.3f}"
            + (" | square-local coordinates" if square else "")
        )
    )


def set_initial_detection_callback():
    global initial_detection, initial_frame_index

    if current_blob_result is None:
        set_status("Run detection first.")
        return

    initial_detection = current_blob_result.copy()
    initial_frame_index = get_current_frame_index()
    initial_detection["x0_px"] = float(initial_detection["x"])
    initial_detection["y0_px"] = float(initial_detection["y"])
    if dpg.does_item_exist("initial_text"):
        dpg.set_value(
            "initial_text",
            (
                f"Initial detection frame {initial_frame_index} | "
                f"x0={initial_detection['x0_px']:.2f}, "
                f"y0={initial_detection['y0_px']:.2f}, "
                f"r={initial_detection['radius']:.2f}"
            ),
        )
    set_status(
        (
            "Initial blob detection set as reference. "
            f"x0={initial_detection['x0_px']:.2f}, y0={initial_detection['y0_px']:.2f}"
        )
    )


def add_relative_coordinates(result, x0_px, y0_px, pixel_size_um=np.nan):
    result["x_rel_px"] = float(result["x"] - x0_px)
    result["y_rel_px"] = float(result["y"] - y0_px)
    result["x_rel_um"] = (
        float(result["x_rel_px"] * pixel_size_um)
        if np.isfinite(pixel_size_um)
        else np.nan
    )
    result["y_rel_um"] = (
        float(result["y_rel_px"] * pixel_size_um)
        if np.isfinite(pixel_size_um)
        else np.nan
    )
    return result


def smooth_1d(values, passes=2):
    values = np.asarray(values, dtype=float)
    if len(values) < 3:
        return values
    kernel = np.array([1.0, 2.0, 1.0], dtype=float) / 4.0
    smoothed = values
    for _ in range(passes):
        smoothed = np.convolve(smoothed, kernel, mode="same")
    return smoothed


def smooth_2d(values, passes=2):
    smoothed = np.asarray(values, dtype=float)
    kernel = np.array([1.0, 2.0, 1.0], dtype=float) / 4.0
    for _ in range(passes):
        smoothed = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="same"), 0, smoothed)
        smoothed = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="same"), 1, smoothed)
    return smoothed


def density_plot_data(x_values, y_values, bins=48):
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]

    if len(x) < 3:
        return None

    mean_x = float(np.mean(x))
    mean_y = float(np.mean(y))
    std_x = float(np.std(x, ddof=1)) if len(x) > 1 else 0.0
    std_y = float(np.std(y, ddof=1)) if len(y) > 1 else 0.0

    x_min = float(np.min(x))
    x_max = float(np.max(x))
    y_min = float(np.min(y))
    y_max = float(np.max(y))
    x_padding = max((x_max - x_min) * 0.12, std_x * 0.6, 1e-3)
    y_padding = max((y_max - y_min) * 0.12, std_y * 0.6, 1e-3)
    x_range = (x_min - x_padding, x_max + x_padding)
    y_range = (y_min - y_padding, y_max + y_padding)

    heat, x_edges, y_edges = np.histogram2d(x, y, bins=bins, range=[x_range, y_range], density=True)
    heat = smooth_2d(heat, passes=3)
    heat_values = heat.T.ravel().astype(float).tolist()

    x_hist = smooth_1d(heat.sum(axis=1), passes=3)
    y_hist = smooth_1d(heat.sum(axis=0), passes=3)
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])

    if np.nanmax(x_hist) > 0:
        x_hist = x_hist / np.nanmax(x_hist)
    if np.nanmax(y_hist) > 0:
        y_hist = y_hist / np.nanmax(y_hist)

    return {
        "heat_values": heat_values,
        "rows": bins,
        "cols": bins,
        "x_min": x_range[0],
        "x_max": x_range[1],
        "y_min": y_range[0],
        "y_max": y_range[1],
        "scale_max": float(np.nanmax(heat)) if np.isfinite(np.nanmax(heat)) else 1.0,
        "x_centers": x_centers.tolist(),
        "x_density": x_hist.tolist(),
        "y_centers": y_centers.tolist(),
        "y_density": y_hist.tolist(),
        "mean_x": mean_x,
        "mean_y": mean_y,
        "std_x": std_x,
        "std_y": std_y,
        "n": int(len(x)),
    }


def set_series_value(tag, x_values, y_values):
    if dpg.does_item_exist(tag):
        dpg.set_value(tag, [list(x_values), list(y_values)])


def update_density_plot(x_values, y_values, bins=48):
    data = density_plot_data(x_values, y_values, bins=bins)
    if data is None:
        return None

    if dpg.does_item_exist("kde_heat_series"):
        dpg.delete_item("kde_heat_series")
    dpg.add_heat_series(
        data["heat_values"],
        data["rows"],
        data["cols"],
        tag="kde_heat_series",
        parent="kde_y_axis",
        before="kde_mean_x_line" if dpg.does_item_exist("kde_mean_x_line") else 0,
        scale_min=0.0,
        scale_max=max(data["scale_max"], 1e-12),
        bounds_min=(data["x_min"], data["y_min"]),
        bounds_max=(data["x_max"], data["y_max"]),
        format="",
    )
    dpg.bind_colormap("kde_joint_plot", KDE_COLORMAP_TAG)

    set_series_value("kde_x_marginal_series", data["x_centers"], data["x_density"])
    set_series_value("kde_y_marginal_series", data["y_density"], data["y_centers"])

    x_min, x_max = data["x_min"], data["x_max"]
    y_min, y_max = data["y_min"], data["y_max"]
    mean_x, mean_y = data["mean_x"], data["mean_y"]
    std_x, std_y = data["std_x"], data["std_y"]

    set_series_value("kde_mean_x_line", [mean_x, mean_x], [y_min, y_max])
    set_series_value("kde_mean_y_line", [x_min, x_max], [mean_y, mean_y])
    set_series_value("kde_minus_sigma_x_line", [mean_x - std_x, mean_x - std_x], [y_min, y_max])
    set_series_value("kde_plus_sigma_x_line", [mean_x + std_x, mean_x + std_x], [y_min, y_max])
    set_series_value("kde_minus_sigma_y_line", [x_min, x_max], [mean_y - std_y, mean_y - std_y])
    set_series_value("kde_plus_sigma_y_line", [x_min, x_max], [mean_y + std_y, mean_y + std_y])
    set_series_value("kde_mean_point", [mean_x], [mean_y])

    dpg.configure_item("kde_colorbar", min_scale=0.0, max_scale=max(data["scale_max"], 1e-12))
    for axis in ("kde_x_axis", "kde_y_axis", "kde_top_x_axis", "kde_top_y_axis", "kde_right_x_axis", "kde_right_y_axis"):
        if dpg.does_item_exist(axis):
            dpg.fit_axis_data(axis)

    return data


def clear_analysis_plots():
    empty = [[], []]
    for tag in [
        "kde_x_marginal_series", "kde_y_marginal_series",
        "kde_mean_x_line", "kde_mean_y_line",
        "kde_minus_sigma_x_line", "kde_plus_sigma_x_line",
        "kde_minus_sigma_y_line", "kde_plus_sigma_y_line",
        "kde_mean_point",
    ]:
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, empty)
    if dpg.does_item_exist("kde_heat_series"):
        dpg.delete_item("kde_heat_series")

    if dpg.does_item_exist("stats_text"):
        dpg.set_value("stats_text", "N = 0 | sigma x/y/r = not calculated")
    if dpg.does_item_exist("kx_text"):
        dpg.set_value("kx_text", "kx = not calculated yet")
    if dpg.does_item_exist("tracking_metrics_text"):
        dpg.set_value("tracking_metrics_text", "Frames: 0/0 | 0.00 frames/s | remaining: --:--")


def compute_live_results(records, params, compute_stiffness=False):
    valid = [record for record in records if record is not None]
    if len(valid) < 3:
        return None

    radii_px = np.array([record["radius"] for record in valid], dtype=float)
    finite_radii = radii_px[np.isfinite(radii_px) & (radii_px > 0)]
    if len(finite_radii) == 0:
        return None

    stable_radius_px = np.nanmedian(finite_radii[:50])
    if not np.isfinite(stable_radius_px) or stable_radius_px <= 0:
        return None

    pixel_size_um = params["particle_diameter_um"] / (2.0 * stable_radius_px)
    t_ms = np.array([record["t_ms"] for record in valid], dtype=float)
    x_px = np.array([record["x"] for record in valid], dtype=float)
    y_px = np.array([record["y"] for record in valid], dtype=float)
    r_px = np.array([record["radius"] for record in valid], dtype=float)
    x0_px = float(valid[0].get("x0_px", valid[0]["x"]))
    y0_px = float(valid[0].get("y0_px", valid[0]["y"]))
    x_rel_px = x_px - x0_px
    y_rel_px = y_px - y0_px
    x_rel_um = x_rel_px * pixel_size_um
    y_rel_um = y_rel_px * pixel_size_um
    r_um = r_px * pixel_size_um
    if compute_stiffness:
        stiffness = compute_stiffness_equipartition(
            x_rel_px,
            pixel_size_um,
            params["temperature_k"],
        )
    else:
        stiffness = {
            "kx_pN_per_um": np.nan,
            "sigma_um": np.nan,
            "n_points": int(len(x_px)),
            "warning": "not computed yet",
        }

    return {
        "t_ms": t_ms,
        "x_rel_um": x_rel_um,
        "y_rel_um": y_rel_um,
        "r_um": r_um,
        "x0_px": x0_px,
        "y0_px": y0_px,
        "pixel_size_um": pixel_size_um,
        "stable_radius_px": stable_radius_px,
        "stiffness": stiffness,
        "kx_pn_per_um": stiffness["kx_pN_per_um"],
        "sigma_x_stiffness_um": stiffness["sigma_um"],
        "kx_n_points": stiffness["n_points"],
        "kx_n_outliers_mad": stiffness.get("n_outliers_mad", 0),
        "kx_warning": stiffness["warning"],
        "n_fallback": sum(1 for record in valid if not record.get("accepted", True)),
    }


def estimate_pixel_size_um(records, params):
    live = compute_live_results(records, params)
    if live is not None:
        return live["pixel_size_um"]

    valid_radii = [
        float(record["radius"])
        for record in records
        if record is not None and np.isfinite(record.get("radius", np.nan)) and record.get("radius", 0) > 0
    ]
    if not valid_radii:
        return np.nan
    return params["particle_diameter_um"] / (2.0 * np.nanmedian(valid_radii[:50]))


def make_histogram(values, bins=30):
    counts, edges = np.histogram(values, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    mean = float(np.mean(values)) if len(values) else 0.0
    sigma = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    return centers, counts, mean, sigma


def update_bar_series(series_tag, mean_tag, minus_sigma_tag, plus_sigma_tag, values):
    centers, counts, mean, sigma = make_histogram(values)
    y_max = max(counts) if len(counts) else 1
    dpg.set_value(series_tag, [centers.tolist(), counts.tolist()])
    dpg.set_value(mean_tag, [[mean, mean], [0, y_max]])
    dpg.set_value(minus_sigma_tag, [[mean - sigma, mean - sigma], [0, y_max]])
    dpg.set_value(plus_sigma_tag, [[mean + sigma, mean + sigma], [0, y_max]])


def update_histograms_and_curves(records, params, compute_stiffness=False, force_kde=False, live_kde=False):
    global last_kde_update_time

    live = compute_live_results(records, params, compute_stiffness=compute_stiffness)
    if live is None:
        return

    if dpg.does_item_exist("kde_plot_panel"):
        now = time.perf_counter()
        should_update_kde = force_kde or (live_kde and now - last_kde_update_time >= 0.12)
        if should_update_kde:
            update_density_plot(live["x_rel_um"], live["y_rel_um"], bins=42 if live_kde else 56)
            last_kde_update_time = now

    mean_x = float(np.nanmean(live["x_rel_um"]))
    mean_y = float(np.nanmean(live["y_rel_um"]))
    sigma_x = float(np.nanstd(live["x_rel_um"], ddof=1))
    sigma_y = float(np.nanstd(live["y_rel_um"], ddof=1))
    if dpg.does_item_exist("stats_text"):
        dpg.set_value(
            "stats_text",
            (
                f"N = {len(live['x_rel_um'])} | "
                f"mean x = {mean_x:.4g} um | std x = {sigma_x:.4g} um | "
                f"mean y = {mean_y:.4g} um | std y = {sigma_y:.4g} um"
            ),
        )

    if not compute_stiffness:
        kx_text = (
            "kx = calculated after tracking finishes | "
            f"N = {live['kx_n_points']} | "
            f"pixel size = {live['pixel_size_um']:.5f} um/px"
        )
    elif live["kx_n_points"] > 100 and live["kx_warning"] is None and np.isfinite(live["kx_pn_per_um"]):
        kx_text = (
            f"kx = {live['kx_pn_per_um']:.4g} pN/um | "
            f"sigma_x = {live['sigma_x_stiffness_um']:.4g} um | "
            f"N = {live['kx_n_points']} | "
            f"MAD outliers = {live['kx_n_outliers_mad']} | "
            f"pixel size = {live['pixel_size_um']:.5f} um/px | "
            f"stable radius = {live['stable_radius_px']:.2f} px | "
            f"fallback = {live['n_fallback']} | "
            f"reference: initial detection x0={live['x0_px']:.2f}, y0={live['y0_px']:.2f}"
        )
    else:
        kx_text = (
            "kx = Not enough data | "
            f"N = {live['kx_n_points']} | "
            f"sigma_x = {live['sigma_x_stiffness_um'] if np.isfinite(live['sigma_x_stiffness_um']) else np.nan} um | "
            f"pixel size = {live['pixel_size_um']:.5f} um/px | "
            f"reference: initial detection x0={live['x0_px']:.2f}, y0={live['y0_px']:.2f}"
        )

    dpg.set_value("kx_text", kx_text)


def make_fallback_detection(previous_result, frame_index, start, params, reason):
    fallback = previous_result.copy()
    fallback["frame"] = frame_index
    fallback["t_ms"] = (frame_index - start) * params["dt_ms"]
    fallback["accepted"] = False
    fallback["reason"] = f"fallback_previous_after_{reason}"
    fallback["quality_score"] = 0.0
    return fallback


def validate_tracking_detection(result, previous_result, params):
    if result is None:
        return False, "no_detection"
    displacement = np.hypot(result["x"] - previous_result["x"], result["y"] - previous_result["y"])
    max_displacement = float(params.get("max_displacement_px", 20.0))
    if displacement > max_displacement:
        return False, f"large_jump_{displacement:.2f}px"
    return True, "ok"


def append_tracking_result(result, frame_index, start, params, previous_result):
    result = result.copy()
    result["frame"] = frame_index
    result["t_ms"] = (frame_index - start) * params["dt_ms"]
    result["accepted"] = True
    if params.get("keep_radius_constant", True):
        result["radius"] = previous_result["radius"]
    return result


def update_relative_coordinates_for_records(records, params):
    if not records:
        return np.nan

    valid_radii = [
        float(record["radius"])
        for record in records
        if record is not None and np.isfinite(record.get("radius", np.nan)) and record.get("radius", 0) > 0
    ]
    if not valid_radii:
        return np.nan

    pixel_size_um = params["particle_diameter_um"] / (2.0 * np.nanmedian(valid_radii[:50]))
    x0_px = float(records[0].get("x0_px", records[0]["x"]))
    y0_px = float(records[0].get("y0_px", records[0]["y"]))

    for record in records:
        add_relative_coordinates(record, x0_px, y0_px, pixel_size_um)
        record["x0_px"] = x0_px
        record["y0_px"] = y0_px

    return pixel_size_um


def tracking_worker():
    global current_frame, current_blob_result, current_blob_debug, tracking_records
    global tracking_stop_requested, tracking_is_running

    if video_stack is None or initial_detection is None:
        set_status("Load a video and set an initial detection first.")
        tracking_is_running = False
        return

    params = get_preprocessing_parameters()
    params["use_blob_detection"] = True
    start = initial_frame_index
    requested = len(video_stack) - start if params.get("process_all_frames", False) else max(1, int(params["n_frames_to_process"]))
    stop = min(start + requested, len(video_stack))
    total = max(1, stop - start)
    start_time = time.perf_counter()

    tracking_records = []
    previous_result = initial_detection.copy()
    previous_result["frame"] = start
    previous_result["t_ms"] = 0.0
    previous_result["accepted"] = True
    previous_result["reason"] = "initial"
    previous_result["x0_px"] = float(initial_detection["x0_px"])
    previous_result["y0_px"] = float(initial_detection["y0_px"])
    add_relative_coordinates(previous_result, previous_result["x0_px"], previous_result["y0_px"])
    tracking_records.append(previous_result)

    dpg.configure_item("start_tracking_button", enabled=False)
    dpg.configure_item("stop_tracking_button", enabled=True)
    dpg.configure_item("save_results_button", enabled=False)
    dpg.set_value("tracking_progress", 0.0)
    dpg.configure_item("tracking_progress", overlay="0 %")
    update_tracking_metrics(1, total, start_time)
    set_status(f"Preloading frames {start} to {stop - 1} in RAM for fast tracking...")
    try:
        tracking_stack = preload_video_range(start, stop)
    except Exception as exc:
        tracking_is_running = False
        dpg.configure_item("start_tracking_button", enabled=True)
        dpg.configure_item("stop_tracking_button", enabled=False)
        dpg.configure_item("save_results_button", enabled=True)
        set_status(f"Could not preload tracking frames: {exc}")
        return

    current_frame = tracking_stack[0]
    display_frame, display_result, display_records, _ = display_frame_result_records(
        current_frame,
        current_blob_result,
        tracking_records,
        params,
    )
    update_texture(
        RAW_TEXTURE_TAG,
        draw_trajectory_overlay(
            display_frame,
            display_result,
            display_records,
            show_detection=params.get("show_detection_overlay", True),
        ),
    )

    for frame_index in range(start + 1, stop):
        if tracking_stop_requested:
            break

        frame = tracking_stack[frame_index - start]
        prediction = {
            "x": previous_result["x"],
            "y": previous_result["y"],
            "radius": previous_result["radius"],
        }
        result, debug = detect_blob_on_frame(frame, params, prediction=prediction)
        is_valid, reason = validate_tracking_detection(result, previous_result, params)

        if is_valid:
            result = append_tracking_result(result, frame_index, start, params, previous_result)
            result["reason"] = reason
            tracking_records.append(result)
            previous_result = result
            current_blob_result = result
        else:
            fallback = make_fallback_detection(previous_result, frame_index, start, params, reason)
            tracking_records.append(fallback)
            current_blob_result = fallback

        current_blob_debug = debug
        local_i = frame_index - start
        should_refresh_display = local_i % 3 == 0 or frame_index == stop - 1

        if should_refresh_display:
            update_relative_coordinates_for_records(tracking_records, params)
            current_frame = frame
            if debug is not None:
                display_frame, display_result, display_records, square = display_frame_result_records(
                    current_frame,
                    current_blob_result,
                    tracking_records,
                    params,
                )
                update_texture(
                    RAW_TEXTURE_TAG,
                    draw_trajectory_overlay(
                        display_frame,
                        display_result,
                        display_records,
                        show_detection=params.get("show_detection_overlay", True),
                    ),
                )
                preprocessed_frame = debug.get("preprocessed", display_frame)
                preprocessed_display = (
                    draw_detection_overlay(preprocessed_frame, display_result)
                    if params.get("show_detection_overlay", True)
                    else preprocessed_frame
                )
                enhanced_key = "enhanced_display" if params.get("show_detection_overlay", True) else "enhanced_binary"
                update_texture(PREPROCESSED_TEXTURE_TAG, preprocessed_display)
                update_texture(BINARY_TEXTURE_TAG, debug.get("binary", np.zeros_like(display_frame)))
                update_texture(ENHANCED_BINARY_TEXTURE_TAG, debug.get(enhanced_key, np.zeros_like(display_frame)))
            update_histograms_and_curves(tracking_records, params, compute_stiffness=False, live_kde=True)
            progress = local_i / max(total - 1, 1)
            dpg.set_value("tracking_progress", progress)
            dpg.configure_item("tracking_progress", overlay=f"{100 * progress:.1f} %")
            update_tracking_metrics(local_i + 1, total, start_time)
            set_status(f"Blob tracking frame {frame_index}/{stop - 1} | records = {len(tracking_records)} | last reason = {current_blob_result.get('reason', 'unknown')}")
            time.sleep(0.001)

    stopped = tracking_stop_requested
    tracking_stop_requested = False
    tracking_is_running = False
    dpg.configure_item("start_tracking_button", enabled=True)
    dpg.configure_item("stop_tracking_button", enabled=False)
    dpg.configure_item("save_results_button", enabled=True)
    update_relative_coordinates_for_records(tracking_records, params)
    update_histograms_and_curves(tracking_records, params, compute_stiffness=True, force_kde=True)
    if len(tracking_records) > 0 and current_frame is not None:
        display_frame, display_result, display_records, _ = display_frame_result_records(
            current_frame,
            current_blob_result,
            tracking_records,
            params,
        )
        update_texture(
            RAW_TEXTURE_TAG,
            draw_trajectory_overlay(
                display_frame,
                display_result,
                display_records,
                show_detection=params.get("show_detection_overlay", True),
            ),
        )

    if stopped:
        set_status(f"Tracking stopped | records kept = {len(tracking_records)}")
    else:
        dpg.set_value("tracking_progress", 1.0)
        dpg.configure_item("tracking_progress", overlay="100 %")
        update_tracking_metrics(total, total, start_time)
        set_status(f"Blob tracking finished | records = {len(tracking_records)}")


def start_tracking_callback():
    global current_frame, current_blob_result, current_blob_debug
    global initial_detection, initial_frame_index, tracking_is_running, tracking_stop_requested

    if tracking_is_running:
        set_status("Tracking is already running.")
        return

    if video_stack is None:
        set_status("Load a video first.", level="warning")
        return

    if initial_detection is None:
        params = get_preprocessing_parameters()
        params["use_blob_detection"] = True
        initial_frame_index = 0
        if dpg.does_item_exist("frame_slider"):
            dpg.set_value("frame_slider", 0)
        current_frame = get_video_frame(0)
        result, debug = detect_blob_on_frame(current_frame, params, prediction=None)
        if result is None:
            current_blob_debug = debug
            set_status("Could not auto-detect initial particle on frame 0.", level="error")
            return
        result = result.copy()
        result["x0_px"] = float(result["x"])
        result["y0_px"] = float(result["y"])
        initial_detection = result
        current_blob_result = result
        current_blob_debug = debug
        if dpg.does_item_exist("initial_text"):
            dpg.set_value(
                "initial_text",
                (
                    f"Initial detection frame 0 | "
                    f"x0={result['x0_px']:.2f}, "
                    f"y0={result['y0_px']:.2f}, "
                    f"r={result['radius']:.2f}"
                ),
            )
        refresh_current_frame(apply_preprocessing=True)
        set_status("Initial detection auto-set on frame 0.", level="success")

    tracking_stop_requested = False
    tracking_is_running = True
    threading.Thread(target=tracking_worker, daemon=True).start()


def stop_tracking_callback():
    global tracking_stop_requested
    tracking_stop_requested = True
    if dpg.does_item_exist("stop_tracking_button"):
        dpg.configure_item("stop_tracking_button", enabled=False)
    set_status("Stopping tracking after the current frame...")


def save_results_callback():
    if len(tracking_records) == 0:
        set_status("No tracking data to save.")
        return

    # Read all GUI parameters at save time so last-minute calibration edits are exported.
    params = get_preprocessing_parameters()
    acquisition_calibration = get_acquisition_calibration_parameters()
    params.update(acquisition_calibration)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(params["save_folder"].strip() or Path.cwd())
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = params["save_base_name"].strip() or f"tracking_{timestamp}"
    csv_path = output_dir / f"{base_name}.csv"
    json_path = output_dir / f"{base_name}.json"
    pixel_size_um = update_relative_coordinates_for_records(tracking_records, params)
    if not np.isfinite(pixel_size_um):
        pixel_size_um = estimate_pixel_size_um(tracking_records, params)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "particle_id", "frame", "time_ms", "time_s",
            "x_px", "y_px", "radius_px",
            "x_rel_px", "y_rel_px",
            "x_um", "y_um", "radius_um",
            "x_rel_um", "y_rel_um",
            "area", "eccentricity", "major_axis_length", "minor_axis_length",
            "accepted", "reason", "quality_score", "method",
        ])
        for record in tracking_records:
            frame_index = record.get("frame", "")
            if frame_index == "":
                time_ms = ""
                time_s = ""
            else:
                time_ms = (int(frame_index) - initial_frame_index) * params["dt_ms"]
                time_s = time_ms / 1000.0
            x_px = record.get("x", np.nan)
            y_px = record.get("y", np.nan)
            radius_px = record.get("radius", np.nan)
            writer.writerow([
                params["particle_id"], frame_index, time_ms, time_s,
                x_px, y_px, radius_px,
                record.get("x_rel_px", ""),
                record.get("y_rel_px", ""),
                x_px * pixel_size_um, y_px * pixel_size_um, radius_px * pixel_size_um,
                record.get("x_rel_um", ""),
                record.get("y_rel_um", ""),
                record.get("area", ""), record.get("eccentricity", ""),
                record.get("major_axis_length", ""), record.get("minor_axis_length", ""),
                record.get("accepted", ""), record.get("reason", ""),
                record.get("quality_score", ""), record.get("method", ""),
            ])

    metadata = {
        "timestamp": timestamp,
        "selected_file": selected_file,
        "output_csv": str(csv_path),
        "output_json": str(json_path),
        "processing_square": {
            "enabled": bool(params.get("use_processing_square", False)),
            "x": int(params.get("square_x", 0)),
            "y": int(params.get("square_y", 0)),
            "size": int(params.get("square_size", 0)),
            "coordinate_system": "square_local" if params.get("use_processing_square", False) else "full_frame",
        },
        "initial_frame_index": initial_frame_index,
        "pixel_size_um_per_px": pixel_size_um,
        "initial_reference": {
            "x0_px": float(initial_detection["x0_px"]) if initial_detection is not None else None,
            "y0_px": float(initial_detection["y0_px"]) if initial_detection is not None else None,
            "frame0": initial_frame_index,
        },
        "acquisition_calibration": acquisition_calibration,
        "n_records_saved": len(tracking_records),
        "parameters": params,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    set_status(f"Saved: {csv_path} and {json_path}")


def image_to_uint8_rgb(image):
    rgba = image_to_rgba(image)
    rgb = np.clip(rgba[..., :3] * 255.0, 0, 255).astype(np.uint8)
    return rgb


def save_display_image(path, image):
    rgb = image_to_uint8_rgb(image)
    if cv2 is not None:
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        if cv2.imwrite(str(path), bgr):
            return path

    fallback_path = path.with_suffix(".tif")
    tifffile.imwrite(fallback_path, rgb)
    return fallback_path


def save_images_callback():
    if current_frame is None:
        set_status("Load a video first.", level="warning")
        return

    params = get_preprocessing_parameters()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(params["save_folder"].strip() or Path.cwd())
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = params["save_base_name"].strip() or f"tracking_{timestamp}"
    frame_index = get_current_frame_index()

    processing_frame, _ = crop_frame_with_processing_square(current_frame, params)
    result = current_blob_result
    debug = current_blob_debug

    if params.get("use_blob_detection", False) and debug is None:
        result, debug = preprocess_blob_image(processing_frame, params)

    if debug is not None:
        preprocessed = debug.get("preprocessed", preprocess_frame(processing_frame, params))
        binary = debug.get("binary", np.zeros_like(preprocessed))
        enhanced = (
            debug.get("enhanced_display")
            if params.get("show_detection_overlay", True)
            else debug.get("enhanced_binary")
        )
        if enhanced is None:
            enhanced = np.zeros_like(preprocessed)
    else:
        preprocessed = current_preprocessed if current_preprocessed is not None else preprocess_frame(processing_frame, params)
        binary = current_binary if current_binary is not None else np.zeros_like(preprocessed)
        enhanced = current_enhanced_binary if current_enhanced_binary is not None else np.zeros_like(preprocessed)

    raw_display = draw_trajectory_overlay(
        processing_frame,
        result,
        tracking_records,
        show_detection=params.get("show_detection_overlay", True),
    )
    preprocessed_display = (
        draw_detection_overlay(preprocessed, result)
        if params.get("show_detection_overlay", True)
        else preprocessed
    )

    saved_paths = []
    for suffix, image in (
        ("raw", raw_display),
        ("preprocessed", preprocessed_display),
        ("binary", binary),
        ("enhanced_binary", enhanced),
    ):
        path = output_dir / f"{base_name}_frame{frame_index:04d}_{suffix}.png"
        saved_paths.append(save_display_image(path, image))

    set_status(f"Saved {len(saved_paths)} images in {output_dir}")


def auto_update_callback(sender=None, app_data=None):
    if dpg.does_item_exist("auto_update_preprocessing_input"):
        if dpg.get_value("auto_update_preprocessing_input") and current_frame is not None:
            apply_preprocessing_callback()


def refresh_current_frame(apply_preprocessing=True):
    global current_frame

    if video_stack is None:
        return

    frame_index = get_current_frame_index()
    current_frame = get_video_frame(frame_index)
    refresh_raw_image()

    dpg.set_value("frame_text", f"Current frame: {frame_index}")

    if apply_preprocessing:
        apply_preprocessing_callback()


def slider_callback(sender, app_data):
    refresh_current_frame(
        apply_preprocessing=dpg.get_value("auto_update_preprocessing_input")
    )


def previous_frame_callback():
    if not dpg.does_item_exist("frame_slider"):
        return
    value = max(0, int(dpg.get_value("frame_slider")) - 1)
    dpg.set_value("frame_slider", value)
    refresh_current_frame(apply_preprocessing=True)


def next_frame_callback():
    if not dpg.does_item_exist("frame_slider"):
        return
    max_value = len(video_stack) - 1 if video_stack is not None else 0
    value = min(max_value, int(dpg.get_value("frame_slider")) + 1)
    dpg.set_value("frame_slider", value)
    refresh_current_frame(apply_preprocessing=True)


def step_frame(delta):
    if not dpg.does_item_exist("frame_slider"):
        return
    max_value = len(video_stack) - 1 if video_stack is not None else 0
    value = min(max_value, max(0, int(dpg.get_value("frame_slider")) + int(delta)))
    dpg.set_value("frame_slider", value)
    refresh_current_frame(apply_preprocessing=True)


def step_frame_callback(sender=None, app_data=None, user_data=0):
    step_frame(user_data)


def play_pause_callback():
    global playback_active
    playback_active = not playback_active
    if dpg.does_item_exist("play_button"):
        dpg.configure_item("play_button", label="Pause" if playback_active else "Play")
    if playback_active:
        threading.Thread(target=playback_worker, daemon=True).start()


def playback_worker():
    global playback_active
    while playback_active and video_stack is not None:
        if not dpg.does_item_exist("frame_slider"):
            playback_active = False
            break
        max_value = len(video_stack) - 1
        current = int(dpg.get_value("frame_slider"))
        if current >= max_value:
            playback_active = False
            break
        step_frame(1)
        speed = dpg.get_value("playback_speed_input") if dpg.does_item_exist("playback_speed_input") else 12.0
        time.sleep(max(0.01, 1.0 / max(float(speed), 1.0)))
    if dpg.does_item_exist("play_button"):
        dpg.configure_item("play_button", label="Play")


def choose_save_folder_callback():
    path = native_choose_output_folder()
    if path:
        dpg.set_value("save_folder_input", path)


def save_defaults_callback():
    try:
        save_user_settings()
        set_status(f"Default parameters saved in {USER_SETTINGS_PATH.name}.")
    except Exception as exc:
        set_status(f"Could not save default parameters: {exc}")


def apply_processing_square_callback():
    if current_frame is None:
        set_status("Load a video first.")
        return
    configure_square_sliders_for_frame()
    dpg.set_value("use_processing_square_input", True)
    apply_preprocessing_callback()
    update_square_text(get_square_from_params(current_frame, get_preprocessing_parameters()), True)


def reset_processing_square_callback():
    global square_preview_visible
    dpg.set_value("use_processing_square_input", False)
    square_preview_visible = False
    if current_frame is not None:
        configure_square_sliders_for_frame()
        refresh_raw_image()
        if dpg.does_item_exist("square_text"):
            dpg.set_value("square_text", "Square: disabled, full frame is used")
    set_status("Processing square disabled. Processing uses the full frame.")


def start_square_selection_callback():
    global square_selection_active, square_preview_visible

    if current_frame is None:
        set_status("Load a video first.")
        return

    square_selection_active = True
    square_preview_visible = True
    dpg.set_value("use_processing_square_input", False)
    configure_square_sliders_for_frame()
    refresh_raw_image()
    set_status("Square selection active: click the particle center on the Raw image.")


def raw_image_mouse_pixel():
    if current_frame is None or not dpg.does_item_exist(RAW_IMAGE_TAG):
        return None

    rect_min = dpg.get_item_rect_min(RAW_IMAGE_TAG)
    rect_max = dpg.get_item_rect_max(RAW_IMAGE_TAG)
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    display_width = max(1.0, float(rect_max[0] - rect_min[0]))
    display_height = max(1.0, float(rect_max[1] - rect_min[1]))

    if mouse_x < rect_min[0] or mouse_x > rect_max[0] or mouse_y < rect_min[1] or mouse_y > rect_max[1]:
        return None

    frame = np.asarray(current_frame)
    height, width = frame.shape[:2]
    x = int(round((mouse_x - rect_min[0]) / display_width * (width - 1)))
    y = int(round((mouse_y - rect_min[1]) / display_height * (height - 1)))
    return max(0, min(x, width - 1)), max(0, min(y, height - 1))


def draw_square_preview_overlay(frame, square):
    rgba = image_to_rgba(frame)
    if square is None:
        return rgba

    height, width = rgba.shape[:2]
    x_min = int(square["x"])
    y_min = int(square["y"])
    size = int(square["size"])
    x_max = x_min + size - 1
    y_max = y_min + size - 1
    x_min = max(0, min(x_min, width - 1))
    x_max = max(0, min(x_max, width - 1))
    y_min = max(0, min(y_min, height - 1))
    y_max = max(0, min(y_max, height - 1))

    if cv2 is not None:
        base = np.clip(rgba[..., :3] * 255.0, 0, 255).astype(np.uint8)
        overlay = base.copy()
        cv2.rectangle(overlay, (x_min, y_min), (x_max, y_max), (255, 170, 90), 2, lineType=cv2.LINE_AA)
        fill = overlay.copy()
        cv2.rectangle(fill, (x_min, y_min), (x_max, y_max), (90, 170, 255), -1)
        overlay = cv2.addWeighted(fill, 0.12, overlay, 0.88, 0)
        blended = cv2.addWeighted(overlay, 0.62, base, 0.38, 0)
        rgba[..., :3] = blended.astype(np.float32) / 255.0
        return rgba

    roi_color = np.array([0.35, 0.67, 1.0], dtype=np.float32)
    rgba[y_min:y_max + 1, x_min:x_max + 1, :3] = (
        0.88 * rgba[y_min:y_max + 1, x_min:x_max + 1, :3] + 0.12 * roi_color
    )
    rgba[y_min:y_max + 1, x_min, :3] = [1.0, 0.67, 0.35]
    rgba[y_min:y_max + 1, x_max, :3] = [1.0, 0.67, 0.35]
    rgba[y_min, x_min:x_max + 1, :3] = [1.0, 0.67, 0.35]
    rgba[y_max, x_min:x_max + 1, :3] = [1.0, 0.67, 0.35]
    return rgba


def update_square_text(square, enabled):
    if not dpg.does_item_exist("square_text"):
        return
    if square is None:
        dpg.set_value("square_text", "Square: unavailable")
        return
    mode = "active crop" if enabled else "preview only"
    dpg.set_value(
        "square_text",
        f"Square: x={square['x']}, y={square['y']}, size={square['size']} px | {mode}",
    )


def configure_square_sliders_for_frame():
    if current_frame is None or not dpg.does_item_exist("square_size_input"):
        return

    height, width = np.asarray(current_frame).shape[:2]
    max_size = max(1, min(width, height))
    size = int(dpg.get_value("square_size_input"))
    size = max(1, min(size, max_size))
    x = int(dpg.get_value("square_x_input"))
    y = int(dpg.get_value("square_y_input"))
    x = max(0, min(x, width - size))
    y = max(0, min(y, height - size))

    dpg.configure_item("square_size_input", min_value=1, max_value=max_size)
    dpg.configure_item("square_x_input", min_value=0, max_value=max(0, width - size))
    dpg.configure_item("square_y_input", min_value=0, max_value=max(0, height - size))
    dpg.set_value("square_size_input", size)
    dpg.set_value("square_x_input", x)
    dpg.set_value("square_y_input", y)


def square_slider_callback(sender=None, app_data=None):
    global square_preview_visible
    if current_frame is None:
        return

    square_preview_visible = True
    configure_square_sliders_for_frame()
    params = get_preprocessing_parameters()
    square = get_square_from_params(current_frame, params)
    update_square_text(square, params.get("use_processing_square", False))

    if params.get("use_processing_square", False):
        apply_preprocessing_callback()
    else:
        refresh_raw_image()


def mouse_square_down_callback(sender=None, app_data=None):
    global square_selection_active, square_preview_visible

    if not square_selection_active:
        return
    if not dpg.is_item_hovered(RAW_IMAGE_TAG):
        return

    center_px = raw_image_mouse_pixel()
    if center_px is None or current_frame is None:
        return

    frame = np.asarray(current_frame)
    height, width = frame.shape[:2]
    size = int(dpg.get_value("square_size_input"))
    size = max(1, min(size, width, height))
    half_size = size // 2
    x_center, y_center = center_px
    x0 = max(0, min(int(x_center - half_size), width - size))
    y0 = max(0, min(int(y_center - half_size), height - size))

    dpg.set_value("square_x_input", x0)
    dpg.set_value("square_y_input", y0)
    dpg.set_value("square_size_input", size)
    dpg.set_value("use_processing_square_input", False)

    square_selection_active = False
    square_preview_visible = True
    configure_square_sliders_for_frame()
    square = get_square_from_params(current_frame, get_preprocessing_parameters())
    update_square_text(square, False)
    refresh_raw_image()
    set_status(f"Square selected: x={x0}, y={y0}, size={size}. Click Zoom/process square to use it.")


def open_file_dialog():
    path = native_open_video_dialog()
    if path:
        load_video_from_path(path)


def open_multiple_file_dialog():
    paths = native_open_multiple_video_dialog()
    if paths:
        load_video_from_paths(paths)


def open_one_or_multiple_file_dialog():
    paths = native_open_multiple_video_dialog()
    if paths:
        load_video_from_paths(paths)


def load_video_from_path(path):
    load_video_from_paths([path])


def load_video_from_paths(paths):
    global selected_file, video_stack, current_frame, current_preprocessed
    global current_binary, current_enhanced_binary, current_blob_result, current_blob_debug
    global initial_detection, initial_frame_index, tracking_records, tracking_stop_requested
    global square_preview_visible, square_selection_active

    close_loaded_video_stack()

    try:
        use_lazy_import = (
            dpg.get_value("lazy_import_mode_input")
            if dpg.does_item_exist("lazy_import_mode_input")
            else True
        )
        stack, load_mode = open_video_stack_with_mode(paths, use_lazy_import=use_lazy_import)
    except Exception as exc:
        set_status(f"Failed to load video: {exc}")
        return

    selected_file = paths[0] if len(paths) == 1 else list(paths)
    video_stack = stack
    current_frame = get_video_frame(0)
    current_preprocessed = None
    current_binary = None
    current_enhanced_binary = None
    current_blob_result = None
    current_blob_debug = None
    initial_detection = None
    initial_frame_index = 0
    tracking_records = []
    tracking_stop_requested = False
    square_preview_visible = False
    square_selection_active = False

    if len(paths) == 1:
        file_label = Path(paths[0]).name
    else:
        file_label = f"{len(paths)} files combined: " + ", ".join(Path(path).name for path in paths[:3])
        if len(paths) > 3:
            file_label += ", ..."

    dpg.set_value("file_text", file_label)
    mode_labels = {
        "lazy": "lazy fast open",
        "full": "full RAM load",
        "full_fallback": "full RAM load (lazy fallback)",
    }
    mode_label = mode_labels.get(load_mode, str(load_mode))
    dpg.set_value(
        "shape_text",
        (
            f"Combined stack shape: {stack.shape} | {mode_label}"
            if len(paths) > 1
            else f"Stack shape: {stack.shape} | {mode_label}"
        ),
    )
    dpg.configure_item("frame_slider", min_value=0, max_value=max(0, len(stack) - 1))
    dpg.set_value("frame_slider", 0)
    dpg.set_value("frame_text", "Current frame: 0")
    clear_analysis_plots()
    if dpg.does_item_exist("initial_text"):
        dpg.set_value("initial_text", "Initial detection: not set")
    if dpg.does_item_exist("tracking_progress"):
        dpg.set_value("tracking_progress", 0.0)
        dpg.configure_item("tracking_progress", overlay="0 %")
    if dpg.does_item_exist("use_processing_square_input"):
        dpg.set_value("use_processing_square_input", False)
        dpg.set_value("square_x_input", 0)
        dpg.set_value("square_y_input", 0)
        configure_square_sliders_for_frame()
        if dpg.does_item_exist("square_text"):
            dpg.set_value("square_text", "Square: disabled, full frame is used")

    try:
        refresh_raw_image()
        apply_preprocessing_callback()
        set_status(
            (
                f"{len(paths)} videos combined. Raw and preprocessed views are ready."
                if len(paths) > 1
                else f"Video loaded ({mode_label}). Raw and preprocessed views are ready."
            )
        )
    except Exception as exc:
        set_status(f"Video loaded, but display failed: {exc}")


def resize_main_layout(sender=None, app_data=None):
    if not dpg.does_item_exist("parameter_panel"):
        return

    viewport_width = max(MIN_WINDOW_WIDTH, dpg.get_viewport_client_width())
    viewport_height = max(650, dpg.get_viewport_client_height())
    content_height = max(520, viewport_height - 72)
    available_width = viewport_width - 4 * PANEL_GAP
    parameter_width = max(210, int(available_width * 0.17))
    analysis_width = max(360, int(available_width * 0.30))
    image_panel_width = max(520, available_width - parameter_width - analysis_width)

    dpg.configure_item("parameter_panel", width=parameter_width, height=content_height)
    dpg.configure_item("image_panel", width=image_panel_width, height=content_height)
    dpg.configure_item("analysis_panel", width=analysis_width, height=content_height)
    if dpg.does_item_exist("status_bar"):
        dpg.configure_item("status_bar", width=max(400, viewport_width - 28), height=42)
    dpg.configure_item("frame_slider", width=max(280, image_panel_width - 40))
    if dpg.does_item_exist("main_image_panel"):
        dpg.configure_item("main_image_panel", width=max(420, image_panel_width - 45), height=max(360, content_height - 355))
        update_main_view_from_cache()
    global IMAGE_DISPLAY_WIDTH, IMAGE_DISPLAY_HEIGHT
    IMAGE_DISPLAY_WIDTH = max(160, int((image_panel_width - 70) / 2))
    IMAGE_DISPLAY_HEIGHT = max(120, int((content_height - 170) / 2))
    for panel_tag in (
        "raw_image_panel",
        "preprocessed_image_panel",
        "binary_image_panel",
        "enhanced_binary_image_panel",
    ):
        if dpg.does_item_exist(panel_tag):
            dpg.configure_item(
                panel_tag,
                width=max(220, int((image_panel_width - 36) / 2)),
                height=max(170, int((content_height - 110) / 2)),
            )
    if dpg.does_item_exist("tracking_progress"):
        dpg.configure_item("tracking_progress", width=max(280, analysis_width - 35))

    if dpg.does_item_exist("kde_plot_panel"):
        kde_width = max(320, analysis_width - 30)
        kde_height = max(360, content_height - 390)
        top_height = 110
        joint_height = max(240, kde_height - top_height - 32)
        joint_width = max(220, kde_width - 145)
        dpg.configure_item("kde_plot_panel", width=kde_width, height=kde_height)
        if dpg.does_item_exist("kde_top_plot"):
            dpg.configure_item("kde_top_plot", width=joint_width, height=top_height)
        if dpg.does_item_exist("kde_joint_plot"):
            dpg.configure_item("kde_joint_plot", width=joint_width, height=joint_height)
        if dpg.does_item_exist("kde_colorbar"):
            dpg.configure_item("kde_colorbar", height=joint_height, width=28)
        if dpg.does_item_exist("kde_right_plot"):
            dpg.configure_item("kde_right_plot", width=95, height=joint_height)


def setup_theme():
    """Global dark dashboard theme. Edit color tokens near the top of the file."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, COLOR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, COLOR_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, COLOR_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Text, COLOR_TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, COLOR_TEXT_MUTED)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (55, 65, 80, 180))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (23, 28, 36, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (39, 48, 61, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (45, 56, 72, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, COLOR_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, COLOR_PANEL_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_Header, (40, 48, 61, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (48, 58, 74, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (55, 68, 88, 255))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, COLOR_ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Button, (43, 52, 66, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (54, 66, 84, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (64, 78, 99, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PlotLines, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, COLOR_ACCENT)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 10)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 7)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, CARD_PAD, CARD_PAD)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 9, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, ITEM_SPACING, ITEM_SPACING)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 8, 6)
    dpg.bind_theme(global_theme)

    with dpg.theme(tag=THEME_PRIMARY_BUTTON):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COLOR_ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (34, 118, 218, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 9)

    with dpg.theme(tag=THEME_SECONDARY_BUTTON):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (45, 54, 68, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (58, 70, 88, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)

    with dpg.theme(tag=THEME_DANGER_BUTTON):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (120, 54, 61, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COLOR_ERROR)

    with dpg.colormap_registry():
        # Scientific density map: white -> light blue -> mid blue -> dark blue.
        dpg.add_colormap(
            [
                (255, 255, 255, 255),
                (191, 217, 255, 255),
                (115, 166, 242, 255),
                (31, 71, 166, 255),
            ],
            False,
            tag=KDE_COLORMAP_TAG,
        )

    for tag, color in (
        (THEME_SUCCESS_TEXT, COLOR_SUCCESS),
        (THEME_WARNING_TEXT, COLOR_WARNING),
        (THEME_ERROR_TEXT, COLOR_ERROR),
        (THEME_MUTED_TEXT, COLOR_TEXT_MUTED),
    ):
        with dpg.theme(tag=tag):
            with dpg.theme_component(dpg.mvText):
                dpg.add_theme_color(dpg.mvThemeCol_Text, color)


def setup_fonts():
    """Use Segoe UI on Windows when available; DearPyGui falls back if not found."""
    font_candidates = [
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\SegoeUI.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    font_path = next((path for path in font_candidates if path.exists()), None)
    if font_path is None:
        return

    with dpg.font_registry():
        body_font = dpg.add_font(str(font_path), BODY_FONT_SIZE, tag=BODY_FONT_TAG)
        dpg.add_font(str(font_path), TITLE_FONT_SIZE, tag=TITLE_FONT_TAG)
    dpg.bind_font(body_font)


def add_section_title(text):
    item = dpg.add_text(text)
    if dpg.does_item_exist(TITLE_FONT_TAG):
        dpg.bind_item_font(item, TITLE_FONT_TAG)
    dpg.add_separator()
    return item


@contextmanager
def add_card(title, width=-1, height=0):
    """Reusable visual card. Add new panels by wrapping controls in this helper."""
    with dpg.child_window(width=width, height=height, border=True):
        add_section_title(title)
        yield


@contextmanager
def add_collapsible_card(title, default_open=True, width=-1, height=0):
    """Collapsible card for dense side-panel settings."""
    with dpg.collapsing_header(label=title, default_open=default_open):
        with add_card(title, width=width, height=height):
            yield


def add_labeled_slider(label, tag, default_value, min_value, max_value, is_float=False, callback=auto_update_callback):
    dpg.add_text(label)
    add_fn = dpg.add_slider_float if is_float else dpg.add_slider_int
    return add_fn(
        label="",
        default_value=setting_default(tag, default_value),
        min_value=min_value,
        max_value=max_value,
        width=-1,
        tag=tag,
        callback=callback,
    )


def bind_button_theme(tag, theme):
    if dpg.does_item_exist(tag) and dpg.does_item_exist(theme):
        dpg.bind_item_theme(tag, theme)


def add_small_input_float(label, default_value, tag, callback=auto_update_callback):
    dpg.add_text(label)
    dpg.add_input_float(
        label="",
        default_value=setting_default(tag, default_value),
        width=-1,
        tag=tag,
        step=0,
        callback=callback,
    )


def add_small_input_int(label, default_value, tag, callback=auto_update_callback):
    dpg.add_text(label)
    dpg.add_input_int(
        label="",
        default_value=setting_default(tag, default_value),
        width=-1,
        tag=tag,
        step=0,
        callback=callback,
    )


def add_checkbox(label, default_value, tag):
    dpg.add_checkbox(
        label=label,
        default_value=setting_default(tag, default_value),
        tag=tag,
        callback=auto_update_callback,
    )


def build_layout():
    """Main dashboard layout. Add future panels here; processing logic lives above."""
    with dpg.window(label="Particle BF Particle Tracking", tag="main_window", no_scrollbar=True, no_scroll_with_mouse=True):
        with dpg.group(horizontal=True):
            with dpg.child_window(width=PARAMETER_PANEL_WIDTH, height=960, tag="parameter_panel"):
                build_left_panel()
            with dpg.child_window(width=620, height=960, tag="image_panel"):
                build_image_viewer()
            with dpg.child_window(width=PARAMETER_PANEL_WIDTH, height=960, tag="analysis_panel"):
                build_analysis_tabs()
        with dpg.child_window(height=42, width=-1, tag="status_bar", border=False):
            dpg.add_text("Ready", tag="status_text")
            if dpg.does_item_exist(THEME_MUTED_TEXT):
                dpg.bind_item_theme("status_text", THEME_MUTED_TEXT)


def build_left_panel():
    with add_collapsible_card("Input", default_open=True, width=-1, height=150):
        dpg.add_button(label="Import image stack file", callback=open_file_dialog, width=-1)
        bind_button_theme(dpg.last_item(), THEME_PRIMARY_BUTTON)
        dpg.add_text("No file selected", tag="file_text")
        dpg.add_text("Stack shape: unknown", tag="shape_text")
        dpg.add_checkbox(label="Fast lazy import", default_value=setting_default("lazy_import_mode_input", True), tag="lazy_import_mode_input")

    with add_collapsible_card("Range of interest", default_open=True, width=-1, height=285):
        dpg.add_checkbox(
            label="Use processing square",
            default_value=setting_default("use_processing_square_input", False),
            tag="use_processing_square_input",
            callback=square_slider_callback,
        )
        add_labeled_slider("Square x", "square_x_input", 0, 0, 1000, callback=square_slider_callback)
        add_labeled_slider("Square y", "square_y_input", 0, 0, 1000, callback=square_slider_callback)
        add_labeled_slider("Square size (px)", "square_size_input", 200, 1, 1000, callback=square_slider_callback)
        dpg.add_button(label="Zoom/process square", callback=apply_processing_square_callback, width=-1)
        dpg.add_button(label="Use full frame", callback=reset_processing_square_callback, width=-1)
        dpg.add_text("Square: disabled, full frame is used", tag="square_text")

    with add_collapsible_card("Pipeline", default_open=True, width=-1, height=235):
        add_checkbox("Use blob detection", False, "use_blob_detection_input")
        add_checkbox("Convert to grayscale", True, "convert_to_grayscale_input")
        add_checkbox("Invert image", False, "invert_image_input")
        add_checkbox("Percentile normalization", True, "percentile_normalization_input")
        dpg.add_text("Threshold method")
        dpg.add_combo(["otsu", "manual"], label="", default_value=setting_default("threshold_method_input", "otsu"), width=-1, tag="threshold_method_input", callback=auto_update_callback)
        dpg.add_checkbox(label="Auto update preprocessing", default_value=setting_default("auto_update_preprocessing_input", False), tag="auto_update_preprocessing_input")
        dpg.add_checkbox(
            label="Show detection overlay",
            default_value=setting_default("show_detection_overlay_input", True),
            tag="show_detection_overlay_input",
            callback=apply_preprocessing_callback,
        )

    with add_collapsible_card("Tracking parameters", default_open=True, width=-1, height=315):
        add_small_input_float("Threshold (0-1)", 0.5, "blob_threshold_manual_input")
        add_small_input_int("Min area (px)", 20, "min_area_input")
        add_small_input_int("Max area (px)", 100000, "max_area_input")
        add_small_input_int("Expected diameter (px)", 91, "detect_diameter_input")

    with dpg.collapsing_header(label="Advanced settings", default_open=False):
        with add_card("Morphology / debug", width=-1, height=720):
            add_checkbox("Background correction", False, "background_correction_input")
            add_small_input_float("Background sigma", 60.0, "background_sigma_input")
            dpg.add_text("Background method")
            dpg.add_combo(["subtract", "divide"], label="", default_value=setting_default("background_method_input", "subtract"), width=-1, tag="background_method_input", callback=auto_update_callback)
            add_checkbox("Gaussian smoothing", False, "gaussian_smoothing_input")
            add_small_input_float("Gaussian sigma", 1.0, "gaussian_sigma_input")
            add_checkbox("Tophat", False, "tophat_input")
            add_small_input_int("Tophat radius", 80, "tophat_radius_input")
            add_small_input_float("Percentile low", 1.0, "percentile_low_input")
            add_small_input_float("Percentile high", 99.0, "percentile_high_input")
            add_checkbox("Gamma correction", False, "gamma_correction_input")
            add_small_input_float("Gamma value", 0.7, "gamma_value_input")
            add_checkbox("CLAHE", False, "clahe_input")
            add_small_input_float("CLAHE clip limit", 0.01, "clahe_clip_limit_input")
            add_small_input_int("Blob top-hat radius", 80, "blob_tophat_radius_input")
            add_checkbox("Invert before top-hat", False, "blob_invert_before_tophat_input")
            add_small_input_int("Opening radius", 1, "opening_radius_input")
            add_small_input_int("Closing radius", 1, "closing_radius_input")
            add_small_input_int("Remove holes area", 20, "remove_small_holes_area_input")
            add_checkbox("Choose by prediction", True, "blob_choose_by_prediction_input")
            add_small_input_int("Min object size", 200, "binary_min_object_size_input")
            add_small_input_int("Hole area", 200, "binary_hole_area_input")
            add_small_input_int("Binary opening radius", 1, "binary_opening_radius_input")
            add_small_input_int("Binary closing radius", 3, "binary_closing_radius_input")
            add_checkbox("Fill holes", True, "fill_binary_holes_input")
            add_checkbox("Keep largest blob only", True, "keep_largest_blob_only_input")
            dpg.add_checkbox(label="Keep radius constant", default_value=setting_default("keep_radius_constant_input", True), tag="keep_radius_constant_input")
            add_small_input_float("Max displacement/frame (px)", 20.0, "max_displacement_px_input", callback=None)

def build_image_viewer():
    with add_card("Processing view", width=-1, height=0):
        with dpg.group(horizontal=True):
            dpg.add_button(label="-10", callback=step_frame_callback, user_data=-10, width=54)
            dpg.add_button(label="<", callback=previous_frame_callback, width=44)
            dpg.add_button(label="Play", callback=play_pause_callback, tag="play_button", width=70)
            dpg.add_button(label=">", callback=next_frame_callback, width=44)
            dpg.add_button(label="+10", callback=step_frame_callback, user_data=10, width=54)
            dpg.add_text("Current frame: 0", tag="frame_text")
            dpg.add_input_float(label="fps", default_value=12.0, width=72, tag="playback_speed_input", step=0)
        dpg.add_text("Frame")
        dpg.add_slider_int(label="", default_value=0, min_value=0, max_value=1, callback=slider_callback, tag="frame_slider", width=-1)
        dpg.add_separator()

        with dpg.group(horizontal=True):
            with dpg.child_window(width=290, height=350, tag="raw_image_panel", no_scrollbar=True, no_scroll_with_mouse=True):
                add_section_title("Raw + overlay")
                dpg.add_image(RAW_TEXTURE_TAG, tag=RAW_IMAGE_TAG)
            with dpg.child_window(width=290, height=350, tag="preprocessed_image_panel", no_scrollbar=True, no_scroll_with_mouse=True):
                add_section_title("Preprocessed")
                dpg.add_image(PREPROCESSED_TEXTURE_TAG, tag=PREPROCESSED_IMAGE_TAG)

        with dpg.group(horizontal=True):
            with dpg.child_window(width=290, height=350, tag="binary_image_panel", no_scrollbar=True, no_scroll_with_mouse=True):
                add_section_title("Binary mask")
                dpg.add_image(BINARY_TEXTURE_TAG, tag=BINARY_IMAGE_TAG)
            with dpg.child_window(width=290, height=350, tag="enhanced_binary_image_panel", no_scrollbar=True, no_scroll_with_mouse=True):
                add_section_title("Enhanced mask")
                dpg.add_image(ENHANCED_BINARY_TEXTURE_TAG, tag=ENHANCED_BINARY_IMAGE_TAG)


def build_analysis_tabs():
    with dpg.tab_bar():
        with dpg.tab(label="Detection"):
            with dpg.child_window(width=-1, height=505, border=True):
                dpg.add_button(label="Run tracking", callback=start_tracking_callback, tag="start_tracking_button", width=-1, height=38)
                bind_button_theme("start_tracking_button", THEME_PRIMARY_BUTTON)
                dpg.add_button(label="Preview frame", callback=apply_preprocessing_callback, width=-1)
                bind_button_theme(dpg.last_item(), THEME_SECONDARY_BUTTON)
                dpg.add_button(label="Save images", callback=save_images_callback, width=-1, height=34)
                bind_button_theme(dpg.last_item(), THEME_SECONDARY_BUTTON)
                dpg.add_button(label="Save results", callback=save_results_callback, tag="save_results_button", width=-1, height=34)
                bind_button_theme("save_results_button", THEME_PRIMARY_BUTTON)
                dpg.add_button(label="Stop tracking", callback=stop_tracking_callback, tag="stop_tracking_button", width=-1, height=34, enabled=False)
                bind_button_theme("stop_tracking_button", THEME_DANGER_BUTTON)
                dpg.add_separator()
                dpg.add_button(label="Preview frame", callback=run_single_detection_callback, width=-1)
                bind_button_theme(dpg.last_item(), THEME_SECONDARY_BUTTON)
                dpg.add_button(label="Set as initial detection", callback=set_initial_detection_callback, width=-1)
                bind_button_theme(dpg.last_item(), THEME_SECONDARY_BUTTON)
                dpg.add_text("Initial detection: not set", tag="initial_text")
                dpg.add_text("Frames: 0/0 | 0.00 frames/s | remaining: --:--", tag="tracking_metrics_text")
                dpg.add_progress_bar(default_value=0.0, width=-1, overlay="0 %", tag="tracking_progress")
                dpg.add_text("kx = not calculated yet", tag="kx_text")
                dpg.add_text("N = 0 | sigma x/y/r = not calculated", tag="stats_text")
        with dpg.tab(label="Plots"):
            build_density_panel()
        with dpg.tab(label="Experimental options"):
            build_experimental_options_panel()
        with dpg.tab(label="Export"):
            dpg.add_text("Output folder")
            dpg.add_input_text(label="", default_value=setting_default("save_folder_input", str(Path.cwd())), width=-1, tag="save_folder_input")
            dpg.add_button(label="Choose output folder", callback=choose_save_folder_callback, width=-1)
            dpg.add_text("Base file name")
            dpg.add_input_text(label="", default_value=setting_default("save_base_name_input", "tracking_result"), width=-1, tag="save_base_name_input")
            dpg.add_button(label="Save images", callback=save_images_callback, width=-1, height=34)
            bind_button_theme(dpg.last_item(), THEME_SECONDARY_BUTTON)
            dpg.add_button(label="Save results", callback=save_results_callback, width=-1, height=34)
            bind_button_theme(dpg.last_item(), THEME_PRIMARY_BUTTON)


def build_experimental_options_panel():
    with dpg.child_window(width=-1, height=390, border=True):
        dpg.add_text("Particle ID")
        dpg.add_input_text(label="", default_value=setting_default("particle_id_input", "particle_001"), width=-1, tag="particle_id_input")
        add_small_input_float("Diameter (um)", 5.0, "particle_diameter_um_input", callback=None)
        add_small_input_float("Time between frames dt (ms)", 100.0, "dt_ms_input", callback=None)
        add_small_input_float("Temperature (K)", 298.15, "temperature_k_input", callback=None)
        dpg.add_checkbox(label="Process all frames", default_value=setting_default("process_all_frames_input", False), tag="process_all_frames_input")
        add_small_input_int("Frames to process", 300, "n_frames_to_process_input", callback=None)
        add_small_input_float("Wavenumber (cm-1)", 1700.0, "wavenumber_input", callback=None)
        add_small_input_float("Power (mW)", 0.0, "power_input", callback=None)
        dpg.add_text("Note")
        dpg.add_input_text(label="", default_value=setting_default("note_input", ""), multiline=True, height=68, width=-1, tag="note_input")


def build_density_panel():
    with dpg.child_window(width=-1, height=570, border=True):
        with dpg.child_window(width=360, height=520, tag="kde_plot_panel", border=False):
            with dpg.plot(label="x/y density", height=110, width=360, tag="kde_top_plot"):
                dpg.add_plot_axis(dpg.mvXAxis, label="x centered (um)", tag="kde_top_x_axis")
                dpg.add_plot_axis(dpg.mvYAxis, label="density", tag="kde_top_y_axis")
                dpg.add_line_series([], [], parent="kde_top_y_axis", tag="kde_x_marginal_series")
            with dpg.group(horizontal=True):
                with dpg.plot(label="KDE density", height=390, width=300, tag="kde_joint_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, label="x centered (um)", tag="kde_x_axis")
                    dpg.add_plot_axis(dpg.mvYAxis, label="y centered (um)", tag="kde_y_axis")
                    dpg.add_line_series([], [], label="mean x", parent="kde_y_axis", tag="kde_mean_x_line")
                    dpg.add_line_series([], [], label="mean y", parent="kde_y_axis", tag="kde_mean_y_line")
                    dpg.add_line_series([], [], label="-sigma x", parent="kde_y_axis", tag="kde_minus_sigma_x_line")
                    dpg.add_line_series([], [], label="+sigma x", parent="kde_y_axis", tag="kde_plus_sigma_x_line")
                    dpg.add_line_series([], [], label="-sigma y", parent="kde_y_axis", tag="kde_minus_sigma_y_line")
                    dpg.add_line_series([], [], label="+sigma y", parent="kde_y_axis", tag="kde_plus_sigma_y_line")
                    dpg.add_scatter_series([], [], label="mean", parent="kde_y_axis", tag="kde_mean_point")
                dpg.add_colormap_scale(label="density", tag="kde_colorbar", height=390, width=28, colormap=KDE_COLORMAP_TAG, min_scale=0.0, max_scale=1.0)
                with dpg.plot(label="y density", height=390, width=95, tag="kde_right_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, label="density", tag="kde_right_x_axis")
                    dpg.add_plot_axis(dpg.mvYAxis, label="y centered (um)", tag="kde_right_y_axis")
                    dpg.add_line_series([], [], parent="kde_right_y_axis", tag="kde_y_marginal_series")


def launch_app():
    dpg.create_context()
    setup_theme()
    setup_fonts()

    with dpg.texture_registry(tag="texture_registry"):
        empty = np.ones((1, 1, 4), dtype=np.float32)
        dpg.add_dynamic_texture(1, 1, empty.ravel(), tag=RAW_TEXTURE_TAG)
        dpg.add_dynamic_texture(1, 1, empty.ravel(), tag=PREPROCESSED_TEXTURE_TAG)
        dpg.add_dynamic_texture(1, 1, empty.ravel(), tag=BINARY_TEXTURE_TAG)
        dpg.add_dynamic_texture(1, 1, empty.ravel(), tag=ENHANCED_BINARY_TEXTURE_TAG)
        dpg.add_dynamic_texture(1, 1, empty.ravel(), tag=MAIN_TEXTURE_TAG)

    build_layout()

    with dpg.handler_registry():
        dpg.add_mouse_down_handler(button=dpg.mvMouseButton_Left, callback=mouse_square_down_callback)

    viewport_kwargs = {
        "title": "BF-Particle-Tracker",
        "width": 1600,
        "height": 950,
    }
    if APP_ICON_PATH.exists():
        viewport_kwargs["small_icon"] = str(APP_ICON_PATH)
        viewport_kwargs["large_icon"] = str(APP_ICON_PATH)
    dpg.create_viewport(**viewport_kwargs)
    dpg.set_primary_window("main_window", True)
    dpg.set_viewport_resize_callback(resize_main_layout)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    resize_main_layout()
    dpg.start_dearpygui()
    save_user_settings()
    close_loaded_video_stack()
    dpg.destroy_context()
