"""
System Instruction Editor Panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTextEdit, QLabel, QComboBox,
    QMessageBox, QDialog, QFormLayout, QLineEdit,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import Dict, List, Optional

from models.api_models import SystemInstructionTemplate


class InstructionTemplateDialog(QDialog):
    """Dialog để thêm/sửa instruction template"""

    def __init__(self, parent=None, template: Optional[SystemInstructionTemplate] = None):
        super().__init__(parent)
        self.template = template
        self.is_edit = template is not None
        self.setup_ui()

        if template:
            self.load_template_data(template)

    def setup_ui(self):
        """Setup UI"""
        self.setWindowTitle("Add Template" if not self.is_edit else "Edit Template")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Form
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.description_edit = QLineEdit()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["translation", "summary"])

        form.addRow("Name:", self.name_edit)
        form.addRow("Description:", self.description_edit)
        form.addRow("Type:", self.type_combo)

        layout.addLayout(form)

        # Content
        content_label = QLabel("Instruction Content:")
        layout.addWidget(content_label)

        self.content_edit = QTextEdit()
        self.content_edit.setMinimumHeight(300)
        layout.addWidget(self.content_edit)

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

    def load_template_data(self, template: SystemInstructionTemplate):
        """Load template data"""
        self.name_edit.setText(template.name)
        self.description_edit.setText(template.description)
        self.type_combo.setCurrentText(template.instruction_type)
        self.content_edit.setPlainText(template.content)

    def get_template(self) -> SystemInstructionTemplate:
        """Get template from form"""
        import uuid
        from datetime import datetime

        template_id = self.template.id if self.template else str(uuid.uuid4())

        return SystemInstructionTemplate(
            id=template_id,
            name=self.name_edit.text(),
            description=self.description_edit.text(),
            instruction_type=self.type_combo.currentText(),
            content=self.content_edit.toPlainText(),
            created_at=datetime.now().isoformat()
        )


class InstructionPanel(QWidget):
    """Panel để chỉnh sửa system instructions"""

    instruction_changed = pyqtSignal(str, str)  # type, content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.templates: List[SystemInstructionTemplate] = []
        self.setup_ui()
        self.load_default_instructions()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("<h3>System Instructions</h3>")
        layout.addWidget(header_label)

        # Translation instruction
        translation_group = QGroupBox("Translation Instruction")
        translation_layout = QVBoxLayout()

        trans_header = QHBoxLayout()
        trans_label = QLabel("System instruction for translation:")
        trans_header.addWidget(trans_label)
        trans_header.addStretch()

        self.load_trans_template_btn = QPushButton("📁 Load Template")
        self.load_trans_template_btn.clicked.connect(lambda: self.load_template("translation"))
        trans_header.addWidget(self.load_trans_template_btn)

        self.save_trans_template_btn = QPushButton("💾 Save as Template")
        self.save_trans_template_btn.clicked.connect(lambda: self.save_as_template("translation"))
        trans_header.addWidget(self.save_trans_template_btn)

        translation_layout.addLayout(trans_header)

        self.translation_instruction_edit = QTextEdit()
        self.translation_instruction_edit.setMinimumHeight(250)
        self.translation_instruction_edit.textChanged.connect(
            lambda: self.instruction_changed.emit("translation", self.translation_instruction_edit.toPlainText())
        )
        translation_layout.addWidget(self.translation_instruction_edit)

        translation_group.setLayout(translation_layout)
        layout.addWidget(translation_group)

        # Summary instruction
        summary_group = QGroupBox("Summary Instruction")
        summary_layout = QVBoxLayout()

        summary_header = QHBoxLayout()
        summary_label = QLabel("System instruction for summary:")
        summary_header.addWidget(summary_label)
        summary_header.addStretch()

        self.load_summary_template_btn = QPushButton("📁 Load Template")
        self.load_summary_template_btn.clicked.connect(lambda: self.load_template("summary"))
        summary_header.addWidget(self.load_summary_template_btn)

        self.save_summary_template_btn = QPushButton("💾 Save as Template")
        self.save_summary_template_btn.clicked.connect(lambda: self.save_as_template("summary"))
        summary_header.addWidget(self.save_summary_template_btn)

        summary_layout.addLayout(summary_header)

        self.summary_instruction_edit = QTextEdit()
        self.summary_instruction_edit.setMinimumHeight(250)
        self.summary_instruction_edit.textChanged.connect(
            lambda: self.instruction_changed.emit("summary", self.summary_instruction_edit.toPlainText())
        )
        summary_layout.addWidget(self.summary_instruction_edit)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Template management buttons
        template_btn_layout = QHBoxLayout()
        template_btn_layout.addStretch()

        self.manage_templates_btn = QPushButton("📝 Manage Templates")
        self.manage_templates_btn.clicked.connect(self.manage_templates)
        template_btn_layout.addWidget(self.manage_templates_btn)

        layout.addLayout(template_btn_layout)
        layout.addStretch()

    def load_default_instructions(self):
        """Load default instructions"""
        # Default translation instruction (từ translation_engine.py)
        default_translation = """Bạn là AI chuyên dịch văn bản tiếng Nhật sang tiếng Việt cho các trò chơi visual novel.
Bạn sẽ nhận đầu vào ở định dạng mảng JSON và phải xuất bản dịch theo đúng cấu trúc JSON với format:
{"translation": [{"line": 1, "text": "..."}, {"line": 2, "text": "..."}, ...]}

Quy tắc dịch:
- Giữ nguyên số lượng và thứ tự phần tử
- Bảo tồn văn hóa và ngữ cảnh Nhật Bản
- Sử dụng giọng điệu trẻ trung, không trang trọng
- Giữ nguyên kính ngữ (-san, -chan, -kun, etc.)
- Dịch tự nhiên và súc tích sang tiếng Việt"""

        # Default summary instruction
        default_summary = """Bạn là AI chuyên tóm tắt nội dung từ các file dịch thuật.
Hãy tóm tắt nội dung một cách ngắn gọn, rõ ràng và súc tích.
Tập trung vào các điểm chính và thông tin quan trọng.
Trình bày dưới dạng bullet points hoặc đoạn văn ngắn."""

        self.translation_instruction_edit.setPlainText(default_translation)
        self.summary_instruction_edit.setPlainText(default_summary)

        # Create default templates
        self.templates = [
            SystemInstructionTemplate(
                id="default_translation",
                name="Default Translation",
                description="Default instruction for visual novel translation",
                instruction_type="translation",
                content=default_translation,
                is_default=True
            ),
            SystemInstructionTemplate(
                id="default_summary",
                name="Default Summary",
                description="Default instruction for content summary",
                instruction_type="summary",
                content=default_summary,
                is_default=True
            )
        ]

    def load_template(self, instruction_type: str):
        """Load template cho instruction type"""
        # Filter templates by type
        filtered_templates = [t for t in self.templates if t.instruction_type == instruction_type]

        if not filtered_templates:
            QMessageBox.information(self, "No Templates", "No templates available for this type.")
            return

        # Show dialog to select template
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Template")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        label = QLabel(f"Select a {instruction_type} template:")
        layout.addWidget(label)

        template_list = QListWidget()
        for template in filtered_templates:
            item = QListWidgetItem(f"{template.name} - {template.description}")
            item.setData(Qt.ItemDataRole.UserRole, template)
            template_list.addItem(item)

        layout.addWidget(template_list)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        load_btn = QPushButton("Load")
        load_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(load_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_item = template_list.currentItem()
            if selected_item:
                template = selected_item.data(Qt.ItemDataRole.UserRole)
                if instruction_type == "translation":
                    self.translation_instruction_edit.setPlainText(template.content)
                else:
                    self.summary_instruction_edit.setPlainText(template.content)

    def save_as_template(self, instruction_type: str):
        """Save current instruction as template"""
        if instruction_type == "translation":
            content = self.translation_instruction_edit.toPlainText()
        else:
            content = self.summary_instruction_edit.toPlainText()

        if not content.strip():
            QMessageBox.warning(self, "Warning", "Instruction content is empty.")
            return

        # Create template
        dialog = InstructionTemplateDialog(self)
        dialog.type_combo.setCurrentText(instruction_type)
        dialog.content_edit.setPlainText(content)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            template = dialog.get_template()
            self.templates.append(template)
            QMessageBox.information(self, "Success", "Template saved successfully!")

    def manage_templates(self):
        """Manage instruction templates"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Templates")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        # List
        template_list = QListWidget()
        for template in self.templates:
            item_text = f"{template.name} ({template.instruction_type})"
            if template.is_default:
                item_text += " [Default]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, template)
            template_list.addItem(item)

        layout.addWidget(template_list)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Add")
        add_btn.clicked.connect(lambda: self.add_template_from_dialog(template_list))

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.clicked.connect(lambda: self.edit_template_from_dialog(template_list))

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(lambda: self.delete_template_from_dialog(template_list))

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)

        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def add_template_from_dialog(self, list_widget: QListWidget):
        """Add template from dialog"""
        dialog = InstructionTemplateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            template = dialog.get_template()
            self.templates.append(template)

            # Add to list
            item_text = f"{template.name} ({template.instruction_type})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, template)
            list_widget.addItem(item)

            QMessageBox.information(self, "Success", "Template added successfully!")

    def edit_template_from_dialog(self, list_widget: QListWidget):
        """Edit template from dialog"""
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to edit.")
            return

        template = current_item.data(Qt.ItemDataRole.UserRole)
        if template.is_default:
            QMessageBox.warning(self, "Warning", "Cannot edit default templates.")
            return

        dialog = InstructionTemplateDialog(self, template)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_template = dialog.get_template()

            # Update in list
            index = self.templates.index(template)
            self.templates[index] = updated_template

            # Update list item
            current_item.setText(f"{updated_template.name} ({updated_template.instruction_type})")
            current_item.setData(Qt.ItemDataRole.UserRole, updated_template)

            QMessageBox.information(self, "Success", "Template updated successfully!")

    def delete_template_from_dialog(self, list_widget: QListWidget):
        """Delete template from dialog"""
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to delete.")
            return

        template = current_item.data(Qt.ItemDataRole.UserRole)
        if template.is_default:
            QMessageBox.warning(self, "Warning", "Cannot delete default templates.")
            return

        reply = QMessageBox.question(
            self, "Confirm",
            f"Are you sure you want to delete '{template.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.templates.remove(template)
            list_widget.takeItem(list_widget.row(current_item))
            QMessageBox.information(self, "Success", "Template deleted successfully!")

    def get_translation_instruction(self) -> str:
        """Get translation instruction"""
        return self.translation_instruction_edit.toPlainText()

    def get_summary_instruction(self) -> str:
        """Get summary instruction"""
        return self.summary_instruction_edit.toPlainText()

    def set_translation_instruction(self, instruction: str):
        """Set translation instruction"""
        self.translation_instruction_edit.setPlainText(instruction)

    def set_summary_instruction(self, instruction: str):
        """Set summary instruction"""
        self.summary_instruction_edit.setPlainText(instruction)

    def get_templates(self) -> List[SystemInstructionTemplate]:
        """Get all templates"""
        return self.templates

    def set_templates(self, templates: List[SystemInstructionTemplate]):
        """Set templates"""
        self.templates = templates
