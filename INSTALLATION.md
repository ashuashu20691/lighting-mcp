# Installation Guide

## Quick Start

1. **Set your OpenAI API Key**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **The application is ready to run**
   - All dependencies are pre-installed
   - Database is automatically initialized
   - No additional setup required

3. **Access the application**
   - Open your browser to the provided URL
   - Start chatting with the Oracle ADB agent

## Dependencies

The following packages are already installed:

- **Core**: streamlit, openai, pandas, requests, aiohttp
- **LangChain**: langchain, langchain-community, langchain-core, langchain-openai
- **Utilities**: pydantic, python-dotenv, dataclasses-json

## Environment Variables

### Required
- `OPENAI_API_KEY`: Your OpenAI API key for GPT-4o access

### Optional
- `LOG_LEVEL`: Logging level (default: INFO)
- `DB_PATH`: Database file path (default: ./data/enterprise_db.sqlite)
- `API_TIMEOUT`: API request timeout (default: 30 seconds)

## Troubleshooting

**OpenAI Connection Issues:**
- Verify your API key is valid
- Check OpenAI service status
- Ensure sufficient API credits

**Database Issues:**
- Database auto-initializes on first run
- Check file permissions if needed
- Review logs for detailed errors