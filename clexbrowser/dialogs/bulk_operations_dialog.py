from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem,
                            QHeaderView, QAbstractItemView, QCheckBox,
                            QComboBox, QFrame, QMessageBox, QProgressBar,
                            QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
import sqlite3
from typing import List, Dict, Any, Tuple, Optional, Callable

class BulkOperationsDialog(QDialog):
    """
    Dialog for performing operations on multiple items simultaneously.
    
    This dialog allows users to select multiple devices or CLEX definitions
    and perform batch operations like deletion or export on all selected items.
    """
    
    # Signal emitted when a bulk operation is completed
    operationCompleted = pyqtSignal(str, int)  # operation_type, success_count
    
    def __init__(self, parent=None, db_file=None, db_manager=None):
        """
        Initialize the bulk operations dialog.
        
        Args:
            parent: Parent widget
            db_file: Path to the SQLite database file
            db_manager: Optional DatabaseManager instance
        """
        super().__init__(parent)
        self.db_file = db_file
        self.db_manager = db_manager
        self.parent = parent
        self.selected_items = []
        self.operation_handlers = {}
        
        self.setWindowTitle("Bulk Operations")
        self.resize(800, 600)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        
        # Header section
        header_layout = QHBoxLayout()
        
        # Operation selection
        operation_layout = QVBoxLayout()
        operation_layout.addWidget(QLabel("Operation:"))
        self.operation_combo = QComboBox()
        self.operation_combo.currentIndexChanged.connect(self.on_operation_changed)
        operation_layout.addWidget(self.operation_combo)
        header_layout.addLayout(operation_layout)
        
        # Scope selection
        scope_layout = QVBoxLayout()
        scope_layout.addWidget(QLabel("Scope:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("Current Technology", "current_tech")
        self.scope_combo.addItem("All Technologies", "all_techs")
        self.scope_combo.currentIndexChanged.connect(self.on_scope_changed)
        scope_layout.addWidget(self.scope_combo)
        header_layout.addLayout(scope_layout)
        
        # Filter options
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.only_with_clex_check = QCheckBox("Only with CLEX definitions")
        self.only_with_clex_check.setChecked(True)
        self.only_with_clex_check.stateChanged.connect(self.refresh_items)
        filter_layout.addWidget(self.only_with_clex_check)
        header_layout.addLayout(filter_layout)
        
        # Search filter
        search_layout = QVBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by name...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)
        header_layout.addLayout(search_layout)
        
        layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Items table
        self.items_table = QTableWidget()
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["", "Device", "Technology", "Has CLEX"])
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setAlternatingRowColors(True)
        layout.addWidget(self.items_table)
        
        # Selection controls
        selection_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all)
        selection_layout.addWidget(self.select_all_button)
        
        self.select_none_button = QPushButton("Select None")
        self.select_none_button.clicked.connect(self.select_none)
        selection_layout.addWidget(self.select_none_button)
        
        self.invert_selection_button = QPushButton("Invert Selection")
        self.invert_selection_button.clicked.connect(self.invert_selection)
        selection_layout.addWidget(self.invert_selection_button)
        
        selection_layout.addStretch()
        
        self.selection_label = QLabel("0 items selected")
        selection_layout.addWidget(self.selection_label)
        
        layout.addLayout(selection_layout)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Button area
        button_layout = QHBoxLayout()
        
        self.execute_button = QPushButton("Execute")
        self.execute_button.clicked.connect(self.execute_operation)
        button_layout.addWidget(self.execute_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Register standard operations
        self.register_operation("Export CLEX Definitions", self.handle_export_operation)
        self.register_operation("Delete CLEX Definitions", self.handle_delete_operation)
    
    def register_operation(self, operation_name: str, handler: Callable):
        """
        Register a bulk operation type with a handler function.
        
        Args:
            operation_name: Display name for the operation
            handler: Function to handle the operation execution
        """
        self.operation_combo.addItem(operation_name)
        self.operation_handlers[operation_name] = handler
    
    def on_operation_changed(self, index: int):
        """
        Handle changes to the selected operation.
        
        Args:
            index: Index of the newly selected operation
        """
        operation = self.operation_combo.currentText()
        
        # Adjust UI based on operation type
        if operation == "Delete CLEX Definitions":
            self.only_with_clex_check.setChecked(True)
            self.only_with_clex_check.setEnabled(False)
        else:
            self.only_with_clex_check.setEnabled(True)
        
        self.refresh_items()
    
    def on_scope_changed(self, index: int):
        """
        Handle changes to the selected scope.
        
        Args:
            index: Index of the newly selected scope
        """
        self.refresh_items()
    
    def on_search_changed(self, text: str):
        """
        Handle changes to the search filter.
        
        Args:
            text: Current search text
        """
        self.refresh_items()
    
    def refresh_items(self):
        """Load or refresh the list of items based on current settings."""
        scope = self.scope_combo.currentData()
        only_with_clex = self.only_with_clex_check.isChecked()
        search_text = self.search_input.text().strip().lower()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Determine technology filter
            tech_filter = ""
            tech_params = []
            
            if scope == "current_tech" and hasattr(self.parent, "current_tech_id"):
                tech_id = self.parent.current_tech_id
                if tech_id:
                    tech_filter = "WHERE d.technology_id = ?"
                    tech_params.append(tech_id)
            
            # Build query
            query = (
                "SELECT d.id, d.name, t.name, d.has_clex_definition, t.id "
                "FROM devices d JOIN technologies t ON d.technology_id = t.id "
            )
            
            params = tech_params.copy()
            
            if tech_filter:
                query += tech_filter
            
            if only_with_clex:
                if tech_filter:
                    query += " AND d.has_clex_definition = 1"
                else:
                    query += "WHERE d.has_clex_definition = 1"
            
            query += " ORDER BY t.name, d.name"
            
            # Execute query
            cursor.execute(query, params)
            items = cursor.fetchall()
            conn.close()
            
            # Filter by search text if needed
            if search_text:
                items = [
                    item for item in items
                    if search_text in item[1].lower() or search_text in item[2].lower()
                ]
            
            # Populate table
            self.items_table.clearContents()
            self.items_table.setRowCount(len(items))
            
            for row, (device_id, device_name, tech_name, has_clex, tech_id) in enumerate(items):
                # Checkbox cell
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                checkbox.setCheckState(Qt.Unchecked)
                self.items_table.setItem(row, 0, checkbox)
                
                # Device name cell
                device_item = QTableWidgetItem(device_name)
                device_item.setData(Qt.UserRole, (device_id, tech_id))
                if has_clex:
                    font = QFont()
                    font.setBold(True)
                    device_item.setFont(font)
                self.items_table.setItem(row, 1, device_item)
                
                # Technology name cell
                tech_item = QTableWidgetItem(tech_name)
                self.items_table.setItem(row, 2, tech_item)
                
                # Has CLEX cell
                clex_item = QTableWidgetItem("Yes" if has_clex else "No")
                self.items_table.setItem(row, 3, clex_item)
            
            # Adjust column widths
            self.items_table.setColumnWidth(0, 30)  # Checkbox column
            self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            
            # Update selection label
            self.update_selection_count()
            
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load items: {e}")
    
    def select_all(self):
        """Select all items in the table."""
        for row in range(self.items_table.rowCount()):
            checkbox = self.items_table.item(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.Checked)
        
        self.update_selection_count()
    
    def select_none(self):
        """Deselect all items in the table."""
        for row in range(self.items_table.rowCount()):
            checkbox = self.items_table.item(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.Unchecked)
        
        self.update_selection_count()
    
    def invert_selection(self):
        """Invert the current selection."""
        for row in range(self.items_table.rowCount()):
            checkbox = self.items_table.item(row, 0)
            if checkbox:
                new_state = Qt.Unchecked if checkbox.checkState() == Qt.Checked else Qt.Checked
                checkbox.setCheckState(new_state)
        
        self.update_selection_count()
    
    def update_selection_count(self):
        """Update the selection count label."""
        count = self.get_selected_count()
        self.selection_label.setText(f"{count} items selected")
        self.execute_button.setEnabled(count > 0)
    
    def get_selected_count(self) -> int:
        """
        Get the number of selected items.
        
        Returns:
            Number of selected items
        """
        count = 0
        for row in range(self.items_table.rowCount()):
            checkbox = self.items_table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.Checked:
                count += 1
        return count
    
    def get_selected_items(self) -> List[Tuple[int, str, int, str]]:
        """
        Get information about all selected items.
        
        Returns:
            List of tuples (device_id, device_name, tech_id, tech_name)
        """
        selected = []
        for row in range(self.items_table.rowCount()):
            checkbox = self.items_table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.Checked:
                device_item = self.items_table.item(row, 1)
                device_id, tech_id = device_item.data(Qt.UserRole)
                device_name = device_item.text()
                tech_name = self.items_table.item(row, 2).text()
                selected.append((device_id, device_name, tech_id, tech_name))
        return selected
    
    def execute_operation(self):
        """Execute the selected operation on the selected items."""
        operation = self.operation_combo.currentText()
        selected_items = self.get_selected_items()
        
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one item.")
            return
        
        # Get the handler for the selected operation
        handler = self.operation_handlers.get(operation)
        if not handler:
            QMessageBox.warning(self, "Operation Not Implemented",
                             f"The operation '{operation}' is not implemented.")
            return
        
        # Execute the operation
        handler(selected_items)
    
    def handle_export_operation(self, selected_items: List[Tuple[int, str, int, str]]):
        """
        Handle the export operation.
        
        Args:
            selected_items: List of selected items (device_id, device_name, tech_id, tech_name)
        """
        # Since we may not have ExportDialog fully implemented yet, use a placeholder implementation
        device_ids = [item[0] for item in selected_items]
        QMessageBox.information(self, "Export Operation", 
                               f"Export operation would be performed on {len(device_ids)} devices.")
        
        # Emit completion signal
        self.operationCompleted.emit("export", len(device_ids))
    
    def handle_delete_operation(self, selected_items: List[Tuple[int, str, int, str]]):
        """
        Handle the delete operation.
        
        Args:
            selected_items: List of selected items (device_id, device_name, tech_id, tech_name)
        """
        # Confirm deletion (placeholder if ConfirmationService not fully implemented)
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion",
            f"Are you sure you want to delete {len(selected_items)} CLEX definitions?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected_items))
        
        # Disable controls during operation
        self.execute_button.setEnabled(False)
        self.close_button.setEnabled(False)
        
        # Execute deletion
        success_count = 0
        error_count = 0
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            for i, (device_id, device_name, tech_id, tech_name) in enumerate(selected_items):
                try:
                    # Delete the CLEX definition
                    cursor.execute("DELETE FROM clex_definitions WHERE device_id = ?", (device_id,))
                    
                    # Update the device to indicate it no longer has a CLEX definition
                    cursor.execute("UPDATE devices SET has_clex_definition = 0 WHERE id = ?", (device_id,))
                    
                    success_count += 1
                except sqlite3.Error:
                    error_count += 1
                
                # Update progress
                self.progress_bar.setValue(i + 1)
            
            # Commit changes
            conn.commit()
            conn.close()
            
            # Show results
            QMessageBox.information(
                self, "Deletion Complete",
                f"Successfully deleted {success_count} CLEX definitions.\n"
                f"Failed to delete {error_count} CLEX definitions."
            )
            
            # Emit completion signal
            self.operationCompleted.emit("delete", success_count)
            
            # Refresh items
            self.refresh_items()
            
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to delete CLEX definitions: {e}")
        
        finally:
            # Hide progress bar
            self.progress_bar.setVisible(False)
            
            # Re-enable controls
            self.execute_button.setEnabled(True)
            self.close_button.setEnabled(True)