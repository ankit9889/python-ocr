from __future__ import annotations
import cv2


def read_barcodes(image) -> list[dict]:
    """Decode QR codes always; decode other symbologies when zbar is available."""
    found = []
    value, _points, _ = cv2.QRCodeDetector().detectAndDecode(image)
    if value:
        found.append({"type": "QRCODE", "value": value})
    try:
        from pyzbar.pyzbar import decode
        for item in decode(image):
            entry = {"type": item.type, "value": item.data.decode("utf-8", errors="replace")}
            if entry not in found:
                found.append(entry)
    except (ImportError, OSError):
        pass  # pyzbar requires the system zbar library.
    return found
