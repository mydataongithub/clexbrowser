import re
import sqlite3
import os

def parse_log_file(log_content):
    """Parse the log file to extract technologies, devices, and CLEX definitions."""
    technologies = []
    devices = {}  # {tech_name: [device1, device2, ...]}
    clex_definitions = []  # [(device_name, tech_name, folder_path, file_name, definition_text)]
    
    current_tech = None
    current_tech_version = None
    current_tech_path = None
    
    # Capture groups of device definitions
    device_blocks = {}  # {(device_name, tech_name): [lines]}
    current_device = None
    current_device_tech = None
    in_device_block = False
    current_block = []
    current_folder_path = None
    current_file_name = None
    
    lines = log_content.split('\n')
    line_index = 0
    
    while line_index < len(lines):
        line = lines[line_index]
        line_index += 1
        
        # Technology detection
        tech_match = re.search(r'The latest directory is: (.*?)/models', line)
        if tech_match:
            current_tech_path = tech_match.group(1)
        
        tech_name_match = re.search(r'Technology: (\w+)', line)
        if tech_name_match:
            current_tech = tech_name_match.group(1)
            # Extract version from path
            version_match = re.search(r'/v([\d\.]+)', current_tech_path) if current_tech_path else None
            current_tech_version = version_match.group(1) if version_match else None
            technologies.append((current_tech, current_tech_version, current_tech_path))
            devices[current_tech] = []
        
        # Device list detection
        devices_match = re.search(r'List of all devices: (.*)', line)
        if devices_match and current_tech:
            device_list_text = devices_match.group(1)
            device_list = device_list_text.split(', ')
            for device in device_list:
                device = device.strip()
                if device and device not in devices[current_tech]:
                    devices[current_tech].append(device)
        
        # Start of a device definition block
        inline_match = re.search(r'inline subckt (\w+)', line)
        if inline_match:
            # End previous block if any
            if in_device_block and current_device and current_device_tech:
                device_blocks[(current_device, current_device_tech)] = current_block
            
            current_device = inline_match.group(1)
            current_device_tech = current_tech
            in_device_block = True
            current_block = [line]
            current_folder_path = None
            current_file_name = None
        elif line.startswith('Folder Path:') and in_device_block:
            current_folder_path = line.replace('Folder Path:', '').strip()
            current_block.append(line)
        elif line.startswith('File Name:') and in_device_block:
            current_file_name = line.replace('File Name:', '').strip()
            current_block.append(line)
        elif in_device_block:
            current_block.append(line)
            
            # Check if this is the end of a block (empty line or next device definition)
            if (line.strip() == "" or 
                line_index < len(lines) and re.search(r'inline subckt (\w+)', lines[line_index])):
                device_blocks[(current_device, current_device_tech)] = current_block
                
                # Process the block to see if it contains CLEX definitions
                if current_device and current_device_tech and current_folder_path and current_file_name:
                    # Clean up the block - only keep relevant lines
                    cleaned_block = []
                    inside_def = False
                    
                    for block_line in current_block:
                        # Start capturing at the inline subckt line
                        if block_line.strip().startswith("inline subckt"):
                            inside_def = True
                            cleaned_block.append(block_line)
                        # Add folder and file info
                        elif block_line.strip().startswith("Folder Path:") or block_line.strip().startswith("File Name:"):
                            cleaned_block.append(block_line)
                        # Add CLEX assert lines
                        elif inside_def and ("assert" in block_line or "clex" in block_line.lower()):
                            cleaned_block.append(block_line)
                        # Stop at lines indicating a new section
                        elif block_line.strip().startswith("Searching in") or block_line.strip().startswith("Technology:"):
                            inside_def = False
                            break
                    
                    block_text = '\n'.join(cleaned_block)
                    
                    # Look for assert statements that indicate CLEX definitions
                    # This more broadly searches for assertion patterns
                    if (re.search(r'clex\w*\s+assert', block_text, re.IGNORECASE) or
                        re.search(r'assert\s+.*expr', block_text, re.IGNORECASE)):
                        clex_definitions.append((current_device, 
                                               current_device_tech, 
                                               current_folder_path, 
                                               current_file_name, 
                                               block_text))
                        
                        # Make sure the device is in our list
                        if current_device not in devices.get(current_device_tech, []):
                            if current_device_tech in devices:
                                devices[current_device_tech].append(current_device)
                
                in_device_block = False
                current_block = []
    
    # Check for any final block
    if in_device_block and current_device and current_device_tech:
        device_blocks[(current_device, current_device_tech)] = current_block
        
        if current_folder_path and current_file_name:
            # Clean up the block - only keep relevant lines
            cleaned_block = []
            inside_def = False
                
            for block_line in current_block:
                # Start capturing at the inline subckt line
                if block_line.strip().startswith("inline subckt"):
                    inside_def = True
                    cleaned_block.append(block_line)
                # Add folder and file info
                elif block_line.strip().startswith("Folder Path:") or block_line.strip().startswith("File Name:"):
                    cleaned_block.append(block_line)
                # Add CLEX assert lines
                elif inside_def and ("assert" in block_line or "clex" in block_line.lower()):
                    cleaned_block.append(block_line)
                # Stop at lines indicating a new section
                elif block_line.strip().startswith("Searching in") or block_line.strip().startswith("Technology:"):
                    inside_def = False
                    break
                
            block_text = '\n'.join(cleaned_block)
            
            if (re.search(r'clex\w*\s+assert', block_text, re.IGNORECASE) or
                re.search(r'assert\s+.*expr', block_text, re.IGNORECASE)):
                clex_definitions.append((current_device, 
                                       current_device_tech, 
                                       current_folder_path, 
                                       current_file_name, 
                                       block_text))
    
    # Print some stats
    print(f"Found {len(technologies)} technologies")
    print(f"Found {len(clex_definitions)} CLEX definitions")
    
    # Count number of devices with CLEX for each technology
    clex_counts = {}
    for device, tech, _, _, _ in clex_definitions:
        if tech not in clex_counts:
            clex_counts[tech] = set()
        clex_counts[tech].add(device)
    
    for tech_name, tech_version, _ in technologies:
        tech_devices = len(devices.get(tech_name, []))
        tech_clex = len(clex_counts.get(tech_name, set()))
        print(f"Technology {tech_name}: {tech_devices} devices, {tech_clex} with CLEX")
    
    return technologies, devices, clex_definitions

def create_database(db_name, technologies, devices_dict, clex_definitions):
    """Create SQLite database with the parsed data."""
    # Remove existing database if it exists
    if os.path.exists(db_name):
        os.remove(db_name)
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE technologies (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        version TEXT,
        path TEXT
    )''')
    
    cursor.execute('''
    CREATE TABLE devices (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        technology_id INTEGER,
        has_clex_definition BOOLEAN DEFAULT 0,
        FOREIGN KEY (technology_id) REFERENCES technologies(id)
    )''')
    
    cursor.execute('''
    CREATE TABLE clex_definitions (
        id INTEGER PRIMARY KEY,
        device_id INTEGER,
        folder_path TEXT,
        file_name TEXT,
        definition_text TEXT,
        FOREIGN KEY (device_id) REFERENCES devices(id)
    )''')
    
    # Insert technologies
    for tech_name, tech_version, tech_path in technologies:
        cursor.execute("INSERT INTO technologies (name, version, path) VALUES (?, ?, ?)",
                       (tech_name, tech_version, tech_path))
    
    # Get technology IDs for later use
    tech_id_map = {}
    for tech_name, _, _ in technologies:
        cursor.execute("SELECT id FROM technologies WHERE name = ?", (tech_name,))
        tech_id = cursor.fetchone()[0]
        tech_id_map[tech_name] = tech_id
    
    # Create a set of devices with CLEX definitions for each technology
    devices_with_clex = {}
    for device, tech, _, _, _ in clex_definitions:
        if tech not in devices_with_clex:
            devices_with_clex[tech] = set()
        devices_with_clex[tech].add(device)
    
    # Insert devices 
    device_id_map = {}  # To store (device_name, tech_id) -> device_id mapping
    
    for tech_name, devices_list in devices_dict.items():
        tech_id = tech_id_map.get(tech_name)
        if not tech_id:
            continue
            
        # Debug print
        clex_count = len(devices_with_clex.get(tech_name, set()))
        print(f"Technology {tech_name} (ID: {tech_id}): {len(devices_list)} devices, {clex_count} with CLEX")
        
        for device_name in devices_list:
            has_clex = 1 if device_name in devices_with_clex.get(tech_name, set()) else 0
            
            cursor.execute("INSERT INTO devices (name, technology_id, has_clex_definition) VALUES (?, ?, ?)",
                         (device_name, tech_id, has_clex))
            
            cursor.execute("SELECT last_insert_rowid()")
            device_id = cursor.fetchone()[0]
            device_id_map[(device_name, tech_id)] = device_id
    
    # Insert CLEX definitions
    for device_name, tech_name, folder_path, file_name, definition_text in clex_definitions:
        tech_id = tech_id_map.get(tech_name)
        if not tech_id:
            continue
            
        device_id = device_id_map.get((device_name, tech_id))
        if not device_id:
            # This is a fallback in case a device was found in CLEX but not in device list
            print(f"Warning: Device {device_name} in technology {tech_name} has CLEX but wasn't in device list")
            continue
            
        cursor.execute("""
            INSERT INTO clex_definitions (device_id, folder_path, file_name, definition_text)
            VALUES (?, ?, ?, ?)
        """, (device_id, folder_path, file_name, definition_text))
    
    # Verify CLEX associations
    cursor.execute("SELECT COUNT(*) FROM devices WHERE has_clex_definition = 1")
    device_clex_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM clex_definitions")
    def_count = cursor.fetchone()[0]
    
    print(f"Database summary:")
    print(f"- Total devices with CLEX flag: {device_clex_count}")
    print(f"- Total CLEX definitions: {def_count}")
    
    conn.commit()
    conn.close()

def process_log_file(log_file_path, db_name="clex_database.db"):
    """Process the log file and create a SQLite database."""
    try:
        with open(log_file_path, 'r') as file:
            log_content = file.read()
        
        technologies, devices, clex_definitions = parse_log_file(log_content)
        create_database(db_name, technologies, devices, clex_definitions)
        
        return db_name
    except Exception as e:
        print(f"Error processing log file: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    log_file_path = "output.log"  # Update with actual path
    db_file = process_log_file(log_file_path)
    print(f"Database file created: {db_file}")