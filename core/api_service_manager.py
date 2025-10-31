"""
API Service Manager - Quản lý API services và authentication
"""

import json
import os
import requests
from typing import Dict, List, Optional, Any, Callable, Tuple
from pathlib import Path
from datetime import datetime
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib

from models.api_models import (
    APIServiceConfig,
    APIProviderType,
    AuthType,
    get_predefined_service,
    get_all_predefined_services,
    PREDEFINED_SERVICES
)


class EncryptionManager:
    """Quản lý mã hóa API keys"""
    
    def __init__(self, master_password: Optional[str] = None):
        """
        Initialize encryption manager
        
        Args:
            master_password: Master password for encryption. If None, uses machine-specific key
        """
        self.master_password = master_password or self._get_machine_key()
        self.fernet = self._init_fernet()
    
    def _get_machine_key(self) -> str:
        """Get machine-specific key"""
        # Sử dụng machine ID hoặc username để tạo key cố định cho máy
        import platform
        import getpass
        machine_id = f"{platform.node()}-{getpass.getuser()}"
        return hashlib.sha256(machine_id.encode()).hexdigest()
    
    def _init_fernet(self) -> Fernet:
        """Initialize Fernet cipher"""
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'csv_translator_salt',  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_password.encode())
        )
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string"""
        if not plaintext:
            return ""
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt a string"""
        if not encrypted_text:
            return ""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return ""


class APIServiceManager:
    """Quản lý các API services"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize API Service Manager
        
        Args:
            config_dir: Directory to store service configurations
        """
        self.config_dir = Path(config_dir) if config_dir else Path.home() / ".csv_translator"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.services_file = self.config_dir / "api_services.json"
        self.keys_file = self.config_dir / "api_keys.enc"
        
        self.encryption_manager = EncryptionManager()
        
        # Storage
        self.services: Dict[str, APIServiceConfig] = {}
        self.api_keys: Dict[str, str] = {}  # service_id -> encrypted_key
        
        # Load existing configurations
        self.load_services()
        self.load_api_keys()
        
        # Initialize predefined services if empty
        if not self.services:
            self._initialize_predefined_services()
    
    def _initialize_predefined_services(self):
        """Initialize with predefined services"""
        for service_id, config in PREDEFINED_SERVICES.items():
            self.services[service_id] = config
        self.save_services()
    
    def add_service(self, config: APIServiceConfig) -> bool:
        """
        Add or update a service configuration
        
        Args:
            config: API service configuration
            
        Returns:
            True if successful
        """
        try:
            config.last_modified = datetime.now().isoformat()
            self.services[config.id] = config
            self.save_services()
            return True
        except Exception as e:
            print(f"Error adding service: {e}")
            return False
    
    def remove_service(self, service_id: str) -> bool:
        """
        Remove a service
        
        Args:
            service_id: Service ID to remove
            
        Returns:
            True if successful
        """
        try:
            if service_id in self.services:
                # Don't allow removing predefined services
                if not self.services[service_id].is_custom:
                    print(f"Cannot remove predefined service: {service_id}")
                    return False
                
                del self.services[service_id]
                
                # Also remove API key
                if service_id in self.api_keys:
                    del self.api_keys[service_id]
                    self.save_api_keys()
                
                self.save_services()
                return True
            return False
        except Exception as e:
            print(f"Error removing service: {e}")
            return False
    
    def get_service(self, service_id: str) -> Optional[APIServiceConfig]:
        """Get service configuration"""
        return self.services.get(service_id)
    
    def get_all_services(self) -> List[APIServiceConfig]:
        """Get all service configurations"""
        return list(self.services.values())
    
    def get_active_services(self) -> List[APIServiceConfig]:
        """Get only active services"""
        return [s for s in self.services.values() if s.is_active]
    
    def set_api_key(self, service_id: str, api_key: str) -> bool:
        """
        Set API key for a service
        
        Args:
            service_id: Service ID
            api_key: Plain text API key
            
        Returns:
            True if successful
        """
        try:
            encrypted_key = self.encryption_manager.encrypt(api_key)
            self.api_keys[service_id] = encrypted_key
            self.save_api_keys()
            return True
        except Exception as e:
            print(f"Error setting API key: {e}")
            return False
    
    def get_api_key(self, service_id: str) -> Optional[str]:
        """
        Get decrypted API key for a service
        
        Args:
            service_id: Service ID
            
        Returns:
            Decrypted API key or None
        """
        encrypted_key = self.api_keys.get(service_id)
        if encrypted_key:
            return self.encryption_manager.decrypt(encrypted_key)
        return None
    
    def has_api_key(self, service_id: str) -> bool:
        """Check if service has API key configured"""
        return service_id in self.api_keys and bool(self.api_keys[service_id])
    
    def test_service(
        self, 
        service_id: str, 
        test_prompt: str = "Hello, this is a test message.",
        timeout: int = 10
    ) -> Tuple[bool, str]:
        """
        Test API service connection
        
        Args:
            service_id: Service ID to test
            test_prompt: Test prompt to send
            timeout: Request timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            service = self.get_service(service_id)
            if not service:
                return False, "Service not found"
            
            api_key = self.get_api_key(service_id)
            if not api_key:
                return False, "API key not configured"
            
            # Build request
            headers = dict(service.endpoint.headers)
            
            # Add authentication
            if service.auth_type == AuthType.BEARER_TOKEN:
                headers[service.api_key_header_name] = f"{service.api_key_prefix} {api_key}".strip()
            elif service.auth_type == AuthType.API_KEY_HEADER:
                headers[service.api_key_header_name] = api_key
            
            # Build request body
            body = self._build_request_body(service, test_prompt, is_test=True)
            
            # Send request
            response = requests.request(
                method=service.endpoint.method,
                url=service.endpoint.url.format(model=service.model_name),
                headers=headers,
                json=body,
                params=service.endpoint.query_params,
                timeout=timeout
            )
            
            if response.status_code == 200:
                # Try to parse response
                try:
                    result = self._parse_response(service, response.json())
                    service.update_test_status(True, "Connection successful")
                    self.save_services()
                    return True, f"Success! Response: {result[:100]}..."
                except Exception as e:
                    return False, f"Response parsing error: {str(e)}"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                service.update_test_status(False, error_msg)
                self.save_services()
                return False, error_msg
                
        except requests.exceptions.Timeout:
            return False, "Request timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def _build_request_body(
        self, 
        service: APIServiceConfig, 
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
        is_test: bool = False
    ) -> Dict[str, Any]:
        """Build request body from template"""
        body = dict(service.request_format.body_template)
        
        # Replace placeholders
        body_str = json.dumps(body)
        body_str = body_str.replace("{model}", service.model_name)
        body_str = body_str.replace("{temperature}", str(service.temperature))
        body_str = body_str.replace("{max_tokens}", str(service.max_tokens))
        body_str = body_str.replace("{top_p}", str(service.top_p))
        body_str = body_str.replace("{text}", prompt)
        
        body = json.loads(body_str)
        
        # Build messages for chat-based APIs
        if "messages" in body and isinstance(body["messages"], list):
            messages = []
            
            # Add system instruction
            if system_instruction:
                if service.provider_type == APIProviderType.GOOGLE:
                    # Google Gemini uses system_instruction field
                    body["system_instruction"] = {
                        "parts": [{"text": system_instruction}]
                    }
                else:
                    messages.append({
                        "role": "system",
                        "content": system_instruction
                    })
            
            # Add context (previous conversations)
            if context and not is_test:
                for ctx in context:
                    messages.append({
                        "role": "user",
                        "content": ctx.get("user", "")
                    })
                    if "assistant" in ctx:
                        messages.append({
                            "role": "assistant",
                            "content": ctx["assistant"]
                        })
            
            # Add current prompt
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            body["messages"] = messages
        
        # For Google Gemini format
        if "contents" in body:
            contents = []
            if context and not is_test:
                for ctx in context:
                    contents.append({
                        "role": "user",
                        "parts": [{"text": ctx.get("user", "")}]
                    })
                    if "assistant" in ctx:
                        contents.append({
                            "role": "model",
                            "parts": [{"text": ctx["assistant"]}]
                        })
            
            contents.append({
                "role": "user",
                "parts": [{"text": prompt}]
            })
            body["contents"] = contents
        
        return body
    
    def _parse_response(self, service: APIServiceConfig, response_data: Dict[str, Any]) -> str:
        """Parse API response to extract text"""
        # Navigate through the path
        path_parts = service.response_format.text_path.split(".")
        current = response_data
        
        for part in path_parts:
            if part.isdigit():
                # Array index
                current = current[int(part)]
            else:
                # Object key
                current = current.get(part)
                if current is None:
                    raise ValueError(f"Path not found: {part}")
        
        return str(current)
    
    def call_api(
        self,
        service_id: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Call API service
        
        Args:
            service_id: Service ID
            prompt: User prompt
            system_instruction: System instruction
            context: Conversation context
            on_progress: Progress callback
            
        Returns:
            (success, result_text, metadata) tuple
        """
        try:
            service = self.get_service(service_id)
            if not service:
                return False, "Service not found", None
            
            api_key = self.get_api_key(service_id)
            if not api_key:
                return False, "API key not configured", None
            
            if on_progress:
                on_progress(f"Calling {service.name}...")
            
            # Build request
            headers = dict(service.endpoint.headers)
            headers["Content-Type"] = "application/json"
            
            # Add authentication
            if service.auth_type == AuthType.BEARER_TOKEN:
                headers[service.api_key_header_name] = f"{service.api_key_prefix} {api_key}".strip()
            elif service.auth_type == AuthType.API_KEY_HEADER:
                headers[service.api_key_header_name] = api_key
            
            # Build request body
            body = self._build_request_body(
                service, 
                prompt, 
                system_instruction, 
                context
            )
            
            # Send request with retry logic
            max_retries = service.endpoint.retry_count
            retry_delay = service.endpoint.retry_delay
            
            for attempt in range(max_retries):
                try:
                    if on_progress and attempt > 0:
                        on_progress(f"Retry {attempt}/{max_retries}...")
                    
                    response = requests.request(
                        method=service.endpoint.method,
                        url=service.endpoint.url.format(model=service.model_name),
                        headers=headers,
                        json=body,
                        params=service.endpoint.query_params,
                        timeout=service.endpoint.timeout
                    )
                    
                    if response.status_code == 200:
                        result_text = self._parse_response(service, response.json())
                        
                        # Extract metadata if available
                        metadata = {}
                        if service.response_format.usage_path:
                            try:
                                usage_parts = service.response_format.usage_path.split(".")
                                usage = response.json()
                                for part in usage_parts:
                                    usage = usage.get(part) if isinstance(usage, dict) else None
                                metadata["usage"] = usage
                            except:
                                pass
                        
                        return True, result_text, metadata
                    
                    elif attempt < max_retries - 1:
                        # Wait before retry
                        import time
                        time.sleep(retry_delay)
                    else:
                        return False, f"HTTP {response.status_code}: {response.text[:200]}", None
                        
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay)
                    else:
                        return False, "Request timeout after retries", None
                        
            return False, "Max retries exceeded", None
            
        except Exception as e:
            return False, f"Error: {str(e)}", None
    
    def save_services(self) -> bool:
        """Save service configurations to file"""
        try:
            data = {
                "version": "2.0",
                "services": [service.to_dict() for service in self.services.values()]
            }
            
            with open(self.services_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving services: {e}")
            return False
    
    def load_services(self) -> bool:
        """Load service configurations from file"""
        try:
            if not self.services_file.exists():
                return False
            
            with open(self.services_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.services = {}
            for service_data in data.get("services", []):
                try:
                    service = APIServiceConfig.from_dict(service_data)
                    self.services[service.id] = service
                except Exception as e:
                    print(f"Error loading service: {e}")
            
            return True
        except Exception as e:
            print(f"Error loading services: {e}")
            return False
    
    def save_api_keys(self) -> bool:
        """Save encrypted API keys to file"""
        try:
            data = {
                "version": "2.0",
                "keys": self.api_keys
            }
            
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving API keys: {e}")
            return False
    
    def load_api_keys(self) -> bool:
        """Load encrypted API keys from file"""
        try:
            if not self.keys_file.exists():
                return False
            
            with open(self.keys_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.api_keys = data.get("keys", {})
            return True
        except Exception as e:
            print(f"Error loading API keys: {e}")
            return False
