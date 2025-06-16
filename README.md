# Oracle ADB AI Agent - Enterprise LangChain Integration

Enterprise-grade LangChain agent with Oracle Autonomous Database (ADB) integration using Model Context Protocol (MCP) for AI-powered database operations and API orchestration.

## Overview

This system provides a sophisticated AI-powered interface for Oracle database operations, combining natural language processing with enterprise database connectivity. The agent can understand complex queries, execute SQL operations, explore schema relationships, and integrate with external APIs.

## Key Features

### AI-Powered Database Operations
- Natural language to SQL translation using OpenAI GPT-4o
- Intelligent query optimization and result interpretation
- Context-aware database exploration and schema discovery

### Enterprise Oracle ADB Integration
- Production-ready Oracle Autonomous Database connectivity
- Wallet-based secure authentication
- Connection pooling for high-performance operations
- Transaction management with rollback capabilities

### Model Context Protocol (MCP) Server
- Microservices architecture for tool orchestration
- Real-time tool execution monitoring
- Comprehensive error handling and logging
- Extensible plugin architecture

### Interactive Web Interface
- Streamlit-based chat interface with real-time responses
- Visual query result display with data tables
- One-click deployment configuration presets
- System health monitoring and status indicators

### Advanced Analytics & Reporting
- Multi-table join operations with complex filtering
- Salary analytics and department performance metrics
- Sales analysis with employee performance tracking
- Real-time schema exploration and relationship mapping

## Quick Start Guide

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd oracle-adb-ai-agent

# Dependencies are already installed in the current environment
```

### 2. Configuration

#### Required Environment Variables
```bash
# OpenAI Configuration
export OPENAI_API_KEY="sk-your-openai-api-key"

# Oracle ADB Configuration (for production)
export ORACLE_WALLET_LOCATION="/path/to/oracle/wallet"
export ORACLE_WALLET_PASSWORD="your_wallet_password"
export ORACLE_CONNECTION_STRING="service_name_high"
export ORACLE_USERNAME="ADMIN"
export ORACLE_PASSWORD="your_db_password"

# Application Configuration
export LOG_LEVEL="INFO"
export ENVIRONMENT="production"
```

#### Alternative: Use Web Interface
- Enter OpenAI API key directly in the web interface sidebar
- Select deployment preset (Development/Production/Testing/Demo)
- System will guide you through configuration

### 3. Run Application

```bash
streamlit run app.py --server.port 5000
```

Access the application at: `http://localhost:5000`

## Architecture Deep Dive

### System Components

```
┌─────────────────────────────────────────────────────┐
│                Web Interface                        │
│            (Streamlit + Chat UI)                   │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                MCP Server                           │
│         (Query Orchestration + AI)                 │
└─────────┬───────────────────────────┬───────────────┘
          │                           │
┌─────────▼─────────┐       ┌─────────▼─────────┐
│  Database Tools   │       │   API Tools       │
│ • Query Executor  │       │ • HTTP Requests   │
│ • Schema Explorer │       │ • Authentication  │
│ • Transactions    │       │ • Response Parser │
└─────────┬─────────┘       └─────────┬─────────┘
          │                           │
┌─────────▼─────────┐       ┌─────────▼─────────┐
│   Oracle ADB      │       │  External APIs    │
│ • Employee Data   │       │ • REST Services   │
│ • Department Info │       │ • JSON APIs       │
│ • Order Records   │       │ • Status Checks   │
└───────────────────┘       └───────────────────┘
```

### Data Model

The system includes a comprehensive enterprise data model:

**Employees Table**
- Employee ID, Name, Department ID
- Salary, Hire Date, Email
- Performance metrics and status

**Departments Table**
- Department ID, Name, Budget
- Manager ID, Location, Status
- Performance tracking

**Orders Table**
- Order ID, Customer Name, Amount
- Order Date, Status, Employee ID
- Revenue tracking and analytics

## Usage Examples

### Basic Database Queries

```
User: "Show me all employees in the database"
Response: Returns formatted table with employee details

User: "What departments do we have and their budgets?"
Response: Department overview with financial information

User: "Find the top 10 highest paid employees"
Response: Salary rankings with department information
```

### Advanced Analytics

```
User: "What is the average salary by department?"
Response: Statistical analysis with department comparisons

User: "Show me sales performance by employee for this quarter"
Response: Revenue analysis with individual performance metrics

User: "Find employees hired in the last year working in high-budget departments"
Response: Complex filtered results with multi-table joins
```

### Schema Exploration

```
User: "What tables are available in the database?"
Response: Complete schema overview with table descriptions

User: "How are employees and departments connected?"
Response: Relationship mapping with foreign key details

User: "Show me the structure of the orders table"
Response: Column details with data types and constraints
```

### API Integration

```
User: "Test external API connectivity"
Response: API call execution with status and response data

User: "Check system health and tool availability"
Response: Comprehensive system status report
```

## Configuration Management

### Deployment Presets

#### Development Configuration
```yaml
LOG_LEVEL: DEBUG
API_TIMEOUT: 30 seconds
API_MAX_RETRIES: 3
CACHE_TOOL_RESULTS: enabled
ENVIRONMENT: development
```

#### Production Configuration
```yaml
LOG_LEVEL: INFO
API_TIMEOUT: 15 seconds
API_MAX_RETRIES: 5
CACHE_TOOL_RESULTS: enabled
ENVIRONMENT: production
```

#### Testing Configuration
```yaml
LOG_LEVEL: WARNING
API_TIMEOUT: 60 seconds
API_MAX_RETRIES: 1
CACHE_TOOL_RESULTS: disabled
ENVIRONMENT: testing
```

#### Demo Configuration
```yaml
LOG_LEVEL: INFO
API_TIMEOUT: 20 seconds
API_MAX_RETRIES: 2
CACHE_TOOL_RESULTS: enabled
ENVIRONMENT: demo
```

## File Structure and Responsibilities

```
oracle-adb-ai-agent/
├── app.py                    # Main Streamlit web interface
├── working_mcp_server.py     # Simplified MCP server implementation
├── mcp_server.py            # Full-featured MCP server
├── database.py              # Database connection and operations
├── oracle_connection.py     # Production Oracle ADB connectivity
├── oracle_tools.py          # Oracle-specific database tools
├── api_tools.py             # External API integration tools
├── config.py                # Configuration management
├── logger.py                # Comprehensive logging system
├── DOCUMENTATION.md         # Complete technical documentation
├── dependencies.txt         # Python package requirements
├── architecture_diagram.svg # System architecture visualization
└── .streamlit/
    └── config.toml          # Streamlit server configuration
```

## Production Deployment

### Oracle ADB Setup

1. **Download Oracle Wallet**
   ```bash
   # From Oracle Cloud Infrastructure Console
   # Navigate to Autonomous Database → DB Connection
   # Download Client Credentials (Wallet)
   ```

2. **Configure Wallet**
   ```bash
   # Extract wallet to secure location
   unzip wallet.zip -d /secure/path/wallet/
   
   # Set permissions
   chmod 600 /secure/path/wallet/*
   
   # Set environment variable
   export TNS_ADMIN=/secure/path/wallet/
   ```

3. **Validate Connection**
   ```bash
   # Test connection using provided validation script
   python oracle_connection.py
   ```

### Security Best Practices

- **API Key Management**: Store OpenAI API keys in secure environment variables
- **Database Security**: Use Oracle Wallet for encrypted authentication
- **Network Security**: Deploy behind load balancer with SSL/TLS termination
- **Access Control**: Implement proper user authentication and authorization
- **Audit Logging**: Enable comprehensive audit trails for all operations

### Performance Optimization

- **Connection Pooling**: Configure optimal pool sizes for concurrent users
- **Query Caching**: Enable intelligent caching for frequently accessed data
- **Resource Monitoring**: Implement monitoring for CPU, memory, and database connections
- **Load Balancing**: Deploy multiple instances behind load balancer for high availability

## Troubleshooting Guide

### Common Issues and Solutions

#### Database Connection Problems
```
Problem: "Oracle connection failed"
Solutions:
1. Verify wallet file permissions (600)
2. Check TNS_ADMIN environment variable
3. Validate connection string format
4. Test network connectivity to Oracle Cloud
5. Verify wallet password correctness
```

#### OpenAI API Issues
```
Problem: "OpenAI API authentication failed"
Solutions:
1. Verify API key format (starts with sk-)
2. Check API key validity on OpenAI platform
3. Verify account billing status and credits
4. Check rate limits and usage quotas
5. Test API connectivity with curl
```

#### Tool Execution Failures
```
Problem: "Tool execution timeout or error"
Solutions:
1. Review application logs for detailed errors
2. Check database connection status
3. Validate query syntax and parameters
4. Verify tool configuration and permissions
5. Test individual tools in isolation
```

## Development and Extension

### Adding Custom Tools

1. **Create Tool Class**
   ```python
   from langchain.tools import BaseTool
   
   class CustomTool(BaseTool):
       name = "custom_tool"
       description = "Description of tool functionality"
       
       def _run(self, input_data: str) -> str:
           # Implementation logic
           return result
   ```

2. **Register Tool**
   ```python
   # In MCP server initialization
   def _initialize_tools(self):
       self.tools.append(CustomTool())
   ```

3. **Update UI** (if needed)
   ```python
   # Add tool-specific display logic in app.py
   ```

### Custom Database Providers

1. **Extend Database Manager**
   ```python
   class CustomDBManager(DatabaseManager):
       def __init__(self, connection_params):
           # Custom initialization
           pass
       
       def execute_query(self, query, parameters):
           # Provider-specific implementation
           pass
   ```

2. **Update Configuration**
   ```python
   # Add provider-specific configuration options
   ```

## API Reference

### Core Classes

#### WorkingMCPServer
- `execute_agent_query(query: str)` → Dict[str, Any]
- `execute_oracle_query(query: str, parameters: Dict)` → Dict[str, Any]
- `make_api_call(url: str, method: str)` → Dict[str, Any]
- `check_openai_connection()` → bool
- `get_database_schema()` → Dict[str, Any]

#### DatabaseManager
- `execute_query(query: str, parameters: Dict)` → Dict[str, Any]
- `begin_transaction()` → None
- `commit_transaction()` → None
- `rollback_transaction()` → None
- `get_schema_info()` → Dict[str, Any]

#### OracleADBConnection
- `create_connection_pool(min_conn: int, max_conn: int)` → bool
- `execute_query(query: str, parameters: Dict, fetch_mode: str)` → Dict[str, Any]
- `get_schema_info()` → Dict[str, Any]
- `get_table_details(table_name: str)` → Dict[str, Any]
- `test_connection()` → Dict[str, Any]

## Support and Contributing

### Enterprise Support
For enterprise deployment assistance, custom integrations, or technical support, contact the development team.

### Contributing Guidelines
1. Fork the repository
2. Create feature branch
3. Implement changes with comprehensive tests
4. Update documentation
5. Submit pull request with detailed description

### License
This project is licensed under the MIT License. See LICENSE file for details.

---

**Built with enterprise-grade security, performance, and reliability in mind.**