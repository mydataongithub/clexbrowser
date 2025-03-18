from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QTextEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import sqlite3
from typing import Optional, Dict, Tuple

from ui_components.form_validation import (ValidatedLineEdit, FormFieldGroup, 
                                         FormValidator, required_validator)

class EditCLEXDialog(QDialog):
    """
    Dialog for editing an existing CLEX definition.
    
    This dialog allows users to modify the folder path, file name, and
    definition text for an existing CLEX definition.
    """
    
    def __init__(self, parent=None, db_file=None, device_id=None, db_manager=None):
        """
        Initialize the edit CLEX definition dialog.
        
        Args:
            parent: Parent widget
            db_file: Path to the SQLite database file
            device_id: ID of the device to edit
            db_manager: Optional DatabaseManager instance
        """
        super().__init__(parent)
        self.db_file = db_file
        self.db_manager = db_manager
        self.device_id = device_id
        self.parent = parent
        self.form_validator = FormValidator()
        self.original_data = None
        
        self.setWindowTitle("Edit CLEX Definition")
        self.resize(700, 500)
        self.setup_ui()
        self.load_definition()
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        # Create form layout
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        # Device information (read-only)
        device_layout = QHBoxLayout()
        device_label = QLabel("Device:")
        device_label.setFont(QFont("", -1, QFont.Bold))
        self.device_name_label = QLabel()
        self.device_name_label.setStyleSheet("font-weight: bold;")
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_name_label)
        device_layout.addStretch()
        form_layout.addLayout(device_layout)
        
        # Technology information (read-only)
        tech_layout = QHBoxLayout()
        tech_label = QLabel("Technology:")
        tech_label.setFont(QFont("", -1, QFont.Bold))
        self.tech_name_label = QLabel()
        tech_layout.addWidget(tech_label)
        tech_layout.addWidget(self.tech_name_label)
        tech_layout.addStretch()
        form_layout.addLayout(tech_layout)
        
        # Folder path
        folder_validator = required_validator("Folder path is required")
        self.folder_input = ValidatedLineEdit(validator=folder_validator)
        folder_field = FormFieldGroup("Folder Path:", self.folder_input)
        form_layout.addWidget(folder_field)
        self.form_validator.add_field("folder", folder_field)
        
        # File name
        file_validator = required_validator("File name is required")
        self.file_input = ValidatedLineEdit(validator=file_validator)
        file_field = FormFieldGroup("File Name:", self.file_input)
        form_layout.addWidget(file_field)
        self.form_validator.add_field("file", file_field)
        
        # CLEX definition
        def_label = QLabel("CLEX Definition:")
        def_label.setFont(QFont("", -1, QFont.Bold))
        form_layout.addWidget(def_label)
        
        self.def_text = QTextEdit()
        self.def_text.setFont(QFont("Consolas", 10))
        form_layout.addWidget(self.def_text)
        
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
    
    def load_definition(self):
        """Load the CLEX definition data for editing."""
        if not self.device_id:
            QMessageBox.critical(self, "Error", "No device specified for editing.")
            self.reject()
            return
        
        try:
            if self.db_manager:
                # Use DatabaseManager if available
                device_info = self.db_manager.get_device_info(self.device_id)
                if not device_info:
                    raise ValueError(f"Device with ID {self.device_id} not found")
                
                tech_id, device_name, has_clex = device_info
                
                # Get technology name
                technologies = self.db_manager.get_technologies()
                tech_name = None
                for t_id, t_name, t_version in technologies:
                    if t_id == tech_id:
                        tech_name = t_name
                        if t_version:
                            tech_name += f" v{t_version}"
                        break
                
                # Get CLEX definition
                clex_data = self.db_manager.get_clex_definition(self.device_id)
                if not clex_data:
                    raise ValueError(f"No CLEX definition found for device {device_name}")
                
                folder_path, file_name, definition_text = clex_data
                
            else:
                # Use direct SQL
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                # Get device information
                cursor.execute(
                    "SELECT d.name, t.name, t.version "
                    "FROM devices d JOIN technologies t ON d.technology_id = t.id "
                    "WHERE d.id = ?",
                    (self.device_id,)
                )
                device_info = cursor.fetchone()
                if not device_info:
                    raise ValueError(f"Device with ID {self.device_id} not found")
                
                device_name, tech_name, tech_version = device_info
                if tech_version:
                    tech_name += f" v{tech_version}"
                
                # Get CLEX definition
                cursor.execute(
                    "SELECT folder_path, file_name, definition_text "
                    "FROM clex_definitions WHERE device_id = ?",
                    (self.device_id,)
                )
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"No CLEX definition found for device {device_name}")
                
                folder_path, file_name, definition_text = result
                conn.close()
            
            # Update UI with loaded data
            self.device_name_label.setText(device_name)
            self.tech_name_label.setText(tech_name)
            self.folder_input.setText(folder_path)
            self.file_input.setText(file_name)
            self.def_text.setPlainText(definition_text)
            
            # Store original data for comparison
            self.original_data = {
                "folder_path": folder_path,
                "file_name": file_name,
                "definition_text": definition_text
            }
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CLEX definition: {e}")
            self.reject()
    
    def save_definition(self):
        """Save the modified CLEX definition."""
        # Validate form
        if not self.form_validator.is_form_valid():
            self.form_validator.show_errors()
            QMessageBox.warning(self, "Validation Error", "Please correct the errors in the form.")
            return
        
        # Get form values
        folder_path = self.folder_input.text().strip()
        file_name = self.file_input.text().strip()
        definition_text = self.def_text.toPlainText().strip()
        
        # Check if anything changed
        if (self.original_data["folder_path"] == folder_path and 
            self.original_data["file_name"] == file_name and 
            self.original_data["definition_text"] == definition_text):
            QMessageBox.information(self, "No Changes", "No changes were made to the CLEX definition.")
            self.accept()
            return
        
        # Validate CLEX definition
        if not definition_text:
            QMessageBox.warning(self, "Missing Definition", "CLEX definition cannot be empty.")
            return
        
        try:
            # Update the CLEX definition
            if self.db_manager:
                success = self.db_manager.update_clex_definition(
                    self.device_id, folder_path, file_name, definition_text
                )
            else:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE clex_definitions SET folder_path = ?, file_name = ?, definition_text = ? "
                    "WHERE device_id = ?",
                    (folder_path, file_name, definition_text, self.device_id)
                )
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
            
            if success:
                QMessageBox.information(self, "Success", "CLEX definition updated successfully.")
                
                # Notify parent to update display
                if hasattr(self.parent, 'load_clex_definition'):
                    self.parent.load_clex_definition(self.device_id, self.device_name_label.text())
                
                self.accept()
            else:
                QMessageBox.warning(self, "Update Failed", "Failed to update CLEX definition.")
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update CLEX definition: {e}")