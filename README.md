# CLEX Browser Project Overview

## Introduction

The CLEX Browser is a specialized software application designed for browsing, managing, and analyzing CLEX (Circuit-Level Expression) definitions in semiconductor technologies. This desktop application provides semiconductor engineers with a comprehensive toolset for working with CLEX definitions, which are assertions or constraints used in semiconductor device modeling to verify that circuit designs meet specific electrical parameter requirements.

## Core Features

### User Interface Components

- **Technology Browser**: Hierarchical navigation structure that organizes CLEX definitions by technology and device
- **Device Navigator**: Lists devices within a selected technology with visual indicators for those containing CLEX definitions
- **CLEX Definition Viewer**: Displays CLEX definitions with syntax highlighting for improved readability
- **Search Functionality**: Global search across technologies and devices with context-aware results display
- **Status Indicators**: Progress bars and loading overlays to provide visual feedback during operations

### Core Functionality

- **CLEX Management**:
  - View CLEX definitions with syntax highlighting
  - Add new CLEX definitions
  - Edit existing CLEX definitions
  - Delete CLEX definitions
  - Compare CLEX definitions between devices

- **Data Analysis**:
  - Statistics showing coverage of CLEX definitions across technologies
  - Analysis of voltage and current limits from CLEX definitions
  - Filtering capabilities to focus on specific subsets of devices or definitions

- **Export and Sharing**:
  - Export CLEX definitions to text, HTML, or CSV formats
  - Bulk operations for managing multiple definitions simultaneously
  - Copy CLEX definitions to clipboard

- **User Experience Enhancements**:
  - Dark mode support for reduced eye strain
  - Enhanced tooltips for improved usability
  - Undo/redo functionality for definition changes
  - Form validation with real-time feedback
  - Keyboard shortcuts for efficient navigation

## Technical Architecture

### Framework and Libraries
- **UI Framework**: PyQt5 for cross-platform graphical user interface
- **Database**: SQLite for local storage of technologies, devices, and CLEX definitions
- **Threading**: Custom thread management system for responsive UI during database operations

### Key Components

- **Database Management**:
  - `DatabaseManager`: Central class for database operations
  - `database_creator.py`: Utilities for parsing log files and initializing the database

- **UI Components**:
  - `EnhancedCLEXBrowser`: Main application window containing the browser interface
  - `SyntaxHighlighter`: Provides syntax highlighting for CLEX definitions
  - Form validation components for input validation
  - Loading indicators and progress reporting

- **Worker System**:
  - `ThreadManager`: Coordinates background threads for database operations
  - Worker classes for specific operations (loading technologies, devices, definitions)

- **Command Pattern Implementation**:
  - `CommandManager`: Implements undo/redo functionality
  - Command classes for specific operations (add, edit, delete)

- **Dialogs and UI Components**:
  - Dialog classes for specific operations (export, search, comparison)
  - Enhanced tooltips and form validation

## Workflow and Use Cases

1. **Browsing CLEX Definitions**:
   - Select a technology from the left panel
   - Browse devices within the technology in the right panel
   - View CLEX definitions for selected devices in the bottom panel

2. **Managing CLEX Definitions**:
   - Add new CLEX definitions using the floating action button or toolbar
   - Edit or delete CLEX definitions using the corresponding buttons
   - Undo/redo changes as needed

3. **Searching and Filtering**:
   - Use search boxes to filter technologies and devices
   - Use the global search feature to find specific text across all definitions
   - Apply filters like "Only with CLEX" to focus on specific subsets

4. **Analysis and Export**:
   - Use the statistics dialog to analyze CLEX coverage
   - Compare definitions between devices
   - Export definitions to various formats for sharing or documentation

## Design Considerations

- **Performance**: Threading model for responsive UI during database operations
- **Error Handling**: Comprehensive error handling with user-friendly error messages
- **Extensibility**: Command pattern for operations, allowing for easy addition of new features
- **Cross-Platform**: PyQt5 ensures compatibility across operating systems
- **User Experience**: Dark mode, tooltips, and visual indicators for improved usability

## Conclusion

The CLEX Browser provides semiconductor engineers with a powerful and intuitive tool for managing CLEX definitions, helping ensure circuit designs meet electrical parameter requirements. With its comprehensive feature set and responsive interface, it streamlines the workflow for analyzing and maintaining these critical assertions in semiconductor device modeling.
