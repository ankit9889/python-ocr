from __future__ import annotations
import re


def labeled_value(items: list[dict], labels: tuple[str, ...]) -> str | None:
    pattern = re.compile(r"(?:" + "|".join(map(re.escape, labels)) + r")\s*[:#-]?\s*(.+)", re.I)
    for item in items:
        match = pattern.search(item["text"])
        if match:
            return match.group(1).strip()
    return None
