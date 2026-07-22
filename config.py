from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "output"
EXPORT_DIR = ROOT_DIR / "exports"
MODEL_DIR = ROOT_DIR / "models"
for directory in (OUTPUT_DIR, EXPORT_DIR, MODEL_DIR):
    directory.mkdir(exist_ok=True)

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MIN_OCR_CONFIDENCE = 0.35
VIN_MIN_LENGTH = 16
VIN_MAX_LENGTH = 20
VIN_PATTERN = rf"[A-HJ-NPR-Z0-9]{{{VIN_MIN_LENGTH},{VIN_MAX_LENGTH}}}"

# Hardware & Acceleration settings ('auto', 'gpu', 'cpu')
DEVICE_PREFERENCE = "cpu"

# PaddleOCR 3.x settings tuned for small, dense vehicle identification labels.
PADDLE_TEXT_DET_LIMIT_SIDE_LEN = 2048
PADDLE_TEXT_DET_THRESH = 0.22
PADDLE_TEXT_DET_BOX_THRESH = 0.40
PADDLE_TEXT_DET_UNCLIP_RATIO = 1.6
PADDLE_TEXT_REC_SCORE_THRESH = 0.15

