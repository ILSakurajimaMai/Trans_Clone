"""
Enhanced Data Structures - Các cấu trúc dữ liệu cải tiến
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum, auto
import pandas as pd
from pathlib import Path
import time
from datetime import datetime


class ModelProvider(Enum):
    """Supported model providers"""

    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class ChatMessage:
    """A single chat message"""

    role: str  # human, ai, system
    content: str
    timestamp: str = ""
    model_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ChatHistory:
    """Complete chat history"""

    messages: List[ChatMessage] = field(default_factory=list)
    context_id: str = ""
    model_provider: Optional[ModelProvider] = None
    model_name: str = ""
    creation_time: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S")
    )
    last_updated: str = ""

    def add_message(self, role: str, content: str, **kwargs):
        """Add a message to history"""
        message = ChatMessage(role=role, content=content, **kwargs)
        self.messages.append(message)
        self.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_langgraph_format(self) -> List[Dict[str, Any]]:
        """Convert to LangGraph format"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "model_name": msg.model_name,
                "metadata": msg.metadata,
            }
            for msg in self.messages
        ]

    def from_langgraph_format(self, data: List[Dict[str, Any]]):
        """Load from LangGraph format"""
        self.messages = []
        for msg_data in data:
            self.add_message(**msg_data)


class UndoRedoAction(Enum):
    """Types of undo/redo actions"""

    EDIT_CELL = "edit_cell"
    TRANSLATE = "translate"
    PASTE_DATA = "paste_data"
    DELETE_DATA = "delete_data"
    CUT_DATA = "cut_data"


@dataclass
class TranslationChunk:
    """A chunk of text to be translated"""

    chunk_id: int
    original_texts: List[str]
    translated_texts: List[str] = field(default_factory=list)
    start_row: int = 0
    end_row: int = 0
    target_column: str = "Initial"
    status: str = "pending"  # pending, translating, completed, error
    error_message: str = ""

    # Context information
    has_context: bool = False
    context_chunks: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class TranslationRequest:
    """Translation request configuration"""

    # Service configuration
    model_provider: ModelProvider
    model_name: str = ""

    # Target settings
    target_column: str = "Initial"
    selected_rows: Optional[List[int]] = None  # None = all rows

    # Translation settings
    sleep_time: int = 10
    chunk_size: int = 50

    # Context settings
    use_context: bool = False
    context_files: List[str] = field(default_factory=list)
    context_chunk_count: int = 5

    # System instruction
    system_instruction: Optional[str] = None
    use_custom_instruction: bool = False

    # Processing options
    max_retries: int = 3
    use_history: bool = False
    skip_translated: bool = False  # Skip rows that already have translation


@dataclass
class HistoryEntry:
    """History entry for conversation"""

    role: str  # user, assistant, system
    content: str
    timestamp: str = ""
    model_name: str = ""
    context_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class UndoRedoState:
    """State for undo/redo operations"""

    action_type: UndoRedoAction
    timestamp: str
    description: str
    # For cell edits
    cell_position: Tuple[int, int] = None
    old_value: Any = None
    new_value: Any = None
    # For bulk operations
    old_data: pd.DataFrame = None
    new_data: pd.DataFrame = None
    affected_cells: Set[Tuple[int, int]] = field(default_factory=set)


@dataclass
class SearchResult:
    """Search result in table data"""

    file_index: int
    row: int
    column: int
    column_name: str
    value: str
    file_name: str


@dataclass
class FileInfo:
    """Information about a CSV file"""

    file_path: str
    file_name: str
    row_count: int = 0
    column_count: int = 0
    columns: List[str] = field(default_factory=list)
    has_original_text: bool = False
    has_translation: bool = False
    translation_columns: List[str] = field(default_factory=list)

    # Additional metadata
    file_size: int = 0
    last_modified: str = ""
    encoding: str = "utf-8"
    parser_used: Optional[str] = None


@dataclass
class CustomModel:
    """Configuration for a custom model"""

    provider: ModelProvider
    model_name: str
    display_name: str = ""
    description: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    is_active: bool = True

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.model_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "description": self.description,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomModel":
        if "provider" in data:
            data["provider"] = ModelProvider(data["provider"])
        return cls(**data)


@dataclass
class CSVParserConfig:
    """Configuration for CSV parser"""

    parser_id: str
    name: str
    parser_type: str  # "default", "regex", "custom"
    description: str = ""

    # Parsing settings
    delimiter: str = ","
    encoding: str = "utf-8"
    skip_rows: int = 0

    # Regex pattern (for regex parser)
    regex_pattern: Optional[str] = None
    regex_groups: Dict[str, int] = field(
        default_factory=dict
    )  # column_name -> group_index

    # Column mapping (after parsing)
    column_mapping: Dict[str, str] = field(
        default_factory=dict
    )  # original_name -> new_name

    # Validation rules
    required_columns: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parser_id": self.parser_id,
            "name": self.name,
            "parser_type": self.parser_type,
            "description": self.description,
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "skip_rows": self.skip_rows,
            "regex_pattern": self.regex_pattern,
            "regex_groups": self.regex_groups,
            "column_mapping": self.column_mapping,
            "required_columns": self.required_columns,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CSVParserConfig":
        return cls(**data)


@dataclass
class AppState:
    """Enhanced Application state"""

    # File management
    input_directory: str = ""
    output_directory: str = ""
    history_file: str = ""
    csv_files: List[Path] = field(default_factory=list)
    current_file_index: int = -1
    current_files: List[str] = field(default_factory=list)
    current_data: pd.DataFrame = None

    # API settings
    current_service_id: str = ""
    available_services: List[str] = field(default_factory=list)
    current_model_provider: ModelProvider = ModelProvider.OPENAI
    api_keys: Dict[str, str] = field(default_factory=dict)
    custom_models: List[Any] = field(default_factory=list)
    # Translation settings
    current_target_column: str = "Initial"
    chunk_size: int = 50
    sleep_time: int = 10
    translation_count: int = 0

    # Context settings
    context_enabled: bool = False
    context_files: List[str] = field(default_factory=list)

    # Parser settings
    current_parser_id: str = "default"
    available_parsers: List[CSVParserConfig] = field(default_factory=list)

    # System instructions
    translation_instruction: str = ""
    summary_instruction: str = ""

    # UI settings
    current_theme: str = "light"
    current_tab: str = "main"  # main, api_settings, system_instruction, summary

    # Undo/Redo state
    undo_stack: List[UndoRedoState] = field(default_factory=list)
    redo_stack: List[UndoRedoState] = field(default_factory=list)
    max_undo_states: int = 50

    # Search state
    current_search_term: str = ""
    search_results: List[SearchResult] = field(default_factory=list)
    current_search_index: int = 0

    # Selection state
    selected_cells: Set[Tuple[int, int]] = field(default_factory=set)
    highlighted_cells: Set[Tuple[int, int]] = field(default_factory=set)

    # Summary history (max 3)
    summary_history: List[Dict[str, Any]] = field(default_factory=list)
    max_summary_history: int = 3

    def add_undo_state(self, state: UndoRedoState):
        """Add an undo state"""
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo_states:
            self.undo_stack.pop(0)
        # Clear redo stack when new action is performed
        self.redo_stack.clear()

    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return len(self.redo_stack) > 0

    def get_undo_state(self) -> Optional[UndoRedoState]:
        """Get the last undo state"""
        if self.can_undo():
            state = self.undo_stack.pop()
            self.redo_stack.append(state)
            return state
        return None

    def get_redo_state(self) -> Optional[UndoRedoState]:
        """Get the last redo state"""
        if self.can_redo():
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            return state
        return None

    def get_current_file(self) -> str:
        """Get the current file path"""
        if 0 <= self.current_file_index < len(self.current_files):
            return self.current_files[self.current_file_index]
        return ""

    def add_summary(self, summary_data: Dict[str, Any]):
        """Add summary to history (max 3, remove oldest if full)"""
        self.summary_history.append(summary_data)
        if len(self.summary_history) > self.max_summary_history:
            self.summary_history.pop(0)  # Remove oldest

    def get_parser_by_id(self, parser_id: str) -> Optional[CSVParserConfig]:
        """Get parser configuration by ID"""
        for parser in self.available_parsers:
            if parser.parser_id == parser_id:
                return parser
        return None


@dataclass
class TableSelection:
    """Represents table selection state"""

    start_row: int
    start_col: int
    end_row: int
    end_col: int

    def get_range(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Get selection range as ((min_row, min_col), (max_row, max_col))"""
        min_row = min(self.start_row, self.end_row)
        max_row = max(self.start_row, self.end_row)
        min_col = min(self.start_col, self.end_col)
        max_col = max(self.start_col, self.end_col)
        return ((min_row, min_col), (max_row, max_col))

    def contains_cell(self, row: int, col: int) -> bool:
        """Check if a cell is within the selection"""
        (min_row, min_col), (max_row, max_col) = self.get_range()
        return min_row <= row <= max_row and min_col <= col <= max_col

    def get_selected_rows(self) -> List[int]:
        """Get list of selected row indices"""
        (min_row, _), (max_row, _) = self.get_range()
        return list(range(min_row, max_row + 1))


@dataclass
class ProjectConfig:
    """Enhanced project configuration"""

    # Version info
    version: str = "2.0"
    schema_version: int = 2

    # Project metadata
    project_name: str = ""
    created_at: str = ""
    last_modified: str = ""

    # Directories
    input_dir: str = ""
    output_dir: str = ""
    history_file: str = ""

    # File state
    current_file: str = ""
    open_file_index: int = 0
    file_list: List[str] = field(default_factory=list)

    # API services (list of service IDs with encrypted API keys)
    api_services: List[Dict[str, Any]] = field(default_factory=list)
    current_service_id: str = ""

    # System instructions
    translation_instruction: str = ""
    summary_instruction: str = ""
    instruction_templates: List[Dict[str, Any]] = field(default_factory=list)

    # CSV Parsers
    csv_parsers: List[Dict[str, Any]] = field(default_factory=list)
    current_parser_id: str = "default"

    # Context configuration
    context_config: Dict[str, Any] = field(default_factory=dict)

    # Translation settings
    target_column: str = "Initial"
    chunk_size: int = 50
    sleep_time: int = 10

    # Summary history
    summary_history: List[Dict[str, Any]] = field(default_factory=list)

    # UI state
    ui_state: Dict[str, Any] = field(default_factory=dict)

    # Processing state
    processed_files: List[str] = field(default_factory=list)
    failed_files: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_modified:
            self.last_modified = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
            "history_file": self.history_file,
            "current_file": self.current_file,
            "open_file_index": self.open_file_index,
            "file_list": self.file_list,
            "api_services": self.api_services,
            "current_service_id": self.current_service_id,
            "translation_instruction": self.translation_instruction,
            "summary_instruction": self.summary_instruction,
            "instruction_templates": self.instruction_templates,
            "csv_parsers": self.csv_parsers,
            "current_parser_id": self.current_parser_id,
            "context_config": self.context_config,
            "target_column": self.target_column,
            "chunk_size": self.chunk_size,
            "sleep_time": self.sleep_time,
            "summary_history": self.summary_history,
            "ui_state": self.ui_state,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
