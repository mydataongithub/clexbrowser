import sys
import os
import sqlite3
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QSettings

# Import the database creator
from database_creator import process_log_file

# Import the enhanced CLEX browser
from clex_browser import EnhancedCLEXBrowser

def main():
    # Set up application
    app = QApplication(sys.argv)
    app.setApplicationName("CLEX Database Manager")
    app.setOrganizationName("CLEXTools")
    
    # Get settings
    settings = QSettings()
    
    # Handle command line arguments
    db_file = "clex_database.db"
    
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        log_file = sys.argv[1]
        
        # Check if database should be refreshed
        refresh_db = len(sys.argv) > 2 and sys.argv[2].lower() == "refresh"
        
        if not os.path.exists(db_file) or refresh_db:
            try:
                if os.path.exists(db_file) and refresh_db:
                    os.remove(db_file)
                
                print(f"Creating/refreshing database from {log_file}...")
                process_log_file(log_file, db_file)
                print(f"Database created/refreshed: {db_file}")
            except Exception as e:
                print(f"Error creating database: {e}")
                QMessageBox.critical(None, "Error", f"Failed to create database: {e}")
                return
    elif not os.path.exists(db_file):
        # No database exists and no log file provided
        QMessageBox.critical(None, "Error", "Database file not found and no log file provided.\n\n"
                                         "Usage: python main.py [log_file] [refresh]")
        return
    
    # Launch the enhanced browser
    browser = EnhancedCLEXBrowser(db_file)
    browser.show()
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()