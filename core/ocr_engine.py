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


def _create_paddle_ocr(device: str, force_default: bool = False) -> Any:
    from paddleocr import PaddleOCR
    from core.settings import load_settings
    settings = load_settings()
    
    kwargs = {
        "lang": "en",
        "use_angle_cls": settings.get("angle_classifier", False),
        "show_log": False,
        "use_gpu": (device == "gpu"),
        "cpu_threads": 2,
        "enable_mkldnn": True,
        "det_limit_side_len": PADDLE_TEXT_DET_LIMIT_SIDE_LEN,
        "det_limit_type": "max",
        "det_thresh": PADDLE_TEXT_DET_THRESH,
        "det_box_thresh": PADDLE_TEXT_DET_BOX_THRESH,
        "det_unclip_ratio": PADDLE_TEXT_DET_UNCLIP_RATIO,
        "rec_score_thresh": PADDLE_TEXT_REC_SCORE_THRESH,
        "use_doc_orientation_classify": True,
        "use_doc_unwarping": True,
        "use_textline_orientation": True,
    }
    
    engine = settings.get("engine", "default")
    if not force_default and engine == "onnx":
        # Convert models to ONNX using paddle2onnx automatically if missing
        import os, subprocess
        home = os.path.expanduser('~')
        det_dir = os.path.join(home, '.paddleocr', 'whl', 'det', 'en', 'en_PP-OCRv3_det_infer')
        rec_dir = os.path.join(home, '.paddleocr', 'whl', 'rec', 'en', 'en_PP-OCRv4_rec_infer')
        
        for mdir in [det_dir, rec_dir]:
            onnx_path = os.path.join(mdir, 'model.onnx')
            if os.path.exists(mdir) and not os.path.exists(onnx_path):
                print(f"[OCR Engine] Automatically converting model in {mdir} to ONNX...")
                try:
                    import sys
                    bin_path = os.path.join(os.path.dirname(sys.executable), 'paddle2onnx')
                    if os.name == 'nt' and not bin_path.endswith('.exe'):
                        bin_path += '.exe'
                    subprocess.run(
                        [bin_path, '--model_dir', mdir, '--model_filename', 'inference.pdmodel', '--params_filename', 'inference.pdiparams', '--save_file', onnx_path],
                        check=True, capture_output=True
                    )
                except Exception as e:
                    print(f"Error converting to ONNX: {e}")
                    
        kwargs["use_onnx"] = True
        kwargs["det_model_dir"] = os.path.join(det_dir, 'model.onnx')
        kwargs["rec_model_dir"] = os.path.join(rec_dir, 'model.onnx')
    elif not force_default and engine == "openvino":
        kwargs["use_openvino"] = True
        
    if settings.get("batching", False):
        kwargs["rec_batch_num"] = 12
        
    return PaddleOCR(**kwargs)


def _get_engine(preference: str | None = None) -> Any:
    global _engine, _active_device
    if _engine is None:
        target_pref = preference or DEVICE_PREFERENCE
        target_device = detect_device(target_pref)
        
        # Ensure base models are downloaded BEFORE initializing ONNX/OpenVINO
        from core.settings import load_settings
        if load_settings().get("engine") in ["onnx", "openvino"]:
            print("[OCR Engine] Ensuring base models are downloaded...")
            _create_paddle_ocr("cpu", force_default=True)
            
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

