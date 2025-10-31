"""
Improved file manager with optimizations and better error handling
"""

import os
import pandas as pd
import asyncio
import aiofiles
from typing import List, Optional, Tuple, Dict, Any, AsyncGenerator
from pathlib import Path
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import StringIO

from models.data_structures import FileInfo, TranslationChunk, AppState
from utils.file_utils import FileUtils, CSVConverter
from config.settings import AppSettings


@dataclass
class ProcessingResult:
    """Result of file processing operation"""

    success: bool
    message: str
    data: Optional[pd.DataFrame] = None
    error_code: Optional[str] = None
    processing_time: Optional[float] = None


class OptimizedFileManager:
    """
    Improved file manager with:
    - Better error handling
    - Memory optimization
    - Async file operations
    - Progress tracking
    - Lazy loading support
    """

    def __init__(self):
        self.input_directory = ""
        self.output_directory = ""
        self.csv_files: List[str] = []
        self.file_infos: List[FileInfo] = []
        self.current_file_index = 0
        self.current_dataframe: Optional[pd.DataFrame] = None

        # Performance tracking
        self.processing_stats = {
            "files_processed": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "errors_count": 0,
        }

        # Memory management
        self.max_memory_usage = 500 * 1024 * 1024  # 500MB
        self.chunk_size = 10000  # Rows per chunk for large files

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def set_input_directory_async(self, directory: str) -> ProcessingResult:
        """Set input directory and load CSV files asynchronously"""
        start_time = time.time()

        try:
            if not os.path.exists(directory):
                return ProcessingResult(
                    success=False,
                    message=f"Directory not found: {directory}",
                    error_code="DIRECTORY_NOT_FOUND",
                )

            self.input_directory = directory

            # Discover CSV files asynchronously
            csv_files = await self._discover_csv_files_async(directory)
            self.csv_files = csv_files

            # Load file information in parallel
            self.file_infos = await self._load_file_infos_async()

            self.current_file_index = 0
            processing_time = time.time() - start_time

            self._update_stats("files_discovered", len(csv_files), processing_time)

            return ProcessingResult(
                success=True,
                message=f"Successfully loaded {len(csv_files)} CSV files",
                processing_time=processing_time,
            )

        except Exception as e:
            self.logger.error(f"Error setting input directory: {e}")
            return ProcessingResult(
                success=False,
                message=f"Error setting input directory: {str(e)}",
                error_code="DIRECTORY_LOAD_ERROR",
                processing_time=time.time() - start_time,
            )

    async def _discover_csv_files_async(self, directory: str) -> List[str]:
        """Discover CSV files asynchronously"""

        def _scan_directory():
            return [f for f in os.listdir(directory) if f.lower().endswith(".csv")]

        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _scan_directory
        )

    async def _load_file_infos_async(self) -> List[FileInfo]:
        """Load file information in parallel"""
        tasks = []
        for csv_file in self.csv_files:
            file_path = os.path.join(self.input_directory, csv_file)
            task = self._get_file_info_async(file_path)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        file_infos = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.warning(f"Error loading file info: {result}")
                continue
            if result:
                file_infos.append(result)

        return file_infos

    async def _get_file_info_async(self, file_path: str) -> Optional[FileInfo]:
        """Get file information asynchronously"""
        try:

            def _get_info():
                return FileUtils.get_file_info(file_path)

            return await asyncio.get_event_loop().run_in_executor(
                self.executor, _get_info
            )
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            return None

    async def load_file_async(
        self, file_index: int, use_chunks: bool = False
    ) -> ProcessingResult:
        """Load a specific file by index with optional chunking"""
        start_time = time.time()

        try:
            if not (0 <= file_index < len(self.csv_files)):
                return ProcessingResult(
                    success=False,
                    message=f"Invalid file index: {file_index}",
                    error_code="INVALID_FILE_INDEX",
                )

            file_path = os.path.join(self.input_directory, self.csv_files[file_index])

            # Check file size to determine loading strategy
            file_size = os.path.getsize(file_path)

            if use_chunks or file_size > 50 * 1024 * 1024:  # 50MB threshold
                dataframe = await self._load_large_file_async(file_path)
            else:
                dataframe = await self._load_regular_file_async(file_path)

            if dataframe is not None:
                self.current_file_index = file_index
                self.current_dataframe = dataframe
                processing_time = time.time() - start_time

                self._update_stats("file_loaded", 1, processing_time)

                return ProcessingResult(
                    success=True,
                    message=f"Successfully loaded {self.csv_files[file_index]}",
                    data=dataframe,
                    processing_time=processing_time,
                )
            else:
                return ProcessingResult(
                    success=False,
                    message=f"Failed to load file: {self.csv_files[file_index]}",
                    error_code="FILE_LOAD_ERROR",
                )

        except Exception as e:
            self.logger.error(f"Error loading file {file_index}: {e}")
            return ProcessingResult(
                success=False,
                message=f"Error loading file: {str(e)}",
                error_code="FILE_LOAD_EXCEPTION",
                processing_time=time.time() - start_time,
            )

    async def _load_regular_file_async(self, file_path: str) -> Optional[pd.DataFrame]:
        """Load regular sized file asynchronously"""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            def _parse_csv():
                return pd.read_csv(StringIO(content))

            return await asyncio.get_event_loop().run_in_executor(
                self.executor, _parse_csv
            )

        except Exception as e:
            self.logger.error(f"Error loading regular file {file_path}: {e}")
            return None

    async def _load_large_file_async(self, file_path: str) -> Optional[pd.DataFrame]:
        """Load large file with chunking strategy"""
        try:

            def _load_chunks():
                chunks = []
                for chunk in pd.read_csv(file_path, chunksize=self.chunk_size):
                    chunks.append(chunk)
                    if (
                        len(chunks) * self.chunk_size > 100000
                    ):  # Limit to 100k rows initially
                        break
                return pd.concat(chunks, ignore_index=True) if chunks else None

            return await asyncio.get_event_loop().run_in_executor(
                self.executor, _load_chunks
            )

        except Exception as e:
            self.logger.error(f"Error loading large file {file_path}: {e}")
            return None

    async def save_file_async(
        self, dataframe: pd.DataFrame, output_filename: str
    ) -> ProcessingResult:
        """Save file asynchronously with backup"""
        start_time = time.time()

        try:
            if not self.output_directory:
                return ProcessingResult(
                    success=False,
                    message="Output directory not set",
                    error_code="NO_OUTPUT_DIRECTORY",
                )

            output_path = os.path.join(self.output_directory, output_filename)

            # Create backup if file exists
            if os.path.exists(output_path):
                await self._create_backup_async(output_path)

            # Save file asynchronously
            success = await self._save_csv_async(dataframe, output_path)

            processing_time = time.time() - start_time

            if success:
                self._update_stats("file_saved", 1, processing_time)
                return ProcessingResult(
                    success=True,
                    message=f"Successfully saved {output_filename}",
                    processing_time=processing_time,
                )
            else:
                return ProcessingResult(
                    success=False,
                    message=f"Failed to save {output_filename}",
                    error_code="FILE_SAVE_ERROR",
                )

        except Exception as e:
            self.logger.error(f"Error saving file {output_filename}: {e}")
            return ProcessingResult(
                success=False,
                message=f"Error saving file: {str(e)}",
                error_code="FILE_SAVE_EXCEPTION",
                processing_time=time.time() - start_time,
            )

    async def _create_backup_async(self, file_path: str):
        """Create backup of existing file"""
        try:
            backup_path = f"{file_path}.backup.{int(time.time())}"

            async with aiofiles.open(file_path, "rb") as src:
                async with aiofiles.open(backup_path, "wb") as dst:
                    await dst.write(await src.read())

        except Exception as e:
            self.logger.warning(f"Failed to create backup for {file_path}: {e}")

    async def _save_csv_async(self, dataframe: pd.DataFrame, file_path: str) -> bool:
        """Save CSV file asynchronously"""
        try:

            def _save():
                dataframe.to_csv(file_path, index=False, encoding="utf-8")
                return True

            return await asyncio.get_event_loop().run_in_executor(self.executor, _save)

        except Exception as e:
            self.logger.error(f"Error saving CSV to {file_path}: {e}")
            return False

    def prepare_optimized_translation_chunks(
        self,
        dataframe: pd.DataFrame,
        source_column: str,
        chunk_size: int = None,
        max_chunks: int = None,
    ) -> List[TranslationChunk]:
        """
        Prepare optimized translation chunks with better memory management
        """
        if source_column not in dataframe.columns:
            return []

        chunk_size = chunk_size or AppSettings.DEFAULT_CHUNK_SIZE

        # Filter out empty rows
        non_empty_data = dataframe[
            dataframe[source_column].notna()
            & (dataframe[source_column].astype(str).str.strip() != "")
        ]

        if non_empty_data.empty:
            return []

        # Convert to optimized chunks
        total_rows = len(non_empty_data)
        chunks = []

        for i in range(0, total_rows, chunk_size):
            end_idx = min(i + chunk_size, total_rows)
            chunk_data = non_empty_data.iloc[i:end_idx]

            # Create chunk with metadata
            chunk = TranslationChunk(
                chunk_id=len(chunks),
                original_texts=[],
                start_row=chunk_data.index[0],
                end_row=chunk_data.index[-1],
                status="pending",
            )

            # Prepare JSON format with line numbers
            for idx, (row_idx, row) in enumerate(chunk_data.iterrows()):
                text = str(row[source_column]).strip()
                if text:
                    chunk.original_texts.append(
                        {
                            "line": row_idx + 1,
                            "text": text,
                            "metadata": {
                                "chunk_id": chunk.chunk_id,
                                "position_in_chunk": idx,
                            },
                        }
                    )

            if chunk.original_texts:  # Only add non-empty chunks
                chunks.append(chunk)

            # Limit chunks if specified
            if max_chunks and len(chunks) >= max_chunks:
                break

        return chunks

    def _update_stats(self, operation: str, count: int, processing_time: float):
        """Update processing statistics"""
        if operation == "files_discovered":
            self.processing_stats["files_discovered"] = count
        elif operation == "file_loaded":
            self.processing_stats["files_processed"] += count
        elif operation == "file_saved":
            self.processing_stats["files_saved"] = (
                self.processing_stats.get("files_saved", 0) + count
            )

        self.processing_stats["total_processing_time"] += processing_time

        if self.processing_stats["files_processed"] > 0:
            self.processing_stats["average_processing_time"] = (
                self.processing_stats["total_processing_time"]
                / self.processing_stats["files_processed"]
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        return {
            **self.processing_stats,
            "memory_usage": self._get_memory_usage(),
            "cache_hit_rate": self._get_cache_hit_rate(),
            "error_rate": self._get_error_rate(),
        }

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage"""
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": process.memory_percent(),
            "dataframe_size": (
                self.current_dataframe.memory_usage(deep=True).sum()
                if self.current_dataframe is not None
                else 0
            ),
        }

    def _get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (placeholder)"""
        # Implementation depends on caching strategy
        return 0.0

    def _get_error_rate(self) -> float:
        """Calculate error rate"""
        total_operations = self.processing_stats.get("files_processed", 0)
        errors = self.processing_stats.get("errors_count", 0)
        return errors / total_operations if total_operations > 0 else 0.0

    def cleanup(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
