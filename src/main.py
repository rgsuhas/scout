"""
AI Roadmap Service - Main Application Entry Point

This service generates personalized learning roadmaps using OpenAI API
based on user goals, current skills, and experience level.
"""

import sys
from pathlib import Path

# Add project root to Python path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import structlog
import uvicorn

from src.config.settings import settings
from src.api.roadmap_routes import router as roadmap_router
from src.api.health_routes import router as health_router
from src.services.ai_service_factory import create_ai_service_from_settings
from src.services.roadmap_service import RoadmapService
from src.utils.logger import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting AI Roadmap Service", version=settings.service_version)
    
    # Initialize AI service (model-agnostic)
    try:
        ai_service = create_ai_service_from_settings(settings)
        
        # Initialize business logic service layer with AI service dependency
        roadmap_service = RoadmapService(ai_service)
        app.state.roadmap_service = roadmap_service
        app.state.ai_service = ai_service  # Keep for backward compatibility with health routes
        
        # Get model info for logging
        model_info = await ai_service.get_model_info()
        logger.info("Services initialized successfully", 
                   provider=model_info.get("provider"),
                   model=model_info.get("model"),
                   service_layer="RoadmapService")
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise
    
    yield
    
    logger.info("Shutting down AI Roadmap Service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Goal-Based LMS - AI Roadmap Service",
        description="Generates personalized learning roadmaps using AI",
        version=settings.service_version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Frontend development
            "http://localhost:3001",  # Alternative frontend port
            settings.frontend_url,    # Configured frontend URL
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*"] if settings.environment == "development" else ["yourdomain.com"]
    )

    # Include routers
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(roadmap_router, prefix="/api/v1", tags=["Roadmaps"])

    # Mount static files
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Root endpoint - serve frontend
    @app.get("/")
    async def root():
        static_file = Path(__file__).parent.parent / "static" / "index.html"
        if static_file.exists():
            return FileResponse(static_file)
        return {
            "service": "AI Roadmap Service",
            "version": settings.service_version,
            "status": "running",
            "docs": "/docs",
            "health": "/health"
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )