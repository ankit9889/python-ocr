"""Dictionary-free visual colour classification using HSV/Lab image statistics and OCR text matching."""
from __future__ import annotations
import cv2
import numpy as np

_COLOR_WORDS = {
    "BLACK": "black", "WHITE": "white", "SILVER": "silver", "GREY": "gray", "GRAY": "gray",
    "RED": "red", "BLUE": "blue", "GREEN": "green", "YELLOW": "yellow", "ORANGE": "orange",
    "BROWN": "brown", "GOLD": "gold", "PURPLE": "purple", "MAROON": "maroon", "BEIGE": "beige",
    # Frequent manufacturer paint-name terms. These are aliases, while the
    # original OCR phrase remains available in color_description.
    "CRIMSON": "red", "SCARLET": "red", "RUBY": "red", "WINE": "red", "CHERRY": "red", "BURGUNDY": "red",
    "NAVY": "blue", "AZURE": "blue", "CYAN": "blue", "TEAL": "blue",
    "TURQUOISE": "blue", "INDIGO": "blue", "SAPPHIRE": "blue", "VIOLET": "purple",
    "IVORY": "white", "CREAM": "white", "CHARCOAL": "gray", "GRAPHITE": "gray", "SLATE": "gray",
    "CHAMPAGNE": "gold", "COPPER": "brown", "BRONZE": "brown",
    "EMERALD": "green", "MINT": "green", "OLIVE": "green", "LIME": "green",
    "RACIING": "green", "RACING": "green",
}

_KNOWN_PAINT_WORDS = sorted(list(set(list(_COLOR_WORDS.keys()) + [
    "METALLIC", "MICA", "PEARL", "IGNEOUS", "JET", "DEEP", "LIGHT", "DARK",
    "INTENSE", "ATHLETIC", "MIDNIGHT", "RACING", "RACIING", "GRANITE",
    "SAPPHIRE", "CLEAR", "COAT", "GLOSS", "MATTE", "SATIN"
])), key=len, reverse=True)


def format_paint_text(text: str) -> str:
    raw = text.strip()
    if " " in raw:
        return raw
    curr = raw.upper()
    matched = []
    while curr:
        found = False
        for w in _KNOWN_PAINT_WORDS:
            if curr.startswith(w):
                matched.append(w)
                curr = curr[len(w):]
                found = True
                break
        if not found:
            return raw
    return " ".join(matched) if matched else raw


def extract_color(image: np.ndarray, ocr_items: list[dict] | None = None) -> dict:
    name = None
    description = None

    if ocr_items:
        candidates = [item for item in ocr_items if sum(ch.isalpha() for ch in item["text"]) >= 3]
        std_colors = {"BLACK", "WHITE", "RED", "BLUE", "GREEN", "YELLOW", "ORANGE", "PURPLE", "GRAY", "GREY", "SILVER", "BROWN"}

        for item in reversed(candidates):
            raw_text = item["text"].strip()
            text_upper = raw_text.upper()
            words = {w.strip(" ,.-").upper() for w in text_upper.split()}
            matches = {_COLOR_WORDS[w] for w in words if w in _COLOR_WORDS}

            if len(matches) >= 1:
                color_matches = [w for w in words if w in _COLOR_WORDS]
                std = [w for w in color_matches if w in std_colors]
                name = _COLOR_WORDS[std[0]] if std else _COLOR_WORDS[color_matches[0]]
                description = format_paint_text(raw_text)
                break
            else:
                formatted = format_paint_text(raw_text)
                formatted_words = {w.upper() for w in formatted.split()}
                sub_matches = {_COLOR_WORDS[w] for w in formatted_words if w in _COLOR_WORDS}
                if len(sub_matches) >= 1:
                    color_matches = [w for w in formatted_words if w in _COLOR_WORDS]
                    std = [w for w in color_matches if w in std_colors]
                    name = _COLOR_WORDS[std[0]] if std else _COLOR_WORDS[color_matches[0]]
                    description = formatted
                    break

    # Centre crop avoids much of the dark background; dominant saturated paint pixels win.
    h, w = image.shape[:2]
    crop = image[h // 6: h * 5 // 6, w // 6: w * 5 // 6]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    pixels = hsv.reshape(-1, 3)
    usable = pixels[(pixels[:, 2] > 45) & (pixels[:, 1] > 25)]
    if len(usable) < 50:
        median = np.median(pixels, axis=0)
    else:
        median = np.median(usable, axis=0)
    hue, sat, value = map(float, median)
    if value < 55: visual_name = "black"
    elif sat < 22 and value > 195: visual_name = "white"
    elif sat < 45: visual_name = "silver" if value > 125 else "gray"
    elif hue < 10 or hue >= 170: visual_name = "red"
    elif hue < 22: visual_name = "orange"
    elif hue < 35: visual_name = "yellow"
    elif hue < 85: visual_name = "green"
    elif hue < 135: visual_name = "blue"
    elif hue < 160: visual_name = "purple"
    else: visual_name = "red"

    if name is None:
        name = visual_name

    return {
        "value": name,
        "description": description,
        "visual_value": visual_name,
        "method": "OCR paint-description + HSV fallback" if description else "HSV dominant-pixel analysis",
        "hsv": [round(hue), round(sat), round(value)],
    }

