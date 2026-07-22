"""OpenCV image enhancement for reflective vehicle labels."""
from __future__ import annotations
import cv2
import numpy as np


def preprocess(image_path: str) -> tuple[np.ndarray, np.ndarray]:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    # Preserve colour for paint analysis
    # For extremely large images (e.g., manual uploads > 1600px), downscale immediately to save CPU time on older processors
    h, w = image.shape[:2]
    if w > 1600:
        scale = 1600 / w
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    from core.settings import load_settings
    settings = load_settings()
    if settings.get("smart_crop", False):
        # Crop the outer 15% to save ~30% OCR processing area
        h, w = image.shape[:2]
        crop_y, crop_x = int(h * 0.15), int(w * 0.15)
        image = image[crop_y:h-crop_y, crop_x:w-crop_x]

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(l)
    
    # Ultra-fast median blur instead of NLMeans (saves 4-15 seconds on old CPUs)
    l_denoised = cv2.medianBlur(l, 3)
    denoised = cv2.cvtColor(cv2.merge((l_denoised, a, b)), cv2.COLOR_LAB2BGR)
    
    blurred = cv2.GaussianBlur(denoised, (0, 0), 1.2)
    sharpened = cv2.addWeighted(denoised, 1.6, blurred, -0.6, 0)
    return image, sharpened


def ocr_views(prepared: np.ndarray) -> list[np.ndarray]:
    # Complementary OCR views for glare, small print, and low contrast labels.
    gray = cv2.cvtColor(prepared, cv2.COLOR_BGR2GRAY)
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 9)
    
    # Only enlarge heavily if the image is small. High-res images like Zebra (1280px width) don't need 1.75x zoom.
    h, w = prepared.shape[:2]
    fx = 1.75 if w < 800 else (1.2 if w < 1500 else 1.0)
    enlarged = cv2.resize(prepared, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
    return [prepared, cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR), enlarged]
