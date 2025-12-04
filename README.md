# AI Roadmap Service

**AI-Powered Learning Path Generator** for the Goal-Based LMS

This service generates personalized learning roadmaps using **Google Gemini** (with optional OpenAI support) based on user goals, current skills, and experience level.

## Quick Start

### 1. Setup Environment

Create a `.env` file in the project root with the following content:

```bash
# Create .env file
cat > .env << EOF
AI_PROVIDER=google
GOOGLE_API_KEY=your-google-api-key-here
PORT=8003
ENVIRONMENT=development
EOF
```

Or manually create `.env` and add:
```
AI_PROVIDER=google
GOOGLE_API_KEY=your-google-api-key-here
```

**Required Environment Variables:**
- `AI_PROVIDER`: AI provider to use (default: `google`)
- `GOOGLE_API_KEY`: Your Google Gemini API key (required for default provider)

**Supported AI Providers:**
- **Google Gemini** (default): Requires `GOOGLE_API_KEY` - Fully implemented and tested
- **OpenAI** (optional): Requires `OPENAI_API_KEY` and `openai` package - Partially supported

**Note:** Other providers (Anthropic, Ollama, Hugging Face) are not currently installed. The service is optimized for Google Gemini.

### 2. Install Dependencies

```bash
# Install virtualenv if not available (for systems without python3-venv)
pip3 install --user --break-system-packages virtualenv

# Create virtual environment
virtualenv venv
# or if python3-venv is installed:
# python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

**Note:** If you encounter "externally-managed-environment" errors, use `virtualenv` instead of `python -m venv`, or install `python3-venv` with sudo.

### 3. Run the Service

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Option 1: Using the run script (recommended)
./run.sh

# Option 2: Development mode (with auto-reload)
python src/main.py

# Option 3: Using uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 8003 --reload
```

**Note:** The `run.sh` script automatically activates the virtual environment and sets the correct Python path.

### 4. Test the API (Smoke Test)

Service will be available at: http://localhost:8003

- **API Documentation**: http://localhost:8003/docs
- **Health Check**: http://localhost:8003/health
- **API Status**: http://localhost:8003/

You can quickly verify everything is working with:

```bash
curl http://localhost:8003/health
curl http://localhost:8003/api/v1/providers
```

### 5. Steps to Reproduce Core Flows

#### A. Generate a Roadmap

1. **Ensure service is running**
   - `python src/main.py` (from project root, venv activated)
2. **Check health**
   - `curl http://localhost:8003/health`
3. **Call the generate endpoint**

```bash
curl -X POST http://localhost:8003/api/v1/roadmaps/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_goal": "Full Stack Developer",
    "user_skills": [
      {"skill": "javascript", "score": 6, "level": "intermediate"},
      {"skill": "python", "score": 3, "level": "beginner"}
    ],
    "experience_level": "beginner",
    "preferences": {
      "learning_style": "hands-on",
      "time_commitment": "10 hours/week"
    }
  }'
```

4. **Confirm response**
   - Response should include `success: true`, a populated `roadmap`, and `metadata` with `ai_provider` and `ai_model`.

#### B. Update an Existing Roadmap

1. **Generate a roadmap** using the steps above and copy:
   - `roadmap.id`
   - The full `roadmap` object from the response
2. **Call the update endpoint**:

```bash
curl -X PUT http://localhost:8003/api/v1/roadmaps/<ROADMAP_ID> \
  -H "Content-Type: application/json" \
  -d "{
    \"user_prompt\": \"Add more Python-focused modules and reduce the timeline by 2 weeks. Focus more on backend development.\",
    \"existing_roadmap\": REPLACE_WITH_ROADMAP_JSON
  }"
```

3. **Confirm response**
   - Response should include an updated `roadmap` and `metadata.update_type` set to `"modification"`.

#### C. Verify Available Providers

1. With the service running, call:

```bash
curl http://localhost:8003/api/v1/providers
```

2. Confirm that the response lists:
   - `current_provider` (based on `AI_PROVIDER`)
   - `available_providers` (from the provider factory)

## MCP Server (Model Context Protocol)

The service also provides an MCP server that exposes roadmap generation and update functionality as MCP tools. This allows AI assistants and other MCP-compatible clients to interact with the roadmap service.

### Running the MCP Server

The MCP server runs independently from the FastAPI service and uses stdio transport:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run the MCP server
python src/mcp_server.py
```

The MCP server uses the same configuration (`.env` file) as the FastAPI service.

### Available MCP Tools

#### 1. `generate_roadmap`

Generates a personalized learning roadmap based on user goals and skills.

**Parameters:**
- `user_goal` (str): Target career goal (e.g., 'Full Stack Developer', 'Data Scientist')
- `user_skills` (list): List of skill assessments, each with:
  - `skill` (str): Name of the skill
  - `score` (int): Skill score from 1-10
  - `level` (str): Skill level ('beginner', 'intermediate', or 'advanced')
- `experience_level` (str, optional): Overall experience level (default: 'beginner')
- `preferences` (dict, optional): Learning preferences dictionary
- `user_id` (str, optional): User identifier (default: 'mcp-user')

**Returns:**
Dictionary containing:
- `success` (bool): Whether generation was successful
- `roadmap` (dict): Generated roadmap object
- `metadata` (dict): Generation metadata (time, provider, model, etc.)

**Example:**
```json
{
  "user_goal": "Full Stack Developer",
  "user_skills": [
    {"skill": "javascript", "score": 6, "level": "intermediate"},
    {"skill": "python", "score": 3, "level": "beginner"}
  ],
  "experience_level": "beginner"
}
```

#### 2. `update_roadmap`

Updates an existing roadmap based on user modifications.

**Parameters:**
- `roadmap_id` (str): Unique identifier for the roadmap to update
- `user_prompt` (str): User's prompt describing how to modify the roadmap
  (e.g., 'Add more Python modules', 'Reduce timeline by 2 weeks')
- `existing_roadmap` (dict, optional): Existing roadmap dictionary. If not provided,
  the roadmap will be retrieved by ID (if database is configured)
- `user_id` (str, optional): User identifier (default: 'mcp-user')

**Returns:**
Dictionary containing:
- `success` (bool): Whether update was successful
- `roadmap` (dict): Updated roadmap object
- `metadata` (dict): Update metadata (time, provider, model, etc.)

**Example:**
```json
{
  "roadmap_id": "roadmap-abc123",
  "user_prompt": "Add more Python-focused modules and reduce timeline by 2 weeks",
  "existing_roadmap": {...}  // Full roadmap object from previous generation
}
```

### MCP Client Configuration

To use the MCP server with an MCP client (e.g., Claude Desktop, Cursor), add it to your MCP configuration:

**Example configuration for Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "pathfinder": {
      "command": "python",
      "args": ["/path/to/pathfinder/src/mcp_server.py"],
      "env": {
        "GOOGLE_API_KEY": "your-google-api-key",
        "AI_PROVIDER": "google"
      }
    }
  }
}
```

**Example configuration for Cursor** (in Cursor settings):
```json
{
  "mcp": {
    "servers": {
      "pathfinder": {
        "command": "python",
        "args": ["/absolute/path/to/pathfinder/src/mcp_server.py"]
      }
    }
  }
}
```

### Testing the MCP Server

You can test the MCP server using the MCP Inspector or any MCP-compatible client:

```bash
# Install MCP Inspector (if available)
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python src/mcp_server.py
```

### Notes

- The MCP server and FastAPI service can run simultaneously (they use different processes)
- Both services share the same configuration and service layer
- The MCP server uses stdio transport (standard input/output)
- Error handling is built-in and returns MCP-compatible error responses

## Development

### Project Structure

```
ai-roadmap-service/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── mcp_server.py        # MCP server entry point
│   ├── config/
│   │   └── settings.py      # Configuration management
│   ├── models/
│   │   └── roadmap.py       # Pydantic data models
│   ├── api/
│   │   ├── roadmap_routes.py # Roadmap generation endpoints
│   │   └── health_routes.py  # Health check endpoints
│   ├── services/
│   │   ├── ai_service_factory.py   # AI provider factory
│   │   ├── ai_service_interface.py # Provider-agnostic interface
│   │   ├── providers/              # Concrete AI providers (OpenAI, Google Gemini, etc.)
│   │   └── roadmap_service.py      # Business logic for roadmap workflows
│   └── utils/
│       └── logger.py        # Logging configuration
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

### API Endpoints

#### Generate Roadmap
```http
POST /api/v1/roadmaps/generate
Content-Type: application/json

{
  "user_goal": "Full Stack Developer",
  "user_skills": [
    {
      "skill": "javascript",
      "score": 6,
      "level": "intermediate"
    },
    {
      "skill": "python", 
      "score": 3,
      "level": "beginner"
    }
  ],
  "experience_level": "beginner",
  "preferences": {
    "learning_style": "hands-on",
    "time_commitment": "10 hours/week"
  }
}
```

Response:
```json
{
  "success": true,
  "roadmap": {
    "id": "roadmap-abc123",
    "user_id": "user-456", 
    "title": "Full Stack Developer Learning Path",
    "career_goal": "Full Stack Developer",
    "estimated_weeks": 16,
    "modules": [
      {
        "id": "module-1",
        "title": "JavaScript Fundamentals",
        "description": "Master modern JavaScript ES6+ features",
        "estimated_hours": 40,
        "skills_taught": ["javascript", "es6", "async-programming"],
        "resources": [
          {
            "title": "JavaScript: The Modern Parts",
            "type": "documentation",
            "url": "https://javascript.info/",
            "duration": "20 hours",
            "difficulty": "beginner"
          }
        ],
        "project": {
          "title": "Interactive Todo App", 
          "description": "Build a dynamic todo application",
          "deliverables": ["CRUD functionality", "Local storage"],
          "estimated_hours": 12
        }
      }
    ]
  },
  "metadata": {
    "generation_time": "2.3s",
    "ai_provider": "google",
    "ai_model": "gemini-pro"
  }
}
```

### Supported Career Goals

- Full Stack Developer
- Data Scientist  
- Cloud Engineer
- DevOps Engineer
- Mobile Developer
- Machine Learning Engineer
- Product Manager
- UX/UI Designer

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_roadmap_generation.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t ai-roadmap-service .

# Run container
docker run -d \
  --name ai-roadmap-service \
  -p 8003:8003 \
  -e AI_PROVIDER=google \
  -e GOOGLE_API_KEY=your-google-api-key \
  ai-roadmap-service
```

### Docker Compose (with other services)

```yaml
version: '3.8'
services:
  ai-service:
    build: .
    ports:
      - "8003:8003"
    environment:
      - AI_PROVIDER=google
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - AUTH_SERVICE_URL=http://auth-service:8001
      - PROFILE_SERVICE_URL=http://profile-service:8002
    depends_on:
      - auth-service
      - profile-service
```

## Monitoring

The service includes built-in monitoring:

- **Health checks**: `/health` and `/ready` endpoints
- **Metrics**: Prometheus metrics on port 9090 (if enabled)
- **Structured logging**: JSON format for easy parsing

## Security

- Input validation using Pydantic models
- Rate limiting (100 requests per hour by default)
- CORS configuration for frontend integration
- No API keys logged or exposed in responses

## Troubleshooting

### Common Issues

1. **Google API Key Not Set**
   ```
   ValueError: API key required for google provider
   ```
   Solution: Set `GOOGLE_API_KEY` in your `.env` file or export it as an environment variable

2. **Module Import Errors**
   ```
   ModuleNotFoundError: No module named 'src'
   ```
   Solution: 
   - Run from project root: `python src/main.py` (path is auto-detected)
   - Or use: `PYTHONPATH=$(pwd) python src/main.py`
   - Or use the `run.sh` script which handles this automatically

3. **Virtual Environment Issues**
   ```
   error: externally-managed-environment
   ```
   Solution: 
   - Install virtualenv: `pip3 install --user --break-system-packages virtualenv`
   - Then create venv: `virtualenv venv`
   - Or install python3-venv: `sudo apt install python3-venv`

4. **Port Already in Use**
   ```
   OSError: [Errno 48] Address already in use
   ```
   Solution: Change port in `.env` file or stop the conflicting process:
   ```bash
   lsof -ti :8003 | xargs kill -9
   ```

5. **Missing Dependencies**
   ```
   ModuleNotFoundError: No module named 'asyncpg'
   ```
   Solution: This is expected if you're not using PostgreSQL. The service works without it. If you need PostgreSQL support, install asyncpg separately (note: asyncpg may not support Python 3.13 yet).

### Logs

Service logs are structured and include:
- Request IDs for tracing
- Performance metrics
- Error details with stack traces
- AI provider usage statistics (Google Gemini by default)

## Integration

This service integrates with:

- **Auth Service** (port 8001): User authentication (optional)
- **Profile Service** (port 8002): User skill data (optional)
- **Frontend** (port 3000): Web interface (optional)
- **Google Gemini API**: Roadmap generation (default)
- **OpenAI API**: Roadmap generation (optional, if configured)

## Performance

- **Target Response Time**: < 5 seconds for roadmap generation
- **Caching**: Redis-based caching for repeated requests
- **Rate Limiting**: Prevents API abuse
- **Async Processing**: Non-blocking I/O operations

---

## Environment Variables Reference

See `.env.example` for a complete list of available environment variables. Key variables:

- **Required:**
  - `GOOGLE_API_KEY`: Your Google Gemini API key
  
- **Optional:**
  - `AI_PROVIDER`: Provider to use (default: `google`)
  - `GOOGLE_MODEL`: Model to use (default: `gemini-pro`)
  - `PORT`: Server port (default: `8003`)
  - `ENVIRONMENT`: Environment mode (default: `development`)
  - `DATABASE_URL`: Database connection string (default: SQLite)
  - `REDIS_URL`: Redis connection string (optional)

## Current Status

✅ **Fully Working:**
- Google Gemini integration
- Roadmap generation
- Roadmap updates
- Health checks
- API documentation

⚠️ **Optional/Partial:**
- OpenAI support (requires `openai` package)
- PostgreSQL/Supabase persistence (requires `asyncpg` package, may not work with Python 3.13)
- Redis caching

❌ **Not Currently Supported:**
- Anthropic Claude
- Ollama
- Hugging Face

---

**Ready to use!** The service is fully functional with Google Gemini. Just set your `GOOGLE_API_KEY` and run!