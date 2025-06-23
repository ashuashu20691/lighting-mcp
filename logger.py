"""
Logging Configuration for MCP Server
Provides centralized logging with rotation and structured output
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging output
    """
    
    def format(self, record):
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add context information
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        
        return json.dumps(log_entry, ensure_ascii=False)

class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for console output
    """
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to log level
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        
        # Format the message
        formatted = super().format(record)
        
        # Add exception information with proper formatting
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted

class MCPLogger:
    """
    MCP Server Logger with structured logging and rotation
    """
    
    def __init__(self, name: str = "mcp_server"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._configure_handlers()
    
    def _configure_handlers(self):
        """Configure logging handlers based on environment"""
        
        # Get configuration
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_file = os.getenv("LOG_FILE", "./logs/mcp_server.log")
        max_size_mb = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        enable_console = os.getenv("LOG_CONSOLE", "true").lower() == "true"
        structured_logging = os.getenv("STRUCTURED_LOGGING", "false").lower() == "true"
        
        # Create log directory
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Set logger level
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level, logging.INFO))
            
            if structured_logging:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_formatter = ConsoleFormatter(
                    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(console_formatter)
            
            self.logger.addHandler(console_handler)
        
        # File handler with rotation
        if log_file:
            try:
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=max_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.DEBUG)
                
                # Always use structured format for file logging
                file_handler.setFormatter(StructuredFormatter())
                
                self.logger.addHandler(file_handler)
                
            except Exception as e:
                # Fallback to console logging if file logging fails
                self.logger.warning(f"Failed to setup file logging: {e}")
        
        # Error handler - separate file for errors
        error_file = log_file.replace('.log', '_errors.log') if log_file else './logs/mcp_errors.log'
        try:
            error_handler = logging.handlers.RotatingFileHandler(
                error_file,
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StructuredFormatter())
            
            self.logger.addHandler(error_handler)
            
        except Exception as e:
            self.logger.warning(f"Failed to setup error logging: {e}")
    
    def debug(self, message: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, extra_fields, **kwargs)
    
    def info(self, message: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, extra_fields, **kwargs)
    
    def warning(self, message: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, extra_fields, **kwargs)
    
    def error(self, message: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, extra_fields, **kwargs)
    
    def critical(self, message: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, extra_fields, **kwargs)
    
    def exception(self, message: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log exception with traceback"""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, message, extra_fields, **kwargs)
    
    def _log(self, level: int, message: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Internal logging method"""
        
        # Create log record
        extra = kwargs.copy()
        
        if extra_fields:
            extra['extra_fields'] = extra_fields
        
        # Add context information if available
        if 'user_id' in kwargs:
            extra['user_id'] = kwargs['user_id']
        
        if 'session_id' in kwargs:
            extra['session_id'] = kwargs['session_id']
        
        if 'request_id' in kwargs:
            extra['request_id'] = kwargs['request_id']
        
        # Log the message
        self.logger.log(level, message, extra=extra)
    
    def log_query_execution(self, query: str, parameters: Optional[Dict[str, Any]] = None, 
                          execution_time: Optional[float] = None, rows_affected: Optional[int] = None):
        """Log database query execution"""
        extra_fields = {
            "query_type": "database_query",
            "query": query[:200] + "..." if len(query) > 200 else query,
            "has_parameters": parameters is not None,
            "parameter_count": len(parameters) if parameters else 0,
            "execution_time": execution_time,
            "rows_affected": rows_affected
        }
        
        self.info("Database query executed", extra_fields=extra_fields)
    
    def log_api_call(self, url: str, method: str, status_code: Optional[int] = None,
                     response_time: Optional[float] = None, error: Optional[str] = None):
        """Log API call execution"""
        extra_fields = {
            "api_call_type": "external_api",
            "url": url,
            "method": method,
            "status_code": status_code,
            "response_time": response_time,
            "success": status_code and 200 <= status_code < 300,
            "error": error
        }
        
        if error:
            self.error(f"API call failed: {method} {url}", extra_fields=extra_fields)
        else:
            self.info(f"API call completed: {method} {url}", extra_fields=extra_fields)
    
    def log_tool_execution(self, tool_name: str, input_data: Any, output_data: Any = None,
                          execution_time: Optional[float] = None, error: Optional[str] = None):
        """Log tool execution"""
        extra_fields = {
            "tool_execution_type": "langchain_tool",
            "tool_name": tool_name,
            "input_size": len(str(input_data)) if input_data else 0,
            "output_size": len(str(output_data)) if output_data else 0,
            "execution_time": execution_time,
            "success": error is None,
            "error": error
        }
        
        if error:
            self.error(f"Tool execution failed: {tool_name}", extra_fields=extra_fields)
        else:
            self.info(f"Tool executed successfully: {tool_name}", extra_fields=extra_fields)
    
    def log_agent_interaction(self, user_query: str, agent_response: str, 
                            tools_used: List[str], total_time: Optional[float] = None):
        """Log agent interaction"""
        extra_fields = {
            "interaction_type": "agent_conversation",
            "query_length": len(user_query),
            "response_length": len(agent_response),
            "tools_used": tools_used,
            "tool_count": len(tools_used),
            "total_time": total_time
        }
        
        self.info("Agent interaction completed", extra_fields=extra_fields)
    
    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance"""
        return self.logger

# Global logger instance
_logger_instance = None

def get_logger(name: str = "mcp_server") -> MCPLogger:
    """
    Get or create logger instance
    
    Args:
        name: Logger name
        
    Returns:
        MCPLogger instance
    """
    global _logger_instance
    
    if _logger_instance is None or _logger_instance.name != name:
        _logger_instance = MCPLogger(name)
    
    return _logger_instance

def setup_logging():
    """
    Setup logging configuration for the entire application
    """
    # Suppress some noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    
    # Create main logger
    logger = get_logger("mcp_server")
    logger.info("Logging system initialized")
    
    return logger

# Context manager for request logging
class LogContext:
    """
    Context manager for adding request context to logs
    """
    
    def __init__(self, logger: MCPLogger, request_id: str, user_id: Optional[str] = None,
                 session_id: Optional[str] = None):
        self.logger = logger
        self.request_id = request_id
        self.user_id = user_id
        self.session_id = session_id
        self.start_time = datetime.now()
    
    def __enter__(self):
        self.logger.info(
            f"Request started: {self.request_id}",
            extra_fields={
                "request_id": self.request_id,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "start_time": self.start_time.isoformat()
            }
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"Request failed: {self.request_id}",
                extra_fields={
                    "request_id": self.request_id,
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "duration": duration,
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val)
                }
            )
        else:
            self.logger.info(
                f"Request completed: {self.request_id}",
                extra_fields={
                    "request_id": self.request_id,
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "duration": duration
                }
            )
