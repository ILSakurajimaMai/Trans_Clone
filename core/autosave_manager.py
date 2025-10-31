"""
Auto-save manager for crash protection
Handles session-level auto-save functionality
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import pandas as pd
from PyQt6.QtCore import QTimer, QObject, pyqtSignal


class AutoSaveManager(QObject):
    """
    Manages automatic saving of work to prevent data loss.
    Creates temporary snapshots that can be recovered after crashes.
    """

    # Signal emitted when auto-save occurs
    auto_saved = pyqtSignal(str)  # Emits the auto-save file path
    recovery_available = pyqtSignal(str)  # Emits when recovery data is found

    def __init__(self, interval_seconds: int = 30):
        super().__init__()
        self.interval_seconds = interval_seconds
        self.is_enabled = True
        self.is_dirty = False

        # Timer for auto-save
        self.timer = QTimer()
        self.timer.timeout.connect(self._auto_save)

        # Current session data
        self.current_data: Dict[str, Any] = {}
        self.data_providers: Dict[str, Callable] = {}

        # Auto-save file paths
        self.temp_dir = Path(tempfile.gettempdir()) / "csv_translator_autosave"
        self.temp_dir.mkdir(exist_ok=True)
        self.autosave_file = self.temp_dir / "session.autosave.json"
        self.recovery_info_file = self.temp_dir / "recovery_info.json"

    def start(self) -> None:
        """Start the auto-save timer"""
        if self.is_enabled and self.interval_seconds > 0:
            self.timer.start(self.interval_seconds * 1000)  # Convert to milliseconds

    def stop(self) -> None:
        """Stop the auto-save timer"""
        self.timer.stop()

    def set_interval(self, seconds: int) -> None:
        """Set auto-save interval"""
        self.interval_seconds = seconds
        if self.timer.isActive():
            self.timer.stop()
            self.start()

    def enable(self, enabled: bool = True) -> None:
        """Enable/disable auto-save"""
        self.is_enabled = enabled
        if enabled:
            self.start()
        else:
            self.stop()

    def mark_dirty(self) -> None:
        """Mark session as having unsaved changes"""
        self.is_dirty = True

    def mark_clean(self) -> None:
        """Mark session as saved"""
        self.is_dirty = False

    def register_data_provider(self, name: str, provider: Callable) -> None:
        """
        Register a data provider function that returns data to be auto-saved

        Args:
            name: Unique identifier for this data source
            provider: Callable that returns data to save
        """
        self.data_providers[name] = provider

    def unregister_data_provider(self, name: str) -> None:
        """Unregister a data provider"""
        if name in self.data_providers:
            del self.data_providers[name]

    def _auto_save(self) -> None:
        """Perform auto-save if data is dirty"""
        if not self.is_dirty or not self.data_providers:
            return

        try:
            # Collect data from all providers
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self._get_session_id(),
                "data": {},
            }

            for name, provider in self.data_providers.items():
                try:
                    data = provider()
                    if data is not None:
                        save_data["data"][name] = data
                except Exception as e:
                    print(f"Error collecting data from provider '{name}': {e}")

            # Save to file
            with open(self.autosave_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)

            # Update recovery info
            self._update_recovery_info(save_data)

            # Mark as clean and emit signal
            self.is_dirty = False
            self.auto_saved.emit(str(self.autosave_file))

        except Exception as e:
            print(f"Auto-save failed: {e}")

    def _update_recovery_info(self, save_data: Dict[str, Any]) -> None:
        """Update recovery information file"""
        try:
            recovery_info = {
                "last_autosave": save_data["timestamp"],
                "session_id": save_data["session_id"],
                "autosave_file": str(self.autosave_file),
                "data_sources": list(save_data["data"].keys()),
            }

            with open(self.recovery_info_file, "w", encoding="utf-8") as f:
                json.dump(recovery_info, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Failed to update recovery info: {e}")

    def _get_session_id(self) -> str:
        """Generate unique session ID"""
        import hashlib
        import time

        session_data = f"{os.getpid()}_{time.time()}"
        return hashlib.md5(session_data.encode()).hexdigest()[:8]

    def check_for_recovery(self) -> Optional[Dict[str, Any]]:
        """Check if recovery data is available"""
        try:
            if not self.autosave_file.exists():
                return None

            # Check if autosave file is recent (within last hour)
            autosave_mtime = datetime.fromtimestamp(self.autosave_file.stat().st_mtime)
            time_diff = datetime.now() - autosave_mtime

            if time_diff.total_seconds() > 3600:  # 1 hour
                return None

            # Load and return recovery data
            with open(self.autosave_file, "r", encoding="utf-8") as f:
                recovery_data = json.load(f)

            return recovery_data

        except Exception as e:
            print(f"Error checking recovery data: {e}")
            return None

    def recover_data(self, recovery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract recoverable data from recovery file"""
        try:
            return recovery_data.get("data", {})
        except Exception as e:
            print(f"Error recovering data: {e}")
            return {}

    def clear_recovery_data(self) -> None:
        """Clear recovery data files"""
        try:
            if self.autosave_file.exists():
                self.autosave_file.unlink()
            if self.recovery_info_file.exists():
                self.recovery_info_file.unlink()
        except Exception as e:
            print(f"Error clearing recovery data: {e}")

    def save_dataframe_snapshot(
        self, df: pd.DataFrame, file_path: str, metadata: Dict[str, Any] = None
    ) -> str:
        """
        Save a DataFrame snapshot for recovery

        Args:
            df: DataFrame to save
            file_path: Original file path
            metadata: Additional metadata to save

        Returns:
            Path to snapshot file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"df_snapshot_{timestamp}.json"
            snapshot_path = self.temp_dir / snapshot_name

            # Prepare snapshot data
            snapshot_data = {
                "timestamp": datetime.now().isoformat(),
                "original_file": str(file_path),
                "dataframe": df.to_json(orient="split", force_ascii=False),
                "metadata": metadata or {},
            }

            # Save snapshot
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

            return str(snapshot_path)

        except Exception as e:
            print(f"Error saving DataFrame snapshot: {e}")
            return ""

    def load_dataframe_snapshot(
        self, snapshot_path: str
    ) -> tuple[Optional[pd.DataFrame], Dict[str, Any]]:
        """
        Load DataFrame from snapshot

        Returns:
            Tuple of (DataFrame, metadata)
        """
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot_data = json.load(f)

            # Reconstruct DataFrame
            df_json = snapshot_data.get("dataframe")
            if df_json:
                df = pd.read_json(df_json, orient="split")
                metadata = snapshot_data.get("metadata", {})
                return df, metadata
            else:
                return None, {}

        except Exception as e:
            print(f"Error loading DataFrame snapshot: {e}")
            return None, {}

    def cleanup_old_snapshots(self, max_age_hours: int = 24) -> None:
        """Remove old snapshot files"""
        try:
            current_time = datetime.now()

            for file_path in self.temp_dir.glob("*.json"):
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                age_hours = (current_time - file_time).total_seconds() / 3600

                if age_hours > max_age_hours:
                    file_path.unlink()

        except Exception as e:
            print(f"Error cleaning up snapshots: {e}")

    def get_recovery_info(self) -> Dict[str, Any]:
        """Get information about available recovery data"""
        try:
            if not self.recovery_info_file.exists():
                return {}

            with open(self.recovery_info_file, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            print(f"Error reading recovery info: {e}")
            return {}

    def get_temp_directory(self) -> Path:
        """Get the temporary directory used for auto-save"""
        return self.temp_dir
