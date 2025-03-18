from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                           QWidget, QTextEdit, QTableWidget, QTableWidgetItem,
                           QPushButton, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import sqlite3
import re
from typing import List, Dict, Tuple, Any, Optional

class StatsDialog(QDialog):
    """
    Dialog for displaying statistics about CLEX definitions.
    
    This dialog shows an overview of CLEX definitions in the database,
    information about voltage/current limits, and technology-specific data.
    """
    
    def __init__(self, parent=None, db_file=None):
        """
        Initialize the statistics dialog.
        
        Args:
            parent: Parent widget
            db_file: Path to the SQLite database file
        """
        super().__init__(parent)
        self.db_file = db_file
        self.setWindowTitle("CLEX Statistics")
        self.resize(800, 600)
        self.setup_ui()
        self.refresh_stats()
    
    def setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Overview tab
        self.overview_tab = QWidget()
        self.create_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")
        
        # Limits tab
        self.limits_tab = QWidget()
        self.create_limits_tab()
        self.tabs.addTab(self.limits_tab, "Voltage/Current Limits")
        
        # Technology tab
        self.tech_tab = QWidget()
        self.create_tech_tab()
        self.tabs.addTab(self.tech_tab, "Technologies")
        
        layout.addWidget(self.tabs)
        
        # Button area
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Refresh statistics from the database")
        self.refresh_button.clicked.connect(self.refresh_stats)
        button_layout.addWidget(self.refresh_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_overview_tab(self):
        """Create the overview tab content."""
        layout = QVBoxLayout()
        
        # Overview text area
        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)
        layout.addWidget(self.overview_text)
        
        self.overview_tab.setLayout(layout)
    
    def create_limits_tab(self):
        """Create the voltage/current limits tab content."""
        layout = QVBoxLayout()
        
        # Limits table
        self.limits_table = QTableWidget()
        self.limits_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.limits_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.limits_table.setSortingEnabled(True)
        self.limits_table.setAlternatingRowColors(True)
        layout.addWidget(self.limits_table)
        
        self.limits_tab.setLayout(layout)
    
    def create_tech_tab(self):
        """Create the technologies tab content."""
        layout = QVBoxLayout()
        
        # Technology table
        self.tech_table = QTableWidget()
        self.tech_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tech_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tech_table.setSortingEnabled(True)
        self.tech_table.setAlternatingRowColors(True)
        layout.addWidget(self.tech_table)
        
        self.tech_tab.setLayout(layout)
    
    def refresh_stats(self):
        """Refresh all statistics from the database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Refresh overview tab
            self.refresh_overview_stats(cursor)
            
            # Refresh limits tab
            self.refresh_limits_stats(cursor)
            
            # Refresh technology tab
            self.refresh_tech_stats(cursor)
            
            conn.close()
        
        except sqlite3.Error as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Database Error", f"Failed to load statistics: {e}")
    
    def refresh_overview_stats(self, cursor: sqlite3.Cursor):
        """
        Refresh overview statistics.
        
        Args:
            cursor: Database cursor
        """
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM technologies")
        tech_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM devices")
        device_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM devices WHERE has_clex_definition = 1")
        clex_device_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clex_definitions")
        clex_count = cursor.fetchone()[0]
        
        # Calculate percentage of devices with CLEX definitions
        clex_percentage = 0
        if device_count > 0:
            clex_percentage = (clex_device_count / device_count) * 100
        
        # Get top technologies by CLEX definitions
        cursor.execute(
            "SELECT t.name, COUNT(d.id) as clex_count "
            "FROM technologies t "
            "JOIN devices d ON t.id = d.technology_id "
            "WHERE d.has_clex_definition = 1 "
            "GROUP BY t.name "
            "ORDER BY clex_count DESC LIMIT 10"
        )
        top_techs = cursor.fetchall()
        
        # Build HTML content
        overview_text = f"""
<h2>CLEX Database Statistics</h2>
<table style="border-collapse: collapse; width: 100%;">
<tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Total Technologies</b></td><td style="padding: 8px; border: 1px solid #ddd;">{tech_count}</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Total Devices</b></td><td style="padding: 8px; border: 1px solid #ddd;">{device_count}</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Devices with CLEX Definitions</b></td><td style="padding: 8px; border: 1px solid #ddd;">{clex_device_count} ({clex_percentage:.1f}%)</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Total CLEX Definitions</b></td><td style="padding: 8px; border: 1px solid #ddd;">{clex_count}</td></tr>
</table>
<h3>Top Technologies by CLEX Definitions</h3>
"""
        
        if top_techs:
            overview_text += """
<table style="border-collapse: collapse; width: 100%;">
<tr><th style="padding: 8px; border: 1px solid #ddd; background-color: #f2f2f2; text-align: left;">Technology</th><th style="padding: 8px; border: 1px solid #ddd; background-color: #f2f2f2; text-align: left;">CLEX Devices</th></tr>
"""
            for tech_name, clex_count in top_techs:
                overview_text += f"""<tr><td style="padding: 8px; border: 1px solid #ddd;">{tech_name}</td><td style="padding: 8px; border: 1px solid #ddd;">{clex_count}</td></tr>"""
            overview_text += "</table>"
        else:
            overview_text += "<p>No technologies with CLEX definitions found.</p>"
        
        self.overview_text.setHtml(overview_text)
    
    def refresh_limits_stats(self, cursor: sqlite3.Cursor):
        """
        Refresh voltage/current limits statistics.
        
        Args:
            cursor: Database cursor
        """
        voltage_limits = []
        current_limits = []
        
        # Extract voltage and current limits from CLEX definitions
        cursor.execute(
            "SELECT d.name, t.name, c.definition_text "
            "FROM clex_definitions c "
            "JOIN devices d ON c.device_id = d.id "
            "JOIN technologies t ON d.technology_id = t.id"
        )
        
        for device_name, tech_name, definition_text in cursor.fetchall():
            # Extract voltage limits
            for match in re.finditer(r'expr=".*?V\(([^)]+)\).*?min=([^,\s]+).*?max=([^,\s]+)', definition_text):
                terminals, min_val, max_val = match.groups()
                try:
                    min_val = float(min_val) if min_val.replace('.', '', 1).isdigit() else min_val
                    max_val = float(max_val) if max_val.replace('.', '', 1).isdigit() else max_val
                except:
                    pass
                voltage_limits.append((device_name, tech_name, terminals, min_val, max_val))
            
            # Extract current limits
            for match in re.finditer(r'expr="I\(([^)]+)\)".*?min=([^,\s]+).*?max=([^,\s]+)', definition_text):
                terminal, min_val, max_val = match.groups()
                try:
                    min_val = float(min_val) if min_val.replace('.', '', 1).isdigit() else min_val
                    max_val = float(max_val) if max_val.replace('.', '', 1).isdigit() else max_val
                except:
                    pass
                current_limits.append((device_name, tech_name, terminal, min_val, max_val))
        
        # Set up voltage limits table
        self.limits_table.clear()
        self.limits_table.setColumnCount(5)
        self.limits_table.setHorizontalHeaderLabels(["Device", "Technology", "Terminals", "Min Value", "Max Value"])
        
        # Populate voltage limits
        if voltage_limits:
            self.limits_table.setRowCount(len(voltage_limits) + 1)
            
            # Add header row
            header_item = QTableWidgetItem("Voltage Limits (V)")
            header_item.setBackground(QColor(230, 230, 230))
            header_font = QFont()
            header_font.setBold(True)
            header_item.setFont(header_font)
            self.limits_table.setItem(0, 0, header_item)
            
            # Fill cells in header row
            for i in range(1, 5):
                item = QTableWidgetItem("")
                item.setBackground(QColor(230, 230, 230))
                self.limits_table.setItem(0, i, item)
            
            # Add voltage limit rows
            for row, (device_name, tech_name, terminals, min_val, max_val) in enumerate(voltage_limits, 1):
                self.limits_table.setItem(row, 0, QTableWidgetItem(device_name))
                self.limits_table.setItem(row, 1, QTableWidgetItem(tech_name))
                self.limits_table.setItem(row, 2, QTableWidgetItem(terminals))
                self.limits_table.setItem(row, 3, QTableWidgetItem(str(min_val)))
                self.limits_table.setItem(row, 4, QTableWidgetItem(str(max_val)))
        
        # Resize columns to content
        self.limits_table.resizeColumnsToContents()
    
    def refresh_tech_stats(self, cursor: sqlite3.Cursor):
        """
        Refresh technology statistics.
        
        Args:
            cursor: Database cursor
        """
        # Get technology statistics
        cursor.execute(
            "SELECT t.name, t.version, "
            "COUNT(d.id) as device_count, "
            "SUM(CASE WHEN d.has_clex_definition = 1 THEN 1 ELSE 0 END) as clex_count "
            "FROM technologies t "
            "LEFT JOIN devices d ON t.id = d.technology_id "
            "GROUP BY t.id "
            "ORDER BY t.name"
        )
        techs = cursor.fetchall()
        
        # Set up table
        self.tech_table.clear()
        self.tech_table.setColumnCount(5)
        self.tech_table.setHorizontalHeaderLabels([
            "Technology", "Version", "Total Devices", "CLEX Devices", "CLEX Coverage (%)"
        ])
        
        # Populate table
        self.tech_table.setRowCount(len(techs))
        for row, (tech_name, tech_version, device_count, clex_count) in enumerate(techs):
            # Calculate coverage percentage
            coverage = 0
            if device_count > 0 and clex_count is not None:
                coverage = (clex_count / device_count) * 100
            
            # Create table items
            self.tech_table.setItem(row, 0, QTableWidgetItem(tech_name))
            self.tech_table.setItem(row, 1, QTableWidgetItem(tech_version or ""))
            self.tech_table.setItem(row, 2, QTableWidgetItem(str(device_count)))
            self.tech_table.setItem(row, 3, QTableWidgetItem(str(clex_count or 0)))
            
            coverage_item = QTableWidgetItem(f"{coverage:.1f}")
            coverage_item.setData(Qt.DisplayRole, coverage)  # For proper sorting
            self.tech_table.setItem(row, 4, coverage_item)
        
        # Resize columns to content
        self.tech_table.resizeColumnsToContents()