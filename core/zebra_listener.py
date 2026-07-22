import time
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import win32com.client
import pythoncom
import threading

# Directory to save live scans
SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "live_scans")

class ZebraScannerEvents:
    def OnImageEvent(self, eventType, scanData):
        """Triggered automatically by the Zebra scanner when an image is captured."""
        print("\n[Zebra] Image captured! Processing...")
        try:
            # Parse the XML data from the scanner
            root = ET.fromstring(scanData)
            
            # The image data is usually in <imagedata> as a HEX string
            image_data_hex = root.find('.//imagedata')
            
            if image_data_hex is not None and image_data_hex.text:
                # Convert HEX string back to binary image bytes
                image_bytes = bytes.fromhex(image_data_hex.text)
                
                os.makedirs(SAVE_DIR, exist_ok=True)
                filename = os.path.join(SAVE_DIR, f"zebra_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                
                with open(filename, "wb") as f:
                    f.write(image_bytes)
                    
                print(f"[Zebra] Successfully saved image to: {filename}")
            else:
                print("[Zebra] Error: No image data found in the scanner event.")
                
        except Exception as e:
            print(f"[Zebra] Error saving image: {e}")

    def OnBarcodeEvent(self, eventType, scanData):
        print("[Zebra] Barcode scanned (ignored for image capture mode).")

def start_zebra_listener():
    print("Starting Zebra Scanner Background Listener...")
    try:
        # Initialize COM
        pythoncom.CoInitialize()
        
        # Connect to the Zebra CoreScanner driver
        # DispatchWithEvents allows us to listen to scanner triggers
        cc = win32com.client.DispatchWithEvents("CoreScanner.CoreScanner", ZebraScannerEvents)
        
        # Open connection: appType=0, scannerTypes=(1,) (SNAPI), count=1
        # In win32com, out parameters shouldn't be lists. 
        cc.Open(0, (1,), 1, 0)
        
        # Register for events: 1 = Barcode, 2 = Image
        # Opcode 1001 is REGISTER_FOR_EVENTS
        in_xml = "<inArgs><cmdArgs><arg-int>2</arg-int><arg-int>1,2</arg-int></cmdArgs></inArgs>"
        cc.ExecCommand(1001, in_xml, "", 0)
        
        print("Connected to Zebra Scanner in SNAPI mode!")
        print(f"Waiting for you to pull the trigger... (Images will Auto-Save to {SAVE_DIR})")
        
        # Keep the script running to listen for events
        while True:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
            
    except Exception as e:
        print(f"\n[Error] Could not connect to Zebra Scanner: {e}")
        print("Please ensure:")
        print("1. Zebra Scanner SDK is installed.")
        print("2. The scanner is set to 'SNAPI with Imaging' mode.")
        print("3. No other Zebra app (like 123Scan or C# Sample App) is currently open.")

if __name__ == "__main__":
    start_zebra_listener()
