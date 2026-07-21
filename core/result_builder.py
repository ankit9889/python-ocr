from __future__ import annotations
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from config import EXPORT_DIR, OUTPUT_DIR, SUPPORTED_SUFFIXES
from core.barcode_reader import read_barcodes
from core.color_extractor import extract_color
from core.ocr_engine import read, read_views
from core.preprocess import ocr_views, preprocess
from core.utils import labeled_value
from core.vin_extractor import extract_vin


def analyse_image(path: Path) -> dict:
    original, prepared = preprocess(str(path))
    views = ocr_views(prepared)
    # Most clean labels are fully read in one pass. Run slower thresholded and
    # enlarged views only when the primary result is not usable.
    ocr_items = read(views[0])
    primary_vin = extract_vin(ocr_items)
    primary_color = extract_color(original, ocr_items)
    requires_retry = (
        primary_vin is None
        or primary_vin["confidence"] < 0.80
        or primary_color.get("description") is None
    )
    if requires_retry:
        additional_items = read_views(views[1:])
        best_by_text = {"".join(item["text"].upper().split()): item for item in ocr_items}
        for item in additional_items:
            key = "".join(item["text"].upper().split())
            if key not in best_by_text or item["confidence"] > best_by_text[key]["confidence"]:
                best_by_text[key] = item
        ocr_items = list(best_by_text.values())
    return {
        "image": str(path.resolve()), "processed_at": datetime.now(timezone.utc).isoformat(),
        "vin": extract_vin(ocr_items), "color": extract_color(original, ocr_items), "barcodes": read_barcodes(original),
        "model": labeled_value(ocr_items, ("model", "vehicle model")),
        "engine_number": labeled_value(ocr_items, ("engine no", "engine number", "engine")), "ocr": ocr_items,
    }


def scan_path(path: Path, export_csv: bool = False, workers: int = 1) -> list[dict]:
    ignored_directories = {".venv", "output", "exports", "models", "__pycache__", ".git"}
    files = [path] if path.is_file() else sorted(
        file for file in path.rglob("*")
        if file.suffix.lower() in SUPPORTED_SUFFIXES
        and not any(part in ignored_directories for part in file.relative_to(path).parts[:-1])
    )
    if not files:
        raise FileNotFoundError(f"No supported images found in {path}")
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(analyse_image, files))
    else:
        results = [analyse_image(file) for file in files]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (OUTPUT_DIR / f"vehicle_scan_{stamp}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    if export_csv:
        with (EXPORT_DIR / f"vehicle_scan_{stamp}.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "image", "vin", "vin_status", "vin_partial", "vin_note", "vin_confidence", "iso_3779_valid",
                "color", "color_description", "model", "engine_number", "barcodes"
            ])
            writer.writeheader()
            for item in results:
                vin = item["vin"] or {}
                writer.writerow({"image": item["image"], "vin": vin.get("value"), "vin_status": vin.get("status"),
                    "vin_partial": vin.get("partial_value"), "vin_note": vin.get("note"),
                    "vin_confidence": vin.get("confidence"), "iso_3779_valid": vin.get("validation", {}).get("iso_3779_valid"),
                    "color": item["color"]["value"], "color_description": item["color"].get("description"),
                    "model": item["model"], "engine_number": item["engine_number"], "barcodes": json.dumps(item["barcodes"])})
    return results
