"""
Action panel with navigation and translation controls
"""

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QSpacerItem,
    QFrame,
    QToolButton,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon


class ActionPanel(QWidget):
    """Action panel with file navigation and translation controls"""

    # Signals
    previous_file_requested = pyqtSignal()
    next_file_requested = pyqtSignal()
    translate_current_requested = pyqtSignal()
    save_changes_requested = pyqtSignal()
    auto_translate_requested = pyqtSignal()
    summarize_history_requested = pyqtSignal()
    save_chat_history_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the action panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Top row: File info and navigation
        top_layout = QHBoxLayout()

        # File Info Label - prominent
        self.file_info_label = QLabel("No file loaded")
        self.file_info_label.setStyleSheet(
            "font-weight: bold; color: #333; font-size: 12px;"
        )
        top_layout.addWidget(self.file_info_label)

        top_layout.addStretch()

        # File Navigation - compact
        nav_frame = QFrame()
        nav_frame.setFrameShape(QFrame.Shape.StyledPanel)
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(5, 2, 5, 2)

        self.prev_btn = QToolButton()
        self.prev_btn.setText("⬅")
        self.prev_btn.setToolTip("Previous file")
        self.prev_btn.clicked.connect(self.previous_file_requested.emit)
        self.prev_btn.setMaximumSize(30, 25)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QToolButton()
        self.next_btn.setText("➡")
        self.next_btn.setToolTip("Next file")
        self.next_btn.clicked.connect(self.next_file_requested.emit)
        self.next_btn.setMaximumSize(30, 25)
        nav_layout.addWidget(self.next_btn)

        top_layout.addWidget(nav_frame)
        layout.addLayout(top_layout)

        # Bottom row: Main action buttons
        action_layout = QHBoxLayout()

        # Primary actions - bigger buttons
        self.translate_btn = QPushButton("🔄 Translate")
        self.translate_btn.setToolTip("Translate current file")
        self.translate_btn.clicked.connect(self.translate_current_requested.emit)
        self.translate_btn.setMinimumHeight(35)
        self.translate_btn.setStyleSheet("font-weight: bold; font-size: 11px;")
        action_layout.addWidget(self.translate_btn)

        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setToolTip("Save changes")
        self.save_btn.clicked.connect(self.save_changes_requested.emit)
        self.save_btn.setMinimumHeight(35)
        action_layout.addWidget(self.save_btn)

        action_layout.addStretch()

        # Secondary actions - smaller buttons
        self.auto_translate_btn = QPushButton("⚡ Auto All")
        self.auto_translate_btn.setToolTip("Auto translate all files")
        self.auto_translate_btn.clicked.connect(self.auto_translate_requested.emit)
        self.auto_translate_btn.setMaximumHeight(30)
        action_layout.addWidget(self.auto_translate_btn)

        self.summarize_btn = QPushButton("📊 Summary")
        self.summarize_btn.setToolTip("Summarize history")
        self.summarize_btn.clicked.connect(self.summarize_history_requested.emit)
        self.summarize_btn.setMaximumHeight(30)
        action_layout.addWidget(self.summarize_btn)

        # New button: Save chat history
        self.save_chat_btn = QPushButton("💬 Save Chat")
        self.save_chat_btn.setToolTip("Save chat history for current file")
        self.save_chat_btn.clicked.connect(self.save_chat_history_requested.emit)
        self.save_chat_btn.setMaximumHeight(30)
        action_layout.addWidget(self.save_chat_btn)

        layout.addLayout(action_layout)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        layout.addWidget(self.progress_bar)

        # Set initial button states
        self.update_navigation_buttons(False, False)
        self.update_action_buttons(False)

    def update_file_info(
        self, current_index: int, total_files: int, filename: str = ""
    ):
        """Update file information display"""
        if total_files == 0:
            self.file_info_label.setText("📂 No files loaded")
        else:
            display_name = filename if filename else f"File {current_index + 1}"
            self.file_info_label.setText(
                f"📄 {display_name} ({current_index + 1}/{total_files})"
            )

    def update_navigation_buttons(self, can_go_prev: bool, can_go_next: bool):
        """Update navigation button states"""
        self.prev_btn.setEnabled(can_go_prev)
        self.next_btn.setEnabled(can_go_next)

    def update_action_buttons(self, has_data: bool):
        """Update action button states based on data availability"""
        self.translate_btn.setEnabled(has_data)
        self.save_btn.setEnabled(has_data)
        self.auto_translate_btn.setEnabled(has_data)
        self.save_chat_btn.setEnabled(has_data)

    def set_translation_in_progress(self, in_progress: bool):
        """Set UI state for translation in progress"""
        # Disable buttons during translation
        self.translate_btn.setEnabled(not in_progress)
        self.auto_translate_btn.setEnabled(not in_progress)
        self.prev_btn.setEnabled(not in_progress)
        self.next_btn.setEnabled(not in_progress)

        # Update button text
        if in_progress:
            self.translate_btn.setText("⏳ Translating...")
            self.auto_translate_btn.setText("⏳ Processing...")
        else:
            self.translate_btn.setText("🔄 Translate")
            self.auto_translate_btn.setText("⚡ Auto All")

    def show_progress(self, show: bool = True):
        """Show or hide progress bar"""
        self.progress_bar.setVisible(show)
        if not show:
            self.progress_bar.setValue(0)

    def hide_progress(self):
        """Hide progress bar"""
        self.show_progress(False)

    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress bar"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

            if message:
                self.progress_bar.setFormat(f"{message} ({current}/{total}) - %p%")
            else:
                self.progress_bar.setFormat(f"({current}/{total}) - %p%")

    def set_auto_translate_enabled(self, enabled: bool):
        """Enable or disable auto translate button"""
        self.auto_translate_btn.setEnabled(enabled)

    def set_summarize_enabled(self, enabled: bool):
        """Enable or disable summarize button"""
        self.summarize_btn.setEnabled(enabled)


class ExtendedActionPanel(ActionPanel):
    """Extended action panel with additional controls"""

    # Additional signals
    find_requested = pyqtSignal()
    replace_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    toggle_theme_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_extended_controls()

    def add_extended_controls(self):
        """Add extended controls to the action panel"""
        # Get the bottom action layout to add more controls
        bottom_layout = self.layout().itemAt(1).layout()  # action_layout

        # Add edit controls before the stretch
        edit_frame = QFrame()
        edit_frame.setFrameShape(QFrame.Shape.StyledPanel)
        edit_layout = QHBoxLayout(edit_frame)
        edit_layout.setContentsMargins(3, 2, 3, 2)

        self.undo_btn = QToolButton()
        self.undo_btn.setText("↶")
        self.undo_btn.setToolTip("Undo (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.undo_requested.emit)
        self.undo_btn.setMaximumSize(25, 25)
        self.undo_btn.setEnabled(False)
        edit_layout.addWidget(self.undo_btn)

        self.redo_btn = QToolButton()
        self.redo_btn.setText("↷")
        self.redo_btn.setToolTip("Redo (Ctrl+Y)")
        self.redo_btn.clicked.connect(self.redo_requested.emit)
        self.redo_btn.setMaximumSize(25, 25)
        self.redo_btn.setEnabled(False)
        edit_layout.addWidget(self.redo_btn)

        self.find_btn = QToolButton()
        self.find_btn.setText("🔍")
        self.find_btn.setToolTip("Find/Replace (Ctrl+F)")
        self.find_btn.clicked.connect(self.find_requested.emit)
        self.find_btn.setMaximumSize(25, 25)
        edit_layout.addWidget(self.find_btn)

        # Insert before the stretch (which is at index 2)
        bottom_layout.insertWidget(2, edit_frame)

        # Theme toggle at the end
        self.theme_btn = QToolButton()
        self.theme_btn.setText("🌙")
        self.theme_btn.setToolTip("Toggle theme")
        self.theme_btn.clicked.connect(self.toggle_theme_requested.emit)
        self.theme_btn.setMaximumSize(25, 25)
        bottom_layout.addWidget(self.theme_btn)

    def update_undo_redo_states(
        self,
        can_undo: bool,
        can_redo: bool,
        undo_description: str = "",
        redo_description: str = "",
    ):
        """Update undo/redo button states"""
        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)

        # Update tooltips with descriptions
        if can_undo and undo_description:
            self.undo_btn.setToolTip(f"Undo: {undo_description} (Ctrl+Z)")
        else:
            self.undo_btn.setToolTip("Undo (Ctrl+Z)")

        if can_redo and redo_description:
            self.redo_btn.setToolTip(f"Redo: {redo_description} (Ctrl+Y)")
        else:
            self.redo_btn.setToolTip("Redo (Ctrl+Y)")

    def update_theme_button(self, is_dark_theme: bool):
        """Update theme button appearance"""
        if is_dark_theme:
            self.theme_btn.setText("☀️")
            self.theme_btn.setToolTip("Switch to light theme")
        else:
            self.theme_btn.setText("🌙")
            self.theme_btn.setToolTip("Switch to dark theme")
