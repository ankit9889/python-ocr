"""VehicleVisionOCR command line and image-upload GUI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tkinter import Tk, filedialog, ttk, Text, END

from config import OUTPUT_DIR
from core.result_builder import scan_path


def choose_images(parent=None) -> list[Path]:
    paths = filedialog.askopenfilenames(parent=parent,
        title="Select vehicle label image(s)",
        filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"), ("All files", "*.*")],
    )
    return [Path(path) for path in paths]


def run_gui() -> None:
    """Upload interface; drag/drop is enabled when tkinterdnd2 is installed."""
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        DND_FILES = None
        root = Tk()
    root.title("VehicleVisionOCR")
    root.geometry("720x440")
    status = ttk.Label(root, text="Drop vehicle-label images here, or choose files.", padding=18)
    status.pack(fill="x")
    output = Text(root, wrap="word", height=18)
    output.pack(fill="both", expand=True, padx=12, pady=8)

    def process(paths: list[Path]) -> None:
        if not paths:
            return
        status.configure(text=f"Processing {len(paths)} image(s)...")
        root.update_idletasks()
        try:
            results = []
            for path in paths:
                results.extend(scan_path(path))
            output.delete("1.0", END)
            output.insert(END, json.dumps(results, indent=2, ensure_ascii=False))
            status.configure(text=f"Complete - JSON saved in {OUTPUT_DIR.resolve()}")
        except Exception as exc:
            status.configure(text=f"Failed: {exc}")

    ttk.Button(root, text="Choose image(s)", command=lambda: process(choose_images(root))).pack(pady=4)
    if DND_FILES:
        status.drop_target_register(DND_FILES)
        status.dnd_bind("<<Drop>>", lambda event: process([Path(p) for p in root.tk.splitlist(event.data)]))
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract VIN and vehicle-label data from images.")
    parser.add_argument("path", nargs="?", help="Image or folder to scan")
    parser.add_argument("--gui", action="store_true", help="Open the native image upload dialog")
    parser.add_argument("--csv", action="store_true", help="Also write a CSV report")
    parser.add_argument("--device", choices=["auto", "gpu", "cpu"], default="auto", help="Hardware device preference for OCR (default: auto)")
    parser.add_argument("--workers", type=int, default=1, help="Parallel files (keep 1 for GPU OCR)")
    parser.add_argument("--verbose", action="store_true", help="Print complete JSON, including all OCR text")
    args = parser.parse_args()

    if args.device:
        from core.ocr_engine import set_device_preference
        set_device_preference(args.device)

    if args.gui or not args.path:
        run_gui()
        return

    paths = [Path(args.path)]
    if not paths:
        return
    results = []
    try:
        for path in paths:
            results.extend(scan_path(path, export_csv=args.csv, workers=args.workers))
    except FileNotFoundError as exc:
        parser.error(f"{exc}. Put vehicle images in that folder, or scan the project folder with: python run.py . --csv")
    if args.verbose:
        # ensure_ascii prevents Windows cp1252 consoles from failing on OCR symbols.
        print(json.dumps(results, indent=2, ensure_ascii=True))
    print(f"Processed {len(results)} image(s). Saved report(s) in: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
