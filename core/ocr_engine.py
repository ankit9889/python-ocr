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
        device=device,
        use_doc_orientation_classify=True,
        use_doc_unwarping=True,
        use_textline_orientation=True,
        text_det_limit_side_len=PADDLE_TEXT_DET_LIMIT_SIDE_LEN,
        text_det_limit_type="max",
        text_det_thresh=PADDLE_TEXT_DET_THRESH,
        text_det_box_thresh=PADDLE_TEXT_DET_BOX_THRESH,
        text_det_unclip_ratio=PADDLE_TEXT_DET_UNCLIP_RATIO,
        text_rec_score_thresh=PADDLE_TEXT_REC_SCORE_THRESH,
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
    # The official 3.x API exposes predict_iter for incremental processing;
    # using it prevents result accumulation during large folder scans.
    result = _get_engine().predict_iter(image)
    items: list[dict] = []
    for page in result:
        texts, scores = page.get("rec_texts", []), page.get("rec_scores", [])
        boxes = page.get("rec_boxes", [])
        for index, (text, score) in enumerate(zip(texts, scores)):
            items.append({
                "text": str(text),
                "confidence": round(float(score), 4),
                "box": (boxes[index].tolist() if hasattr(boxes[index], "tolist") else boxes[index])
                if index < len(boxes) else None,
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

