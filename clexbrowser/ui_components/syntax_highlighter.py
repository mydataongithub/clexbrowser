from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
import re
from typing import Optional

class SyntaxHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for CLEX definitions.
    
    This class provides syntax highlighting for CLEX definition text,
    making different elements like keywords, assertions, and messages
    visually distinct with different colors and styles.
    """
    
    def __init__(self, parent=None, dark_mode=False):
        """
        Initialize the syntax highlighter.
        
        Args:
            parent: Parent document (typically a QTextDocument)
            dark_mode: Whether to use dark mode colors
        """
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.create_formats()
        
    def create_formats(self):
        """Create text formats for different syntax elements."""
        # Keyword format (for CLEX keywords like 'inline', 'subckt', etc.)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setFontWeight(QFont.Bold)
        self.keyword_format.setForeground(
            QColor("#0066CC") if not self.dark_mode else QColor("#56AAFF")
        )
        
        # Assertion format (for assertions like 'clexvw', 'clexcw', etc.)
        self.assertion_format = QTextCharFormat()
        self.assertion_format.setFontWeight(QFont.Bold)
        self.assertion_format.setForeground(
            QColor("#CC0000") if not self.dark_mode else QColor("#FF5555")
        )
        
        # Device format (for device headers)
        self.device_format = QTextCharFormat()
        self.device_format.setFontWeight(QFont.Bold)
        
        # File format (for file and folder paths)
        self.file_format = QTextCharFormat()
        self.file_format.setForeground(
            QColor("#0066CC") if not self.dark_mode else QColor("#56AAFF")
        )
        
        # Terminals format (for terminal connections)
        self.terminals_format = QTextCharFormat()
        self.terminals_format.setForeground(
            QColor("#008800") if not self.dark_mode else QColor("#55FF55")
        )
        
        # Message format (for message strings)
        self.message_format = QTextCharFormat()
        self.message_format.setForeground(
            QColor("#8800AA") if not self.dark_mode else QColor("#CC55FF")
        )
        
        # Comment format (for comment lines)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(
            QColor("#808080") if not self.dark_mode else QColor("#AAAAAA")
        )
        self.comment_format.setFontItalic(True)
    
    def set_dark_mode(self, dark_mode: bool):
        """
        Update highlighter colors for dark/light mode.
        
        Args:
            dark_mode: Whether to use dark mode colors
        """
        self.dark_mode = dark_mode
        self.create_formats()
        self.rehighlight()
    
    def highlightBlock(self, text: str):
        """
        Apply highlighting to a block of text.
        
        Args:
            text: The text block to highlight
        """
        # Handle special case: Device header
        if text.startswith("Device:"):
            self.setFormat(0, len(text), self.device_format)
            return
        
        # Handle special case: File/Folder header
        if text.startswith("Folder:") or text.startswith("File:"):
            self.setFormat(0, len(text), self.file_format)
            return
        
        # Handle inline subckt with terminals
        inline_match = re.match(r'(inline\s+subckt\s+\w+\s*)(\([^)]*\))(.*)', text)
        if inline_match:
            self.setFormat(0, len(inline_match.group(1)), self.keyword_format)
            start_terminals = len(inline_match.group(1))
            terminals_length = len(inline_match.group(2))
            self.setFormat(start_terminals, terminals_length, self.terminals_format)
            return
        
        # Highlight keywords
        keywords = ["inline", "subckt", "assert", "expr", "min", "max", "level", 
                   "duration", "sub", "anal_types"]
        for keyword in keywords:
            pattern = r'\b' + keyword + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)
        
        # Highlight assertions
        assertions = ["clexvw", "clexcw", "clex_"]
        for assertion in assertions:
            pattern = r'\b' + assertion + r'\w*'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.assertion_format)
        
        # Highlight message strings
        message_match = re.search(r'message="([^"]*)"', text)
        if message_match:
            start_pos = message_match.start(1)
            length = len(message_match.group(1))
            self.setFormat(start_pos, length, self.message_format)
        
        # Highlight comments
        if text.strip().startswith('//'):
            self.setFormat(0, len(text), self.comment_format)