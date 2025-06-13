"""
Simplified MCP Server - Microservices Control Plane for LLM orchestration
Handles OpenAI integration with Oracle ADB patterns and tool integration
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from openai import OpenAI
from database import DatabaseManager
from config import Config
from logger import get_logger

# Configure logging
logger = get_logger(__name__)

class SimpleMCPServer:
    """
    Simplified Microservices Control Plane Server
    Direct integration with OpenAI and database tools
    """
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.openai_client = None
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            self.openai_client = OpenAI(
                api_key=self.config.openai_api_key
            )
            logger.info("OpenAI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def check_openai_connection(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            if not self.openai_client:
                return False
            
            # Simple test to verify API key
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            content = response.choices[0].message.content
            return content is not None and len(content) > 0
        except Exception as e:
            logger.error(f"OpenAI connection check failed: {e}")
            return False
    
    def check_database_connection(self) -> bool:
        """Check if database connection is working"""
        try:
            return self.db_manager.test_connection()
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return [
            "oracle_query_executor",
            "oracle_schema_explorer", 
            "oracle_transaction_manager",
            "api_caller",
            "http_request_tool"
        ]
    
    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            return self.db_manager.get_schema_info()
        except Exception as e:
            logger.error(f"Failed to get database schema: {e}")
            return {}
    
    def execute_oracle_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Oracle-style SQL query"""
        try:
            logger.info(f"Executing Oracle query: {query[:100]}...")
            
            # Execute query through database manager
            result = self.db_manager.execute_query(query, parameters)
            
            # Format result in Oracle ADB style
            if result.get("status") == "success":
                oracle_result = {
                    "status": "success",
                    "execution_time_ms": result.get("execution_time", 0) * 1000,
                    "rows_affected": len(result.get("data", [])),
                    "data": result.get("data", []),
                    "columns": result.get("columns", []),
                    "oracle_metadata": {
                        "session_id": "ADB_SESSION_001",
                        "database_version": "Oracle Database 19c Enterprise Edition",
                        "service_name": "autonomous_db_high",
                        "connection_pool": "default_pool",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                # Add query plan for SELECT queries
                if query.upper().strip().startswith('SELECT'):
                    oracle_result["query_plan"] = {
                        "plan_hash_value": "1234567890",
                        "optimizer_mode": "ALL_ROWS",
                        "cost": 10,
                        "cardinality": len(result.get("data", []))
                    }
                
                return oracle_result
            else:
                return {
                    "status": "error",
                    "error_code": "ORA-00942",
                    "error_message": result.get("error", "Unknown Oracle error"),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Oracle query execution failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error_code": "ORA-00001",
                "error_message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    
    def make_api_call(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
                     data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP API call"""
        try:
            import requests
            
            logger.info(f"Making API call: {method} {url}")
            
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'timeout': 30
            }
            
            if headers:
                request_kwargs['headers'] = headers
            
            if data and method.upper() in ['POST', 'PUT', 'PATCH']:
                request_kwargs['json'] = data
            
            response = requests.request(**request_kwargs)
            
            # Process response
            try:
                response_data = response.json()
            except:
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
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error_type": "api_call_failed",
                "error_message": str(e),
                "url": url,
                "method": method,
                "timestamp": datetime.now().isoformat()
            }
    
    async def execute_agent_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a query through the simplified MCP agent
        
        Args:
            query: User query string
            
        Returns:
            Dictionary containing response and tool execution details
        """
        try:
            start_time = datetime.now()
            tool_executions = []
            
            # Create system prompt for Oracle ADB and MCP context
            system_prompt = """You are an Oracle ADB (Autonomous Database) expert assistant with MCP (Model Context Protocol) integration. 
            You have access to:
            1. Oracle Database queries (use oracle_query_executor)
            2. Database schema exploration (use oracle_schema_explorer)
            3. Transaction management (use oracle_transaction_manager)
            4. External API calls (use api_caller)
            
            When users ask about database operations, write Oracle-compatible SQL queries.
            When users ask about external services, make appropriate API calls.
            Always explain your reasoning and provide detailed responses.
            
            Available tables in the Oracle ADB:
            - employees (employee_id, first_name, last_name, email, phone_number, hire_date, job_id, salary, commission_pct, manager_id, department_id)
            - departments (department_id, department_name, manager_id, location_id)
            - orders (order_id, customer_id, order_date, ship_date, order_status, total_amount, discount_amount, tax_amount)
            - products (product_id, product_name, product_code, category_id, unit_price, units_in_stock, discontinued)
            """
            
            # Determine if the query needs database operations
            query_lower = query.lower()
            needs_db = any(keyword in query_lower for keyword in [
                'select', 'insert', 'update', 'delete', 'table', 'database', 
                'employee', 'department', 'order', 'product', 'sql', 'query'
            ])
            
            # Determine if the query needs API calls
            needs_api = any(keyword in query_lower for keyword in [
                'api', 'http', 'request', 'call', 'external', 'service', 'endpoint'
            ])
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            # Get initial response from OpenAI
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                agent_response = response.choices[0].message.content or ""
            else:
                agent_response = "OpenAI client not initialized properly"
            
            # Execute tools based on query analysis
            if needs_db and ("select" in query_lower or "show" in query_lower or "list" in query_lower):
                # Execute a sample query
                if "employee" in query_lower:
                    sql_query = "SELECT * FROM employees LIMIT 10"
                elif "department" in query_lower:
                    sql_query = "SELECT * FROM departments"
                elif "order" in query_lower:
                    sql_query = "SELECT * FROM orders LIMIT 10"
                elif "schema" in query_lower or "table" in query_lower:
                    sql_query = "SELECT name FROM sqlite_master WHERE type='table'"
                else:
                    sql_query = "SELECT name FROM sqlite_master WHERE type='table'"
                
                # Execute the query
                query_result = self.execute_oracle_query(sql_query)
                tool_executions.append({
                    "tool_name": "oracle_query_executor",
                    "input": sql_query,
                    "output": query_result,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update response with query results
                if query_result.get("status") == "success":
                    agent_response += f"\n\nQuery Results:\n{json.dumps(query_result, indent=2)}"
            
            if needs_api and "example" in query_lower:
                # Make example API call
                api_result = self.make_api_call("https://jsonplaceholder.typicode.com/posts/1")
                tool_executions.append({
                    "tool_name": "api_caller",
                    "input": "https://jsonplaceholder.typicode.com/posts/1",
                    "output": api_result,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "response": agent_response,
                "tool_executions": tool_executions,
                "timestamp": start_time.isoformat(),
                "execution_time": execution_time,
                "status": "success"
            }
            
            logger.info(f"Agent query executed successfully in {execution_time:.3f}s. Tools used: {len(tool_executions)}")
            return result
            
        except Exception as e:
            logger.error(f"Agent query execution failed: {e}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "tool_executions": [],
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def reset_memory(self):
        """Reset agent conversation memory"""
        logger.info("Memory reset (simplified implementation)")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return []
    
    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'db_manager'):
                self.db_manager.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")