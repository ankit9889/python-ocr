"""ISO 3779 VIN validation, including North-American check digit when applicable."""
from __future__ import annotations
import re
from config import VIN_MAX_LENGTH, VIN_MIN_LENGTH

_VALUES = {str(n): n for n in range(10)}
_VALUES.update({c: v for chars, v in (("AJ", 1), ("BKS", 2), ("CLT", 3), ("DMU", 4), ("ENV", 5), ("FW", 6), ("GPX", 7), ("HY", 8), ("RZ", 9)) for c in chars})
_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)


def validate_vin(vin: str) -> dict:
    vin = vin.upper().strip()
    character_valid = bool(re.fullmatch(r"[A-HJ-NPR-Z0-9]+", vin))
    length_valid = VIN_MIN_LENGTH <= len(vin) <= VIN_MAX_LENGTH
    iso_length = len(vin) == 17
    format_valid = character_valid and length_valid
    result = {"format_valid": format_valid, "length_valid": length_valid,
              "iso_3779_applicable": iso_length, "check_digit_valid": None, "iso_3779_valid": False}
    if not format_valid:
        return result
    if not iso_length:
        return result
    # The check digit is mandated for North America; elsewhere it may be arbitrary.
    total = sum(_VALUES[c] * weight for c, weight in zip(vin, _WEIGHTS))
    expected = "X" if total % 11 == 10 else str(total % 11)
    is_na = vin[0] in "12345"
    result["check_digit_valid"] = vin[8] == expected
    result["iso_3779_valid"] = format_valid and (not is_na or result["check_digit_valid"])
    return result
