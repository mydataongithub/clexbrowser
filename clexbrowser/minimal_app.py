import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtCore import QThread, pyqtSignal

class TestWorker(QThread):
    """Test worker thread to verify thread management."""
    completed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
    
    def run(self):
        """Simulate work without database operations."""
        import time
        time.sleep(1)  # Simulate work
        self.completed.emit()

class MinimalCLEXBrowser(QMainWindow):
    """Minimal version of the CLEX Browser to isolate threading issues."""
    
    def __init__(self, db_file):
        super().__init__()
        self.db_file = db_file
        self.setWindowTitle("Minimal CLEX Browser")
        self.resize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add some UI elements
        title_label = QLabel("Minimal CLEX Browser")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        info_label = QLabel(f"Database: {self.db_file}")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Add a test button
        test_button = QPushButton("Test Button (No Threads)")
        test_button.clicked.connect(self.on_test_clicked)
        layout.addWidget(test_button)
        
        layout.addStretch()
    
    def on_test_clicked(self):
        """Test thread creation and cleanup."""
        print("Creating test worker thread")
        worker = self.create_safe_worker()
        worker.completed.connect(lambda: print("Worker completed"))
        worker.start()
    
    def closeEvent(self, event):
        """Handle window close event."""
        print("Application closing normally")
        event.accept()

    def create_safe_worker(self):
        """Create a worker thread with proper cleanup."""
        worker = TestWorker()
        worker.completed.connect(worker.deleteLater)
        worker.finished.connect(worker.deleteLater)
        return worker

def main():
    app = QApplication(sys.argv)
    db_file = "clex_database.db"
    browser = MinimalCLEXBrowser(db_file)
    browser.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()