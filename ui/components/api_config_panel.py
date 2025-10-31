"""
API Configuration Panel - Tab để quản lý API services và keys
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QMessageBox, QDialog, QFormLayout, QCheckBox, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import Dict, List, Optional

from core.api_service_manager import APIServiceManager
from models.api_models import (
    APIServiceConfig, APIProviderType, AuthType,
    APIEndpointConfig, RequestFormat, ResponseFormat
)


class APIServiceDialog(QDialog):
    """Dialog để thêm/sửa API service"""

    def __init__(self, parent=None, service: Optional[APIServiceConfig] = None):
        super().__init__(parent)
        self.service = service
        self.is_edit = service is not None
        self.setup_ui()

        if service:
            self.load_service_data(service)

    def setup_ui(self):
        """Setup UI"""
        self.setWindowTitle("Add Custom API Service" if not self.is_edit else "Edit API Service")
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)

        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.id_edit = QLineEdit()
        self.id_edit.setEnabled(not self.is_edit)  # ID không thể sửa
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)

        basic_layout.addRow("Service Name:", self.name_edit)
        basic_layout.addRow("Service ID:", self.id_edit)
        basic_layout.addRow("Description:", self.description_edit)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Provider
        provider_group = QGroupBox("Provider Configuration")
        provider_layout = QFormLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems([p.value for p in APIProviderType])

        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("e.g., gemini-2.0-flash-exp")

        provider_layout.addRow("Provider Type:", self.provider_combo)
        provider_layout.addRow("Model Name:", self.model_name_edit)

        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Authentication
        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout()

        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems([a.value for a in AuthType])

        self.api_key_header_edit = QLineEdit()
        self.api_key_header_edit.setText("Authorization")

        self.api_key_prefix_edit = QLineEdit()
        self.api_key_prefix_edit.setText("Bearer")

        auth_layout.addRow("Auth Type:", self.auth_type_combo)
        auth_layout.addRow("API Key Header:", self.api_key_header_edit)
        auth_layout.addRow("API Key Prefix:", self.api_key_prefix_edit)

        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)

        # Endpoint
        endpoint_group = QGroupBox("API Endpoint")
        endpoint_layout = QFormLayout()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://api.example.com/v1/chat/completions")

        self.method_combo = QComboBox()
        self.method_combo.addItems(["POST", "GET", "PUT"])

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)

        endpoint_layout.addRow("URL:", self.url_edit)
        endpoint_layout.addRow("Method:", self.method_combo)
        endpoint_layout.addRow("Timeout (s):", self.timeout_spin)

        endpoint_group.setLayout(endpoint_layout)
        layout.addWidget(endpoint_group)

        # Model parameters
        params_group = QGroupBox("Model Parameters")
        params_layout = QFormLayout()

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setSingleStep(0.1)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 32768)
        self.max_tokens_spin.setValue(4096)
        self.max_tokens_spin.setSingleStep(256)

        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setValue(0.95)
        self.top_p_spin.setSingleStep(0.05)

        params_layout.addRow("Temperature:", self.temperature_spin)
        params_layout.addRow("Max Tokens:", self.max_tokens_spin)
        params_layout.addRow("Top P:", self.top_p_spin)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Response format
        response_group = QGroupBox("Response Format")
        response_layout = QFormLayout()

        self.text_path_edit = QLineEdit()
        self.text_path_edit.setPlaceholderText("choices.0.message.content")

        self.usage_path_edit = QLineEdit()
        self.usage_path_edit.setPlaceholderText("usage")

        response_layout.addRow("Text Path:", self.text_path_edit)
        response_layout.addRow("Usage Path:", self.usage_path_edit)

        response_group.setLayout(response_layout)
        layout.addWidget(response_group)

        # Active checkbox
        self.active_check = QCheckBox("Active")
        self.active_check.setChecked(True)
        layout.addWidget(self.active_check)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def load_service_data(self, service: APIServiceConfig):
        """Load service data vào form"""
        self.name_edit.setText(service.name)
        self.id_edit.setText(service.id)
        self.description_edit.setPlainText(service.description)

        # Provider
        self.provider_combo.setCurrentText(service.provider_type.value)
        self.model_name_edit.setText(service.model_name)

        # Auth
        self.auth_type_combo.setCurrentText(service.auth_type.value)
        self.api_key_header_edit.setText(service.api_key_header_name)
        self.api_key_prefix_edit.setText(service.api_key_prefix)

        # Endpoint
        self.url_edit.setText(service.endpoint.url)
        self.method_combo.setCurrentText(service.endpoint.method)
        self.timeout_spin.setValue(service.endpoint.timeout)

        # Parameters
        self.temperature_spin.setValue(service.temperature)
        self.max_tokens_spin.setValue(service.max_tokens)
        self.top_p_spin.setValue(service.top_p)

        # Response
        self.text_path_edit.setText(service.response_format.text_path)
        if service.response_format.usage_path:
            self.usage_path_edit.setText(service.response_format.usage_path)

        self.active_check.setChecked(service.is_active)

    def get_service_config(self) -> APIServiceConfig:
        """Get service config từ form"""
        # Basic endpoint
        endpoint = APIEndpointConfig(
            url=self.url_edit.text(),
            method=self.method_combo.currentText(),
            timeout=self.timeout_spin.value()
        )

        # Request format (basic template for chat)
        request_format = RequestFormat(
            body_template={
                "model": "{model}",
                "messages": [],
                "temperature": "{temperature}",
                "max_tokens": "{max_tokens}"
            }
        )

        # Response format
        response_format = ResponseFormat(
            text_path=self.text_path_edit.text(),
            usage_path=self.usage_path_edit.text() or None
        )

        # Create config
        config = APIServiceConfig(
            id=self.id_edit.text(),
            name=self.name_edit.text(),
            provider_type=APIProviderType(self.provider_combo.currentText()),
            description=self.description_edit.toPlainText(),
            auth_type=AuthType(self.auth_type_combo.currentText()),
            api_key_header_name=self.api_key_header_edit.text(),
            api_key_prefix=self.api_key_prefix_edit.text(),
            endpoint=endpoint,
            request_format=request_format,
            response_format=response_format,
            model_name=self.model_name_edit.text(),
            temperature=self.temperature_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
            top_p=self.top_p_spin.value(),
            is_active=self.active_check.isChecked(),
            is_custom=True
        )

        return config


class APIConfigPanel(QWidget):
    """Panel để quản lý API services và keys"""

    service_changed = pyqtSignal(str)  # service_id
    api_key_changed = pyqtSignal(str, str)  # service_id, api_key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_manager = APIServiceManager()
        self.setup_ui()
        self.load_services()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("<h3>API Services Configuration</h3>")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Services table
        services_group = QGroupBox("API Services")
        services_layout = QVBoxLayout()

        self.services_table = QTableWidget()
        self.services_table.setColumnCount(6)
        self.services_table.setHorizontalHeaderLabels([
            "Name", "Provider", "Model", "Status", "Has Key", "Actions"
        ])
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.services_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.services_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        services_layout.addWidget(self.services_table)

        # Service buttons
        service_btn_layout = QHBoxLayout()

        self.add_service_btn = QPushButton("➕ Add Custom Service")
        self.add_service_btn.clicked.connect(self.add_custom_service)

        self.edit_service_btn = QPushButton("✏️ Edit Service")
        self.edit_service_btn.clicked.connect(self.edit_selected_service)

        self.remove_service_btn = QPushButton("🗑️ Remove Service")
        self.remove_service_btn.clicked.connect(self.remove_selected_service)

        self.test_service_btn = QPushButton("🧪 Test Connection")
        self.test_service_btn.clicked.connect(self.test_selected_service)

        service_btn_layout.addWidget(self.add_service_btn)
        service_btn_layout.addWidget(self.edit_service_btn)
        service_btn_layout.addWidget(self.remove_service_btn)
        service_btn_layout.addWidget(self.test_service_btn)
        service_btn_layout.addStretch()

        services_layout.addLayout(service_btn_layout)
        services_group.setLayout(services_layout)
        layout.addWidget(services_group)

        # API Key section
        key_group = QGroupBox("API Key Management")
        key_layout = QVBoxLayout()

        key_form = QFormLayout()

        self.service_combo = QComboBox()
        self.service_combo.currentTextChanged.connect(self.on_service_selected)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter API key...")

        self.show_key_check = QCheckBox("Show key")
        self.show_key_check.toggled.connect(self.toggle_key_visibility)

        key_form.addRow("Select Service:", self.service_combo)
        key_form.addRow("API Key:", self.api_key_edit)
        key_form.addRow("", self.show_key_check)

        key_layout.addLayout(key_form)

        # Key buttons
        key_btn_layout = QHBoxLayout()
        key_btn_layout.addStretch()

        self.save_key_btn = QPushButton("💾 Save API Key")
        self.save_key_btn.clicked.connect(self.save_api_key)

        self.clear_key_btn = QPushButton("🗑️ Clear Key")
        self.clear_key_btn.clicked.connect(self.clear_api_key)

        key_btn_layout.addWidget(self.save_key_btn)
        key_btn_layout.addWidget(self.clear_key_btn)

        key_layout.addLayout(key_btn_layout)
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)

        layout.addStretch()

    def load_services(self):
        """Load services vào table"""
        services = self.api_manager.get_all_services()

        self.services_table.setRowCount(len(services))
        self.service_combo.clear()

        for i, service in enumerate(services):
            # Name
            self.services_table.setItem(i, 0, QTableWidgetItem(service.name))

            # Provider
            self.services_table.setItem(i, 1, QTableWidgetItem(service.provider_type.value))

            # Model
            self.services_table.setItem(i, 2, QTableWidgetItem(service.model_name))

            # Status
            status_item = QTableWidgetItem("🟢 Active" if service.is_active else "⚪ Inactive")
            self.services_table.setItem(i, 3, status_item)

            # Has key
            has_key = self.api_manager.has_api_key(service.id)
            key_item = QTableWidgetItem("✅ Yes" if has_key else "❌ No")
            self.services_table.setItem(i, 4, key_item)

            # Actions
            actions_item = QTableWidgetItem(service.id)  # Store service_id
            self.services_table.setItem(i, 5, actions_item)

            # Add to combo
            self.service_combo.addItem(service.name, service.id)

        # Select first service
        if self.service_combo.count() > 0:
            self.service_combo.setCurrentIndex(0)

    def on_service_selected(self, text):
        """Handle service selection"""
        service_id = self.service_combo.currentData()
        if service_id:
            # Load API key if exists
            api_key = self.api_manager.get_api_key(service_id)
            if api_key:
                self.api_key_edit.setText(api_key)
            else:
                self.api_key_edit.clear()

    def toggle_key_visibility(self, checked):
        """Toggle API key visibility"""
        if checked:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def save_api_key(self):
        """Save API key"""
        service_id = self.service_combo.currentData()
        api_key = self.api_key_edit.text().strip()

        if not service_id:
            QMessageBox.warning(self, "Warning", "Please select a service first.")
            return

        if not api_key:
            QMessageBox.warning(self, "Warning", "Please enter an API key.")
            return

        if self.api_manager.set_api_key(service_id, api_key):
            QMessageBox.information(self, "Success", "API key saved successfully!")
            self.api_key_changed.emit(service_id, api_key)
            self.load_services()  # Refresh table
        else:
            QMessageBox.critical(self, "Error", "Failed to save API key.")

    def clear_api_key(self):
        """Clear API key"""
        service_id = self.service_combo.currentData()
        if service_id:
            reply = QMessageBox.question(
                self, "Confirm",
                "Are you sure you want to clear this API key?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.api_manager.set_api_key(service_id, "")
                self.api_key_edit.clear()
                self.load_services()
                QMessageBox.information(self, "Success", "API key cleared.")

    def add_custom_service(self):
        """Add custom service"""
        dialog = APIServiceDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_service_config()
            if self.api_manager.add_service(config):
                QMessageBox.information(self, "Success", "Service added successfully!")
                self.load_services()
                self.service_changed.emit(config.id)
            else:
                QMessageBox.critical(self, "Error", "Failed to add service.")

    def edit_selected_service(self):
        """Edit selected service"""
        row = self.services_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a service to edit.")
            return

        service_id = self.services_table.item(row, 5).text()
        service = self.api_manager.get_service(service_id)

        if not service:
            QMessageBox.critical(self, "Error", "Service not found.")
            return

        if not service.is_custom:
            QMessageBox.warning(self, "Warning", "Cannot edit predefined services.")
            return

        dialog = APIServiceDialog(self, service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_service_config()
            if self.api_manager.add_service(config):
                QMessageBox.information(self, "Success", "Service updated successfully!")
                self.load_services()
                self.service_changed.emit(config.id)
            else:
                QMessageBox.critical(self, "Error", "Failed to update service.")

    def remove_selected_service(self):
        """Remove selected service"""
        row = self.services_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a service to remove.")
            return

        service_id = self.services_table.item(row, 5).text()
        service = self.api_manager.get_service(service_id)

        if not service:
            return

        if not service.is_custom:
            QMessageBox.warning(self, "Warning", "Cannot remove predefined services.")
            return

        reply = QMessageBox.question(
            self, "Confirm",
            f"Are you sure you want to remove '{service.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.api_manager.remove_service(service_id):
                QMessageBox.information(self, "Success", "Service removed successfully!")
                self.load_services()
            else:
                QMessageBox.critical(self, "Error", "Failed to remove service.")

    def test_selected_service(self):
        """Test selected service connection"""
        row = self.services_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a service to test.")
            return

        service_id = self.services_table.item(row, 5).text()

        # Test connection
        success, message = self.api_manager.test_service(service_id)

        if success:
            QMessageBox.information(self, "Test Successful", message)
        else:
            QMessageBox.critical(self, "Test Failed", message)

        # Refresh table to show updated test status
        self.load_services()

    def get_api_manager(self) -> APIServiceManager:
        """Get API manager instance"""
        return self.api_manager
