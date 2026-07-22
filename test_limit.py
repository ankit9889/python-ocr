import time
from pathlib import Path
from core.ocr_engine import _create_paddle_ocr
from core.preprocess import preprocess
from core.vin_extractor import extract_vin
img_path = Path('live_scans/zebra_scan_20260722_140327.jpg')
orig, prep = preprocess(str(img_path))

for limit in [2048, 1280, 960]:
    engine = _create_paddle_ocr("cpu")
    # Hack to set det_limit_side_len for PaddleOCR
    engine.ocr_version = "PP-OCRv3" # just in case
    t0 = time.time()
    res = engine.ocr(prep, cls=False, det_limit_side_len=limit)
    t1 = time.time()
    print(f"Limit {limit}: {t1-t0:.2f}s")
