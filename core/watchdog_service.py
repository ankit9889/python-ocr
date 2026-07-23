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

from concurrent.futures import ThreadPoolExecutor

class ZebraScannerHandler(FileSystemEventHandler):
    def __init__(self, callback=None):
        self.callback = callback
        self.processing = set()
        self.executor = ThreadPoolExecutor(max_workers=1)

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
                from core.zebra_scanner import scanner_manager
                scanner_manager.disable_scanner()

                # Tell app processing started
                if hasattr(self, 'app') and self.app:
                    self.app.is_processing = True
                
                # Wait a bit for the file to finish writing to disk
                time.sleep(1.0)
                logger.info(f"Watchdog picked up new image: {file_path}")
                
                start_time = time.time()
                result = analyse_image(Path(file_path))
                processing_time = time.time() - start_time
                
                vin = result.get("vin", {})
                vin_val = vin.get("value") if vin else ""
                
                color = result.get("color", {})
                color_val = color.get("description") or color.get("value") or ""
                
                if self.callback:
                    self.callback({
                        "image_path": file_path,
                        "vin": vin_val,
                        "color": color_val,
                        "processing_time": processing_time
                    })
            except Exception as e:
                logger.error(f"Error processing image {file_path}: {e}")
            finally:
                if file_path in self.processing:
                    self.processing.remove(file_path)
                
                try:
                    from core.zebra_scanner import scanner_manager
                    scanner_manager.enable_scanner()
                except Exception as e:
                    logger.error(f"Failed to enable scanner: {e}")

        # Run sequentially in background to not block watchdog, but prevent CPU starvation from multiple OCR threads
        self.executor.submit(run_processing)


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
