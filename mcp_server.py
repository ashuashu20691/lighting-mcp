"""
MCP Server - Microservices Control Plane for LLM orchestration
Handles LangChain agent initialization and tool integration
"""

import os
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_openai import OpenAI
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import BaseMessage
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.tools import BaseTool

from oracle_tools import OracleQueryTool, OracleSchemaExplorer, OracleTransactionTool
from api_tools import APICallTool, HTTPRequestTool
from database import DatabaseManager
from config import Config
from logger import get_logger

# Configure logging
logger = get_logger(__name__)

class ToolExecutionCallback(BaseCallbackHandler):
    """Callback handler to track tool executions"""
    
    def __init__(self):
        self.tool_executions: List[Dict[str, Any]] = []
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Track when a tool starts executing"""
        execution = {
            "tool_name": serialized.get("name", "unknown"),
            "input": input_str,
            "timestamp": datetime.now().isoformat(),
            "status": "started"
        }
        self.tool_executions.append(execution)
        logger.info(f"Tool execution started: {serialized.get('name')}")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Track when a tool finishes executing"""
        if self.tool_executions:
            self.tool_executions[-1]["output"] = output
            self.tool_executions[-1]["status"] = "completed"
            self.tool_executions[-1]["end_timestamp"] = datetime.now().isoformat()
        logger.info(f"Tool execution completed")
    
    def on_tool_error(self, error: BaseException, **kwargs) -> None:
        """Track when a tool encounters an error"""
        if self.tool_executions:
            self.tool_executions[-1]["error"] = str(error)
            self.tool_executions[-1]["status"] = "error"
            self.tool_executions[-1]["end_timestamp"] = datetime.now().isoformat()
        logger.error(f"Tool execution error: {error}")

class MCPServer:
    """
    Microservices Control Plane Server
    Orchestrates LLM queries with database and API tool integration
    """
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.agent = None
        self.tools = []
        self.memory = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the LangChain agent with tools and memory"""
        try:
            # Initialize OpenAI LLM
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            self.llm = OpenAI(
                model="gpt-4o",
                temperature=0.7,
                api_key=self.config.openai_api_key,
                max_tokens=2000
            )
            
            # Initialize tools
            self._initialize_tools()
            
            # Initialize memory
            self.memory = ConversationBufferWindowMemory(
                memory_key="chat_history",
                k=10,  # Keep last 10 exchanges
                return_messages=True
            )
            
            # Initialize agent
            self.agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5
            )
            
            logger.info("MCP Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Server: {e}")
            raise
    
    def _initialize_tools(self):
        """Initialize all available tools"""
        self.tools = []
        
        # Oracle Database Tools
        try:
            oracle_query_tool = OracleQueryTool(self.db_manager)
            oracle_schema_tool = OracleSchemaExplorer(self.db_manager)
            oracle_transaction_tool = OracleTransactionTool(self.db_manager)
            
            self.tools.extend([
                oracle_query_tool,
                oracle_schema_tool,
                oracle_transaction_tool
            ])
            logger.info("Oracle database tools initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Oracle tools: {e}")
        
        # API Tools
        try:
            api_call_tool = APICallTool()
            http_request_tool = HTTPRequestTool()
            
            self.tools.extend([
                api_call_tool,
                http_request_tool
            ])
            logger.info("API tools initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize API tools: {e}")
        
        logger.info(f"Total tools initialized: {len(self.tools)}")
    
    def check_openai_connection(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            # Simple test to verify API key
            test_response = self.llm.predict("Hello")
            return len(test_response) > 0
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
        return [tool.name for tool in self.tools]
    
    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            return self.db_manager.get_schema_info()
        except Exception as e:
            logger.error(f"Failed to get database schema: {e}")
            return {}
    
    async def execute_agent_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a query through the LangChain agent
        
        Args:
            query: User query string
            
        Returns:
            Dictionary containing response and tool execution details
        """
        try:
            # Create callback handler to track tool executions
            callback_handler = ToolExecutionCallback()
            
            # Execute agent query
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.agent.run(
                    input=query,
                    callbacks=[callback_handler]
                )
            )
            
            # Parse tool executions
            tool_executions = []
            for execution in callback_handler.tool_executions:
                # Parse JSON output if it's a string
                if isinstance(execution.get("output"), str):
                    try:
                        execution["output"] = json.loads(execution["output"])
                    except json.JSONDecodeError:
                        # Keep as string if not valid JSON
                        pass
                
                tool_executions.append(execution)
            
            result = {
                "response": response,
                "tool_executions": tool_executions,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
            logger.info(f"Agent query executed successfully. Tools used: {len(tool_executions)}")
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
        try:
            self.memory.clear()
            logger.info("Agent memory reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset agent memory: {e}")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history from memory"""
        try:
            messages = self.memory.chat_memory.messages
            history = []
            
            for message in messages:
                history.append({
                    "type": message.__class__.__name__,
                    "content": message.content,
                    "timestamp": getattr(message, 'timestamp', datetime.now().isoformat())
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'db_manager'):
                self.db_manager.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
