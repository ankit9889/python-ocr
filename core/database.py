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
            
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def save_scan(image_path: str, vin: str, color: str, processing_time: float = 0.0):
    """Saves a scan result into the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        vin_val = vin if vin else ""
        color_val = color if color else ""
        
        cursor.execute('''
            INSERT INTO scans (timestamp, image_path, vin, color, processing_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, image_path, vin_val, color_val, processing_time))
        conn.commit()
        conn.close()
        logger.info(f"Scan saved to DB: VIN={vin_val}, Color={color_val}, Time={processing_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to save scan to DB: {e}")

def get_recent_scans(limit: int = 50):
    """Fetches the most recent scans from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, image_path, vin, color, processing_time
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
                "processing_time": row[5] if len(row) > 5 and row[5] is not None else 0.0
            })
        return results
    except Exception as e:
        logger.error(f"Failed to fetch recent scans: {e}")
        return []

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
