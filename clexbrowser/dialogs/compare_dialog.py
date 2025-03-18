# dialogs/compare_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
                            QGroupBox, QComboBox, QTextEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import sqlite3
from typing import Optional, List, Tuple, Any

# We'll import the SyntaxHighlighter class later when we move it to its own module
# For now, we'll assume it's available from a ui_components module
from ui_components.syntax_highlighter import SyntaxHighlighter

class CompareDialog(QDialog):
    """
    Dialog for comparing CLEX definitions between two devices.
    
    This dialog allows users to select two devices from potentially different
    technologies and compare their CLEX definitions side by side.
    """
    
    def __init__(self, parent=None, db_file=None):
        """
        Initialize the compare dialog.
        
        Args:
            parent: Parent widget
            db_file: Path to the SQLite database file
        """
        super().__init__(parent)
        self.db_file = db_file
        self.parent = parent
        self.setWindowTitle("Compare CLEX Definitions")
        self.resize(900, 600)
        
        # Initialize UI
        self.setup_ui()
        
        # Set up syntax highlighters
        self.left_highlighter = SyntaxHighlighter(
            self.left_text.document(), 
            self.parent.dark_mode if self.parent else False
        )
        self.right_highlighter = SyntaxHighlighter(
            self.right_text.document(),
            self.parent.dark_mode if self.parent else False
        )
        
        # Load initial data
        self.load_technologies()
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        # Selection area (top)
        selection_layout = QHBoxLayout()
        
        # Left panel (first device)
        left_group = self.create_device_selection_group("First Device", "left")
        selection_layout.addWidget(left_group)
        
        # Right panel (second device)
        right_group = self.create_device_selection_group("Second Device", "right")
        selection_layout.addWidget(right_group)
        
        layout.addLayout(selection_layout)
        
        # Compare button
        self.compare_button = QPushButton("Compare")
        self.compare_button.clicked.connect(self.compare_devices)
        layout.addWidget(self.compare_button, alignment=Qt.AlignCenter)
        
        # Result area (bottom)
        result_layout = QHBoxLayout()
        
        # Left text display
        self.left_text = QTextEdit()
        self.left_text.setReadOnly(True)
        result_layout.addWidget(self.left_text)
        
        # Right text display
        self.right_text = QTextEdit()
        self.right_text.setReadOnly(True)
        result_layout.addWidget(self.right_text)
        
        layout.addLayout(result_layout)
        
        # Button area
        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button, alignment=Qt.AlignRight)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_device_selection_group(self, title: str, side: str) -> QGroupBox:
        """
        Create a device selection group box.
        
        Args:
            title: Title for the group box
            side: Which side this is for ('left' or 'right')
            
        Returns:
            QGroupBox containing tech and device selection widgets
        """
        group = QGroupBox(title)
        layout = QVBoxLayout()
        
        # Technology selection
        layout.addWidget(QLabel("Technology:"))
        tech_combo = QComboBox()
        
        # Set attribute and connect signals based on side
        if side == "left":
            self.left_tech_combo = tech_combo
            self.left_tech_combo.currentIndexChanged.connect(self.on_left_tech_changed)
        else:
            self.right_tech_combo = tech_combo
            self.right_tech_combo.currentIndexChanged.connect(self.on_right_tech_changed)
        
        layout.addWidget(tech_combo)
        
        # Device selection
        layout.addWidget(QLabel("Device:"))
        device_list = QListWidget()
        
        # Set attribute based on side
        if side == "left":
            self.left_device_list = device_list
        else:
            self.right_device_list = device_list
        
        layout.addWidget(device_list)
        group.setLayout(layout)
        
        return group
    
    def load_technologies(self):
        """Load technologies into both combo boxes."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
            technologies = cursor.fetchall()
            conn.close()
            
            for tech_id, tech_name, tech_version in technologies:
                display_text = f"{tech_name} v{tech_version}" if tech_version else tech_name
                self.left_tech_combo.addItem(display_text, tech_id)
                self.right_tech_combo.addItem(display_text, tech_id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load technologies: {e}")
    
    def on_left_tech_changed(self, index: int):
        """
        Handle selection of a technology in the left combo box.
        
        Args:
            index: Index of the selected item
        """
        tech_id = self.left_tech_combo.itemData(index)
        self.load_devices(tech_id, self.left_device_list)
    
    def on_right_tech_changed(self, index: int):
        """
        Handle selection of a technology in the right combo box.
        
        Args:
            index: Index of the selected item
        """
        tech_id = self.right_tech_combo.itemData(index)
        self.load_devices(tech_id, self.right_device_list)
    
    def load_devices(self, tech_id: int, list_widget: QListWidget):
        """
        Load devices for a technology into a list widget.
        
        Args:
            tech_id: ID of the technology
            list_widget: List widget to populate
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, has_clex_definition FROM devices "
                "WHERE technology_id = ? AND has_clex_definition = 1 ORDER BY name", 
                (tech_id,)
            )
            devices = cursor.fetchall()
            conn.close()
            
            list_widget.clear()
            for device_id, device_name, has_clex in devices:
                item = QListWidget.QListWidgetItem(device_name)
                item.setData(Qt.UserRole, device_id)
                list_widget.addItem(item)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load devices: {e}")
    
    def compare_devices(self):
        """Compare the CLEX definitions of the selected devices."""
        left_item = self.left_device_list.currentItem()
        right_item = self.right_device_list.currentItem()
        
        if not left_item or not right_item:
            QMessageBox.warning(self, "Selection Required", "Please select devices from both lists.")
            return
        
        left_id = left_item.data(Qt.UserRole)
        right_id = right_item.data(Qt.UserRole)
        left_name = left_item.text()
        right_name = right_item.text()
        
        self.load_definition(left_id, left_name, self.left_text)
        self.load_definition(right_id, right_name, self.right_text)
    
    def load_definition(self, device_id: int, device_name: str, text_edit: QTextEdit):
        """
        Load the CLEX definition for a device into a text edit.
        
        Args:
            device_id: ID of the device
            device_name: Name of the device
            text_edit: QTextEdit to display the definition
        """
        try:
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
                header_text = f"Device: {device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n"
                
                # Filter out folder and file name lines from the definition
                definition_lines = definition_text.split('\n')
                filtered_lines = [
                    line for line in definition_lines 
                    if not line.strip().startswith(("Folder Path:", "File Name:"))
                ]
                filtered_definition = '\n'.join(filtered_lines)
                
                text_edit.clear()
                text_edit.setPlainText(header_text + filtered_definition)
            else:
                text_edit.clear()
                text_edit.setPlainText(f"No CLEX definition found for '{device_name}'")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load CLEX definition: {e}")