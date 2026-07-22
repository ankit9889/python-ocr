import cv2
import time
import numpy as np

image = np.random.randint(0, 255, (3000, 4000, 3), dtype=np.uint8)
t0 = time.time()
lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
l, a, b = cv2.split(lab)
l = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(l)
t1 = time.time()
l_denoised = cv2.fastNlMeansDenoising(l, None, 5, 7, 21)
t2 = time.time()
print(f"CLAHE: {t1-t0:.2f}s")
print(f"NLMeans L-channel: {t2-t1:.2f}s")
