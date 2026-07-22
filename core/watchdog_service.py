import time
import os
import threading
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.result_builder import analyse_image
from core.database import save_scan

logger = logging.getLogger(__name__)

class ZebraScannerHandler(FileSystemEventHandler):
    def __init__(self, callback=None):
        self.callback = callback
        self.processing = set()

    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            self.process_image(file_path)

    def process_image(self, file_path):
        # Avoid processing the same file multiple times if events trigger rapidly
        if file_path in self.processing:
            return
        self.processing.add(file_path)
        
        def run_processing():
            try:
                # Wait a bit for the file to finish writing to disk
                time.sleep(1.0)
                logger.info(f"Watchdog picked up new image: {file_path}")
                
                result = analyse_image(Path(file_path))
                
                vin = result.get("vin", {})
                vin_val = vin.get("value") if vin else ""
                
                color = result.get("color", {})
                color_val = color.get("description") or color.get("value") or ""
                
                save_scan(file_path, vin_val, color_val)
                
                if self.callback:
                    self.callback({
                        "image_path": file_path,
                        "vin": vin_val,
                        "color": color_val
                    })
            except Exception as e:
                logger.error(f"Error processing image {file_path}: {e}")
            finally:
                if file_path in self.processing:
                    self.processing.remove(file_path)

        # Run in background to not block watchdog
        threading.Thread(target=run_processing, daemon=True).start()


class ScannerWatchdog:
    def __init__(self, watch_dir: str, callback=None):
        self.watch_dir = watch_dir
        self.callback = callback
        self.observer = None

    def start(self):
        os.makedirs(self.watch_dir, exist_ok=True)
        event_handler = ZebraScannerHandler(callback=self.callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.watch_dir, recursive=False)
        self.observer.start()
        logger.info(f"Watchdog started watching {self.watch_dir}")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watchdog stopped.")
