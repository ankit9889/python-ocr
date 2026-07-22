import cv2
from pathlib import Path
from core.preprocess import preprocess
from core.ocr_engine import read

try:
    img_path = list(Path("live_scans").glob("*.jpg"))[-1]
    print(f"Testing with {img_path}")
    orig, prep = preprocess(str(img_path))
    cv2.imwrite("test_prep.jpg", prep)
    items = read(prep)
    for it in items:
        print(f"[{it['confidence']:.2f}] {it['text']}")
except Exception as e:
    print(e)
