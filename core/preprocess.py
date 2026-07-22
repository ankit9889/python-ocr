"""OpenCV image enhancement for reflective vehicle labels."""
from __future__ import annotations
import cv2
import numpy as np


def preprocess(image_path: str) -> tuple[np.ndarray, np.ndarray]:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    # Preserve colour for paint analysis; create a high-local-contrast OCR view.
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(l)
    
    # Fast L-channel denoising instead of slow Colored denoising
    l_denoised = cv2.fastNlMeansDenoising(l, None, 5, 7, 21)
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
