"""
Application configuration settings
"""

import os
from typing import Dict, Any, List
from pathlib import Path


class AppSettings:
    """Application settings and configuration"""

    # Default directories
    DEFAULT_INPUT_DIR = ""
    DEFAULT_OUTPUT_DIR = ""
    DEFAULT_HISTORY_FILE = ""

    # AI Model settings
    DEFAULT_AI_MODEL = "gemini-2.0-flash-exp"
    AVAILABLE_MODELS = ["gemini-2.0-flash-exp", "gpt-4", "claude-3-sonnet-20240229"]

    # Custom models by provider
    CUSTOM_MODELS = {
        "google": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
        "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic": [
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229",
        ],
    }

    # Translation settings
    DEFAULT_SLEEP_TIME = 10  # seconds between API calls
    DEFAULT_CHUNK_SIZE = 50  # lines per translation chunk
    MAX_RETRIES = 3

    # Target columns for translation results
    CSV_TARGET_COLUMNS = [
        "Initial",
        "Machine translation",
        "Better translation",
        "Best translation",
    ]
    DEFAULT_TARGET_COLUMN = "Initial"

    # UI settings
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    TABLE_MIN_HEIGHT = 600
    CELL_DETAIL_HEIGHT = 50
    STATUS_HEIGHT = 50

    # Theme settings
    THEMES = {
        "light": {
            "background": "#ffffff",
            "foreground": "#000000",
            "table_grid": "#d0d0d0",
            "table_selection": "#0078D7",
            "table_header": "#f0f0f0",
            "button_normal": "#e1e1e1",
            "button_hover": "#d0d0d0",
            "input_background": "#ffffff",
            "input_border": "#cccccc",
        },
        "dark": {
            "background": "#2b2b2b",
            "foreground": "#ffffff",
            "table_grid": "#3c3c3c",
            "table_selection": "#094771",
            "table_header": "#3c3c3c",
            "button_normal": "#404040",
            "button_hover": "#505050",
            "input_background": "#3c3c3c",
            "input_border": "#5a5a5a",
        },
    }

    DEFAULT_THEME = "light"

    # File settings
    SUPPORTED_FILE_EXTENSIONS = [".csv"]
    DEFAULT_ENCODING = "utf-8"

    # Chat history settings for LangGraph compatibility
    CHAT_HISTORY_FORMAT = "langgraph"  # or "simple"
    MAX_CHAT_HISTORY_SIZE = 50

    @classmethod
    def get_provider_models(cls, provider: str) -> List[str]:
        """Get available models for a specific provider"""
        return cls.CUSTOM_MODELS.get(provider.lower(), [])

    @classmethod
    def add_custom_model(cls, provider: str, model_name: str):
        """Add a custom model for a provider"""
        provider_key = provider.lower()
        if provider_key not in cls.CUSTOM_MODELS:
            cls.CUSTOM_MODELS[provider_key] = []
        if model_name not in cls.CUSTOM_MODELS[provider_key]:
            cls.CUSTOM_MODELS[provider_key].append(model_name)

    @classmethod
    def get_theme_style(cls, theme_name: str = None) -> str:
        """Get CSS stylesheet for the specified theme"""
        if theme_name is None:
            theme_name = cls.DEFAULT_THEME

        theme = cls.THEMES.get(theme_name, cls.THEMES[cls.DEFAULT_THEME])

        return f"""
        QMainWindow {{
            background-color: {theme['background']};
            color: {theme['foreground']};
        }}
        
        QWidget {{
            background-color: {theme['background']};
            color: {theme['foreground']};
        }}
        
        QTableView {{
            gridline-color: {theme['table_grid']};
            border: 1px solid {theme['table_grid']};
            background-color: {theme['background']};
            selection-background-color: {theme['table_selection']};
            selection-color: white;
            alternate-background-color: {theme['background']};
        }}
        
        QTableView::item {{
            border: 1px solid {theme['table_grid']};
            padding: 5px;
        }}
        
        QHeaderView::section {{
            background-color: {theme['table_header']};
            padding: 5px;
            border: 1px solid {theme['table_grid']};
            font-weight: bold;
            color: {theme['foreground']};
        }}
        
        QTableView::item:selected {{
            background-color: {theme['table_selection']};
            color: white;
        }}
        
        QPushButton {{
            background-color: {theme['button_normal']};
            border: 1px solid {theme['table_grid']};
            padding: 8px;
            border-radius: 4px;
            color: {theme['foreground']};
        }}
        
        QPushButton:hover {{
            background-color: {theme['button_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme['table_selection']};
            color: white;
        }}
        
        QLineEdit, QTextEdit {{
            background-color: {theme['input_background']};
            border: 1px solid {theme['input_border']};
            padding: 4px;
            border-radius: 2px;
            color: {theme['foreground']};
        }}
        
        QComboBox {{
            background-color: {theme['input_background']};
            border: 1px solid {theme['input_border']};
            padding: 4px;
            border-radius: 2px;
            color: {theme['foreground']};
        }}
        
        QComboBox::drop-down {{
            border: none;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {theme['table_grid']};
            border-radius: 4px;
            margin: 5px 0px;
            padding-top: 10px;
            color: {theme['foreground']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
        
        QLabel {{
            color: {theme['foreground']};
        }}
        
        QMenuBar {{
            background-color: {theme['background']};
            color: {theme['foreground']};
            border-bottom: 1px solid {theme['table_grid']};
        }}
        
        QMenuBar::item {{
            background: transparent;
            padding: 4px 8px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme['button_hover']};
        }}
        
        QMenu {{
            background-color: {theme['background']};
            color: {theme['foreground']};
            border: 1px solid {theme['table_grid']};
        }}
        
        QMenu::item {{
            padding: 4px 16px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme['table_selection']};
            color: white;
        }}
        """


# Global settings instance
app_settings = AppSettings()
