"""
Enhanced table model for CSV data with undo/redo and advanced features
"""

import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Any, List, Set, Optional, Tuple
import time

from models.data_structures import UndoRedoState, UndoRedoAction, TableSelection


class EnhancedPandasModel(QAbstractTableModel):
    """Enhanced pandas model with undo/redo support and Excel-like features"""

    # Signals
    dataEdited = pyqtSignal(int, int, str, str)  # row, col, old_value, new_value
    selectionChanged = pyqtSignal()

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = pd.DataFrame() if data is None else data.copy()
        self._original_data = self._data.copy()
        self._selected_indexes = set()
        self._highlighted_cells = set()  # For search highlighting
        self._modified_cells = set()  # Track modified cells

        # Undo/Redo stacks
        self._undo_stack: List[UndoRedoState] = []
        self._redo_stack: List[UndoRedoState] = []
        self._max_undo_states = 50

        # Find/replace state
        self._search_term = ""
        self._case_sensitive = False
        self._whole_words = False

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._data.columns) if not self._data.empty else 0

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row, col = index.row(), index.column()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            value = self._data.iloc[row, col]
            # Handle NaN and None values
            if pd.isna(value) or value is None:
                return ""
            # Convert to string and handle "nan" strings
            str_value = str(value)
            if str_value.lower() == "nan":
                return ""
            return str_value

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlighted cells (search results)
            if (row, col) in self._highlighted_cells:
                return QColor(255, 255, 0, 180)  # Yellow highlight
            # Selected cells
            elif index in self._selected_indexes:
                return QColor(173, 216, 230, 180)  # Light blue
            # Modified cells
            elif (row, col) in self._modified_cells:
                return QColor(144, 238, 144, 100)  # Light green

        elif role == Qt.ItemDataRole.ForegroundRole:
            if index in self._selected_indexes or (row, col) in self._highlighted_cells:
                return QColor(0, 0, 0)  # Black text for visibility

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return (
                    str(self._data.columns[section])
                    if section < len(self._data.columns)
                    else ""
                )
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row, col = index.row(), index.column()
        old_value = str(self._data.iloc[row, col])
        new_value = str(value)

        if old_value != new_value:
            # Create undo state
            undo_state = UndoRedoState(
                action_type=UndoRedoAction.EDIT_CELL,
                cell_position=(row, col),
                old_value=old_value,
                new_value=new_value,
                timestamp=time.strftime("%H:%M:%S"),
                description=f"Edit cell ({row+1}, {self._data.columns[col]})",
            )
            self._add_undo_state(undo_state)

            # Update data
            self._data.iloc[row, col] = value
            self._modified_cells.add((row, col))

            # Emit signals
            self.dataChanged.emit(index, index)
            self.dataEdited.emit(row, col, old_value, new_value)

        return True

    def getDataFrame(self):
        """Get the current DataFrame"""
        return self._data.copy()

    def setDataFrame(self, dataframe):
        """Set a new DataFrame"""
        self.beginResetModel()

        # Create undo state for full data change
        if not self._data.empty:
            undo_state = UndoRedoState(
                action_type=UndoRedoAction.TRANSLATE,
                old_data=self._data.copy(),
                new_data=dataframe.copy(),
                timestamp=time.strftime("%H:%M:%S"),
                description="Load new data",
            )
            self._add_undo_state(undo_state)

        self._data = dataframe.copy()
        self._original_data = dataframe.copy()
        self._modified_cells.clear()
        self._selected_indexes.clear()
        self._highlighted_cells.clear()

        self.endResetModel()

    def updateSelection(self, selected_indexes):
        """Update the selected indexes"""
        old_selection = self._selected_indexes.copy()
        self._selected_indexes = set(selected_indexes)

        # Emit dataChanged for affected cells
        all_affected = old_selection.union(self._selected_indexes)
        if all_affected:
            self._emit_data_changed_for_indexes(all_affected)

        self.selectionChanged.emit()

    def highlightCells(self, cells: Set[Tuple[int, int]]):
        """Highlight specific cells (for search results)"""
        old_highlighted = self._highlighted_cells.copy()
        self._highlighted_cells = cells

        # Emit dataChanged for affected cells
        all_affected_positions = old_highlighted.union(self._highlighted_cells)
        affected_indexes = [
            self.index(row, col)
            for row, col in all_affected_positions
            if 0 <= row < self.rowCount() and 0 <= col < self.columnCount()
        ]

        if affected_indexes:
            self._emit_data_changed_for_indexes(affected_indexes)

    def clearHighlights(self):
        """Clear all highlighted cells"""
        self.highlightCells(set())

    def _emit_data_changed_for_indexes(self, indexes):
        """Emit dataChanged for a set of indexes"""
        if not indexes:
            return

        # Convert to list if it's a set of tuples
        if indexes and isinstance(next(iter(indexes)), tuple):
            indexes = [
                self.index(row, col)
                for row, col in indexes
                if 0 <= row < self.rowCount() and 0 <= col < self.columnCount()
            ]

        if indexes:
            min_row = min(idx.row() for idx in indexes)
            max_row = max(idx.row() for idx in indexes)
            min_col = min(idx.column() for idx in indexes)
            max_col = max(idx.column() for idx in indexes)

            top_left = self.index(min_row, min_col)
            bottom_right = self.index(max_row, max_col)
            self.dataChanged.emit(top_left, bottom_right)

    def _add_undo_state(self, state: UndoRedoState):
        """Add an undo state"""
        self._undo_stack.append(state)
        if len(self._undo_stack) > self._max_undo_states:
            self._undo_stack.pop(0)
        # Clear redo stack when new action is performed
        self._redo_stack.clear()

    def canUndo(self) -> bool:
        """Check if undo is possible"""
        return len(self._undo_stack) > 0

    def canRedo(self) -> bool:
        """Check if redo is possible"""
        return len(self._redo_stack) > 0

    def undo(self) -> bool:
        """Perform undo operation"""
        if not self.canUndo():
            return False

        state = self._undo_stack.pop()
        self._redo_stack.append(state)

        if state.action_type == UndoRedoAction.EDIT_CELL:
            row, col = state.cell_position
            self._data.iloc[row, col] = state.old_value
            self._modified_cells.discard((row, col))
            index = self.index(row, col)
            self.dataChanged.emit(index, index)

        elif state.action_type in [UndoRedoAction.TRANSLATE, UndoRedoAction.PASTE_DATA]:
            if state.old_data is not None:
                self.beginResetModel()
                self._data = state.old_data.copy()
                self.endResetModel()

        return True

    def redo(self) -> bool:
        """Perform redo operation"""
        if not self.canRedo():
            return False

        state = self._redo_stack.pop()
        self._undo_stack.append(state)

        if state.action_type == UndoRedoAction.EDIT_CELL:
            row, col = state.cell_position
            self._data.iloc[row, col] = state.new_value
            self._modified_cells.add((row, col))
            index = self.index(row, col)
            self.dataChanged.emit(index, index)

        elif state.action_type in [UndoRedoAction.TRANSLATE, UndoRedoAction.PASTE_DATA]:
            if state.new_data is not None:
                self.beginResetModel()
                self._data = state.new_data.copy()
                self.endResetModel()

        return True

    def getUndoDescription(self) -> str:
        """Get description of the last undo action"""
        if self.canUndo():
            return self._undo_stack[-1].description
        return ""

    def getRedoDescription(self) -> str:
        """Get description of the last redo action"""
        if self.canRedo():
            return self._redo_stack[-1].description
        return ""

    def find(
        self,
        search_term: str,
        case_sensitive: bool = False,
        whole_words: bool = False,
        start_from: Tuple[int, int] = (0, 0),
    ) -> List[Tuple[int, int]]:
        """Find all occurrences of search term"""
        results = []
        self._search_term = search_term
        self._case_sensitive = case_sensitive
        self._whole_words = whole_words

        if not search_term:
            return results

        search_str = search_term if case_sensitive else search_term.lower()

        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                cell_value = str(self._data.iloc[row, col])
                compare_value = cell_value if case_sensitive else cell_value.lower()

                if whole_words:
                    # Simple whole word matching
                    if search_str == compare_value:
                        results.append((row, col))
                else:
                    if search_str in compare_value:
                        results.append((row, col))

        return results

    def replace(
        self,
        old_text: str,
        new_text: str,
        case_sensitive: bool = False,
        whole_words: bool = False,
        selected_only: bool = False,
    ) -> int:
        """Replace text in cells"""
        replaced_count = 0
        cells_to_check = []

        if selected_only and self._selected_indexes:
            cells_to_check = [
                (idx.row(), idx.column()) for idx in self._selected_indexes
            ]
        else:
            cells_to_check = [
                (row, col)
                for row in range(self.rowCount())
                for col in range(self.columnCount())
            ]

        # Create undo state for multiple replacements
        old_data = self._data.copy()

        search_str = old_text if case_sensitive else old_text.lower()

        for row, col in cells_to_check:
            cell_value = str(self._data.iloc[row, col])
            compare_value = cell_value if case_sensitive else cell_value.lower()

            if whole_words:
                if search_str == compare_value:
                    self._data.iloc[row, col] = new_text
                    self._modified_cells.add((row, col))
                    replaced_count += 1
            else:
                if search_str in compare_value:
                    # Preserve original case in replacement
                    if case_sensitive:
                        new_value = cell_value.replace(old_text, new_text)
                    else:
                        # Case-insensitive replacement is more complex
                        import re

                        pattern = re.escape(old_text)
                        new_value = re.sub(
                            pattern, new_text, cell_value, flags=re.IGNORECASE
                        )

                    self._data.iloc[row, col] = new_value
                    self._modified_cells.add((row, col))
                    replaced_count += 1

        if replaced_count > 0:
            # Add undo state
            undo_state = UndoRedoState(
                action_type=UndoRedoAction.PASTE_DATA,  # Reuse for multiple cell changes
                old_data=old_data,
                new_data=self._data.copy(),
                timestamp=time.strftime("%H:%M:%S"),
                description=f"Replace '{old_text}' with '{new_text}' ({replaced_count} replacements)",
            )
            self._add_undo_state(undo_state)

            # Emit data changed for entire model
            if self.rowCount() > 0 and self.columnCount() > 0:
                self.dataChanged.emit(
                    self.index(0, 0),
                    self.index(self.rowCount() - 1, self.columnCount() - 1),
                )

        return replaced_count

    def copySelectedData(self, selected_indexes) -> str:
        """Copy selected cells to clipboard format"""
        if not selected_indexes:
            return ""

        # Group indexes by row for better organization
        rows_data = {}
        for index in selected_indexes:
            row = index.row()
            col = index.column()
            if row not in rows_data:
                rows_data[row] = {}
            rows_data[row][col] = str(self._data.iloc[row, col])

        # Find the range of selection
        min_row = min(rows_data.keys())
        max_row = max(rows_data.keys())
        all_cols = set()
        for row_data in rows_data.values():
            all_cols.update(row_data.keys())
        min_col = min(all_cols)
        max_col = max(all_cols)

        # Build the clipboard data
        clipboard_rows = []
        for row in range(min_row, max_row + 1):
            row_cells = []
            for col in range(min_col, max_col + 1):
                if row in rows_data and col in rows_data[row]:
                    row_cells.append(rows_data[row][col])
                else:
                    row_cells.append("")  # Empty cell for gaps
            clipboard_rows.append("\t".join(row_cells))

        return "\n".join(clipboard_rows)

    def cutSelectedData(self, selected_indexes) -> str:
        """Cut selected cells (copy + delete)"""
        if not selected_indexes:
            return ""

        # First copy the data
        clipboard_data = self.copySelectedData(selected_indexes)

        # Create undo state before deletion
        old_data = self._data.copy()

        # Delete the data
        for index in selected_indexes:
            row, col = index.row(), index.column()
            self._data.iloc[row, col] = ""
            self._modified_cells.add((row, col))

        # Add undo state
        undo_state = UndoRedoState(
            action_type=UndoRedoAction.CUT_DATA,
            old_data=old_data,
            new_data=self._data.copy(),
            timestamp=time.strftime("%H:%M:%S"),
            description=f"Cut {len(selected_indexes)} cells",
            affected_cells=set((idx.row(), idx.column()) for idx in selected_indexes),
        )
        self._add_undo_state(undo_state)

        # Emit data changed
        self._emit_data_changed_for_indexes(selected_indexes)

        return clipboard_data

    def pasteData(self, start_row: int, start_col: int, text_data: str) -> bool:
        """Paste clipboard data starting from specified position"""
        try:
            # Parse text data
            rows = text_data.strip().split("\n")
            if not rows:
                return False

            # Create undo state
            old_data = self._data.copy()

            # Parse and paste data
            affected_cells = set()
            for i, row_data in enumerate(rows):
                target_row = start_row + i
                if target_row >= self.rowCount():
                    break

                cols = row_data.split("\t")
                for j, value in enumerate(cols):
                    target_col = start_col + j
                    if target_col >= self.columnCount():
                        break

                    self._data.iloc[target_row, target_col] = value
                    self._modified_cells.add((target_row, target_col))
                    affected_cells.add((target_row, target_col))

            # Add undo state
            undo_state = UndoRedoState(
                action_type=UndoRedoAction.PASTE_DATA,
                old_data=old_data,
                new_data=self._data.copy(),
                timestamp=time.strftime("%H:%M:%S"),
                description=f"Paste data at ({start_row+1}, {start_col+1})",
                affected_cells=affected_cells,
            )
            self._add_undo_state(undo_state)

            # Emit data changed
            end_row = min(start_row + len(rows) - 1, self.rowCount() - 1)
            max_cols = max(len(row.split("\t")) for row in rows)
            end_col = min(start_col + max_cols - 1, self.columnCount() - 1)

            self.dataChanged.emit(
                self.index(start_row, start_col), self.index(end_row, end_col)
            )

            return True

        except Exception as e:
            print(f"Error pasting data: {e}")
            return False

    def copyColumn(self, column: int) -> str:
        """Copy entire column data"""
        if column < 0 or column >= self.columnCount():
            return ""

        column_data = []
        for row in range(self.rowCount()):
            column_data.append(str(self._data.iloc[row, column]))

        return "\n".join(column_data)

    def copyRow(self, row: int) -> str:
        """Copy entire row data"""
        if row < 0 or row >= self.rowCount():
            return ""

        row_data = []
        for col in range(self.columnCount()):
            row_data.append(str(self._data.iloc[row, col]))

        return "\t".join(row_data)

    def getSelectedRange(self, selected_indexes) -> Tuple[int, int, int, int]:
        """Get the bounding box of selected cells (min_row, min_col, max_row, max_col)"""
        if not selected_indexes:
            return (0, 0, 0, 0)

        min_row = min(idx.row() for idx in selected_indexes)
        max_row = max(idx.row() for idx in selected_indexes)
        min_col = min(idx.column() for idx in selected_indexes)
        max_col = max(idx.column() for idx in selected_indexes)

        return (min_row, min_col, max_row, max_col)

    def deleteSelectedData(self, selected_indexes) -> bool:
        """Delete data in selected cells"""
        if not selected_indexes:
            return False

        # Create undo state
        old_data = self._data.copy()

        # Delete data
        for index in selected_indexes:
            row, col = index.row(), index.column()
            self._data.iloc[row, col] = ""
            self._modified_cells.add((row, col))

        # Add undo state
        undo_state = UndoRedoState(
            action_type=UndoRedoAction.DELETE_DATA,
            old_data=old_data,
            new_data=self._data.copy(),
            timestamp=time.strftime("%H:%M:%S"),
            description=f"Delete {len(selected_indexes)} cells",
        )
        self._add_undo_state(undo_state)

        # Emit data changed
        self._emit_data_changed_for_indexes(selected_indexes)

        return True

    def isModified(self) -> bool:
        """Check if data has been modified"""
        return len(self._modified_cells) > 0 or not self._data.equals(
            self._original_data
        )

    def resetModified(self):
        """Reset the modified state"""
        self._modified_cells.clear()
        self._original_data = self._data.copy()
