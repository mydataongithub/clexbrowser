from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar, 
                            QPushButton)
from PyQt5.QtCore import Qt

class ProgressDialog(QDialog):
    """
    Dialog showing progress for long-running operations.
    
    This dialog displays a progress bar and status message during operations
    like database creation or loading, providing visual feedback to the user.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the progress dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Operation in Progress")
        self.setFixedSize(400, 150)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)
        
        self.setLayout(layout)
    
    def update_progress(self, value):
        """
        Update the progress bar value.
        
        Args:
            value: Progress percentage (0-100)
        """
        self.progress_bar.setValue(value)
    
    def update_status(self, status):
        """
        Update the status message.
        
        Args:
            status: Status message to display
        """
        self.status_label.setText(status)