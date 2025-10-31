"""
Enhanced table widget with performance optimizations and advanced features
"""

from PyQt6.QtWidgets import (
    QTableView,
    QHeaderView,
    QAbstractItemView,
    QMenu,
    QApplication,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QToolTip,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QModelIndex
from PyQt6.QtGui import QKeySequence, QShortcut, QPainter, QFont
from typing import List, Tuple, Optional, Set
import time


class VirtualizedTableView(QTableView):
    """
    Enhanced table view with:
    - Virtual scrolling for large datasets
    - Smart cell rendering
    - Performance monitoring
    - Enhanced keyboard navigation
    """

    # Custom signals
    cellDoubleClicked = pyqtSignal(int, int)  # row, col
    selectionSummaryChanged = pyqtSignal(str)  # summary text
    performanceUpdate = pyqtSignal(dict)  # performance metrics

    def __init__(self, parent=None):
        super().__init__(parent)

        # Performance tracking
        self.render_times = []
        self.max_render_samples = 100

        # Selection tracking
        self.last_selection_time = 0
        self.selection_cache = set()

        # Setup enhanced features
        self._setup_enhanced_features()
        self._setup_performance_monitoring()
        self._setup_keyboard_shortcuts()

    def _setup_enhanced_features(self):
        """Setup enhanced table features"""
        # Enable advanced selection
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Enable sorting and resizing
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Enable drag and drop
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        # Optimize rendering
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.SolidLine)

        # Connect selection changes
        selection_model = self.selectionModel()
        if selection_model:
            selection_model.selectionChanged.connect(self._on_selection_changed)

    def _setup_performance_monitoring(self):
        """Setup performance monitoring"""
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_performance_metrics)
        self.performance_timer.start(5000)  # Update every 5 seconds

    def _setup_keyboard_shortcuts(self):
        """Setup enhanced keyboard shortcuts"""
        # Navigation shortcuts
        QShortcut(QKeySequence("Ctrl+Home"), self, self._go_to_top)
        QShortcut(QKeySequence("Ctrl+End"), self, self._go_to_bottom)
        QShortcut(QKeySequence("Ctrl+G"), self, self._go_to_cell)

        # Selection shortcuts
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, self._select_all_visible)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._select_column)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, self._select_row)

        # View shortcuts
        QShortcut(QKeySequence("Ctrl+0"), self, self._reset_zoom)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)

    def paintEvent(self, event):
        """Override paint event to track rendering performance"""
        start_time = time.time()
        super().paintEvent(event)
        render_time = time.time() - start_time

        # Track render times
        self.render_times.append(render_time)
        if len(self.render_times) > self.max_render_samples:
            self.render_times.pop(0)

    def _on_selection_changed(self, selected, deselected):
        """Handle selection changes with performance optimization"""
        current_time = time.time()

        # Throttle selection updates
        if current_time - self.last_selection_time < 0.1:  # 100ms throttle
            return

        self.last_selection_time = current_time

        # Update selection cache
        selected_indexes = self.selectionModel().selectedIndexes()
        self.selection_cache = {(idx.row(), idx.column()) for idx in selected_indexes}

        # Emit selection summary
        summary = self._create_selection_summary(selected_indexes)
        self.selectionSummaryChanged.emit(summary)

    def _create_selection_summary(self, selected_indexes: List[QModelIndex]) -> str:
        """Create a summary of the current selection"""
        if not selected_indexes:
            return "No selection"

        rows = {idx.row() for idx in selected_indexes}
        cols = {idx.column() for idx in selected_indexes}

        row_count = len(rows)
        col_count = len(cols)
        cell_count = len(selected_indexes)

        if row_count == 1 and col_count == 1:
            return f"Cell ({min(rows)+1}, {min(cols)+1})"
        elif row_count == 1:
            return f"Row {min(rows)+1}, {cell_count} cells"
        elif col_count == 1:
            return f"Column {min(cols)+1}, {cell_count} cells"
        else:
            return f"{row_count} rows × {col_count} columns ({cell_count} cells)"

    def _update_performance_metrics(self):
        """Update and emit performance metrics"""
        if not self.render_times:
            return

        avg_render_time = sum(self.render_times) / len(self.render_times)
        max_render_time = max(self.render_times)

        metrics = {
            "avg_render_time": avg_render_time,
            "max_render_time": max_render_time,
            "render_fps": 1.0 / avg_render_time if avg_render_time > 0 else 0,
            "selection_count": len(self.selection_cache),
            "visible_rows": self._get_visible_row_count(),
            "visible_columns": self._get_visible_column_count(),
        }

        self.performanceUpdate.emit(metrics)

    def _get_visible_row_count(self) -> int:
        """Get number of visible rows"""
        if not self.model():
            return 0

        viewport_height = self.viewport().height()
        row_height = self.verticalHeader().defaultSectionSize()
        return min(viewport_height // row_height + 2, self.model().rowCount())

    def _get_visible_column_count(self) -> int:
        """Get number of visible columns"""
        if not self.model():
            return 0

        viewport_width = self.viewport().width()
        col_width = self.horizontalHeader().defaultSectionSize()
        return min(viewport_width // col_width + 2, self.model().columnCount())

    # Navigation methods
    def _go_to_top(self):
        """Go to top-left cell"""
        if self.model():
            index = self.model().index(0, 0)
            self.setCurrentIndex(index)
            self.scrollTo(index)

    def _go_to_bottom(self):
        """Go to bottom-right cell"""
        if self.model():
            last_row = self.model().rowCount() - 1
            last_col = self.model().columnCount() - 1
            index = self.model().index(last_row, last_col)
            self.setCurrentIndex(index)
            self.scrollTo(index)

    def _go_to_cell(self):
        """Show go-to-cell dialog"""
        # This would open a dialog to enter row/column coordinates
        pass

    # Selection methods
    def _select_all_visible(self):
        """Select all visible cells"""
        if not self.model():
            return

        visible_rows = self._get_visible_row_count()
        visible_cols = self._get_visible_column_count()

        top_left = self.model().index(0, 0)
        bottom_right = self.model().index(visible_rows - 1, visible_cols - 1)

        from PyQt6.QtCore import QItemSelection

        selection = QItemSelection(top_left, bottom_right)
        self.selectionModel().select(
            selection, self.selectionModel().SelectionFlag.Select
        )

    def _select_column(self):
        """Select current column"""
        current = self.currentIndex()
        if current.isValid():
            self.selectColumn(current.column())

    def _select_row(self):
        """Select current row"""
        current = self.currentIndex()
        if current.isValid():
            self.selectRow(current.row())

    # View methods
    def _reset_zoom(self):
        """Reset zoom to 100%"""
        font = self.font()
        font.setPointSize(9)  # Default size
        self.setFont(font)

    def _zoom_in(self):
        """Zoom in"""
        font = self.font()
        current_size = font.pointSize()
        if current_size < 20:  # Max zoom
            font.setPointSize(current_size + 1)
            self.setFont(font)

    def _zoom_out(self):
        """Zoom out"""
        font = self.font()
        current_size = font.pointSize()
        if current_size > 6:  # Min zoom
            font.setPointSize(current_size - 1)
            self.setFont(font)

    def mouseDoubleClickEvent(self, event):
        """Handle double click events"""
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            self.cellDoubleClicked.emit(index.row(), index.column())
        super().mouseDoubleClickEvent(event)

    def get_performance_info(self) -> dict:
        """Get current performance information"""
        return {
            "render_samples": len(self.render_times),
            "avg_render_time": (
                sum(self.render_times) / len(self.render_times)
                if self.render_times
                else 0
            ),
            "selection_cache_size": len(self.selection_cache),
            "model_size": (
                f"{self.model().rowCount()}x{self.model().columnCount()}"
                if self.model()
                else "None"
            ),
        }


class SmartProgressBar(QProgressBar):
    """Progress bar with smart ETA calculation and throughput display"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_time = None
        self.processed_items = 0
        self.total_items = 0
        self.last_update_time = 0

    def start_progress(self, total_items: int):
        """Start progress tracking"""
        self.start_time = time.time()
        self.total_items = total_items
        self.processed_items = 0
        self.setMaximum(total_items)
        self.setValue(0)

    def update_progress(self, completed_items: int):
        """Update progress with smart ETA calculation"""
        current_time = time.time()

        # Throttle updates for performance
        if current_time - self.last_update_time < 0.5:  # Update every 500ms max
            return

        self.last_update_time = current_time
        self.processed_items = completed_items
        self.setValue(completed_items)

        # Calculate ETA
        if self.start_time and completed_items > 0:
            elapsed_time = current_time - self.start_time
            items_per_second = completed_items / elapsed_time

            if items_per_second > 0:
                remaining_items = self.total_items - completed_items
                eta_seconds = remaining_items / items_per_second

                # Format ETA
                if eta_seconds < 60:
                    eta_text = f"{eta_seconds:.0f}s"
                elif eta_seconds < 3600:
                    eta_text = f"{eta_seconds/60:.1f}m"
                else:
                    eta_text = f"{eta_seconds/3600:.1f}h"

                # Update format
                percentage = (completed_items / self.total_items) * 100
                throughput_text = f"{items_per_second:.1f} items/s"

                self.setFormat(
                    f"{percentage:.1f}% - ETA: {eta_text} ({throughput_text})"
                )
            else:
                self.setFormat(f"{(completed_items / self.total_items) * 100:.1f}%")

    def finish_progress(self):
        """Finish progress tracking"""
        self.setValue(self.maximum())

        if self.start_time:
            total_time = time.time() - self.start_time
            if total_time > 0:
                avg_throughput = self.total_items / total_time
                self.setFormat(f"Completed - {avg_throughput:.1f} items/s average")
            else:
                self.setFormat("Completed")


class TableStatusWidget(QWidget):
    """Status widget showing table information and performance metrics"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the status widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # Selection info
        self.selection_label = QLabel("No selection")
        layout.addWidget(self.selection_label)

        layout.addStretch()

        # Performance info
        self.performance_label = QLabel("Performance: OK")
        layout.addWidget(self.performance_label)

        # Memory usage
        self.memory_label = QLabel("Memory: --")
        layout.addWidget(self.memory_label)

    def update_selection(self, selection_text: str):
        """Update selection information"""
        self.selection_label.setText(f"Selection: {selection_text}")

    def update_performance(self, metrics: dict):
        """Update performance metrics"""
        fps = metrics.get("render_fps", 0)
        if fps > 30:
            status = "Excellent"
            color = "green"
        elif fps > 15:
            status = "Good"
            color = "orange"
        else:
            status = "Poor"
            color = "red"

        self.performance_label.setText(f"Performance: {status} ({fps:.1f} FPS)")
        self.performance_label.setStyleSheet(f"color: {color}")

    def update_memory(self, memory_mb: float):
        """Update memory usage display"""
        if memory_mb < 100:
            color = "green"
        elif memory_mb < 500:
            color = "orange"
        else:
            color = "red"

        self.memory_label.setText(f"Memory: {memory_mb:.1f} MB")
        self.memory_label.setStyleSheet(f"color: {color}")

