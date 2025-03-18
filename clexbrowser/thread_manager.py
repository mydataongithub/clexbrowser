import time
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication

class ThreadManager:
    """
    Manages and tracks all worker threads in the application.
    
    This class provides centralized thread lifecycle management to ensure
    proper creation, tracking, and cleanup of background worker threads.
    """
    
    def __init__(self):
        """Initialize the thread manager."""
        self.active_threads = []
    
    def create_worker(self, worker_class, *args, **kwargs):
        """
        Create a worker thread with proper tracking.
        
        Args:
            worker_class: The QThread subclass to instantiate
            *args: Arguments to pass to the worker constructor
            **kwargs: Keyword arguments to pass to the worker constructor
            
        Returns:
            The created worker instance
        """
        worker = worker_class(*args, **kwargs)
        
        # Track this thread
        self.active_threads.append(worker)
        
        # Set up cleanup when thread finishes
        worker.finished.connect(lambda: self._cleanup_thread(worker))
        
        return worker
    
    def _cleanup_thread(self, worker):
        """
        Remove thread from tracking when it finishes.
        
        Args:
            worker: The worker thread to clean up
        """
        if worker in self.active_threads:
            self.active_threads.remove(worker)
            worker.deleteLater()
    
    def wait_for_threads(self, timeout_ms=5000):
        """
        Wait for all threads to finish with timeout.
        
        Args:
            timeout_ms: Maximum time to wait in milliseconds
            
        Returns:
            True if all threads finished, False if some remain
        """
        if not self.active_threads:
            return True
            
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
            for thread in self.active_threads[:]:  # Use a copy of the list
                if thread.isRunning():
                    thread.terminate()
                    thread.wait()
                self._cleanup_thread(thread)
        
        return len(self.active_threads) == 0