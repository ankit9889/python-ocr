import logging
import threading
import time
import xml.etree.ElementTree as ET
import winsound

logger = logging.getLogger(__name__)

# Global state to hold the latest scanned barcode from the SDK
LATEST_HARDWARE_VIN = ""

class ZebraEvents:
    def OnBarcodeEvent(self, eventType, pscanData):
        """
        Callback fired by CoreScanner when a barcode is scanned.
        """
        global LATEST_HARDWARE_VIN
        try:
            # pscanData is XML like:
            # <outArgs><scannerID>1</scannerID><arg-xml><scandata>
            # <datalabel>0x31 0x32 0x33</datalabel><datatype>1</datatype></scandata></arg-xml></outArgs>
            root = ET.fromstring(pscanData)
            datalabel = root.find('.//datalabel')
            if datalabel is not None and datalabel.text:
                # Zebra datalabel is often space-separated hex bytes: "0x31 0x32 0x33"
                hex_values = datalabel.text.strip().split()
                if all(h.startswith("0x") for h in hex_values):
                    decoded_string = "".join(chr(int(h, 16)) for h in hex_values)
                else:
                    decoded_string = datalabel.text.strip()
                    
                LATEST_HARDWARE_VIN = decoded_string
                logger.info(f"Zebra SDK Extracted VIN: {LATEST_HARDWARE_VIN}")
        except Exception as e:
            logger.error(f"Error parsing OnBarcodeEvent XML: {e}")

class ZebraScannerManager:
    def __init__(self):
        self.ccore = None
        self.scanner_id = 1
        self.is_connected = False
        
        # Start the background thread for COM message pumping
        self._thread = threading.Thread(target=self._run_com_loop, daemon=True)
        self._thread.start()
        
    def _run_com_loop(self):
        try:
            import pythoncom
            import win32com.client
            
            # COM must be initialized in this thread
            pythoncom.CoInitialize()
            
            # Dispatch with events
            self.ccore = win32com.client.DispatchWithEvents("CoreScanner.CoreScanner", ZebraEvents)
            
            # Open API: AppHandle=0, Types=[1,2,3,4,8] (all types), count=5
            # In pythoncom we can try passing an array, or just basic integers
            # Some versions of CoreScanner expect Open(0, [1], 1, status)
            # We will use late binding or pass dummy values and let pythoncom handle it.
            try:
                # Type 1 = SNAPI, 8 = CDC. We'll pass [1, 8]
                status = self.ccore.Open(0, [1, 8], 2) 
            except:
                try:
                    # Fallback for simple SNAPI
                    status = self.ccore.Open(0, [1], 1)
                except Exception as e:
                    logger.error(f"Failed to Open CoreScanner: {e}")
                    return
            
            # Try to get active scanner ID to send beeps to
            try:
                # GetScanners(numberOfScanners, outXML, status)
                res = self.ccore.GetScanners()
                # res is usually a tuple: (numberOfScanners, outXML, status)
                if isinstance(res, tuple) and len(res) >= 2:
                    out_xml = res[1]
                    root = ET.fromstring(out_xml)
                    first_scanner = root.find('.//scannerID')
                    if first_scanner is not None:
                        self.scanner_id = int(first_scanner.text)
                        logger.info(f"Found active scanner ID: {self.scanner_id}")
            except Exception as e:
                logger.warning(f"Could not discover scanner ID, defaulting to 1: {e}")
            
            # Register for events (Opcode 1001)
            # 1 = Barcode events
            in_xml = """<inArgs>
                          <cmdArgs>
                            <arg-int>1</arg-int>
                            <arg-int>1</arg-int>
                          </cmdArgs>
                        </inArgs>"""
            try:
                self.ccore.ExecCommand(1001, in_xml, "", 0)
                logger.info("Successfully registered for Zebra SDK Barcode events.")
                self.is_connected = True
            except Exception as e:
                logger.error(f"Failed to register for events: {e}")
            
            # Keep the message pump running to receive events
            while True:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.1)
                
        except Exception as e:
            logger.warning(f"Zebra CoreScanner SDK is not available or failed: {e}")
            self.ccore = None

    def get_latest_hardware_vin(self):
        global LATEST_HARDWARE_VIN
        vin = LATEST_HARDWARE_VIN
        # Clear it after reading so we don't accidentally reuse it
        LATEST_HARDWARE_VIN = ""
        return vin

    def hardware_beep(self, beep_code):
        if not self.ccore or not self.is_connected:
            return False
        try:
            in_xml = f"""<inArgs>
                            <scannerID>{self.scanner_id}</scannerID>
                            <cmdArgs>
                                <arg-int>{beep_code}</arg-int>
                            </cmdArgs>
                         </inArgs>"""
            # Opcode 6000 = Action Beep
            self.ccore.ExecCommand(6000, in_xml, "", 0)
            return True
        except Exception as e:
            logger.error(f"Failed to send hardware beep command: {e}")
            return False

scanner_manager = ZebraScannerManager()

def trigger_beep(condition: str):
    """
    Triggers a beep on the Zebra hardware if connected, else falls back to PC speaker.
    Conditions: 'success', 'empty_color', 'duplicate'
    """
    success = False
    if condition == "success":
        # 0 = One short high beep
        success = scanner_manager.hardware_beep(0)
        if not success:
            winsound.Beep(2500, 150)
            
    elif condition == "empty_color":
        # 16 = Low-high beep
        success = scanner_manager.hardware_beep(16)
        if not success:
            winsound.Beep(1200, 600)
            
    elif condition == "duplicate":
        # 13 = Fast warble error beep
        success = scanner_manager.hardware_beep(13)
        if not success:
            winsound.Beep(700, 200)
            winsound.Beep(700, 200)
