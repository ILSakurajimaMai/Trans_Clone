"""
Main window for the CSV Translator application
"""

import sys
import threading
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
import os

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QTableView,
    QTextEdit,
    QGroupBox,
    QSplitter,
    QMenuBar,
    QMenu,
    QAbstractItemView,
    QHeaderView,
    QMessageBox,
    QDialog,
    QPushButton,
    QFrame,
    QTabWidget,
)
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QTimer

from config.settings import AppSettings
from core.preferences import prefs
from core.project_manager import ProjectManager
from core.autosave_manager import AutoSaveManager
from models.table_model import EnhancedPandasModel
from models.data_structures import (
    AppState,
    ModelProvider,
    TranslationRequest,
    TranslationChunk,
    UndoRedoState,
    UndoRedoAction,
)
from core.file_manager import OptimizedFileManager as FileManager
from core.translation_engine import TranslationEngine
from core.history_manager import HistoryManager
from ui.components.config_panel import ConfigPanel
from ui.components.action_panel import ExtendedActionPanel
from ui.dialogs import APIKeyDialog, FindReplaceDialog
from utils.file_utils import ConfigManager


class CSVTranslatorMainWindow(QMainWindow):
    """Main window for the CSV Translator application"""

    def __init__(self):
        super().__init__()

        # Initialize managers and state
        self.app_state = AppState()
        self.file_manager = FileManager()
        self.translation_engine = TranslationEngine()
        self.history_manager = HistoryManager()

        # New storage managers
        self.project_manager = ProjectManager()
        self.autosave_manager = AutoSaveManager(
            interval_seconds=prefs.get("auto_save_interval", 30)
        )

        # UI components
        self.table_model = None
        self.find_dialog = None
        self.settings_visible = True

        # Setup
        self.setup_window()
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_api_keys()

        # Setup storage systems
        self.setup_storage_managers()

        # Apply theme from preferences
        theme = prefs.get("theme", AppSettings.DEFAULT_THEME)
        self.apply_theme(theme)

        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second

        # Check for recovery on startup
        self.check_recovery_on_startup()

        # Load last project if available
        self.load_last_project()

    def setup_window(self):
        """Setup main window properties"""
        self.setWindowTitle("CSV Translator with AI")

        # Restore window geometry from preferences
        x, y, width, height, maximized = prefs.get_window_geometry()
        self.setGeometry(x, y, width, height)

        if maximized:
            self.showMaximized()

        # Set minimum size
        self.setMinimumSize(800, 600)

    def setup_ui(self):
        """Setup the user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create tab widget for main interface
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Tab 1: Main workspace
        self.main_tab = QWidget()
        self.setup_main_tab()
        self.tab_widget.addTab(self.main_tab, "📄 Main Workspace")

        # Tab 2: API Configuration (lazy import to avoid QWidget before QApplication)
        try:
            from ui.components.api_config_panel import APIConfigPanel

            self.api_config_panel = APIConfigPanel()
            self.api_config_panel.api_key_changed.connect(self.on_api_key_configured)
            self.tab_widget.addTab(self.api_config_panel, "🔑 API Configuration")
        except Exception as e:
            # Create placeholder with error message
            placeholder = QWidget()
            placeholder_layout = QVBoxLayout(placeholder)
            from PyQt6.QtWidgets import QLabel

            error_label = QLabel(
                f"<h3>⚠️ Error loading API Configuration</h3>"
                f"<p><b>Error:</b> {str(e)}</p>"
                f"<p>Please install missing dependencies:</p>"
                f"<code>pip install cryptography requests</code>"
            )
            error_label.setWordWrap(True)
            placeholder_layout.addWidget(error_label)
            placeholder_layout.addStretch()
            self.tab_widget.addTab(placeholder, "🔑 API Configuration")
            self.api_config_panel = None
            print(f"Warning: Could not load API Configuration panel: {e}")

        # Tab 3: System Instructions
        try:
            from ui.components.instruction_panel import InstructionPanel

            self.instruction_panel = InstructionPanel()
            self.instruction_panel.instruction_changed.connect(
                self.on_instruction_changed
            )
            self.tab_widget.addTab(self.instruction_panel, "📝 Instructions")
        except Exception as e:
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "📝 Instructions")
            self.instruction_panel = None
            print(f"Warning: Could not load Instructions panel: {e}")

        # Tab 4: Summary
        try:
            from ui.components.summary_panel import SummaryPanel

            self.summary_panel = SummaryPanel()
            self.summary_panel.summary_requested.connect(self.on_summary_requested)
            self.tab_widget.addTab(self.summary_panel, "📊 Summary")
        except Exception as e:
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "📊 Summary")
            self.summary_panel = None
            print(f"Warning: Could not load Summary panel: {e}")

        # Setup menu bar after all components are created
        self.setup_menu_bar()

    def setup_main_tab(self):
        """Setup main workspace tab"""
        main_layout = QVBoxLayout(self.main_tab)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Settings panel with toggle button
        settings_header = QHBoxLayout()

        # Toggle button for settings
        self.toggle_settings_btn = QPushButton("🔧 Hide Settings")
        self.toggle_settings_btn.setMaximumWidth(120)
        self.toggle_settings_btn.clicked.connect(self.toggle_settings_panel)
        settings_header.addWidget(self.toggle_settings_btn)

        settings_header.addStretch()
        main_layout.addLayout(settings_header)

        # Settings container
        self.settings_container = QWidget()
        settings_layout = QVBoxLayout(self.settings_container)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        # Configuration panel
        self.config_panel = ConfigPanel()
        self.config_panel.input_directory_changed.connect(
            self.on_input_directory_changed
        )
        self.config_panel.output_directory_changed.connect(
            self.on_output_directory_changed
        )
        self.config_panel.history_file_changed.connect(self.on_history_file_changed)
        self.config_panel.model_changed.connect(self.on_model_changed)
        self.config_panel.target_column_changed.connect(self.on_target_column_changed)
        self.config_panel.sleep_time_changed.connect(self.on_sleep_time_changed)
        self.config_panel.chunk_size_changed.connect(self.on_chunk_size_changed)
        self.config_panel.load_files_requested.connect(self.load_files)
        self.config_panel.custom_model_added.connect(self.on_custom_model_added)
        self.config_panel.custom_model_removed.connect(self.on_custom_model_removed)
        settings_layout.addWidget(self.config_panel)

        main_layout.addWidget(self.settings_container)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        # Action panel (always visible)
        self.action_panel = ExtendedActionPanel()
        self.action_panel.previous_file_requested.connect(self.previous_file)
        self.action_panel.next_file_requested.connect(self.next_file)
        self.action_panel.translate_current_requested.connect(
            self.translate_current_file
        )
        self.action_panel.save_changes_requested.connect(self.save_changes)
        self.action_panel.auto_translate_requested.connect(self.auto_translate_all)
        self.action_panel.summarize_history_requested.connect(self.summarize_history)
        self.action_panel.undo_requested.connect(self.undo)
        self.action_panel.redo_requested.connect(self.redo)
        self.action_panel.find_requested.connect(self.show_find_dialog)
        self.action_panel.toggle_theme_requested.connect(self.toggle_theme)
        self.action_panel.save_chat_history_requested.connect(self.save_chat_history)
        main_layout.addWidget(self.action_panel)

        # Create splitter for table and details
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)

        # Table view
        self.table_view = QTableView()
        self.setup_table_view()
        splitter.addWidget(self.table_view)

        # Bottom section with cell detail and status
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Cell detail
        cell_detail_group = QGroupBox("Cell Content")
        cell_detail_layout = QVBoxLayout(cell_detail_group)

        self.cell_detail_text = QTextEdit()
        self.cell_detail_text.setMaximumHeight(AppSettings.CELL_DETAIL_HEIGHT)
        self.cell_detail_text.textChanged.connect(self.on_cell_detail_modified)
        cell_detail_layout.addWidget(self.cell_detail_text)

        bottom_layout.addWidget(cell_detail_group)

        # Status log
        status_group = QGroupBox("Status & Log")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(AppSettings.STATUS_HEIGHT)
        status_layout.addWidget(self.status_text)

        bottom_layout.addWidget(status_group)

        splitter.addWidget(bottom_widget)

        # Set splitter proportions - give more space to table
        splitter.setSizes([700, 150])

    def setup_menu_bar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Directory...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.config_panel.browse_input_dir)
        file_menu.addAction(open_action)

        save_action = QAction("Save Changes", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_changes)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Project menu
        project_menu = menubar.addMenu("Project")

        new_project_action = QAction("New Project...", self)
        new_project_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_project_action.triggered.connect(self.new_project)
        project_menu.addAction(new_project_action)

        open_project_action = QAction("Open Project...", self)
        open_project_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_project_action.triggered.connect(self.open_project)
        project_menu.addAction(open_project_action)

        save_project_action = QAction("Save Project", self)
        save_project_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_project_action.triggered.connect(self.save_project)
        project_menu.addAction(save_project_action)

        save_project_as_action = QAction("Save Project As...", self)
        save_project_as_action.triggered.connect(self.save_project_as)
        project_menu.addAction(save_project_as_action)

        project_menu.addSeparator()

        # Recent projects submenu
        self.recent_projects_menu = project_menu.addMenu("Recent Projects")
        self.update_recent_projects_menu()

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        find_action = QAction("Find and Replace...", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.show_find_dialog)
        edit_menu.addAction(find_action)

        # Translation menu
        translation_menu = menubar.addMenu("Translation")

        translate_action = QAction("Translate Current File", self)
        translate_action.setShortcut(QKeySequence("Ctrl+T"))
        translate_action.triggered.connect(self.translate_current_file)
        translation_menu.addAction(translate_action)

        auto_translate_action = QAction("Auto Translate All", self)
        auto_translate_action.triggered.connect(self.auto_translate_all)
        translation_menu.addAction(auto_translate_action)

        translation_menu.addSeparator()

        summarize_action = QAction("Summarize History", self)
        summarize_action.triggered.connect(self.summarize_history)
        translation_menu.addAction(summarize_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        api_keys_action = QAction("API Keys...", self)
        api_keys_action.triggered.connect(self.setup_api_keys)
        tools_menu.addAction(api_keys_action)

        theme_action = QAction("Toggle Theme", self)
        theme_action.triggered.connect(self.toggle_theme)
        tools_menu.addAction(theme_action)

    def setup_table_view(self):
        """Setup the table view"""
        # Configure table
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self.table_view.setMinimumHeight(AppSettings.TABLE_MIN_HEIGHT)

        # Setup model
        self.table_model = EnhancedPandasModel()
        self.table_view.setModel(self.table_model)

        # Connect signals
        self.table_view.clicked.connect(self.on_cell_clicked)
        self.table_view.selectionModel().selectionChanged.connect(
            self.on_selection_changed
        )
        self.table_model.dataEdited.connect(self.on_data_edited)

        # Setup context menu
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Standard shortcuts
        shortcuts = [
            ("Ctrl+S", self.save_changes),
            ("Ctrl+Z", self.undo),
            ("Ctrl+Y", self.redo),
            ("Ctrl+C", self.copy_selected),
            ("Ctrl+X", self.cut_selected),  # Add cut shortcut
            ("Ctrl+V", self.paste_data),
            ("Del", self.delete_selected),
            ("Ctrl+F", self.show_find_dialog),
            ("F3", self.find_next),
            ("Shift+F3", self.find_previous),
        ]

        for shortcut, function in shortcuts:
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(function)
            self.addAction(action)

    def setup_api_keys(self):
        """Setup API keys - now handled by API config panel"""
        # Load API keys from API service manager if available
        if hasattr(self, "api_config_panel") and self.api_config_panel is not None:
            try:
                api_manager = self.api_config_panel.get_api_manager()

                # Get all services with API keys
                for service in api_manager.get_all_services():
                    if api_manager.has_api_key(service.id):
                        api_key = api_manager.get_api_key(service.id)

                        # Set in translation engine (map to provider)
                        if service.provider_type.value in [
                            p.value for p in ModelProvider
                        ]:
                            provider = ModelProvider(service.provider_type.value)
                            self.translation_engine.set_api_key(provider, api_key)

                            # Store in app state
                            self.app_state.api_keys[provider.value] = api_key

                if self.app_state.api_keys:
                    self.log(f"Loaded {len(self.app_state.api_keys)} API key(s)")
                else:
                    self.log(
                        "No API keys configured. Go to API Configuration tab to set up."
                    )
            except Exception as e:
                self.log(f"Warning: Could not load API keys: {e}")
        else:
            self.log(
                "API Configuration panel not available. Please install cryptography: pip install cryptography requests"
            )

    def setup_storage_managers(self):
        """Setup storage managers and connections"""
        # Connect autosave signals
        self.autosave_manager.auto_saved.connect(self.on_auto_saved)
        self.autosave_manager.recovery_available.connect(self.on_recovery_available)

        # Register data providers for autosave
        self.autosave_manager.register_data_provider(
            "table_data", self.get_table_data_for_autosave
        )
        self.autosave_manager.register_data_provider(
            "ui_state", self.get_ui_state_for_autosave
        )
        self.autosave_manager.register_data_provider(
            "project_state", self.get_project_state_for_autosave
        )

        # Start autosave if enabled
        if prefs.get("auto_save_enabled", True):
            self.autosave_manager.start()

    def get_table_data_for_autosave(self) -> dict:
        """Get table data for autosave"""
        if not self.table_model or not hasattr(self.table_model, "get_dataframe"):
            return {}

        try:
            df = self.table_model.get_dataframe()
            if df is not None and not df.empty:
                return {
                    "dataframe_json": df.to_json(orient="split", force_ascii=False),
                    "current_file": (
                        str(self.app_state.csv_files[self.app_state.current_file_index])
                        if self.app_state.csv_files
                        else ""
                    ),
                    "file_index": self.app_state.current_file_index,
                }
        except Exception as e:
            print(f"Error getting table data for autosave: {e}")

        return {}

    def get_ui_state_for_autosave(self) -> dict:
        """Get UI state for autosave"""
        try:
            current_index = self.table_view.currentIndex()
            selected_indexes = []
            if self.table_view.selectionModel():
                selected_indexes = [
                    (idx.row(), idx.column())
                    for idx in self.table_view.selectionModel().selectedIndexes()
                ]

            return {
                "current_cell": (
                    (current_index.row(), current_index.column())
                    if current_index.isValid()
                    else None
                ),
                "selected_cells": selected_indexes,
                "scroll_position": (
                    self.table_view.verticalScrollBar().value()
                    if self.table_view.verticalScrollBar()
                    else 0
                ),
                "column_widths": {
                    i: self.table_view.columnWidth(i)
                    for i in range(
                        self.table_view.model().columnCount()
                        if self.table_view.model()
                        else 0
                    )
                },
                "settings_visible": self.settings_visible,
            }
        except Exception as e:
            print(f"Error getting UI state for autosave: {e}")
            return {}

    def get_project_state_for_autosave(self) -> dict:
        """Get project state for autosave"""
        return {
            "input_directory": self.app_state.input_directory,
            "output_directory": self.app_state.output_directory,
            "history_file": self.app_state.history_file,
            "current_model": self.app_state.current_model,
            "target_column": self.app_state.current_target_column,
            "chunk_size": self.app_state.chunk_size,
            "sleep_time": self.app_state.sleep_time,
        }

    def check_recovery_on_startup(self):
        """Check for recovery data on startup"""
        recovery_data = self.autosave_manager.check_for_recovery()
        if recovery_data:
            reply = QMessageBox.question(
                self,
                "Recovery Available",
                "An auto-saved session was found. Would you like to recover your work?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.recover_session(recovery_data)
            else:
                self.autosave_manager.clear_recovery_data()

    def recover_session(self, recovery_data: dict):
        """Recover session from autosave data"""
        try:
            data = self.autosave_manager.recover_data(recovery_data)

            # Recover project state
            if "project_state" in data:
                project_state = data["project_state"]
                self.app_state.input_directory = project_state.get(
                    "input_directory", ""
                )
                self.app_state.output_directory = project_state.get(
                    "output_directory", ""
                )
                self.app_state.history_file = project_state.get("history_file", "")
                self.app_state.current_model = project_state.get("current_model", "")
                self.app_state.current_target_column = project_state.get(
                    "target_column", ""
                )
                self.app_state.chunk_size = project_state.get("chunk_size", 50)
                self.app_state.sleep_time = project_state.get("sleep_time", 10)

                # Update UI with recovered state
                self.config_panel.set_input_directory(self.app_state.input_directory)
                self.config_panel.set_output_directory(self.app_state.output_directory)
                self.config_panel.set_history_file(self.app_state.history_file)
                self.config_panel.set_current_model(self.app_state.current_model)
                self.config_panel.set_target_column(
                    self.app_state.current_target_column
                )
                self.config_panel.set_chunk_size(self.app_state.chunk_size)
                self.config_panel.set_sleep_time(self.app_state.sleep_time)

            # Recover table data
            if "table_data" in data:
                table_data = data["table_data"]
                df_json = table_data.get("dataframe_json")
                if df_json:
                    import pandas as pd

                    df = pd.read_json(df_json, orient="split")
                    if self.table_model:
                        self.table_model.setDataFrame(df)

                    # Set file info
                    file_path = table_data.get("current_file", "")
                    if file_path:
                        self.action_panel.update_file_info(
                            Path(file_path).name, table_data.get("file_index", 0) + 1, 1
                        )

            # Recover UI state
            if "ui_state" in data:
                ui_state = data["ui_state"]
                self.settings_visible = ui_state.get("settings_visible", True)
                self.toggle_settings_panel() if not self.settings_visible else None

                # Restore scroll position
                scroll_pos = ui_state.get("scroll_position", 0)
                if self.table_view.verticalScrollBar():
                    self.table_view.verticalScrollBar().setValue(scroll_pos)

            self.log("Session recovered successfully")
            self.autosave_manager.clear_recovery_data()

        except Exception as e:
            self.log(f"Error recovering session: {e}")
            QMessageBox.warning(
                self, "Recovery Error", f"Failed to recover session: {e}"
            )

    def load_last_project(self):
        """Load the last opened project"""
        last_project = prefs.get("last_project_path", "")
        if last_project and Path(last_project).exists():
            try:
                if self.project_manager.load(last_project):
                    self.apply_project_state()
                    self.log(
                        f"Loaded project: {self.project_manager.get_project_name()}"
                    )
                else:
                    self.log("Failed to load last project")
            except Exception as e:
                self.log(f"Error loading last project: {e}")

    def apply_project_state(self):
        """Apply project state to UI"""
        if not self.project_manager.is_valid_project():
            return

        # Apply project settings to app state
        self.app_state.input_directory = self.project_manager.get_state("input_dir", "")
        self.app_state.output_directory = self.project_manager.get_state(
            "output_dir", ""
        )
        self.app_state.history_file = self.project_manager.get_state("history_file", "")
        self.app_state.current_model = self.project_manager.get_state(
            "model", prefs.get("default_ai_model", "")
        )
        self.app_state.current_target_column = self.project_manager.get_state(
            "target_column", "Initial"
        )
        self.app_state.chunk_size = self.project_manager.get_state("chunk_size", 50)
        self.app_state.sleep_time = self.project_manager.get_state("sleep_time", 10)

        # Update FileManager with directories
        if self.app_state.input_directory:
            self.file_manager.set_input_directory(self.app_state.input_directory)
        if self.app_state.output_directory:
            self.file_manager.set_output_directory(self.app_state.output_directory)

        # Update UI controls
        self.config_panel.set_input_directory(self.app_state.input_directory)
        self.config_panel.set_output_directory(self.app_state.output_directory)
        self.config_panel.set_history_file(self.app_state.history_file)
        self.config_panel.set_current_model(self.app_state.current_model)
        self.config_panel.set_target_column(self.app_state.current_target_column)
        self.config_panel.set_chunk_size(self.app_state.chunk_size)
        self.config_panel.set_sleep_time(self.app_state.sleep_time)

        # Load files if input directory is set
        if self.app_state.input_directory:
            self.load_files()

            # Restore file position and UI state
            file_index = self.project_manager.get_state("open_file_index", 0)
            if 0 <= file_index < len(self.app_state.csv_files):
                self.app_state.current_file_index = file_index
                self.load_current_file()

                # Restore scroll position
                scroll_pos = self.project_manager.get_state("scroll_pos", 0)
                if self.table_view.verticalScrollBar():
                    self.table_view.verticalScrollBar().setValue(scroll_pos)

    def capture_state_into_project(self):
        """Capture current state into project manager"""
        if not self.project_manager.current_path:
            return

        # Get current scroll position
        scroll_pos = 0
        if self.table_view.verticalScrollBar():
            scroll_pos = self.table_view.verticalScrollBar().value()

        # Get selected rows
        selected_rows = []
        if self.table_view.selectionModel():
            for index in self.table_view.selectionModel().selectedRows():
                selected_rows.append(index.row())

        # Update project state
        updates = {
            "input_dir": self.app_state.input_directory,
            "output_dir": self.app_state.output_directory,
            "history_file": self.app_state.history_file,
            "open_file_index": self.app_state.current_file_index,
            "scroll_pos": scroll_pos,
            "selected_rows": selected_rows,
            "target_column": self.app_state.current_target_column,
            "chunk_size": self.app_state.chunk_size,
            "sleep_time": self.app_state.sleep_time,
            "model": self.app_state.current_model,
        }

        self.project_manager.update_state(updates)

    def on_auto_saved(self, file_path: str):
        """Handle auto-save completion"""
        # Optionally show a brief status message
        pass

    def on_recovery_available(self, file_path: str):
        """Handle recovery data availability"""
        self.log("Auto-save recovery data available")

    def apply_theme(self, theme_name: str):
        """Apply theme to the application"""
        self.app_state.current_theme = theme_name
        stylesheet = AppSettings.get_theme_style(theme_name)
        self.setStyleSheet(stylesheet)

        # Update action panel theme button
        self.action_panel.update_theme_button(theme_name == "dark")

        self.log(f"Applied {theme_name} theme")

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_theme = self.app_state.current_theme
        new_theme = "dark" if current_theme == "light" else "light"
        self.apply_theme(new_theme)
        # Save theme preference
        prefs.set("theme", new_theme)

    def toggle_settings_panel(self):
        """Toggle visibility of settings panel"""
        self.settings_visible = not self.settings_visible
        self.settings_container.setVisible(self.settings_visible)

        if self.settings_visible:
            self.toggle_settings_btn.setText("🔧 Hide Settings")
        else:
            self.toggle_settings_btn.setText("🔧 Show Settings")

    # Event handlers
    def on_input_directory_changed(self, directory: str):
        """Handle input directory change"""
        self.app_state.input_directory = directory
        # Update FileManager
        self.file_manager.set_input_directory(directory)
        # Update project state
        self.project_manager.set_state("input_dir", directory)
        prefs.set("last_input_dir", directory)
        self.autosave_manager.mark_dirty()
        self.log(f"Input directory changed to: {directory}")

    def on_output_directory_changed(self, directory: str):
        """Handle output directory change"""
        self.app_state.output_directory = directory
        # Update FileManager
        self.file_manager.set_output_directory(directory)
        # Update project state
        self.project_manager.set_state("output_dir", directory)
        prefs.set("last_output_dir", directory)
        self.autosave_manager.mark_dirty()
        self.log(f"Output directory changed to: {directory}")

    def on_history_file_changed(self, file_path: str):
        """Handle history file change"""
        self.app_state.history_file = file_path
        self.project_manager.set_state("history_file", file_path)
        self.autosave_manager.mark_dirty()
        self.log(f"History file changed to: {file_path}")

    def on_model_changed(self, model_name: str):
        """Handle model selection change"""
        self.app_state.current_model = model_name
        self.project_manager.set_state("model", model_name)
        prefs.set("default_ai_model", model_name)
        self.autosave_manager.mark_dirty()
        self.log(f"Model changed to: {model_name}")

    def on_sleep_time_changed(self, seconds: int):
        """Handle sleep time change"""
        self.app_state.sleep_time = seconds
        self.project_manager.set_state("sleep_time", seconds)
        prefs.set("default_sleep_time", seconds)
        self.autosave_manager.mark_dirty()
        self.log(f"Sleep time changed to: {seconds}s")

    def on_chunk_size_changed(self, size: int):
        """Handle chunk size change"""
        self.app_state.chunk_size = size
        self.project_manager.set_state("chunk_size", size)
        prefs.set("default_chunk_size", size)
        self.autosave_manager.mark_dirty()
        self.log(f"Chunk size changed to: {size} lines")

    def on_cell_clicked(self, index):
        """Handle cell click in table"""
        if index.isValid():
            value = self.table_model.data(index, Qt.ItemDataRole.DisplayRole)
            self.cell_detail_text.setText(str(value) if value else "")

    def on_selection_changed(self, selected, deselected):
        """Handle table selection change"""
        if self.table_model:
            indexes = self.table_view.selectionModel().selectedIndexes()
            self.table_model.updateSelection(indexes)

    def on_data_edited(self, row, col, old_value, new_value):
        """Handle data editing in table"""
        self.log(f"Cell ({row+1}, {col+1}) changed from '{old_value}' to '{new_value}'")

    def on_cell_detail_modified(self):
        """Handle cell detail text modification"""
        current_index = self.table_view.currentIndex()
        if current_index.isValid() and self.table_model:
            new_value = self.cell_detail_text.toPlainText()
            self.table_model.setData(current_index, new_value)

    def on_target_column_changed(self, column: str):
        """Handle target column change"""
        self.app_state.current_target_column = column
        self.log(f"Target column changed to: {column}")

    # File management methods
    def load_files(self):
        """Load CSV files from input directory"""
        if not self.app_state.input_directory:
            QMessageBox.warning(
                self, "Warning", "Please select an input directory first."
            )
            return

        try:
            # Set input directory and get CSV files
            success = self.file_manager.set_input_directory(
                self.app_state.input_directory
            )
            if not success:
                self.log("Failed to set input directory")
                QMessageBox.critical(self, "Error", "Failed to access input directory.")
                return

            # Auto-generate and set history file path
            if self.app_state.csv_files:
                current_file = self.app_state.csv_files[
                    self.app_state.current_file_index
                ]
                file_name = (
                    current_file.name
                    if hasattr(current_file, "name")
                    else Path(current_file).name
                )
                history_path = self.file_manager.ensure_history_file(file_name)
                if history_path:
                    self.app_state.history_file = history_path
                    self.config_panel.set_history_file(history_path)
                    self.log(f"Using history file: {Path(history_path).name}")

            file_count = self.file_manager.get_file_count()
            if file_count > 0:
                # Update app state with Path objects
                csv_files = self.file_manager.csv_files
                self.app_state.csv_files = [
                    Path(self.app_state.input_directory) / f for f in csv_files
                ]
                self.app_state.current_file_index = 0

                self.load_current_file()
                self.log(f"Loaded {file_count} CSV files")
            else:
                self.log("No CSV files found in directory")
                QMessageBox.information(
                    self, "Info", "No CSV files found in the selected directory."
                )

        except Exception as e:
            self.log(f"Error loading files: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load files: {str(e)}")

    def load_current_file(self):
        """Load the current file into the table"""
        if not self.app_state.csv_files or self.app_state.current_file_index < 0:
            return

        try:
            # Use FileManager to load file by index
            df = self.file_manager.load_file(self.app_state.current_file_index)
            if df is None:
                self.log("Failed to load file")
                return

            self.table_model.setDataFrame(df)

            # Update UI
            current_file = self.app_state.csv_files[self.app_state.current_file_index]
            filename = current_file.name
            self.action_panel.update_file_info(
                self.app_state.current_file_index,
                len(self.app_state.csv_files),
                filename,
            )
            self.action_panel.update_navigation_buttons(
                self.app_state.current_file_index > 0,
                self.app_state.current_file_index < len(self.app_state.csv_files) - 1,
            )
            self.action_panel.update_action_buttons(True)

            self.log(f"Loaded file: {filename}")

        except Exception as e:
            self.log(f"Error loading file: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def previous_file(self):
        """Navigate to previous file"""
        if self.app_state.current_file_index > 0:
            self.app_state.current_file_index -= 1
            self.load_current_file()

    def next_file(self):
        """Navigate to next file"""
        if self.app_state.current_file_index < len(self.app_state.csv_files) - 1:
            self.app_state.current_file_index += 1
            self.load_current_file()

    def save_changes(self):
        """Save changes to current file"""
        if not self.table_model or self.table_model.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "No data to save.")
            return

        if not self.app_state.csv_files or self.app_state.current_file_index < 0:
            QMessageBox.warning(self, "Warning", "No file selected.")
            return

        try:
            # Get DataFrame from table model
            df = self.table_model.getDataFrame()

            # Validate we have data
            if df is None or df.empty:
                QMessageBox.warning(self, "Warning", "No data to save.")
                return

            # Ensure output directory exists
            if not self.app_state.output_directory:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "No output directory specified. Please set an output directory first.",
                )
                return

            # Create output directory if it doesn't exist
            if not os.path.exists(self.app_state.output_directory):
                try:
                    os.makedirs(self.app_state.output_directory, exist_ok=True)
                    self.log(
                        f"Created output directory: {self.app_state.output_directory}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Failed to create output directory: {e}"
                    )
                    return

            # Use FileManager to save file by index
            success = self.file_manager.save_file_by_index(
                self.app_state.current_file_index, df
            )

            if success:
                # Reset modified state
                self.table_model.resetModified()

                # Get current file info
                current_file = self.app_state.csv_files[
                    self.app_state.current_file_index
                ]
                filename = (
                    current_file if isinstance(current_file, str) else str(current_file)
                )

                # Update project state if we have a project
                if self.project_manager.current_path:
                    self.project_manager.add_processed_file(filename, success=True)
                    self.capture_state_into_project()

                # Mark autosave as dirty to save the new state
                self.autosave_manager.mark_dirty()

                self.log(f"Saved changes to: {filename}")
                QMessageBox.information(self, "Success", "Changes saved successfully.")

            else:
                # Try to get more detailed error information
                error_details = ""

                # Check if file is writable
                current_file = self.app_state.csv_files[
                    self.app_state.current_file_index
                ]
                filename = (
                    current_file if isinstance(current_file, str) else str(current_file)
                )
                output_path = os.path.join(
                    self.app_state.output_directory, f"translated_{filename}"
                )

                if os.path.exists(output_path):
                    if not os.access(output_path, os.W_OK):
                        error_details = "File is write-protected or being used by another application."
                else:
                    if not os.access(self.app_state.output_directory, os.W_OK):
                        error_details = "No write permission to output directory."

                # Update project state to mark as failed
                if self.project_manager.current_path:
                    self.project_manager.add_processed_file(filename, success=False)

                self.log(f"Failed to save file: {filename}. {error_details}")
                QMessageBox.critical(
                    self,
                    "Error",
                    (
                        f"Failed to save file.\n\n{error_details}"
                        if error_details
                        else "Failed to save file."
                    ),
                )

        except Exception as e:
            # Get current file info for error logging
            filename = "Unknown"
            try:
                if self.app_state.csv_files and self.app_state.current_file_index >= 0:
                    current_file = self.app_state.csv_files[
                        self.app_state.current_file_index
                    ]
                    filename = (
                        current_file
                        if isinstance(current_file, str)
                        else str(current_file)
                    )
            except:
                pass

            # Update project state to mark as failed
            if self.project_manager.current_path:
                self.project_manager.add_processed_file(filename, success=False)

            self.log(f"Error saving file {filename}: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

            # Print traceback for debugging
            import traceback

            print(f"Save error traceback:\n{traceback.format_exc()}")

    # Translation methods
    def translate_current_file(self):
        """Translate the current file using selected target column"""
        if not self.table_model or self.table_model.rowCount() == 0:
            self.log("No data to translate")
            return

        # Get configuration from UI
        target_column = self.config_panel.get_target_column()
        model_name = self.config_panel.get_current_model()
        chunk_size = self.config_panel.get_chunk_size()
        sleep_time = self.config_panel.get_sleep_time()

        # Check if target column exists
        column_names = list(self.table_model.getDataFrame().columns)
        if target_column not in column_names:
            self.log(f"Error: Target column '{target_column}' not found in CSV")
            QMessageBox.warning(
                self,
                "Column Not Found",
                f"Target column '{target_column}' not found in the CSV file.\n\nAvailable columns: {', '.join(column_names)}",
            )
            return

        target_col_index = column_names.index(target_column)

        # Get original text column (assume first column contains original text)
        if len(column_names) < 2:
            self.log("Error: CSV must have at least 2 columns (original and target)")
            QMessageBox.warning(
                self,
                "Invalid CSV Format",
                "CSV file must have at least 2 columns (original text and target column).",
            )
            return

        original_col_index = 0  # First column is original text

        self.log(
            f"Starting translation to '{target_column}' column using model: {model_name}"
        )

        # Get original texts for translation
        original_texts = []
        for row in range(self.table_model.rowCount()):
            text = str(self.table_model.getDataFrame().iloc[row, original_col_index])
            if text and text.strip() and text != "nan":
                original_texts.append(text.strip())
            else:
                original_texts.append("")

        # Filter out empty texts and create mapping
        texts_to_translate = []
        row_mapping = []  # Maps text index to row index

        for i, text in enumerate(original_texts):
            if text and text.strip():
                texts_to_translate.append(text)
                row_mapping.append(i)

        if not texts_to_translate:
            self.log("No text to translate found")
            QMessageBox.information(
                self, "No Content", "No text content found to translate."
            )
            return

        # Create translation chunks
        chunks = []
        chunk_id = 0
        for i in range(0, len(texts_to_translate), chunk_size):
            end_idx = min(i + chunk_size, len(texts_to_translate))
            chunk_texts = texts_to_translate[i:end_idx]

            chunk = TranslationChunk(
                chunk_id=chunk_id,
                original_texts=chunk_texts,
                start_row=i,
                end_row=end_idx - 1,
                target_column=target_column,
            )
            chunks.append(chunk)
            chunk_id += 1

        # Determine model provider based on model name
        model_provider = self.app_state.current_model_provider
        if "gpt" in model_name.lower() or "openai" in model_name.lower():
            model_provider = ModelProvider.OPENAI
        elif "claude" in model_name.lower() or "anthropic" in model_name.lower():
            model_provider = ModelProvider.ANTHROPIC
        else:
            model_provider = ModelProvider.GOOGLE

        # Create translation request
        request = TranslationRequest(
            model_provider=model_provider,
            model_name=model_name,
            target_column=target_column,
            sleep_time=sleep_time,
            chunk_size=chunk_size,
            use_history=True,
        )

        # Set chat history in translation engine
        history = self.history_manager.get_chat_history_for_api()
        self.translation_engine.set_chat_history(history)

        # Start translation in a separate thread
        def translation_worker():
            try:
                total_chunks = len(chunks)
                self.log(f"Translating {total_chunks} chunks...")

                for i, chunk in enumerate(chunks):
                    self.log(
                        f"Translating chunk {i + 1}/{total_chunks} ({len(chunk.original_texts)} texts)..."
                    )

                    # Translate the chunk
                    translated_chunk = self.translation_engine.translate_chunk(
                        chunk, request
                    )

                    if (
                        translated_chunk.status == "completed"
                        and translated_chunk.translated_texts
                    ):
                        # Update the table model with translated texts
                        for j, translated_text in enumerate(
                            translated_chunk.translated_texts
                        ):
                            text_index = chunk.start_row + j
                            if text_index < len(row_mapping):
                                row = row_mapping[text_index]
                                if row < self.table_model.rowCount():
                                    # Set the translated text in target column
                                    index = self.table_model.index(
                                        row, target_col_index
                                    )
                                    self.table_model.setData(index, translated_text)

                        # Add to history
                        self.history_manager.add_translation_entry(
                            chunk.original_texts,
                            translated_chunk.translated_texts,
                            model_name,
                            target_column,
                        )

                        self.log(f"✓ Completed chunk {i + 1}/{total_chunks}")
                    else:
                        error_msg = translated_chunk.error_message or "Unknown error"
                        self.log(f"✗ Failed to translate chunk {i + 1}: {error_msg}")

                    # Sleep between chunks
                    if i < total_chunks - 1:
                        time.sleep(sleep_time)

                self.log("🎉 Translation completed!")

                # Save history
                if self.history_manager.save_history():
                    self.log("Translation history saved")

            except Exception as e:
                self.log(f"Translation error: {e}")
                import traceback

                self.log(f"Full error: {traceback.format_exc()}")

        # Run translation in thread
        thread = threading.Thread(target=translation_worker)
        thread.daemon = True
        thread.start()

    def auto_translate_all(self):
        """Auto translate all files"""
        if not self.app_state.csv_files:
            QMessageBox.warning(self, "Warning", "No files loaded.")
            return

        # Check if API keys are configured
        if not self.app_state.api_keys:
            QMessageBox.warning(self, "Warning", "Please configure API keys first.")
            self.setup_api_keys()
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Auto Translate All",
            f"This will translate all {len(self.app_state.csv_files)} files.\nThis may take a long time. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.action_panel.set_translation_in_progress(True)
            self.action_panel.show_progress(True)

            total_files = len(self.app_state.csv_files)
            successful_files = 0
            failed_files = 0

            for file_index in range(total_files):
                # Update progress
                self.action_panel.update_progress(
                    file_index,
                    total_files,
                    f"Translating file {file_index + 1}/{total_files}",
                )

                # Load file
                df = self.file_manager.load_file(file_index)
                if df is None or df.empty:
                    self.log(f"Skipping empty file {file_index + 1}")
                    failed_files += 1
                    continue

                filename = self.app_state.csv_files[file_index].name
                self.log(f"Auto-translating file: {filename}")

                # Find source column
                source_column = df.columns[0] if len(df.columns) > 0 else None
                if not source_column:
                    self.log(f"No source column found in file: {filename}")
                    failed_files += 1
                    continue

                # Create or find target column
                target_column = "Translation"
                if target_column not in df.columns:
                    df[target_column] = ""

                try:
                    # Prepare translation chunks
                    chunks = self.file_manager.prepare_translation_chunks(
                        df, source_column, self.app_state.chunk_size
                    )

                    if not chunks:
                        self.log(f"No text to translate in file: {filename}")
                        failed_files += 1
                        continue

                    # Create translation request
                    from models.data_structures import TranslationRequest, ModelProvider

                    request = TranslationRequest(
                        source_column=source_column,
                        target_column=target_column,
                        model_provider=ModelProvider.GOOGLE,
                        chunk_size=self.app_state.chunk_size,
                        sleep_time=self.app_state.sleep_time,
                    )

                    # Translate chunks
                    translated_chunks = []
                    for chunk in chunks:
                        result_chunk = self.translation_engine.translate_chunk(
                            chunk, request
                        )
                        translated_chunks.append(result_chunk)

                        # Sleep between chunks to avoid rate limits
                        time.sleep(self.app_state.sleep_time)

                    # Apply translations back to dataframe
                    updated_df = self.file_manager.apply_translation_chunks(
                        df, translated_chunks, target_column
                    )

                    # Save the file
                    success = self.file_manager.save_file_by_index(
                        file_index, updated_df
                    )
                    if success:
                        successful_files += 1
                        self.log(f"Successfully translated and saved: {filename}")
                    else:
                        failed_files += 1
                        self.log(f"Failed to save translated file: {filename}")

                except Exception as e:
                    failed_files += 1
                    self.log(f"Error translating file {filename}: {str(e)}")

            # Final results
            self.action_panel.hide_progress()
            self.action_panel.set_translation_in_progress(False)

            # Reload current file if it was translated
            if self.app_state.current_file_index >= 0:
                self.load_current_file()

            result_message = f"Auto-translation completed!\nSuccessful: {successful_files} files\nFailed: {failed_files} files"
            self.log(result_message)

            if successful_files > 0:
                QMessageBox.information(
                    self, "Auto-Translation Complete", result_message
                )
            else:
                QMessageBox.critical(
                    self,
                    "Auto-Translation Failed",
                    "No files were successfully translated.",
                )

        except Exception as e:
            self.log(f"Auto-translation error: {str(e)}")
            self.action_panel.set_translation_in_progress(False)
            self.action_panel.hide_progress()
            QMessageBox.critical(self, "Error", f"Auto-translation failed: {str(e)}")

    def summarize_history(self):
        """Summarize translation history"""
        self.log("History summarization not yet implemented")
        QMessageBox.information(
            self, "Info", "History summarization feature coming soon!"
        )

    # Edit operations
    def undo(self):
        """Undo last operation"""
        if self.table_model and self.table_model.canUndo():
            self.table_model.undo()
            self.log("Undid last action")
        else:
            self.log("Nothing to undo")

    def redo(self):
        """Redo last undone operation"""
        if self.table_model and self.table_model.canRedo():
            self.table_model.redo()
            self.log("Redid last action")
        else:
            self.log("Nothing to redo")

    def copy_selected(self):
        """Copy selected cells to clipboard"""
        if not self.table_model:
            return

        selected_indexes = self.table_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            return

        clipboard_data = self.table_model.copySelectedData(selected_indexes)
        if clipboard_data:
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_data)
            self.log(f"Copied {len(selected_indexes)} cells to clipboard")

    def cut_selected(self):
        """Cut selected cells to clipboard"""
        if not self.table_model:
            return

        selected_indexes = self.table_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            return

        clipboard_data = self.table_model.cutSelectedData(selected_indexes)
        if clipboard_data:
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_data)
            self.log(f"Cut {len(selected_indexes)} cells to clipboard")

    def paste_data(self):
        """Paste data from clipboard"""
        if not self.table_model:
            return

        clipboard = QApplication.clipboard()
        text_data = clipboard.text()
        if not text_data:
            return

        # Get current selection or use top-left cell
        current_index = self.table_view.currentIndex()
        start_row = current_index.row() if current_index.isValid() else 0
        start_col = current_index.column() if current_index.isValid() else 0

        success = self.table_model.pasteData(start_row, start_col, text_data)
        if success:
            self.log(f"Pasted data at row {start_row + 1}, column {start_col + 1}")
        else:
            self.log("Failed to paste data")

    def delete_selected(self):
        """Delete selected cells"""
        if not self.table_model:
            return

        selected_indexes = self.table_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            return

        success = self.table_model.deleteSelectedData(selected_indexes)
        if success:
            self.log(f"Deleted {len(selected_indexes)} cells")

    def show_find_dialog(self):
        """Show find and replace dialog"""
        if not self.find_dialog:
            self.find_dialog = FindReplaceDialog(self)
            self.find_dialog.find_next_requested.connect(self.find_text)

        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()

    def find_text(self, text, case_sensitive, whole_words):
        """Find text in table"""
        if not self.table_model:
            return

        # Use the enhanced find functionality
        results = self.table_model.find(text, case_sensitive, whole_words)
        if results:
            self.log(f"Found {len(results)} occurrences of '{text}'")
            # Highlight the results
            self.table_model.highlightCells(set(results))
            # Navigate to the first result
            first_result = results[0]
            index = self.table_model.index(first_result[0], first_result[1])
            self.table_view.setCurrentIndex(index)
            self.table_view.scrollTo(index)
        else:
            self.table_model.clearHighlights()
            self.log(f"No occurrences found for '{text}'")

    def on_custom_model_added(self, model):
        """Handle custom model addition"""
        self.app_state.add_custom_model(model)
        self.translation_engine.add_custom_model(model)
        self.log(f"Added custom model: {model.display_name or model.model_name}")

    def on_custom_model_removed(self, model_name: str):
        """Handle custom model removal"""
        # Remove from app state
        self.app_state.custom_models = [
            m for m in self.app_state.custom_models if m.model_name != model_name
        ]
        self.log(f"Removed custom model: {model_name}")

    def find_next(self):
        """Find next occurrence"""
        if self.find_dialog:
            self.find_dialog.find_next()

    def find_previous(self):
        """Find previous occurrence"""
        if self.find_dialog:
            self.find_dialog.find_previous()

    def show_context_menu(self, position):
        """Show context menu for table"""
        if not self.table_model:
            return

        # Get the index at the position
        index = self.table_view.indexAt(position)

        # Create context menu
        from PyQt6.QtWidgets import QMenu

        context_menu = QMenu(self)

        # Translation submenu (if rows are selected)
        has_selection = bool(self.table_view.selectedIndexes())
        if has_selection:
            translate_menu = context_menu.addMenu("🌐 Translate Selected Rows")

            translate_no_context_action = translate_menu.addAction("Without Context")
            translate_no_context_action.triggered.connect(
                lambda: self.translate_selected_rows(use_context=False)
            )

            translate_with_context_action = translate_menu.addAction("With Context...")
            translate_with_context_action.triggered.connect(
                lambda: self.translate_selected_rows(use_context=True)
            )

            context_menu.addSeparator()

        # Copy action
        copy_action = context_menu.addAction("Copy")
        copy_action.triggered.connect(self.copy_selected)
        copy_action.setEnabled(has_selection)

        # Cut action
        cut_action = context_menu.addAction("Cut")
        cut_action.triggered.connect(self.cut_selected)
        cut_action.setEnabled(has_selection)

        # Paste action
        paste_action = context_menu.addAction("Paste")
        paste_action.triggered.connect(self.paste_data)

        # Delete action
        delete_action = context_menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_selected)
        delete_action.setEnabled(has_selection)

        context_menu.addSeparator()

        # Find action
        find_action = context_menu.addAction("Find...")
        find_action.triggered.connect(self.show_find_dialog)

        # Show menu
        context_menu.exec(self.table_view.mapToGlobal(position))

    def update_status(self):
        """Update status periodically"""
        # Update undo/redo button states
        if self.table_model:
            can_undo = self.table_model.canUndo()
            can_redo = self.table_model.canRedo()
            undo_desc = self.table_model.getUndoDescription() if can_undo else ""
            redo_desc = self.table_model.getRedoDescription() if can_redo else ""

            self.action_panel.update_undo_redo_states(
                can_undo, can_redo, undo_desc, redo_desc
            )

    # Project management methods
    def new_project(self):
        """Create a new project"""
        from PyQt6.QtWidgets import QFileDialog

        input_dir = QFileDialog.getExistingDirectory(
            self, "Select Input Directory for New Project"
        )

        if input_dir:
            try:
                project_path = self.project_manager.create_new_project(input_dir)
                prefs.add_recent_project(project_path)
                self.apply_project_state()
                self.update_recent_projects_menu()
                self.log(
                    f"Created new project: {self.project_manager.get_project_name()}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project: {e}")

    def open_project(self):
        """Open an existing project"""
        from PyQt6.QtWidgets import QFileDialog

        project_file, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "CSV Translator Projects (*.csvtproj)"
        )

        if project_file:
            try:
                if self.project_manager.load(project_file):
                    prefs.add_recent_project(project_file)
                    self.apply_project_state()
                    self.update_recent_projects_menu()
                    self.log(
                        f"Opened project: {self.project_manager.get_project_name()}"
                    )
                else:
                    QMessageBox.critical(self, "Error", "Failed to load project file")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {e}")

    def save_project(self):
        """Save current project"""
        if not self.project_manager.current_path:
            self.save_project_as()
            return

        try:
            self.capture_state_into_project()
            if self.project_manager.save():
                self.log("Project saved successfully")
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

    def save_project_as(self):
        """Save project with a new name"""
        from PyQt6.QtWidgets import QFileDialog

        # Suggest default name based on input directory
        default_name = "project.csvtproj"
        if self.app_state.input_directory:
            dir_name = Path(self.app_state.input_directory).name
            default_name = f"{dir_name}.csvtproj"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            default_name,
            "CSV Translator Projects (*.csvtproj)",
        )

        if save_path:
            try:
                self.capture_state_into_project()
                if self.project_manager.save(save_path):
                    prefs.add_recent_project(save_path)
                    self.update_recent_projects_menu()
                    self.log(f"Project saved as: {Path(save_path).name}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to save project")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

    def open_recent_project(self, project_path: str):
        """Open a recent project"""
        try:
            if Path(project_path).exists():
                if self.project_manager.load(project_path):
                    self.apply_project_state()
                    prefs.add_recent_project(project_path)  # Move to top of recent list
                    self.update_recent_projects_menu()
                    self.log(
                        f"Opened recent project: {self.project_manager.get_project_name()}"
                    )
                else:
                    QMessageBox.critical(self, "Error", "Failed to load project file")
            else:
                QMessageBox.warning(self, "Warning", "Project file no longer exists")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open recent project: {e}")

    def update_recent_projects_menu(self):
        """Update the recent projects menu"""
        if not hasattr(self, "recent_projects_menu"):
            return

        # Clear existing actions
        self.recent_projects_menu.clear()

        # Add recent projects
        recent_projects = prefs.get_recent_projects()
        if recent_projects:
            for project_path in recent_projects:
                if Path(project_path).exists():
                    project_name = Path(project_path).stem
                    action = QAction(project_name, self)
                    action.triggered.connect(
                        lambda checked, path=project_path: self.open_recent_project(
                            path
                        )
                    )
                    self.recent_projects_menu.addAction(action)

            self.recent_projects_menu.addSeparator()
            clear_action = QAction("Clear Recent Projects", self)
            clear_action.triggered.connect(self.clear_recent_projects)
            self.recent_projects_menu.addAction(clear_action)
        else:
            no_recent_action = QAction("No recent projects", self)
            no_recent_action.setEnabled(False)
            self.recent_projects_menu.addAction(no_recent_action)

    def clear_recent_projects(self):
        """Clear the recent projects list"""
        prefs.set("recent_projects", [])
        self.update_recent_projects_menu()
        self.log("Recent projects list cleared")

    def on_api_key_configured(self, service_id: str, api_key: str):
        """Handle API key configuration from API config panel"""
        if not self.api_config_panel:
            return

        try:
            # Get service info
            api_manager = self.api_config_panel.get_api_manager()
            service = api_manager.get_service(service_id)

            if service:
                # Set in translation engine
                if service.provider_type.value in [p.value for p in ModelProvider]:
                    provider = ModelProvider(service.provider_type.value)
                    self.translation_engine.set_api_key(provider, api_key)
                    self.app_state.api_keys[provider.value] = api_key

                self.log(f"API key configured for {service.name}")
        except Exception as e:
            self.log(f"Error configuring API key: {e}")

    def on_instruction_changed(self, instruction_type: str, content: str):
        """Handle system instruction changes"""
        if instruction_type == "translation":
            self.app_state.translation_instruction = content
            self.log("Translation instruction updated")
        elif instruction_type == "summary":
            self.app_state.summary_instruction = content
            self.log("Summary instruction updated")

    def on_summary_requested(
        self, system_instruction: str, context_files: list, config: dict
    ):
        """Handle summary request from summary panel"""
        self.log("Starting summary generation...")

        # TODO: Implement actual summary generation using API
        # For now, show placeholder
        QMessageBox.information(
            self,
            "Summary",
            f"Summary generation requested.\n\n"
            f"System instruction: {len(system_instruction)} chars\n"
            f"Context files: {len(context_files)}\n"
            f"This feature will be implemented next.",
        )

    def translate_selected_rows(self, use_context: bool):
        """Translate selected rows with optional context"""
        selected_indexes = self.table_view.selectionModel().selectedIndexes()

        if not selected_indexes:
            QMessageBox.warning(self, "Warning", "No rows selected.")
            return

        # Get unique selected rows
        selected_rows = sorted(set(index.row() for index in selected_indexes))

        self.log(
            f"Translating {len(selected_rows)} selected rows (context: {use_context})..."
        )

        if use_context:
            # Show context file selection dialog
            from ui.dialogs import ContextFileSelectionDialog

            dialog = ContextFileSelectionDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                context_files, context_config = dialog.get_selection()

                if not context_files:
                    QMessageBox.warning(self, "Warning", "No context files selected.")
                    return

                # TODO: Implement translation with context
                self.log(f"Will translate with context from {len(context_files)} files")
                QMessageBox.information(
                    self,
                    "Translation",
                    f"Translation with context will be implemented.\n\n"
                    f"Selected rows: {len(selected_rows)}\n"
                    f"Context files: {len(context_files)}",
                )
        else:
            # Translate without context
            # TODO: Implement translation without context
            self.log(f"Translating {len(selected_rows)} rows without context")
            QMessageBox.information(
                self,
                "Translation",
                f"Translation without context will be implemented.\n\n"
                f"Selected rows: {len(selected_rows)}",
            )

    def log(self, message: str):
        """Add message to status log"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.status_text.append(formatted_message)

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Save window geometry to preferences
            geometry = self.geometry()
            prefs.set_window_geometry(
                geometry.x(),
                geometry.y(),
                geometry.width(),
                geometry.height(),
                self.isMaximized(),
            )

            # Capture current state into project
            self.capture_state_into_project()

            # Save project if valid
            if self.project_manager.current_path:
                self.project_manager.save()
                prefs.set("last_project_path", self.project_manager.current_path)

            # Stop auto-save
            self.autosave_manager.stop()

            # Clean up old auto-save files
            self.autosave_manager.cleanup_old_snapshots()

            # Clear recovery data since we're closing cleanly
            self.autosave_manager.clear_recovery_data()

            self.log("Application closed successfully")

        except Exception as e:
            print(f"Error during close: {e}")

        # Accept the close event
        event.accept()

    def save_chat_history(self):
        """Save chat history for the current file based on edited translations"""
        try:
            if not self.table_model or self.table_model.rowCount() == 0:
                QMessageBox.warning(self, "Warning", "No data to save to chat history.")
                return
            if not self.app_state.csv_files or self.app_state.current_file_index < 0:
                QMessageBox.warning(self, "Warning", "No file selected.")
                return

            # Ensure history file path is set
            if not self.history_manager.history_file:
                if not self.app_state.history_file:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "No history file specified. Please configure history file path first.",
                    )
                    return
                self.history_manager.set_history_file(self.app_state.history_file)

            # Get DataFrame and chunk_size
            df = self.table_model.getDataFrame()
            chunk_size = self.app_state.chunk_size if self.app_state.chunk_size else 50
            target_column = (
                self.app_state.current_target_column or "Machine translation"
            )

            # Current filename
            current_path = self.app_state.csv_files[self.app_state.current_file_index]
            file_name = (
                current_path.name
                if hasattr(current_path, "name")
                else Path(current_path).name
            )

            success = self.history_manager.update_history_for_file(
                file_name,
                df,
                chunk_size=chunk_size,
                target_column=target_column,
            )

            if success:
                self.log("Chat history saved successfully")
                QMessageBox.information(self, "Success", "Chat history updated.")
                # Mark autosave dirty
                self.autosave_manager.mark_dirty()
            else:
                self.log("Failed to update chat history")
                QMessageBox.critical(self, "Error", "Failed to update chat history.")
        except Exception as e:
            import traceback

            self.log(f"Error saving chat history: {e}")
            print(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Error saving chat history: {e}")
