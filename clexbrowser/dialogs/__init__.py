# dialogs/__init__.py
"""
Dialog components for the CLEX Database Manager.

This package contains all dialog classes used throughout the application,
providing consistent interfaces for user interaction.
"""

from .progress_dialog import ProgressDialog
from .compare_dialog import CompareDialog
from .export_dialog import ExportDialog
from .global_search_dialog import GlobalSearchDialog
from .stats_dialog import StatsDialog
from .new_clex_dialog import NewCLEXDialog
from .edit_clex_dialog import EditCLEXDialog
from .confirmation_dialog import ConfirmationDialog
from .bulk_operations_dialog import BulkOperationsDialog