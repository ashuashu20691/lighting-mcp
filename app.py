import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd

from mcp_server import MCPServer
from logger import get_logger

# Configure logging
logger = get_logger(__name__)

# Initialize MCP Server
@st.cache_resource
def init_mcp_server():
    """Initialize and cache the MCP server instance"""
    server = MCPServer()
    return server

def main():
    st.set_page_config(
        page_title="LangChain Agent with Oracle ADB & MCP Tools",
        page_icon="🔗",
        layout="wide"
    )
    
    st.title("🔗 LangChain Agent with Oracle ADB & MCP Tools")
    st.markdown("Enterprise-grade LLM gateway with Oracle database integration and MCP tool orchestration")
    
    # Initialize MCP server
    mcp_server = init_mcp_server()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Key status
        api_key_status = mcp_server.check_openai_connection()
        if api_key_status:
            st.success("✅ OpenAI API Connected")
        else:
            st.error("❌ OpenAI API Not Connected")
            st.warning("Please check your OPENAI_API_KEY environment variable")
        
        # Database status
        db_status = mcp_server.check_database_connection()
        if db_status:
            st.success("✅ Database Connected")
        else:
            st.error("❌ Database Connection Failed")
        
        # Available tools
        st.subheader("Available Tools")
        tools = mcp_server.get_available_tools()
        for tool in tools:
            st.write(f"• {tool}")
        
        # Clear conversation
        if st.button("Clear Conversation", type="secondary"):
            if 'messages' in st.session_state:
                del st.session_state.messages
            if 'tool_executions' in st.session_state:
                del st.session_state.tool_executions
            st.rerun()
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'tool_executions' not in st.session_state:
        st.session_state.tool_executions = []
    
    # Main chat interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Agent Conversation")
        
        # Display conversation history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                
                # Show tool executions for assistant messages
                if message["role"] == "assistant" and "tool_executions" in message:
                    with st.expander("Tool Executions", expanded=False):
                        for execution in message["tool_executions"]:
                            st.json(execution)
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about your Oracle database or external APIs..."):
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.write(prompt)
            
            # Process with MCP server
            with st.chat_message("assistant"):
                with st.spinner("Processing your request..."):
                    try:
                        # Execute agent query
                        result = asyncio.run(mcp_server.execute_agent_query(prompt))
                        
                        # Display response
                        st.write(result["response"])
                        
                        # Store message with tool executions
                        assistant_message = {
                            "role": "assistant",
                            "content": result["response"],
                            "tool_executions": result.get("tool_executions", [])
                        }
                        st.session_state.messages.append(assistant_message)
                        
                        # Update tool executions in session state
                        if result.get("tool_executions"):
                            st.session_state.tool_executions.extend(result["tool_executions"])
                        
                        # Show tool executions
                        if result.get("tool_executions"):
                            with st.expander("Tool Executions", expanded=True):
                                for execution in result["tool_executions"]:
                                    st.json(execution)
                        
                    except Exception as e:
                        error_msg = f"Error processing request: {str(e)}"
                        st.error(error_msg)
                        logger.error(f"Error in agent execution: {e}")
                        
                        # Add error message to chat
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
    
    with col2:
        st.subheader("Tool Execution History")
        
        if st.session_state.tool_executions:
            # Display recent tool executions
            for i, execution in enumerate(reversed(st.session_state.tool_executions[-10:])):
                with st.expander(f"Execution {len(st.session_state.tool_executions) - i}", expanded=False):
                    st.write(f"**Tool:** {execution.get('tool_name', 'Unknown')}")
                    st.write(f"**Status:** {execution.get('status', 'Unknown')}")
                    st.write(f"**Timestamp:** {execution.get('timestamp', 'Unknown')}")
                    
                    if execution.get('input'):
                        st.write("**Input:**")
                        st.json(execution['input'])
                    
                    if execution.get('output'):
                        st.write("**Output:**")
                        # Handle different output types
                        output = execution['output']
                        if isinstance(output, dict) and 'data' in output:
                            # Database query results
                            if isinstance(output['data'], list) and output['data']:
                                df = pd.DataFrame(output['data'])
                                st.dataframe(df, use_container_width=True)
                            else:
                                st.json(output)
                        else:
                            st.json(output)
                    
                    if execution.get('error'):
                        st.error(f"Error: {execution['error']}")
        else:
            st.info("No tool executions yet. Start a conversation to see tool activity.")
        
        # Database schema info
        st.subheader("Database Schema")
        try:
            schema_info = mcp_server.get_database_schema()
            if schema_info:
                st.json(schema_info)
            else:
                st.info("No schema information available")
        except Exception as e:
            st.error(f"Error loading schema: {e}")
    
    # Footer with system information
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Messages", len(st.session_state.messages))
    
    with col2:
        st.metric("Tool Executions", len(st.session_state.tool_executions))
    
    with col3:
        st.metric("Available Tools", len(tools))

if __name__ == "__main__":
    main()
