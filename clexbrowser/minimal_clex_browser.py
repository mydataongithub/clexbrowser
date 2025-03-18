import sys
import os
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                            QTextEdit, QSplitter, QMessageBox, QStatusBar)
from PyQt5.QtCore import Qt, QSettings

class MinimalCLEXBrowser(QMainWindow):
    """Minimal CLEX Browser with essential functionality only."""
    
    def __init__(self, db_file):
        super().__init__()
        self.db_file = db_file
        self.technologies = []
        self.devices = []
        self.current_tech_id = None
        self.current_device_id = None
        
        # Set up UI
        self.setWindowTitle("Minimal CLEX Browser")
        self.resize(1000, 700)
        
        # Create central widget with splitters
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (technologies)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        tech_label = QLabel("Technologies:")
        left_layout.addWidget(tech_label)
        
        self.tech_list = QListWidget()
        self.tech_list.currentItemChanged.connect(self.on_tech_selected)
        left_layout.addWidget(self.tech_list)
        
        # Right panel split vertically
        right_panel = QSplitter(Qt.Vertical)
        
        # Device list panel
        device_panel = QWidget()
        device_layout = QVBoxLayout(device_panel)
        device_label = QLabel("Devices:")
        device_layout.addWidget(device_label)
        
        self.device_list = QListWidget()
        self.device_list.currentItemChanged.connect(self.on_device_selected)
        device_layout.addWidget(self.device_list)
        
        # CLEX definition panel
        clex_panel = QWidget()
        clex_layout = QVBoxLayout(clex_panel)
        clex_label = QLabel("CLEX Definition:")
        clex_layout.addWidget(clex_label)
        
        self.clex_text = QTextEdit()
        self.clex_text.setReadOnly(True)
        clex_layout.addWidget(self.clex_text)
        
        # Add panels to splitters
        right_panel.addWidget(device_panel)
        right_panel.addWidget(clex_panel)
        right_panel.setSizes([300, 400])
        
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([300, 700])
        
        main_layout.addWidget(main_splitter)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Load technologies
        self.load_technologies()
    
    def load_technologies(self):
        """Load technologies using direct database access."""
        try:
            self.status_bar.showMessage("Loading technologies...")
            
            # Connect to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get technologies
            cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
            self.technologies = cursor.fetchall()
            
            # Close connection
            conn.close()
            
            # Update UI
            self.tech_list.clear()
            for tech_id, tech_name, tech_version in self.technologies:
                display_text = f"{tech_name} v{tech_version}" if tech_version else tech_name
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, tech_id)
                # FIXED: Use addItem, not addWidget
                self.tech_list.addItem(item)
            
            self.status_bar.showMessage(f"Loaded {len(self.technologies)} technologies")
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load technologies: {e}")
            self.status_bar.showMessage("Error loading technologies")
    
    def on_tech_selected(self, current, previous):
        """Handle technology selection."""
        if not current:
            return
        
        tech_id = current.data(Qt.UserRole)
        self.current_tech_id = tech_id
        tech_name = current.text().split(" v")[0]
        
        self.load_devices(tech_id)
    
    def load_devices(self, tech_id):
        """Load devices for selected technology."""
        try:
            self.status_bar.showMessage("Loading devices...")
            
            # Connect to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get devices
            cursor.execute(
                "SELECT id, name, has_clex_definition FROM devices WHERE technology_id = ? ORDER BY name", 
                (tech_id,)
            )
            self.devices = cursor.fetchall()
            
            # Get statistics
            cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE technology_id = ? AND has_clex_definition = 1", 
                (tech_id,)
            )
            clex_count = cursor.fetchone()[0]
            
            # Close connection
            conn.close()
            
            # Update UI
            self.device_list.clear()
            for device_id, device_name, has_clex in self.devices:
                item = QListWidgetItem(device_name)
                item.setData(Qt.UserRole, device_id)
                if has_clex:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.device_list.addItem(item)
            
            # Clear CLEX display
            self.clex_text.clear()
            
            self.status_bar.showMessage(f"Loaded {len(self.devices)} devices ({clex_count} with CLEX)")
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load devices: {e}")
            self.status_bar.showMessage(f"Error loading devices")
    
    def on_device_selected(self, current, previous):
        """Handle device selection."""
        if not current:
            return
        
        device_id = current.data(Qt.UserRole)
        self.current_device_id = device_id
        device_name = current.text()
        
        # Check if device has CLEX definition
        has_clex = current.font().bold()
        
        if has_clex:
            self.load_clex_definition(device_id, device_name)
        else:
            self.clex_text.clear()
            self.status_bar.showMessage(f"Device '{device_name}' has no CLEX definition")
    
    def load_clex_definition(self, device_id, device_name):
        """Load CLEX definition for selected device."""
        try:
            self.status_bar.showMessage(f"Loading CLEX definition for {device_name}...")
            
            # Connect to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get CLEX definition
            cursor.execute(
                "SELECT folder_path, file_name, definition_text FROM clex_definitions WHERE device_id = ?", 
                (device_id,)
            )
            result = cursor.fetchone()
            
            # Close connection
            conn.close()
            
            if result:
                folder_path, file_name, definition_text = result
                
                # Format text
                header_text = f"Device: {device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n"
                filtered_lines = [
                    line for line in definition_text.split('\n') 
                    if not line.strip().startswith(("Folder Path:", "File Name:"))
                ]
                filtered_definition = '\n'.join(filtered_lines)
                
                # Update UI
                self.clex_text.setPlainText(header_text + filtered_definition)
                self.status_bar.showMessage(f"Loaded CLEX definition for '{device_name}'")
            else:
                self.clex_text.clear()
                self.status_bar.showMessage(f"No CLEX definition found for '{device_name}'")
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load CLEX definition: {e}")
            self.status_bar.showMessage(f"Error loading CLEX definition for {device_name}")

def main():
    app = QApplication(sys.argv)
    browser = MinimalCLEXBrowser("clex_database.db")
    browser.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()