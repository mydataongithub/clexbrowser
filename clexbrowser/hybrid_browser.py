import sys
import sqlite3
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, QTimer
from clex_browser import EnhancedCLEXBrowser

class SafeEnhancedCLEXBrowser(EnhancedCLEXBrowser):
    """
    A version of EnhancedCLEXBrowser that keeps the UI enhancements
    but uses direct database access for critical operations.
    """
    
    def __init__(self, db_file):
        """Initialize with safety features and timeout protection."""
        # Install global event filter before any UI is created
        self.app = QApplication.instance()
        if self.app:
            self.app.installEventFilter(self)
        
        # Call original init
        super().__init__(db_file)
        
        # Add safety timeout to hide loading overlay if stuck
        self.safety_timer = QTimer(self)
        self.safety_timer.setSingleShot(True)
        self.safety_timer.timeout.connect(self.safety_timeout)
        self.safety_timer.start(8000)  # 8 seconds
        
        print("Hybrid browser initialized with safety features")
    
    def safety_timeout(self):
        """Handle safety timeout by hiding any visible loading overlays."""
        print("Safety timeout triggered - checking for stuck overlays")
        if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            print("Hiding stuck loading overlay")
            self.loading_overlay.hide()
            
        if hasattr(self, 'status_indicator'):
            self.status_indicator.reset()
            
        # Force UI update
        QApplication.processEvents()
        
        # Schedule another check in 5 seconds
        self.safety_timer.start(5000)
    
    def load_technologies(self):
        """Override to use direct database access for technology loading."""
        print("Loading technologies directly")
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
            
            # Process results
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
    
    def on_tech_select(self, current, previous):
        """Override to use direct database access for device loading."""
        if not current:
            return
            
        tech_id = current.data(Qt.UserRole)
        self.current_tech_id = tech_id
        tech_name = current.text().split(" v")[0]
        
        print(f"Selected technology: {tech_name} (ID: {tech_id})")
        
        # Show loading indicators
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.show_loading(f"Loading devices for {tech_name}...")
            
        if hasattr(self, 'status_indicator'):
            self.status_indicator.start_indeterminate()
            
        try:
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
            
            conn.close()
            
            # Process results
            results = {
                "devices": devices,
                "clex_count": clex_count,
                "total_clex": total_clex
            }
            
            # Call the original handler
            self.on_devices_loaded(results)
            
            print(f"Successfully loaded {len(devices)} devices")
            
        except Exception as e:
            print(f"Error loading devices: {str(e)}")
            
            # Hide loading indicators
            if hasattr(self, 'loading_overlay'):
                self.loading_overlay.hide_loading()
                
            if hasattr(self, 'status_indicator'):
                self.status_indicator.reset()
                
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Error loading devices: {str(e)}")
                
        # Update status and settings
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Selected technology: {tech_name}")
            
        if hasattr(self, 'settings'):
            self.settings.setValue("last_tech_id", tech_id)
    
    def on_device_select(self, current, previous):
        """Override to use direct database access for CLEX definition loading."""
        if not current:
            return
            
        device_id = current.data(Qt.UserRole)
        self.current_device_id = device_id
        device_name = current.text()
        has_clex = current.font().bold()
        
        print(f"Selected device: {device_name} (ID: {device_id}, has_clex: {has_clex})")
        
        if has_clex:
            # Show loading indicators
            if hasattr(self, 'loading_overlay'):
                self.loading_overlay.show_loading(f"Loading CLEX definition for {device_name}...")
                
            if hasattr(self, 'status_indicator'):
                self.status_indicator.start_indeterminate()
                
            try:
                # Direct database access
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT folder_path, file_name, definition_text FROM clex_definitions WHERE device_id = ?", 
                    (device_id,)
                )
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    folder_path, file_name, definition_text = result
                    
                    # Create result data
                    clex_data = {
                        "found": True,
                        "folder_path": folder_path,
                        "file_name": file_name,
                        "definition_text": definition_text,
                        "header": f"Device: {device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n",
                        "full_text": f"Device: {device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n{definition_text}"
                    }
                    
                    # Call the original handler
                    self.on_clex_definition_loaded(clex_data)
                    print(f"Successfully loaded CLEX definition for {device_name}")
                    
                else:
                    # No definition found
                    clex_data = {
                        "found": False,
                        "message": f"No CLEX definition found for '{device_name}'"
                    }
                    
                    # Call the original handler
                    self.on_clex_definition_loaded(clex_data)
                    print(f"No CLEX definition found for {device_name}")
                    
            except Exception as e:
                print(f"Error loading CLEX definition: {str(e)}")
                
                # Hide loading indicators
                if hasattr(self, 'loading_overlay'):
                    self.loading_overlay.hide_loading()
                    
                if hasattr(self, 'status_indicator'):
                    self.status_indicator.reset()
                    
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage(f"Error loading CLEX definition: {str(e)}")
                    
        else:
            self.clear_clex_display()
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Device '{device_name}' has no CLEX definition")
                
        self.update_button_states()
        if hasattr(self, 'settings'):
            self.settings.setValue("last_device_id", device_id)
    
    def eventFilter(self, obj, event):
        """Global event filter to detect and fix UI freezes."""
        # Detect paint events to ensure the UI is updating
        if event.type() == QEvent.Paint and hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            # Safety check: if loading overlay is visible during paint, restart the safety timer
            if not self.safety_timer.isActive():
                self.safety_timer.start(5000)
        
        return super().eventFilter(obj, event)
    
    # Override problematic methods to prevent them from being called
    def load_devices(self, tech_id):
        """Prevent original method from being called."""
        print("load_devices bypassed - handled by on_tech_select")
        pass
    
    def load_clex_definition(self, device_id, device_name):
        """Prevent original method from being called."""
        print("load_clex_definition bypassed - handled by on_device_select")
        pass

def main():
    # Set up application
    app = QApplication(sys.argv)
    
    print("Creating hybrid browser instance...")
    browser = SafeEnhancedCLEXBrowser("clex_database.db")
    
    print("Showing browser...")
    browser.show()
    
    print("Entering application event loop...")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()