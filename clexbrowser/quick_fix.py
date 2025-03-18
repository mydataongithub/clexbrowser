import sys
import sqlite3
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Monkey patch the problematic method in the original EnhancedCLEXBrowser
from clex_browser import EnhancedCLEXBrowser

# Save original method
original_load_technologies = EnhancedCLEXBrowser.load_technologies

# Define replacement method
def fixed_load_technologies(self):
    """Fixed version that uses direct database access."""
    print("Using fixed load_technologies method")
    if hasattr(self, 'loading_overlay'):
        self.loading_overlay.show_loading("Loading technologies...")
    
    if hasattr(self, 'status_indicator'):
        self.status_indicator.start_indeterminate()
    
    try:
        # Direct database access
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
        technologies = cursor.fetchall()
        conn.close()
        
        # Process results directly
        self.all_technologies = technologies
        self.technologies = self.all_technologies.copy()
        self.update_technology_listbox()
        
        # Update status
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Loaded {len(technologies)} technologies")
        
        print(f"Successfully loaded {len(technologies)} technologies")
    
    except Exception as e:
        print(f"Error loading technologies: {str(e)}")
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Error loading technologies: {str(e)}")
    
    finally:
        # Always hide loading indicators
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.hide_loading()
        
        if hasattr(self, 'status_indicator'):
            self.status_indicator.reset()

# Replace the method
EnhancedCLEXBrowser.load_technologies = fixed_load_technologies

def main():
    # Set up application
    app = QApplication(sys.argv)
    
    # Add safety mechanism
    def emergency_check():
        print("Emergency check...")
        for window in app.topLevelWidgets():
            if hasattr(window, 'loading_overlay') and window.loading_overlay.isVisible():
                print("Hiding stuck loading overlay")
                window.loading_overlay.hide()
                
            if hasattr(window, 'status_indicator'):
                window.status_indicator.reset()
    
    emergency_timer = QTimer()
    emergency_timer.timeout.connect(emergency_check)
    emergency_timer.start(5000)  # Check every 5 seconds
    
    print("Creating browser with patched method...")
    browser = EnhancedCLEXBrowser("clex_database.db")
    
    print("Showing browser...")
    browser.show()
    
    print("Entering application event loop...")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()