from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QRadioButton, QPushButton, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
import sqlite3
import os
from datetime import datetime
import re
from typing import List, Optional, Dict, Tuple, Set

class ExportDialog(QDialog):
    """
    Dialog for exporting CLEX definitions to various file formats.
    
    This dialog allows users to export a single device, all devices in a 
    technology, or all devices in the database, with options for various
    export formats (text, HTML, CSV).
    """
    
    def __init__(self, parent=None, db_file=None):
        """
        Initialize the export dialog.
        
        Args:
            parent: Parent widget
            db_file: Path to the SQLite database file
        """
        super().__init__(parent)
        self.db_file = db_file
        self.setWindowTitle("Export CLEX Definitions")
        self.resize(600, 400)
        
        # Get device information from parent
        self.current_device_id = parent.current_device_id if parent else None
        self.current_device_name = parent.current_device_name if parent else None
        self.current_tech_id = parent.current_tech_id if parent else None
        self.current_tech_name = None
        
        if parent and hasattr(parent, 'tech_list') and parent.tech_list.currentItem():
            self.current_tech_name = parent.tech_list.currentItem().text().split(" v")[0]
        
        # Selected devices for bulk export
        self.preselected_devices = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        # Export options group
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout()
        
        self.current_radio = QRadioButton("Export Current Device Only")
        self.current_radio.setChecked(True)
        options_layout.addWidget(self.current_radio)
        
        self.tech_radio = QRadioButton("Export All Devices in Current Technology")
        options_layout.addWidget(self.tech_radio)
        
        self.all_radio = QRadioButton("Export All Devices in All Technologies")
        options_layout.addWidget(self.all_radio)
        
        self.selected_radio = QRadioButton("Export Selected Devices")
        self.selected_radio.setVisible(False)  # Hidden until devices are preselected
        options_layout.addWidget(self.selected_radio)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Format options group
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout()
        
        self.txt_radio = QRadioButton("Plain Text (.txt)")
        self.txt_radio.setChecked(True)
        self.txt_radio.setToolTip("Export as plain text with minimal formatting")
        format_layout.addWidget(self.txt_radio)
        
        self.html_radio = QRadioButton("HTML (.html)")
        self.html_radio.setToolTip("Export as HTML with syntax highlighting")
        format_layout.addWidget(self.html_radio)
        
        self.csv_radio = QRadioButton("CSV (.csv)")
        self.csv_radio.setToolTip("Export as CSV for spreadsheet applications")
        format_layout.addWidget(self.csv_radio)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.export_button = QPushButton("Export...")
        self.export_button.clicked.connect(self.export)
        button_layout.addWidget(self.export_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def set_preselected_devices(self, device_ids: List[int]):
        """
        Set preselected devices for bulk export.
        
        Args:
            device_ids: List of device IDs to export
        """
        if device_ids:
            self.preselected_devices = device_ids
            self.selected_radio.setVisible(True)
            self.selected_radio.setChecked(True)
            self.selected_radio.setText(f"Export Selected Devices ({len(device_ids)})")
    
    def export(self):
        """Handle the export operation based on selected options."""
        # Determine export type
        if self.selected_radio.isChecked() and self.selected_radio.isVisible():
            if not self.preselected_devices:
                QMessageBox.warning(self, "No Devices Selected", "No devices have been preselected for export.")
                return
            export_type = "selected"
        elif self.current_radio.isChecked():
            if not self.current_device_id:
                QMessageBox.warning(self, "No Device Selected", "Please select a device to export.")
                return
            export_type = "current"
        elif self.tech_radio.isChecked():
            if not self.current_tech_id:
                QMessageBox.warning(self, "No Technology Selected", "Please select a technology to export.")
                return
            export_type = "technology"
        else:
            export_type = "all"
        
        # Determine export format
        if self.txt_radio.isChecked():
            export_format = "txt"
            filter_string = "Text Files (*.txt)"
        elif self.html_radio.isChecked():
            export_format = "html"
            filter_string = "HTML Files (*.html)"
        else:
            export_format = "csv"
            filter_string = "CSV Files (*.csv)"
        
        # Get export file path
        default_name = ""
        if export_type == "current" and self.current_device_name:
            default_name = f"clex_{self.current_device_name}.{export_format}"
        elif export_type == "technology" and self.current_tech_name:
            default_name = f"clex_{self.current_tech_name}.{export_format}"
        else:
            default_name = f"clex_export.{export_format}"
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Export File", default_name, filter_string
        )
        
        if not file_name:
            return
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Fetch data based on export type
            if export_type == "current":
                cursor.execute(
                    "SELECT d.name, t.name, c.folder_path, c.file_name, c.definition_text "
                    "FROM clex_definitions c "
                    "JOIN devices d ON c.device_id = d.id "
                    "JOIN technologies t ON d.technology_id = t.id "
                    "WHERE d.id = ?", 
                    (self.current_device_id,)
                )
            elif export_type == "technology":
                cursor.execute(
                    "SELECT d.name, t.name, c.folder_path, c.file_name, c.definition_text "
                    "FROM clex_definitions c "
                    "JOIN devices d ON c.device_id = d.id "
                    "JOIN technologies t ON d.technology_id = t.id "
                    "WHERE t.id = ? ORDER BY d.name", 
                    (self.current_tech_id,)
                )
            elif export_type == "selected":
                placeholders = ",".join(["?"] * len(self.preselected_devices))
                cursor.execute(
                    f"SELECT d.name, t.name, c.folder_path, c.file_name, c.definition_text "
                    f"FROM clex_definitions c "
                    f"JOIN devices d ON c.device_id = d.id "
                    f"JOIN technologies t ON d.technology_id = t.id "
                    f"WHERE d.id IN ({placeholders}) ORDER BY t.name, d.name", 
                    self.preselected_devices
                )
            else:
                cursor.execute(
                    "SELECT d.name, t.name, c.folder_path, c.file_name, c.definition_text "
                    "FROM clex_definitions c "
                    "JOIN devices d ON c.device_id = d.id "
                    "JOIN technologies t ON d.technology_id = t.id "
                    "ORDER BY t.name, d.name"
                )
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                QMessageBox.warning(self, "No Data", "No CLEX definitions found to export.")
                return
            
            # Export based on format
            if export_format == "txt":
                self.export_to_txt(file_name, rows)
            elif export_format == "html":
                self.export_to_html(file_name, rows)
            else:
                self.export_to_csv(file_name, rows)
            
            QMessageBox.information(
                self, "Export Complete", 
                f"Successfully exported {len(rows)} CLEX definitions to {file_name}"
            )
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export data: {e}")
    
    def export_to_txt(self, file_name: str, rows: List[Tuple]):
        """
        Export data to a text file.
        
        Args:
            file_name: Path to the output file
            rows: Data rows to export
        """
        with open(file_name, 'w') as f:
            f.write(f"CLEX Definitions Export\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for device_name, tech_name, folder_path, file_name_val, definition_text in rows:
                f.write(f"{'='*80}\n")
                f.write(f"Device: {device_name}\n")
                f.write(f"Technology: {tech_name}\n")
                f.write(f"Folder: {folder_path}\n")
                f.write(f"File: {file_name_val}\n\n")
                
                # Filter out folder and file lines that may be in the definition text
                filtered_lines = [
                    line for line in definition_text.split('\n') 
                    if not line.strip().startswith(("Folder Path:", "File Name:"))
                ]
                f.write('\n'.join(filtered_lines) + "\n\n")
    
    def export_to_html(self, file_name: str, rows: List[Tuple]):
        """
        Export data to an HTML file with syntax highlighting.
        
        Args:
            file_name: Path to the output file
            rows: Data rows to export
        """
        with open(file_name, 'w') as f:
            # Write HTML header
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>CLEX Definitions Export</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .device {{ border: 1px solid #ccc; margin-bottom: 20px; padding: 10px; border-radius: 5px; }}
        .device-header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 10px; border-radius: 3px; }}
        .definition {{ font-family: monospace; white-space: pre-wrap; background-color: #f8f8f8; padding: 10px; border-radius: 3px; }}
        .keyword {{ color: #0066CC; font-weight: bold; }}
        .assertion {{ color: #CC0000; font-weight: bold; }}
        .message {{ color: #8800AA; }}
        .comment {{ color: #808080; font-style: italic; }}
    </style>
</head>
<body>
    <h1>CLEX Definitions Export</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
""")
            
            # Write device definitions
            for device_name, tech_name, folder_path, file_name_val, definition_text in rows:
                f.write(f"""    <div class="device">
        <div class="device-header">
            <h2>{device_name}</h2>
            <p><strong>Technology:</strong> {tech_name}</p>
            <p><strong>Folder:</strong> {folder_path}</p>
            <p><strong>File:</strong> {file_name_val}</p>
        </div>
        <div class="definition">
""")
                # Filter and highlight the definition
                filtered_lines = [
                    line for line in definition_text.split('\n') 
                    if not line.strip().startswith(("Folder Path:", "File Name:"))
                ]
                highlighted_def = '\n'.join(filtered_lines)
                
                # Apply syntax highlighting
                # Keywords
                for keyword in ["inline", "subckt", "assert", "expr", "min", "max", "level", "duration", "sub", "anal_types"]:
                    highlighted_def = re.sub(
                        r'\b' + keyword + r'\b', 
                        f'<span class="keyword">{keyword}</span>', 
                        highlighted_def
                    )
                
                # Assertions
                for assertion in ["clexvw", "clexcw", "clex_"]:
                    highlighted_def = re.sub(
                        r'\b' + assertion + r'\w*', 
                        lambda m: f'<span class="assertion">{m.group(0)}</span>', 
                        highlighted_def
                    )
                
                # Messages
                highlighted_def = re.sub(
                    r'message="([^"]*)"', 
                    r'message="<span class="message">\1</span>"', 
                    highlighted_def
                )
                
                # Comments
                highlighted_def = re.sub(
                    r'^(\s*\/\/.*)$', 
                    r'<span class="comment">\1</span>', 
                    highlighted_def, 
                    flags=re.MULTILINE
                )
                
                f.write(highlighted_def + "\n")
                f.write(f"""        </div>
    </div>
""")
            
            # Write HTML footer
            f.write("</body>\n</html>")
    
    def export_to_csv(self, file_name: str, rows: List[Tuple]):
        """
        Export data to a CSV file.
        
        Args:
            file_name: Path to the output file
            rows: Data rows to export
        """
        with open(file_name, 'w', newline='') as f:
            # Write header
            f.write("Technology\tFolder\tFile\tDevice\tTerminals\tCLEX Definition\n")
            
            # Write data rows
            for device_name, tech_name, folder_path, file_name_val, definition_text in rows:
                lines = definition_text.split('\n')
                
                # Extract terminals from inline subckt
                terminals = ""
                for line in lines:
                    if line.strip().startswith("inline subckt"):
                        match = re.search(r'\((.*?)\)', line)
                        if match:
                            terminals = match.group(1)
                        break
                
                # Extract CLEX assertions
                clex_lines = [
                    line.strip() for line in lines 
                    if "assert" in line and not line.strip().startswith(("Folder Path:", "File Name:"))
                ]
                
                if not clex_lines:
                    # Write a row with no CLEX assertions
                    escaped_fields = [
                        tech_name.replace('\t', ' '),
                        folder_path.replace('\t', ' '),
                        file_name_val.replace('\t', ' '),
                        device_name.replace('\t', ' '),
                        terminals.replace('\t', ' '),
                        ""
                    ]
                    f.write("\t".join(escaped_fields) + "\n")
                else:
                    # Write a row for each CLEX assertion
                    for clex_line in clex_lines:
                        escaped_fields = [
                            tech_name.replace('\t', ' '),
                            folder_path.replace('\t', ' '),
                            file_name_val.replace('\t', ' '),
                            device_name.replace('\t', ' '),
                            terminals.replace('\t', ' '),
                            clex_line.replace('\t', ' ')
                        ]
                        f.write("\t".join(escaped_fields) + "\n")