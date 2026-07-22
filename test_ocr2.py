import cv2
from pathlib import Path
from core.preprocess import preprocess
from core.ocr_engine import read
from core.vin_extractor import extract_vin
from core.color_extractor import extract_color
import time

for img_path in sorted(Path("live_scans").glob("*.jpg")):
    print(f"\n--- Testing {img_path.name} ---")
    orig, prep = preprocess(str(img_path))
    items = read(prep)
    vin = extract_vin(items)
    color = extract_color(orig, items)
    print(f"VIN: {vin}")
    print(f"Color: {color}")
