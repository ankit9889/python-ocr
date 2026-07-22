import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import time

from core.database import init_db, save_scan, get_recent_scans, delete_scan
from core.watchdog_service import ScannerWatchdog
from core.result_builder import analyse_image
from pathlib import Path

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vehicle Scanner (Zebra Edition)")
        self.root.geometry("950x650")

        # Initialize DB
        init_db()

        self.watch_dir = os.path.join(os.getcwd(), "live_scans")
        self.watchdog = None
        self.is_scanner_connected = False
        self.upload_queue = []
        self.is_processing = False

        # Build UI
        self.build_ui()

        # Load initial data
        self.refresh_table()

    def build_ui(self):
        # Top Frame for Actions
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)

        # Upload Button
        self.upload_btn = tk.Button(top_frame, text="Upload Images", command=self.upload_images, bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
        self.upload_btn.pack(side=tk.LEFT, padx=10)

        # Delete Button
        self.delete_btn = tk.Button(top_frame, text="Delete Selected", command=self.delete_selected, bg="#F44336", fg="white", font=("Arial", 11, "bold"))
        self.delete_btn.pack(side=tk.LEFT, padx=10)

        # Connect Scanner Toggle
        self.scanner_btn = tk.Button(top_frame, text="Connect Hardware Scanner", command=self.toggle_scanner, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
        self.scanner_btn.pack(side=tk.LEFT, padx=10)

        # Status Label
        self.status_lbl = tk.Label(top_frame, text="Ready.", fg="blue", font=("Arial", 10))
        self.status_lbl.pack(side=tk.RIGHT, padx=20)

        # Bottom Frame for Table
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ("id", "timestamp", "vin", "color", "time_s", "image")
        self.tree = ttk.Treeview(bottom_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("timestamp", text="Time")
        self.tree.heading("vin", text="VIN")
        self.tree.heading("color", text="Color")
        self.tree.heading("time_s", text="Scan Time (s)")
        self.tree.heading("image", text="Image Path")

        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("timestamp", width=150, anchor=tk.CENTER)
        self.tree.column("vin", width=180, anchor=tk.CENTER)
        self.tree.column("color", width=180, anchor=tk.CENTER)
        self.tree.column("time_s", width=100, anchor=tk.CENTER)
        self.tree.column("image", width=250, anchor=tk.W)

        # Scrollbar
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
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
                f"{scan.get('processing_time', 0.0):.2f}",
                os.path.basename(scan["image_path"])
            ))

    def on_scan_completed(self, result):
        # Update UI thread-safely
        self.root.after(0, self._update_ui_after_scan, result)

    def _update_ui_after_scan(self, result):
        time_str = f" in {result.get('processing_time', 0.0):.2f}s" if 'processing_time' in result else ""
        self.status_lbl.config(text=f"Last Scan: {result['vin']} - {result['color']}{time_str}", fg="green")
        self.refresh_table()

    def toggle_scanner(self):
        if not self.is_scanner_connected:
            # Connect
            self.watchdog = ScannerWatchdog(self.watch_dir, callback=self.on_scan_completed)
            self.watchdog.start()
            self.is_scanner_connected = True
            self.scanner_btn.config(text="Disconnect Scanner", bg="#FF9800")
            
            messagebox.showinfo("Scanner Connected", 
                f"Watchdog Started!\n\n"
                f"Please configure your Zebra DS4608 to save images directly into this folder:\n\n"
                f"{self.watch_dir}\n\n"
                f"Images dropped here will be processed instantly."
            )
            self.status_lbl.config(text="Scanner Connected. Waiting for drops...", fg="blue")
        else:
            # Disconnect
            if self.watchdog:
                self.watchdog.stop()
                self.watchdog = None
            self.is_scanner_connected = False
            self.scanner_btn.config(text="Connect Hardware Scanner", bg="#2196F3")
            self.status_lbl.config(text="Scanner Disconnected.", fg="blue")

    def upload_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Vehicle Label Images",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not file_paths:
            return
        
        self.upload_queue.extend(file_paths)
        if not self.is_processing:
            self.is_processing = True
            threading.Thread(target=self.process_queue, daemon=True).start()

    def process_queue(self):
        while self.upload_queue:
            file_path = self.upload_queue.pop(0)
            self.root.after(0, lambda f=file_path: self.status_lbl.config(text=f"Processing {os.path.basename(f)}... ({len(self.upload_queue)} left)", fg="orange"))
            
            try:
                start_time = time.time()
                result = analyse_image(Path(file_path))
                processing_time = time.time() - start_time
                
                vin = result.get("vin", {})
                vin_val = vin.get("value") if vin else ""
                
                color = result.get("color", {})
                color_val = color.get("description") or color.get("value") or ""
                
                save_scan(file_path, vin_val, color_val, processing_time)
                
                self.on_scan_completed({
                    "image_path": file_path,
                    "vin": vin_val,
                    "color": color_val,
                    "processing_time": processing_time
                })
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.root.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to process image:\n{err}"))
        
        self.is_processing = False
        self.root.after(0, lambda: self.status_lbl.config(text="Processing complete.", fg="green"))

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a record to delete.")
            return
        
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected scan(s)?")
        if confirm:
            for item in selected_items:
                values = self.tree.item(item, 'values')
                scan_id = int(values[0])
                delete_scan(scan_id)
            
            self.refresh_table()
            self.status_lbl.config(text="Record(s) deleted.", fg="blue")

    def on_closing(self):
        if self.watchdog:
            self.watchdog.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
