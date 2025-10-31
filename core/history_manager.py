"""
History manager for translation history operations with LangGraph compatibility
"""

import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from models.data_structures import HistoryEntry, ChatHistory, ChatMessage
from utils.file_utils import ConfigManager


class HistoryManager:
    """Manage translation history with LangGraph compatibility and modification tracking"""

    def __init__(self, history_file: str = ""):
        self.history_file = history_file
        self.chat_history = ChatHistory()
        self.max_history_entries = 100
        self.summarization_threshold = 20
        # Track modifications for updating history
        self.pending_modifications = []

    def set_history_file(self, file_path: str):
        """Set the history file path"""
        self.history_file = file_path

    def add_user_message(self, content: str, context_data: Dict[str, Any] = None):
        """Add a user message to the chat history"""
        self.chat_history.add_message("human", content)

        # Also add to legacy format for compatibility
        entry = HistoryEntry(
            role="user",
            parts=[content],
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            context_data=context_data or {},
        )

    def add_ai_message(self, content: str, model_name: str = ""):
        """Add an AI response message to the chat history"""
        self.chat_history.add_message("ai", content)
        self.chat_history.model_name = model_name

        # Also add to legacy format for compatibility
        entry = HistoryEntry(
            role="assistant",
            parts=[content],
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            model_name=model_name,
        )

    def add_translation_entry(
        self,
        original_texts: List[str],
        translated_texts: List[str],
        model_name: str = "",
        target_column: str = "Initial",
    ):
        """Add a complete translation entry with enhanced tracking"""
        # Create structured data for the request
        translation_request = {
            "action": "translate",
            "target_column": target_column,
            "chunk_count": len(original_texts),
            "texts": original_texts,
        }

        user_content = f"Translate to {target_column} column:\n{json.dumps(original_texts, ensure_ascii=False)}"
        self.add_user_message(
            user_content, {"translation_request": translation_request}
        )

        # Create AI response with metadata
        response_data = {
            "translation": translated_texts,
            "target_column": target_column,
            "model": model_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        ai_content = json.dumps(response_data, ensure_ascii=False)
        self.add_ai_message(ai_content, model_name)

    def update_translation_from_modifications(
        self,
        original_texts: List[str],
        current_texts: List[str],
        target_column: str = "Initial",
    ):
        """Update history based on user modifications to translations"""
        if not original_texts or not current_texts:
            return

        # Find differences
        modifications = []
        for i, (orig, curr) in enumerate(zip(original_texts, current_texts)):
            if orig != curr:
                modifications.append(
                    {"line": i + 1, "original": orig, "modified": curr}
                )

        if modifications:
            # Add modification entry to history
            modification_data = {
                "action": "modify_translation",
                "target_column": target_column,
                "modifications": modifications,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            user_content = f"Modified translations in {target_column}:\n{json.dumps(modification_data, ensure_ascii=False)}"
            self.add_user_message(
                user_content, {"modification_data": modification_data}
            )

            # Update the latest AI response in history if possible
            if self.chat_history.messages:
                for message in reversed(self.chat_history.messages):
                    if message.role == "ai":
                        try:
                            response_data = json.loads(message.content)
                            if "translation" in response_data:
                                response_data["translation"] = current_texts
                                response_data["last_modified"] = time.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                message.content = json.dumps(
                                    response_data, ensure_ascii=False
                                )
                                break
                        except Exception as e:
                            print(f"Error updating translation history: {e}")

    def get_chat_history_for_api(self) -> List[Dict[str, Any]]:
        """Get chat history in format suitable for LangGraph/LangChain APIs"""
        return self.chat_history.to_langgraph_format()

    def get_recent_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context for API calls"""
        recent_messages = (
            self.chat_history.messages[-max_messages:]
            if self.chat_history.messages
            else []
        )
        return [{"role": msg.role, "content": msg.content} for msg in recent_messages]

    def clear_history(self):
        """Clear all history"""
        self.chat_history = ChatHistory()

    def load_history(self) -> bool:
        """Load history from file"""
        if not self.history_file:
            return False

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if it's in LangGraph format
            if isinstance(data, list) and data and "role" in data[0]:
                self.chat_history.from_langgraph_format(data)
            elif isinstance(data, dict) and "messages" in data:
                # New structured format
                self.chat_history = ChatHistory()
                self.chat_history.from_langgraph_format(data["messages"])
                if "context_id" in data:
                    self.chat_history.context_id = data["context_id"]
                if "model_provider" in data:
                    self.chat_history.model_provider = data["model_provider"]
                if "model_name" in data:
                    self.chat_history.model_name = data["model_name"]
            else:
                # Legacy format - convert to new format
                self.chat_history = ChatHistory()
                for entry in data:
                    if isinstance(entry, dict):
                        role = entry.get("role", "human")
                        if role == "user":
                            role = "human"
                        elif role == "model":
                            role = "ai"

                        content = (
                            entry.get("parts", [""])[0] if entry.get("parts") else ""
                        )
                        self.chat_history.add_message(role, content)

            return True

        except Exception as e:
            print(f"Error loading history: {e}")
            return False

    def save_history(self) -> bool:
        """Save history to file in LangGraph-compatible format"""
        if not self.history_file:
            return False

        try:
            # Save in structured format with metadata
            save_data = {
                "format_version": "1.0",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "context_id": self.chat_history.context_id,
                "model_provider": (
                    self.chat_history.model_provider.value
                    if self.chat_history.model_provider
                    else None
                ),
                "model_name": self.chat_history.model_name,
                "messages": self.chat_history.to_langgraph_format(),
            }

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"Error saving history: {e}")
            return False

    def should_summarize(self) -> bool:
        """Check if history should be summarized"""
        return len(self.chat_history.messages) >= self.summarization_threshold

    def create_summary_from_history(self) -> str:
        """Create a summary of the translation history"""
        if not self.chat_history.messages:
            return ""

        # Extract translation data
        translations = []
        modifications = []

        for message in self.chat_history.messages:
            try:
                if message.role == "human" and "translate" in message.content.lower():
                    # Extract original texts
                    content = message.content
                    if ":" in content:
                        json_part = content.split(":", 1)[1].strip()
                        original_texts = json.loads(json_part)
                        if isinstance(original_texts, list):
                            translations.append(original_texts)

                elif message.role == "ai":
                    # Extract AI responses
                    try:
                        response_data = json.loads(message.content)
                        if "translation" in response_data:
                            continue  # Already processed with user message
                    except Exception as e:
                        print(f"Error parsing AI response: {e}")
                        continue

                elif message.role == "human" and "modified" in message.content.lower():
                    # Extract modifications
                    try:
                        mod_data = json.loads(message.content.split(":", 1)[1].strip())
                        if "modifications" in mod_data:
                            modifications.extend(mod_data["modifications"])
                    except Exception as e:
                        print(f"Error parsing modification data: {e}")
                        continue

            except Exception as e:
                print(f"Error processing history message: {e}")
                continue

        # Create summary
        summary_parts = []

        if translations:
            total_lines = sum(len(t) for t in translations)
            summary_parts.append(f"**Tổng số dòng đã dịch**: {total_lines}")
            summary_parts.append(f"**Số lần dịch**: {len(translations)}")

        if modifications:
            summary_parts.append(f"**Số chỗ đã sửa**: {len(modifications)}")

            # Show some example modifications
            example_mods = modifications[:3]
            mod_examples = []
            for mod in example_mods:
                original = mod.get("original", "")[:50]
                modified = mod.get("modified", "")[:50]
                mod_examples.append(
                    f"Dòng {mod.get('line', '?')}: '{original}' → '{modified}'"
                )

            if mod_examples:
                summary_parts.append(f"**Ví dụ sửa đổi**:\n" + "\n".join(mod_examples))

        # Character analysis
        all_text = []
        for translation_list in translations:
            all_text.extend(translation_list)

        if all_text:
            # Extract character names and common terms
            characters = set()
            for text in all_text:
                if any(suffix in text for suffix in ["君", "さん", "ちゃん", "先輩"]):
                    import re

                    char_matches = re.findall(r"(\w+)(?:君|さん|ちゃん|先輩)", text)
                    characters.update(char_matches)

            if characters:
                summary_parts.append(f"**Nhân vật**: {', '.join(sorted(characters))}")

        return (
            "\n\n".join(summary_parts)
            if summary_parts
            else "Chưa có lịch sử dịch thuật."
        )

    def summarize_history(self, translation_engine=None) -> bool:
        """Summarize the current history to reduce size"""
        try:
            if not self.should_summarize():
                return True

            # Create summary
            summary_text = self.create_summary_from_history()

            # If we have a translation engine, use it for better summarization
            if translation_engine and hasattr(translation_engine, "models"):
                try:
                    # Use AI to create a better summary
                    from langchain.schema import HumanMessage, SystemMessage

                    system_prompt = """You are an assistant summarizing key context from a Vietnamese translation project.

**Task**: Analyze the translation history and summarize the main details to create context for future translations. Focus on:
1) **Story Progression**: Main events that occurred
2) **Character Details**: Names, relationships, and how they address each other
3) **Special Terms**: Recurring terminology or expressions
4) **Other Important Information**: Any details necessary for consistent translation

**Requirements**:
- Respond **in Vietnamese**
- Keep concise and clear
- Focus on translation consistency details"""

                    # Use Google model if available
                    google_model = translation_engine.models.get("google")
                    if google_model:
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(
                                content=f"Summarize this translation context:\n{summary_text}"
                            ),
                        ]

                        response = google_model.invoke(messages)
                        summary_text = response.content

                except Exception as e:
                    print(f"Error in AI summarization: {e}")
                    # Fall back to manual summary

            # Keep first few entries for context
            preserved_entries = (
                self.chat_history.messages[:2]
                if len(self.chat_history.messages) >= 2
                else []
            )

            # Add summary entry
            summary_entry = ChatMessage(
                role="user",
                content=f"(TÓM TẮT) {summary_text}",
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

            response_entry = ChatMessage(
                role="ai",
                content="Tôi đã hiểu, tôi sẽ dùng tóm tắt này làm ngữ cảnh cho các lần dịch sắp tới.",
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

            # Keep recent entries
            recent_entries = (
                self.chat_history.messages[-4:]
                if len(self.chat_history.messages) >= 4
                else []
            )

            # Rebuild history
            new_history = (
                preserved_entries + [summary_entry, response_entry] + recent_entries
            )
            self.chat_history.messages = new_history

            return True

        except Exception as e:
            print(f"Error summarizing history: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the translation history"""
        stats = {
            "total_entries": len(self.chat_history.messages),
            "user_entries": len(
                [m for m in self.chat_history.messages if m.role == "human"]
            ),
            "model_entries": len(
                [m for m in self.chat_history.messages if m.role == "ai"]
            ),
            "translation_pairs": 0,
            "models_used": set(),
            "date_range": None,
        }

        # Count translation pairs
        i = 0
        while i < len(self.chat_history.messages) - 1:
            if (
                self.chat_history.messages[i].role == "human"
                and self.chat_history.messages[i + 1].role == "ai"
            ):
                stats["translation_pairs"] += 1
                i += 2
            else:
                i += 1

        # Collect models used
        for message in self.chat_history.messages:
            if message.model_name:
                stats["models_used"].add(message.model_name)

        stats["models_used"] = list(stats["models_used"])

        # Date range
        if self.chat_history.messages:
            timestamps = [
                m.timestamp for m in self.chat_history.messages if m.timestamp
            ]
            if timestamps:
                stats["date_range"] = {"start": min(timestamps), "end": max(timestamps)}

        return stats

    # -------------------------------
    # New helper methods for chunk-wise chat history editing
    # -------------------------------
    def _build_chunks(
        self,
        original_texts: list[str],
        translated_texts: list[str],
        chunk_size: int,
    ) -> list[tuple[int, list[str], list[str]]]:
        """Split texts into equal-sized chunks.

        Returns list of tuples: (chunk_index, original_lines, translated_lines)
        """
        assert len(original_texts) == len(translated_texts)
        chunks = []
        idx = 0
        total = len(original_texts)
        chunk_index = 0
        while idx < total:
            end = min(idx + chunk_size, total)
            chunks.append(
                (chunk_index, original_texts[idx:end], translated_texts[idx:end])
            )
            chunk_index += 1
            idx = end
        return chunks

    def update_history_for_file(
        self,
        file_name: str,
        dataframe,
        chunk_size: int = 50,
        target_column: str = "Machine translation",
    ) -> bool:
        """Create or replace chat history blocks for a specific CSV file.

        Args:
            file_name: base name of CSV file (without path)
            dataframe: current DataFrame after user edits
            chunk_size: chunk size to split lines (use existing if found)
            target_column: column containing translated texts
        """
        try:
            # Extract texts from DataFrame
            if dataframe.empty:
                return False

            original_col_idx = 0  # assume first col is original
            original_texts = (
                dataframe.iloc[:, original_col_idx].fillna("").astype(str).tolist()
            )
            if target_column not in dataframe.columns:
                target_column = dataframe.columns[-1]
            translated_texts = dataframe[target_column].fillna("").astype(str).tolist()

            # Build new chunk blocks
            new_chunks = self._build_chunks(
                original_texts, translated_texts, chunk_size
            )

            # Ensure history is loaded
            if self.history_file:
                self.load_history()

            # Remove existing chunks for this file
            def _is_chunk_of_file(msg_content: str) -> bool:
                return file_name in msg_content and msg_content.startswith(
                    "đây là chunk_"
                )

            filtered_messages = []
            i = 0
            while i < len(self.chat_history.messages):
                msg = self.chat_history.messages[i]
                if msg.role == "human" and _is_chunk_of_file(msg.content):
                    # Skip the pair (user, ai)
                    i += 2  # assumes well-formed pairs
                    continue
                filtered_messages.append(msg)
                i += 1
            self.chat_history.messages = filtered_messages

            # Append new chunks at end
            for chunk_index, orig_lines, trans_lines in new_chunks:
                user_content = (
                    f"đây là chunk_{chunk_index}_{file_name} cần dịch: "
                    + json.dumps(orig_lines, ensure_ascii=False)
                )
                model_content = "đây là kết quả dịch: " + json.dumps(
                    trans_lines, ensure_ascii=False
                )
                self.chat_history.add_message("human", user_content)
                self.chat_history.add_message("ai", model_content)

            return self.save_history()

        except Exception as e:
            print(f"Error updating history for {file_name}: {e}")
            return False
