"""
Default CSV Parser - Standard CSV parsing
"""

import pandas as pd
from typing import Optional
from pathlib import Path

from models.data_structures import CSVParserConfig
from modules.csv_parser.base_parser import BaseCSVParser, parser_registry


class DefaultCSVParser(BaseCSVParser):
    """
    Default CSV parser using pandas.read_csv
    """
    
    def _get_default_config(self) -> CSVParserConfig:
        """Get default configuration"""
        return CSVParserConfig(
            parser_id="default",
            name="Default CSV Parser",
            parser_type="default",
            description="Standard CSV parser using pandas",
            delimiter=",",
            encoding="utf-8",
            skip_rows=0,
            required_columns=["original text"]
        )
    
    def parse(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Parse CSV file using pandas
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame or None if parsing failed
        """
        try:
            # Check if file exists
            if not Path(file_path).exists():
                self.last_error = f"File not found: {file_path}"
                return None
            
            # Read CSV
            df = pd.read_csv(
                file_path,
                delimiter=self.config.delimiter,
                encoding=self.config.encoding,
                skiprows=self.config.skip_rows,
                keep_default_na=False  # Don't convert empty strings to NaN
            )
            
            return df
            
        except Exception as e:
            self.last_error = f"Error parsing CSV: {str(e)}"
            print(self.last_error)
            return None
    
    def auto_detect_encoding(self, file_path: str) -> Optional[str]:
        """
        Auto-detect file encoding
        
        Args:
            file_path: Path to file
            
        Returns:
            Detected encoding or None
        """
        try:
            import chardet
            
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read())
                return result['encoding']
        except ImportError:
            # chardet not available, try common encodings
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read()
                    return encoding
                except:
                    continue
        except Exception as e:
            print(f"Error detecting encoding: {e}")
        
        return None
    
    def parse_with_auto_encoding(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Parse CSV with automatic encoding detection
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame or None if parsing failed
        """
        # Try configured encoding first
        df = self.parse(file_path)
        if df is not None:
            return df
        
        # Try auto-detect
        detected_encoding = self.auto_detect_encoding(file_path)
        if detected_encoding and detected_encoding != self.config.encoding:
            print(f"Auto-detected encoding: {detected_encoding}")
            old_encoding = self.config.encoding
            self.config.encoding = detected_encoding
            df = self.parse(file_path)
            self.config.encoding = old_encoding  # Restore original
            return df
        
        return None


# Register default parser
parser_registry.register("default", DefaultCSVParser)
