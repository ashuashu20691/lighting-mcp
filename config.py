"""
Configuration Management for MCP Server
Handles environment variables, API keys, and application settings
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

class Config:
    """
    Configuration class for MCP Server
    Manages environment variables and application settings
    """
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables"""
        
        # OpenAI Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Database Configuration (Oracle ADB simulation)
        self.database_url = os.getenv("DATABASE_URL", "")
        self.database_path = os.getenv("DB_PATH", "./data/enterprise_db.sqlite")
        
        # Oracle ADB Mock Configuration
        self.oracle_config = {
            "host": os.getenv("ORACLE_HOST", "autonomous-db.oracle.com"),
            "port": int(os.getenv("ORACLE_PORT", "1522")),
            "service_name": os.getenv("ORACLE_SERVICE", "autonomous_db_high"),
            "username": os.getenv("ORACLE_USER", "ADMIN"),
            "password": os.getenv("ORACLE_PASSWORD", "mock_password"),
            "wallet_path": os.getenv("ORACLE_WALLET", "/opt/oracle/wallet"),
            "connection_pool_size": int(os.getenv("ORACLE_POOL_SIZE", "10")),
            "connection_timeout": int(os.getenv("ORACLE_TIMEOUT", "30"))
        }
        
        # PostgreSQL Configuration (from secrets)
        self.postgres_config = {
            "host": os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("PGPORT", "5432")),
            "database": os.getenv("PGDATABASE", "postgres"),
            "username": os.getenv("PGUSER", "postgres"),
            "password": os.getenv("PGPASSWORD", ""),
            "url": os.getenv("DATABASE_URL", "")
        }
        
        # API Configuration
        self.api_config = {
            "max_retries": int(os.getenv("API_MAX_RETRIES", "3")),
            "timeout": int(os.getenv("API_TIMEOUT", "30")),
            "rate_limit": int(os.getenv("API_RATE_LIMIT", "100")),
            "user_agent": os.getenv("API_USER_AGENT", "MCP-LangChain-Agent/1.0")
        }
        
        # LangChain Configuration
        self.langchain_config = {
            "model_name": os.getenv("LANGCHAIN_MODEL", "gpt-4o"),
            "temperature": float(os.getenv("LANGCHAIN_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("LANGCHAIN_MAX_TOKENS", "2000")),
            "memory_window": int(os.getenv("LANGCHAIN_MEMORY_WINDOW", "10")),
            "max_iterations": int(os.getenv("LANGCHAIN_MAX_ITERATIONS", "5")),
            "verbose": os.getenv("LANGCHAIN_VERBOSE", "true").lower() == "true"
        }
        
        # Security Configuration
        self.security_config = {
            "api_key_header": os.getenv("API_KEY_HEADER", "X-API-Key"),
            "allowed_origins": os.getenv("ALLOWED_ORIGINS", "*").split(","),
            "rate_limit_enabled": os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
            "max_query_length": int(os.getenv("MAX_QUERY_LENGTH", "10000")),
            "blocked_keywords": os.getenv("BLOCKED_KEYWORDS", "DROP,DELETE,TRUNCATE,ALTER").split(",")
        }
        
        # Logging Configuration
        self.logging_config = {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            "file_path": os.getenv("LOG_FILE", "./logs/mcp_server.log"),
            "max_size_mb": int(os.getenv("LOG_MAX_SIZE_MB", "10")),
            "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
            "enable_console": os.getenv("LOG_CONSOLE", "true").lower() == "true"
        }
        
        # Application Configuration
        self.app_config = {
            "name": "MCP LangChain Server",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", "8000")),
            "workers": int(os.getenv("WORKERS", "1"))
        }
        
        # Tool Configuration
        self.tool_config = {
            "enable_oracle_tools": os.getenv("ENABLE_ORACLE_TOOLS", "true").lower() == "true",
            "enable_api_tools": os.getenv("ENABLE_API_TOOLS", "true").lower() == "true",
            "max_concurrent_tools": int(os.getenv("MAX_CONCURRENT_TOOLS", "5")),
            "tool_timeout": int(os.getenv("TOOL_TIMEOUT", "60")),
            "cache_tool_results": os.getenv("CACHE_TOOL_RESULTS", "true").lower() == "true"
        }
        
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories for the application"""
        directories = [
            os.path.dirname(self.database_path),
            os.path.dirname(self.logging_config["file_path"]),
            "./cache",
            "./temp"
        ]
        
        for directory in directories:
            if directory:  # Skip empty directory names
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_oracle_connection_string(self) -> str:
        """Generate Oracle connection string for demonstration"""
        return (
            f"oracle+cx_oracle://{self.oracle_config['username']}:"
            f"{self.oracle_config['password']}@"
            f"{self.oracle_config['host']}:{self.oracle_config['port']}/"
            f"{self.oracle_config['service_name']}"
        )
    
    def get_postgres_connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        if self.postgres_config["url"]:
            return self.postgres_config["url"]
        
        return (
            f"postgresql://{self.postgres_config['username']}:"
            f"{self.postgres_config['password']}@"
            f"{self.postgres_config['host']}:{self.postgres_config['port']}/"
            f"{self.postgres_config['database']}"
        )
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required configurations
        if not self.openai_api_key:
            validation_results["errors"].append("OpenAI API key is missing")
            validation_results["valid"] = False
        
        # Check Oracle configuration
        required_oracle_fields = ["host", "port", "service_name", "username"]
        for field in required_oracle_fields:
            if not self.oracle_config.get(field):
                validation_results["warnings"].append(f"Oracle {field} is not configured")
        
        # Check file paths
        try:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            validation_results["errors"].append(f"Cannot create database directory: {e}")
            validation_results["valid"] = False
        
        try:
            Path(self.logging_config["file_path"]).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            validation_results["warnings"].append(f"Cannot create log directory: {e}")
        
        # Validate numeric configurations
        if self.langchain_config["temperature"] < 0 or self.langchain_config["temperature"] > 2:
            validation_results["warnings"].append("LangChain temperature should be between 0 and 2")
        
        if self.langchain_config["max_tokens"] < 1:
            validation_results["errors"].append("LangChain max_tokens must be positive")
            validation_results["valid"] = False
        
        return validation_results
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging/debugging"""
        return {
            "app": {
                "name": self.app_config["name"],
                "version": self.app_config["version"],
                "environment": self.app_config["environment"],
                "debug": self.app_config["debug"]
            },
            "database": {
                "path": self.database_path,
                "oracle_host": self.oracle_config["host"],
                "oracle_service": self.oracle_config["service_name"]
            },
            "langchain": {
                "model": self.langchain_config["model_name"],
                "temperature": self.langchain_config["temperature"],
                "max_tokens": self.langchain_config["max_tokens"]
            },
            "tools": {
                "oracle_enabled": self.tool_config["enable_oracle_tools"],
                "api_enabled": self.tool_config["enable_api_tools"]
            },
            "security": {
                "rate_limit_enabled": self.security_config["rate_limit_enabled"],
                "max_query_length": self.security_config["max_query_length"]
            }
        }
    
    def __str__(self) -> str:
        """String representation of configuration"""
        summary = self.get_config_summary()
        return f"MCPConfig({summary})"
    
    def __repr__(self) -> str:
        """Detailed representation of configuration"""
        return self.__str__()
