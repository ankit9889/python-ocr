from __future__ import annotations
import re
from config import VIN_MAX_LENGTH, VIN_MIN_LENGTH
from core.validator import validate_vin


def _clean(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def extract_vin(ocr_items: list[dict]) -> dict | None:
    candidates = []
    for item in ocr_items:
        compact = _clean(item["text"])
        # Some manufacturers use a 16-20 character chassis/VIN identifier.
        # ISO-3779 validation remains applicable only at exactly 17 characters.
        if VIN_MIN_LENGTH <= len(compact) <= VIN_MAX_LENGTH:
            raw = compact
            # OCR commonly swaps I/O/Q despite prohibited VIN characters.
            normalized = raw.replace("I", "1").replace("O", "0").replace("Q", "0")
            check = validate_vin(normalized)
            if check["format_valid"]:
                score = float(item["confidence"]) * 0.70 + (0.30 if check["iso_3779_valid"] else 0.20)
                candidates.append((score, normalized, check, item))
    if not candidates:
        return None
    score, vin, validation, source = max(candidates, key=lambda candidate: candidate[0])
    status = "verified" if len(vin) == 17 else "detected"
    note = None if len(vin) == 17 else f"{len(vin)}-character chassis/VIN identifier; ISO-3779 check digit does not apply."
    return {"value": vin, "confidence": round(min(score, 1.0), 4), "validation": validation,
            "source_text": source["text"], "status": status, "note": note}
