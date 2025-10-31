"""
Summary Panel - Tab cho chức năng tóm tắt với history
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTextEdit, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class SummaryPanel(QWidget):
    """Panel cho summary với history (max 3)"""

    summary_requested = pyqtSignal(str, list, dict)  # system_instruction, context_files, config

    def __init__(self, parent=None):
        super().__init__(parent)
        self.summary_history: List[Dict[str, Any]] = []
        self.max_history = 3
        self.setup_ui()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("<h3>Content Summary</h3>")
        layout.addWidget(header_label)

        # Main content split: History list (left) and Detail (right)
        content_layout = QHBoxLayout()

        # History list (left panel)
        history_group = QGroupBox("Summary History (Max 3)")
        history_layout = QVBoxLayout()

        self.history_list = QListWidget()
        self.history_list.currentRowChanged.connect(self.on_history_selected)
        history_layout.addWidget(self.history_list)

        # History buttons
        history_btn_layout = QHBoxLayout()

        self.new_summary_btn = QPushButton("➕ New Summary")
        self.new_summary_btn.clicked.connect(self.new_summary)

        self.delete_summary_btn = QPushButton("🗑️ Delete Selected")
        self.delete_summary_btn.clicked.connect(self.delete_selected_summary)

        history_btn_layout.addWidget(self.new_summary_btn)
        history_btn_layout.addWidget(self.delete_summary_btn)

        history_layout.addLayout(history_btn_layout)
        history_group.setLayout(history_layout)
        history_group.setMaximumWidth(250)

        content_layout.addWidget(history_group)

        # Detail panel (right)
        detail_group = QGroupBox("Summary Details")
        detail_layout = QVBoxLayout()

        # Summary info
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        detail_layout.addWidget(self.info_label)

        # Summary content display
        content_label = QLabel("Summary Content:")
        detail_layout.addWidget(content_label)

        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        self.summary_display.setMinimumHeight(400)
        detail_layout.addWidget(self.summary_display)

        # Context files info
        self.context_files_label = QLabel()
        self.context_files_label.setWordWrap(True)
        detail_layout.addWidget(self.context_files_label)

        # Export button
        export_btn_layout = QHBoxLayout()
        export_btn_layout.addStretch()

        self.export_summary_btn = QPushButton("📄 Export Summary")
        self.export_summary_btn.clicked.connect(self.export_current_summary)
        self.export_summary_btn.setEnabled(False)

        export_btn_layout.addWidget(self.export_summary_btn)

        detail_layout.addLayout(export_btn_layout)

        detail_group.setLayout(detail_layout)
        content_layout.addWidget(detail_group)

        layout.addLayout(content_layout)

        # Update display
        self.update_display()

    def new_summary(self):
        """Create new summary"""
        # Emit signal to parent to handle summary generation
        from ui.dialogs import ContextFileSelectionDialog

        dialog = ContextFileSelectionDialog(self)

        if dialog.exec() == dialog.DialogCode.Accepted:
            selected_files, config = dialog.get_selection()

            if not selected_files:
                QMessageBox.warning(self, "Warning", "No context files selected.")
                return

            # Get system instruction from parent (instruction panel)
            parent_window = self.window()
            if hasattr(parent_window, 'instruction_panel'):
                system_instruction = parent_window.instruction_panel.get_summary_instruction()
            else:
                system_instruction = "Summarize the content from the selected files."

            # Emit signal
            self.summary_requested.emit(system_instruction, selected_files, config)

    def add_summary(self, summary_data: Dict[str, Any]):
        """
        Add summary to history (max 3, remove oldest if full)

        Args:
            summary_data: Dict containing:
                - id: unique id
                - timestamp: creation time
                - system_instruction: instruction used
                - context_files: list of file paths
                - model_used: model name
                - result: summary text
                - tokens_used: optional token count
        """
        # Ensure has required fields
        if 'id' not in summary_data:
            summary_data['id'] = str(uuid.uuid4())
        if 'timestamp' not in summary_data:
            summary_data['timestamp'] = datetime.now().isoformat()

        # Add to history
        self.summary_history.append(summary_data)

        # Remove oldest if exceeds max
        if len(self.summary_history) > self.max_history:
            removed = self.summary_history.pop(0)  # Remove oldest
            QMessageBox.information(
                self, "Info",
                f"Maximum history reached. Removed oldest summary:\n{removed.get('timestamp', 'Unknown')}"
            )

        # Update display
        self.update_display()

        # Select newest
        self.history_list.setCurrentRow(len(self.summary_history) - 1)

    def delete_selected_summary(self):
        """Delete selected summary from history"""
        current_row = self.history_list.currentRow()

        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a summary to delete.")
            return

        reply = QMessageBox.question(
            self, "Confirm",
            "Are you sure you want to delete this summary?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.summary_history[current_row]
            self.update_display()
            QMessageBox.information(self, "Success", "Summary deleted.")

    def on_history_selected(self, row):
        """Handle history selection"""
        if 0 <= row < len(self.summary_history):
            summary_data = self.summary_history[row]
            self.display_summary(summary_data)
            self.export_summary_btn.setEnabled(True)
        else:
            self.clear_display()
            self.export_summary_btn.setEnabled(False)

    def display_summary(self, summary_data: Dict[str, Any]):
        """Display summary details"""
        # Info
        timestamp = summary_data.get('timestamp', 'Unknown')
        model = summary_data.get('model_used', 'Unknown')
        tokens = summary_data.get('tokens_used', 'N/A')

        info_text = f"<b>Created:</b> {timestamp}<br>"
        info_text += f"<b>Model:</b> {model}<br>"
        info_text += f"<b>Tokens:</b> {tokens}"

        self.info_label.setText(info_text)

        # Content
        result = summary_data.get('result', '')
        self.summary_display.setPlainText(result)

        # Context files
        context_files = summary_data.get('context_files', [])
        if context_files:
            from pathlib import Path
            file_names = [Path(f).name for f in context_files]
            files_text = f"<b>Context Files ({len(file_names)}):</b><br>" + "<br>".join(f"• {name}" for name in file_names)
        else:
            files_text = "<b>Context Files:</b> None"

        self.context_files_label.setText(files_text)

    def clear_display(self):
        """Clear detail display"""
        self.info_label.clear()
        self.summary_display.clear()
        self.context_files_label.clear()

    def update_display(self):
        """Update history list display"""
        self.history_list.clear()

        for i, summary_data in enumerate(self.summary_history):
            timestamp = summary_data.get('timestamp', 'Unknown')
            # Format timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp)
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                display_time = timestamp

            item_text = f"{i + 1}. {display_time}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, summary_data)
            self.history_list.addItem(item)

        # If no summaries, show placeholder
        if not self.summary_history:
            self.clear_display()
            self.info_label.setText("<i>No summaries yet. Click 'New Summary' to create one.</i>")

    def export_current_summary(self):
        """Export current summary to file"""
        current_row = self.history_list.currentRow()

        if current_row < 0:
            return

        summary_data = self.summary_history[current_row]

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Summary",
            f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Write header
                    f.write("=" * 80 + "\n")
                    f.write("SUMMARY EXPORT\n")
                    f.write("=" * 80 + "\n\n")

                    # Write metadata
                    f.write(f"Timestamp: {summary_data.get('timestamp', 'Unknown')}\n")
                    f.write(f"Model: {summary_data.get('model_used', 'Unknown')}\n")
                    f.write(f"Tokens: {summary_data.get('tokens_used', 'N/A')}\n\n")

                    # Context files
                    context_files = summary_data.get('context_files', [])
                    if context_files:
                        f.write("Context Files:\n")
                        for cf in context_files:
                            from pathlib import Path
                            f.write(f"  - {Path(cf).name}\n")
                        f.write("\n")

                    # System instruction
                    f.write("System Instruction:\n")
                    f.write("-" * 80 + "\n")
                    f.write(summary_data.get('system_instruction', '') + "\n")
                    f.write("-" * 80 + "\n\n")

                    # Summary content
                    f.write("Summary:\n")
                    f.write("-" * 80 + "\n")
                    f.write(summary_data.get('result', '') + "\n")
                    f.write("-" * 80 + "\n")

                QMessageBox.information(self, "Success", f"Summary exported to:\n{file_path}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export summary:\n{str(e)}")

    def get_summary_history(self) -> List[Dict[str, Any]]:
        """Get summary history"""
        return self.summary_history

    def set_summary_history(self, history: List[Dict[str, Any]]):
        """Set summary history"""
        self.summary_history = history[:self.max_history]  # Ensure max 3
        self.update_display()

    def get_current_summary(self) -> Optional[Dict[str, Any]]:
        """Get currently selected summary"""
        current_row = self.history_list.currentRow()
        if 0 <= current_row < len(self.summary_history):
            return self.summary_history[current_row]
        return None
