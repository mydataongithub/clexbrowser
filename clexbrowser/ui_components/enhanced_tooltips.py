from PyQt5.QtWidgets import (QLabel, QWidget, QVBoxLayout, QHBoxLayout, 
                           QToolTip, QPushButton, QApplication)
from PyQt5.QtCore import Qt, QEvent, QPoint, QRect, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QFontMetrics, QPixmap, QIcon
from PyQt5.QtCore import QObject, Qt, QEvent, QPoint, QRect, QSize, QTimer
from typing import Optional, Dict

class EnhancedTooltip(QWidget):
    """
    A customizable tooltip widget with rich formatting capabilities.
    
    This class provides tooltips with support for rich text, icons,
    keyboard shortcuts, and multi-section content.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the enhanced tooltip widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent, Qt.ToolTip | Qt.BypassWindowManagerHint)
        
        # Set up appearance
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(True)
        
        # Configure layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 8, 10, 8)
        self.layout.setSpacing(5)
        
        # Initialize content widgets
        self.title_label = QLabel()
        self.title_label.setObjectName("tooltipTitle")
        self.title_label.setWordWrap(True)
        title_font = self.title_label.font()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        
        self.body_label = QLabel()
        self.body_label.setObjectName("tooltipBody")
        self.body_label.setWordWrap(True)
        self.body_label.setTextFormat(Qt.RichText)
        
        self.shortcut_label = QLabel()
        self.shortcut_label.setObjectName("tooltipShortcut")
        shortcut_font = self.shortcut_label.font()
        shortcut_font.setItalic(True)
        self.shortcut_label.setFont(shortcut_font)
        
        # Apply styles
        self.setStyleSheet("""
            EnhancedTooltip {
                background-color: #ffffdc;
                border: 1px solid #bdbdbd;
                border-radius: 4px;
            }
            QLabel#tooltipTitle {
                color: #333333;
                font-size: 12px;
            }
            QLabel#tooltipBody {
                color: #333333;
                font-size: 11px;
            }
            QLabel#tooltipShortcut {
                color: #666666;
                font-size: 10px;
            }
        """)
        
        # Hide by default
        self.hide()
        
        # Set up hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
        # Track mouse position
        self.installEventFilter(self)
    
    def set_content(self, title: str = "", body: str = "", shortcut: str = "", 
                   icon: Optional[QIcon] = None, duration_ms: int = 5000):
        """
        Set the tooltip content.
        
        Args:
            title: Title text (bold)
            body: Main body text (supports rich text)
            shortcut: Keyboard shortcut text
            icon: Optional icon to display
            duration_ms: Time in milliseconds to display the tooltip (0 for no auto-hide)
        """
        # Clear the layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                self.layout.removeWidget(item.widget())
        
        # Add icon and title in a horizontal layout if an icon is provided
        if icon and not icon.isNull():
            header_layout = QHBoxLayout()
            header_layout.setSpacing(5)
            
            icon_label = QLabel()
            pixmap = icon.pixmap(QSize(16, 16))
            icon_label.setPixmap(pixmap)
            header_layout.addWidget(icon_label, 0, Qt.AlignTop)
            
            self.title_label.setText(title)
            header_layout.addWidget(self.title_label, 1)
            
            self.layout.addLayout(header_layout)
        elif title:
            self.title_label.setText(title)
            self.layout.addWidget(self.title_label)
        
        # Add body text if provided
        if body:
            self.body_label.setText(body)
            self.layout.addWidget(self.body_label)
        
        # Add shortcut text if provided
        if shortcut:
            self.shortcut_label.setText(f"Shortcut: {shortcut}")
            self.layout.addWidget(self.shortcut_label)
        
        # Set up auto-hide timer if duration is specified
        if duration_ms > 0:
            self.hide_timer.setInterval(duration_ms)
        
        # Resize to fit content
        self.adjustSize()
    
    def show_tooltip(self, pos: QPoint):
        """
        Show the tooltip at the specified position.
        
        Args:
            pos: Global screen position to show the tooltip
        """
        # Adjust position to ensure the tooltip is within screen bounds
        screen_rect = QApplication.desktop().screenGeometry(pos)
        tooltip_size = self.sizeHint()
        
        # Check if tooltip would extend beyond right edge of screen
        if pos.x() + tooltip_size.width() > screen_rect.right():
            pos.setX(screen_rect.right() - tooltip_size.width())
        
        # Check if tooltip would extend beyond bottom edge of screen
        if pos.y() + tooltip_size.height() > screen_rect.bottom():
            pos.setY(pos.y() - tooltip_size.height() - 20)  # Show above cursor
        else:
            pos.setY(pos.y() + 20)  # Show below cursor
        
        # Move to position and show
        self.move(pos)
        self.show()
        
        # Start auto-hide timer if interval is set
        if self.hide_timer.interval() > 0:
            self.hide_timer.start()
    
    def eventFilter(self, obj, event):
        """
        Filter events to auto-hide tooltip when mouse moves away.
        
        Args:
            obj: Object that generated the event
            event: Event that occurred
            
        Returns:
            True if the event was handled, False otherwise
        """
        if event.type() == QEvent.MouseMove:
            if not self.geometry().contains(event.globalPos()):
                self.hide()
        return super().eventFilter(obj, event)

class TooltipManager(QObject):
    """
    Manager class for enhanced tooltips throughout the application.
    
    This class provides centralized management of tooltips, including
    registration, display, and content management.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(TooltipManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the tooltip manager (only once due to singleton pattern)."""
        if not self._initialized:
            super().__init__()  # Initialize QObject base class
            self.tooltips = {}  # id -> tooltip data
            self.widget_tooltips = {}  # widget -> tooltip id
            self.tooltip_widget = EnhancedTooltip()
            self._initialized = True
    
    def register_tooltip(self, tooltip_id: str, title: str, body: str = "", 
                        shortcut: str = "", icon: Optional[QIcon] = None):
        """
        Register a tooltip in the system.
        
        Args:
            tooltip_id: Unique identifier for the tooltip
            title: Title text (bold)
            body: Main body text (supports rich text)
            shortcut: Keyboard shortcut text
            icon: Optional icon to display
        """
        self.tooltips[tooltip_id] = {
            'title': title,
            'body': body,
            'shortcut': shortcut,
            'icon': icon
        }
    
    def register_feature_tooltip(self, tooltip_id: str, feature_name: str, 
                               description: str, shortcut: str = ""):
        """
        Register a tooltip for a feature.
        
        Args:
            tooltip_id: Unique identifier for the tooltip
            feature_name: Name of the feature (used as title)
            description: Description of the feature (used as body)
            shortcut: Keyboard shortcut for the feature
        """
        self.register_tooltip(
            tooltip_id,
            title=feature_name,
            body=description,
            shortcut=shortcut
        )
    
    def attach_tooltip(self, widget: QWidget, tooltip_id: str):
        """
        Attach a tooltip to a widget.
        
        Args:
            widget: Widget to attach the tooltip to
            tooltip_id: ID of the tooltip to attach
        """
        if tooltip_id not in self.tooltips:
            return
        
        self.widget_tooltips[widget] = tooltip_id
        widget.setToolTip("")  # Clear default tooltip
        
        # Only try to remove event filter if it was installed previously
        if widget in self.widget_tooltips:
            try:
                widget.removeEventFilter(self)
            except TypeError:
                pass  # Ignore if event filter wasn't installed
        
        # Install event filter to show enhanced tooltip
        widget.installEventFilter(self)
    
    def show_tooltip(self, tooltip_id: str, pos: QPoint):
        """
        Show a tooltip at the specified position.
        
        Args:
            tooltip_id: ID of the tooltip to show
            pos: Global screen position to show the tooltip
        """
        if tooltip_id not in self.tooltips:
            return
        
        tooltip_data = self.tooltips[tooltip_id]
        self.tooltip_widget.set_content(
            title=tooltip_data['title'],
            body=tooltip_data['body'],
            shortcut=tooltip_data['shortcut'],
            icon=tooltip_data['icon']
        )
        self.tooltip_widget.show_tooltip(pos)
    
    def eventFilter(self, obj, event):
        """
        Event filter to show tooltips when hovering over widgets.
        
        Args:
            obj: Object that generated the event
            event: Event that occurred
            
        Returns:
            True if the event was handled, False otherwise
        """
        if event.type() == QEvent.ToolTip and obj in self.widget_tooltips:
            tooltip_id = self.widget_tooltips[obj]
            self.show_tooltip(tooltip_id, event.globalPos())
            return True
        
        return super().eventFilter(obj, event)

class CLEXTooltips:
    """
    Helper class for registering common CLEX Browser tooltips.
    
    This class provides methods to register tooltips for common
    features and UI elements in the CLEX Browser application.
    """
    
    @staticmethod
    def register_common_tooltips():
        """Register common tooltips used throughout the application."""
        manager = TooltipManager()
        
        # Main toolbar tooltips
        manager.register_feature_tooltip(
            "refresh_database",
            "Refresh Database",
            "Reload the database from a CLEX log file to update with the latest definitions.",
            "F5"
        )
        
        manager.register_feature_tooltip(
            "global_search",
            "Global Search",
            "Search for text across all technologies and CLEX definitions.",
            "Ctrl+F"
        )
        
        manager.register_feature_tooltip(
            "new_clex",
            "New CLEX Definition",
            "Create a new CLEX definition for a device.",
            "Ctrl+N"
        )
        
        manager.register_feature_tooltip(
            "edit_clex",
            "Edit CLEX Definition",
            "Edit the currently selected CLEX definition.",
            "Ctrl+E"
        )
        
        manager.register_feature_tooltip(
            "delete_clex",
            "Delete CLEX Definition",
            "Delete the currently selected CLEX definition.",
            "Delete"
        )
        
        manager.register_feature_tooltip(
            "compare_devices",
            "Compare Devices",
            "Compare CLEX definitions between two devices side by side.",
            "Ctrl+D"
        )
        
        manager.register_feature_tooltip(
            "clex_statistics",
            "CLEX Statistics",
            "View statistics about CLEX definitions in the database.",
            "Ctrl+T"
        )
        
        manager.register_feature_tooltip(
            "export",
            "Export CLEX Definitions",
            "Export CLEX definitions to various file formats.",
            "Ctrl+E"
        )
        
        manager.register_feature_tooltip(
            "dark_mode",
            "Toggle Dark Mode",
            "Switch between light and dark color themes.",
            "Ctrl+Shift+D"
        )
        
        # UI element tooltips
        manager.register_tooltip(
            "tech_search",
            "Filter Technologies",
            "Enter text to filter the list of technologies by name or version.",
            "Ctrl+1 to focus"
        )
        
        manager.register_tooltip(
            "device_search",
            "Filter Devices",
            "Enter text to filter the list of devices by name.",
            "Ctrl+2 to focus"
        )
        
        manager.register_tooltip(
            "only_clex_checkbox",
            "Show Only CLEX Devices",
            "When checked, only devices with CLEX definitions will be shown in the list."
        )
        
        manager.register_tooltip(
            "copy_button",
            "Copy to Clipboard",
            "Copy the current CLEX definition to the clipboard.",
            "Ctrl+C"
        )
    
    @staticmethod
    def attach_tooltips_to_main_window(window):
        """
        Attach tooltips to widgets in the main window.
        
        Args:
            window: Main application window
        """
        manager = TooltipManager()
        
        # Attach tooltips to toolbar buttons and other elements
        # These will be connected when the window has the appropriate attributes
        
        if hasattr(window, 'refresh_action'):
            manager.attach_tooltip(window.refresh_action, "refresh_database")
        
        if hasattr(window, 'global_search_action'):
            manager.attach_tooltip(window.global_search_action, "global_search")
        
        if hasattr(window, 'tech_search_box'):
            manager.attach_tooltip(window.tech_search_box, "tech_search")
        
        if hasattr(window, 'search_box'):
            manager.attach_tooltip(window.search_box, "device_search")
        
        if hasattr(window, 'only_clex_checkbox'):
            manager.attach_tooltip(window.only_clex_checkbox, "only_clex_checkbox")