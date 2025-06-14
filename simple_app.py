import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd

from working_mcp_server import WorkingMCPServer

# Configuration presets
DEPLOYMENT_PRESETS = {
    "Development": {
        "description": "Local development with detailed logging",
        "config": {
            "LOG_LEVEL": "DEBUG",
            "API_TIMEOUT": "30",
            "API_MAX_RETRIES": "3",
            "CACHE_TOOL_RESULTS": "true",
            "ENVIRONMENT": "development"
        }
    },
    "Production": {
        "description": "Production deployment with optimized settings",
        "config": {
            "LOG_LEVEL": "INFO",
            "API_TIMEOUT": "15",
            "API_MAX_RETRIES": "5",
            "CACHE_TOOL_RESULTS": "true",
            "ENVIRONMENT": "production"
        }
    },
    "Testing": {
        "description": "Testing environment with verbose logging",
        "config": {
            "LOG_LEVEL": "WARNING",
            "API_TIMEOUT": "60",
            "API_MAX_RETRIES": "1",
            "CACHE_TOOL_RESULTS": "false",
            "ENVIRONMENT": "testing"
        }
    },
    "Demo": {
        "description": "Demo setup with sample data focus",
        "config": {
            "LOG_LEVEL": "INFO",
            "API_TIMEOUT": "20",
            "API_MAX_RETRIES": "2",
            "CACHE_TOOL_RESULTS": "true",
            "ENVIRONMENT": "demo"
        }
    }
}

# Example queries
EXAMPLE_QUERIES = [
    {
        "title": "📊 Show all employees",
        "query": "Show me all employees in the database",
        "category": "Database"
    },
    {
        "title": "🏢 Department information",
        "query": "What departments do we have?",
        "category": "Database"
    },
    {
        "title": "📦 Recent orders",
        "query": "Show me the latest orders",
        "category": "Database"
    },
    {
        "title": "🔍 Database schema",
        "query": "What tables are available in the database?",
        "category": "Schema"
    },
    {
        "title": "🌐 Test API call",
        "query": "Make a test API call to get sample data",
        "category": "API"
    },
    {
        "title": "💡 Ask anything",
        "query": "What can you help me with?",
        "category": "General"
    }
]

@st.cache_resource
def init_mcp_server(api_key=None):
    """Initialize MCP server with optional API key"""
    if api_key:
        import os
        os.environ["OPENAI_API_KEY"] = api_key
    return WorkingMCPServer()

def apply_preset_config(preset_name):
    """Apply configuration preset"""
    if preset_name in DEPLOYMENT_PRESETS:
        preset = DEPLOYMENT_PRESETS[preset_name]
        import os
        for key, value in preset["config"].items():
            os.environ[key] = value
        return True
    return False

def main():
    st.set_page_config(
        page_title="Oracle ADB AI Agent",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Header
    st.title("🤖 Oracle ADB AI Agent")
    st.markdown("Enterprise AI assistant for database operations and API integrations")

    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # OpenAI API Key Input
        st.subheader("🔑 OpenAI API Key")
        api_key_input = st.text_input(
            "Enter your OpenAI API Key",
            type="password",
            help="Get your API key from https://platform.openai.com/api-keys"
        )
        
        if api_key_input:
            st.success("✅ API Key provided")
        else:
            st.warning("⚠️ API Key required for AI responses")
        
        st.divider()
        
        # Deployment Presets
        st.subheader("🚀 Deployment Presets")
        preset_choice = st.selectbox(
            "Choose deployment scenario:",
            options=list(DEPLOYMENT_PRESETS.keys()),
            help="Pre-configured settings for different environments"
        )
        
        if st.button("Apply Preset", type="primary"):
            if apply_preset_config(preset_choice):
                st.success(f"✅ Applied {preset_choice} preset")
                st.rerun()
        
        # Show current preset details
        if preset_choice:
            preset = DEPLOYMENT_PRESETS[preset_choice]
            st.info(f"**{preset_choice}**: {preset['description']}")
            with st.expander("Configuration Details"):
                for key, value in preset["config"].items():
                    st.text(f"{key}: {value}")
        
        st.divider()
        
        # System Status
        st.subheader("📊 System Status")
        if api_key_input:
            mcp_server = init_mcp_server(api_key_input)
            
            # Connection status
            openai_status = mcp_server.check_openai_connection()
            db_status = mcp_server.check_database_connection()
            
            st.metric("OpenAI API", "Connected" if openai_status else "Disconnected")
            st.metric("Database", "Connected" if db_status else "Disconnected")
            st.metric("Available Tools", len(mcp_server.get_available_tools()))
        else:
            st.info("Enter API key to check status")

    # Main Content Area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 Chat Interface")
        
        # Initialize session state
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'tool_executions' not in st.session_state:
            st.session_state.tool_executions = []
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation"):
            st.session_state.messages = []
            st.session_state.tool_executions = []
            st.rerun()
        
        # Display conversation
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                
                # Show tool executions for assistant messages
                if message["role"] == "assistant" and "tool_executions" in message:
                    if message["tool_executions"]:
                        with st.expander("🔧 Tool Executions", expanded=False):
                            for execution in message["tool_executions"]:
                                st.json(execution)
        
        # Chat input
        if prompt := st.chat_input("Ask me about your Oracle database or APIs..."):
            if not api_key_input:
                st.error("Please enter your OpenAI API Key in the sidebar first.")
                return
            
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.write(prompt)
            
            # Process with MCP server
            with st.chat_message("assistant"):
                with st.spinner("Processing your request..."):
                    try:
                        mcp_server = init_mcp_server(api_key_input)
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
                        
                        # Show tool executions if any
                        if result.get("tool_executions"):
                            with st.expander("🔧 Tool Executions", expanded=True):
                                for execution in result["tool_executions"]:
                                    st.json(execution)
                        
                    except Exception as e:
                        error_msg = f"Error processing request: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
    
    with col2:
        st.header("💡 Examples")
        st.markdown("Click any example to try it:")
        
        # Group examples by category
        categories = {}
        for example in EXAMPLE_QUERIES:
            category = example["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(example)
        
        for category, examples in categories.items():
            st.subheader(f"📁 {category}")
            for example in examples:
                if st.button(example["title"], key=f"example_{example['title']}", use_container_width=True):
                    if not api_key_input:
                        st.error("Please enter your OpenAI API Key first.")
                        continue
                    
                    # Add to chat
                    st.session_state.messages.append({"role": "user", "content": example["query"]})
                    st.rerun()
        
        st.divider()
        
        # Architecture Overview
        st.header("🏗️ Architecture")
        st.markdown("""
        **System Components:**
        - 🌐 **Streamlit Interface**: Web-based chat UI
        - 🤖 **MCP Server**: Query orchestration
        - 🧠 **OpenAI GPT-4o**: AI responses
        - 🗄️ **Oracle ADB Simulation**: Database operations
        - 🔌 **API Tools**: External service calls
        """)
        
        # Quick Stats
        if api_key_input and 'messages' in st.session_state:
            st.header("📈 Session Stats")
            st.metric("Messages", len(st.session_state.messages))
            st.metric("Tool Calls", len(st.session_state.tool_executions))

if __name__ == "__main__":
    main()