import time
from pathlib import Path
from core.result_builder import analyse_image
import logging
logging.basicConfig(level=logging.WARNING)
img_path = Path('live_scans/zebra_scan_20260722_140327.jpg')
t0 = time.time()
analyse_image(img_path)
t1 = time.time()
print(f'Warmup scan time: {t1-t0:.2f}s')

t2 = time.time()
analyse_image(img_path)
t3 = time.time()
print(f'Subsequent scan time: {t3-t2:.2f}s')
