"""
API Tools for MCP Integration
Final fixed implementation with proper Pydantic model handling
"""

import json
import requests
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from urllib.parse import urljoin, urlparse
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr

from logger import get_logger

logger = get_logger(__name__)

class APICallInput(BaseModel):
    """Input schema for API call tool"""
    url: str = Field(..., description="Full URL for the API endpoint")
    method: str = Field("GET", description="HTTP method (GET, POST, PUT, DELETE)")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")
    data: Optional[Dict[str, Any]] = Field(None, description="Request body data")
    params: Optional[Dict[str, str]] = Field(None, description="URL parameters")
    timeout: Optional[int] = Field(30, description="Request timeout in seconds")

    model_config = ConfigDict(arbitrary_types_allowed=True)

class HTTPRequestInput(BaseModel):
    """Input schema for HTTP request tool"""
    url: str = Field(..., description="URL to make the request to")
    method: str = Field("GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(None, description="Request headers")
    json_data: Optional[Dict[str, Any]] = Field(None, description="JSON data for POST/PUT requests")
    form_data: Optional[Dict[str, str]] = Field(None, description="Form data for POST requests")
    auth: Optional[Dict[str, str]] = Field(None, description="Authentication details")

    model_config = ConfigDict(arbitrary_types_allowed=True)

class APICallTool(BaseTool):
    """
    General purpose API calling tool with authentication support
    """
    
    name: str = "api_caller"
    description: str = """
    Make HTTP API calls to external services with full REST support.
    Supports GET, POST, PUT, DELETE methods with authentication.
    Handles JSON and form data, custom headers, and URL parameters.
    Returns structured response with status, headers, and data.
    """
    args_schema: type[BaseModel] = APICallInput
    
    _session: requests.Session = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = requests.Session()
        # Set default headers
        self._session.headers.update({
            'User-Agent': 'MCP-Agent/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _run(self, **kwargs) -> str:
        """Execute HTTP API call with proper kwargs handling"""
        try:
            # Convert input to dict if it's a Pydantic model
            if hasattr(kwargs.get('input'), 'model_dump'):
                kwargs = kwargs['input'].model_dump()
            elif hasattr(kwargs.get('input'), 'dict'):
                kwargs = kwargs['input'].dict()
            
            # Validate required parameters
            if 'url' not in kwargs:
                raise ValueError("URL is required for API calls")
            
            url = kwargs['url']
            method = kwargs.get('method', 'GET')
            
            logger.info(f"Making API call: {method} {url}")
            
            # Validate URL
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL format: {url}")
            
            # Prepare request
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'timeout': kwargs.get('timeout', 30)
            }
            
            # Add optional parameters
            if 'headers' in kwargs and kwargs['headers']:
                request_kwargs['headers'] = kwargs['headers']
            
            if 'params' in kwargs and kwargs['params']:
                request_kwargs['params'] = kwargs['params']
            
            # Add data based on method
            if 'data' in kwargs and kwargs['data'] and method.upper() in ['POST', 'PUT', 'PATCH']:
                if isinstance(kwargs['data'], dict):
                    request_kwargs['json'] = kwargs['data']
                else:
                    request_kwargs['data'] = kwargs['data']
            
            # Execute request
            response = self._session.request(**request_kwargs)
            
            # Process response
            result = self._process_api_response(response, url, method)
            
            logger.info(f"API call completed: {response.status_code}")
            return json.dumps(result, indent=2)
            
        except requests.exceptions.Timeout as e:
            error_result = self._create_error_response(
                "timeout", f"Request timeout after {kwargs.get('timeout', 30)} seconds", url, method
            )
            return json.dumps(error_result, indent=2)
            
        except Exception as e:
            error_result = self._create_error_response(
                "general_error", str(e), url or 'unknown', method or 'GET'
            )
            logger.error(f"API call failed: {e}")
            return json.dumps(error_result, indent=2)
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format and security"""
        try:
            parsed = urlparse(url)
            return all([
                parsed.scheme in ['http', 'https'],
                parsed.netloc,
                not any(host in parsed.netloc.lower() 
                       for host in ['localhost', '127.0.0.1', '0.0.0.0', '::1'])
            ])
        except Exception:
            return False
    
    def _process_api_response(self, response: requests.Response, url: str, method: str) -> Dict[str, Any]:
        """Process and format API response"""
        try:
            response_data = response.json() if 'application/json' in response.headers.get('content-type', '').lower() else response.text
            
            return {
                "status": "success" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response_data,
                "url": url,
                "method": method,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return self._create_error_response("response_processing_error", str(e), url, method)
    
    def _create_error_response(self, error_type: str, error_message: str, url: str, method: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "status": "error",
            "error_type": error_type,
            "error_message": error_message,
            "url": url,
            "method": method,
            "timestamp": datetime.now().isoformat()
        }

class HTTPRequestTool(BaseTool):
    """
    Advanced HTTP request tool with authentication support
    """
    
    name: str = "http_request_tool"
    description: str = """
    Advanced HTTP request tool with authentication support.
    Supports various authentication methods (API key, Bearer token, Basic auth).
    Handles complex request scenarios including file uploads and custom content types.
    Provides detailed response analysis and debugging information.
    """
    args_schema: type[BaseModel] = HTTPRequestInput
    
    _session: requests.Session = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = requests.Session()
    
    def _run(self, **kwargs) -> str:
        """Execute advanced HTTP request with proper kwargs handling"""
        try:
            # Convert input to dict if it's a Pydantic model
            if hasattr(kwargs.get('input'), 'model_dump'):
                kwargs = kwargs['input'].model_dump()
            elif hasattr(kwargs.get('input'), 'dict'):
                kwargs = kwargs['input'].dict()
            
            # Validate required parameters
            if 'url' not in kwargs:
                raise ValueError("URL is required for HTTP requests")
            
            url = kwargs['url']
            method = kwargs.get('method', 'GET')
            
            logger.info(f"HTTP request: {method} {url}")
            
            # Prepare request
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'timeout': 30
            }
            
            # Handle authentication
            if 'auth' in kwargs and kwargs['auth']:
                request_kwargs.update(self._handle_authentication(kwargs['auth']))
            
            # Handle headers
            if 'headers' in kwargs and kwargs['headers']:
                request_kwargs.setdefault('headers', {}).update(kwargs['headers'])
            
            # Handle data
            if 'json_data' in kwargs and kwargs['json_data']:
                request_kwargs['json'] = kwargs['json_data']
                request_kwargs.setdefault('headers', {})['Content-Type'] = 'application/json'
            elif 'form_data' in kwargs and kwargs['form_data']:
                request_kwargs['data'] = kwargs['form_data']
                request_kwargs.setdefault('headers', {})['Content-Type'] = 'application/x-www-form-urlencoded'
            
            # Execute request
            response = self._session.request(**request_kwargs)
            
            # Process and analyze response
            result = self._analyze_response(response, url, method)
            
            logger.info(f"HTTP request completed: {response.status_code}")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error_type": "request_failed",
                "error_message": str(e),
                "url": url or 'unknown',
                "method": method or 'GET',
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"HTTP request failed: {e}")
            return json.dumps(error_result, indent=2)
    
    def _handle_authentication(self, auth: Dict[str, str]) -> Dict[str, Any]:
        """Handle different authentication methods"""
        auth_type = auth.get("type", "").lower()
        
        if auth_type == "bearer":
            return {"headers": {"Authorization": f"Bearer {auth.get('token')}"}}
        elif auth_type == "api_key":
            key_location = auth.get("location", "header").lower()
            key_name = auth.get("key_name", "X-API-Key")
            key_value = auth.get("key_value")
            
            if key_location == "header":
                return {"headers": {key_name: key_value}}
            elif key_location == "query":
                return {"params": {key_name: key_value}}
        elif auth_type == "basic":
            return {"auth": (auth.get("username"), auth.get("password"))}
        
        return {}
    
    def _analyze_response(self, response: requests.Response, url: str, method: str) -> Dict[str, Any]:
        """Analyze and format HTTP response with detailed information"""
        try:
            content_type = response.headers.get('content-type', '').lower()
            
            try:
                parsed_data = response.json() if 'application/json' in content_type else response.text
            except ValueError:
                parsed_data = response.text
            
            return {
                "status": "success" if response.status_code < 400 else "error",
                "request": {"url": url, "method": method, "timestamp": datetime.now().isoformat()},
                "response": {
                    "status_code": response.status_code,
                    "status_text": response.reason,
                    "headers": dict(response.headers),
                    "content_type": content_type,
                    "content_length": len(response.content),
                    "data": parsed_data,
                    "encoding": response.encoding
                },
                "performance": {
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "size_bytes": len(response.content)
                },
                "analysis": {
                    "is_json": 'application/json' in content_type,
                    "is_success": 200 <= response.status_code < 300,
                    "is_redirect": 300 <= response.status_code < 400,
                    "is_client_error": 400 <= response.status_code < 500,
                    "is_server_error": response.status_code >= 500
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "analysis_failed",
                "error_message": str(e),
                "url": url,
                "method": method,
                "timestamp": datetime.now().isoformat()
            }