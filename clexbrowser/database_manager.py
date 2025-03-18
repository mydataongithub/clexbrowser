import sqlite3
import os
from typing import List, Tuple, Dict, Any, Optional, Union
from datetime import datetime

class DatabaseManager:
    """
    Manages all database operations for the CLEX Browser application.
    
    This class centralizes database access, providing a clean interface
    for querying and modifying data while handling connections and errors.
    """
    
    def __init__(self, db_file: str):
        """
        Initialize the database manager with the specified database file.
        
        Args:
            db_file: Path to the SQLite database file
        """
        self.db_file = db_file
        
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            A connection to the SQLite database
        
        Raises:
            sqlite3.Error: If connection cannot be established
        """
        if not os.path.exists(self.db_file):
            raise FileNotFoundError(f"Database file not found: {self.db_file}")
        return sqlite3.connect(self.db_file)
    
    def get_technologies(self) -> List[Tuple[int, str, str]]:
        """
        Retrieve all technologies from the database.
        
        Returns:
            List of tuples containing (id, name, version)
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
                return cursor.fetchall()
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to load technologies: {e}")
    
    def get_devices(self, tech_id: int) -> List[Tuple[int, str, int]]:
        """
        Retrieve all devices for a specific technology.
        
        Args:
            tech_id: The ID of the technology
            
        Returns:
            List of tuples containing (id, name, has_clex_definition)
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, has_clex_definition FROM devices WHERE technology_id = ? ORDER BY name", 
                    (tech_id,)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to load devices: {e}")
    
    def get_tech_statistics(self, tech_id: int) -> Dict[str, int]:
        """
        Get statistics for a specific technology.
        
        Args:
            tech_id: The ID of the technology
            
        Returns:
            Dictionary containing statistics (total_devices, clex_devices, total_clex)
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Get total devices
                cursor.execute("SELECT COUNT(*) FROM devices WHERE technology_id = ?", (tech_id,))
                total_devices = cursor.fetchone()[0]
                
                # Get devices with CLEX
                cursor.execute(
                    "SELECT COUNT(*) FROM devices WHERE technology_id = ? AND has_clex_definition = 1", 
                    (tech_id,)
                )
                clex_devices = cursor.fetchone()[0]
                
                # Get total CLEX definitions
                cursor.execute(
                    "SELECT COUNT(*) FROM clex_definitions c JOIN devices d ON c.device_id = d.id "
                    "WHERE d.technology_id = ?", 
                    (tech_id,)
                )
                total_clex = cursor.fetchone()[0]
                
                return {
                    "total_devices": total_devices,
                    "clex_devices": clex_devices,
                    "total_clex": total_clex
                }
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to load technology statistics: {e}")
    
    def get_clex_definition(self, device_id: int) -> Optional[Tuple[str, str, str]]:
        """
        Get the CLEX definition for a device.
        
        Args:
            device_id: The ID of the device
            
        Returns:
            Tuple containing (folder_path, file_name, definition_text) or None if not found
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT folder_path, file_name, definition_text FROM clex_definitions WHERE device_id = ?", 
                    (device_id,)
                )
                return cursor.fetchone()
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to load CLEX definition: {e}")
    
    def get_device_info(self, device_id: int) -> Optional[Tuple[int, str, int]]:
        """
        Get information about a device.
        
        Args:
            device_id: The ID of the device
            
        Returns:
            Tuple containing (technology_id, device_name, has_clex_definition) or None if not found
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT technology_id, name, has_clex_definition FROM devices WHERE id = ?", 
                    (device_id,)
                )
                return cursor.fetchone()
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to get device info: {e}")
    
    def update_clex_definition(self, device_id: int, folder_path: str, file_name: str, 
                               definition_text: str) -> bool:
        """
        Update an existing CLEX definition.
        
        Args:
            device_id: The ID of the device
            folder_path: The folder path
            file_name: The file name
            definition_text: The CLEX definition text
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE clex_definitions SET folder_path = ?, file_name = ?, definition_text = ? "
                    "WHERE device_id = ?", 
                    (folder_path, file_name, definition_text, device_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to update CLEX definition: {e}")
    
    def add_clex_definition(self, device_id: int, folder_path: str, file_name: str, 
                            definition_text: str) -> bool:
        """
        Add a new CLEX definition for an existing device.
        
        Args:
            device_id: The ID of the device
            folder_path: The folder path
            file_name: The file name
            definition_text: The CLEX definition text
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # First update the device to indicate it has a CLEX definition
                cursor.execute(
                    "UPDATE devices SET has_clex_definition = 1 WHERE id = ?", 
                    (device_id,)
                )
                
                # Then add the CLEX definition
                cursor.execute(
                    "INSERT INTO clex_definitions (device_id, folder_path, file_name, definition_text) "
                    "VALUES (?, ?, ?, ?)", 
                    (device_id, folder_path, file_name, definition_text)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to add CLEX definition: {e}")
    
    def delete_clex_definition(self, device_id: int) -> bool:
        """
        Delete a CLEX definition.
        
        Args:
            device_id: The ID of the device
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Delete the CLEX definition
                cursor.execute("DELETE FROM clex_definitions WHERE device_id = ?", (device_id,))
                
                # Update the device to indicate it no longer has a CLEX definition
                cursor.execute("UPDATE devices SET has_clex_definition = 0 WHERE id = ?", (device_id,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to delete CLEX definition: {e}")

    def create_new_device_with_clex(self, device_name: str, tech_id: int, folder_path: str, 
                                  file_name: str, definition_text: str) -> int:
        """
        Create a new device with a CLEX definition.
        
        Args:
            device_name: Name of the device
            tech_id: ID of the technology
            folder_path: Folder path for the CLEX definition
            file_name: File name for the CLEX definition
            definition_text: The CLEX definition text
            
        Returns:
            ID of the newly created device
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Create a new device
                cursor.execute(
                    "INSERT INTO devices (name, technology_id, has_clex_definition) VALUES (?, ?, 1)", 
                    (device_name, tech_id)
                )
                device_id = cursor.lastrowid
                
                # Add the CLEX definition
                cursor.execute(
                    "INSERT INTO clex_definitions (device_id, folder_path, file_name, definition_text) "
                    "VALUES (?, ?, ?, ?)", 
                    (device_id, folder_path, file_name, definition_text)
                )
                conn.commit()
                return device_id
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to create device with CLEX definition: {e}")
    
    def device_name_exists(self, device_name: str, tech_id: int) -> bool:
        """
        Check if a device name already exists in a technology.
        
        Args:
            device_name: Name of the device to check
            tech_id: ID of the technology
            
        Returns:
            True if the device name exists, False otherwise
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM devices WHERE name = ? AND technology_id = ?", 
                    (device_name, tech_id)
                )
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to check device name: {e}")
    
    def search_devices_and_clex(self, search_text: str, case_sensitive: bool = False, 
                              search_devices: bool = True, search_defs: bool = True) -> List[Tuple]:
        """
        Search for devices and CLEX definitions.
        
        Args:
            search_text: Text to search for
            case_sensitive: Whether to use case-sensitive search
            search_devices: Whether to search device names
            search_defs: Whether to search CLEX definitions
            
        Returns:
            List of search results
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        results = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if search_devices:
                    query = (
                        "SELECT d.id, d.name, t.name, t.id FROM devices d "
                        "JOIN technologies t ON d.technology_id = t.id WHERE " + 
                        ("d.name LIKE ?" if case_sensitive else "LOWER(d.name) LIKE LOWER(?)") + 
                        " ORDER BY t.name, d.name"
                    )
                    cursor.execute(query, (f"%{search_text}%",))
                    for device_id, device_name, tech_name, tech_id in cursor.fetchall():
                        results.append((device_id, device_name, tech_name, tech_id, "Device Name", device_name))
                
                if search_defs:
                    query = (
                        "SELECT d.id, d.name, t.name, t.id, c.definition_text FROM clex_definitions c "
                        "JOIN devices d ON c.device_id = d.id "
                        "JOIN technologies t ON d.technology_id = t.id WHERE " + 
                        ("c.definition_text LIKE ?" if case_sensitive else "LOWER(c.definition_text) LIKE LOWER(?)") + 
                        " ORDER BY t.name, d.name"
                    )
                    cursor.execute(query, (f"%{search_text}%",))
                    for device_id, device_name, tech_name, tech_id, definition_text in cursor.fetchall():
                        match_pos = (
                            definition_text.find(search_text) if case_sensitive 
                            else definition_text.lower().find(search_text.lower())
                        )
                        if match_pos >= 0:
                            start_line = (
                                definition_text.rfind('\n', 0, match_pos) + 1 
                                if definition_text.rfind('\n', 0, match_pos) >= 0 else 0
                            )
                            end_line = (
                                definition_text.find('\n', match_pos) 
                                if definition_text.find('\n', match_pos) >= 0 else len(definition_text)
                            )
                            context = definition_text[start_line:end_line]
                            results.append((device_id, device_name, tech_name, tech_id, "CLEX Definition", context))
                
                return results
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to perform search: {e}")