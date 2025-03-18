# dialogs/global_search_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QPushButton, QCheckBox, QTableWidget, QTableWidgetItem,
                            QAbstractItemView, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt
from typing import Optional, List, Tuple, Any, Union
import sqlite3

class GlobalSearchDialog(QDialog):
    """
    Dialog for searching across all technologies and CLEX definitions.
    
    This dialog allows users to search for text in device names and CLEX
    definitions across the entire database, with options for case sensitivity
    and search scope.
    """
    
    def __init__(self, parent=None, db_file=None, db_manager=None):
        """
        Initialize the global search dialog.
        
        Args:
            parent: Parent widget
            db_file: Path to the SQLite database file
            db_manager: Optional DatabaseManager instance
        """
        super().__init__(parent)
        self.db_file = db_file
        self.db_manager = db_manager
        self.parent = parent
        
        self.setWindowTitle("Global Search")
        self.resize(800, 600)
        self.setup_ui()
        
        # Focus the search input when dialog opens
        self.search_input.setFocus()
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search for:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("Search")
        self.search_button.setToolTip("Start the search")
        self.search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_button)
        
        layout.addLayout(search_layout)
        
        # Search options
        options_layout = QHBoxLayout()
        
        self.case_checkbox = QCheckBox("Case Sensitive")
        self.case_checkbox.setToolTip("Match exact case of search term")
        options_layout.addWidget(self.case_checkbox)
        
        self.devices_checkbox = QCheckBox("Device Names")
        self.devices_checkbox.setChecked(True)
        self.devices_checkbox.setToolTip("Search in device names")
        options_layout.addWidget(self.devices_checkbox)
        
        self.defs_checkbox = QCheckBox("CLEX Definitions")
        self.defs_checkbox.setChecked(True)
        self.defs_checkbox.setToolTip("Search in CLEX definition text")
        options_layout.addWidget(self.defs_checkbox)
        
        layout.addLayout(options_layout)
        
        # Results table
        results_label = QLabel("Search Results:")
        layout.addWidget(results_label)
        
        self.results_table = QTableWidget()
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Device", "Technology", "Type", "Match"])
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.results_table.doubleClicked.connect(self.on_result_double_clicked)
        self.results_table.setAlternatingRowColors(True)  # Improve readability
        layout.addWidget(self.results_table)
        
        # Button area
        button_layout = QHBoxLayout()
        
        self.view_button = QPushButton("View Selected")
        self.view_button.setToolTip("View the selected search result")
        self.view_button.clicked.connect(self.view_selected)
        self.view_button.setEnabled(False)  # Disable until a result is selected
        button_layout.addWidget(self.view_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.setToolTip("Close the search dialog")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Connect selection changed to update button state
        self.results_table.itemSelectionChanged.connect(self.update_button_state)
    
    def update_button_state(self):
        """Enable or disable the view button based on selection."""
        self.view_button.setEnabled(len(self.results_table.selectedItems()) > 0)
    
    def perform_search(self):
        """Execute the search based on user inputs."""
        search_text = self.search_input.text().strip()
        
        if not search_text:
            QMessageBox.warning(self, "Empty Search", "Please enter a search term.")
            return
        
        case_sensitive = self.case_checkbox.isChecked()
        search_devices = self.devices_checkbox.isChecked()
        search_defs = self.defs_checkbox.isChecked()
        
        if not search_devices and not search_defs:
            QMessageBox.warning(self, "No Search Scope", 
                              "Please select at least one search scope (Device Names or CLEX Definitions).")
            return
        
        # Show a small loading indicator in the status bar
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage("Searching...")
        
        self.setCursor(Qt.BusyCursor)  # Show busy cursor
        
        try:
            # Use database manager if available, otherwise use direct SQL
            if self.db_manager:
                results = self.db_manager.search_devices_and_clex(
                    search_text, case_sensitive, search_devices, search_defs)
            else:
                results = self._perform_search_sql(
                    search_text, case_sensitive, search_devices, search_defs)
            
            self.display_search_results(results, search_text, case_sensitive)
            
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"Failed to perform search: {e}")
        
        finally:
            self.unsetCursor()  # Restore normal cursor
            if hasattr(self, 'status_bar'):
                self.status_bar.clearMessage()
    
    def _perform_search_sql(self, search_text: str, case_sensitive: bool, 
                          search_devices: bool, search_defs: bool) -> List[Tuple]:
        """
        Perform the search using direct SQL queries.
        
        Args:
            search_text: Text to search for
            case_sensitive: Whether to use case-sensitive search
            search_devices: Whether to search device names
            search_defs: Whether to search CLEX definitions
            
        Returns:
            List of search results
        """
        results = []
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            if search_devices:
                query = (
                    "SELECT d.id, d.name, t.name, t.id FROM devices d "
                    "JOIN technologies t ON d.technology_id = t.id WHERE " + 
                    ("d.name LIKE ?" if case_sensitive else "LOWER(d.name) LIKE LOWER(?)") + 
                    " ORDER BY t.name, d.name"
                )
                cursor.execute(query, (f"%{search_text}%",))
                for device_id, device_name, tech_name, tech_id in cursor.fetchall():
                    results.append((device_id, device_name, tech_name, tech_id, "Device Name", device_name))
            
            if search_defs:
                query = (
                    "SELECT d.id, d.name, t.name, t.id, c.definition_text FROM clex_definitions c "
                    "JOIN devices d ON c.device_id = d.id "
                    "JOIN technologies t ON d.technology_id = t.id WHERE " + 
                    ("c.definition_text LIKE ?" if case_sensitive else "LOWER(c.definition_text) LIKE LOWER(?)") + 
                    " ORDER BY t.name, d.name"
                )
                cursor.execute(query, (f"%{search_text}%",))
                for device_id, device_name, tech_name, tech_id, definition_text in cursor.fetchall():
                    match_pos = (
                        definition_text.find(search_text) if case_sensitive 
                        else definition_text.lower().find(search_text.lower())
                    )
                    if match_pos >= 0:
                        start_line = (
                            definition_text.rfind('\n', 0, match_pos) + 1 
                            if definition_text.rfind('\n', 0, match_pos) >= 0 else 0
                        )
                        end_line = (
                            definition_text.find('\n', match_pos) 
                            if definition_text.find('\n', match_pos) >= 0 else len(definition_text)
                        )
                        context = definition_text[start_line:end_line]
                        results.append((device_id, device_name, tech_name, tech_id, "CLEX Definition", context))
            
            conn.close()
            return results
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    def display_search_results(self, results: List[Tuple], search_text: str, case_sensitive: bool):
        """
        Display the search results in the table.
        
        Args:
            results: List of search result tuples
            search_text: The original search text
            case_sensitive: Whether the search was case-sensitive
        """
        self.results_table.setRowCount(len(results))
        
        for row, (device_id, device_name, tech_name, tech_id, match_type, context) in enumerate(results):
            # Create and populate table items
            device_item = QTableWidgetItem(device_name)
            tech_item = QTableWidgetItem(tech_name)
            type_item = QTableWidgetItem(match_type)
            
            # Highlight the search term in the context
            highlight_start = (
                context.find(search_text) if case_sensitive 
                else context.lower().find(search_text.lower())
            )
            
            if highlight_start >= 0:
                # Create a version of the context with visual markers around the match
                context_with_highlight = (
                    f"{context[:highlight_start]}→{context[highlight_start:highlight_start+len(search_text)]}←"
                    f"{context[highlight_start+len(search_text):]}"
                )
                context_item = QTableWidgetItem(context_with_highlight)
            else:
                context_item = QTableWidgetItem(context)
            
            # Store the device ID and technology ID as user data
            device_item.setData(Qt.UserRole, (device_id, tech_id))
            
            # Add items to the table
            self.results_table.setItem(row, 0, device_item)
            self.results_table.setItem(row, 1, tech_item)
            self.results_table.setItem(row, 2, type_item)
            self.results_table.setItem(row, 3, context_item)
        
        # Update status message
        status_message = f"Found {len(results)} matches for '{search_text}'"
        self.setWindowTitle(f"Global Search - {status_message}")
        
        # Select the first result if available
        if len(results) > 0:
            self.results_table.selectRow(0)
    
    def on_result_double_clicked(self, index):
        """Handle double-click on a search result."""
        self.view_selected()
    
    def view_selected(self):
        """View the currently selected search result."""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a result to view.")
            return
        
        row = selected_rows[0].row()
        device_data = self.results_table.item(row, 0).data(Qt.UserRole)
        
        if device_data and self.parent:
            device_id, tech_id = device_data
            self.accept()  # Close the dialog
            
            # Navigate to the selected device in the parent window
            if hasattr(self.parent, 'select_device_by_id'):
                if self.parent.select_device_by_id(device_id):
                    if hasattr(self.parent, 'status_bar'):
                        self.parent.status_bar.showMessage(f"Selected device from search results")
                else:
                    QMessageBox.warning(
                        self.parent, 
                        "Selection Failed", 
                        "Could not select the device from search results."
                    )
        else:
            QMessageBox.warning(
                self, 
                "Selection Failed", 
                "Invalid device data or no parent window."
            )