"""
Project state management for CSV Translator
Handles project-level settings and workspace state
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class ProjectManager:
    """
    Manages project-level state and settings.
    Each project corresponds to a translation workspace with specific files and settings.
    """

    def __init__(self):
        self.current_path: Optional[str] = None
        self.state: Dict[str, Any] = {}
        self.is_dirty: bool = False
        self._default_state = self._get_default_state()

    def _get_default_state(self) -> Dict[str, Any]:
        """Get default project state"""
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            # Directory settings
            "input_dir": "",
            "output_dir": "",
            "history_file": "",
            # File state
            "current_file": "",
            "open_file_index": 0,
            "scroll_pos": 0,
            "selected_rows": [],
            "selected_columns": [],
            # Translation settings
            "target_column": "Initial",
            "chunk_size": 50,
            "sleep_time": 10,
            "model": "gemini-2.0-flash-exp",
            "max_retries": 3,
            # UI state
            "column_widths": {},
            "hidden_columns": [],
            "sort_column": -1,
            "sort_order": "asc",
            # Advanced settings
            "custom_prompts": {},
            "translation_history": [],
            "bookmarks": [],
            "notes": "",
            # File list state
            "file_list": [],
            "processed_files": [],
            "failed_files": [],
        }

    def create_new_project(self, input_dir: str, output_dir: str = None) -> str:
        """Create a new project in the specified directory"""
        input_path = Path(input_dir)
        if not input_path.exists():
            raise ValueError(f"Input directory does not exist: {input_dir}")

        # Create output directory if not specified
        if not output_dir:
            output_dir = str(input_path / "translated")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate project file name
        project_name = input_path.name.replace(" ", "_")
        project_file = input_path / f"{project_name}.csvtproj"

        # Initialize state
        self.state = self._get_default_state()
        self.state.update(
            {
                "input_dir": str(input_path),
                "output_dir": str(output_path),
                "history_file": str(input_path / "translation_history.json"),
            }
        )

        # Save project
        self.current_path = str(project_file)
        self.save()

        return self.current_path

    def save(self, path: Optional[str] = None) -> bool:
        """Save project state to file"""
        try:
            save_path = path or self.current_path
            if not save_path:
                raise ValueError("No project path specified")

            # Update last modified timestamp
            self.state["last_modified"] = datetime.now().isoformat()

            # Ensure directory exists
            project_path = Path(save_path)
            project_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to file
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)

            self.current_path = save_path
            self.is_dirty = False
            return True

        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    def load(self, path: str) -> bool:
        """Load project state from file"""
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Project file not found: {path}")

            with open(path, "r", encoding="utf-8") as f:
                loaded_state = json.load(f)

            # Merge with default state to ensure all keys exist
            self.state = self._get_default_state()
            self.state.update(loaded_state)

            self.current_path = path
            self.is_dirty = False
            return True

        except Exception as e:
            print(f"Error loading project: {e}")
            return False

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update project state and mark as dirty"""
        self.state.update(updates)
        self.is_dirty = True

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a specific state value"""
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set a specific state value"""
        self.state[key] = value
        self.is_dirty = True

    def get_project_name(self) -> str:
        """Get project name from file path"""
        if not self.current_path:
            return "Untitled Project"
        return Path(self.current_path).stem

    def get_project_dir(self) -> str:
        """Get project directory"""
        if not self.current_path:
            return ""
        return str(Path(self.current_path).parent)

    def is_valid_project(self) -> bool:
        """Check if current project state is valid"""
        required_keys = ["input_dir", "output_dir"]
        return all(key in self.state and self.state[key] for key in required_keys)

    def add_processed_file(self, file_path: str, success: bool = True) -> None:
        """Add a file to processed or failed list"""
        file_path = str(file_path)

        if success:
            if file_path not in self.state.get("processed_files", []):
                self.state.setdefault("processed_files", []).append(file_path)
            # Remove from failed list if it was there
            failed_files = self.state.get("failed_files", [])
            if file_path in failed_files:
                failed_files.remove(file_path)
        else:
            if file_path not in self.state.get("failed_files", []):
                self.state.setdefault("failed_files", []).append(file_path)
            # Remove from processed list if it was there
            processed_files = self.state.get("processed_files", [])
            if file_path in processed_files:
                processed_files.remove(file_path)

        self.is_dirty = True

    def get_file_status(self, file_path: str) -> str:
        """Get processing status of a file"""
        file_path = str(file_path)

        if file_path in self.state.get("processed_files", []):
            return "processed"
        elif file_path in self.state.get("failed_files", []):
            return "failed"
        else:
            return "pending"

    def add_bookmark(
        self, name: str, file_path: str, row: int, column: str = ""
    ) -> None:
        """Add a bookmark for quick navigation"""
        bookmark = {
            "name": name,
            "file_path": str(file_path),
            "row": row,
            "column": column,
            "created_at": datetime.now().isoformat(),
        }

        self.state.setdefault("bookmarks", []).append(bookmark)
        self.is_dirty = True

    def get_bookmarks(self) -> List[Dict[str, Any]]:
        """Get all bookmarks"""
        return self.state.get("bookmarks", [])

    def export_project_summary(self) -> Dict[str, Any]:
        """Export project summary for reports"""
        return {
            "project_name": self.get_project_name(),
            "project_path": self.current_path,
            "input_dir": self.state.get("input_dir"),
            "output_dir": self.state.get("output_dir"),
            "total_files": len(self.state.get("file_list", [])),
            "processed_files": len(self.state.get("processed_files", [])),
            "failed_files": len(self.state.get("failed_files", [])),
            "model": self.state.get("model"),
            "target_column": self.state.get("target_column"),
            "last_modified": self.state.get("last_modified"),
        }

    @staticmethod
    def find_project_files(directory: str) -> List[str]:
        """Find all .csvtproj files in a directory"""
        try:
            directory_path = Path(directory)
            return [str(f) for f in directory_path.glob("*.csvtproj")]
        except Exception:
            return []

    @staticmethod
    def is_project_file(file_path: str) -> bool:
        """Check if a file is a project file"""
        return Path(file_path).suffix.lower() == ".csvtproj"
