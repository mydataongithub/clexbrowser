# ui_components/form_validation.py
from PyQt5.QtWidgets import QLineEdit, QLabel, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QPalette
from typing import Callable, Optional, Dict, List, Tuple

class ValidatedLineEdit(QLineEdit):
    """
    A line edit widget with built-in validation and visual feedback.
    
    This enhanced line edit provides real-time validation as the user types,
    showing visual cues (color changes, icons) to indicate validation status.
    """
    
    validationChanged = pyqtSignal(bool, str)  # (is_valid, error_message)
    
    def __init__(self, parent=None, validator: Callable[[str], Tuple[bool, str]] = None):
        """
        Initialize the validated line edit.
        
        Args:
            parent: Parent widget
            validator: Function that takes a string and returns (is_valid, error_message)
        """
        super().__init__(parent)
        
        self.validator = validator
        self.is_valid = True
        self.error_message = ""
        self.validation_delay = 300  # ms
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate)
        
        # Connect signals
        self.textChanged.connect(self._on_text_changed)
        
        # Initial styling
        self.update_style()
    
    def _on_text_changed(self, text):
        """
        Handle text changes by scheduling validation.
        
        Args:
            text: New text content
        """
        # Reset validation timer to prevent excessive validation calls
        if self.validation_timer.isActive():
            self.validation_timer.stop()
        
        # Schedule validation after delay
        self.validation_timer.start(self.validation_delay)
    
    def _validate(self):
        """Validate the current text and update the UI accordingly."""
        if not self.validator:
            self.is_valid = True
            self.error_message = ""
        else:
            self.is_valid, self.error_message = self.validator(self.text())
        
        self.update_style()
        self.validationChanged.emit(self.is_valid, self.error_message)
    
    def update_style(self):
        """Update the visual style based on validation state."""
        if self.is_valid:
            self.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #aaaaaa;
                    border-radius: 3px;
                    padding: 2px;
                    background-color: #ffffff;
                }
                QLineEdit:focus {
                    border: 1px solid #4a90e2;
                }
            """)
            self.setToolTip("")
        else:
            self.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #e74c3c;
                    border-radius: 3px;
                    padding: 2px;
                    background-color: #ffeeee;
                }
                QLineEdit:focus {
                    border: 1px solid #e74c3c;
                }
            """)
            self.setToolTip(self.error_message)
    
    def set_validator(self, validator: Callable[[str], Tuple[bool, str]]):
        """
        Set or change the validator function.
        
        Args:
            validator: Function that takes a string and returns (is_valid, error_message)
        """
        self.validator = validator
        self._validate()
    
    def is_input_valid(self) -> bool:
        """
        Check if the current input is valid.
        
        Returns:
            True if the input is valid, False otherwise
        """
        self._validate()  # Force validation
        return self.is_valid
    
    def get_error_message(self) -> str:
        """
        Get the current error message.
        
        Returns:
            Error message, or empty string if input is valid
        """
        return self.error_message


class FormFieldGroup(QWidget):
    """
    A widget that groups a label, an input field, and an error message.
    
    This widget provides a standardized layout for form fields with validation,
    showing a field label, the input widget, and validation error messages.
    """
    
    def __init__(self, label_text: str, field: QWidget, parent=None):
        """
        Initialize the form field group.
        
        Args:
            label_text: Text for the field label
            field: Input widget (e.g., ValidatedLineEdit)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.field = field
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Add label
        self.label = QLabel(label_text)
        self.label.setObjectName("fieldLabel")
        layout.addWidget(self.label)
        
        # Add field
        layout.addWidget(field)
        
        # Add error message label
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setStyleSheet("QLabel#errorLabel { color: #e74c3c; font-size: 11px; }")
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        self.setLayout(layout)
        
        # Connect validation signal if available
        if hasattr(field, 'validationChanged'):
            field.validationChanged.connect(self._on_validation_changed)
    
    def _on_validation_changed(self, is_valid: bool, error_message: str):
        """
        Handle validation changes.
        
        Args:
            is_valid: Whether the input is valid
            error_message: Error message to display if invalid
        """
        if is_valid:
            self.error_label.hide()
        else:
            self.error_label.setText(error_message)
            self.error_label.show()
    
    def set_label_text(self, text: str):
        """
        Set the label text.
        
        Args:
            text: New label text
        """
        self.label.setText(text)
    
    def set_error(self, error_message: str):
        """
        Manually set an error message.
        
        Args:
            error_message: Error message to display
        """
        if error_message:
            self.error_label.setText(error_message)
            self.error_label.show()
        else:
            self.error_label.hide()
    
    def is_valid(self) -> bool:
        """
        Check if the field is valid.
        
        Returns:
            True if the field is valid, False otherwise
        """
        if hasattr(self.field, 'is_input_valid'):
            return self.field.is_input_valid()
        return True


class FormValidator:
    """
    A class to manage validation for multiple form fields.
    
    This class coordinates validation across a form with multiple fields,
    providing methods to check if the entire form is valid and get all errors.
    """
    
    def __init__(self):
        """Initialize the form validator."""
        self.fields: Dict[str, FormFieldGroup] = {}
    
    def add_field(self, field_name: str, field_group: FormFieldGroup):
        """
        Add a field to the validator.
        
        Args:
            field_name: Unique name for the field
            field_group: FormFieldGroup instance
        """
        self.fields[field_name] = field_group
    
    def is_form_valid(self) -> bool:
        """
        Check if all fields in the form are valid.
        
        Returns:
            True if all fields are valid, False otherwise
        """
        for field_group in self.fields.values():
            if not field_group.is_valid():
                return False
        return True
    
    def get_errors(self) -> Dict[str, str]:
        """
        Get all validation errors in the form.
        
        Returns:
            Dictionary mapping field names to error messages
        """
        errors = {}
        for field_name, field_group in self.fields.items():
            if hasattr(field_group.field, 'get_error_message'):
                error_message = field_group.field.get_error_message()
                if error_message:
                    errors[field_name] = error_message
        return errors
    
    def show_errors(self):
        """Display error messages for all invalid fields."""
        for field_name, field_group in self.fields.items():
            if hasattr(field_group.field, 'get_error_message'):
                error_message = field_group.field.get_error_message()
                field_group.set_error(error_message)


# Validator function factories
def required_validator(message: str = "This field is required"):
    """
    Create a validator function that requires a non-empty value.
    
    Args:
        message: Error message to display if validation fails
        
    Returns:
        Validator function
    """
    def validator(text: str) -> Tuple[bool, str]:
        if not text.strip():
            return False, message
        return True, ""
    return validator


def min_length_validator(min_length: int, message: str = None):
    """
    Create a validator function that requires a minimum text length.
    
    Args:
        min_length: Minimum required length
        message: Error message to display if validation fails
        
    Returns:
        Validator function
    """
    if message is None:
        message = f"Must be at least {min_length} characters"
    
    def validator(text: str) -> Tuple[bool, str]:
        if len(text.strip()) < min_length:
            return False, message
        return True, ""
    return validator


def regex_validator(pattern: str, message: str = "Invalid format"):
    """
    Create a validator function that checks if text matches a regex pattern.
    
    Args:
        pattern: Regular expression pattern
        message: Error message to display if validation fails
        
    Returns:
        Validator function
    """
    import re
    compiled_pattern = re.compile(pattern)
    
    def validator(text: str) -> Tuple[bool, str]:
        if not compiled_pattern.match(text):
            return False, message
        return True, ""
    return validator


def composite_validator(*validators):
    """
    Create a validator function that combines multiple validators.
    
    Args:
        validators: Validator functions to combine
        
    Returns:
        Validator function that passes only if all validators pass
    """
    def validator(text: str) -> Tuple[bool, str]:
        for v in validators:
            is_valid, message = v(text)
            if not is_valid:
                return False, message
        return True, ""
    return validator


def unique_name_validator(db_manager, tech_id: int, exclude_id: int = None, 
                        message: str = "This name already exists"):
    """
    Create a validator function that checks if a device name is unique within a technology.
    
    Args:
        db_manager: DatabaseManager instance
        tech_id: ID of the technology
        exclude_id: ID of the device to exclude from uniqueness check (for editing)
        message: Error message to display if validation fails
        
    Returns:
        Validator function
    """
    def validator(name: str) -> Tuple[bool, str]:
        # No need to check empty strings (let the required validator handle that)
        if not name.strip():
            return True, ""
        
        try:
            # Check if name exists in the database
            exists = db_manager.device_name_exists(name, tech_id)
            
            # If we're editing an existing device, its current name should be allowed
            if exclude_id:
                # Get the device's current name
                device_info = db_manager.get_device_info(exclude_id)
                if device_info and device_info[1] == name:
                    return True, ""
            
            if exists:
                return False, message
            
            return True, ""
        except Exception as e:
            return False, f"Validation error: {e}"
    
    return validator