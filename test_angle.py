import time
from core.ocr_engine import _create_paddle_ocr
from core.preprocess import preprocess
from core.vin_extractor import extract_vin
from core.color_extractor import extract_color
from pathlib import Path

# Create engine without angle cls
engine = _create_paddle_ocr("cpu")

img_path = Path('live_scans/zebra_scan_20260722_140327.jpg')
orig, prep = preprocess(str(img_path))
t0 = time.time()
res = engine.ocr(prep, cls=False)
t1 = time.time()
items = []
for line in res[0]:
    if not line: continue
    box = line[0]
    text, score = line[1]
    items.append({"text": str(text), "confidence": round(float(score), 4), "box": box})
print(f"Time without cls: {t1-t0:.2f}s")
print(extract_vin(items))
print(extract_color(orig, items))
