from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QCheckBox, QFrame, QSpacerItem,
                            QSizePolicy, QDialogButtonBox, QApplication)
from PyQt5.QtCore import Qt, QSettings, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette
from typing import Optional, Dict, List, Tuple, Callable

class ConfirmationDialog(QDialog):
    """
    Enhanced confirmation dialog with detailed information and consequences.
    
    This dialog provides clear information about the action being taken and
    its consequences, with visual cues to indicate severity.
    """
    
    # Dialog types with associated icons and colors
    DIALOG_TYPES = {
        'warning': {
            'icon': 'dialog-warning',
            'color': '#f39c12',
            'title': 'Warning',
        },
        'destructive': {
            'icon': 'dialog-error',
            'color': '#e74c3c',
            'title': 'Caution',
        },
        'information': {
            'icon': 'dialog-information',
            'color': '#3498db',
            'title': 'Information',
        },
        'question': {
            'icon': 'dialog-question',
            'color': '#2980b9',
            'title': 'Confirmation',
        }
    }
    
    def __init__(self, parent=None, settings: Optional[QSettings] = None):
        """
        Initialize the confirmation dialog.
        
        Args:
            parent: Parent widget
            settings: QSettings instance for remembering user preferences
        """
        super().__init__(parent)
        
        self.settings = settings or QSettings()
        self.dialog_id = None
        self.dont_show_option = False
        
        # Initialize UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        # Configure dialog properties
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(450)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Create header layout (icon and title)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        # Icon label
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        header_layout.addWidget(self.icon_label, 0, Qt.AlignTop)
        
        # Title and message
        message_layout = QVBoxLayout()
        
        # Title label
        self.title_label = QLabel()
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        self.title_label.setFont(title_font)
        message_layout.addWidget(self.title_label)
        
        # Message label
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        message_layout.addWidget(self.message_label)
        
        header_layout.addLayout(message_layout, 1)
        main_layout.addLayout(header_layout)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Consequences section
        consequences_layout = QVBoxLayout()
        
        # Consequences label
        consequences_title = QLabel("Consequences:")
        consequences_font = consequences_title.font()
        consequences_font.setBold(True)
        consequences_title.setFont(consequences_font)
        consequences_layout.addWidget(consequences_title)
        
        # Consequences content
        self.consequences_label = QLabel()
        self.consequences_label.setWordWrap(True)
        consequences_layout.addWidget(self.consequences_label, 1)
        
        main_layout.addLayout(consequences_layout)
        
        # "Don't show again" checkbox
        self.dont_show_checkbox = QCheckBox("Don't show this confirmation again")
        self.dont_show_checkbox.setVisible(False)
        main_layout.addWidget(self.dont_show_checkbox)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        # Create buttons
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.confirm_button)
        
        main_layout.addLayout(button_layout)
        
        # Set layout
        self.setLayout(main_layout)
    
    def should_show_dialog(self, dialog_id: str) -> bool:
        """
        Check if the dialog should be shown based on user preferences.
        
        Args:
            dialog_id: Unique identifier for the dialog
            
        Returns:
            True if the dialog should be shown, False otherwise
        """
        if not dialog_id:
            return True
        
        key = f"confirmations/show_{dialog_id}"
        return self.settings.value(key, True, type=bool)
    
    def set_content(self, title: str, message: str, consequences: str, 
                  dialog_type: str = 'question', confirm_text: str = "Confirm",
                  cancel_text: str = "Cancel", dialog_id: str = None,
                  dont_show_option: bool = False):
        """
        Set the content of the confirmation dialog.
        
        Args:
            title: Dialog title
            message: Main message explaining the action
            consequences: Description of the consequences of the action
            dialog_type: Type of dialog ('warning', 'destructive', 'information', 'question')
            confirm_text: Text for the confirm button
            cancel_text: Text for the cancel button
            dialog_id: Unique identifier for remembering "don't show again" preference
            dont_show_option: Whether to show the "don't show again" checkbox
        """
        self.dialog_id = dialog_id
        self.dont_show_option = dont_show_option
        
        # Set dialog title
        type_info = self.DIALOG_TYPES.get(dialog_type, self.DIALOG_TYPES['question'])
        self.setWindowTitle(f"{type_info['title']}: {title}")
        
        # Set icon
        icon_name = type_info['icon']
        if QIcon.hasThemeIcon(icon_name):
            icon = QIcon.fromTheme(icon_name)
            pixmap = icon.pixmap(QSize(48, 48))
            self.icon_label.setPixmap(pixmap)
        
        # Set title and message
        self.title_label.setText(title)
        self.message_label.setText(message)
        
        # Set consequences
        self.consequences_label.setText(consequences)
        
        # Set button text
        self.confirm_button.setText(confirm_text)
        self.cancel_button.setText(cancel_text)
        
        # Style confirm button based on dialog type
        if dialog_type == 'destructive':
            self.confirm_button.setStyleSheet(f"QPushButton {{ background-color: {type_info['color']}; color: white; }}")
        else:
            self.confirm_button.setStyleSheet("")
        
        # Configure "don't show again" checkbox
        self.dont_show_checkbox.setVisible(dont_show_option and dialog_id is not None)
        
    def accept(self):
        """Handle dialog acceptance, saving "don't show again" preference if needed."""
        # Save "don't show again" preference if the checkbox is checked
        if self.dont_show_option and self.dialog_id and self.dont_show_checkbox.isChecked():
            key = f"confirmations/show_{self.dialog_id}"
            self.settings.setValue(key, False)
        
        super().accept()


class ConfirmationService:
    """
    Service for managing confirmation dialogs throughout the application.
    
    This class provides methods for showing various types of confirmation
    dialogs with consistent styling and behavior.
    """
    
    def __init__(self, settings: Optional[QSettings] = None):
        """
        Initialize the confirmation service.
        
        Args:
            settings: QSettings instance for remembering user preferences
        """
        self.settings = settings or QSettings()
        self.dialog = None
    
    def confirm_action(self, parent, title: str, message: str, consequences: str,
                      dialog_type: str = 'question', confirm_text: str = "Confirm",
                      cancel_text: str = "Cancel", dialog_id: str = None,
                      dont_show_option: bool = False) -> bool:
        """
        Show a confirmation dialog and return whether the user confirmed.
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Main message explaining the action
            consequences: Description of the consequences of the action
            dialog_type: Type of dialog ('warning', 'destructive', 'information', 'question')
            confirm_text: Text for the confirm button
            cancel_text: Text for the cancel button
            dialog_id: Unique identifier for remembering "don't show again" preference
            dont_show_option: Whether to show the "don't show again" checkbox
            
        Returns:
            True if the user confirmed, False otherwise
        """
        # Check if dialog should be shown
        if dialog_id and not self.should_show_dialog(dialog_id):
            return True
        
        # Create dialog if needed
        if not self.dialog:
            self.dialog = ConfirmationDialog(parent, self.settings)
        
        # Set content
        self.dialog.set_content(
            title, message, consequences, dialog_type,
            confirm_text, cancel_text, dialog_id, dont_show_option
        )
        
        # Show dialog and return result
        result = self.dialog.exec_() == QDialog.Accepted
        return result
    
    def should_show_dialog(self, dialog_id: str) -> bool:
        """
        Check if a dialog should be shown based on user preferences.
        
        Args:
            dialog_id: Unique identifier for the dialog
            
        Returns:
            True if the dialog should be shown, False otherwise
        """
        key = f"confirmations/show_{dialog_id}"
        return self.settings.value(key, True, type=bool)
    
    def confirm_delete(self, parent, item_type: str, item_name: str, 
                     consequences: str = None, dialog_id: str = None,
                     dont_show_option: bool = False) -> bool:
        """
        Show a confirmation dialog for deleting an item.
        
        Args:
            parent: Parent widget
            item_type: Type of item being deleted (e.g., "CLEX Definition")
            item_name: Name of the item being deleted
            consequences: Custom consequences text (uses default if None)
            dialog_id: Unique identifier for remembering "don't show again" preference
            dont_show_option: Whether to show the "don't show again" checkbox
            
        Returns:
            True if the user confirmed, False otherwise
        """
        title = f"Delete {item_type}"
        message = f"Are you sure you want to delete the {item_type.lower()} for '{item_name}'?"
        
        if consequences is None:
            consequences = (
                f"This will permanently remove the {item_type.lower()} for '{item_name}'. "
                f"This action cannot be undone.\n\n"
                f"Any references to this {item_type.lower()} will be lost."
            )
        
        return self.confirm_action(
            parent, title, message, consequences,
            dialog_type='destructive', confirm_text="Delete",
            cancel_text="Cancel", dialog_id=dialog_id,
            dont_show_option=dont_show_option
        )
    
    def confirm_edit(self, parent, item_type: str, item_name: str, 
                   consequences: str = None, dialog_id: str = None,
                   dont_show_option: bool = False) -> bool:
        """
        Show a confirmation dialog for editing an item.
        
        Args:
            parent: Parent widget
            item_type: Type of item being edited (e.g., "CLEX Definition")
            item_name: Name of the item being edited
            consequences: Custom consequences text (uses default if None)
            dialog_id: Unique identifier for remembering "don't show again" preference
            dont_show_option: Whether to show the "don't show again" checkbox
            
        Returns:
            True if the user confirmed, False otherwise
        """
        title = f"Edit {item_type}"
        message = f"Are you sure you want to edit the {item_type.lower()} for '{item_name}'?"
        
        if consequences is None:
            consequences = (
                f"This will modify the {item_type.lower()} for '{item_name}'. "
                f"The previous version will be replaced with your changes.\n\n"
                f"You can undo this action after saving if needed."
            )
        
        return self.confirm_action(
            parent, title, message, consequences,
            dialog_type='warning', confirm_text="Edit",
            cancel_text="Cancel", dialog_id=dialog_id,
            dont_show_option=dont_show_option
        )
    
    def confirm_bulk_operation(self, parent, operation: str, item_type: str, 
                             item_count: int, consequences: str = None,
                             dialog_id: str = None, 
                             dont_show_option: bool = False) -> bool:
        """
        Show a confirmation dialog for a bulk operation.
        
        Args:
            parent: Parent widget
            operation: Operation being performed (e.g., "Delete", "Export")
            item_type: Type of items being operated on (e.g., "CLEX Definitions")
            item_count: Number of items affected
            consequences: Custom consequences text (uses default if None)
            dialog_id: Unique identifier for remembering "don't show again" preference
            dont_show_option: Whether to show the "don't show again" checkbox
            
        Returns:
            True if the user confirmed, False otherwise
        """
        title = f"Bulk {operation} {item_type}"
        message = f"Are you sure you want to {operation.lower()} {item_count} {item_type.lower()}?"
        
        if consequences is None:
            if operation.lower() == "delete":
                consequences = (
                    f"This will permanently remove {item_count} {item_type.lower()}. "
                    f"This action cannot be undone.\n\n"
                    f"Any references to these {item_type.lower()} will be lost."
                )
            else:
                consequences = (
                    f"This will {operation.lower()} {item_count} {item_type.lower()}. "
                    f"This operation may take some time to complete."
                )
        
        dialog_type = 'destructive' if operation.lower() == "delete" else 'warning'
        
        return self.confirm_action(
            parent, title, message, consequences,
            dialog_type=dialog_type, confirm_text=operation,
            cancel_text="Cancel", dialog_id=dialog_id,
            dont_show_option=dont_show_option
        )