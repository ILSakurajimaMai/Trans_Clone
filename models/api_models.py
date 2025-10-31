"""
API Service Models - Định nghĩa các model cho custom API services
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from enum import Enum
import json
from datetime import datetime


class APIProviderType(Enum):
    """Các loại API provider"""
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"  # Custom API endpoint


class AuthType(Enum):
    """Các loại authentication"""
    BEARER_TOKEN = "bearer"
    API_KEY_HEADER = "api_key_header"
    BASIC_AUTH = "basic"
    OAUTH2 = "oauth2"


@dataclass
class APIEndpointConfig:
    """Cấu hình cho API endpoint"""
    url: str
    method: str = "POST"  # GET, POST, PUT, etc.
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIEndpointConfig':
        return cls(**data)


@dataclass
class RequestFormat:
    """Format cho API request"""
    # Template cho request body sử dụng placeholders
    # Ví dụ: {"messages": [{"role": "user", "content": "{text}"}]}
    body_template: Dict[str, Any] = field(default_factory=dict)
    
    # Mapping từ các field chuẩn sang field của API
    field_mapping: Dict[str, str] = field(default_factory=dict)
    
    # Các parameters bổ sung
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RequestFormat':
        return cls(**data)


@dataclass
class ResponseFormat:
    """Format cho API response"""
    # Path đến text trong response (dùng dot notation)
    # Ví dụ: "choices.0.message.content" hoặc "content.0.text"
    text_path: str
    
    # Path đến các metadata khác
    usage_path: Optional[str] = None
    error_path: Optional[str] = None
    
    # Custom parser function name (nếu cần)
    custom_parser: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResponseFormat':
        return cls(**data)


@dataclass
class APIServiceConfig:
    """Cấu hình đầy đủ cho một API service"""
    # Thông tin cơ bản
    id: str  # Unique identifier
    name: str  # Display name
    provider_type: APIProviderType
    description: str = ""
    
    # Authentication
    auth_type: AuthType = AuthType.BEARER_TOKEN
    api_key_header_name: str = "Authorization"  # Header name cho API key
    api_key_prefix: str = "Bearer"  # Prefix cho API key (Bearer, Api-Key, etc.)
    
    # Endpoint configuration
    endpoint: APIEndpointConfig = field(default_factory=APIEndpointConfig)
    
    # Request/Response format
    request_format: RequestFormat = field(default_factory=RequestFormat)
    response_format: ResponseFormat = field(default_factory=ResponseFormat)
    
    # Model parameters
    model_name: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95
    
    # Status
    is_active: bool = True
    is_custom: bool = False
    
    # Metadata
    created_at: str = ""
    last_modified: str = ""
    last_tested: Optional[str] = None
    test_status: str = "untested"  # untested, success, failed
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_modified:
            self.last_modified = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['provider_type'] = self.provider_type.value
        data['auth_type'] = self.auth_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIServiceConfig':
        # Convert enum strings back to enums
        if 'provider_type' in data:
            data['provider_type'] = APIProviderType(data['provider_type'])
        if 'auth_type' in data:
            data['auth_type'] = AuthType(data['auth_type'])
        
        # Convert nested objects
        if 'endpoint' in data and isinstance(data['endpoint'], dict):
            data['endpoint'] = APIEndpointConfig.from_dict(data['endpoint'])
        if 'request_format' in data and isinstance(data['request_format'], dict):
            data['request_format'] = RequestFormat.from_dict(data['request_format'])
        if 'response_format' in data and isinstance(data['response_format'], dict):
            data['response_format'] = ResponseFormat.from_dict(data['response_format'])
        
        return cls(**data)
    
    def update_test_status(self, success: bool, message: str = ""):
        """Update test status"""
        self.last_tested = datetime.now().isoformat()
        self.test_status = "success" if success else "failed"
        self.last_modified = self.last_tested


@dataclass
class ContextConfig:
    """Cấu hình cho context management"""
    # Files to include in context
    enabled_files: List[str] = field(default_factory=list)
    
    # Columns to use for context
    source_column: str = "original text"
    translation_column: str = "Initial"
    
    # Context settings
    chunk_size: int = 50
    max_context_chunks: int = 10  # Maximum chunks to include as context
    only_translated_rows: bool = True  # Chỉ include rows đã có translation
    
    # Context format
    include_row_numbers: bool = False
    reverse_order: bool = False  # Newest first
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextConfig':
        return cls(**data)


@dataclass
class SummaryEntry:
    """Một entry trong summary history"""
    id: str
    timestamp: str
    system_instruction: str
    context_files: List[str]
    context_config: ContextConfig
    model_used: str
    result: str
    tokens_used: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['context_config'] = self.context_config.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SummaryEntry':
        if 'context_config' in data and isinstance(data['context_config'], dict):
            data['context_config'] = ContextConfig.from_dict(data['context_config'])
        return cls(**data)


@dataclass
class SystemInstructionTemplate:
    """Template cho system instruction"""
    id: str
    name: str
    description: str
    instruction_type: str  # "translation" hoặc "summary"
    content: str
    variables: List[str] = field(default_factory=list)  # Các biến có thể customize
    is_default: bool = False
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemInstructionTemplate':
        return cls(**data)


# Predefined API service templates
PREDEFINED_SERVICES = {
    "google_gemini": APIServiceConfig(
        id="google_gemini",
        name="Google Gemini",
        provider_type=APIProviderType.GOOGLE,
        description="Google Gemini API",
        endpoint=APIEndpointConfig(
            url="https://generativelanguage.googleapis.com/v1/models/{model}:generateContent",
            method="POST"
        ),
        request_format=RequestFormat(
            body_template={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": "{text}"}]
                    }
                ],
                "generationConfig": {
                    "temperature": "{temperature}",
                    "maxOutputTokens": "{max_tokens}",
                    "topP": "{top_p}"
                }
            },
            field_mapping={
                "text": "contents.0.parts.0.text",
                "system_instruction": "system_instruction.parts.0.text"
            }
        ),
        response_format=ResponseFormat(
            text_path="candidates.0.content.parts.0.text",
            usage_path="usageMetadata"
        ),
        model_name="gemini-2.0-flash-exp",
        is_custom=False
    ),
    
    "openai_gpt": APIServiceConfig(
        id="openai_gpt",
        name="OpenAI GPT",
        provider_type=APIProviderType.OPENAI,
        description="OpenAI GPT API",
        endpoint=APIEndpointConfig(
            url="https://api.openai.com/v1/chat/completions",
            method="POST"
        ),
        request_format=RequestFormat(
            body_template={
                "model": "{model}",
                "messages": [],  # Will be filled dynamically
                "temperature": "{temperature}",
                "max_tokens": "{max_tokens}"
            }
        ),
        response_format=ResponseFormat(
            text_path="choices.0.message.content",
            usage_path="usage"
        ),
        model_name="gpt-4",
        is_custom=False
    ),
    
    "anthropic_claude": APIServiceConfig(
        id="anthropic_claude",
        name="Anthropic Claude",
        provider_type=APIProviderType.ANTHROPIC,
        description="Anthropic Claude API",
        auth_type=AuthType.API_KEY_HEADER,
        api_key_header_name="x-api-key",
        api_key_prefix="",
        endpoint=APIEndpointConfig(
            url="https://api.anthropic.com/v1/messages",
            method="POST",
            headers={
                "anthropic-version": "2023-06-01"
            }
        ),
        request_format=RequestFormat(
            body_template={
                "model": "{model}",
                "messages": [],
                "max_tokens": "{max_tokens}",
                "temperature": "{temperature}"
            }
        ),
        response_format=ResponseFormat(
            text_path="content.0.text",
            usage_path="usage"
        ),
        model_name="claude-3-sonnet-20240229",
        is_custom=False
    )
}


def get_predefined_service(service_id: str) -> Optional[APIServiceConfig]:
    """Get a predefined service config"""
    return PREDEFINED_SERVICES.get(service_id)


def get_all_predefined_services() -> List[APIServiceConfig]:
    """Get all predefined service configs"""
    return list(PREDEFINED_SERVICES.values())
