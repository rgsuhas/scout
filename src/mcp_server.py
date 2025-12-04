"""
MCP Server for Pathfinder Roadmap Service

This module provides a Model Context Protocol (MCP) server that exposes
roadmap generation and update functionality as MCP tools.
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog

# Determine project root and add to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables from .env file BEFORE importing settings
from dotenv import load_dotenv
import os

# Load .env file from project root
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory as fallback
    load_dotenv()

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback for older MCP SDK versions
    try:
        from mcp import FastMCP
    except ImportError:
        raise ImportError(
            "MCP package not found. Install it with: pip install mcp"
        )

from src.config.settings import settings
from src.services.ai_service_factory import create_ai_service_from_settings
from src.services.roadmap_service import RoadmapService
from src.services.ai_service_interface import AIServiceError
from src.models.roadmap import (
    RoadmapRequest,
    RoadmapUpdateRequest,
    SkillAssessment,
    DifficultyLevel,
    Roadmap,
)
from src.utils.logger import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

# Initialize MCP server
mcp = FastMCP("Pathfinder Roadmap Service")

# Global service instance (initialized in main)
roadmap_service: Optional[RoadmapService] = None


async def initialize_services() -> RoadmapService:
    """
    Initialize the roadmap service with AI service dependency.
    This is called once at startup.
    
    Returns:
        RoadmapService: Initialized roadmap service instance
    """
    global roadmap_service
    
    if roadmap_service is not None:
        return roadmap_service
    
    logger.info("Initializing MCP server services", version=settings.service_version)
    
    try:
        # Create AI service from settings
        ai_service = create_ai_service_from_settings(settings)
        
        # Initialize business logic service layer
        roadmap_service = RoadmapService(ai_service)
        
        # Get model info for logging
        model_info = await ai_service.get_model_info()
        logger.info(
            "MCP services initialized successfully",
            provider=model_info.get("provider"),
            model=model_info.get("model"),
        )
        
        return roadmap_service
        
    except Exception as e:
        logger.error("Failed to initialize MCP services", error=str(e))
        raise


@mcp.tool()
async def generate_roadmap(
    user_goal: str,
    user_skills: List[Dict[str, Any]],
    experience_level: str = "beginner",
    preferences: Optional[Dict[str, Any]] = None,
    user_id: str = "mcp-user",
) -> Dict[str, Any]:
    """
    Generate a personalized learning roadmap based on user goals and skills.
    
    Args:
        user_goal: Target career goal (e.g., 'Full Stack Developer', 'Data Scientist')
        user_skills: List of skill assessments, each with 'skill' (str), 'score' (int 1-10), and 'level' (str: beginner/intermediate/advanced)
        experience_level: Overall experience level (beginner, intermediate, or advanced)
        preferences: Optional learning preferences dictionary
        user_id: User identifier (defaults to 'mcp-user')
    
    Returns:
        Dictionary containing the generated roadmap with success status and metadata
    
    Example:
        {
            "user_goal": "Full Stack Developer",
            "user_skills": [
                {"skill": "javascript", "score": 6, "level": "intermediate"},
                {"skill": "python", "score": 3, "level": "beginner"}
            ],
            "experience_level": "beginner"
        }
    """
    global roadmap_service
    
    if roadmap_service is None:
        # Initialize services if not already done (await since we're in async context)
        roadmap_service = await initialize_services()
    
    try:
        # Convert user_skills dicts to SkillAssessment objects
        skill_assessments = []
        for skill_dict in user_skills:
            skill_assessments.append(
                SkillAssessment(
                    skill=skill_dict["skill"],
                    score=skill_dict["score"],
                    level=DifficultyLevel(skill_dict["level"].lower()),
                )
            )
        
        # Create RoadmapRequest
        request = RoadmapRequest(
            user_goal=user_goal,
            user_skills=skill_assessments,
            experience_level=DifficultyLevel(experience_level.lower()),
            preferences=preferences or {},
        )
        
        # Generate roadmap (async call)
        response = await roadmap_service.generate_roadmap(request, user_id)
        
        # Convert response to dict for MCP
        return {
            "success": response.success,
            "roadmap": response.roadmap.model_dump(mode="json"),
            "metadata": response.metadata,
        }
        
    except AIServiceError as e:
        logger.error(
            "AI service error during roadmap generation",
            error=e.message,
            provider=e.provider,
            error_code=e.error_code,
        )
        return {
            "success": False,
            "error": e.message,
            "provider": e.provider,
            "error_code": e.error_code,
        }
    except ValueError as e:
        logger.error("Validation error during roadmap generation", error=str(e))
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
            "error_code": "VALIDATION_ERROR",
        }
    except Exception as e:
        logger.error("Unexpected error during roadmap generation", error=str(e))
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
        }


@mcp.tool()
async def update_roadmap(
    roadmap_id: str,
    user_prompt: str,
    existing_roadmap: Optional[Dict[str, Any]] = None,
    user_id: str = "mcp-user",
) -> Dict[str, Any]:
    """
    Update an existing roadmap based on user modifications.
    
    Args:
        roadmap_id: Unique identifier for the roadmap to update
        user_prompt: User's prompt describing how to modify the roadmap
                     (e.g., 'Add more Python modules', 'Reduce timeline by 2 weeks')
        existing_roadmap: Optional existing roadmap dictionary. If not provided,
                         the roadmap will be retrieved by ID (if database is configured)
        user_id: User identifier (defaults to 'mcp-user')
    
    Returns:
        Dictionary containing the updated roadmap with success status and metadata
    
    Example:
        {
            "roadmap_id": "roadmap-abc123",
            "user_prompt": "Add more Python-focused modules and reduce timeline by 2 weeks",
            "existing_roadmap": {...}  # Full roadmap object from previous generation
        }
    """
    global roadmap_service
    
    if roadmap_service is None:
        # Initialize services if not already done (await since we're in async context)
        roadmap_service = await initialize_services()
    
    try:
        # Convert existing_roadmap dict to Roadmap object if provided
        roadmap_obj = None
        if existing_roadmap:
            try:
                roadmap_obj = Roadmap(**existing_roadmap)
            except Exception as e:
                logger.warning(
                    "Failed to parse existing_roadmap, will try to fetch by ID",
                    error=str(e),
                )
        
        # Create RoadmapUpdateRequest
        update_request = RoadmapUpdateRequest(
            user_prompt=user_prompt, existing_roadmap=roadmap_obj
        )
        
        # Update roadmap (async call)
        response = await roadmap_service.update_roadmap(roadmap_id, update_request, user_id)
        
        # Convert response to dict for MCP
        return {
            "success": response.success,
            "roadmap": response.roadmap.model_dump(mode="json"),
            "metadata": response.metadata,
        }
        
    except AIServiceError as e:
        logger.error(
            "AI service error during roadmap update",
            roadmap_id=roadmap_id,
            error=e.message,
            provider=e.provider,
            error_code=e.error_code,
        )
        return {
            "success": False,
            "error": e.message,
            "provider": e.provider,
            "error_code": e.error_code,
        }
    except ValueError as e:
        logger.error(
            "Validation error during roadmap update",
            roadmap_id=roadmap_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
            "error_code": "VALIDATION_ERROR",
        }
    except Exception as e:
        logger.error(
            "Unexpected error during roadmap update",
            roadmap_id=roadmap_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
        }


def main():
    """Main entry point for MCP server"""
    try:
        # Initialize services (run async initialization)
        # Use asyncio.run() for Python 3.7+ (handles event loop creation properly)
        asyncio.run(initialize_services())
        
        logger.info("MCP server starting", provider=settings.ai_provider)
        
        # Run MCP server (stdio transport)
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error("MCP server error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

