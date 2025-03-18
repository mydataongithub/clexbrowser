# workers/fixed_device_loader.py
from PyQt5.QtCore import QThread, pyqtSignal
import sqlite3
import os

class SafeLoadDevicesWorker(QThread):
    """
    Safe worker for loading devices with minimal dependencies.
    
    This simplified implementation focuses on reliable device loading
    with proper error handling and minimal external dependencies.
    """
    
    # Signals for communication with main thread
    result_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    
    def __init__(self, db_file, tech_id):
        """
        Initialize the worker.
        
        Args:
            db_file: Path to SQLite database file
            tech_id: ID of the technology to load devices for
        """
        super().__init__()
        self.db_file = db_file
        self.tech_id = tech_id
        
    def run(self):
        """Load devices from the database."""
        try:
            # Ensure database file exists
            if not os.path.exists(self.db_file):
                self.error_signal.emit(f"Database file not found: {self.db_file}")
                return
                
            # Connect to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Load devices
            cursor.execute(
                "SELECT id, name, has_clex_definition FROM devices WHERE technology_id = ? ORDER BY name", 
                (self.tech_id,)
            )
            devices = cursor.fetchall()
            
            # Load statistics
            cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE technology_id = ? AND has_clex_definition = 1", 
                (self.tech_id,)
            )
            clex_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM clex_definitions c JOIN devices d ON c.device_id = d.id WHERE d.technology_id = ?", 
                (self.tech_id,)
            )
            total_clex = cursor.fetchone()[0]
            
            # Close connection
            conn.close()
            
            # Prepare results
            results = {
                "devices": devices,
                "clex_count": clex_count,
                "total_clex": total_clex
            }
            
            # Return results
            self.result_signal.emit(results)
            
        except Exception as e:
            self.error_signal.emit(f"Failed to load devices: {str(e)}")