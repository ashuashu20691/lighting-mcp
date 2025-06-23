"""
Enhanced MCP Server with API Tools Integration
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
from enum import Enum
import os
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from database import DatabaseManager
from config import Config
from api_tools import APICallTool, HTTPRequestTool  # Import the API tools

class Status(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

class MCP:
    """
    Microservices Control Plane Server with integrated API tools
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.openai_client = None
        self.api_tools = {
            'api_caller': APICallTool(),
            'http_request_tool': HTTPRequestTool()
        }
        self._initialize_openai()
        self._initialize_services()

    def _initialize_openai(self):
        """Initialize OpenAI client if API key is available"""
        try:
            if self.config.openai_api_key and OpenAI:
                self.openai_client = OpenAI(api_key=self.config.openai_api_key)
                self.logger.info("OpenAI client initialized successfully")
            else:
                self.logger.warning("OpenAI client not initialized - API key missing or module unavailable")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")

    def _initialize_services(self):
        """Initialize all required services"""
        try:
            # Test database connection
            db_status = self.db_manager.test_connection()
            self.logger.info(f"Database connection status: {db_status}")
            
            # Initialize available tools
            self.available_tools = self.get_available_tools()
            self.logger.info(f"Initialized {len(self.available_tools)} tools")
            
        except Exception as e:
            self.logger.error(f"Service initialization failed: {e}")

    def check_openai_connection(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            if not self.openai_client:
                return False
            
            # Test with a simple completion
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            self.logger.error(f"OpenAI connection check failed: {e}")
            return False

    def check_database_connection(self) -> bool:
        """Check if database connection is working"""
        try:
            return self.db_manager.test_connection()
        except Exception as e:
            self.logger.error(f"Database connection check failed: {e}")
            return False

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            schema_info = self.db_manager.get_schema_info()
            return {
                "status": Status.SUCCESS.value,
                "data": schema_info,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get database schema: {e}")
            return {
                "status": Status.ERROR.value,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def execute_oracle_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute SQL query against Oracle database"""
        try:
            self.logger.info(f"Executing Oracle query: {query[:100]}...")
            result = self.db_manager.execute_query(query, parameters)
            
            return {
                "status": Status.SUCCESS.value,
                "data": result.get("data", []),
                "row_count": result.get("row_count", 0),
                "execution_time": result.get("execution_time", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Oracle query execution failed: {e}")
            return {
                "status": Status.ERROR.value,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get detailed list of available tools including API tools"""
        base_tools = [
            {
                "name": "oracle_query_executor",
                "description": "Execute SQL queries against Oracle ADB",
                "parameters": ["query", "parameters"],
                "return_type": "Dict[str, Any]"
            },
            {
                "name": "oracle_schema_explorer",
                "description": "Explore database schema and metadata",
                "parameters": [],
                "return_type": "Dict[str, Any]"
            }
        ]
        
        # Add API tools to the available tools list
        api_tools = []
        for tool_name, tool_instance in self.api_tools.items():
            api_tools.append({
                "name": tool_name,
                "description": tool_instance.description,
                "parameters": list(tool_instance.args_schema.schema()['properties'].keys()),
                "return_type": "Dict[str, Any]"
            })
        
        return base_tools + api_tools

    def make_api_call(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, 
                     body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP API call using the integrated API tool"""
        try:
            # Use the APICallTool for the request
            result = self.api_tools['api_caller']._run(
                url=url,
                method=method,
                headers=headers,
                data=body
            )
            return json.loads(result)
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            return {
                "status": Status.ERROR.value,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def execute_agent_query(self, query: str) -> Dict[str, Any]:
        """Execute a query through the MCP agent with API tool integration"""
        self.logger.info(f"Processing agent query: {query[:100]}...")
        
        try:
            start_time = datetime.now()
            tool_executions = []
            response_parts = []
            
            query_analysis = self._analyze_query(query.lower())
            
            # Process database queries
            if query_analysis["is_database_query"]:
                result = self._handle_database_query(query, query_analysis)
                tool_executions.extend(result.get("tool_executions", []))
                response_parts.append(result.get("response", ""))
            
            # Process API requests using the integrated tools
            if query_analysis["is_api_request"]:
                result = await self._handle_api_request_with_tools(query, query_analysis)
                tool_executions.extend(result.get("tool_executions", []))
                response_parts.append(result.get("response", ""))
            
            # Process system status queries
            if query_analysis["is_system_query"]:
                result = self._handle_system_query(query, query_analysis)
                tool_executions.extend(result.get("tool_executions", []))
                response_parts.append(result.get("response", ""))
            
            # Generate AI response if needed
            if not response_parts or query_analysis["requires_ai"]:
                ai_response = self._generate_ai_response(query, query_analysis)
                response_parts.append(ai_response)
            
            final_response = "\n\n".join(filter(None, response_parts)) or "How can I assist you?"
            
            return {
                "response": final_response,
                "tool_executions": tool_executions,
                "timestamp": start_time.isoformat(),
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "status": Status.SUCCESS.value
            }
            
        except Exception as e:
            self.logger.error(f"Agent query processing failed: {e}")
            return {
                "response": f"Error processing request: {str(e)}",
                "tool_executions": [],
                "timestamp": datetime.now().isoformat(),
                "status": Status.ERROR.value,
                "error": str(e)
            }

    async def _handle_api_request_with_tools(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API requests using the integrated API tools"""
        tool_executions = []
        response = ""
        
        try:
            # Determine which API tool to use based on query
            if "complex" in query.lower() or "auth" in query.lower():
                # Use the advanced HTTP tool for complex requests
                tool_name = "http_request_tool"
                auth_details = {"type": "bearer", "token": "sample_token"}  # Example
                result = self.api_tools[tool_name]._run(
                    url="https://api.example.com/data",
                    method="GET",
                    auth=auth_details
                )
            else:
                # Use the standard API caller for simple requests
                tool_name = "api_caller"
                result = self.api_tools[tool_name]._run(
                    url="https://jsonplaceholder.typicode.com/posts/1",
                    method="GET"
                )
            
            # Process the tool result
            parsed_result = json.loads(result)
            tool_executions.append({
                "tool_name": tool_name,
                "input": {"query": query},
                "output": parsed_result,
                "status": Status.SUCCESS.value if parsed_result.get("status") == "success" else Status.ERROR.value,
                "timestamp": datetime.now().isoformat()
            })
            
            response = self._format_api_response(parsed_result)
            
        except Exception as e:
            self.logger.error(f"API request handling failed: {e}")
            response = f"Error processing API request: {str(e)}"
            
        return {
            "response": response,
            "tool_executions": tool_executions
        }

    def _format_api_response(self, api_result: Dict[str, Any]) -> str:
        """Format API response for display"""
        if api_result.get("status") == "success":
            if isinstance(api_result.get("data"), dict):
                return "API request successful. Received structured data."
            elif isinstance(api_result.get("data"), list):
                return f"API request successful. Received {len(api_result['data'])} items."
            else:
                return "API request completed successfully."
        else:
            return f"API request failed: {api_result.get('error_message', 'Unknown error')}"

    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Advanced query analysis to determine processing requirements"""
        query_lower = query.lower()
        
        # Database-related keywords (expanded)
        db_keywords = [
            'select', 'table', 'database', 'schema', 'sql', 'query', 'data',
            'employee', 'department', 'order', 'customer', 'column', 'row',
            'insert', 'update', 'delete', 'join', 'where', 'group by',
            'employees', 'departments', 'orders', 'customers', 'records',
            'show me', 'get all', 'find', 'list', 'retrieve', 'fetch',
            'structure', 'tables', 'metadata', 'information'
        ]
        
        # API-related keywords (expanded)
        api_keywords = [
            'api', 'http', 'request', 'endpoint', 'call', 'external',
            'service', 'rest', 'json', 'response', 'web service',
            'integration', 'third party', 'remote', 'fetch data',
            'jsonplaceholder', 'typicode', 'posts', 'users'
        ]
        
        # AI assistance keywords (expanded)
        ai_keywords = [
            'explain', 'how', 'what', 'why', 'help', 'describe', 'tell me',
            'analyze', 'suggest', 'recommend', 'optimize', 'improve',
            'understand', 'clarify', 'breakdown', 'summary', 'overview',
            'best practice', 'advice', 'guidance', 'meaning', 'purpose'
        ]
        
        # System/status keywords
        system_keywords = [
            'status', 'health', 'check', 'connection', 'available', 'tools',
            'system', 'server', 'running', 'working', 'test', 'verify'
        ]
        
        # Check for database queries
        is_database_query = any(keyword in query_lower for keyword in db_keywords)
        
        # Check for API requests
        is_api_request = any(keyword in query_lower for keyword in api_keywords)
        
        # Check if AI assistance is needed
        requires_ai = any(keyword in query_lower for keyword in ai_keywords)
        
        # Check for system status queries
        is_system_query = any(keyword in query_lower for keyword in system_keywords)
        
        # Determine query intent more specifically
        query_intent = "general"
        if "schema" in query_lower or "structure" in query_lower or "tables" in query_lower:
            query_intent = "schema_exploration"
        elif any(word in query_lower for word in ['employee', 'department', 'order', 'customer']):
            query_intent = "data_retrieval"
        elif is_api_request:
            query_intent = "api_call"
        elif is_system_query:
            query_intent = "system_status"
        elif requires_ai and not is_database_query:
            query_intent = "ai_assistance"
        
        return {
            "is_database_query": is_database_query,
            "is_api_request": is_api_request,
            "requires_ai": requires_ai,
            "is_system_query": is_system_query,
            "is_complex": len(query.split()) > 10,
            "query_intent": query_intent,
            "word_count": len(query.split()),
            "confidence": self._calculate_confidence(query_lower, db_keywords, api_keywords, ai_keywords, system_keywords)
        }
    
    def _calculate_confidence(self, query: str, db_kw: list, api_kw: list, ai_kw: list, sys_kw: list) -> Dict[str, float]:
        """Calculate confidence scores for different query types"""
        total_words = len(query.split())
        
        db_matches = sum(1 for kw in db_kw if kw in query)
        api_matches = sum(1 for kw in api_kw if kw in query)
        ai_matches = sum(1 for kw in ai_kw if kw in query)
        sys_matches = sum(1 for kw in sys_kw if kw in query)
        
        return {
            "database": min(db_matches / max(total_words * 0.3, 1), 1.0),
            "api": min(api_matches / max(total_words * 0.3, 1), 1.0),
            "ai": min(ai_matches / max(total_words * 0.3, 1), 1.0),
            "system": min(sys_matches / max(total_words * 0.3, 1), 1.0)
        }
    
    def _handle_database_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database-related queries with enhanced schema support"""
        tool_executions = []
        response = ""
        
        try:
            query_intent = analysis.get("query_intent", "general")
            
            if query_intent == "schema_exploration" or any(word in query.lower() for word in ["schema", "structure", "tables", "metadata"]):
                # Schema exploration
                schema_result = self.get_database_schema()
                tool_executions.append({
                    "tool_name": "oracle_schema_explorer",
                    "input": {"query": query, "intent": "schema_exploration"},
                    "output": schema_result,
                    "status": Status.SUCCESS.value if schema_result["status"] == Status.SUCCESS.value else Status.ERROR.value,
                    "timestamp": datetime.now().isoformat()
                })
                
                if schema_result["status"] == Status.SUCCESS.value:
                    schema_data = schema_result.get("data", {})
                    tables = schema_data.get("tables", [])
                    
                    if tables:
                        table_names = [table.get("name", "Unknown") for table in tables]
                        response = f"Database schema retrieved successfully. Found {len(tables)} tables: {', '.join(table_names[:5])}{'...' if len(table_names) > 5 else ''}. "
                        response += "The schema includes table structures, column definitions, and relationships."
                    else:
                        response = "Database schema retrieved but no tables found."
                else:
                    response = f"Failed to retrieve schema information: {schema_result.get('error_message', 'Unknown error')}"
                    
            elif query_intent == "data_retrieval" or any(word in query.lower() for word in ["employee", "department", "order", "customer", "show", "get", "list"]):
                # Data retrieval
                sql_query = self._generate_sql_from_query(query)
                query_result = self.execute_oracle_query(sql_query)
                
                tool_executions.append({
                    "tool_name": "oracle_query_executor", 
                    "input": {"sql_query": sql_query, "intent": "data_retrieval"},
                    "output": query_result,
                    "status": Status.SUCCESS.value if query_result["status"] == Status.SUCCESS.value else Status.ERROR.value,
                    "timestamp": datetime.now().isoformat()
                })
                
                if query_result["status"] == Status.SUCCESS.value:
                    data = query_result.get("data", [])
                    row_count = query_result.get("row_count", 0)
                    response = f"Query executed successfully. Retrieved {row_count} records from the database."
                    
                    if data and len(data) > 0:
                        # Show sample of data structure
                        first_row = data[0] if isinstance(data, list) else data
                        if isinstance(first_row, dict):
                            columns = list(first_row.keys())
                            response += f" Columns: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}"
                else:
                    response = f"Query execution failed: {query_result.get('error_message', 'Unknown error')}"
            else:
                # General database query
                if "select" in query.lower() or "sql" in query.lower():
                    # Direct SQL execution
                    sql_query = query if "select" in query.lower() else self._generate_sql_from_query(query)
                    query_result = self.execute_oracle_query(sql_query)
                    
                    tool_executions.append({
                        "tool_name": "oracle_query_executor",
                        "input": {"sql_query": sql_query, "intent": "custom_sql"},
                        "output": query_result,
                        "status": Status.SUCCESS.value if query_result["status"] == Status.SUCCESS.value else Status.ERROR.value,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    if query_result["status"] == Status.SUCCESS.value:
                        response = f"SQL query executed successfully. Retrieved {query_result.get('row_count', 0)} records."
                    else:
                        response = f"SQL execution failed: {query_result.get('error_message', 'Unknown error')}"
                else:
                    # Default to schema exploration if unclear
                    schema_result = self.get_database_schema()
                    response = "I'll show you the available database information."
                    tool_executions.append({
                        "tool_name": "oracle_schema_explorer",
                        "input": {"query": query, "intent": "default_exploration"},
                        "output": schema_result,
                        "status": Status.SUCCESS.value if schema_result["status"] == Status.SUCCESS.value else Status.ERROR.value,
                        "timestamp": datetime.now().isoformat()
                    })
                    
        except Exception as e:
            self.logger.error(f"Database query handling failed: {e}")
            response = f"Error processing database request: {str(e)}"
            tool_executions.append({
                "tool_name": "error_handler",
                "input": {"query": query, "error": str(e)},
                "output": {"error": str(e)},
                "status": Status.ERROR.value,
                "timestamp": datetime.now().isoformat()
            })
            
        return {
            "response": response,
            "tool_executions": tool_executions
        }
    
    def _generate_sql_from_query(self, query: str) -> str:
        """Generate SQL from natural language query with enhanced pattern matching"""
        query_lower = query.lower()
        
        # Employee-related queries
        if any(word in query_lower for word in ["employee", "employees", "staff", "worker"]):
            if "department" in query_lower:
                return "SELECT e.*, d.department_name FROM employees e LEFT JOIN departments d ON e.department_id = d.department_id FETCH FIRST 20 ROWS ONLY"
            elif "salary" in query_lower or "pay" in query_lower:
                return "SELECT employee_id, first_name, last_name, salary, hire_date FROM employees ORDER BY salary DESC FETCH FIRST 15 ROWS ONLY"
            elif "recent" in query_lower or "new" in query_lower:
                return "SELECT * FROM employees WHERE hire_date >= DATE('now', '-1 year') ORDER BY hire_date DESC FETCH FIRST 10 ROWS ONLY"
            else:
                return "SELECT employee_id, first_name, last_name, email, department_id, hire_date FROM employees FETCH FIRST 15 ROWS ONLY"
        
        # Department-related queries
        elif any(word in query_lower for word in ["department", "departments", "dept"]):
            if "budget" in query_lower:
                return "SELECT department_name, budget, manager_id FROM departments ORDER BY budget DESC"
            elif "employee" in query_lower:
                return "SELECT d.department_name, COUNT(e.employee_id) as employee_count FROM departments d LEFT JOIN employees e ON d.department_id = e.department_id GROUP BY d.department_id, d.department_name"
            else:
                return "SELECT department_id, department_name, manager_id, budget FROM departments"
        
        # Order-related queries
        elif any(word in query_lower for word in ["order", "orders", "sale", "sales"]):
            if "amount" in query_lower or "value" in query_lower:
                return "SELECT order_id, customer_id, order_date, total_amount FROM orders ORDER BY total_amount DESC FETCH FIRST 15 ROWS ONLY"
            elif "recent" in query_lower:
                return "SELECT * FROM orders WHERE order_date >= DATE('now', '-30 days') ORDER BY order_date DESC FETCH FIRST 10 ROWS ONLY"
            else:
                return "SELECT order_id, customer_id, order_date, total_amount, status FROM orders ORDER BY order_date DESC FETCH FIRST 20 ROWS ONLY"
        
        # Customer-related queries
        elif any(word in query_lower for word in ["customer", "customers", "client"]):
            if "order" in query_lower:
                return "SELECT c.customer_id, c.customer_name, COUNT(o.order_id) as order_count, SUM(o.total_amount) as total_spent FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_name FETCH FIRST 15 ROWS ONLY"
            else:
                return "SELECT customer_id, customer_name, email, phone, address FROM customers FETCH FIRST 15 ROWS ONLY"
        
        # Schema/structure queries
        elif any(word in query_lower for word in ["table", "tables", "schema", "structure"]):
            return "SELECT name as table_name, type FROM sqlite_master WHERE type='table' ORDER BY name"
        
        # General data queries
        elif any(word in query_lower for word in ["show", "list", "get", "find", "all"]):
            if "data" in query_lower:
                return "SELECT name as table_name FROM sqlite_master WHERE type='table' ORDER BY name"
            else:
                return "SELECT name as table_name, sql FROM sqlite_master WHERE type='table' LIMIT 5"
        
        # Count queries
        elif "count" in query_lower or "how many" in query_lower:
            if "employee" in query_lower:
                return "SELECT COUNT(*) as employee_count FROM employees"
            elif "department" in query_lower:
                return "SELECT COUNT(*) as department_count FROM departments"
            elif "order" in query_lower:
                return "SELECT COUNT(*) as order_count FROM orders"
            else:
                return "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table'"
        
        # Average/statistics queries
        elif any(word in query_lower for word in ["average", "avg", "mean", "statistics"]):
            if "salary" in query_lower:
                return "SELECT AVG(salary) as average_salary, MIN(salary) as min_salary, MAX(salary) as max_salary FROM employees"
            elif "order" in query_lower or "amount" in query_lower:
                return "SELECT AVG(total_amount) as average_order, MIN(total_amount) as min_order, MAX(total_amount) as max_order FROM orders"
        
        # Default fallback
        return "SELECT name as table_name FROM sqlite_master WHERE type='table' ORDER BY name"
    
    def _handle_system_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system status and monitoring queries"""
        tool_executions = []
        response = ""
        
        try:
            # Get system status
            status = self.get_status()
            
            tool_executions.append({
                "tool_name": "system_status_monitor",
                "input": {"query": query, "intent": "system_monitoring"},
                "output": status,
                "status": Status.SUCCESS.value,
                "timestamp": datetime.now().isoformat()
            })
            
            # Format response based on status
            db_status = "Connected" if status.get("database") else "Disconnected"
            ai_status = "Connected" if status.get("openai") else "Disconnected"
            tool_count = status.get("available_tools", 0)
            
            response = f"System Status Report:\n"
            response += f"- Database: {db_status}\n"
            response += f"- AI Service: {ai_status}\n"
            response += f"- Available Tools: {tool_count}\n"
            response += f"- Server: Running\n"
            response += f"- Timestamp: {status.get('timestamp', 'Unknown')}"
            
            if "tool" in query.lower():
                tools = self.get_available_tools()
                if tools:
                    tool_names = [tool.get("name", "Unknown") for tool in tools]
                    response += f"\n\nAvailable Tools: {', '.join(tool_names)}"
            
        except Exception as e:
            self.logger.error(f"System query handling failed: {e}")
            response = f"Error retrieving system status: {str(e)}"
            tool_executions.append({
                "tool_name": "system_status_monitor",
                "input": {"query": query, "error": str(e)},
                "output": {"error": str(e)},
                "status": Status.ERROR.value,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "response": response,
            "tool_executions": tool_executions
        }
    
    def _generate_ai_response(self, query: str, analysis: Dict[str, Any]) -> str:
        """Generate AI response using OpenAI"""
        if not self.openai_client:
            return "I'm an Oracle ADB assistant. How can I help you with database operations?"
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert Oracle Autonomous Database assistant. " +
                               "Provide concise, technical responses about database operations, " +
                               "schema design, and data management."
                },
                {"role": "user", "content": query}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content or "No response generated"
            
        except Exception as e:
            self.logger.error(f"AI response generation failed: {e}")
            return "I couldn't generate a response. Please try again later."
    
    def reset(self):
        """Reset the MCP server state"""
        self._initialize_services()
        self.logger.info("MCP server reset complete")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "database": self.check_database_connection(),
            "openai": self.check_openai_connection(),
            "available_tools": len(self.available_tools),
            "timestamp": datetime.now().isoformat()
        }

# Alias for backward compatibility
MCPServer = MCP