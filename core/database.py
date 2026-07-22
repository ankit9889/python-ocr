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
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def save_scan(image_path: str, vin: str, color: str):
    """Saves a scan result into the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert None to empty string for cleaner DB storage
        vin_val = vin if vin else ""
        color_val = color if color else ""
        
        cursor.execute('''
            INSERT INTO scans (timestamp, image_path, vin, color)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, image_path, vin_val, color_val))
        conn.commit()
        conn.close()
        logger.info(f"Scan saved to DB: VIN={vin_val}, Color={color_val}")
    except Exception as e:
        logger.error(f"Failed to save scan to DB: {e}")

def get_recent_scans(limit: int = 50):
    """Fetches the most recent scans from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, image_path, vin, color 
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
                "color": row[4]
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
