"""
Health check routes for the AI roadmap service

Layer 1: Presentation/API Layer
These routes handle health checks and service information.
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns:
        Dict containing service health status
    """
    return {
        "status": "healthy",
        "service": "ai-roadmap-service",
        "version": "1.0.0",
        "timestamp": "2025-10-18T07:30:00Z"
    }


@router.get("/ready")
async def readiness_check(request: Request) -> Dict[str, Any]:
    """
    Readiness check endpoint - verifies all dependencies are available
    
    Args:
        request: FastAPI request object to access app state
        
    Returns:
        Dict containing readiness status
        
    Raises:
        HTTPException: If service is not ready
    """
    try:
        # Check if roadmap service is available (business logic layer)
        roadmap_service = getattr(request.app.state, 'roadmap_service', None)
        
        if not roadmap_service:
            raise HTTPException(
                status_code=503,
                detail="Roadmap service not initialized"
            )
        
        # Check if AI service is available and healthy (provider layer)
        ai_service = getattr(request.app.state, 'ai_service', None)
        
        if not ai_service:
            raise HTTPException(
                status_code=503,
                detail="AI service not initialized"
            )
        
        # Perform AI service health check
        ai_health = await ai_service.health_check()
        
        if ai_health.get("status") != "healthy":
            raise HTTPException(
                status_code=503,
                detail=f"AI service unhealthy: {ai_health.get('error', 'Unknown error')}"
            )
        
        # Get model info
        model_info = await ai_service.get_model_info()
        
        return {
            "status": "ready",
            "service": "ai-roadmap-service",
            "timestamp": "2025-10-18T07:30:00Z",
            "dependencies": {
                "roadmap_service": {
                    "status": "initialized"
                },
                "ai_service": {
                    "status": "healthy",
                    "provider": model_info.get("provider"),
                    "model": model_info.get("model")
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/info")
async def service_info(request: Request) -> Dict[str, Any]:
    """
    Get detailed service information
    
    Args:
        request: FastAPI request object to access app state
        
    Returns:
        Dict containing service information
    """
    try:
        ai_service = getattr(request.app.state, 'ai_service', None)
        
        if not ai_service:
            return {
                "service": "ai-roadmap-service",
                "version": "1.0.0",
                "status": "ai_service_not_initialized"
            }
        
        # Get model info
        model_info = await ai_service.get_model_info()
        
        return {
            "service": "ai-roadmap-service",
            "version": "1.0.0",
            "ai_provider": {
                "provider": model_info.get("provider"),
                "model": model_info.get("model"),
                "capabilities": model_info.get("capabilities", []),
                "supported_languages": model_info.get("supported_languages", [])
            },
            "endpoints": {
                "generate_roadmap": "/api/v1/roadmaps/generate",
                "health": "/health",
                "readiness": "/health/ready",
                "info": "/health/info"
            },
            "supported_career_goals": [
                "Full Stack Developer",
                "Data Scientist",
                "Cloud Engineer", 
                "DevOps Engineer",
                "Mobile Developer",
                "Machine Learning Engineer",
                "Product Manager",
                "UX/UI Designer"
            ]
        }
    
    except Exception as e:
        logger.error("Failed to get service info", error=str(e))
        return {
            "service": "ai-roadmap-service",
            "version": "1.0.0",
            "status": "error",
            "error": str(e)
        }