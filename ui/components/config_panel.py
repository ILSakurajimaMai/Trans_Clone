"""
Configuration panel for the CSV Translator application
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QDoubleSpinBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QGridLayout,
    QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from config.settings import AppSettings
from models.data_structures import ModelProvider, CustomModel


class CustomModelDialog(QDialog):
    """Dialog for adding/editing custom models"""

    def __init__(self, model: CustomModel = None, parent=None):
        super().__init__(parent)
        self.model = model
        self.setup_ui()

        if model:
            self.load_model_data()

    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Custom Model Configuration")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Provider
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(
            [provider.value.title() for provider in ModelProvider]
        )
        form_layout.addRow("Provider:", self.provider_combo)

        # Model name
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("e.g., gpt-4-turbo, claude-3-opus")
        form_layout.addRow("Model Name:", self.model_name_edit)

        # Display name
        self.display_name_edit = QLineEdit()
        self.display_name_edit.setPlaceholderText("Optional display name")
        form_layout.addRow("Display Name:", self.display_name_edit)

        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        form_layout.addRow("Temperature:", self.temperature_spin)

        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 32000)
        self.max_tokens_spin.setValue(4096)
        form_layout.addRow("Max Tokens:", self.max_tokens_spin)

        # Active checkbox
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)
        form_layout.addRow("", self.active_checkbox)

        layout.addLayout(form_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_model_data(self):
        """Load existing model data"""
        if self.model:
            # Set provider
            provider_index = list(ModelProvider).index(self.model.provider)
            self.provider_combo.setCurrentIndex(provider_index)

            self.model_name_edit.setText(self.model.model_name)
            self.display_name_edit.setText(self.model.display_name)
            self.temperature_spin.setValue(self.model.temperature)
            self.max_tokens_spin.setValue(self.model.max_tokens)
            self.active_checkbox.setChecked(self.model.is_active)

    def get_model(self) -> CustomModel:
        """Get the configured model"""
        provider = list(ModelProvider)[self.provider_combo.currentIndex()]

        return CustomModel(
            provider=provider,
            model_name=self.model_name_edit.text().strip(),
            display_name=self.display_name_edit.text().strip(),
            temperature=self.temperature_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
            is_active=self.active_checkbox.isChecked(),
        )


class ConfigPanel(QWidget):
    """Configuration panel for directories and settings"""

    # Signals
    input_directory_changed = pyqtSignal(str)
    output_directory_changed = pyqtSignal(str)
    history_file_changed = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    target_column_changed = pyqtSignal(str)
    sleep_time_changed = pyqtSignal(int)
    chunk_size_changed = pyqtSignal(int)
    load_files_requested = pyqtSignal()
    custom_model_added = pyqtSignal(CustomModel)
    custom_model_removed = pyqtSignal(str)  # model name

    def __init__(self):
        super().__init__()
        self.custom_models = []
        self.setup_ui()

    def setup_ui(self):
        """Setup the configuration panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Main configuration in a grid for compact layout
        main_group = QGroupBox("Configuration")
        main_layout = QGridLayout(main_group)
        main_layout.setSpacing(5)

        # Row 1: Input directory
        main_layout.addWidget(QLabel("Input Dir:"), 0, 0)
        self.input_dir_edit = QLineEdit()
        self.input_dir_edit.setPlaceholderText("CSV files folder...")
        main_layout.addWidget(self.input_dir_edit, 0, 1)

        self.browse_input_btn = QPushButton("📁")
        self.browse_input_btn.setMaximumWidth(35)
        self.browse_input_btn.clicked.connect(self.browse_input_dir)
        main_layout.addWidget(self.browse_input_btn, 0, 2)

        # Row 2: Output directory
        main_layout.addWidget(QLabel("Output Dir:"), 1, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Output folder...")
        main_layout.addWidget(self.output_dir_edit, 1, 1)

        self.browse_output_btn = QPushButton("📁")
        self.browse_output_btn.setMaximumWidth(35)
        self.browse_output_btn.clicked.connect(self.browse_output_dir)
        main_layout.addWidget(self.browse_output_btn, 1, 2)

        # Row 3: History file
        main_layout.addWidget(QLabel("History:"), 2, 0)
        self.history_file_edit = QLineEdit()
        self.history_file_edit.setPlaceholderText("History JSON file...")
        main_layout.addWidget(self.history_file_edit, 2, 1)

        self.browse_history_btn = QPushButton("📁")
        self.browse_history_btn.setMaximumWidth(35)
        self.browse_history_btn.clicked.connect(self.browse_history_file)
        main_layout.addWidget(self.browse_history_btn, 2, 2)

        layout.addWidget(main_group)

        # AI Settings in compact layout
        ai_group = QGroupBox("AI Settings")
        ai_layout = QGridLayout(ai_group)
        ai_layout.setSpacing(5)

        # Row 1: Model and Target Column
        ai_layout.addWidget(QLabel("Model:"), 0, 0)
        self.model_combo = QComboBox()
        self._populate_model_combo()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        ai_layout.addWidget(self.model_combo, 0, 1)

        self.custom_model_btn = QPushButton("⚙️")
        self.custom_model_btn.setMaximumWidth(35)
        self.custom_model_btn.setToolTip("Manage Custom Models")
        self.custom_model_btn.clicked.connect(self.manage_custom_models)
        ai_layout.addWidget(self.custom_model_btn, 0, 2)

        ai_layout.addWidget(QLabel("Target:"), 0, 3)
        self.target_column_combo = QComboBox()
        self.target_column_combo.addItems(AppSettings.CSV_TARGET_COLUMNS)
        self.target_column_combo.setCurrentText(AppSettings.DEFAULT_TARGET_COLUMN)
        self.target_column_combo.currentTextChanged.connect(
            self.on_target_column_changed
        )
        ai_layout.addWidget(self.target_column_combo, 0, 4)

        # Row 2: Sleep time and Chunk size
        ai_layout.addWidget(QLabel("Sleep(s):"), 1, 0)
        self.sleep_time_spin = QSpinBox()
        self.sleep_time_spin.setRange(1, 60)
        self.sleep_time_spin.setValue(AppSettings.DEFAULT_SLEEP_TIME)
        self.sleep_time_spin.valueChanged.connect(self.on_sleep_time_changed)
        ai_layout.addWidget(self.sleep_time_spin, 1, 1)

        ai_layout.addWidget(QLabel("Chunk:"), 1, 3)
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1, 100)
        self.chunk_size_spin.setValue(AppSettings.DEFAULT_CHUNK_SIZE)
        self.chunk_size_spin.valueChanged.connect(self.on_chunk_size_changed)
        ai_layout.addWidget(self.chunk_size_spin, 1, 4)

        layout.addWidget(ai_group)

        # Load files button - prominent
        self.load_files_btn = QPushButton("📂 Load Files")
        self.load_files_btn.setFont(QFont("", 10, QFont.Weight.Bold))
        self.load_files_btn.setMinimumHeight(35)
        self.load_files_btn.clicked.connect(self.on_load_files)
        layout.addWidget(self.load_files_btn)

        # Connect change signals
        self.input_dir_edit.textChanged.connect(
            lambda text: self.input_directory_changed.emit(text)
        )
        self.output_dir_edit.textChanged.connect(
            lambda text: self.output_directory_changed.emit(text)
        )
        self.history_file_edit.textChanged.connect(
            lambda text: self.history_file_changed.emit(text)
        )

    def _populate_model_combo(self):
        """Populate model combo with all available models from settings"""
        self.model_combo.clear()

        # Add models by provider from settings
        for provider, models in AppSettings.CUSTOM_MODELS.items():
            for model in models:
                display_name = f"{provider.title()}: {model}"
                self.model_combo.addItem(display_name)

        # Set default selection
        if AppSettings.DEFAULT_AI_MODEL:
            # Find the default model in the combo
            for i in range(self.model_combo.count()):
                item_text = self.model_combo.itemText(i)
                if AppSettings.DEFAULT_AI_MODEL in item_text:
                    self.model_combo.setCurrentIndex(i)
                    break

    def browse_input_dir(self):
        """Browse for input directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Input Directory", self.input_dir_edit.text()
        )
        if directory:
            self.input_dir_edit.setText(directory)

    def browse_output_dir(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def browse_history_file(self):
        """Browse for history file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select History File",
            self.history_file_edit.text(),
            "JSON Files (*.json)",
        )
        if file_path:
            self.history_file_edit.setText(file_path)

    def manage_custom_models(self):
        """Open custom models management dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Custom Models")
        dialog.setModal(True)
        dialog.resize(500, 400)

        layout = QVBoxLayout(dialog)

        # Model list
        self.model_list = QListWidget()
        self.refresh_model_list()
        layout.addWidget(QLabel("Custom Models:"))
        layout.addWidget(self.model_list)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("Add Model")
        add_btn.clicked.connect(self.add_custom_model)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Model")
        edit_btn.clicked.connect(self.edit_custom_model)
        button_layout.addWidget(edit_btn)

        remove_btn = QPushButton("Remove Model")
        remove_btn.clicked.connect(self.remove_custom_model)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def refresh_model_list(self):
        """Refresh the custom models list"""
        self.model_list.clear()
        for model in self.custom_models:
            display_text = f"{model.provider.value.title()}: {model.display_name or model.model_name}"
            if not model.is_active:
                display_text += " (Inactive)"

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, model)
            self.model_list.addItem(item)

    def add_custom_model(self):
        """Add a new custom model"""
        dialog = CustomModelDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            model = dialog.get_model()
            if model.model_name:  # Validate required field
                self.custom_models.append(model)
                self.refresh_model_list()
                self.update_model_combo()
                self.custom_model_added.emit(model)

    def edit_custom_model(self):
        """Edit selected custom model"""
        current_item = self.model_list.currentItem()
        if current_item:
            model = current_item.data(Qt.ItemDataRole.UserRole)
            dialog = CustomModelDialog(model, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_model = dialog.get_model()
                if updated_model.model_name:
                    # Update the model in the list
                    index = self.custom_models.index(model)
                    self.custom_models[index] = updated_model
                    self.refresh_model_list()
                    self.update_model_combo()

    def remove_custom_model(self):
        """Remove selected custom model"""
        current_item = self.model_list.currentItem()
        if current_item:
            model = current_item.data(Qt.ItemDataRole.UserRole)
            self.custom_models.remove(model)
            self.refresh_model_list()
            self.update_model_combo()
            self.custom_model_removed.emit(model.model_name)

    def update_model_combo(self):
        """Update the model combo box with all models"""
        current_text = self.model_combo.currentText()
        self.model_combo.clear()

        # Add models from settings by provider
        for provider, models in AppSettings.CUSTOM_MODELS.items():
            for model in models:
                display_name = f"{provider.title()}: {model}"
                self.model_combo.addItem(display_name)

        # Add user custom models
        for model in self.custom_models:
            if model.is_active:
                display_name = model.display_name or model.model_name
                self.model_combo.addItem(
                    f"{model.provider.value.title()}: {display_name}"
                )

        # Try to restore previous selection
        index = self.model_combo.findText(current_text)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
            # Set default if no previous selection found
            if AppSettings.DEFAULT_AI_MODEL:
                for i in range(self.model_combo.count()):
                    item_text = self.model_combo.itemText(i)
                    if AppSettings.DEFAULT_AI_MODEL in item_text:
                        self.model_combo.setCurrentIndex(i)
                        break

    def on_model_changed(self, model_name: str):
        """Handle model change"""
        self.model_changed.emit(model_name)

    def on_target_column_changed(self, column: str):
        """Handle target column change"""
        self.target_column_changed.emit(column)

    def on_sleep_time_changed(self, value: int):
        """Handle sleep time change"""
        self.sleep_time_changed.emit(value)

    def on_chunk_size_changed(self, value: int):
        """Handle chunk size change"""
        self.chunk_size_changed.emit(value)

    def on_load_files(self):
        """Handle load files button click"""
        self.load_files_requested.emit()

    def get_input_directory(self) -> str:
        """Get the input directory"""
        return self.input_dir_edit.text()

    def get_output_directory(self) -> str:
        """Get the output directory"""
        return self.output_dir_edit.text()

    def get_history_file(self) -> str:
        """Get the history file path"""
        return self.history_file_edit.text()

    def get_current_model(self) -> str:
        """Get the current model"""
        return self.model_combo.currentText()

    def get_target_column(self) -> str:
        """Get the target column"""
        return self.target_column_combo.currentText()

    def get_sleep_time(self) -> int:
        """Get the sleep time"""
        return self.sleep_time_spin.value()

    def get_chunk_size(self) -> int:
        """Get the chunk size"""
        return self.chunk_size_spin.value()

    def set_input_directory(self, directory: str):
        """Set the input directory"""
        self.input_dir_edit.setText(directory)

    def set_output_directory(self, directory: str):
        """Set the output directory"""
        self.output_dir_edit.setText(directory)

    def set_history_file(self, file_path: str):
        """Set the history file path"""
        self.history_file_edit.setText(file_path)

    def set_current_model(self, model_name: str):
        """Set the current model"""
        index = self.model_combo.findText(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

    def set_target_column(self, column: str):
        """Set the target column"""
        index = self.target_column_combo.findText(column)
        if index >= 0:
            self.target_column_combo.setCurrentIndex(index)
