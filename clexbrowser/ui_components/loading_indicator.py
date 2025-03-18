from PyQt5.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFrame)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPalette

class CircularProgressIndicator(QWidget):
    """
    A circular progress indicator for showing indeterminate progress.
    
    This widget displays a spinning circular indicator to show that an operation
    is in progress, without indicating a specific percentage of completion.
    """
    
    def __init__(self, parent=None, size=40, color=None):
        """
        Initialize the circular progress indicator.
        
        Args:
            parent: Parent widget
            size: Size of the indicator in pixels
            color: Color of the indicator (uses accent color if None)
        """
        super().__init__(parent)
        
        # Set widget properties
        self.setFixedSize(size, size)
        self.setContentsMargins(0, 0, 0, 0)
        
        # Initialize variables
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_angle)
        self._speed = 50  # milliseconds per frame
        
        # Set color
        if color is None:
            palette = self.palette()
            self._color = palette.color(QPalette.Highlight)
        else:
            self._color = color
    
    def paintEvent(self, event):
        """Paint the circular indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions
        width = self.width()
        height = self.height()
        size = min(width, height)
        
        # Set up the pen for drawing
        pen_width = max(3, size / 10)
        pen = QPen(self._color, pen_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # Calculate the rectangle for the arc
        rect = QRect(
            int(pen_width), 
            int(pen_width), 
            int(size - 2 * pen_width), 
            int(size - 2 * pen_width)
        )
        
        # Draw the arc (from current angle, spanning 120 degrees)
        painter.drawArc(rect, int(self._angle * 16), 120 * 16)
    
    def _update_angle(self):
        """Update the rotation angle for animation."""
        self._angle = (self._angle + 30) % 360
        self.update()
    
    def start_animation(self):
        """Start the spinning animation."""
        if not self._timer.isActive():
            self._timer.start(self._speed)
    
    def stop_animation(self):
        """Stop the spinning animation."""
        if self._timer.isActive():
            self._timer.stop()
    
    def set_color(self, color):
        """
        Set the color of the indicator.
        
        Args:
            color: QColor to use for the indicator
        """
        self._color = color
        self.update()
    
    def showEvent(self, event):
        """Handle the widget being shown."""
        self.start_animation()
        super().showEvent(event)
    
    def hideEvent(self, event):
        """Handle the widget being hidden."""
        self.stop_animation()
        super().hideEvent(event)


class LoadingOverlay(QWidget):
    """
    A semi-transparent overlay widget with a loading indicator and message.
    
    This widget can be placed over other widgets to show that an operation is
    in progress, preventing user interaction until the operation completes.
    """
    
    def __init__(self, parent=None, message="Loading..."):
        """
        Initialize the loading overlay.
        
        Args:
            parent: Parent widget (the widget to overlay)
            message: Message to display during loading
        """
        super().__init__(parent)
        
        # Set up the overlay
        self.setObjectName("loadingOverlay")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Add progress indicator
        self.progress_indicator = CircularProgressIndicator(self, size=60)
        layout.addWidget(self.progress_indicator, 0, Qt.AlignCenter)
        
        # Add message label
        self.message_label = QLabel(message)
        self.message_label.setStyleSheet("QLabel { color: #333333; font-size: 14px; }")
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label, 0, Qt.AlignCenter)
        
        # Create a frame to hold everything
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 220);
                border-radius: 10px;
                border: 1px solid #cccccc;
            }
        """)
        frame.setLayout(layout)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(frame, 0, Qt.AlignCenter)
        self.setLayout(main_layout)
        
        # Initially hide the overlay
        self.hide()
        
        # Position the overlay to cover the parent widget
        if parent:
            self.resize(parent.size())
    
    def set_message(self, message):
        """
        Set the loading message.
        
        Args:
            message: Message to display
        """
        self.message_label.setText(message)
    
    def show_loading(self, message=None):
        """
        Show the loading overlay.
        
        Args:
            message: Optional message to display (uses existing message if None)
        """
        if message:
            self.set_message(message)
        
        # Position the overlay to cover the parent widget
        if self.parent():
            self.resize(self.parent().size())
        
        # Show the overlay with a fade-in effect
        self.setWindowOpacity(0.0)
        self.show()
        
        # Create animation for fade-in
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(300)  # 300ms
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.start()
    
    def hide_loading(self):
        """Hide the loading overlay immediately."""
        # Create animation for fade-out
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(300)  # 300ms
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.finished.connect(self.hide)
        animation.start()
        #self.hide()
    
    def resizeEvent(self, event):
        """Handle resize events to keep the overlay covering the parent."""
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)


class StatusIndicator(QWidget):
    """
    A status indicator widget that shows both progress and status messages.
    
    This widget combines a progress bar and a status label, suitable for
    showing at the bottom of a window or in a status bar.
    """
    
    progressChanged = pyqtSignal(int)
    statusChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """
        Initialize the status indicator.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setMaximumHeight(16)
        layout.addWidget(self.progress_bar)
        
        # Add status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label, 1)
        
        # Set up the widget
        self.setLayout(layout)
        
        # Connect signals
        self.progressChanged.connect(self.set_progress)
        self.statusChanged.connect(self.set_status)
    
    def set_progress(self, value):
        """
        Set the progress bar value.
        
        Args:
            value: Progress percentage (0-100)
        """
        self.progress_bar.setValue(value)
    
    def set_status(self, status):
        """
        Set the status message.
        
        Args:
            status: Status message to display
        """
        self.status_label.setText(status)
    
    def reset(self):
        """Reset the indicator to its default state."""
        # Stop indeterminate mode if active
        self.progress_bar.setRange(0, 100)  # Ensure range is reset
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
    
        # Explicitly stop indeterminate mode
        self.stop_indeterminate()
    
    def start_indeterminate(self):
        """Start displaying indeterminate progress (busy indicator)."""
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
    
    def stop_indeterminate(self):
        """Stop indeterminate progress and return to normal mode."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)