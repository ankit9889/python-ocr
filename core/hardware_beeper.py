import logging
import winsound

logger = logging.getLogger(__name__)

class ZebraHardwareBeeper:
    def __init__(self):
        self.ccore = None
        self.scanner_id = 1
        try:
            import win32com.client
            self.ccore = win32com.client.Dispatch("CoreScanner.CoreScanner")
            # Open API: appHandle=0, scannerTypes=1 (SNAPI), noOfScannerTypes=1
            self.ccore.Open(0, [1], 1) 
            logger.info("Zebra CoreScanner initialized successfully.")
        except Exception as e:
            logger.warning(f"Zebra CoreScanner not available (fallback to PC speaker will be used): {e}")

    def hardware_beep(self, beep_code):
        if not self.ccore:
            return False
        try:
            in_xml = f"""<inArgs>
                            <scannerID>{self.scanner_id}</scannerID>
                            <cmdArgs>
                                <arg-int>{beep_code}</arg-int>
                            </cmdArgs>
                         </inArgs>"""
            # Opcode 6000 is for Action Beep
            self.ccore.ExecCommand(6000, in_xml, "", 0)
            return True
        except Exception as e:
            logger.error(f"Failed to send hardware beep command: {e}")
            return False

beeper_instance = ZebraHardwareBeeper()

def trigger_beep(condition: str):
    """
    Triggers a beep on the Zebra hardware if connected, else falls back to PC speaker.
    Conditions: 'success', 'empty_color', 'duplicate'
    """
    success = False
    if condition == "success":
        # 0 = One short high beep
        success = beeper_instance.hardware_beep(0)
        if not success:
            winsound.Beep(2500, 150)
            
    elif condition == "empty_color":
        # 16 = Low-high beep (Attention)
        success = beeper_instance.hardware_beep(16)
        if not success:
            winsound.Beep(1200, 600)
            
    elif condition == "duplicate":
        # 20 = Error double beep (high-low) or 13 = Fast warble
        success = beeper_instance.hardware_beep(13)
        if not success:
            winsound.Beep(700, 200)
            winsound.Beep(700, 200)
