"""
Base CSV Parser - Abstract base class cho các CSV parsers
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any, List
from pathlib import Path

from models.data_structures import CSVParserConfig


class BaseCSVParser(ABC):
    """
    Abstract base class cho CSV parsers
    
    Tất cả custom parsers phải kế thừa từ class này
    """
    
    def __init__(self, config: Optional[CSVParserConfig] = None):
        """
        Initialize parser
        
        Args:
            config: Parser configuration
        """
        self.config = config or self._get_default_config()
        self.last_error: Optional[str] = None
    
    @abstractmethod
    def _get_default_config(self) -> CSVParserConfig:
        """Get default configuration for this parser"""
        pass
    
    @abstractmethod
    def parse(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Parse CSV file and return DataFrame
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame or None if parsing failed
        """
        pass
    
    def validate(self, df: pd.DataFrame) -> bool:
        """
        Validate parsed DataFrame
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid
        """
        if df is None or df.empty:
            self.last_error = "DataFrame is empty"
            return False
        
        # Check required columns
        if self.config.required_columns:
            missing = set(self.config.required_columns) - set(df.columns)
            if missing:
                self.last_error = f"Missing required columns: {missing}"
                return False
        
        return True
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformations to DataFrame
        
        Args:
            df: Input DataFrame
            
        Returns:
            Transformed DataFrame
        """
        # Apply column mapping if configured
        if self.config.column_mapping:
            df = df.rename(columns=self.config.column_mapping)
        
        return df
    
    def process(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Full processing pipeline: parse -> validate -> transform
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Processed DataFrame or None if failed
        """
        try:
            # Parse
            df = self.parse(file_path)
            if df is None:
                return None
            
            # Validate
            if not self.validate(df):
                return None
            
            # Transform
            df = self.transform(df)
            
            return df
            
        except Exception as e:
            self.last_error = str(e)
            print(f"Error processing file: {e}")
            return None
    
    def get_last_error(self) -> Optional[str]:
        """Get last error message"""
        return self.last_error
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information"""
        return {
            "parser_id": self.config.parser_id,
            "name": self.config.name,
            "type": self.config.parser_type,
            "description": self.config.description
        }
    
    def set_config(self, config: CSVParserConfig):
        """Update parser configuration"""
        self.config = config
    
    def get_config(self) -> CSVParserConfig:
        """Get parser configuration"""
        return self.config


class ParserRegistry:
    """
    Registry for managing CSV parsers
    """
    
    def __init__(self):
        self.parsers: Dict[str, type] = {}
    
    def register(self, parser_id: str, parser_class: type):
        """Register a parser class"""
        if not issubclass(parser_class, BaseCSVParser):
            raise ValueError(f"Parser class must inherit from BaseCSVParser")
        self.parsers[parser_id] = parser_class
    
    def get_parser(
        self, 
        parser_id: str, 
        config: Optional[CSVParserConfig] = None
    ) -> Optional[BaseCSVParser]:
        """Get parser instance"""
        parser_class = self.parsers.get(parser_id)
        if parser_class:
            return parser_class(config)
        return None
    
    def list_parsers(self) -> List[str]:
        """List registered parser IDs"""
        return list(self.parsers.keys())
    
    def unregister(self, parser_id: str):
        """Unregister a parser"""
        if parser_id in self.parsers:
            del self.parsers[parser_id]


# Global parser registry
parser_registry = ParserRegistry()
