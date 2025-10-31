"""
Context Manager - Quản lý context cho translation
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from models.api_models import ContextConfig


class ContextManager:
    """
    Quản lý context để gửi tới API
    
    Context được build từ các cặp original text và translation
    để AI hiểu được ngữ cảnh và dịch tốt hơn
    """
    
    def __init__(self):
        self.context_config = ContextConfig()
        self.loaded_files: Dict[str, pd.DataFrame] = {}  # file_path -> DataFrame
    
    def set_config(self, config: ContextConfig):
        """Set context configuration"""
        self.context_config = config
    
    def load_file(self, file_path: str, force_reload: bool = False) -> bool:
        """
        Load CSV file for context
        
        Args:
            file_path: Path to CSV file
            force_reload: Force reload even if already loaded
            
        Returns:
            True if successful
        """
        try:
            if file_path in self.loaded_files and not force_reload:
                return True
            
            df = pd.read_csv(file_path, encoding='utf-8')
            self.loaded_files[file_path] = df
            return True
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            return False
    
    def unload_file(self, file_path: str):
        """Unload file from memory"""
        if file_path in self.loaded_files:
            del self.loaded_files[file_path]
    
    def clear_all(self):
        """Clear all loaded files"""
        self.loaded_files.clear()
    
    def get_context_for_chunk(
        self,
        current_chunk_start: int,
        current_chunk_end: int,
        max_chunks: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get context chunks for a translation chunk
        
        Args:
            current_chunk_start: Start row of current chunk
            current_chunk_end: End row of current chunk
            max_chunks: Maximum number of context chunks to return
            
        Returns:
            List of context chunks in format [{"user": "...", "assistant": "..."}]
        """
        if max_chunks is None:
            max_chunks = self.context_config.max_context_chunks
        
        context_chunks = []
        
        for file_path in self.context_config.enabled_files:
            if file_path not in self.loaded_files:
                # Try to load file
                if not self.load_file(file_path):
                    continue
            
            df = self.loaded_files[file_path]
            
            # Extract context chunks from this file
            file_contexts = self._extract_context_from_dataframe(
                df,
                current_chunk_start,
                current_chunk_end
            )
            
            context_chunks.extend(file_contexts)
        
        # Limit to max chunks
        if len(context_chunks) > max_chunks:
            if self.context_config.reverse_order:
                # Take most recent (last) chunks
                context_chunks = context_chunks[-max_chunks:]
            else:
                # Take oldest (first) chunks
                context_chunks = context_chunks[:max_chunks]
        
        # Reverse order if configured
        if self.context_config.reverse_order:
            context_chunks = list(reversed(context_chunks))
        
        return context_chunks
    
    def _extract_context_from_dataframe(
        self,
        df: pd.DataFrame,
        current_start: int,
        current_end: int
    ) -> List[Dict[str, str]]:
        """
        Extract context chunks from a dataframe
        
        Args:
            df: DataFrame to extract from
            current_start: Start row of current chunk (to exclude it)
            current_end: End row of current chunk (to exclude it)
            
        Returns:
            List of context chunks
        """
        chunks = []
        
        # Check if required columns exist
        source_col = self.context_config.source_column
        trans_col = self.context_config.translation_column
        
        if source_col not in df.columns or trans_col not in df.columns:
            return chunks
        
        # Build chunks
        chunk_size = self.context_config.chunk_size
        num_rows = len(df)
        
        for start_idx in range(0, num_rows, chunk_size):
            end_idx = min(start_idx + chunk_size, num_rows)
            
            # Skip if this is the current chunk we're translating
            if start_idx >= current_start and end_idx <= current_end:
                continue
            
            # Extract rows for this chunk
            chunk_df = df.iloc[start_idx:end_idx]
            
            # Build context from chunk
            chunk_original = []
            chunk_translation = []
            
            has_valid_translation = False
            
            for _, row in chunk_df.iterrows():
                original = row[source_col]
                translation = row[trans_col]
                
                # Skip if not string
                if not isinstance(original, str):
                    original = str(original) if pd.notna(original) else ""
                if not isinstance(translation, str):
                    translation = str(translation) if pd.notna(translation) else ""
                
                # Check if has translation
                if translation and translation.strip():
                    has_valid_translation = True
                
                chunk_original.append(original)
                chunk_translation.append(translation)
            
            # Only include chunk if configured to include all or has translation
            if not self.context_config.only_translated_rows or has_valid_translation:
                # Join texts in chunk
                original_text = self._join_chunk_texts(chunk_original)
                translation_text = self._join_chunk_texts(chunk_translation)
                
                # Only add if both have content
                if original_text and translation_text:
                    context = {
                        "user": original_text,
                        "assistant": translation_text
                    }
                    
                    # Add row numbers if configured
                    if self.context_config.include_row_numbers:
                        context["rows"] = f"{start_idx}-{end_idx-1}"
                    
                    chunks.append(context)
        
        return chunks
    
    def _join_chunk_texts(self, texts: List[str]) -> str:
        """Join texts in a chunk"""
        # Filter out empty texts
        texts = [t.strip() for t in texts if t and t.strip()]
        
        # Join with newline
        return "\n".join(texts)
    
    def get_context_preview(
        self,
        max_chunks: int = 5
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Get a preview of context that would be sent
        
        Args:
            max_chunks: Maximum chunks to preview
            
        Returns:
            (context_chunks, stats) tuple where stats contains:
                - total_chunks: Total number of chunks available
                - total_chars: Total characters in context
                - files_included: Number of files included
        """
        context_chunks = []
        
        for file_path in self.context_config.enabled_files:
            if file_path not in self.loaded_files:
                if not self.load_file(file_path):
                    continue
            
            df = self.loaded_files[file_path]
            file_contexts = self._extract_context_from_dataframe(df, -1, -1)
            context_chunks.extend(file_contexts)
        
        # Calculate stats
        total_chunks = len(context_chunks)
        total_chars = sum(
            len(c.get("user", "")) + len(c.get("assistant", ""))
            for c in context_chunks
        )
        files_included = len([
            f for f in self.context_config.enabled_files
            if f in self.loaded_files
        ])
        
        stats = {
            "total_chunks": total_chunks,
            "total_chars": total_chars,
            "files_included": files_included,
            "estimated_tokens": total_chars // 4  # Rough estimate
        }
        
        # Return preview (limited chunks)
        preview_chunks = context_chunks[:max_chunks]
        
        return preview_chunks, stats
    
    def validate_context_files(self) -> Dict[str, bool]:
        """
        Validate that context files exist and have required columns
        
        Returns:
            Dict mapping file_path -> is_valid
        """
        results = {}
        
        for file_path in self.context_config.enabled_files:
            try:
                # Try to load
                if file_path not in self.loaded_files:
                    if not self.load_file(file_path):
                        results[file_path] = False
                        continue
                
                df = self.loaded_files[file_path]
                
                # Check columns
                has_source = self.context_config.source_column in df.columns
                has_translation = self.context_config.translation_column in df.columns
                
                results[file_path] = has_source and has_translation
                
            except Exception as e:
                print(f"Error validating {file_path}: {e}")
                results[file_path] = False
        
        return results
    
    def get_available_columns(self, file_path: str) -> List[str]:
        """Get available columns in a file"""
        try:
            if file_path not in self.loaded_files:
                if not self.load_file(file_path):
                    return []
            
            return list(self.loaded_files[file_path].columns)
        except Exception as e:
            print(f"Error getting columns from {file_path}: {e}")
            return []
    
    def estimate_context_size(self) -> Dict[str, Any]:
        """
        Estimate the size of context that would be sent
        
        Returns:
            Dictionary with size estimates
        """
        total_rows = 0
        total_chunks = 0
        total_chars = 0
        
        for file_path in self.context_config.enabled_files:
            if file_path not in self.loaded_files:
                if not self.load_file(file_path):
                    continue
            
            df = self.loaded_files[file_path]
            
            # Count valid rows
            if self.context_config.only_translated_rows:
                trans_col = self.context_config.translation_column
                if trans_col in df.columns:
                    valid_rows = df[trans_col].notna().sum()
                else:
                    valid_rows = 0
            else:
                valid_rows = len(df)
            
            total_rows += valid_rows
            
            # Estimate chunks
            file_chunks = (valid_rows + self.context_config.chunk_size - 1) // self.context_config.chunk_size
            total_chunks += file_chunks
            
            # Estimate characters
            source_col = self.context_config.source_column
            trans_col = self.context_config.translation_column
            
            if source_col in df.columns and trans_col in df.columns:
                source_chars = df[source_col].astype(str).str.len().sum()
                trans_chars = df[trans_col].astype(str).str.len().sum()
                total_chars += source_chars + trans_chars
        
        return {
            "total_rows": total_rows,
            "total_chunks": total_chunks,
            "total_chars": total_chars,
            "estimated_tokens": total_chars // 4,  # Rough estimate
            "chunks_per_request": min(total_chunks, self.context_config.max_context_chunks)
        }
    
    def export_context_preview(self, output_path: str, max_chunks: int = 10) -> bool:
        """
        Export context preview to a file for inspection
        
        Args:
            output_path: Path to save preview
            max_chunks: Maximum chunks to include
            
        Returns:
            True if successful
        """
        try:
            context_chunks, stats = self.get_context_preview(max_chunks)
            
            output = {
                "config": self.context_config.to_dict(),
                "stats": stats,
                "preview_chunks": context_chunks[:max_chunks]
            }
            
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error exporting context preview: {e}")
            return False
