"""
File utilities for CSV operations and data handling
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import csv

from models.data_structures import FileInfo
from config.settings import AppSettings


class FileUtils:
    """Utilities for file operations"""

    @staticmethod
    def get_csv_files(directory: str) -> List[str]:
        """Get all CSV files in a directory"""
        if not os.path.exists(directory):
            return []

        csv_files = []
        for file in os.listdir(directory):
            if file.lower().endswith(".csv"):
                csv_files.append(file)

        return sorted(csv_files)

    @staticmethod
    def load_csv_file(file_path: str, encoding: str = None) -> Optional[pd.DataFrame]:
        """Load a CSV file with error handling"""
        if encoding is None:
            encoding = AppSettings.DEFAULT_ENCODING

        try:
            # Try different encodings if the default fails
            encodings_to_try = [encoding, "utf-8", "latin-1", "cp1252"]

            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    # Replace NaN values with empty strings to avoid "nan" display
                    df = df.fillna("")
                    return df
                except UnicodeDecodeError:
                    continue

            # If all encodings fail, try with error handling
            df = pd.read_csv(file_path, encoding="utf-8", errors="replace")
            # Replace NaN values with empty strings
            df = df.fillna("")
            return df

        except Exception as e:
            print(f"Error loading CSV file {file_path}: {e}")
            return None

    @staticmethod
    def save_csv_file(
        dataframe: pd.DataFrame, file_path: str, encoding: str = None
    ) -> bool:
        """Save DataFrame to CSV file"""
        if encoding is None:
            encoding = AppSettings.DEFAULT_ENCODING

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Save to CSV
            dataframe.to_csv(file_path, index=False, encoding=encoding)
            return True

        except Exception as e:
            print(f"Error saving CSV file {file_path}: {e}")
            return False

    @staticmethod
    def get_file_info(file_path: str) -> Optional[FileInfo]:
        """Get information about a CSV file"""
        try:
            df = FileUtils.load_csv_file(file_path)
            if df is None:
                return None

            file_name = os.path.basename(file_path)
            columns = df.columns.tolist()

            # Check for translation-related columns
            has_original_text = "Original Text" in columns
            translation_columns = []

            for col in ["Initial", "Machine translation", "Translation", "Translated"]:
                if col in columns:
                    translation_columns.append(col)

            has_translation = len(translation_columns) > 0

            return FileInfo(
                file_path=file_path,
                file_name=file_name,
                row_count=len(df),
                column_count=len(df.columns),
                columns=columns,
                has_original_text=has_original_text,
                has_translation=has_translation,
                translation_columns=translation_columns,
            )

        except Exception as e:
            print(f"Error getting file info for {file_path}: {e}")
            return None

    @staticmethod
    def backup_file(file_path: str, backup_dir: str = None) -> Optional[str]:
        """Create a backup of a file"""
        try:
            if backup_dir is None:
                backup_dir = os.path.join(os.path.dirname(file_path), "backups")

            os.makedirs(backup_dir, exist_ok=True)

            # Create backup filename with timestamp
            import time

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            file_name = os.path.basename(file_path)
            backup_name = f"{timestamp}_{file_name}"
            backup_path = os.path.join(backup_dir, backup_name)

            # Copy file
            import shutil

            shutil.copy2(file_path, backup_path)

            return backup_path

        except Exception as e:
            print(f"Error creating backup for {file_path}: {e}")
            return None


class CSVConverter:
    """Convert between CSV and JSON formats"""

    @staticmethod
    def csv_to_json_chunks(
        dataframe: pd.DataFrame, column: str, chunk_size: int = 100
    ) -> List[List[Dict[str, any]]]:
        """Convert CSV column to JSON chunks for translation with line numbers"""
        if column not in dataframe.columns:
            return []

        # Convert to string and handle NaN/empty values
        texts = dataframe[column].fillna("").astype(str).tolist()

        # Create list of dictionaries with line numbers
        json_data = []
        for i, text in enumerate(texts):
            # Skip empty or "nan" entries
            if text and text.strip() and text.lower() != "nan":
                json_data.append({"line": i + 1, "text": text.strip()})

        # Split into chunks
        chunks = []
        for i in range(0, len(json_data), chunk_size):
            chunk = json_data[i : i + chunk_size]
            chunks.append(chunk)

        return chunks

    @staticmethod
    def json_chunks_to_csv(
        chunks: List[List[Dict[str, any]]], target_dataframe: pd.DataFrame, column: str
    ) -> pd.DataFrame:
        """Convert JSON chunks back to CSV column"""
        result_df = target_dataframe.copy()

        # Initialize the column with empty strings
        result_df[column] = ""

        # Process all chunks
        for chunk in chunks:
            for item in chunk:
                if isinstance(item, dict) and "line" in item and "text" in item:
                    line_num = item["line"] - 1  # Convert to 0-based index
                    if 0 <= line_num < len(result_df):
                        result_df.iloc[line_num, result_df.columns.get_loc(column)] = (
                            item["text"]
                        )

        return result_df

    @staticmethod
    def create_translation_request_json(
        chunk_data: List[Dict[str, any]],
    ) -> Dict[str, any]:
        """Create the JSON request format for LLM translation"""
        return chunk_data  # Input format: [{"line": 1, "text": "..."}, ...]

    @staticmethod
    def parse_translation_response_json(response_json: str) -> List[Dict[str, any]]:
        """Parse LLM response JSON format"""
        try:
            import json

            response_data = (
                json.loads(response_json)
                if isinstance(response_json, str)
                else response_json
            )

            # Expected format: {"translation": [{"line": 1, "text": "..."}, ...]}
            if isinstance(response_data, dict) and "translation" in response_data:
                return response_data["translation"]

            # Fallback: if it's already in the expected array format
            if isinstance(response_data, list):
                return response_data

            return []

        except Exception as e:
            print(f"Error parsing translation response: {e}")
            return []

    @staticmethod
    def export_to_json(
        dataframe: pd.DataFrame, file_path: str, columns: List[str] = None
    ) -> bool:
        """Export DataFrame to JSON file"""
        try:
            if columns:
                # Export only specified columns
                export_data = dataframe[columns].to_dict("records")
            else:
                # Export all data
                export_data = dataframe.to_dict("records")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"Error exporting to JSON {file_path}: {e}")
            return False

    @staticmethod
    def import_from_json(file_path: str) -> Optional[pd.DataFrame]:
        """Import DataFrame from JSON file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            df = pd.DataFrame(data)
            return df

        except Exception as e:
            print(f"Error importing from JSON {file_path}: {e}")
            return None


class ConfigManager:
    """Manage application configuration files"""

    @staticmethod
    def save_config(config_data: Dict, file_path: str) -> bool:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"Error saving config to {file_path}: {e}")
            return False

    @staticmethod
    def load_config(file_path: str) -> Optional[Dict]:
        """Load configuration from file"""
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            return config_data

        except Exception as e:
            print(f"Error loading config from {file_path}: {e}")
            return None

    @staticmethod
    def get_default_config_path() -> str:
        """Get default configuration file path"""
        from pathlib import Path

        home_dir = Path.home()
        config_dir = home_dir / ".csv_translator"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "config.json")
