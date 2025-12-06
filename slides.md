# Scout: AI-Powered Learning Roadmap Service

## 1: Project Overview

**Scout: AI-Powered Learning Path Generator**

Scout is an intelligent microservice that generates personalized learning roadmaps using advanced AI models. Built as part of a Goal-Based Learning Management System (LMS), Scout transforms user goals, current skills, and learning preferences into structured, actionable learning paths.

**Key Highlights:**
- **AI-Driven Personalization**: Leverages Google Gemini AI to create customized learning roadmaps
- **Multi-Provider Support**: Flexible architecture supporting Google Gemini (primary) and OpenAI (optional)
- **RESTful API**: FastAPI-based service with comprehensive endpoints for roadmap generation and management
- **Production-Ready**: Dockerized, deployable to cloud platforms like Render, with health checks and monitoring

**Problem Solved**: Traditional learning paths are one-size-fits-all. Scout creates personalized roadmaps that adapt to each learner's unique starting point, goals, and preferences.

---

## 2: Key Features & Capabilities

**Core Functionality:**

**1. Intelligent Roadmap Generation**
   - Analyzes user goals (any career path: Full Stack Developer, Data Scientist, Cloud Engineer, etc.)
   - Assesses current skill levels and experience
   - Generates 6-module structured learning paths with estimated timelines
   - Includes learning resources, projects, and assessments for each module

**2. Dynamic Roadmap Updates**
   - Users can modify existing roadmaps with natural language prompts
   - AI adapts roadmaps based on feedback (e.g., "Add more Python modules", "Reduce timeline by 2 weeks")
   - Preserves roadmap structure while incorporating changes

**3. MCP Server Integration**
   - Model Context Protocol (MCP) support for AI assistant integration
   - Enables AI assistants like Claude Desktop and Cursor to generate roadmaps directly
   - Seamless integration with modern AI tooling ecosystems

**4. Enterprise Features**
   - Health check endpoints for monitoring
   - Structured logging with request tracing
   - CORS configuration for frontend integration
   - Optional PostgreSQL/Supabase persistence

---

## 3: Technical Architecture

**Architecture Overview:**

**Layered Design:**
- **Presentation Layer**: FastAPI routes handling HTTP requests/responses
- **Business Logic Layer**: RoadmapService orchestrating workflows and business rules
- **AI Provider Layer**: Provider-agnostic interface supporting multiple AI services
- **Data Layer**: Pydantic models ensuring type safety and validation

**Technology Stack:**
- **Framework**: FastAPI (async Python web framework)
- **AI Provider**: Google Gemini API (primary), OpenAI (optional)
- **Data Validation**: Pydantic models with comprehensive validation
- **Logging**: Structured logging with structlog
- **Deployment**: Docker containers, Render.com compatible

**Key Design Patterns:**
- **Factory Pattern**: AI service factory for provider abstraction
- **Dependency Injection**: Services injected into routes via app state
- **Interface Segregation**: Clean separation between API, business logic, and AI providers
- **Error Handling**: Comprehensive error handling with custom exception types

**Scalability Features:**
- Async/await for non-blocking I/O
- Background tasks for metrics logging
- Optional database persistence for roadmap storage
- Rate limiting and CORS protection

---

## 4: Use Cases & Impact

**Target Use Cases:**

**1. Individual Learners**
   - Career changers seeking structured paths to new roles
   - Students planning their learning journey
   - Professionals upskilling in new technologies
   - Anyone with a specific career goal needing guidance

**2. Educational Platforms**
   - LMS integration for personalized course recommendations
   - Bootcamp programs creating custom curricula
   - Corporate training platforms tailoring employee development
   - EdTech platforms offering AI-powered learning guidance

**3. AI Assistant Integration**
   - AI assistants helping users create learning plans
   - Chatbots providing educational guidance
   - Developer tools suggesting skill development paths

**Impact & Benefits:**

**For Learners:**
- Personalized learning paths tailored to their starting point
- Clear progression from beginner to advanced
- Actionable projects and resources for hands-on learning
- Time estimates for realistic planning

**For Organizations:**
- Scalable AI-powered content generation
- Reduced manual curriculum design effort
- Consistent, high-quality learning path creation
- Integration-ready API for existing platforms

**Technical Impact:**
- Microservice architecture enabling independent scaling
- Provider-agnostic design allowing AI model flexibility
- Production-ready deployment with monitoring and health checks
- Open API design supporting diverse integrations

---

**Next Steps:**
- Deploy to production environment
- Integrate with frontend applications
- Expand AI provider support (Anthropic, Ollama)
- Add progress tracking and adaptive learning features

