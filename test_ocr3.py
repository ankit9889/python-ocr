import cv2
from pathlib import Path
from core.preprocess import preprocess
from core.ocr_engine import read

img_path = Path("live_scans/zebra_scan_20260722_140524.jpg")
orig, prep = preprocess(str(img_path))
items = read(prep)
for it in items:
    print(f"[{it['confidence']:.2f}] {it['text']}")
