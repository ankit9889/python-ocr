import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DB_PATH = "scans.db"

def init_db():
    """Initializes the SQLite database and creates the scans table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                image_path TEXT NOT NULL,
                vin TEXT,
                color TEXT
            )
        ''')
        # Check if processing_time column exists, add it if not (for migration)
        cursor.execute("PRAGMA table_info(scans)")
        columns = [col[1] for col in cursor.fetchall()]
        if "processing_time" not in columns:
            cursor.execute("ALTER TABLE scans ADD COLUMN processing_time REAL DEFAULT 0.0")
        if "hardware_vin" not in columns:
            cursor.execute("ALTER TABLE scans ADD COLUMN hardware_vin TEXT DEFAULT ''")
            
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def save_scan(image_path: str, vin: str, color: str, processing_time: float = 0.0, hardware_vin: str = ""):
    """Saves a scan result into the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        vin_val = vin if vin else ""
        color_val = color if color else ""
        hw_vin_val = hardware_vin if hardware_vin else ""
        
        cursor.execute('''
            INSERT INTO scans (timestamp, image_path, vin, color, processing_time, hardware_vin)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, image_path, vin_val, color_val, processing_time, hw_vin_val))
        conn.commit()
        conn.close()
        logger.info(f"Scan saved to DB: HW_VIN={hw_vin_val}, VIN={vin_val}, Color={color_val}, Time={processing_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to save scan to DB: {e}")

def get_recent_scans(limit: int = 50):
    """Fetches the most recent scans from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, image_path, vin, color, processing_time, hardware_vin
            FROM scans 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts for easier consumption in UI
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "timestamp": row[1],
                "image_path": row[2],
                "vin": row[3],
                "color": row[4],
                "processing_time": row[5] if len(row) > 5 and row[5] is not None else 0.0,
                "hardware_vin": row[6] if len(row) > 6 and row[6] is not None else ""
            })
        return results
    except Exception as e:
        logger.error(f"Failed to fetch recent scans: {e}")
        return []

def check_vin_exists(vin: str):
    """Checks if a VIN exists and returns its ID."""
    if not vin:
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM scans WHERE vin = ? ORDER BY timestamp DESC LIMIT 1', (vin,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Failed to check VIN: {e}")
        return None

def update_scan(scan_id: int, image_path: str, color: str, processing_time: float = 0.0, hardware_vin: str = ""):
    """Updates an existing scan."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color_val = color if color else ""
        hw_vin_val = hardware_vin if hardware_vin else ""
        
        cursor.execute('''
            UPDATE scans 
            SET timestamp = ?, image_path = ?, color = ?, processing_time = ?, hardware_vin = ?
            WHERE id = ?
        ''', (timestamp, image_path, color_val, processing_time, hw_vin_val, scan_id))
        conn.commit()
        conn.close()
        logger.info(f"Scan updated in DB: ID={scan_id}")
    except Exception as e:
        logger.error(f"Failed to update scan DB: {e}")

def delete_scan(scan_id: int):
    """Deletes a scan record from the database by ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
        conn.commit()
        conn.close()
        logger.info(f"Deleted scan ID {scan_id} from DB.")
    except Exception as e:
        logger.error(f"Failed to delete scan ID {scan_id}: {e}")
