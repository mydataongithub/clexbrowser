# device_loader_test.py
import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QComboBox, QListWidget, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal

class SimpleDeviceLoaderWorker(QThread):
    """Simplified worker for loading devices without complex signal structures."""
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, db_file, tech_id):
        super().__init__()
        self.db_file = db_file
        self.tech_id = tech_id
        
    def run(self):
        try:
            # Connect to database directly - simplest approach
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Execute a simple query
            cursor.execute(
                "SELECT id, name, has_clex_definition FROM devices WHERE technology_id = ? ORDER BY name", 
                (self.tech_id,)
            )
            
            # Fetch all results
            devices = cursor.fetchall()
            conn.close()
            
            # Send results back
            self.result_signal.emit(devices)
            
        except Exception as e:
            self.error_signal.emit(f"Error loading devices: {str(e)}")

class DeviceLoaderTest(QMainWindow):
    """Specialized test application focusing only on device loading."""
    
    def __init__(self, db_file):
        super().__init__()
        self.db_file = db_file
        self.setWindowTitle("Device Loader Test")
        self.resize(600, 400)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Add technology selector
        self.tech_label = QLabel("Select Technology:")
        layout.addWidget(self.tech_label)
        
        self.tech_combo = QComboBox()
        self.tech_combo.currentIndexChanged.connect(self.on_tech_selected)
        layout.addWidget(self.tech_combo)
        
        # Add device list
        self.device_label = QLabel("Devices:")
        layout.addWidget(self.device_label)
        
        self.device_list = QListWidget()
        layout.addWidget(self.device_list)
        
        # Add status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Load technologies
        self.load_technologies()
    
    def load_technologies(self):
        """Load technologies into combo box - direct database access for simplicity."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
            technologies = cursor.fetchall()
            conn.close()
            
            for tech_id, tech_name, tech_version in technologies:
                display_text = f"{tech_name} v{tech_version}" if tech_version else tech_name
                self.tech_combo.addItem(display_text, tech_id)
                
            self.status_label.setText(f"Loaded {len(technologies)} technologies")
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load technologies: {e}")
            self.status_label.setText("Error loading technologies")
    
    def on_tech_selected(self, index):
        """Handle technology selection."""
        if index < 0:
            return
            
        tech_id = self.tech_combo.itemData(index)
        self.status_label.setText(f"Loading devices for technology ID {tech_id}...")
        
        # Create worker thread
        self.worker = SimpleDeviceLoaderWorker(self.db_file, tech_id)
        self.worker.result_signal.connect(self.on_devices_loaded)
        self.worker.error_signal.connect(self.on_error)
        
        # Connect cleanup
        self.worker.finished.connect(self.worker.deleteLater)
        
        # Start worker
        self.worker.start()
    
    def on_devices_loaded(self, devices):
        """Handle loaded devices."""
        self.device_list.clear()
        
        for device_id, device_name, has_clex in devices:
            self.device_list.addItem(device_name)
        
        self.status_label.setText(f"Loaded {len(devices)} devices")
    
    def on_error(self, error_message):
        """Handle error."""
        QMessageBox.critical(self, "Error", error_message)
        self.status_label.setText(error_message)

def main():
    app = QApplication(sys.argv)
    window = DeviceLoaderTest("clex_database.db")
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()