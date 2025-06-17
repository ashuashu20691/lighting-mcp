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

# Enhanced example queries with better categorization and descriptions
EXAMPLE_QUERIES = [
    {
        "title": "📊 View All Employees",
        "query": "Show me all employees with their details including department and salary information",
        "category": "Database Queries",
        "description": "Retrieve complete employee roster",
        "complexity": "Basic",
        "expected_result": "Table with employee names, departments, salaries, and hire dates"
    },
    {
        "title": "🏢 Department Overview",
        "query": "What departments do we have and what are their budgets?",
        "category": "Database Queries", 
        "description": "Get department structure and financial data",
        "complexity": "Basic",
        "expected_result": "Department names with budget allocations"
    },
    {
        "title": "📈 Sales Analysis",
        "query": "Show me the top 10 orders by amount and which employees handled them",
        "category": "Database Queries",
        "description": "Revenue analysis with employee performance",
        "complexity": "Intermediate",
        "expected_result": "Top orders with amounts and responsible employees"
    },
    {
        "title": "💰 Salary Analytics",
        "query": "What is the average salary by department and who are the highest paid employees?",
        "category": "Analytics",
        "description": "Compensation analysis across departments",
        "complexity": "Intermediate", 
        "expected_result": "Average salaries by department plus top earners"
    },
    {
        "title": "🔍 Database Schema Explorer",
        "query": "What tables are available and what columns do they contain?",
        "category": "Schema Discovery",
        "description": "Explore database structure and relationships",
        "complexity": "Basic",
        "expected_result": "Complete schema overview with table structures"
    },
    {
        "title": "📋 Table Relationships",
        "query": "Show me how the employees, departments, and orders tables are connected",
        "category": "Schema Discovery",
        "description": "Understand data relationships and foreign keys",
        "complexity": "Intermediate",
        "expected_result": "Relationship mapping between tables"
    },
    {
        "title": "🌐 External API Test",
        "query": "Make a test API call to fetch sample JSON data",
        "category": "API Integration",
        "description": "Test external service connectivity",
        "complexity": "Basic",
        "expected_result": "JSON response from external API"
    },
    {
        "title": "🔧 System Status Check",
        "query": "Check the status of all database connections and available tools",
        "category": "System Health",
        "description": "Verify system components are working",
        "complexity": "Basic",
        "expected_result": "Connection status and tool availability report"
    },
    {
        "title": "💡 AI Assistant Capabilities",
        "query": "What can you help me with? Show me your available features and tools",
        "category": "Getting Started",
        "description": "Learn about available features and capabilities",
        "complexity": "Basic",
        "expected_result": "Overview of available tools and use cases"
    },
    {
        "title": "🚀 Complex Query Example",
        "query": "Find employees hired in the last year who work in departments with budgets over $100,000 and show their total sales",
        "category": "Advanced Queries",
        "description": "Multi-table join with date and amount filtering",
        "complexity": "Advanced",
        "expected_result": "Filtered employee list with sales performance data"
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

def display_tool_execution(execution):
    """Display tool execution in a user-friendly format"""
    tool_name = execution.get("tool_name", "Unknown Tool")
    status = execution.get("status", "unknown")
    
    # Status indicator
    status_icon = "✅" if status == "completed" else "❌" if status == "error" else "⏳"
    
    st.markdown(f"**{status_icon} {tool_name}**")
    
    # Input display
    if "input" in execution:
        input_data = execution["input"]
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                st.text(f"Input {key}: {value}")
        else:
            st.text(f"Input: {input_data}")
    
    # Output display
    if "output" in execution:
        output_data = execution["output"]
        if isinstance(output_data, dict):
            if output_data.get("status") == "success" and "data" in output_data:
                # Display database results as table
                data = output_data["data"]
                if isinstance(data, list) and data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    st.caption(f"Rows: {len(data)}")
                else:
                    st.info("No data returned")
            else:
                # Display other outputs as formatted text
                if "error_message" in output_data:
                    st.error(f"Error: {output_data['error_message']}")
                else:
                    st.json(output_data)
        else:
            st.text(str(output_data))
    
    # Timestamp
    if "timestamp" in execution:
        st.caption(f"Executed at: {execution['timestamp']}")
    
    st.divider()

def main():
    st.set_page_config(
        page_title="Oracle ADB MCP AI Agent",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Header
    st.title("Oracle ADB MCP AI Agent")
    st.markdown("MCP-powered AI agent for Oracle Autonomous Database operations, API integrations, and cross-cloud management")

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
                                display_tool_execution(execution)
        
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
                                    display_tool_execution(execution)
                        
                    except Exception as e:
                        error_msg = f"Error processing request: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
    
    with col2:
        st.header("💡 Query Examples")
        st.markdown("Explore capabilities with these pre-built examples")
        
        # Filter by complexity
        complexity_filter = st.selectbox(
            "Filter by complexity:",
            ["All", "Basic", "Intermediate", "Advanced"],
            key="complexity_filter"
        )
        
        # Group examples by category
        categories = {}
        for example in EXAMPLE_QUERIES:
            if complexity_filter == "All" or example["complexity"] == complexity_filter:
                category = example["category"]
                if category not in categories:
                    categories[category] = []
                categories[category].append(example)
        
        # Display categories with improved UI
        for category, examples in categories.items():
            with st.expander(f"📁 {category} ({len(examples)} examples)", expanded=True):
                for example in examples:
                    # Create a card-like layout for each example
                    with st.container():
                        col_button, col_info = st.columns([3, 1])
                        
                        with col_button:
                            if st.button(
                                example["title"], 
                                key=f"example_{example['title']}", 
                                use_container_width=True,
                                help=example["description"]
                            ):
                                if not api_key_input:
                                    st.error("Please enter your OpenAI API Key first.")
                                    continue
                                
                                # Add to chat and process immediately
                                st.session_state.messages.append({"role": "user", "content": example["query"]})
                                with st.spinner("Processing your request..."):
                                    try:
                                        mcp_server = init_mcp_server(api_key_input)
                                        result = asyncio.run(mcp_server.execute_agent_query(example["query"]))
                                        
                                        # Add assistant response
                                        assistant_message = {
                                            "role": "assistant",
                                            "content": result["response"],
                                            "tool_executions": result.get("tool_executions", [])
                                        }
                                        st.session_state.messages.append(assistant_message)
                                        
                                        # Rerun to display the new messages
                                        st.rerun()
                                        
                                    except Exception as e:
                                        error_msg = f"Error processing request: {str(e)}"
                                        st.session_state.messages.append({
                                            "role": "assistant",
                                            "content": error_msg
                                        })
                                        st.rerun()
                                # st.rerun()
                        
                        with col_info:
                            # Complexity badge
                            complexity_color = {
                                "Basic": "🟢",
                                "Intermediate": "🟡", 
                                "Advanced": "🔴"
                            }
                            st.caption(f"{complexity_color.get(example['complexity'], '⚪')} {example['complexity']}")
                        
                        # Description and expected result
                        st.caption(f"📝 {example['description']}")
                        st.caption(f"📊 Expected: {example['expected_result']}")
                        st.divider()
        
        # Architecture Overview
        st.header("🏗️ System Architecture")
        
        # Display architecture diagram
        try:
            st.image("architecture_diagram.svg", caption="System Architecture Diagram", use_container_width=True)
        except:
            st.markdown("""
            **System Components:**
            - **Web Interface**: Streamlit chat UI with configuration
            - **MCP Server**: Query orchestration and AI integration  
            - **OpenAI GPT-4o**: Natural language processing
            - **Database Layer**: Oracle ADB simulation with enterprise data
            - **API Tools**: External service integrations
            - **Configuration**: One-click deployment presets
            """)
        
        # Quick Stats
        if api_key_input and 'messages' in st.session_state:
            st.header("📈 Session Statistics")
            
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("Messages", len(st.session_state.messages))
                st.metric("Tool Calls", len(st.session_state.tool_executions))
            
            with col_stat2:
                # Calculate response time average if available
                total_messages = len(st.session_state.messages)
                user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
                st.metric("User Queries", user_messages)
                st.metric("Success Rate", f"{max(0, total_messages-1) * 100 // max(1, total_messages)}%")
        
        # Help section
        st.header("🆘 Need Help?")
        st.markdown("""
        **Getting Started:**
        1. Enter your OpenAI API key in the sidebar
        2. Select a deployment preset (Demo recommended)
        3. Try an example query or ask your own question
        
        **Tips:**
        - Use natural language for database queries
        - Ask about table structures and relationships
        - Test API integrations with sample endpoints
        - Explore advanced analytics and reporting
        """)
        
        if st.button("📚 View Complete Documentation", use_container_width=True):
            st.info("Documentation available in DOCUMENTATION.md file")
        
        if st.button("🔧 Download Oracle Connection Template", use_container_width=True):
            st.info("Oracle connection code available in oracle_connection.py")

if __name__ == "__main__":
    main()
