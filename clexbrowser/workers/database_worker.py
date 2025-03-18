from PyQt5.QtCore import QThread, pyqtSignal
import sqlite3
import time
import os
from typing import List, Tuple, Dict, Any, Optional, Union

class DatabaseWorker(QThread):
    """
    Base worker class for handling database operations asynchronously.
    
    This class provides the foundation for running database operations
    in a separate thread to keep the UI responsive.
    """
    
    # Signals for communication with the main thread
    progress_signal = pyqtSignal(int)  # Report progress percentage
    status_signal = pyqtSignal(str)  # Report status message
    error_signal = pyqtSignal(str)  # Report error message
    finished_signal = pyqtSignal(bool, str)  # Report completion (success, message)
    result_signal = pyqtSignal(object)  # Return operation result
    
    def __init__(self, db_file: str, device_id=None, device_name=None):
        """
        Initialize the database worker.
        
        Args:
            db_file: Path to the SQLite database file
        """
        super().__init__()
        self.db_file = db_file
        self.device_id = device_id
        self.device_name = device_name
        self.is_cancelled = False
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            A connection to the SQLite database
            
        Raises:
            FileNotFoundError: If the database file doesn't exist
            sqlite3.Error: If connection cannot be established
        """
        if not os.path.exists(self.db_file):
            raise FileNotFoundError(f"Database file not found: {self.db_file}")
        return sqlite3.connect(self.db_file)
    
    def cancel(self):
        """Cancel the currently running operation."""
        self.is_cancelled = True
        self.terminate()
    
    def run(self):
        """
        Execute the worker's task.
        
        This method should be overridden by subclasses.
        """
        pass


class CreateDatabaseWorker(DatabaseWorker):
    """
    Worker for creating or refreshing the database from a log file.
    """
    
    def __init__(self, log_file: str, db_file: str):
        """
        Initialize the database creation worker.
        
        Args:
            log_file: Path to the CLEX log file
            db_file: Path to the SQLite database file
        """
        super().__init__(db_file)
        self.log_file = log_file
    
    def run(self):
        """Process the log file and create the database."""
        try:
            # Import here to avoid circular imports
            from database_creator import process_log_file
            
            # Report initial status
            self.status_signal.emit("Reading log file...")
            self.progress_signal.emit(10)
            
            # Check if the log file exists
            if not os.path.exists(self.log_file):
                raise FileNotFoundError(f"Log file not found: {self.log_file}")
            
            # Read the log file
            with open(self.log_file, 'r') as f:
                log_content = f.read()
            
            # Report progress
            self.status_signal.emit("Parsing technologies...")
            self.progress_signal.emit(30)
            
            # Check for cancellation
            if self.is_cancelled:
                self.finished_signal.emit(False, "Operation cancelled")
                return
            
            # Small delay to show progress
            time.sleep(0.5)
            
            # Report progress
            self.status_signal.emit("Extracting CLEX definitions...")
            self.progress_signal.emit(60)
            
            # Check for cancellation
            if self.is_cancelled:
                self.finished_signal.emit(False, "Operation cancelled")
                return
            
            # Small delay to show progress
            time.sleep(0.5)
            
            # Report progress
            self.status_signal.emit("Creating database...")
            self.progress_signal.emit(80)
            
            # Process the log file and create the database
            process_log_file(self.log_file, self.db_file)
            
            # Report completion
            self.progress_signal.emit(100)
            self.status_signal.emit("Database created successfully!")
            self.finished_signal.emit(True, "")
            
        except Exception as e:
            # Report error
            self.error_signal.emit(str(e))
            self.finished_signal.emit(False, str(e))


class LoadTechnologiesWorker(QThread):
    """
    Worker for loading technologies from the database.
    """
    
    # Define signals
    result_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    
    def __init__(self, db_file: str):
        """
        Initialize the technologies loading worker.
        
        Args:
            db_file: Path to the SQLite database file
        """
        super().__init__()
        self.db_file = db_file
    
    def run(self):
        """Load technologies from the database."""
        try:
            # Report initial status
            self.status_signal.emit("Loading technologies...")
            self.progress_signal.emit(10)
            
            # Ensure database file exists
            if not os.path.exists(self.db_file):
                error_msg = f"Database file not found: {self.db_file}"
                self.error_signal.emit(error_msg)
                print(f"Error: {error_msg}")
                return
            
            # Add explicit print statements for debugging
            print(f"Opening database: {self.db_file}")
            
            # Connect directly to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Load technologies
            print("Executing technology query")
            cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
            self.progress_signal.emit(60)
            
            # Fetch results
            technologies = cursor.fetchall()
            conn.close()
            print(f"Found {len(technologies)} technologies")
            
            # Report completion and return results
            self.progress_signal.emit(100)
            self.status_signal.emit(f"Loaded {len(technologies)} technologies")
            self.result_signal.emit(technologies)
            print("Results emitted")
            
        except Exception as e:
            # Report error with debug output
            error_msg = f"Failed to load technologies: {str(e)}"
            print(f"Error in LoadTechnologiesWorker: {error_msg}")
            self.error_signal.emit(error_msg)

class LoadDevicesWorker(QThread):
    """
    Worker for loading devices for a technology.
    """
    
    # Define signals
    result_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    
    def __init__(self, db_file: str, tech_id: int):
        """
        Initialize the device loading worker.
        
        Args:
            db_file: Path to the SQLite database file
            tech_id: ID of the technology
        """
        super().__init__()
        self.db_file = db_file
        self.tech_id = tech_id
    
    def run(self):
        """Load devices for the specified technology."""
        try:
            # Report initial status
            self.status_signal.emit("Loading devices...")
            self.progress_signal.emit(10)
            
            # Ensure database file exists
            if not os.path.exists(self.db_file):
                self.error_signal.emit(f"Database file not found: {self.db_file}")
                return
            
            # Connect directly to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Load devices
            cursor.execute(
                "SELECT id, name, has_clex_definition FROM devices WHERE technology_id = ? ORDER BY name", 
                (self.tech_id,)
            )
            self.progress_signal.emit(40)
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
            self.progress_signal.emit(80)
            results = {
                "devices": devices,
                "clex_count": clex_count,
                "total_clex": total_clex
            }
            
            # Report completion and return results
            self.progress_signal.emit(100)
            self.status_signal.emit(f"Loaded {len(devices)} devices")
            self.result_signal.emit(results)
            
        except Exception as e:
            # Report error
            self.error_signal.emit(f"Failed to load devices: {str(e)}")

class LoadClexDefinitionWorker(DatabaseWorker):
    """
    Worker for loading a CLEX definition for a device.
    """
    
    def __init__(self, db_file: str, device_id: int, device_name: str):
        """
        Initialize the CLEX definition loading worker.
        
        Args:
            db_file: Path to the SQLite database file
            device_id: ID of the device
            device_name: Name of the device (for reporting)
        """
        super().__init__(db_file)
        self.device_id = device_id
        self.device_name = device_name
    
    def run(self):
        """Load the CLEX definition for the specified device."""
        try:
            # Report initial status
            self.status_signal.emit(f"Loading CLEX definition for {self.device_name}...")
            self.progress_signal.emit(20)
            
            # Get a database connection
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Execute the query
            cursor.execute(
                "SELECT folder_path, file_name, definition_text FROM clex_definitions WHERE device_id = ?", 
                (self.device_id,)
            )
            
            # Report progress
            self.progress_signal.emit(60)
            
            # Check for cancellation
            if self.is_cancelled:
                conn.close()
                self.finished_signal.emit(False, "Operation cancelled")
                return
            
            # Fetch the result
            result = cursor.fetchone()
            
            # Close the connection
            conn.close()
            
            # Report progress
            self.progress_signal.emit(100)
            
            if result:
                folder_path, file_name, definition_text = result
                
                # Process the definition text
                header_text = f"Device: {self.device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n"
                definition_lines = definition_text.split('\n')
                filtered_lines = [
                    line for line in definition_lines 
                    if not line.strip().startswith(("Folder Path:", "File Name:"))
                ]
                filtered_definition = '\n'.join(filtered_lines)
                
                # Prepare the result
                clex_data = {
                    "found": True,
                    "header": header_text,
                    "definition": filtered_definition,
                    "full_text": header_text + filtered_definition
                }
                
                self.status_signal.emit(f"Loaded CLEX definition for {self.device_name}")
            else:
                # No definition found
                clex_data = {
                    "found": False,
                    "message": f"No CLEX definition found for '{self.device_name}'"
                }
                
                self.status_signal.emit(f"No CLEX definition found for {self.device_name}")
            
            # Return the result
            self.result_signal.emit(clex_data)
            self.finished_signal.emit(True, "")
            
        except Exception as e:
            # Report error
            self.error_signal.emit(str(e))
            self.finished_signal.emit(False, str(e))

