import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys

from core.database import init_db, save_scan, get_recent_scans
from core.watchdog_service import ScannerWatchdog
from core.result_builder import analyse_image
from pathlib import Path

# Setup simple logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vehicle Scanner (Zebra Edition)")
        self.root.geometry("800x600")

        # Initialize DB
        init_db()

        # Build UI
        self.build_ui()

        # Load initial data
        self.refresh_table()

        # Start Watchdog
        self.watch_dir = os.path.join(os.getcwd(), "live_scans")
        self.watchdog = ScannerWatchdog(self.watch_dir, callback=self.on_scan_completed)
        self.watchdog.start()

    def build_ui(self):
        # Top Frame for Actions
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)

        self.upload_btn = tk.Button(top_frame, text="Upload Image Manually", command=self.upload_image, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.upload_btn.pack(side=tk.LEFT, padx=20)

        self.status_lbl = tk.Label(top_frame, text="Waiting for scans...", fg="blue", font=("Arial", 10))
        self.status_lbl.pack(side=tk.RIGHT, padx=20)

        # Bottom Frame for Table
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ("id", "timestamp", "vin", "color", "image")
        self.tree = ttk.Treeview(bottom_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("timestamp", text="Time")
        self.tree.heading("vin", text="VIN")
        self.tree.heading("color", text="Color")
        self.tree.heading("image", text="Image Path")

        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("timestamp", width=150, anchor=tk.CENTER)
        self.tree.column("vin", width=200, anchor=tk.CENTER)
        self.tree.column("color", width=150, anchor=tk.CENTER)
        self.tree.column("image", width=200, anchor=tk.W)

        self.tree.pack(fill=tk.BOTH, expand=True)

    def refresh_table(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load recent scans
        scans = get_recent_scans()
        for scan in scans:
            self.tree.insert("", tk.END, values=(
                scan["id"],
                scan["timestamp"],
                scan["vin"],
                scan["color"],
                os.path.basename(scan["image_path"])
            ))

    def on_scan_completed(self, result):
        # This is called from a background thread by watchdog, we need to update UI thread-safely
        self.root.after(0, self._update_ui_after_scan, result)

    def _update_ui_after_scan(self, result):
        self.status_lbl.config(text=f"Last Scan: {result['vin']} - {result['color']}", fg="green")
        self.refresh_table()

    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Vehicle Label Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not file_path:
            return
        
        self.status_lbl.config(text="Processing image...", fg="orange")
        self.root.update()

        # Run process in thread to not freeze UI
        threading.Thread(target=self.process_manual_upload, args=(file_path,), daemon=True).start()

    def process_manual_upload(self, file_path):
        try:
            result = analyse_image(Path(file_path))
            
            vin = result.get("vin", {})
            vin_val = vin.get("value") if vin else ""
            
            color = result.get("color", {})
            color_val = color.get("value") if color else ""
            
            save_scan(file_path, vin_val, color_val)
            
            self.on_scan_completed({
                "image_path": file_path,
                "vin": vin_val,
                "color": color_val
            })
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.root.after(0, lambda: self.status_lbl.config(text="Error during processing!", fg="red"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to process image:\n{e}"))

    def on_closing(self):
        self.watchdog.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
