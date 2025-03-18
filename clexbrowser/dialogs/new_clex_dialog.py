from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QTextEdit, QPushButton, QComboBox,
                           QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import sqlite3
import re
from datetime import datetime
from typing import Tuple, Optional, Dict, List, Callable

from ui_components.form_validation import (ValidatedLineEdit, FormFieldGroup, 
                                         FormValidator, required_validator,
                                         min_length_validator, composite_validator)

class NewCLEXDialog(QDialog):
    """
    Dialog for creating a new CLEX definition.
    
    This dialog allows users to create a new device with a CLEX definition,
    with real-time validation to ensure all inputs are valid.
    """
    
    def __init__(self, parent=None, db_file=None, db_manager=None):
        """
        Initialize the new CLEX definition dialog.
        
        Args:
            parent: Parent widget
            db_file: Path to the SQLite database file
            db_manager: Optional DatabaseManager instance
        """
        super().__init__(parent)
        self.db_file = db_file
        self.db_manager = db_manager
        self.parent = parent
        self.form_validator = FormValidator()
        
        self.setWindowTitle("New CLEX Definition")
        self.resize(700, 500)
        self.setup_ui()
        self.load_technologies()
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        # Create form layout
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        # Technology selection
        tech_layout = QHBoxLayout()
        tech_label = QLabel("Technology:")
        tech_label.setFont(QFont("", -1, QFont.Bold))
        self.tech_combo = QComboBox()
        self.tech_combo.setMinimumWidth(300)
        self.tech_combo.currentIndexChanged.connect(self.on_tech_changed)
        tech_layout.addWidget(tech_label)
        tech_layout.addWidget(self.tech_combo)
        tech_layout.addStretch()
        form_layout.addLayout(tech_layout)
        
        # Device name
        device_validator = composite_validator(
            required_validator("Device name is required"),
            min_length_validator(2, "Device name must be at least 2 characters")
        )
        self.device_input = ValidatedLineEdit(validator=device_validator)
        self.device_input.setPlaceholderText("Enter device name")
        device_field = FormFieldGroup("Device Name:", self.device_input)
        form_layout.addWidget(device_field)
        self.form_validator.add_field("device", device_field)
        
        # Folder path
        folder_validator = required_validator("Folder path is required")
        self.folder_input = ValidatedLineEdit(validator=folder_validator)
        self.folder_input.setPlaceholderText("Enter folder path (e.g., /path/to/folder)")
        folder_field = FormFieldGroup("Folder Path:", self.folder_input)
        form_layout.addWidget(folder_field)
        self.form_validator.add_field("folder", folder_field)
        
        # File name
        file_validator = required_validator("File name is required")
        self.file_input = ValidatedLineEdit(validator=file_validator)
        self.file_input.setPlaceholderText("Enter file name (e.g., device.clex)")
        file_field = FormFieldGroup("File Name:", self.file_input)
        form_layout.addWidget(file_field)
        self.form_validator.add_field("file", file_field)
        
        # CLEX definition
        def_label = QLabel("CLEX Definition:")
        def_label.setFont(QFont("", -1, QFont.Bold))
        form_layout.addWidget(def_label)
        
        self.def_text = QTextEdit()
        self.def_text.setFont(QFont("Consolas", 10))
        self.def_text.setPlaceholderText("Enter CLEX definition here...")
        form_layout.addWidget(self.def_text)
        
        # Template button
        template_button = QPushButton("Insert Template")
        template_button.setToolTip("Insert a basic CLEX definition template")
        template_button.clicked.connect(self.insert_template)
        form_layout.addWidget(template_button, 0, Qt.AlignLeft)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save_definition)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect validation change signals
        self.device_input.textChanged.connect(self.validate_device_name)
    
    def load_technologies(self):
        """Load technologies into the combo box."""
        try:
            if self.db_manager:
                technologies = self.db_manager.get_technologies()
            else:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
                technologies = cursor.fetchall()
                conn.close()
            
            for tech_id, tech_name, tech_version in technologies:
                display_text = f"{tech_name} v{tech_version}" if tech_version else tech_name
                self.tech_combo.addItem(display_text, tech_id)
            
            # Select current technology if available
            if hasattr(self.parent, 'current_tech_id') and self.parent.current_tech_id:
                for i in range(self.tech_combo.count()):
                    if self.tech_combo.itemData(i) == self.parent.current_tech_id:
                        self.tech_combo.setCurrentIndex(i)
                        break
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load technologies: {e}")
    
    def on_tech_changed(self, index: int):
        """
        Handle technology selection change.
        
        Args:
            index: Index of the selected technology
        """
        # Clear the device name field when technology changes
        self.device_input.clear()
    
    def validate_device_name(self):
        """Validate that the device name is unique within the selected technology."""
        device_name = self.device_input.text().strip()
        if not device_name:
            return
        
        tech_id = self.tech_combo.currentData()
        if not tech_id:
            return
        
        try:
            # Use DatabaseManager if available
            if self.db_manager:
                exists = self.db_manager.device_name_exists(device_name, tech_id)
            else:
                # Otherwise use direct SQL
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM devices WHERE name = ? AND technology_id = ?", 
                    (device_name, tech_id)
                )
                exists = cursor.fetchone() is not None
                conn.close()
            
            if exists:
                self.device_input.set_validator(lambda text: (
                    False, f"A device named '{device_name}' already exists in this technology."
                ))
            else:
                # Reset to basic validation
                self.device_input.set_validator(composite_validator(
                    required_validator("Device name is required"),
                    min_length_validator(2, "Device name must be at least 2 characters")
                ))
            
        except Exception as e:
            self.device_input.set_validator(lambda text: (False, f"Validation error: {e}"))
    
    def insert_template(self):
        """Insert a CLEX definition template into the text editor."""
        device_name = self.device_input.text().strip()
        if not device_name:
            device_name = "device_name"
        
        template = f"""inline subckt {device_name} (a b c)
    // CLEX assertions
    assert clexvw_vab
        expr="V(a,b)"
        min=-2.0
        max=2.0
        level=warning
        message="Voltage between a and b is outside recommended range"
    end
    
    assert clexcw_ia
        expr="I(a)"
        min=-0.1
        max=0.1
        level=warning
        message="Current through terminal a exceeds recommended limit"
    end
end
"""
        
        self.def_text.setPlainText(template)
    
    def save_definition(self):
        """Save the new CLEX definition."""
        # Validate form
        if not self.form_validator.is_form_valid():
            self.form_validator.show_errors()
            QMessageBox.warning(self, "Validation Error", "Please correct the errors in the form.")
            return
        
        # Validate CLEX definition
        definition_text = self.def_text.toPlainText().strip()
        if not definition_text:
            QMessageBox.warning(self, "Missing Definition", "Please enter a CLEX definition.")
            return
        
        # Get form values
        tech_id = self.tech_combo.currentData()
        device_name = self.device_input.text().strip()
        folder_path = self.folder_input.text().strip()
        file_name = self.file_input.text().strip()
        
        try:
            # Check again if device name exists (in case of race condition)
            if self.db_manager:
                exists = self.db_manager.device_name_exists(device_name, tech_id)
            else:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM devices WHERE name = ? AND technology_id = ?", 
                    (device_name, tech_id)
                )
                exists = cursor.fetchone() is not None
                conn.close()
            
            if exists:
                QMessageBox.warning(
                    self, "Duplicate Device",
                    f"A device named '{device_name}' already exists in this technology."
                )
                return
            
            # Create the new device and CLEX definition
            if self.db_manager:
                device_id = self.db_manager.create_new_device_with_clex(
                    device_name, tech_id, folder_path, file_name, definition_text
                )
            else:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                # Create a new device
                cursor.execute(
                    "INSERT INTO devices (name, technology_id, has_clex_definition) VALUES (?, ?, 1)",
                    (device_name, tech_id)
                )
                device_id = cursor.lastrowid
                
                # Add the CLEX definition
                cursor.execute(
                    "INSERT INTO clex_definitions (device_id, folder_path, file_name, definition_text) "
                    "VALUES (?, ?, ?, ?)",
                    (device_id, folder_path, file_name, definition_text)
                )
                
                conn.commit()
                conn.close()
            
            QMessageBox.information(
                self, "Success", "New device and CLEX definition added successfully."
            )
            
            # Notify parent to refresh
            if hasattr(self.parent, 'refresh_database'):
                self.parent.refresh_database()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save CLEX definition: {e}")