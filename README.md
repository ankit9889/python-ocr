# Python OCR & Barcode Reader

A Python application for OCR text recognition, VIN extraction, barcode reading, and color extraction.

## Features
- **OCR Engine**: Powered by PaddleOCR for accurate text detection and recognition.
- **VIN Extractor**: Identifies and validates Vehicle Identification Numbers (VIN).
- **Barcode & QR Reader**: Decodes QR codes and barcodes using OpenCV and PyZBar.
- **Color Extractor**: Detects primary color attributes from image regions.
- **Batch Processing & GUI**: Built-in GUI and batch pipeline support.

---

## Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/ankit9889/python-ocr.git
cd python-ocr
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

#### For Systems with GPU (NVIDIA CUDA):
```bash
pip install -r requirements.txt
```

#### For CPU-only Systems:
```bash
pip install paddlepaddle paddleocr opencv-python numpy Pillow pyzbar tkinterdnd2
```

---

## Running the Application

To start the application GUI / processing script:
```bash
python run.py
```

---

## Project Structure
- `config.py` - Application configuration & model thresholds
- `run.py` - Application entry point
- `core/` - Core processing modules:
  - `ocr_engine.py` - PaddleOCR setup and text extraction
  - `barcode_reader.py` - QR and barcode decoding
  - `color_extractor.py` - Dominant color detection
  - `vin_extractor.py` - VIN regex matching & validation
  - `preprocess.py` - Image preprocessing pipeline
  - `result_builder.py` - Result aggregation & exports
