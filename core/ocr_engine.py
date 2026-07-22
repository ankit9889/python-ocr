"""Lazy PaddleOCR adapter, keeping application imports lightweight with auto GPU/CPU switching."""
from __future__ import annotations
import logging
from typing import Any

from config import (
    DEVICE_PREFERENCE,
    PADDLE_TEXT_DET_BOX_THRESH,
    PADDLE_TEXT_DET_LIMIT_SIDE_LEN,
    PADDLE_TEXT_DET_THRESH,
    PADDLE_TEXT_DET_UNCLIP_RATIO,
    PADDLE_TEXT_REC_SCORE_THRESH,
)

logger = logging.getLogger(__name__)
_engine: Any = None
_active_device: str = "cpu"


def detect_device(preference: str = DEVICE_PREFERENCE) -> str:
    """Detect available hardware or respect preference ('auto', 'gpu', 'cpu')."""
    pref = (preference or "auto").lower()
    if pref == "cpu":
        return "cpu"

    try:
        import paddle
        if paddle.is_compiled_with_cuda():
            return "gpu"
    except Exception as err:
        logger.warning("Error probing GPU support: %s", err)

    if pref == "gpu":
        logger.warning("GPU preference requested, but CUDA is not available in Paddle. Falling back to CPU.")
    return "cpu"


def _create_paddle_ocr(device: str) -> Any:
    from paddleocr import PaddleOCR
    return PaddleOCR(
        lang="en",
        use_angle_cls=False,  # Disabling angle classifier saves ~30% CPU time (labels are always horizontal)
        show_log=False,
        use_gpu=(device == "gpu"),
        cpu_threads=2,  # Prevent thread thrashing on older 2-core processors like i3
        enable_mkldnn=True,  # Accelerate CPU inference using Intel Math Kernel Library
    )


def _get_engine(preference: str | None = None) -> Any:
    global _engine, _active_device
    if _engine is None:
        target_pref = preference or DEVICE_PREFERENCE
        target_device = detect_device(target_pref)
        if target_device == "gpu":
            try:
                print("[OCR Engine] Attempting to initialize PaddleOCR on GPU (CUDA)...")
                _engine = _create_paddle_ocr("gpu")
                # Eagerly test the GPU with a dummy prediction to catch lazy-loading cuDNN errors
                import numpy as np
                _engine.ocr(np.zeros((10, 10, 3), dtype=np.uint8), cls=False)
                _active_device = "gpu"
                print("[OCR Engine] PaddleOCR successfully running on GPU.")
            except Exception as exc:
                print(f"[OCR Engine Warning] GPU initialization failed ({exc}). Auto-switching to CPU...")
                _engine = _create_paddle_ocr("cpu")
                _active_device = "cpu"
                print("[OCR Engine] PaddleOCR running on CPU (fallback).")
        else:
            print("[OCR Engine] Initializing PaddleOCR on CPU...")
            _engine = _create_paddle_ocr("cpu")
            _active_device = "cpu"

    return _engine


def get_active_device() -> str:
    """Returns the device ('gpu' or 'cpu') currently active."""
    _get_engine()
    return _active_device


def set_device_preference(preference: str) -> None:
    """Re-initializes the OCR engine with a new device preference."""
    global _engine
    _engine = None
    _get_engine(preference)


def read(image) -> list[dict]:
    # PaddleOCR 2.x API
    result = _get_engine().ocr(image, cls=True)
    items: list[dict] = []
    if not result or not result[0]:
        return items
    
    for line in result[0]:
        if not line:
            continue
        box = line[0]
        text, score = line[1]
        items.append({
            "text": str(text),
            "confidence": round(float(score), 4),
            "box": box,
        })
    return items


def read_views(images) -> list[dict]:
    """OCR multiple renderings and retain the highest-confidence duplicate text."""
    unique: dict[str, dict] = {}
    for view_index, image in enumerate(images):
        for item in read(image):
            item["view"] = view_index
            key = "".join(item["text"].upper().split())
            if key not in unique or item["confidence"] > unique[key]["confidence"]:
                unique[key] = item
    return list(unique.values())

