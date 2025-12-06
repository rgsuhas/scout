# VS Code MCP Server Integration Guide

## Overview
This project has been configured as a Model Context Protocol (MCP) server for VS Code. It provides AI-powered roadmap generation and update functionality to the Claude extension in VS Code.

## Setup Instructions

### 1. **Install MCP for VS Code**
- Install the latest version of VS Code
- Ensure you have Claude extension or MCP extension installed from the VS Code marketplace

### 2. **Configure the MCP Server in VS Code Settings**

The MCP server configuration can be added in one of two ways:

#### Option A: Using the Project Configuration File (Recommended)
The `mcp-server-config.json` file in the project root contains the server configuration:

```json
{
  "mcpServers": {
    "pathfinder-roadmap-service": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/home/rg/gbl/scout",
      "env": {
        "PYTHONPATH": "/home/rg/gbl/scout",
        "AI_PROVIDER": "google",
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
        "GOOGLE_MODEL": "gemini-2.5-flash",
        "AI_MAX_TOKENS": "65536",
        "AI_TEMPERATURE": "0.7",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

#### Option B: Manual Configuration in VS Code Settings
1. Open VS Code Settings (Cmd/Ctrl + ,)
2. Search for "MCP Servers" or navigate to Extensions > Claude > Settings
3. Add the server configuration:
   ```json
   {
     "pathfinder-roadmap-service": {
       "command": "python",
       "args": ["-m", "src.mcp_server"],
       "cwd": "/home/rg/gbl/scout",
       "env": {
         "PYTHONPATH": "/home/rg/gbl/scout",
         "GOOGLE_API_KEY": "your-api-key-here"
       }
     }
   }
   ```

### 3. **Set Environment Variables**
Ensure the following environment variables are set in your `.env` file (already configured):
- `AI_PROVIDER=google`
- `GOOGLE_API_KEY=<your-api-key>`
- `GOOGLE_MODEL=gemini-2.5-flash`
- `AI_MAX_TOKENS=65536`
- `AI_TEMPERATURE=0.7`
- `AI_TIMEOUT=60`

### 4. **Install Dependencies**
If not already installed, run:
```bash
pip install -r requirements.txt
```

## Available Tools

The MCP server exposes two main tools to Claude:

### 1. `generate_roadmap`
Generates a personalized learning roadmap based on user goals and skills.

**Parameters:**
- `user_goal` (string): Target career goal (e.g., 'Full Stack Developer')
- `user_skills` (list): List of skill assessments with fields:
  - `skill` (string): Skill name
  - `score` (integer 1-10): Proficiency score
  - `level` (string): "beginner", "intermediate", or "advanced"
- `experience_level` (string, optional): Overall experience level (default: "beginner")
- `preferences` (object, optional): Learning preferences
- `user_id` (string, optional): User identifier (default: "mcp-user")

**Example Usage in Claude:**
```
I want a roadmap to become a Full Stack Developer. 
I know:
- JavaScript at level 6 (intermediate)
- Python at level 3 (beginner)
- HTML/CSS at level 5 (intermediate)

My experience level is beginner.
```

### 2. `update_roadmap`
Updates an existing roadmap based on user modifications.

**Parameters:**
- `roadmap_id` (string): Unique identifier for the roadmap
- `user_prompt` (string): Description of modifications (e.g., "Add more Python modules")
- `existing_roadmap` (object, optional): The existing roadmap to update
- `user_id` (string, optional): User identifier (default: "mcp-user")

**Example Usage in Claude:**
```
Update my roadmap to include more Python-focused modules and reduce the timeline by 2 weeks.
```

## Troubleshooting

### MCP Server Not Connecting
1. **Check Python path**: Ensure Python is in your PATH
   ```bash
   which python
   ```

2. **Check dependencies**: Verify all requirements are installed
   ```bash
   pip install -r requirements.txt
   ```

3. **Check logs**: Enable debug logging in VS Code:
   - Open Output panel (View > Output)
   - Select "MCP Server" from the dropdown
   - Look for error messages

4. **Verify configuration**: Ensure `cwd` path is correct and `PYTHONPATH` is set properly

### API Key Issues
- Verify `GOOGLE_API_KEY` is set in your `.env` file
- Check that the API key has access to the Gemini API

### Module Import Errors
- Ensure the project root is in `PYTHONPATH`
- Check that all Python files have proper `__init__.py` files
- Verify the relative imports are correct

## Development

### Running the Server Locally (for testing)
```bash
cd /home/rg/gbl/scout
python -m src.mcp_server
```

### Testing the Server
You can test the MCP server independently:
```bash
# Start the server in one terminal
python -m src.mcp_server

# In another terminal, send test requests via MCP protocol
```

## Architecture

The MCP server consists of:
- **mcp_server.py**: FastMCP server definition with tool implementations
- **services/roadmap_service.py**: Business logic for roadmap generation and updates
- **services/ai_service_factory.py**: Creates appropriate AI service based on provider
- **models/roadmap.py**: Data models for roadmaps and related objects
- **config/settings.py**: Configuration management from environment variables

## Next Steps

1. Verify the configuration in VS Code
2. Test by asking Claude to generate a roadmap
3. Monitor logs if issues occur
4. Adjust API parameters in `.env` as needed for your use case

## References

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [VS Code MCP Integration](https://github.com/modelcontextprotocol/servers)
- [FastMCP Documentation](https://github.com/jloakes/FastMCP)
