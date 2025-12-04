"""
API routes for roadmap generation and management

Layer 1: Presentation/API Layer
This layer handles HTTP requests/responses and delegates business logic to the service layer.
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from typing import Dict, Any
import structlog

from ..models.roadmap import RoadmapRequest, RoadmapResponse, RoadmapUpdateRequest
from ..services.roadmap_service import RoadmapService
from ..services.ai_service_interface import AIServiceError

logger = structlog.get_logger()
router = APIRouter()


@router.post("/roadmaps/generate", response_model=RoadmapResponse)
async def generate_roadmap(
    request: RoadmapRequest, 
    fastapi_request: Request,
    background_tasks: BackgroundTasks
) -> RoadmapResponse:
    """
    Generate a personalized learning roadmap based on user goals and skills
    
    Args:
        request: RoadmapRequest containing user goals, skills, and preferences
        fastapi_request: FastAPI request object to access app state
        background_tasks: Background tasks for async operations
        
    Returns:
        RoadmapResponse: Generated roadmap with metadata
        
    Raises:
        HTTPException: If roadmap generation fails
    """
    # Extract user ID (in real implementation, this would come from JWT token)
    user_id = "demo-user-123"  # TODO: Extract from authentication
    
    try:
        # Get roadmap service from app state
        roadmap_service: RoadmapService = getattr(fastapi_request.app.state, 'roadmap_service', None)
        
        if not roadmap_service:
            raise HTTPException(
                status_code=503,
                detail="Roadmap service not available"
            )
        
        # Delegate to business logic layer
        response = await roadmap_service.generate_roadmap(request, user_id)
        
        # Add background task to log usage metrics
        metadata = response.metadata or {}
        generation_time_str = metadata.get("generation_time", "0s")
        # Extract numeric value from string like "2.3s"
        try:
            generation_time = float(generation_time_str.replace("s", "").strip())
        except (ValueError, AttributeError):
            generation_time = 0.0
        
        background_tasks.add_task(
            roadmap_service.log_generation_metrics,
            user_id,
            request.user_goal,
            generation_time,
            metadata.get("ai_provider", "unknown")
        )
        
        return response
        
    except AIServiceError as e:
        logger.error("AI service error during roadmap generation", 
                    user_id=user_id,
                    error=e.message,
                    provider=e.provider,
                    error_code=e.error_code)
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to generate roadmap",
                "error": e.message,
                "provider": e.provider,
                "error_code": e.error_code
            }
        )
    
    except Exception as e:
        logger.error("Unexpected error during roadmap generation", 
                    user_id=user_id,
                    error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error",
                "error": "An unexpected error occurred during roadmap generation"
            }
        )


@router.get("/roadmaps/{roadmap_id}")
async def get_roadmap(
    roadmap_id: str,
    fastapi_request: Request
) -> Dict[str, Any]:
    """
    Get an existing roadmap by ID
    
    Args:
        roadmap_id: Unique roadmap identifier
        fastapi_request: FastAPI request object to access app state
        
    Returns:
        Dict containing roadmap data
        
    Note:
        This is a placeholder implementation. In production, you would
        fetch from a database.
    """
    # Get roadmap service from app state
    roadmap_service: RoadmapService = getattr(fastapi_request.app.state, 'roadmap_service', None)
    
    if not roadmap_service:
        raise HTTPException(
            status_code=503,
            detail="Roadmap service not available"
        )
    
    # Delegate to business logic layer
    return await roadmap_service.get_roadmap(roadmap_id)


@router.put("/roadmaps/{roadmap_id}", response_model=RoadmapResponse)
async def update_roadmap(
    roadmap_id: str,
    update_request: RoadmapUpdateRequest,
    fastapi_request: Request,
    background_tasks: BackgroundTasks
) -> RoadmapResponse:
    """
    Update an existing roadmap based on user modifications
    
    This endpoint allows users to modify an existing roadmap by providing
    a prompt describing the desired changes. The AI will generate a new
    version of the roadmap incorporating the modifications.
    
    Args:
        roadmap_id: Unique identifier for the roadmap to update
        update_request: RoadmapUpdateRequest containing user prompt and optional existing roadmap
        fastapi_request: FastAPI request object to access app state
        background_tasks: Background tasks for async operations
        
    Returns:
        RoadmapResponse: Updated roadmap with metadata
        
    Raises:
        HTTPException: If roadmap update fails
    """
    # Extract user ID (in real implementation, this would come from JWT token)
    user_id = "demo-user-123"  # TODO: Extract from authentication
    
    try:
        # Get roadmap service from app state
        roadmap_service: RoadmapService = getattr(fastapi_request.app.state, 'roadmap_service', None)
        
        if not roadmap_service:
            raise HTTPException(
                status_code=503,
                detail="Roadmap service not available"
            )
        
        # Delegate to business logic layer
        response = await roadmap_service.update_roadmap(
            roadmap_id=roadmap_id,
            update_request=update_request,
            user_id=user_id
        )
        
        # Add background task to log usage metrics
        metadata = response.metadata or {}
        update_time_str = metadata.get("generation_time", "0s")
        try:
            update_time = float(update_time_str.replace("s", "").strip())
        except (ValueError, AttributeError):
            update_time = 0.0
        
        background_tasks.add_task(
            roadmap_service.log_generation_metrics,
            user_id,
            f"Update: {update_request.user_prompt[:50]}",  # Truncated prompt
            update_time,
            metadata.get("ai_provider", "unknown")
        )
        
        return response
        
    except ValueError as e:
        logger.error("Validation error during roadmap update", 
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    error=str(e))
        
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid request",
                "error": str(e)
            }
        )
        
    except AIServiceError as e:
        logger.error("AI service error during roadmap update", 
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    error=e.message,
                    provider=e.provider,
                    error_code=e.error_code)
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to update roadmap",
                "error": e.message,
                "provider": e.provider,
                "error_code": e.error_code
            }
        )
    
    except Exception as e:
        logger.error("Unexpected error during roadmap update", 
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error",
                "error": "An unexpected error occurred during roadmap update"
            }
        )


@router.put("/roadmaps/{roadmap_id}/progress")
async def update_roadmap_progress(
    roadmap_id: str,
    progress_data: Dict[str, Any],
    fastapi_request: Request
) -> Dict[str, Any]:
    """
    Update progress on a roadmap
    
    Args:
        roadmap_id: Unique roadmap identifier
        progress_data: Progress update data
        fastapi_request: FastAPI request object to access app state
        
    Returns:
        Dict containing update status
        
    Note:
        This is a placeholder implementation. In production, you would
        update the database and possibly trigger roadmap adaptations.
    """
    # Get roadmap service from app state
    roadmap_service: RoadmapService = getattr(fastapi_request.app.state, 'roadmap_service', None)
    
    if not roadmap_service:
        raise HTTPException(
            status_code=503,
            detail="Roadmap service not available"
        )
    
    # Delegate to business logic layer
    return await roadmap_service.update_roadmap_progress(roadmap_id, progress_data)


@router.get("/providers")
async def get_available_providers(request: Request) -> Dict[str, Any]:
    """
    Get information about available AI providers
    
    Args:
        request: FastAPI request object to access app state
        
    Returns:
        Dict containing provider information
    """
    try:
        # Get roadmap service from app state
        roadmap_service: RoadmapService = getattr(request.app.state, 'roadmap_service', None)
        
        if not roadmap_service:
            return {
                "message": "Roadmap service not initialized",
                "current_provider": None,
                "available_providers": ["openai"]  # Static fallback
            }
        
        # Delegate to business logic layer
        return await roadmap_service.get_provider_info()
        
    except Exception as e:
        logger.error("Failed to get provider info", error=str(e))
        return {
            "error": "Failed to get provider information",
            "available_providers": ["openai"]
        }

