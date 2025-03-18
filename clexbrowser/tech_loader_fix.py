import sys
import sqlite3
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QListWidget, QMessageBox, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, Qt

class SimpleTechLoader(QThread):
    """Simple technology loader for testing."""
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, db_file):
        super().__init__()
        self.db_file = db_file
        print("SimpleTechLoader initialized")
        
    def run(self):
        try:
            print("SimpleTechLoader started")
            # Add a small delay to make sure UI updates
            time.sleep(0.5)
            
            # Open database connection
            print(f"Opening database: {self.db_file}")
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Execute query
            print("Executing technology query")
            cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
            
            # Fetch results
            technologies = cursor.fetchall()
            conn.close()
            print(f"Found {len(technologies)} technologies")
            
            # Emit results
            self.result_signal.emit(technologies)
            print("Results emitted")
            
        except Exception as e:
            print(f"Error in SimpleTechLoader: {str(e)}")
            self.error_signal.emit(str(e))

class TechLoaderTest(QMainWindow):
    """Test window for technology loading."""
    
    def __init__(self, db_file):
        super().__init__()
        self.db_file = db_file
        self.setWindowTitle("Technology Loader Test")
        self.resize(500, 400)
        
        # Create UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.status_label = QLabel("Ready to load technologies")
        layout.addWidget(self.status_label)
        
        self.tech_list = QListWidget()
        layout.addWidget(self.tech_list)
        
        load_button = QPushButton("Load Technologies")
        load_button.clicked.connect(self.load_technologies)
        layout.addWidget(load_button)
        
    def load_technologies(self):
        """Start loading technologies."""
        self.status_label.setText("Loading technologies...")
        QApplication.processEvents()
        
        # Create and start worker
        self.worker = SimpleTechLoader(self.db_file)
        self.worker.result_signal.connect(self.on_technologies_loaded)
        self.worker.error_signal.connect(self.on_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        
    def on_technologies_loaded(self, technologies):
        """Handle loaded technologies."""
        self.tech_list.clear()
        
        for tech_id, tech_name, tech_version in technologies:
            display_text = f"{tech_name} v{tech_version}" if tech_version else tech_name
            self.tech_list.addItem(display_text)
            
        self.status_label.setText(f"Loaded {len(technologies)} technologies")
        
    def on_error(self, error_message):
        """Handle errors."""
        QMessageBox.critical(self, "Error", error_message)
        self.status_label.setText(f"Error: {error_message}")

def main():
    app = QApplication(sys.argv)
    window = TechLoaderTest("clex_database.db")
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()