"""
API Tools for LangChain Agent
Implements external API integration with proper error handling and authentication
"""

import json
import requests
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from urllib.parse import urljoin, urlparse
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from logger import get_logger

logger = get_logger(__name__)

class APICallInput(BaseModel):
    """Input schema for API call tool"""
    url: str = Field(description="Full URL for the API endpoint")
    method: str = Field(default="GET", description="HTTP method (GET, POST, PUT, DELETE)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Request body data")
    params: Optional[Dict[str, str]] = Field(default=None, description="URL parameters")
    timeout: Optional[int] = Field(default=30, description="Request timeout in seconds")

class HTTPRequestInput(BaseModel):
    """Input schema for HTTP request tool"""
    url: str = Field(description="URL to make the request to")
    method: str = Field(default="GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Request headers")
    json_data: Optional[Dict[str, Any]] = Field(default=None, description="JSON data for POST/PUT requests")
    form_data: Optional[Dict[str, str]] = Field(default=None, description="Form data for POST requests")
    auth: Optional[Dict[str, str]] = Field(default=None, description="Authentication details")

class APICallTool(BaseTool):
    """
    General purpose API calling tool with authentication support
    Handles REST API calls with proper error handling and response formatting
    """
    
    name = "api_caller"
    description = """
    Make HTTP API calls to external services with full REST support.
    Supports GET, POST, PUT, DELETE methods with authentication.
    Handles JSON and form data, custom headers, and URL parameters.
    Returns structured response with status, headers, and data.
    """
    args_schema = APICallInput
    
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'LangChain-MCP-Agent/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _run(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
             data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, str]] = None,
             timeout: int = 30) -> str:
        """Execute HTTP API call"""
        try:
            logger.info(f"Making API call: {method} {url}")
            
            # Validate URL
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL format: {url}")
            
            # Prepare request
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'timeout': timeout
            }
            
            # Add headers
            if headers:
                request_kwargs['headers'] = headers
            
            # Add parameters
            if params:
                request_kwargs['params'] = params
            
            # Add data based on method
            if data and method.upper() in ['POST', 'PUT', 'PATCH']:
                if isinstance(data, dict):
                    request_kwargs['json'] = data
                else:
                    request_kwargs['data'] = data
            
            # Execute request
            response = self.session.request(**request_kwargs)
            
            # Process response
            result = self._process_api_response(response, url, method)
            
            logger.info(f"API call completed: {response.status_code}")
            return json.dumps(result, indent=2)
            
        except requests.exceptions.Timeout:
            error_result = self._create_error_response(
                "timeout", f"Request timeout after {timeout} seconds", url, method
            )
            return json.dumps(error_result, indent=2)
            
        except requests.exceptions.ConnectionError:
            error_result = self._create_error_response(
                "connection_error", "Failed to connect to the API endpoint", url, method
            )
            return json.dumps(error_result, indent=2)
            
        except Exception as e:
            error_result = self._create_error_response(
                "general_error", str(e), url, method
            )
            logger.error(f"API call failed: {e}")
            return json.dumps(error_result, indent=2)
    
    async def _arun(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
                    data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, str]] = None,
                    timeout: int = 30) -> str:
        """Async version of API call"""
        try:
            async with aiohttp.ClientSession() as session:
                request_kwargs = {
                    'method': method.upper(),
                    'url': url,
                    'timeout': aiohttp.ClientTimeout(total=timeout)
                }
                
                if headers:
                    request_kwargs['headers'] = headers
                
                if params:
                    request_kwargs['params'] = params
                
                if data and method.upper() in ['POST', 'PUT', 'PATCH']:
                    if isinstance(data, dict):
                        request_kwargs['json'] = data
                    else:
                        request_kwargs['data'] = data
                
                async with session.request(**request_kwargs) as response:
                    result = await self._process_async_response(response, url, method)
                    return json.dumps(result, indent=2)
                    
        except Exception as e:
            error_result = self._create_error_response(
                "async_error", str(e), url, method
            )
            return json.dumps(error_result, indent=2)
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format and security"""
        try:
            parsed = urlparse(url)
            
            # Check for valid scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check for valid domain
            if not parsed.netloc:
                return False
            
            # Security check - avoid localhost/internal networks
            blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if any(host in parsed.netloc.lower() for host in blocked_hosts):
                logger.warning(f"Blocked request to internal host: {parsed.netloc}")
                return False
            
            return True
            
        except Exception:
            return False
    
    def _process_api_response(self, response: requests.Response, url: str, method: str) -> Dict[str, Any]:
        """Process and format API response"""
        try:
            # Try to parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text
            
            result = {
                "status": "success" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response_data,
                "url": url,
                "method": method,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add error details for non-success responses
            if response.status_code >= 400:
                result["error_type"] = "http_error"
                result["error_message"] = f"HTTP {response.status_code}: {response.reason}"
            
            return result
            
        except Exception as e:
            return self._create_error_response(
                "response_processing_error", str(e), url, method
            )
    
    async def _process_async_response(self, response: aiohttp.ClientResponse, url: str, method: str) -> Dict[str, Any]:
        """Process async API response"""
        try:
            # Try to parse JSON response
            try:
                response_data = await response.json()
            except:
                response_data = await response.text()
            
            result = {
                "status": "success" if response.status < 400 else "error",
                "status_code": response.status,
                "headers": dict(response.headers),
                "data": response_data,
                "url": url,
                "method": method,
                "timestamp": datetime.now().isoformat()
            }
            
            if response.status >= 400:
                result["error_type"] = "http_error"
                result["error_message"] = f"HTTP {response.status}: {response.reason}"
            
            return result
            
        except Exception as e:
            return self._create_error_response(
                "async_response_error", str(e), url, method
            )
    
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
    Advanced HTTP request tool with authentication and advanced features
    """
    
    name = "http_request_tool"
    description = """
    Advanced HTTP request tool with authentication support.
    Supports various authentication methods (API key, Bearer token, Basic auth).
    Handles complex request scenarios including file uploads and custom content types.
    Provides detailed response analysis and debugging information.
    """
    args_schema = HTTPRequestInput
    
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
    
    def _run(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
             json_data: Optional[Dict[str, Any]] = None, form_data: Optional[Dict[str, str]] = None,
             auth: Optional[Dict[str, str]] = None) -> str:
        """Execute advanced HTTP request"""
        try:
            logger.info(f"HTTP request: {method} {url}")
            
            # Prepare request
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'timeout': 30
            }
            
            # Handle authentication
            if auth:
                request_kwargs.update(self._handle_authentication(auth))
            
            # Handle headers
            if headers:
                if 'headers' not in request_kwargs:
                    request_kwargs['headers'] = {}
                request_kwargs['headers'].update(headers)
            
            # Handle data
            if json_data:
                request_kwargs['json'] = json_data
                if 'headers' not in request_kwargs:
                    request_kwargs['headers'] = {}
                request_kwargs['headers']['Content-Type'] = 'application/json'
            elif form_data:
                request_kwargs['data'] = form_data
                if 'headers' not in request_kwargs:
                    request_kwargs['headers'] = {}
                request_kwargs['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
            
            # Execute request
            response = self.session.request(**request_kwargs)
            
            # Process and analyze response
            result = self._analyze_response(response, url, method)
            
            logger.info(f"HTTP request completed: {response.status_code}")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error_type": "request_failed",
                "error_message": str(e),
                "url": url,
                "method": method,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"HTTP request failed: {e}")
            return json.dumps(error_result, indent=2)
    
    async def _arun(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
                    json_data: Optional[Dict[str, Any]] = None, form_data: Optional[Dict[str, str]] = None,
                    auth: Optional[Dict[str, str]] = None) -> str:
        """Async version of HTTP request"""
        return self._run(url, method, headers, json_data, form_data, auth)
    
    def _handle_authentication(self, auth: Dict[str, str]) -> Dict[str, Any]:
        """Handle different authentication methods"""
        auth_type = auth.get("type", "").lower()
        
        if auth_type == "bearer":
            return {
                "headers": {
                    "Authorization": f"Bearer {auth.get('token')}"
                }
            }
        elif auth_type == "api_key":
            key_location = auth.get("location", "header").lower()
            key_name = auth.get("key_name", "X-API-Key")
            key_value = auth.get("key_value")
            
            if key_location == "header":
                return {
                    "headers": {
                        key_name: key_value
                    }
                }
            elif key_location == "query":
                return {
                    "params": {
                        key_name: key_value
                    }
                }
        elif auth_type == "basic":
            username = auth.get("username")
            password = auth.get("password")
            return {
                "auth": (username, password)
            }
        
        return {}
    
    def _analyze_response(self, response: requests.Response, url: str, method: str) -> Dict[str, Any]:
        """Analyze and format HTTP response with detailed information"""
        try:
            # Parse response content
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                try:
                    parsed_data = response.json()
                except json.JSONDecodeError:
                    parsed_data = response.text
            else:
                parsed_data = response.text
            
            # Create detailed analysis
            analysis = {
                "status": "success" if response.status_code < 400 else "error",
                "request": {
                    "url": url,
                    "method": method,
                    "timestamp": datetime.now().isoformat()
                },
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
            
            # Add error details for failed requests
            if response.status_code >= 400:
                analysis["error"] = {
                    "type": "http_error",
                    "code": response.status_code,
                    "message": response.reason,
                    "details": parsed_data if isinstance(parsed_data, str) else str(parsed_data)
                }
            
            return analysis
            
        except Exception as e:
            return {
                "status": "error",
                "error_type": "analysis_failed",
                "error_message": str(e),
                "url": url,
                "method": method,
                "timestamp": datetime.now().isoformat()
            }
