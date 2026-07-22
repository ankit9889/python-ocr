import cv2
import time
from pathlib import Path
img_path = str(list(Path('live_scans').glob('*.jpg'))[0])
image = cv2.imread(img_path)
t0 = time.time()
lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
l, a, b = cv2.split(lab)
l = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(l)
enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
t1 = time.time()
denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 5, 5, 7, 21)
t2 = time.time()
blurred = cv2.GaussianBlur(denoised, (0, 0), 1.2)
sharpened = cv2.addWeighted(denoised, 1.6, blurred, -0.6, 0)
t3 = time.time()
print(f'CLAHE: {t1-t0:.3f}s')
print(f'Denoise: {t2-t1:.3f}s')
print(f'Sharpen: {t3-t2:.3f}s')
