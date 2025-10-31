"""
Dialog components for the CSV Translator application
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QGroupBox,
    QComboBox,
    QTabWidget,
    QWidget,
    QMessageBox,
    QInputDialog,
    QFormLayout,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from models.data_structures import ModelProvider


class APIKeyDialog(QDialog):
    """Dialog for setting up API keys for different providers"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Setup")
        self.setModal(True)
        self.resize(500, 300)

        self.setup_ui()

    def setup_ui(self):
        """Setup the API key dialog UI"""
        layout = QVBoxLayout(self)

        # Instructions
        info_label = QLabel(
            "Enter API keys for the AI providers you want to use. "
            "At least one API key is required for translation functionality."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Google AI
        google_group = QGroupBox("Google AI")
        google_layout = QFormLayout(google_group)

        self.google_key_edit = QLineEdit()
        self.google_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.google_key_edit.setPlaceholderText("Enter your Google AI API key...")
        google_layout.addRow("API Key:", self.google_key_edit)

        layout.addWidget(google_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def get_api_keys(self):
        """Get the entered API keys"""
        keys = {}
        google_key = self.google_key_edit.text().strip()
        if google_key:
            keys[ModelProvider.GOOGLE.value] = google_key
        return keys

    def set_api_keys(self, keys):
        """Set existing API keys"""
        if ModelProvider.GOOGLE.value in keys:
            self.google_key_edit.setText(keys[ModelProvider.GOOGLE.value])


class FindReplaceDialog(QDialog):
    """Dialog for find and replace functionality"""

    # Signals
    find_next_requested = pyqtSignal(
        str, bool, bool
    )  # text, case_sensitive, whole_words
    replace_requested = pyqtSignal(
        str, str, bool, bool, bool
    )  # find, replace, case, whole, selected_only
    replace_all_requested = pyqtSignal(str, str, bool, bool)  # old, new, case, whole

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find and Replace")
        self.setModal(False)
        self.resize(400, 250)

        self.setup_ui()

    def setup_ui(self):
        """Setup the find/replace dialog UI"""
        layout = QVBoxLayout(self)

        # Find section
        find_group = QGroupBox("Find")
        find_layout = QFormLayout(find_group)

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Enter text to find...")
        find_layout.addRow("Find:", self.find_edit)

        layout.addWidget(find_group)

        # Replace section
        replace_group = QGroupBox("Replace")
        replace_layout = QFormLayout(replace_group)

        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Enter replacement text...")
        replace_layout.addRow("Replace with:", self.replace_edit)

        layout.addWidget(replace_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.case_sensitive_check = QCheckBox("Case sensitive")
        options_layout.addWidget(self.case_sensitive_check)

        self.whole_words_check = QCheckBox("Whole words only")
        options_layout.addWidget(self.whole_words_check)

        self.selected_only_check = QCheckBox("Selected cells only")
        options_layout.addWidget(self.selected_only_check)

        layout.addWidget(options_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.find_next_btn = QPushButton("Find Next")
        self.find_next_btn.clicked.connect(self.find_next)
        button_layout.addWidget(self.find_next_btn)

        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace_current)
        button_layout.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all)
        button_layout.addWidget(self.replace_all_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # Connect Enter key to find
        self.find_edit.returnPressed.connect(self.find_next)
        self.replace_edit.returnPressed.connect(self.find_next)

    def find_next(self):
        """Find next occurrence"""
        text = self.find_edit.text()
        if text:
            self.find_next_requested.emit(
                text,
                self.case_sensitive_check.isChecked(),
                self.whole_words_check.isChecked(),
            )

    def replace_current(self):
        """Replace current occurrence"""
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()

        if find_text:
            self.replace_requested.emit(
                find_text,
                replace_text,
                self.case_sensitive_check.isChecked(),
                self.whole_words_check.isChecked(),
                self.selected_only_check.isChecked(),
            )

    def replace_all(self):
        """Replace all occurrences"""
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()

        if find_text:
            reply = QMessageBox.question(
                self,
                "Replace All",
                f"Replace all occurrences of '{find_text}' with '{replace_text}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.replace_all_requested.emit(
                    find_text,
                    replace_text,
                    self.case_sensitive_check.isChecked(),
                    self.whole_words_check.isChecked(),
                )

    def set_find_text(self, text: str):
        """Set the find text"""
        self.find_edit.setText(text)
        self.find_edit.selectAll()


class TranslationSettingsDialog(QDialog):
    """Dialog for translation settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Translation Settings")
        self.setModal(True)
        self.resize(400, 300)

        self.setup_ui()

    def setup_ui(self):
        """Setup the translation settings UI"""
        layout = QVBoxLayout(self)

        # Model Settings
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout(model_group)

        self.model_combo = QComboBox()
        model_layout.addRow("AI Model:", self.model_combo)

        self.chunk_size_spinbox = QSpinBox()
        self.chunk_size_spinbox.setRange(10, 500)
        self.chunk_size_spinbox.setValue(100)
        self.chunk_size_spinbox.setSuffix(" lines")
        model_layout.addRow("Chunk Size:", self.chunk_size_spinbox)

        self.sleep_time_spinbox = QSpinBox()
        self.sleep_time_spinbox.setRange(1, 300)
        self.sleep_time_spinbox.setValue(10)
        self.sleep_time_spinbox.setSuffix(" seconds")
        model_layout.addRow("Sleep Time:", self.sleep_time_spinbox)

        layout.addWidget(model_group)

        # Translation Type
        type_group = QGroupBox("Translation Type")
        type_layout = QVBoxLayout(type_group)

        self.visual_novel_radio = QCheckBox("Visual Novel Mode")
        self.visual_novel_radio.setChecked(True)
        self.visual_novel_radio.setToolTip(
            "Use specialized prompts for visual novel translation"
        )
        type_layout.addWidget(self.visual_novel_radio)

        self.general_radio = QCheckBox("General Translation")
        self.general_radio.setToolTip("Use general translation prompts")
        type_layout.addWidget(self.general_radio)

        layout.addWidget(type_group)

        # Auto-features
        auto_group = QGroupBox("Automatic Features")
        auto_layout = QVBoxLayout(auto_group)

        self.auto_save_check = QCheckBox("Auto-save after translation")
        self.auto_save_check.setChecked(True)
        auto_layout.addWidget(self.auto_save_check)

        self.auto_summarize_check = QCheckBox("Auto-summarize history")
        self.auto_summarize_check.setChecked(True)
        auto_layout.addWidget(self.auto_summarize_check)

        layout.addWidget(auto_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)


class HistoryViewDialog(QDialog):
    """Dialog for viewing translation history"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Translation History")
        self.resize(800, 600)

        self.setup_ui()

    def setup_ui(self):
        """Setup the history view UI"""
        layout = QVBoxLayout(self)

        # Create splitter for history list and content
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # History list
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self.on_history_selected)
        splitter.addWidget(self.history_list)

        # Content view
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setFont(QFont("Consolas", 10))
        content_layout.addWidget(self.content_text)

        splitter.addWidget(content_widget)

        # Set splitter proportions
        splitter.setSizes([200, 600])

        # Buttons
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.clicked.connect(self.clear_history)
        button_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton("Export History")
        self.export_btn.clicked.connect(self.export_history)
        button_layout.addWidget(self.export_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def load_history(self, history_entries):
        """Load history entries into the list"""
        self.history_list.clear()
        self.history_entries = history_entries

        for i, entry in enumerate(history_entries):
            item_text = f"{entry.role.title()} - {entry.timestamp}"
            if entry.model_name:
                item_text += f" ({entry.model_name})"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, i)
            self.history_list.addItem(item)

    def on_history_selected(self, current, previous):
        """Handle history item selection"""
        if current:
            index = current.data(Qt.UserRole)
            if 0 <= index < len(self.history_entries):
                entry = self.history_entries[index]
                content = "\n".join(entry.parts)
                self.content_text.setPlainText(content)

    def clear_history(self):
        """Clear history with confirmation"""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all translation history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.history_list.clear()
            self.content_text.clear()
            # Signal to parent to clear actual history
            self.parent().clear_translation_history()

    def export_history(self):
        """Export history to file"""
        # TODO: Implement history export
        QMessageBox.information(
            self, "Export", "History export functionality coming soon!"
        )


class ContextFileSelectionDialog(QDialog):
    """Dialog để chọn files cho context"""

    def __init__(self, parent=None, available_files: list = None):
        super().__init__(parent)
        self.setWindowTitle("Select Context Files")
        self.setMinimumSize(600, 500)
        self.available_files = available_files or []
        self.setup_ui()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Instructions
        info_label = QLabel(
            "Select CSV files to use as context. The AI will use translations "
            "from these files to understand the context better."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # File selection
        files_group = QGroupBox("Available Files")
        files_layout = QVBoxLayout()

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        # Load available files from parent's app state
        self.load_available_files()

        files_layout.addWidget(self.file_list)

        # Quick selection buttons
        quick_btn_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)

        quick_btn_layout.addWidget(select_all_btn)
        quick_btn_layout.addWidget(deselect_all_btn)
        quick_btn_layout.addStretch()

        files_layout.addLayout(quick_btn_layout)
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)

        # Context configuration
        config_group = QGroupBox("Context Configuration")
        config_layout = QFormLayout()

        self.source_column_combo = QComboBox()
        self.source_column_combo.addItems(["original text", "Original Text", "Text"])
        self.source_column_combo.setEditable(True)

        self.translation_column_combo = QComboBox()
        self.translation_column_combo.addItems(["Initial", "Machine translation", "Translation"])
        self.translation_column_combo.setEditable(True)

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(10, 500)
        self.chunk_size_spin.setValue(50)

        self.max_chunks_spin = QSpinBox()
        self.max_chunks_spin.setRange(1, 50)
        self.max_chunks_spin.setValue(10)

        self.only_translated_check = QCheckBox("Only include rows with translations")
        self.only_translated_check.setChecked(True)

        config_layout.addRow("Source Column:", self.source_column_combo)
        config_layout.addRow("Translation Column:", self.translation_column_combo)
        config_layout.addRow("Chunk Size:", self.chunk_size_spin)
        config_layout.addRow("Max Context Chunks:", self.max_chunks_spin)
        config_layout.addRow("", self.only_translated_check)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def load_available_files(self):
        """Load available files from parent window"""
        self.file_list.clear()

        # Try to get files from parent's app state
        parent_window = self.window()
        if hasattr(parent_window, 'app_state') and parent_window.app_state.csv_files:
            files = parent_window.app_state.csv_files
            for file_path in files:
                from pathlib import Path
                file_name = Path(file_path).name if hasattr(file_path, '__fspath__') or isinstance(file_path, str) else str(file_path)
                item = QListWidgetItem(file_name)
                item.setData(Qt.ItemDataRole.UserRole, str(file_path))
                self.file_list.addItem(item)
        elif self.available_files:
            # Use provided files
            for file_path in self.available_files:
                from pathlib import Path
                file_name = Path(file_path).name
                item = QListWidgetItem(file_name)
                item.setData(Qt.ItemDataRole.UserRole, str(file_path))
                self.file_list.addItem(item)
        else:
            # No files available
            item = QListWidgetItem("No files available")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.file_list.addItem(item)

    def select_all(self):
        """Select all files"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsSelectable:
                item.setSelected(True)

    def deselect_all(self):
        """Deselect all files"""
        self.file_list.clearSelection()

    def get_selection(self):
        """Get selected files and configuration"""
        selected_files = []
        for item in self.file_list.selectedItems():
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path:
                selected_files.append(file_path)

        config = {
            'source_column': self.source_column_combo.currentText(),
            'translation_column': self.translation_column_combo.currentText(),
            'chunk_size': self.chunk_size_spin.value(),
            'max_context_chunks': self.max_chunks_spin.value(),
            'only_translated_rows': self.only_translated_check.isChecked()
        }

        return selected_files, config
