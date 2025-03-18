import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, Qt
from clex_browser import EnhancedCLEXBrowser

class EmergencyOverlayRemover(QTimer):
    """Safety timer that automatically hides any visible loading overlays."""
    
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.setSingleShot(True)
        self.timeout.connect(self.emergency_hide)
    
    def emergency_hide(self):
        print("EMERGENCY: Forcibly hiding loading overlay")
        if hasattr(self.browser, 'loading_overlay') and self.browser.loading_overlay.isVisible():
            self.browser.loading_overlay.hide()
        if hasattr(self.browser, 'status_indicator'):
            self.browser.status_indicator.reset()
        # Force UI update
        QApplication.processEvents()

class SuperFixedCLEXBrowser(EnhancedCLEXBrowser):
    """Aggressively fixed version with direct database access for all operations."""
    
    def __init__(self, db_file):
        """Initialize with safety mechanism."""
        super().__init__(db_file)
        
        # Create emergency timeout
        self.emergency_timer = EmergencyOverlayRemover(self)
        
        # Completely disable all background loading to diagnose the issue
        print("Disabling all background loading")
        
    def load_technologies(self):
        """Override to use direct database access for initial loading."""
        print("Direct technology loading started")
        self.emergency_timer.start(5000)  # 5 seconds safety timeout
        
        # Direct database access
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, version FROM technologies ORDER BY name")
        technologies = cursor.fetchall()
        conn.close()
        
        # Process results directly
        print(f"Directly loaded {len(technologies)} technologies")
        self.all_technologies = technologies
        self.technologies = self.all_technologies.copy()
        self.update_technology_listbox()
        
        # Force UI update
        QApplication.processEvents()
        
        # Manually hide loading
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.hide()
        if hasattr(self, 'status_indicator'):
            self.status_indicator.reset()
        
        # Force another UI update
        QApplication.processEvents()
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Loaded {len(self.technologies)} technologies")
        
        # Cancel emergency timer
        self.emergency_timer.stop()
        print("Direct technology loading completed")
    
    def on_tech_select(self, current, previous):
        """Completely override tech selection to use direct database access."""
        if not current:
            return
            
        tech_id = current.data(Qt.UserRole)
        self.current_tech_id = tech_id
        tech_name = current.text().split(" v")[0]
        
        print(f"Direct device loading for technology: {tech_name} (ID: {tech_id})")
        self.emergency_timer.start(5000)  # 5 seconds safety timeout
        
        try:
            # Manually hide any existing loading overlay
            if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
                self.loading_overlay.hide()
            
            # Direct database access
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get devices
            cursor.execute(
                "SELECT id, name, has_clex_definition FROM devices WHERE technology_id = ? ORDER BY name", 
                (tech_id,)
            )
            devices = cursor.fetchall()
            
            # Get statistics
            cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE technology_id = ? AND has_clex_definition = 1", 
                (tech_id,)
            )
            clex_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM clex_definitions c JOIN devices d ON c.device_id = d.id "
                "WHERE d.technology_id = ?", 
                (tech_id,)
            )
            total_clex = cursor.fetchone()[0]
            
            # Close connection
            conn.close()
            
            # Update device state
            self.devices = devices
            self.all_devices = self.devices.copy()
            
            # Update statistics directly
            self.update_statistics(
                len(self.devices),
                clex_count,
                total_clex
            )
            
            # Update device list directly
            self.update_device_listbox()
            
            # Clear CLEX display
            self.clear_clex_display()
            
            print(f"Loaded {len(self.devices)} devices ({clex_count} with CLEX definitions)")
            
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Selected technology: {tech_name}")
                
            if hasattr(self, 'settings'):
                self.settings.setValue("last_tech_id", tech_id)
                
            # Force UI update
            QApplication.processEvents()
                
        except Exception as e:
            print(f"ERROR in direct device loading: {str(e)}")
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Error loading devices: {str(e)}")
        
        # Cancel emergency timer
        self.emergency_timer.stop()
        print("Direct device loading completed")
    
    def on_device_select(self, current, previous):
        """Completely override device selection to use direct database access."""
        if not current:
            return
        
        device_id = current.data(Qt.UserRole)
        self.current_device_id = device_id
        device_name = current.text()
        has_clex = current.font().bold()
        
        print(f"Direct CLEX loading for device: {device_name} (ID: {device_id}, has_clex: {has_clex})")
        
        # Manually hide any existing loading overlay
        if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            self.loading_overlay.hide()
        
        if has_clex:
            # Start safety timer
            self.emergency_timer.start(5000)  # 5 seconds safety timeout
            
            try:
                # Connect to database directly
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT folder_path, file_name, definition_text FROM clex_definitions WHERE device_id = ?", 
                    (device_id,)
                )
                result = cursor.fetchone()
                conn.close()
                
                # Process result
                if result:
                    folder_path, file_name, definition_text = result
                    header_text = f"Device: {device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n"
                    self.clex_text.clear()
                    self.clex_text.setPlainText(header_text + definition_text)
                    
                    if hasattr(self, 'setWindowTitle'):
                        self.setWindowTitle(f"Enhanced CLEX Browser - {device_name}")
                        
                    if hasattr(self, 'status_bar'):
                        self.status_bar.showMessage(f"Loaded CLEX definition for '{device_name}'")
                        
                    print(f"Successfully loaded CLEX definition for '{device_name}'")
                else:
                    self.clear_clex_display()
                    if hasattr(self, 'status_bar'):
                        self.status_bar.showMessage(f"No CLEX definition found for '{device_name}'")
                    print(f"No CLEX definition found for '{device_name}'")
                
            except Exception as e:
                print(f"ERROR in direct CLEX loading: {str(e)}")
                self.clear_clex_display()
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage(f"Error loading CLEX definition: {str(e)}")
            
            # Cancel emergency timer
            self.emergency_timer.stop()
            
        else:
            self.clear_clex_display()
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Device '{device_name}' has no CLEX definition")
            print(f"Device '{device_name}' has no CLEX definition")
        
        # Update button states
        self.update_button_states()
        
        # Save setting
        if hasattr(self, 'settings'):
            self.settings.setValue("last_device_id", device_id)
        
        # Force UI update
        QApplication.processEvents()
        print("Device selection completed")
    
    # Override all methods that use worker threads
    def load_devices(self, tech_id):
        """Do nothing - handled by on_tech_select."""
        print("load_devices called but ignored - using direct access instead")
        pass
    
    def load_clex_definition(self, device_id, device_name):
        """Do nothing - handled by on_device_select."""
        print("load_clex_definition called but ignored - using direct access instead")
        pass
    
    def restore_settings(self):
        """Disable automatic selection on startup to prevent issues."""
        print("Restoring basic settings only")
        # Only restore window geometry and dark mode
        if self.settings.contains("window_geometry"):
            self.restoreGeometry(self.settings.value("window_geometry"))
        
        if self.settings.contains("dark_mode"):
            self.dark_mode = self.settings.value("dark_mode") == "true" or self.settings.value("dark_mode") is True
            self.apply_theme()
            if hasattr(self, 'syntax_highlighter'):
                self.syntax_highlighter.set_dark_mode(self.dark_mode)
        
        # Skip technology and device restoration to avoid auto-selections
        print("Skipping technology and device restoration")
        
        # Update button states
        self.update_button_states()

def main():
    # Set up application
    app = QApplication(sys.argv)
    
    # Add global safety timeout
    safety_timer = QTimer()
    safety_timer.setSingleShot(True)
    safety_timer.timeout.connect(lambda: print("WARNING: Global safety timeout reached"))
    safety_timer.start(30000)  # 30 seconds
    
    # Create the browser with our super fixed class
    print("Creating super fixed browser instance...")
    browser = SuperFixedCLEXBrowser("clex_database.db")
    
    print("Showing browser...")
    browser.show()
    
    print("Entering application event loop...")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()