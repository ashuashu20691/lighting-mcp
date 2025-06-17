"""
Working MCP Server - Simplified Oracle ADB integration
Direct OpenAI integration with database operations and API calls
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from database import DatabaseManager
from config import Config

class WorkingMCPServer:
    """
    Working Microservices Control Plane Server
    Simplified implementation for Oracle ADB patterns
    """


    logger = logging.getLogger(__name__)  # Add this at the top of the file
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.openai_client = None
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        try:
            if OpenAI and self.config.openai_api_key:
                self.openai_client = OpenAI(api_key=self.config.openai_api_key)
                print("OpenAI client initialized successfully.!")
            else:
                print("OpenAI not available or API key missing")
        except Exception as e:
            print(f"Failed to initialize OpenAI client: {e}")
    
    def check_openai_connection(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            if not self.openai_client:
                return False
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return bool(response.choices[0].message.content)
        except:
            return False
    
    def check_database_connection(self) -> bool:
        """Check if database connection is working"""
        print("claling check_database_connection.......")

        try:
            return self.db_manager.test_connection()
        except:
            return False
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        print("claling get_available_tools.......")
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
            print("claling get_database_schema.......")
            return self.db_manager.get_schema_info()
        except Exception as e:
            return {
                "status": "error",
                "error_code": "ORA-SCHEMA-FAIL",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def execute_oracle_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Oracle-style SQL query and format result with metadata"""
        try:
            print(f"Executing Oracle query: {query}")

            print("calling execture oracle querty.......")
            result = self.db_manager.execute_query(query, parameters)

            if result.get("status") == "success":
                return {
                    "status": "success",
                    "execution_time_ms": round(result.get("execution_time", 0) * 1000, 2),
                    "rows_affected": len(result.get("data", [])),
                    "data": result.get("data", []),
                    "columns": result.get("columns", []),
                    "oracle_metadata": {
                        "session_id": "ADB_SESSION_001",  # Optional: make dynamic
                        "database_version": result.get("version", "Oracle Database 19c"),
                        "service_name": "autonomous_db_high",  # Optional: dynamic
                        "connection_pool": "default_pool",    # Optional: dynamic
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "status": "error",
                    "error_code": "ORA-00942",  # Replace with actual code if available
                    "error_message": result.get("error", "Unknown Oracle error"),
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "status": "error",
                "error_code": "ORA-00001",  # Generic application error
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
    def make_api_call(self, url: str, method: str = "GET") -> Dict[str, Any]:
        """Make HTTP API call"""
        try:
            import requests
            
            response = requests.request(method, url, timeout=30)
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "status": "success" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "data": response_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def execute_agent_query(self, query: str) -> Dict[str, Any]:
        """Execute a query through the MCP agent"""
        print("claling execute_agent_query.......")

        try:
            start_time = datetime.now()
            tool_executions = []
            
            # Simple query analysis
            query_lower = query.lower()
            
            # Build response
            response_parts = []
            
            # Handle database queries
            if any(keyword in query_lower for keyword in ['select', 'table', 'database', 'employee', 'department', 'order', 'product']):
                if "employee" in query_lower:
                    sql_query = "SELECT * FROM employees FETCH FIRST 10 ROWS ONLY"
                elif "department" in query_lower:
                    sql_query = "SELECT * FROM departments"
                elif "order" in query_lower:
                    sql_query = "SELECT * FROM orders ORDER BY orderid FETCH FIRST 10 ROWS ONLY"
                elif "table" in query_lower or "schema" in query_lower:
                    sql_query = "SELECT table_name FROM user_tables"
                else:
                    sql_query = "SELECT table_name FROM user_tables"
                
                query_result = self.execute_oracle_query(sql_query)
                print("query_result")
                tool_executions.append({
                    "tool_name": "oracle_query_executor",
                    "input": {"sql_query": sql_query},
                    "output": query_result,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                
                if query_result.get("status") == "success":
                    response_parts.append(f"Database query executed successfully. Found {len(query_result.get('data', []))} records.")
                else:
                    response_parts.append(f"Database query failed: {query_result.get('error_message', 'Unknown error')}")
            
            # Handle API requests
            if any(keyword in query_lower for keyword in ['api', 'http', 'request']):
                api_result = self.make_api_call("https://jsonplaceholder.typicode.com/posts/1")
                tool_executions.append({
                    "tool_name": "api_caller",
                    "input": {"url": "https://jsonplaceholder.typicode.com/posts/1", "method": "GET"},
                    "output": api_result,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                response_parts.append("API call executed successfully.")
            
            # Use OpenAI if available
            if self.openai_client:
                try:
                    ai_response = self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are an Oracle ADB expert assistant. Provide helpful responses about database operations and enterprise data management."},
                            {"role": "user", "content": query}
                        ],
                        max_tokens=500
                    )
                    if ai_response.choices[0].message.content:
                        response_parts.append(ai_response.choices[0].message.content)
                except Exception as e:
                    response_parts.append(f"AI assistant unavailable: {str(e)}")
            else:
                response_parts.append("I'm an Oracle ADB assistant. I can help you with database queries, schema exploration, and API calls.")
            
            # Combine responses
            final_response = "\n\n".join(response_parts) if response_parts else "I understand your query. How can I help you with Oracle ADB operations?"
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "response": final_response,
                "tool_executions": tool_executions,
                "timestamp": start_time.isoformat(),
                "execution_time": execution_time,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "tool_executions": [],
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def reset_memory(self):
        """Reset agent conversation memory"""
        pass
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return []