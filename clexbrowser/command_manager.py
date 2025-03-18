from typing import List, Dict, Any, Callable, Optional
from abc import ABC, abstractmethod

class Command(ABC):
    """
    Abstract base class for all commands in the undo/redo system.
    
    The Command pattern encapsulates an operation as an object, making it possible
    to parameterize clients with different operations, queue operations, and
    support undoable operations.
    """
    
    def __init__(self, description: str):
        """
        Initialize the command.
        
        Args:
            description: Human-readable description of the command
        """
        self.description = description
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.
        
        Returns:
            True if the command executed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command.
        
        Returns:
            True if the command was undone successfully, False otherwise
        """
        pass
    
    def get_description(self) -> str:
        """
        Get the description of the command.
        
        Returns:
            Human-readable description of the command
        """
        return self.description


class EditClexDefinitionCommand(Command):
    """Command for editing a CLEX definition."""
    
    def __init__(self, device_id: int, old_data: Dict[str, str], new_data: Dict[str, str],
                execute_func: Callable[[int, str, str, str], bool],
                description: str = "Edit CLEX Definition"):
        """
        Initialize the edit command.
        
        Args:
            device_id: ID of the device being edited
            old_data: Original CLEX definition data (folder_path, file_name, definition_text)
            new_data: New CLEX definition data (folder_path, file_name, definition_text)
            execute_func: Function to call to execute the edit
            description: Human-readable description of the command
        """
        super().__init__(description)
        self.device_id = device_id
        self.old_data = old_data
        self.new_data = new_data
        self.execute_func = execute_func
    
    def execute(self) -> bool:
        """
        Execute the edit operation.
        
        Returns:
            True if the edit was successful, False otherwise
        """
        return self.execute_func(
            self.device_id,
            self.new_data['folder_path'],
            self.new_data['file_name'],
            self.new_data['definition_text']
        )
    
    def undo(self) -> bool:
        """
        Undo the edit operation by restoring the previous data.
        
        Returns:
            True if the undo was successful, False otherwise
        """
        return self.execute_func(
            self.device_id,
            self.old_data['folder_path'],
            self.old_data['file_name'],
            self.old_data['definition_text']
        )


class AddClexDefinitionCommand(Command):
    """Command for adding a new CLEX definition."""
    
    def __init__(self, device_id: int, data: Dict[str, str],
                add_func: Callable[[int, str, str, str], bool],
                delete_func: Callable[[int], bool],
                description: str = "Add CLEX Definition"):
        """
        Initialize the add command.
        
        Args:
            device_id: ID of the device
            data: CLEX definition data (folder_path, file_name, definition_text)
            add_func: Function to call to add the definition
            delete_func: Function to call to delete the definition (for undo)
            description: Human-readable description of the command
        """
        super().__init__(description)
        self.device_id = device_id
        self.data = data
        self.add_func = add_func
        self.delete_func = delete_func
    
    def execute(self) -> bool:
        """
        Execute the add operation.
        
        Returns:
            True if the add was successful, False otherwise
        """
        return self.add_func(
            self.device_id,
            self.data['folder_path'],
            self.data['file_name'],
            self.data['definition_text']
        )
    
    def undo(self) -> bool:
        """
        Undo the add operation by deleting the definition.
        
        Returns:
            True if the undo was successful, False otherwise
        """
        return self.delete_func(self.device_id)


class DeleteClexDefinitionCommand(Command):
    """Command for deleting a CLEX definition."""
    
    def __init__(self, device_id: int, data: Dict[str, str],
                delete_func: Callable[[int], bool],
                add_func: Callable[[int, str, str, str], bool],
                description: str = "Delete CLEX Definition"):
        """
        Initialize the delete command.
        
        Args:
            device_id: ID of the device
            data: CLEX definition data to restore if undone
            delete_func: Function to call to delete the definition
            add_func: Function to call to restore the definition (for undo)
            description: Human-readable description of the command
        """
        super().__init__(description)
        self.device_id = device_id
        self.data = data
        self.delete_func = delete_func
        self.add_func = add_func
    
    def execute(self) -> bool:
        """
        Execute the delete operation.
        
        Returns:
            True if the delete was successful, False otherwise
        """
        return self.delete_func(self.device_id)
    
    def undo(self) -> bool:
        """
        Undo the delete operation by restoring the definition.
        
        Returns:
            True if the undo was successful, False otherwise
        """
        return self.add_func(
            self.device_id,
            self.data['folder_path'],
            self.data['file_name'],
            self.data['definition_text']
        )


class CommandManager:
    """
    Manages the execution, undoing, and redoing of commands.
    
    This class maintains the history of executed commands and provides
    methods to undo and redo them, as well as to query the current state
    of the command history.
    """
    
    def __init__(self, max_history: int = 50):
        """
        Initialize the command manager.
        
        Args:
            max_history: Maximum number of commands to keep in history
        """
        self.history: List[Command] = []
        self.current_index: int = -1
        self.max_history: int = max_history
    
    def execute_command(self, command: Command) -> bool:
        """
        Execute a command and add it to the history.
        
        Args:
            command: The command to execute
            
        Returns:
            True if the command executed successfully, False otherwise
        """
        # Clear any redoable commands
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
        
        # Execute the command
        if command.execute():
            # Add to history
            self.history.append(command)
            self.current_index = len(self.history) - 1
            
            # Limit history size
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
                self.current_index = len(self.history) - 1
            
            return True
        
        return False
    
    def can_undo(self) -> bool:
        """
        Check if there are commands that can be undone.
        
        Returns:
            True if there are commands that can be undone, False otherwise
        """
        return self.current_index >= 0
    
    def can_redo(self) -> bool:
        """
        Check if there are commands that can be redone.
        
        Returns:
            True if there are commands that can be redone, False otherwise
        """
        return self.current_index < len(self.history) - 1
    
    def undo(self) -> Optional[str]:
        """
        Undo the most recent command.
        
        Returns:
            Description of the undone command if successful, None otherwise
        """
        if not self.can_undo():
            return None
        
        command = self.history[self.current_index]
        if command.undo():
            self.current_index -= 1
            return command.get_description()
        
        return None
    
    def redo(self) -> Optional[str]:
        """
        Redo the most recently undone command.
        
        Returns:
            Description of the redone command if successful, None otherwise
        """
        if not self.can_redo():
            return None
        
        self.current_index += 1
        command = self.history[self.current_index]
        if command.execute():
            return command.get_description()
        
        # If execution fails, revert the index change
        self.current_index -= 1
        return None
    
    def get_undo_description(self) -> Optional[str]:
        """
        Get the description of the command that would be undone.
        
        Returns:
            Description of the command that would be undone, or None if no commands can be undone
        """
        if not self.can_undo():
            return None
        
        return f"Undo: {self.history[self.current_index].get_description()}"
    
    def get_redo_description(self) -> Optional[str]:
        """
        Get the description of the command that would be redone.
        
        Returns:
            Description of the command that would be redone, or None if no commands can be redone
        """
        if not self.can_redo():
            return None
        
        return f"Redo: {self.history[self.current_index + 1].get_description()}"
    
    def clear_history(self):
        """Clear the command history."""
        self.history = []
        self.current_index = -1