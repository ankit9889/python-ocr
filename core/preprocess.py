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
    enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 5, 5, 7, 21)
    blurred = cv2.GaussianBlur(denoised, (0, 0), 1.2)
    sharpened = cv2.addWeighted(denoised, 1.6, blurred, -0.6, 0)
    return image, sharpened


def ocr_views(prepared: np.ndarray) -> list[np.ndarray]:
    """Complementary OCR views for glare, small print, and low contrast labels."""
    gray = cv2.cvtColor(prepared, cv2.COLOR_BGR2GRAY)
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 35, 9)
    enlarged = cv2.resize(prepared, None, fx=1.75, fy=1.75, interpolation=cv2.INTER_CUBIC)
    return [prepared, cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR), enlarged]
