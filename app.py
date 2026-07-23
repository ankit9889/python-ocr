import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
import sys
import time
import winsound

from core.database import init_db, save_scan, get_recent_scans, delete_scan, check_vin_exists, update_scan
from core.zebra_scanner import trigger_beep, scanner_manager
from core.watchdog_service import ScannerWatchdog
from core.result_builder import analyse_image
from core.settings import load_settings, save_settings
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

        # Select All Button
        self.select_all_btn = tk.Button(top_frame, text="Select All/None", command=self.toggle_select_all, font=("Arial", 11, "bold"))
        self.select_all_btn.pack(side=tk.LEFT, padx=5)

        # Delete Button
        self.delete_btn = tk.Button(top_frame, text="Delete Checked", command=self.delete_selected, bg="#F44336", fg="white", font=("Arial", 11, "bold"))
        self.delete_btn.pack(side=tk.LEFT, padx=5)

        # Connect Scanner Toggle
        self.scanner_btn = tk.Button(top_frame, text="Connect Hardware Scanner", command=self.toggle_scanner, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
        self.scanner_btn.pack(side=tk.LEFT, padx=10)

        # Settings Button
        self.settings_btn = tk.Button(top_frame, text="⚙️ Settings", command=self.open_settings_dialog, bg="#607D8B", fg="white", font=("Arial", 11, "bold"))
        self.settings_btn.pack(side=tk.LEFT, padx=5)

        # Beep Tester Frame
        beep_frame = tk.Frame(top_frame)
        beep_frame.pack(side=tk.LEFT, padx=10)

        self.beep_var = tk.StringVar()
        self.beep_options = {
            "0: 1 Short High (Default)": 0,
            "1: 2 Short High": 1,
            "2: 3 Short High": 2,
            "3: 4 Short High": 3,
            "4: 5 Short High": 4,
            "5: 1 Short Low": 5,
            "6: 2 Short Low": 6,
            "7: 3 Short Low": 7,
            "8: 4 Short Low": 8,
            "9: 5 Short Low": 9,
            "10: 1 Long High": 10,
            "11: 2 Long High": 11,
            "12: 3 Long High": 12,
            "13: Fast Warble (Error)": 13,
            "14: 5 Long High": 14,
            "15: 1 Long Low": 15,
            "16: Low-High (Empty)": 16,
            "17: High-Low": 17
        }
        self.beep_cb = ttk.Combobox(beep_frame, textvariable=self.beep_var, values=list(self.beep_options.keys()), state="readonly", width=22)
        self.beep_cb.current(0)
        self.beep_cb.pack(side=tk.LEFT)

        self.test_beep_btn = tk.Button(beep_frame, text="🔊 Test Beep", command=self.test_hardware_beep, bg="#9C27B0", fg="white", font=("Arial", 9, "bold"))
        self.test_beep_btn.pack(side=tk.LEFT, padx=5)

        # Status Label
        self.status_lbl = tk.Label(top_frame, text="Ready.", fg="blue", font=("Arial", 10))
        self.status_lbl.pack(side=tk.RIGHT, padx=10)

        # Bottom Frame for Table
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ("chk", "id", "timestamp", "hardware_vin", "vin", "color", "time_s", "image")
        self.tree = ttk.Treeview(bottom_frame, columns=columns, show="headings")
        self.tree.heading("chk", text="[ ]")
        self.tree.heading("id", text="ID")
        self.tree.heading("timestamp", text="Time")
        self.tree.heading("hardware_vin", text="Vin Picked By hardware")
        self.tree.heading("vin", text="VIN")
        self.tree.heading("color", text="Color")
        self.tree.heading("time_s", text="Scan Time (s)")
        self.tree.heading("image", text="Image Path")

        self.tree.column("chk", width=40, anchor=tk.CENTER)
        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("timestamp", width=150, anchor=tk.CENTER)
        self.tree.column("hardware_vin", width=180, anchor=tk.CENTER)
        self.tree.column("vin", width=180, anchor=tk.CENTER)
        self.tree.column("color", width=180, anchor=tk.CENTER)
        self.tree.column("time_s", width=100, anchor=tk.CENTER)
        self.tree.column("image", width=250, anchor=tk.W)

        # Bind Click for Checkboxes and Ctrl+A
        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        self.tree.bind("<Control-a>", self.select_all_shortcut)
        self.tree.bind("<Control-A>", self.select_all_shortcut)

        # Scrollbar
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1":  # The 'chk' column
                item = self.tree.identify_row(event.y)
                if item:
                    values = list(self.tree.item(item, "values"))
                    # Toggle checkbox
                    if values[0] == "[ ]":
                        values[0] = "[x]"
                    else:
                        values[0] = "[ ]"
                    self.tree.item(item, values=values)

    def toggle_select_all(self):
        """Toggle all checkboxes."""
        all_checked = True
        for item in self.tree.get_children():
            if self.tree.item(item, "values")[0] == "[ ]":
                all_checked = False
                break
        
        new_val = "[ ]" if all_checked else "[x]"
        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            values[0] = new_val
            self.tree.item(item, values=values)

    def select_all_shortcut(self, event):
        """Ctrl+A sets all checkboxes to checked."""
        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            values[0] = "[x]"
            self.tree.item(item, values=values)
        return "break"

    def refresh_table(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load recent scans
        scans = get_recent_scans()
        for scan in scans:
            self.tree.insert("", tk.END, values=(
                "[ ]",
                scan["id"],
                scan["timestamp"],
                scan.get("hardware_vin", ""),
                scan["vin"],
                scan["color"],
                f"{scan.get('processing_time', 0.0):.2f}",
                os.path.basename(scan["image_path"])
            ))

    def on_scan_completed(self, result):
        # This is called by watchdog_service in a background thread
        self.handle_processed_scan(
            result["image_path"],
            result["vin"],
            result["color"],
            result["processing_time"]
        )

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

    def test_hardware_beep(self):
        selected = self.beep_var.get()
        if selected in self.beep_options:
            beep_code = self.beep_options[selected]
            success = scanner_manager.hardware_beep(beep_code)
            if not success:
                messagebox.showwarning("Scanner Not Ready", "Hardware scanner is not connected or COM object not ready.\\nPlease make sure 123Scan is closed and SDK is installed.")
            else:
                self.status_lbl.config(text=f"Tested beep: {selected}", fg="green")

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

    def handle_processed_scan(self, file_path, vin_val, color_val, processing_time):
        existing_scan_id = check_vin_exists(vin_val) if vin_val else None
        
        # Get hardware vin from the global scanner SDK manager
        hardware_vin_val = scanner_manager.get_latest_hardware_vin()
        
        if existing_scan_id:
            # Duplicate VIN: Only Beep, Do Not Save, Do Not Ask
            trigger_beep("duplicate")
            return
            
        if not color_val:
            # Color is empty: Only Beep, Do Not Save
            trigger_beep("empty_color")
            return
            
        # If it reaches here, it's a completely successful new scan
        save_scan(file_path, vin_val, color_val, processing_time, hardware_vin_val)
        trigger_beep("success")
        
        # Update UI thread-safely
        self.root.after(0, self._update_ui_after_scan, {
            "image_path": file_path,
            "vin": vin_val,
            "color": color_val,
            "processing_time": processing_time
        })

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
                
                self.handle_processed_scan(file_path, vin_val, color_val, processing_time)
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.root.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to process image:\n{err}"))
        
        self.is_processing = False
        self.root.after(0, lambda: self.status_lbl.config(text="Processing complete.", fg="green"))

    def delete_selected(self):
        # Get items where checkbox column is "[x]"
        selected_items = [item for item in self.tree.get_children() if self.tree.item(item, "values")[0] == "[x]"]
        
        if not selected_items:
            messagebox.showwarning("Warning", "Please check at least one record to delete (click the [ ] column).")
            return
        
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected_items)} checked scan(s)?")
        if confirm:
            for item in selected_items:
                values = self.tree.item(item, 'values')
                scan_id = int(values[1])  # column index 1 is now ID
                delete_scan(scan_id)
            
            self.refresh_table()
            self.status_lbl.config(text=f"{len(selected_items)} record(s) deleted.", fg="blue")

    def open_settings_dialog(self):
        settings = load_settings()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("OCR Performance Settings")
        dialog.geometry("400x300")
        dialog.grab_set() # Modal
        
        ttk.Label(dialog, text="Select OCR Engine:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=20, pady=(15, 5))
        
        engine_var = tk.StringVar(value=settings.get("engine", "default"))
        ttk.Radiobutton(dialog, text="Default CPU (Safest)", variable=engine_var, value="default").pack(anchor=tk.W, padx=30)
        ttk.Radiobutton(dialog, text="ONNX Runtime (Fast & Low RAM)", variable=engine_var, value="onnx").pack(anchor=tk.W, padx=30)
        ttk.Radiobutton(dialog, text="Intel OpenVINO (Ultra Fast for Intel)", variable=engine_var, value="openvino").pack(anchor=tk.W, padx=30)
        
        ttk.Label(dialog, text="Optimizations:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=20, pady=(15, 5))
        
        crop_var = tk.BooleanVar(value=settings.get("smart_crop", False))
        ttk.Checkbutton(dialog, text="Enable Smart Region Cropping (20% faster)", variable=crop_var).pack(anchor=tk.W, padx=30)
        
        batch_var = tk.BooleanVar(value=settings.get("batching", False))
        ttk.Checkbutton(dialog, text="Enable Dynamic Batching", variable=batch_var).pack(anchor=tk.W, padx=30)
        
        angle_var = tk.BooleanVar(value=settings.get("angle_classifier", False))
        ttk.Checkbutton(dialog, text="Enable Angle Classifier (Fixes warning but 30% slower)", variable=angle_var).pack(anchor=tk.W, padx=30)
        
        def save_and_close():
            new_settings = {
                "engine": engine_var.get(),
                "smart_crop": crop_var.get(),
                "batching": batch_var.get(),
                "angle_classifier": angle_var.get()
            }
            save_settings(new_settings)
            
            # Re-initialize the OCR engine globally to apply changes immediately
            from core.ocr_engine import set_device_preference
            set_device_preference("cpu") # This will implicitly reload settings inside ocr_engine
            
            dialog.destroy()
            
        ttk.Button(dialog, text="Save Settings", command=save_and_close).pack(pady=20)

    def on_closing(self):
        if self.watchdog:
            self.watchdog.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
