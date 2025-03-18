import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

class ThreadManager:
    """Manages and tracks all worker threads in the application."""
    
    def __init__(self):
        self.active_threads = []
    
    def create_worker(self, worker_class, *args, **kwargs):
        """Create a worker thread with proper tracking."""
        worker = worker_class(*args, **kwargs)
        
        # Track this thread
        self.active_threads.append(worker)
        
        # Set up cleanup when thread finishes
        worker.finished.connect(lambda: self._cleanup_thread(worker))
        
        return worker
    
    def _cleanup_thread(self, worker):
        """Remove thread from tracking when it finishes."""
        if worker in self.active_threads:
            self.active_threads.remove(worker)
            print(f"Thread cleaned up. {len(self.active_threads)} threads remaining.")
    
    def wait_for_threads(self, timeout_ms=5000):
        """Wait for all threads to finish with timeout."""
        print(f"Waiting for {len(self.active_threads)} threads to finish...")
        
        # First try graceful quit
        for thread in self.active_threads:
            if thread.isRunning():
                thread.quit()
        
        # Wait with timeout
        deadline = time.time() + (timeout_ms / 1000)
        while self.active_threads and time.time() < deadline:
            QApplication.processEvents()
            time.sleep(0.1)
        
        # Force terminate any remaining threads
        remaining = len(self.active_threads)
        if remaining > 0:
            print(f"Forcefully terminating {remaining} threads that didn't exit gracefully")
            for thread in self.active_threads[:]:  # Use a copy of the list
                if thread.isRunning():
                    thread.terminate()
                    thread.wait()
                self._cleanup_thread(thread)
        
        return len(self.active_threads) == 0


class SimpleWorker(QThread):
    """Simple worker thread that emits a signal when complete."""
    work_done = pyqtSignal(str)
    
    def __init__(self, sleep_time=3):
        super().__init__()
        self.sleep_time = sleep_time
    
    def run(self):
        """Execute a simple task with deliberate delay."""
        print(f"Worker starting, will take {self.sleep_time} seconds")
        time.sleep(self.sleep_time)
        print("Worker task completed")
        self.work_done.emit(f"Completed work after {self.sleep_time} seconds")


class ThreadSafeApp(QMainWindow):
    """Test application with proper thread management."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thread-Safe Application")
        self.resize(600, 400)
        
        # Create thread manager
        self.thread_manager = ThreadManager()
        
        # Set up UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add instructions
        title_label = QLabel("Thread-Safe Test Application")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        instructions = QLabel(
            "This application demonstrates proper thread management.\n"
            "Click the button to start a worker thread that will run for 3 seconds.\n"
            "You can close the application at any time, and it will properly clean up threads."
        )
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Add status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Add test button
        test_button = QPushButton("Start Worker Thread (3 seconds)")
        test_button.clicked.connect(self.start_worker)
        layout.addWidget(test_button)
        
        # Add quick worker button
        quick_button = QPushButton("Start Quick Worker (1 second)")
        quick_button.clicked.connect(self.start_quick_worker)
        layout.addWidget(quick_button)
        
        layout.addStretch()
    
    def start_worker(self):
        """Start a worker thread that takes 3 seconds."""
        self.status_label.setText("Starting worker thread...")
        
        # Create worker using thread manager
        worker = self.thread_manager.create_worker(SimpleWorker, 3)
        worker.work_done.connect(self.on_work_done)
        worker.start()
    
    def start_quick_worker(self):
        """Start a worker thread that takes 1 second."""
        self.status_label.setText("Starting quick worker thread...")
        
        # Create worker using thread manager
        worker = self.thread_manager.create_worker(SimpleWorker, 1)
        worker.work_done.connect(self.on_work_done)
        worker.start()
    
    def on_work_done(self, result):
        """Handle work completion."""
        self.status_label.setText(result)
    
    def closeEvent(self, event):
        """Handle window close event with proper thread cleanup."""
        if self.thread_manager.active_threads:
            reply = QMessageBox.question(
                self, 
                "Threads Still Running",
                f"There are {len(self.thread_manager.active_threads)} threads still running. "
                "Do you want to wait for them to finish before closing?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Show busy cursor and disable UI
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.setEnabled(False)
                
                # Wait for threads to finish
                all_done = self.thread_manager.wait_for_threads()
                
                # Restore cursor and UI
                QApplication.restoreOverrideCursor()
                self.setEnabled(True)
                
                if not all_done:
                    QMessageBox.warning(
                        self,
                        "Thread Cleanup Issue",
                        "Some threads could not be properly terminated. "
                        "The application will attempt to close anyway."
                    )
        
        # Accept the close event
        print("Application closing")
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = ThreadSafeApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()