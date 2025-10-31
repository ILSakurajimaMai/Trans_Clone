"""
User preferences management using QSettings
"""

from PyQt6.QtCore import QSettings
from typing import Any, Optional
from pathlib import Path


# Organization and application name for QSettings
SETTINGS_ORG = "CSV-Translator"
SETTINGS_APP = "Preferences"


class Prefs:
    """User preferences manager using QSettings"""

    _q = QSettings(SETTINGS_ORG, SETTINGS_APP)

    # Default values for various settings
    DEFAULTS = {
        # UI Settings
        "theme": "light",
        "window_width": 1200,
        "window_height": 800,
        "window_x": 100,
        "window_y": 100,
        "window_maximized": False,
        # Translation Settings
        "default_ai_model": "gemini-2.0-flash-exp",
        "default_chunk_size": 50,
        "default_sleep_time": 10,
        "default_target_column": "Initial",
        # File Settings
        "last_input_dir": "",
        "last_output_dir": "",
        "last_project_path": "",
        "recent_projects": [],
        # UI Behavior
        "auto_save_enabled": True,
        "auto_save_interval": 30,  # seconds
        "confirm_on_exit": True,
        "show_startup_tips": True,
        # Advanced Settings
        "max_retries": 3,
        "encoding": "utf-8",
        "table_font_size": 9,
        "enable_autosave_recovery": True,
    }

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a preference value"""
        cls._q.setValue(key, value)
        cls._q.sync()  # Ensure immediate write

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a preference value with optional default"""
        if default is None:
            default = cls.DEFAULTS.get(key)
        return cls._q.value(key, default)

    @classmethod
    def remove(cls, key: str) -> None:
        """Remove a preference"""
        cls._q.remove(key)

    @classmethod
    def clear_all(cls) -> None:
        """Clear all preferences"""
        cls._q.clear()

    @classmethod
    def get_all_keys(cls) -> list:
        """Get all preference keys"""
        return cls._q.allKeys()

    @classmethod
    def add_recent_project(cls, project_path: str) -> None:
        """Add a project to recent projects list"""
        recent = cls.get("recent_projects", [])
        if isinstance(recent, str):
            recent = [recent] if recent else []

        # Remove if already exists
        if project_path in recent:
            recent.remove(project_path)

        # Add to beginning
        recent.insert(0, project_path)

        # Keep only last 10 projects
        recent = recent[:10]

        cls.set("recent_projects", recent)

    @classmethod
    def get_recent_projects(cls) -> list:
        """Get list of recent projects"""
        recent = cls.get("recent_projects", [])
        if isinstance(recent, str):
            return [recent] if recent else []
        return recent or []

    @classmethod
    def set_window_geometry(
        cls, x: int, y: int, width: int, height: int, maximized: bool = False
    ) -> None:
        """Set window geometry preferences"""
        cls.set("window_x", x)
        cls.set("window_y", y)
        cls.set("window_width", width)
        cls.set("window_height", height)
        cls.set("window_maximized", maximized)

    @classmethod
    def get_window_geometry(cls) -> tuple:
        """Get window geometry preferences"""
        return (
            cls.get("window_x", 100),
            cls.get("window_y", 100),
            cls.get("window_width", 1200),
            cls.get("window_height", 800),
            cls.get("window_maximized", False),
        )

    @classmethod
    def export_to_file(cls, file_path: str) -> bool:
        """Export preferences to a file"""
        try:
            import json

            data = {}
            for key in cls.get_all_keys():
                data[key] = cls.get(key)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting preferences: {e}")
            return False

    @classmethod
    def import_from_file(cls, file_path: str) -> bool:
        """Import preferences from a file"""
        try:
            import json

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for key, value in data.items():
                cls.set(key, value)
            return True
        except Exception as e:
            print(f"Error importing preferences: {e}")
            return False


# Global preferences instance for easy access
prefs = Prefs()
