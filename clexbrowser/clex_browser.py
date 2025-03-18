import sys
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QListWidget, QListWidgetItem, 
                            QTextEdit, QLineEdit, QSplitter, QStatusBar, QMessageBox,
                            QAbstractItemView, QFrame, QPushButton, QToolBar, QAction,
                            QDockWidget, QTabWidget, QDialog, QFileDialog, QCheckBox,
                            QProgressBar, QMenu, QShortcut, QComboBox, QGraphicsDropShadowEffect)

from PyQt5.QtCore import Qt, QSize, QSettings, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import (QFont, QColor, QIcon, QKeySequence)

# Import database manager
from database_manager import DatabaseManager

from thread_manager import ThreadManager

# Import dialogs
from dialogs import (ProgressDialog, CompareDialog, ExportDialog, GlobalSearchDialog,
                    StatsDialog, NewCLEXDialog, EditCLEXDialog, ConfirmationDialog, 
                    BulkOperationsDialog)

# Import UI components
from ui_components import SyntaxHighlighter, LoadingOverlay, StatusIndicator, TooltipManager, CLEXTooltips

# Import workers
from workers import DatabaseWorker, LoadTechnologiesWorker, LoadDevicesWorker, LoadClexDefinitionWorker

# Import command manager
from command_manager import CommandManager, EditClexDefinitionCommand, AddClexDefinitionCommand, DeleteClexDefinitionCommand

class FavoritesManager:
    """
    Manages favorite CLEX definitions.
    
    This class provides functionality to save, load, and manage a user's favorite
    CLEX definitions for quick access.
    """
    
    def __init__(self, db_file: str):
        """
        Initialize the favorites manager.
        
        Args:
            db_file: Path to the database file
        """
        self.db_file = db_file
        self.favorites_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clex_favorites.json")
        self.favorites = self.load_favorites()
    
    def load_favorites(self) -> Dict:
        """
        Load favorites from the JSON file.
        
        Returns:
            Dictionary of favorites
        """
        if os.path.exists(self.favorites_file):
            try:
                import json
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
            except:
                return {"devices": []}
        return {"devices": []}
    
    def save_favorites(self):
        """Save favorites to the JSON file."""
        try:
            import json
            with open(self.favorites_file, 'w') as f:
                json.dump(self.favorites, f)
        except Exception as e:
            print(f"Error saving favorites: {e}")
    
    def add_favorite(self, device_id: int, device_name: str, tech_id: int, tech_name: str) -> bool:
        """
        Add a device to favorites.
        
        Args:
            device_id: ID of the device
            device_name: Name of the device
            tech_id: ID of the technology
            tech_name: Name of the technology
            
        Returns:
            True if added successfully, False if already in favorites
        """
        if not any(d["device_id"] == device_id for d in self.favorites["devices"]):
            self.favorites["devices"].append({
                "device_id": device_id,
                "device_name": device_name,
                "tech_id": tech_id,
                "tech_name": tech_name,
                "added": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            self.save_favorites()
            return True
        return False
    
    def remove_favorite(self, device_id: int):
        """
        Remove a device from favorites.
        
        Args:
            device_id: ID of the device to remove
        """
        self.favorites["devices"] = [d for d in self.favorites["devices"] if d["device_id"] != device_id]
        self.save_favorites()
    
    def is_favorite(self, device_id: int) -> bool:
        """
        Check if a device is in favorites.
        
        Args:
            device_id: ID of the device to check
            
        Returns:
            True if the device is in favorites, False otherwise
        """
        return any(d["device_id"] == device_id for d in self.favorites["devices"])
    
    def get_favorites(self) -> List[Dict]:
        """
        Get all favorite devices.
        
        Returns:
            List of favorite device dictionaries
        """
        return self.favorites["devices"]


class EnhancedCLEXBrowser(QMainWindow):
    """
    Enhanced CLEX Browser application.
    
    This class provides the main application window for browsing and managing
    CLEX definitions, with enhanced features for improved usability and performance.
    """
    
    def __init__(self, db_file: str):
        """
        Initialize the Enhanced CLEX Browser.
        
        Args:
            db_file: Path to the SQLite database file
        """
        super().__init__()
        self.db_file = db_file
        
        # Initialize thread manager
        self.thread_manager = ThreadManager()

        # Initialize database manager
        self.db_manager = DatabaseManager(db_file)
        
        # Initialize command manager for undo/redo
        self.command_manager = CommandManager()
        
        # Initialize state variables
        self.all_devices = []
        self.devices = []
        self.all_technologies = []
        self.technologies = []
        self.current_tech_id = None
        self.current_device_id = None
        self.current_device_name = None
        self.dark_mode = False
        
        # Initialize settings
        self.settings = QSettings("CLEXBrowser", "EnhancedCLEXBrowser")
        
        # Initialize favorites manager
        self.favorites = FavoritesManager(db_file)
        
        # Set up the UI
        self.init_ui()
        
        # Load initial data
        self.load_technologies()
        
        # Restore settings
        self.restore_settings()
        
        # Initialize tooltips
        CLEXTooltips.register_common_tooltips()
        CLEXTooltips.attach_tooltips_to_main_window(self)

        self.safety_timer = QTimer(self)
        self.safety_timer.setSingleShot(True)
        self.safety_timer.timeout.connect(self.safety_timeout)
        self.safety_timer.start(5000)  # 5 seconds

    def safety_timeout(self):
        """Handle safety timeout by hiding any visible loading overlays."""
        if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            print("Safety timeout: Hiding stuck loading overlay")
            self.loading_overlay.hide()
            
        if hasattr(self, 'status_indicator'):
            self.status_indicator.reset()
    
        # Schedule another check
        self.safety_timer.start(5000)

    def hide_loading_emergency(self):
        """Emergency function to hide loading if it gets stuck."""
        if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            print("Emergency: Hiding stuck loading overlay")
            self.loading_overlay.hide_loading()
            self.status_indicator.reset()
            self.status_bar.showMessage("Loading timed out. Application may need to be restarted.")

    def load_technologies(self):
        """Load technologies using direct database access."""
        self.loading_overlay.show_loading("Loading technologies...")
        self.status_indicator.start_indeterminate()
        print("Loading technologies directly")
        
        try:
            # Direct database access
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
            technologies = cursor.fetchall()
            conn.close()
            
            # Process results directly
            self.all_technologies = technologies
            self.technologies = self.all_technologies.copy()
            self.update_technology_listbox()
            
            # Update status
            self.status_bar.showMessage(f"Loaded {len(technologies)} technologies")
            
        except Exception as e:
            print(f"Error loading technologies: {str(e)}")
            self.loading_overlay.hide()
            self.status_indicator.reset()
            QMessageBox.critical(self, "Database Error", f"Failed to load technologies: {e}")
            self.status_bar.showMessage("Error loading technologies")
        
        # Always ensure loading indicators are hidden
        self.loading_overlay.hide()
        self.status_indicator.reset()

    def on_technologies_loaded(self, technologies):
        """Handle loaded technologies."""
        print(f"Technologies loaded: {len(technologies)}")
        self.all_technologies = technologies
        self.technologies = self.all_technologies.copy()
        self.update_technology_listbox()
        print("Technology listbox updated")
        self.status_bar.showMessage(f"Loaded {len(self.technologies)} technologies")
        
        # Cancel safety timer since we've loaded successfully
        if hasattr(self, 'safety_timer') and self.safety_timer.isActive():
            self.safety_timer.stop()
        
        self.loading_overlay.hide_loading()
        self.status_indicator.reset()
        print("Loading overlay hidden")

    def restore_settings(self):
        """Restore application settings."""
        print("Restoring settings...")
        # Existing code...
        
        # Add print statements to track technology and device restoration
        if self.settings.contains("last_tech_id"):
            last_tech_id = int(self.settings.value("last_tech_id"))
            print(f"Restoring last technology ID: {last_tech_id}")
            # Existing code...
            
        if self.settings.contains("last_device_id"):
            last_device_id = int(self.settings.value("last_device_id"))
            print(f"Will restore last device ID: {last_device_id}")
            # Existing code...
        
        print("Settings restored")
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Enhanced CLEX Browser')
        self.resize(1200, 800)
        
        # Create central widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Create splitters for layout
        main_splitter = QSplitter(Qt.Vertical)
        upper_splitter = QSplitter(Qt.Horizontal)
        
        # Create left panel (technologies)
        left_panel = self.create_left_panel()
        
        # Create right panel (devices)
        right_panel = self.create_right_panel()
        
        # Add panels to upper splitter
        upper_splitter.addWidget(left_panel)
        upper_splitter.addWidget(right_panel)
        upper_splitter.setSizes([300, 300])
        
        # Create CLEX definition panel
        clex_panel = self.create_clex_panel()
        
        # Add panels to main splitter
        main_splitter.addWidget(upper_splitter)
        main_splitter.addWidget(clex_panel)
        main_splitter.setSizes([400, 400])
        
        # Add main splitter to layout
        main_layout.addWidget(main_splitter)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add status indicator to status bar
        self.status_indicator = StatusIndicator()
        self.status_bar.addPermanentWidget(self.status_indicator)
        
        # Show initial status
        self.status_bar.showMessage("Ready")
        
        # Create floating action button
        self.create_floating_action_button()
        
        # Create loading overlay
        self.loading_overlay = LoadingOverlay(self)
        
        # Create toolbar and menu
        self.create_toolbar()
        self.create_menu()
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
        # Update button states
        self.update_button_states()

    def create_worker_thread(self, worker_class, *args, **kwargs):
        """Create and properly set up a worker thread."""
        worker = worker_class(*args, **kwargs)
        
        # Clean up thread resources when finished
        worker.finished.connect(worker.deleteLater)
        
        return worker

    def create_left_panel(self) -> QWidget:
        """
        Create the left panel containing technologies list and statistics.
        
        Returns:
            QWidget containing the left panel
        """
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add technology header
        tech_header = QHBoxLayout()
        tech_label = QLabel("Technologies:")
        tech_label.setFont(QFont("Arial", 12, QFont.Bold))
        tech_header.addWidget(tech_label)
        left_layout.addLayout(tech_header)
        
        # Add search box for technologies
        tech_search_layout = QHBoxLayout()
        tech_search_label = QLabel("Search:")
        self.tech_search_box = QLineEdit()
        self.tech_search_box.setPlaceholderText("Filter technologies...")
        self.tech_search_box.textChanged.connect(self.filter_technologies)
        
        # Create clear button
        clear_action = QAction(self)
        if QIcon.hasThemeIcon("edit-clear"):
            clear_action.setIcon(QIcon.fromTheme("edit-clear"))
        elif QIcon.hasThemeIcon("dialog-cancel"):
            clear_action.setIcon(QIcon.fromTheme("dialog-cancel"))
        else:
            clear_action = QAction("✕", self)
            clear_action.setFont(QFont("Arial", 10, QFont.Bold))
        
        clear_action.triggered.connect(self.clear_technology_search)
        self.tech_search_box.addAction(clear_action, QLineEdit.TrailingPosition)
        self.tech_search_box.setClearButtonEnabled(True)
        
        # Hide clear button when search box is empty
        self.tech_search_box.textChanged.connect(
            lambda text: clear_action.setVisible(bool(text))
        )
        clear_action.setVisible(False)
        
        tech_search_layout.addWidget(tech_search_label)
        tech_search_layout.addWidget(self.tech_search_box)
        left_layout.addLayout(tech_search_layout)
        
        # Technology list
        self.tech_list = QListWidget()
        self.tech_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tech_list.currentItemChanged.connect(self.on_tech_select)
        left_layout.addWidget(self.tech_list)
        
        # Statistics panel
        stats_label = QLabel("Technology Statistics:")
        stats_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(stats_label)
        self.stats_panel = QWidget()
        stats_layout = QVBoxLayout(self.stats_panel)
        stats_layout.setContentsMargins(5, 5, 5, 5)
        self.total_devices_label = QLabel("Total Devices: 0")
        stats_layout.addWidget(self.total_devices_label)
        self.clex_devices_label = QLabel("Devices with CLEX: 0")
        stats_layout.addWidget(self.clex_devices_label)
        self.total_clex_label = QLabel("Total CLEX Definitions: 0")
        stats_layout.addWidget(self.total_clex_label)
        left_layout.addWidget(self.stats_panel)
        
        return left_panel
    
    def create_right_panel(self) -> QWidget:
        """
        Create the right panel containing devices list.
        
        Returns:
            QWidget containing the right panel
        """
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add device header
        device_header = QHBoxLayout()
        device_label = QLabel("Devices:")
        device_label.setFont(QFont("Arial", 12, QFont.Bold))
        device_header.addWidget(device_label)
        
        # Add "Only with CLEX" checkbox
        self.only_clex_checkbox = QCheckBox("Only with CLEX")
        self.only_clex_checkbox.stateChanged.connect(self.filter_devices)
        device_header.addWidget(self.only_clex_checkbox)
        
        right_layout.addLayout(device_header)
        
        # Add search layout
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter devices...")
        self.search_box.textChanged.connect(self.filter_devices)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        right_layout.addLayout(search_layout)
        
        # Add device list
        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.device_list.currentItemChanged.connect(self.on_device_select)
        self.device_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.device_list.customContextMenuRequested.connect(self.show_device_context_menu)
        right_layout.addWidget(self.device_list)
        
        return right_panel
    
    def create_clex_panel(self) -> QWidget:
        """
        Create the CLEX definition panel.
        
        Returns:
            QWidget containing the CLEX panel
        """
        clex_panel = QWidget()
        clex_layout = QVBoxLayout(clex_panel)
        clex_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add CLEX header
        clex_header = QHBoxLayout()
        self.clex_label = QLabel("CLEX Definition:")
        self.clex_label.setFont(QFont("Arial", 12, QFont.Bold))
        clex_header.addWidget(self.clex_label)
        
        # Add stretch to push buttons to the right
        clex_header.addStretch()
        
        # Add action buttons
        self.copy_button = QPushButton("Copy")
        self.copy_button.setIcon(QIcon.fromTheme("edit-copy"))
        self.copy_button.clicked.connect(self.copy_clex_to_clipboard)
        self.copy_button.setToolTip("Copy definition to clipboard")
        clex_header.addWidget(self.copy_button)
        
        self.edit_button = QPushButton("Edit")
        self.edit_button.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_button.clicked.connect(self.edit_clex_definition)
        self.edit_button.setToolTip("Edit this CLEX definition")
        clex_header.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_button.clicked.connect(self.delete_clex_definition)
        self.delete_button.setToolTip("Delete this CLEX definition")
        clex_header.addWidget(self.delete_button)
        
        clex_layout.addLayout(clex_header)
        
        # Add CLEX text area
        self.clex_text = QTextEdit()
        self.clex_text.setReadOnly(True)
        self.clex_text.setFont(QFont("Consolas", 10))
        clex_layout.addWidget(self.clex_text)
        
        # Add syntax highlighter
        self.syntax_highlighter = SyntaxHighlighter(self.clex_text.document())
        
        return clex_panel
    
    def create_floating_action_button(self):
        """Create the floating action button for new CLEX definition."""
        self.new_clex_fab = QPushButton("+", self)
        self.new_clex_fab.setFixedSize(60, 60)
        self.new_clex_fab.clicked.connect(self.new_clex_definition)
        self.new_clex_fab.setToolTip("Create new CLEX definition")
        
        # Style the button
        self.new_clex_fab.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                font-size: 28px;
                font-weight: bold;
                border-radius: 30px;
                border: none;
            }
            QPushButton:hover {
                background-color: #5294FF;
            }
            QPushButton:pressed {
                background-color: #3275E4;
            }
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 3)
        self.new_clex_fab.setGraphicsEffect(shadow)
        
        # Set initial position
        self.position_fab()
    
    def position_fab(self):
        """Position the floating action button."""
        if hasattr(self, 'new_clex_fab'):
            margin = 25
            self.new_clex_fab.move(
                self.width() - self.new_clex_fab.width() - margin,
                self.height() - self.new_clex_fab.height() - margin - self.statusBar().height()
            )
    
    def create_toolbar(self):
        """Create the application toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # Refresh action
        self.refresh_action = QAction(QIcon.fromTheme("view-refresh"), "Refresh Database", self)
        self.refresh_action.triggered.connect(self.refresh_database)
        self.refresh_action.setStatusTip("Reload the database")
        toolbar.addAction(self.refresh_action)
        
        # Global search action
        self.global_search_action = QAction(QIcon.fromTheme("edit-find"), "Global Search", self)
        self.global_search_action.triggered.connect(self.show_global_search)
        self.global_search_action.setStatusTip("Search across all technologies and devices")
        toolbar.addAction(self.global_search_action)
        
        toolbar.addSeparator()
        
        # CRUD operations
        self.new_clex_action = QAction(QIcon.fromTheme("document-new"), "New CLEX Definition", self)
        self.new_clex_action.triggered.connect(self.new_clex_definition)
        self.new_clex_action.setStatusTip("Create a new CLEX definition")
        toolbar.addAction(self.new_clex_action)
        
        self.edit_clex_action = QAction(QIcon.fromTheme("document-edit"), "Edit CLEX Definition", self)
        self.edit_clex_action.triggered.connect(self.edit_clex_definition)
        self.edit_clex_action.setStatusTip("Edit the current CLEX definition")
        toolbar.addAction(self.edit_clex_action)
        
        self.delete_clex_action = QAction(QIcon.fromTheme("edit-delete"), "Delete CLEX Definition", self)
        self.delete_clex_action.triggered.connect(self.delete_clex_definition)
        self.delete_clex_action.setStatusTip("Delete the current CLEX definition")
        toolbar.addAction(self.delete_clex_action)
        
        toolbar.addSeparator()
        
        # Compare action
        self.compare_action = QAction(QIcon.fromTheme("view-split-left-right"), "Compare Devices", self)
        self.compare_action.triggered.connect(self.show_compare_dialog)
        self.compare_action.setStatusTip("Compare CLEX definitions between two devices")
        toolbar.addAction(self.compare_action)
        
        # Stats action
        self.stats_action = QAction(QIcon.fromTheme("x-office-spreadsheet"), "CLEX Statistics", self)
        self.stats_action.triggered.connect(self.show_stats_dialog)
        self.stats_action.setStatusTip("View statistics about CLEX definitions")
        toolbar.addAction(self.stats_action)
        
        # Bulk operations action
        self.bulk_action = QAction(QIcon.fromTheme("edit-select-all"), "Bulk Operations", self)
        self.bulk_action.triggered.connect(self.show_bulk_operations_dialog)
        self.bulk_action.setStatusTip("Perform operations on multiple items")
        toolbar.addAction(self.bulk_action)
        
        toolbar.addSeparator()
        
        # Export action
        self.export_action = QAction(QIcon.fromTheme("document-save-as"), "Export", self)
        self.export_action.triggered.connect(self.show_export_dialog)
        self.export_action.setStatusTip("Export CLEX definitions")
        toolbar.addAction(self.export_action)
        
        toolbar.addSeparator()
        
        # Dark mode action
        self.dark_mode_action = QAction(QIcon.fromTheme("weather-clear-night"), "Toggle Dark Mode", self)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        self.dark_mode_action.setStatusTip("Switch between light and dark mode")
        toolbar.addAction(self.dark_mode_action)
        
        # Undo/redo actions
        toolbar.addSeparator()
        
        self.undo_action = QAction(QIcon.fromTheme("edit-undo"), "Undo", self)
        self.undo_action.triggered.connect(self.undo_operation)
        self.undo_action.setStatusTip("Undo the last operation")
        self.undo_action.setEnabled(False)
        toolbar.addAction(self.undo_action)
        
        self.redo_action = QAction(QIcon.fromTheme("edit-redo"), "Redo", self)
        self.redo_action.triggered.connect(self.redo_operation)
        self.redo_action.setStatusTip("Redo the last undone operation")
        self.redo_action.setEnabled(False)
        toolbar.addAction(self.redo_action)
    
    def create_menu(self):
        """Create the application menu."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        refresh_action = QAction("Refresh Database", self)
        refresh_action.triggered.connect(self.refresh_database)
        refresh_action.setShortcut(QKeySequence("F5"))
        file_menu.addAction(refresh_action)
        
        export_action = QAction("Export...", self)
        export_action.triggered.connect(self.show_export_dialog)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        copy_action = QAction("Copy CLEX Definition", self)
        copy_action.triggered.connect(self.copy_clex_to_clipboard)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        edit_menu.addAction(copy_action)
        
        edit_menu.addSeparator()
        
        global_search_action = QAction("Global Search...", self)
        global_search_action.triggered.connect(self.show_global_search)
        global_search_action.setShortcut(QKeySequence("Ctrl+F"))
        edit_menu.addAction(global_search_action)
        
        edit_menu.addSeparator()
        
        new_clex_action = QAction("New CLEX Definition", self)
        new_clex_action.triggered.connect(self.new_clex_definition)
        new_clex_action.setShortcut(QKeySequence("Ctrl+N"))
        edit_menu.addAction(new_clex_action)
        
        edit_clex_action = QAction("Edit CLEX Definition", self)
        edit_clex_action.triggered.connect(self.edit_clex_definition)
        edit_clex_action.setShortcut(QKeySequence("Ctrl+E"))
        edit_menu.addAction(edit_clex_action)
        
        delete_clex_action = QAction("Delete CLEX Definition", self)
        delete_clex_action.triggered.connect(self.delete_clex_definition)
        delete_clex_action.setShortcut(QKeySequence("Delete"))
        edit_menu.addAction(delete_clex_action)
        
        edit_menu.addSeparator()
        
        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(self.undo_operation)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(self.redo_operation)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        edit_menu.addAction(redo_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        compare_action = QAction("Compare Devices...", self)
        compare_action.triggered.connect(self.show_compare_dialog)
        compare_action.setShortcut(QKeySequence("Ctrl+D"))
        view_menu.addAction(compare_action)
        
        stats_action = QAction("CLEX Statistics...", self)
        stats_action.triggered.connect(self.show_stats_dialog)
        stats_action.setShortcut(QKeySequence("Ctrl+T"))
        view_menu.addAction(stats_action)
        
        bulk_action = QAction("Bulk Operations...", self)
        bulk_action.triggered.connect(self.show_bulk_operations_dialog)
        bulk_action.setShortcut(QKeySequence("Ctrl+B"))
        view_menu.addAction(bulk_action)
        
        view_menu.addSeparator()
        
        dark_mode_action = QAction("Toggle Dark Mode", self)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        dark_mode_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        view_menu.addAction(dark_mode_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Navigation shortcuts
        next_tech_shortcut = QShortcut(QKeySequence("Alt+Down"), self)
        next_tech_shortcut.activated.connect(self.select_next_tech)
        
        prev_tech_shortcut = QShortcut(QKeySequence("Alt+Up"), self)
        prev_tech_shortcut.activated.connect(self.select_prev_tech)
        
        next_device_shortcut = QShortcut(QKeySequence("Down"), self)
        next_device_shortcut.activated.connect(self.select_next_device)
        
        prev_device_shortcut = QShortcut(QKeySequence("Up"), self)
        prev_device_shortcut.activated.connect(self.select_prev_device)
        
        # Focus shortcuts
        focus_tech_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        focus_tech_shortcut.activated.connect(lambda: self.tech_list.setFocus())
        
        focus_device_shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        focus_device_shortcut.activated.connect(lambda: self.device_list.setFocus())
        
        focus_search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        focus_search_shortcut.activated.connect(lambda: self.search_box.setFocus())
    
    def update_undo_redo_actions(self):
        """Update the enabled state of undo/redo actions."""
        self.undo_action.setEnabled(self.command_manager.can_undo())
        if self.command_manager.can_undo():
            self.undo_action.setStatusTip(self.command_manager.get_undo_description())
        else:
            self.undo_action.setStatusTip("Nothing to undo")
        
        self.redo_action.setEnabled(self.command_manager.can_redo())
        if self.command_manager.can_redo():
            self.redo_action.setStatusTip(self.command_manager.get_redo_description())
        else:
            self.redo_action.setStatusTip("Nothing to redo")
    
    def undo_operation(self):
        """Undo the last operation."""
        description = self.command_manager.undo()
        if description:
            self.status_bar.showMessage(f"Undone: {description}")
            self.refresh_view()
        self.update_undo_redo_actions()
    
    def redo_operation(self):
        """Redo the last undone operation."""
        description = self.command_manager.redo()
        if description:
            self.status_bar.showMessage(f"Redone: {description}")
            self.refresh_view()
        self.update_undo_redo_actions()
    
    def refresh_view(self):
        """Refresh the current view based on selected technology and device."""
        if self.current_tech_id:
            self.load_devices(self.current_tech_id)
            if self.current_device_id:
                self.select_device_by_id(self.current_device_id)
    
    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.syntax_highlighter.set_dark_mode(self.dark_mode)
        self.settings.setValue("dark_mode", self.dark_mode)
    
    def apply_theme(self):
        """Apply the current theme (light or dark) to the application."""
        if self.dark_mode:
            # Set dark palette
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            QApplication.setPalette(palette)
            
            # Set stylesheet for tooltips
            self.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
        else:
            # Reset to default light palette
            QApplication.setPalette(QApplication.style().standardPalette())
            self.setStyleSheet("")
    
    def filter_technologies(self):
        """Filter technologies based on search text."""
        search_text = self.tech_search_box.text().lower()
        
        if search_text:
            filtered_technologies = [
                (tech_id, tech_name, tech_version) 
                for tech_id, tech_name, tech_version in self.all_technologies 
                if search_text in tech_name.lower() or 
                (tech_version and search_text in tech_version.lower())
            ]
        else:
            filtered_technologies = self.all_technologies.copy()
        
        self.technologies = filtered_technologies
        self.update_technology_listbox()
        
        if search_text:
            self.status_bar.showMessage(f"Found {len(self.technologies)} technologies matching '{search_text}'")
        else:
            self.status_bar.showMessage(f"Showing all {len(self.technologies)} technologies")
    
    def clear_technology_search(self):
        """Clear the technology search box and reset the filter."""
        self.tech_search_box.clear()
        self.filter_technologies()
        self.tech_search_box.setFocus()
    
    def load_technologies(self):
        """Load technologies from the database."""
        self.loading_overlay.show_loading("Loading technologies...")
        self.status_indicator.start_indeterminate()
        print("Starting technology loading")
        
        try:
            # Create worker using thread manager
            worker = self.thread_manager.create_worker(LoadTechnologiesWorker, self.db_file)
            
            # Connect worker signals
            worker.result_signal.connect(self.on_technologies_loaded)
            worker.error_signal.connect(self.on_db_error)
            worker.status_signal.connect(lambda msg: self.status_bar.showMessage(msg))
            worker.progress_signal.connect(lambda val: self.status_indicator.set_progress(val))
            
            # Start the worker
            print("Starting worker thread for technologies")
            worker.start()
            
        except Exception as e:
            print(f"Exception in load_technologies: {str(e)}")
            self.loading_overlay.hide_loading()
            self.status_indicator.reset()
            QMessageBox.critical(self, "Database Error", f"Failed to load technologies: {e}")
            self.status_bar.showMessage("Error loading technologies")


    def on_technologies_loaded(self, technologies):
        """
        Handle loaded technologies.
        
        Args:
            technologies: List of technology tuples (id, name, version)
        """
        print(f"Technologies loaded: {len(technologies)}")
        self.all_technologies = technologies
        self.technologies = self.all_technologies.copy()
        self.update_technology_listbox()
        self.status_bar.showMessage(f"Loaded {len(self.technologies)} technologies")
        self.loading_overlay.hide_loading()
        self.status_indicator.reset()

    def on_db_error(self, error_message):
        """
        Handle database error.
        
        Args:
            error_message: Error message from the worker
        """
        print(f"Database error: {error_message}")
        self.loading_overlay.hide_loading()
        self.status_indicator.reset()
        QMessageBox.critical(self, "Database Error", error_message)
        self.status_bar.showMessage("Error in database operation")



    def update_technology_listbox(self):
        """Update the technology list display."""
        self.tech_list.clear()
        for tech_id, tech_name, tech_version in self.technologies:
            display_text = f"{tech_name} v{tech_version}" if tech_version else tech_name
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, tech_id)
            self.tech_list.addItem(item)
    
    def on_tech_select(self, current, previous):
        """Handle technology selection with direct database access."""
        if not current:
            return
        
        tech_id = current.data(Qt.UserRole)
        self.current_tech_id = tech_id
        tech_name = current.text().split(" v")[0]
        
        print(f"Technology selected: {tech_name} (ID: {tech_id})")
        
        self.loading_overlay.show_loading(f"Loading devices for {tech_name}...")
        self.status_indicator.start_indeterminate()
        
        try:
            # Direct database access
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get devices
            cursor.execute(
                "SELECT id, name, has_clex_definition FROM devices WHERE technology_id = ? ORDER BY name", 
                (tech_id,)
            )
            devices = cursor.fetchall()
            
            # Get statistics
            cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE technology_id = ? AND has_clex_definition = 1", 
                (tech_id,)
            )
            clex_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM clex_definitions c JOIN devices d ON c.device_id = d.id "
                "WHERE d.technology_id = ?", 
                (tech_id,)
            )
            total_clex = cursor.fetchone()[0]
            
            conn.close()
            
            # Update state
            self.devices = devices
            self.all_devices = self.devices.copy()
            
            # Update statistics
            self.update_statistics(
                len(self.devices),
                clex_count,
                total_clex
            )
            
            # Update device list
            self.update_device_listbox()
            
            # Clear CLEX display
            self.clear_clex_display()
            
            self.status_bar.showMessage(f"Loaded {len(devices)} devices ({clex_count} with CLEX definitions)")
            
        except Exception as e:
            print(f"Error loading devices: {str(e)}")
            QMessageBox.critical(self, "Database Error", f"Failed to load devices: {e}")
            self.status_bar.showMessage("Error loading devices")
        
        # Always ensure loading indicators are hidden
        self.loading_overlay.hide()
        self.status_indicator.reset()
        
        self.settings.setValue("last_tech_id", tech_id)

    def load_devices(self, tech_id):
        """
        Load devices for a technology.
        
        Args:
            tech_id: ID of the technology
        """
        self.loading_overlay.show_loading("Loading devices...")
        self.status_indicator.start_indeterminate()
        
        try:
            # Create worker using thread manager and passing both required parameters
            worker = self.thread_manager.create_worker(LoadDevicesWorker, self.db_file, tech_id)
            
            # Connect worker signals
            worker.result_signal.connect(self.on_devices_loaded)
            worker.error_signal.connect(self.on_db_error)
            worker.status_signal.connect(lambda msg: self.status_bar.showMessage(msg))
            worker.progress_signal.connect(lambda val: self.status_indicator.set_progress(val))
            
            # Start the worker
            worker.start()
            
        except Exception as e:
            self.loading_overlay.hide_loading()
            self.status_indicator.reset()
            QMessageBox.critical(self, "Database Error", f"Failed to load devices: {e}")
            self.status_bar.showMessage("Error loading devices")
    
    def on_devices_loaded(self, results):
        """
        Handle loaded devices.
        
        Args:
            results: Dictionary containing devices and statistics
        """
        self.devices = results["devices"]
        self.all_devices = self.devices.copy()
        
        # Update statistics
        self.update_statistics(
            len(self.devices),
            results["clex_count"],
            results["total_clex"]
        )
        
        # Filter and display devices
        self.filter_devices()
        
        # Clear CLEX display
        self.clear_clex_display()
        
        self.status_bar.showMessage(f"Loaded {len(self.devices)} devices ({results['clex_count']} with CLEX definitions)")
        self.loading_overlay.hide_loading()
        self.status_indicator.reset()
    
    def update_statistics(self, total_devices, clex_devices, total_clex):
        """
        Update technology statistics display.
        
        Args:
            total_devices: Total number of devices
            clex_devices: Number of devices with CLEX
            total_clex: Total number of CLEX definitions
        """
        self.total_devices_label.setText(f"Total Devices: {total_devices}")
        self.clex_devices_label.setText(f"Devices with CLEX: {clex_devices}")
        self.total_clex_label.setText(f"Total CLEX Definitions: {total_clex}")
    
    def filter_devices(self):
        """Filter devices based on search text and checkbox state."""
        search_text = self.search_box.text().lower()
        only_clex = self.only_clex_checkbox.isChecked()
        
        # Apply search filter
        if search_text:
            filtered_devices = [
                d for d in self.all_devices 
                if search_text in d[1].lower()
            ]
        else:
            filtered_devices = self.all_devices.copy()
        
        # Apply CLEX filter
        if only_clex:
            filtered_devices = [d for d in filtered_devices if d[2] == 1]
        
        self.devices = filtered_devices
        self.update_device_listbox()
        
        # Update status message
        if search_text and only_clex:
            self.status_bar.showMessage(f"Found {len(self.devices)} devices with CLEX matching '{search_text}'")
        elif search_text:
            self.status_bar.showMessage(f"Found {len(self.devices)} devices matching '{search_text}'")
        elif only_clex:
            self.status_bar.showMessage(f"Showing {len(self.devices)} devices with CLEX definitions")
        else:
            self.status_bar.showMessage(f"Showing all {len(self.devices)} devices")
    
    def update_device_listbox(self):
        """Update the device list display."""
        self.device_list.clear()
        for device_id, device_name, has_clex in self.devices:
            item = QListWidgetItem(device_name)
            item.setData(Qt.UserRole, device_id)
            
            if has_clex:
                font = QFont("Arial", 10, QFont.Bold)
                item.setFont(font)
                item.setForeground(QColor("black") if not self.dark_mode else QColor("white"))
            else:
                item.setForeground(QColor("gray"))
            
            self.device_list.addItem(item)
    

    def on_device_select(self, current, previous):
        """Handle device selection with direct database access."""
        if not current:
            return
        
        device_id = current.data(Qt.UserRole)
        self.current_device_id = device_id
        self.current_device_name = current.text()
        has_clex = current.font().bold()
        
        if has_clex:
            self.load_clex_definition(device_id, self.current_device_name)
        else:
            self.clear_clex_display()
            self.status_bar.showMessage(f"Device '{self.current_device_name}' has no CLEX definition")
        
        self.update_button_states()
        self.settings.setValue("last_device_id", device_id)

    def load_clex_definition(self, device_id, device_name):
        """Load CLEX definition using direct database access."""
        self.loading_overlay.show_loading(f"Loading CLEX definition for {device_name}...")
        self.status_indicator.start_indeterminate()
        
        try:
            # Direct database access
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT folder_path, file_name, definition_text FROM clex_definitions WHERE device_id = ?", 
                (device_id,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                folder_path, file_name, definition_text = result
                
                # Process result directly
                header_text = f"Device: {device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n"
                full_text = header_text + definition_text
                
                # Update UI directly
                self.clex_text.clear()
                self.clex_text.setPlainText(full_text)
                self.setWindowTitle(f"Enhanced CLEX Browser - {device_name}")
                self.status_bar.showMessage(f"Loaded CLEX definition for '{device_name}'")
            else:
                self.clear_clex_display()
                self.status_bar.showMessage(f"No CLEX definition found for '{device_name}'")
            
        except Exception as e:
            self.clear_clex_display()
            QMessageBox.critical(self, "Database Error", f"Failed to load CLEX definition: {e}")
            self.status_bar.showMessage(f"Error loading CLEX definition for {device_name}")
        
        # Always ensure loading indicators are hidden
        self.loading_overlay.hide()
        self.status_indicator.reset()

    def on_clex_definition_loaded(self, clex_data):
        """
        Handle loaded CLEX definition.
        
        Args:
            clex_data: Dictionary with CLEX definition data
        """
        if clex_data["found"]:
            self.clex_text.clear()
            self.clex_text.setPlainText(clex_data["full_text"])
            self.setWindowTitle(f"Enhanced CLEX Browser - {self.current_device_name}")
            self.status_bar.showMessage(f"Loaded CLEX definition for '{self.current_device_name}'")
        else:
            self.clear_clex_display()
            self.status_bar.showMessage(clex_data["message"])
        
        self.loading_overlay.hide_loading()
        self.status_indicator.reset()
    
    def clear_clex_display(self):
        """Clear the CLEX definition display."""
        self.clex_text.clear()
        self.setWindowTitle("Enhanced CLEX Browser")
    
    def copy_clex_to_clipboard(self):
        """Copy CLEX definition to clipboard."""
        text = self.clex_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.status_bar.showMessage("CLEX definition copied to clipboard")
    
    def show_device_context_menu(self, position):
        """
        Show context menu for devices.
        
        Args:
            position: Position where the context menu should be shown
        """
        item = self.device_list.itemAt(position)
        if not item:
            return
        
        device_id = item.data(Qt.UserRole)
        device_name = item.text()
        has_clex = item.font().bold()
        
        menu = QMenu()
        
        # Add "Add CLEX" option if the device doesn't have CLEX
        if not has_clex:
            new_action = menu.addAction("Add CLEX Definition")
            new_action.triggered.connect(lambda: self.add_clex_for_device(device_id, device_name))
        
        # Add options for devices with CLEX
        if has_clex:
            view_action = menu.addAction("View CLEX Definition")
            view_action.triggered.connect(lambda: self.load_clex_definition(device_id, device_name))
            
            copy_action = menu.addAction("Copy CLEX Definition")
            copy_action.triggered.connect(lambda: self.select_and_copy_device(device_id, device_name))
            
            menu.addSeparator()
            
            edit_action = menu.addAction("Edit CLEX Definition")
            edit_action.triggered.connect(lambda: self.edit_clex_for_device(device_id))
            
            delete_action = menu.addAction("Delete CLEX Definition")
            delete_action.triggered.connect(lambda: self.delete_clex_for_device(device_id))
            
            menu.addSeparator()
            
            # Add favorite option
            if self.favorites.is_favorite(device_id):
                favorite_action = menu.addAction("Remove from Favorites")
                favorite_action.triggered.connect(lambda: self.remove_favorite(device_id))
            else:
                favorite_action = menu.addAction("Add to Favorites")
                favorite_action.triggered.connect(lambda: self.add_to_favorites(device_id, device_name))
        
        menu.exec_(self.device_list.mapToGlobal(position))
    
    def add_to_favorites(self, device_id, device_name):
        """
        Add a device to favorites.
        
        Args:
            device_id: ID of the device
            device_name: Name of the device
        """
        if self.current_tech_id:
            tech_id = self.current_tech_id
            
            # Get technology name
            tech_name = None
            for i in range(self.tech_list.count()):
                item = self.tech_list.item(i)
                if item.data(Qt.UserRole) == tech_id:
                    tech_name = item.text().split(" v")[0]
                    break
            
            if tech_name:
                if self.favorites.add_favorite(device_id, device_name, tech_id, tech_name):
                    self.status_bar.showMessage(f"Added '{device_name}' to favorites")
                else:
                    self.status_bar.showMessage(f"'{device_name}' is already in favorites")
    
    def remove_favorite(self, device_id):
        """
        Remove a device from favorites.
        
        Args:
            device_id: ID of the device to remove
        """
        self.favorites.remove_favorite(device_id)
        self.status_bar.showMessage("Removed from favorites")
    
    def add_clex_for_device(self, device_id, device_name):
        """
        Add CLEX definition for a device.
        
        Args:
            device_id: ID of the device
            device_name: Name of the device
        """
        # Set the current device
        self.current_device_id = device_id
        self.current_device_name = device_name
        
        # Call the new CLEX dialog
        self.new_clex_definition()
    
    def edit_clex_for_device(self, device_id):
        """
        Edit CLEX definition for a device.
        
        Args:
            device_id: ID of the device
        """
        # Set the current device if it's different
        if self.current_device_id != device_id:
            self.select_device_by_id(device_id)
        
        self.edit_clex_definition()
    
    def delete_clex_for_device(self, device_id):
        """
        Delete CLEX definition for a device.
        
        Args:
            device_id: ID of the device
        """
        # Set the current device if it's different
        if self.current_device_id != device_id:
            self.select_device_by_id(device_id)
        
        self.delete_clex_definition()
    
    def select_and_copy_device(self, device_id, device_name):
        """
        Select a device and copy its CLEX definition.
        
        Args:
            device_id: ID of the device
            device_name: Name of the device
        """
        self.select_device_by_id(device_id)
        self.copy_clex_to_clipboard()
    
    def select_device_by_id(self, device_id):
        """
        Select a device by its ID.
        
        Args:
            device_id: ID of the device to select
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get technology ID for the device
            tech_id = None
            device_info = self.db_manager.get_device_info(device_id)
            
            if device_info:
                tech_id = device_info[0]
                
                # Select the technology if needed
                if self.current_tech_id != tech_id:
                    for i in range(self.tech_list.count()):
                        tech_item = self.tech_list.item(i)
                        if tech_item and tech_item.data(Qt.UserRole) == tech_id:
                            self.tech_list.setCurrentItem(tech_item)
                            QApplication.processEvents()
                            break
                
                # Select the device
                for i in range(self.device_list.count()):
                    item = self.device_list.item(i)
                    if item and item.data(Qt.UserRole) == device_id:
                        self.device_list.setCurrentItem(item)
                        return True
                
                # If device not found and "Only with CLEX" is checked, uncheck it
                if self.only_clex_checkbox.isChecked():
                    self.only_clex_checkbox.setChecked(False)
                    QApplication.processEvents()
                    
                    # Try again
                    for i in range(self.device_list.count()):
                        item = self.device_list.item(i)
                        if item and item.data(Qt.UserRole) == device_id:
                            self.device_list.setCurrentItem(item)
                            return True
            
            return False
            
        except Exception as e:
            self.status_bar.showMessage(f"Error selecting device: {e}")
            return False
    
    def select_next_tech(self):
        """Select the next technology in the list."""
        current_row = self.tech_list.currentRow()
        if current_row < self.tech_list.count() - 1:
            self.tech_list.setCurrentRow(current_row + 1)
    
    def select_prev_tech(self):
        """Select the previous technology in the list."""
        current_row = self.tech_list.currentRow()
        if current_row > 0:
            self.tech_list.setCurrentRow(current_row - 1)
    
    def select_next_device(self):
        """Select the next device in the list."""
        current_row = self.device_list.currentRow()
        if current_row < self.device_list.count() - 1:
            self.device_list.setCurrentRow(current_row + 1)
    
    def select_prev_device(self):
        """Select the previous device in the list."""
        current_row = self.device_list.currentRow()
        if current_row > 0:
            self.device_list.setCurrentRow(current_row - 1)
    
    def update_button_states(self):
        """Update the enabled/disabled state of buttons based on selection."""
        has_device_selected = self.current_device_id is not None
        has_clex = False
        
        if has_device_selected:
            # Check if the selected device has a CLEX definition
            device_info = self.db_manager.get_device_info(self.current_device_id)
            if device_info:
                has_clex = device_info[2] == 1
        
        # Update button states
        if hasattr(self, 'edit_button'):
            self.edit_button.setEnabled(has_device_selected and has_clex)
            self.edit_clex_action.setEnabled(has_device_selected and has_clex)
            
        if hasattr(self, 'delete_button'):
            self.delete_button.setEnabled(has_device_selected and has_clex)
            self.delete_clex_action.setEnabled(has_device_selected and has_clex)
            
        if hasattr(self, 'copy_button'):
            self.copy_button.setEnabled(has_device_selected and has_clex)
    
    def refresh_database(self):
        """Refresh the database by reloading data."""
        if self.current_tech_id:
            self.load_devices(self.current_tech_id)
        else:
            self.load_technologies()
    
    def reload_database(self):
        """Reload the database from a log file."""
        from dialogs.confirmation_dialog import ConfirmationService
        
        confirmation_service = ConfirmationService()
        if not confirmation_service.confirm_action(
            self,
            "Refresh Database",
            "Do you want to reload the database from a log file?",
            "This will replace the current database with data from the selected log file. "
            "Any changes you have made will be lost.",
            dialog_type="warning",
            confirm_text="Refresh",
            cancel_text="Cancel",
            dialog_id="refresh_database",
            dont_show_option=True
        ):
            return
        
        log_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select CLEX Log File",
            "",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*.*)"
        )
        
        if not log_file:
            return
        
        # Create progress dialog
        progress_dialog = ProgressDialog(self)
        progress_dialog.show()
        
        # Create worker
        self.db_worker = DatabaseWorker(log_file, self.db_file)
        
        self.db_worker.progress_signal.connect(progress_dialog.update_progress)
        self.db_worker.status_signal.connect(progress_dialog.update_status)
        self.db_worker.finished_signal.connect(self.on_database_reload_finished)
        self.db_worker.start()
        
        # Show dialog
        if progress_dialog.exec_() == QDialog.Rejected:
            self.db_worker.terminate()
            self.status_bar.showMessage("Database reload cancelled")
    
    def on_database_reload_finished(self, success, error_message):
        """
        Handle database reload completion.
        
        Args:
            success: Whether the reload was successful
            error_message: Error message if not successful
        """
        if success:
            # Clear command history
            self.command_manager.clear_history()
            
            # Reload data
            self.load_technologies()
            self.update_button_states()
            
            QMessageBox.information(
                self,
                "Refresh Complete",
                "Database has been refreshed successfully."
            )
            
            self.status_bar.showMessage("Database refreshed")
        else:
            QMessageBox.critical(
                self,
                "Refresh Error",
                f"Failed to refresh database: {error_message}"
            )
            
            self.status_bar.showMessage("Database refresh failed")
    
    def new_clex_definition(self):
        """Show dialog to create a new CLEX definition."""
        dialog = NewCLEXDialog(self, self.db_file, self.db_manager)
        if dialog.exec_() == QDialog.Accepted and self.current_tech_id:
            self.load_devices(self.current_tech_id)
            self.update_button_states()
            self.update_undo_redo_actions()
    
    def edit_clex_definition(self):
        """Show dialog to edit the current CLEX definition."""
        if not self.current_device_id:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a device with a CLEX definition."
            )
            return
        
        # Check if the device has a CLEX definition
        device_info = self.db_manager.get_device_info(self.current_device_id)
        if not device_info or device_info[2] != 1:
            QMessageBox.warning(
                self,
                "No CLEX Definition",
                "The selected device does not have a CLEX definition."
            )
            return
        
        # Get confirmation
        from dialogs.confirmation_dialog import ConfirmationService
        confirmation_service = ConfirmationService()
        if not confirmation_service.confirm_edit(
            self,
            "CLEX Definition",
            self.current_device_name,
            dialog_id="edit_clex_definition",
            dont_show_option=True
        ):
            return
        
        # Show edit dialog
        dialog = EditCLEXDialog(
            self,
            self.db_file,
            self.current_device_id,
            self.db_manager
        )
        
        if dialog.exec_() == QDialog.Accepted:
            self.load_clex_definition(self.current_device_id, self.current_device_name)
            self.update_button_states()
            self.update_undo_redo_actions()
    
    def delete_clex_definition(self):
        """Delete the current CLEX definition."""
        if not self.current_device_id:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a device with a CLEX definition."
            )
            return
        
        # Check if the device has a CLEX definition
        device_info = self.db_manager.get_device_info(self.current_device_id)
        if not device_info or device_info[2] != 1:
            QMessageBox.warning(
                self,
                "No CLEX Definition",
                "The selected device does not have a CLEX definition."
            )
            return
        
        # Get confirmation
        from dialogs.confirmation_dialog import ConfirmationService
        confirmation_service = ConfirmationService()
        if not confirmation_service.confirm_delete(
            self,
            "CLEX Definition",
            self.current_device_name,
            dialog_id="delete_clex_definition",
            dont_show_option=True
        ):
            return
        
        try:
            # Get the definition before deleting (for undo)
            clex_data = self.db_manager.get_clex_definition(self.current_device_id)
            if clex_data:
                folder_path, file_name, definition_text = clex_data
                
                # Create command for undo/redo
                command = DeleteClexDefinitionCommand(
                    self.current_device_id,
                    {
                        "folder_path": folder_path,
                        "file_name": file_name,
                        "definition_text": definition_text
                    },
                    self.db_manager.delete_clex_definition,
                    self.db_manager.add_clex_definition
                )
                
                # Execute command
                if self.command_manager.execute_command(command):
                    self.update_undo_redo_actions()
                    
                    # Refresh view
                    self.load_devices(self.current_tech_id)
                    self.clear_clex_display()
                    self.status_bar.showMessage("CLEX definition deleted")
                    self.update_button_states()
                else:
                    QMessageBox.critical(
                        self,
                        "Delete Error",
                        "Failed to delete CLEX definition."
                    )
            else:
                QMessageBox.critical(
                    self,
                    "Delete Error",
                    "Failed to retrieve CLEX definition for delete operation."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Database Error",
                f"Failed to delete CLEX definition: {e}"
            )
    
    def show_global_search(self):
        """Show the global search dialog."""
        dialog = GlobalSearchDialog(self, self.db_file, self.db_manager)
        dialog.exec_()
    
    def show_compare_dialog(self):
        """Show the compare dialog."""
        dialog = CompareDialog(self, self.db_file)
        dialog.exec_()
    
    def show_export_dialog(self):
        """Show the export dialog."""
        dialog = ExportDialog(self, self.db_file)
        dialog.exec_()
    
    def show_stats_dialog(self):
        """Show the statistics dialog."""
        dialog = StatsDialog(self, self.db_file)
        dialog.exec_()
    
    def show_bulk_operations_dialog(self):
        """Show the bulk operations dialog."""
        dialog = BulkOperationsDialog(self, self.db_file, self.db_manager)
        dialog.operationCompleted.connect(self.on_bulk_operation_completed)
        dialog.exec_()
    
    def on_bulk_operation_completed(self, operation_type, success_count):
        """
        Handle completion of a bulk operation.
        
        Args:
            operation_type: Type of operation completed
            success_count: Number of successful operations
        """
        if operation_type == "delete" and success_count > 0:
            self.refresh_database()
            self.command_manager.clear_history()  # Clear undo history after bulk operation
            self.update_undo_redo_actions()
    
    def show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About Enhanced CLEX Browser",
            "Enhanced CLEX Browser\n\n"
            "Version 2.0\n\n"
            "This application allows browsing and exploring CLEX definitions for "
            "semiconductor technologies.\n\n"
            "Created with PyQt5"
        )
    
    def restore_settings(self):
        """Restore application settings."""
        # Restore window geometry
        if self.settings.contains("window_geometry"):
            self.restoreGeometry(self.settings.value("window_geometry"))
        
        # Restore dark mode setting
        if self.settings.contains("dark_mode"):
            self.dark_mode = self.settings.value("dark_mode") == "true" or self.settings.value("dark_mode") is True
            self.apply_theme()
            self.syntax_highlighter.set_dark_mode(self.dark_mode)
        
        # Restore last selected technology
        if self.settings.contains("last_tech_id"):
            last_tech_id = int(self.settings.value("last_tech_id"))
            for i in range(self.tech_list.count()):
                item = self.tech_list.item(i)
                if item.data(Qt.UserRole) == last_tech_id:
                    self.tech_list.setCurrentItem(item)
                    break
        
        # Restore last selected device
        if self.settings.contains("last_device_id"):
            last_device_id = int(self.settings.value("last_device_id"))
            QTimer.singleShot(500, lambda: self.select_device_by_id(last_device_id))
        
        self.update_button_states()
    
    
    def closeEvent(self, event):
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        # Save settings before closing
        self.settings.setValue("window_geometry", self.saveGeometry())
        
        # Wait for all threads to finish
        if hasattr(self, 'thread_manager') and self.thread_manager.active_threads:
            from PyQt5.QtWidgets import QMessageBox
            from PyQt5.QtCore import Qt
            
            reply = QMessageBox.question(
                self, 
                "Threads Still Running",
                f"There are {len(self.thread_manager.active_threads)} operations in progress. "
                "Wait for them to finish before closing?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Show busy cursor and disable UI
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.setEnabled(False)
                
                # Wait for threads to finish
                self.thread_manager.wait_for_threads()
                
                # Restore cursor and UI
                QApplication.restoreOverrideCursor()
                self.setEnabled(True)
        
        # Accept the close event
        event.accept()
    
    def resizeEvent(self, event):
        """
        Handle window resize event.
        
        Args:
            event: Resize event
        """
        super().resizeEvent(event)
        self.position_fab()  # Reposition the floating action button