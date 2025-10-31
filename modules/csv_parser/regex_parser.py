"""
Regex CSV Parser - Parse complex script files using regex patterns
"""

import pandas as pd
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

from models.data_structures import CSVParserConfig
from modules.csv_parser.base_parser import BaseCSVParser, parser_registry


class RegexCSVParser(BaseCSVParser):
    """
    Regex-based parser for complex script files
    
    Cho phép người dùng định nghĩa regex pattern để extract data
    từ các file script phức tạp và chuyển sang dạng bảng CSV
    """
    
    def _get_default_config(self) -> CSVParserConfig:
        """Get default configuration"""
        return CSVParserConfig(
            parser_id="regex",
            name="Regex Parser",
            parser_type="regex",
            description="Parse files using custom regex patterns",
            regex_pattern=None,
            regex_groups={}
        )
    
    def parse(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Parse file using regex pattern
        
        Args:
            file_path: Path to file
            
        Returns:
            DataFrame or None if parsing failed
        """
        try:
            # Check configuration
            if not self.config.regex_pattern:
                self.last_error = "No regex pattern configured"
                return None
            
            if not self.config.regex_groups:
                self.last_error = "No regex groups configured"
                return None
            
            # Check if file exists
            if not Path(file_path).exists():
                self.last_error = f"File not found: {file_path}"
                return None
            
            # Read file
            with open(file_path, 'r', encoding=self.config.encoding) as f:
                content = f.read()
            
            # Skip rows if configured
            if self.config.skip_rows > 0:
                lines = content.split('\n')
                content = '\n'.join(lines[self.config.skip_rows:])
            
            # Apply regex
            pattern = re.compile(self.config.regex_pattern, re.MULTILINE | re.DOTALL)
            matches = pattern.finditer(content)
            
            # Extract data
            data = []
            for match in matches:
                row = {}
                for column_name, group_index in self.config.regex_groups.items():
                    try:
                        value = match.group(group_index)
                        row[column_name] = value if value else ""
                    except IndexError:
                        row[column_name] = ""
                
                if row:  # Only add non-empty rows
                    data.append(row)
            
            if not data:
                self.last_error = "No matches found with regex pattern"
                return None
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            return df
            
        except re.error as e:
            self.last_error = f"Invalid regex pattern: {str(e)}"
            print(self.last_error)
            return None
        except Exception as e:
            self.last_error = f"Error parsing with regex: {str(e)}"
            print(self.last_error)
            return None
    
    def test_pattern(
        self, 
        sample_text: str, 
        max_matches: int = 5
    ) -> List[Dict[str, str]]:
        """
        Test regex pattern on sample text
        
        Args:
            sample_text: Sample text to test on
            max_matches: Maximum matches to return
            
        Returns:
            List of matches with extracted groups
        """
        try:
            if not self.config.regex_pattern:
                return []
            
            pattern = re.compile(self.config.regex_pattern, re.MULTILINE | re.DOTALL)
            matches = pattern.finditer(sample_text)
            
            results = []
            for i, match in enumerate(matches):
                if i >= max_matches:
                    break
                
                result = {
                    "match": match.group(0),
                    "groups": {}
                }
                
                for column_name, group_index in self.config.regex_groups.items():
                    try:
                        result["groups"][column_name] = match.group(group_index)
                    except IndexError:
                        result["groups"][column_name] = None
                
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error testing pattern: {e}")
            return []
    
    def set_pattern(self, pattern: str, groups: Dict[str, int]):
        """
        Set regex pattern and groups
        
        Args:
            pattern: Regex pattern
            groups: Dictionary mapping column names to group indices
        """
        self.config.regex_pattern = pattern
        self.config.regex_groups = groups
    
    def validate_pattern(self) -> tuple[bool, str]:
        """
        Validate regex pattern
        
        Returns:
            (is_valid, error_message) tuple
        """
        try:
            if not self.config.regex_pattern:
                return False, "Pattern is empty"
            
            # Try to compile pattern
            re.compile(self.config.regex_pattern)
            
            # Check groups
            if not self.config.regex_groups:
                return False, "No groups defined"
            
            # Check group indices are valid
            for column_name, group_index in self.config.regex_groups.items():
                if not isinstance(group_index, int) or group_index < 0:
                    return False, f"Invalid group index for {column_name}: {group_index}"
            
            return True, "Pattern is valid"
            
        except re.error as e:
            return False, f"Invalid regex: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"


class TextBlockParser(BaseCSVParser):
    """
    Parser for text files with repeated blocks
    
    Ví dụ: Visual novel scripts với format:
    [Name]
    Text line 1
    Text line 2
    
    [Another Name]
    More text
    """
    
    def _get_default_config(self) -> CSVParserConfig:
        """Get default configuration"""
        return CSVParserConfig(
            parser_id="text_block",
            name="Text Block Parser",
            parser_type="regex",
            description="Parse text files with repeated block structure",
            # Default pattern for name + text blocks
            regex_pattern=r'\[([^\]]+)\]\s*\n((?:(?!\[)[^\n]+\n?)*)',
            regex_groups={
                "Speaker": 1,
                "original text": 2
            }
        )
    
    def parse(self, file_path: str) -> Optional[pd.DataFrame]:
        """Parse text block file"""
        # Use regex parser logic
        return super().parse(file_path)


# Register parsers
parser_registry.register("regex", RegexCSVParser)
parser_registry.register("text_block", TextBlockParser)


# Example patterns for common formats
EXAMPLE_PATTERNS = {
    "visual_novel_brackets": {
        "name": "Visual Novel [Name] Format",
        "pattern": r'\[([^\]]+)\]\s*\n([^\[]+)',
        "groups": {
            "Speaker": 1,
            "original text": 2
        },
        "description": "Parse format: [Name]\\nText content"
    },
    
    "dialogue_colon": {
        "name": "Dialogue with Colon",
        "pattern": r'([^:]+):\s*([^\n]+)',
        "groups": {
            "Speaker": 1,
            "original text": 2
        },
        "description": "Parse format: Name: Text"
    },
    
    "numbered_lines": {
        "name": "Numbered Lines",
        "pattern": r'(\d+)\.\s*([^\n]+)',
        "groups": {
            "Line": 1,
            "original text": 2
        },
        "description": "Parse format: 1. Text"
    },
    
    "xml_tags": {
        "name": "XML/HTML Tags",
        "pattern": r'<([^>]+)>([^<]+)</\1>',
        "groups": {
            "Tag": 1,
            "original text": 2
        },
        "description": "Parse format: <tag>text</tag>"
    },
    
    "json_like": {
        "name": "JSON-like Format",
        "pattern": r'"([^"]+)"\s*:\s*"([^"]+)"',
        "groups": {
            "Key": 1,
            "original text": 2
        },
        "description": 'Parse format: "key": "value"'
    }
}


def get_example_pattern(pattern_id: str) -> Optional[Dict[str, Any]]:
    """Get example pattern by ID"""
    return EXAMPLE_PATTERNS.get(pattern_id)


def get_all_example_patterns() -> Dict[str, Dict[str, Any]]:
    """Get all example patterns"""
    return EXAMPLE_PATTERNS
