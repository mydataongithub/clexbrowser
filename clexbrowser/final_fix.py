import sys
import sqlite3
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt

# Monkey patch the problematic methods in the original EnhancedCLEXBrowser
from clex_browser import EnhancedCLEXBrowser

# First, let's patch the LoadingOverlay class to fix the slow hide animation issue
from ui_components.loading_indicator import LoadingOverlay

# Save original hide_loading method
original_hide_loading = LoadingOverlay.hide_loading

# Create a new hide_loading method with no animation
def quick_hide_loading(self):
    """Hide the loading overlay immediately without animation."""
    print("Quick hiding loading overlay")
    self.hide()  # Hide immediately without animation

# Replace the method
LoadingOverlay.hide_loading = quick_hide_loading

# Fix for technology loading
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
        # Always hide loading indicators - forcefully
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.hide()  # Use direct hide instead of hide_loading
        
        if hasattr(self, 'status_indicator'):
            self.status_indicator.reset()
            # Explicitly stop indeterminate mode and set progress to 0
            self.status_indicator.stop_indeterminate()
            self.status_indicator.set_progress(0)

# Fix for device selection
def fixed_on_device_select(self, current, previous):
    """Fixed version that uses direct database access for CLEX loading."""
    if not current:
        return
    
    device_id = current.data(Qt.UserRole)
    self.current_device_id = device_id
    self.current_device_name = current.text()
    has_clex = current.font().bold()
    
    print(f"Device selected: {self.current_device_name} (ID: {device_id}, has_clex: {has_clex})")
    
    if has_clex:
        # Use direct access instead of worker thread
        self.fixed_load_clex_definition(device_id, self.current_device_name)
    else:
        self.clear_clex_display()
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Device '{self.current_device_name}' has no CLEX definition")
    
    self.update_button_states()
    if hasattr(self, 'settings'):
        self.settings.setValue("last_device_id", device_id)

# Fix for CLEX definition loading
def fixed_load_clex_definition(self, device_id, device_name):
    """Fixed version that uses direct database access."""
    print(f"Loading CLEX definition directly for {device_name}")
    
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
            
            # Process result directly
            header_text = f"Device: {device_name}\nFolder: {folder_path}\nFile: {file_name}\n\n"
            full_text = header_text + definition_text
            
            # Update UI directly
            self.clex_text.clear()
            self.clex_text.setPlainText(full_text)
            self.setWindowTitle(f"Enhanced CLEX Browser - {device_name}")
            
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Loaded CLEX definition for '{device_name}'")
            
            print(f"Successfully loaded CLEX definition for {device_name}")
        else:
            self.clear_clex_display()
            
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"No CLEX definition found for '{device_name}'")
            
            print(f"No CLEX definition found for {device_name}")
    
    except Exception as e:
        print(f"Error loading CLEX definition: {str(e)}")
        self.clear_clex_display()
        
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Error loading CLEX definition: {str(e)}")
    
    finally:
        # Always forcefully hide loading indicators
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.hide()  # Direct hide instead of hide_loading
        
        if hasattr(self, 'status_indicator'):
            print("Explicitly resetting status indicator")
            self.status_indicator.reset()
            # Explicitly stop indeterminate mode and reset
            self.status_indicator.stop_indeterminate()
            self.status_indicator.set_progress(0)

# Fix for technology selection
def fixed_on_tech_select(self, current, previous):
    """Fixed version that uses direct database access."""
    if not current:
        return
    
    tech_id = current.data(Qt.UserRole)
    self.current_tech_id = tech_id
    tech_name = current.text().split(" v")[0]
    
    print(f"Technology selected: {tech_name} (ID: {tech_id})")
    
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
        
        # Update state
        self.devices = devices
        self.all_devices = self.devices.copy()
        
        # Update statistics
        self.update_statistics(
            len(self.devices),
            clex_count,
            total_clex
        )
        
        # Update device list
        self.update_device_listbox()
        
        # Clear CLEX display
        self.clear_clex_display()
        
        # Update status
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Loaded {len(devices)} devices ({clex_count} with CLEX definitions)")
        
        print(f"Successfully loaded {len(devices)} devices ({clex_count} with CLEX)")
    
    except Exception as e:
        print(f"Error loading devices: {str(e)}")
        
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Error loading devices: {str(e)}")
    
    finally:
        # Always forcefully hide loading indicators
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.hide()  # Direct hide instead of hide_loading
        
        if hasattr(self, 'status_indicator'):
            self.status_indicator.reset()
            # Explicitly stop indeterminate mode
            self.status_indicator.stop_indeterminate()
            self.status_indicator.set_progress(0)
    
    # Update settings
    if hasattr(self, 'settings'):
        self.settings.setValue("last_tech_id", tech_id)

# Fix for StatusIndicator class to ensure it properly resets
from ui_components.loading_indicator import StatusIndicator

# Save original reset method
original_reset = StatusIndicator.reset

# Create enhanced reset method
def enhanced_reset(self):
    """Enhanced reset method to ensure complete reset."""
    print("Enhanced status indicator reset")
    # Call original reset
    original_reset(self)
    # Explicitly set range and value
    self.progress_bar.setRange(0, 100)
    self.progress_bar.setValue(0)
    self.status_label.setText("Ready")

# Replace reset method
StatusIndicator.reset = enhanced_reset

# Add new method to update progress bar
EnhancedCLEXBrowser.fixed_load_clex_definition = fixed_load_clex_definition

# Replace the original methods
EnhancedCLEXBrowser.load_technologies = fixed_load_technologies
EnhancedCLEXBrowser.on_device_select = fixed_on_device_select
EnhancedCLEXBrowser.on_tech_select = fixed_on_tech_select

def main():
    # Set up application
    app = QApplication(sys.argv)
    
    # Add safety mechanism
    def emergency_check():
        #print("Emergency check...")
        for window in app.topLevelWidgets():
            if hasattr(window, 'loading_overlay') and window.loading_overlay.isVisible():
                print("Hiding stuck loading overlay")
                window.loading_overlay.hide()
                
            if hasattr(window, 'status_indicator'):
                window.status_indicator.reset()
                if hasattr(window.status_indicator, 'progress_bar'):
                    window.status_indicator.progress_bar.setRange(0, 100)
                    window.status_indicator.progress_bar.setValue(0)
    
    emergency_timer = QTimer()
    emergency_timer.timeout.connect(emergency_check)
    emergency_timer.start(2000)  # Check every 2 seconds
    
    print("Creating browser with final fixed methods...")
    browser = EnhancedCLEXBrowser("clex_database.db")
    
    print("Showing browser...")
    browser.show()
    
    print("Entering application event loop...")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()