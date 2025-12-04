"""
Business Logic Service Layer for Roadmap Generation

This service layer orchestrates the roadmap generation workflow,
handles business rules, and coordinates between different services.
It abstracts business logic from both API and provider layers.
"""

import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import structlog

# Optional import for PostgreSQL support
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None  # type: ignore

from src.config.settings import settings

from ..models.roadmap import RoadmapRequest, RoadmapResponse, Roadmap, RoadmapUpdateRequest
from .ai_service_interface import AIServiceInterface, AIServiceError

logger = structlog.get_logger()


class RoadmapService:
    """Business logic service for roadmap operations"""
    
    def __init__(self, ai_service: AIServiceInterface):
        """
        Initialize RoadmapService with AI service dependency
        
        Args:
            ai_service: AI service instance implementing AIServiceInterface
        """
        self.ai_service = ai_service
        self._db_pool: Optional[Any] = None  # Optional[asyncpg.Pool] when asyncpg is available
        self._database_url: Optional[str] = settings.database_url
        logger.info("RoadmapService initialized", 
                   provider=ai_service.get_provider_name())

    async def _get_db_pool(self) -> Optional[Any]:  # Optional[asyncpg.Pool] when asyncpg is available
        """
        Lazily initialize and return an asyncpg connection pool if configured for Postgres.
        Returns None if database_url is not a Postgres URL or asyncpg is not installed.
        """
        if not ASYNCPG_AVAILABLE:
            logger.debug("asyncpg not available, skipping Postgres connection")
            return None
            
        if not self._database_url or not isinstance(self._database_url, str):
            return None
        if not self._database_url.startswith("postgres"):
            # Likely using default SQLite URL or not configured for Supabase
            return None

        if self._db_pool is None:
            logger.info("Initializing Postgres connection pool for roadmaps",
                        database_url_hint=self._database_url.split("@")[-1] if "@" in self._database_url else "configured")
            if asyncpg:
                self._db_pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=5)
        return self._db_pool

    async def _save_roadmap_to_db(self, roadmap: Roadmap, user_id: str) -> None:
        """
        Persist roadmap to Postgres (Supabase) if configured.
        Stores the full roadmap as JSON in public.roadmaps. Safe no-op if DB is not Postgres.
        """
        pool = await self._get_db_pool()
        if pool is None:
            # DB not configured; skip persistence
            logger.debug("Skipping roadmap persistence; database_url not Postgres")
            return

        roadmap_json = roadmap.model_dump(mode="json")
        query = """
        insert into public.roadmaps (
          id,
          user_id,
          source_service,
          title,
          career_goal,
          estimated_weeks,
          difficulty_progression,
          roadmap_json,
          created_at,
          updated_at
        )
        values ($1, $2, 'ai-roadmap-service', $3, $4, $5, $6, $7, now(), now())
        on conflict (id) do update set
          user_id = excluded.user_id,
          title = excluded.title,
          career_goal = excluded.career_goal,
          estimated_weeks = excluded.estimated_weeks,
          difficulty_progression = excluded.difficulty_progression,
          roadmap_json = excluded.roadmap_json,
          updated_at = now();
        """

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    query,
                    roadmap.id,
                    user_id,
                    roadmap.title,
                    roadmap.career_goal,
                    getattr(roadmap, "estimated_weeks", None),
                    getattr(roadmap, "difficulty_progression", None),
                    json.dumps(roadmap_json),
                )
            logger.info("Roadmap persisted to database", roadmap_id=roadmap.id, user_id=user_id)
        except Exception as e:
            # Log but don't break API flow
            logger.error("Failed to persist roadmap to database",
                         roadmap_id=roadmap.id,
                         user_id=user_id,
                         error=str(e))
    
    async def generate_roadmap(
        self, 
        request: RoadmapRequest, 
        user_id: str
    ) -> RoadmapResponse:
        """
        Generate a personalized learning roadmap
        
        This method orchestrates the roadmap generation workflow:
        1. Validates request (business rules)
        2. Calls AI service to generate roadmap
        3. Generates metadata (timing, provider info, etc.)
        4. Logs business events
        5. Returns structured response
        
        Args:
            request: RoadmapRequest containing user goals, skills, and preferences
            user_id: Unique identifier for the user
            
        Returns:
            RoadmapResponse: Generated roadmap with metadata
            
        Raises:
            AIServiceError: If AI service fails to generate roadmap
            ValueError: If request validation fails
        """
        start_time = time.time()
        
        try:
            # Business-level logging
            logger.info("Starting roadmap generation", 
                       user_id=user_id,
                       goal=request.user_goal,
                       experience_level=request.experience_level,
                       skills_count=len(request.user_skills))
            
            # Generate roadmap using AI service
            roadmap = await self.ai_service.generate_roadmap(request, user_id)
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Get model info for metadata
            model_info = await self.ai_service.get_model_info()

            # Persist roadmap if DB is configured
            await self._save_roadmap_to_db(roadmap, user_id)
            
            # Log successful generation
            logger.info("Roadmap generated successfully", 
                       user_id=user_id,
                       roadmap_id=roadmap.id,
                       generation_time_seconds=round(generation_time, 2),
                       provider=model_info.get("provider"),
                       model=model_info.get("model"))
            
            # Generate metadata (business logic)
            metadata = self._generate_metadata(
                roadmap=roadmap,
                generation_time=generation_time,
                model_info=model_info
            )
            
            # Create response
            response = RoadmapResponse(
                success=True,
                roadmap=roadmap,
                metadata=metadata
            )
            
            return response
            
        except AIServiceError as e:
            # Re-raise AI service errors (business layer doesn't handle them)
            logger.error("AI service error during roadmap generation", 
                        user_id=user_id,
                        error=e.message,
                        provider=e.provider,
                        error_code=e.error_code)
            raise
            
        except Exception as e:
            # Wrap unexpected errors
            logger.error("Unexpected error during roadmap generation", 
                        user_id=user_id,
                        error=str(e))
            raise AIServiceError(
                message=f"Unexpected error during roadmap generation: {str(e)}",
                provider=self.ai_service.get_provider_name(),
                error_code="UNEXPECTED_ERROR",
                original_error=e
            )
    
    async def update_roadmap(
        self,
        roadmap_id: str,
        update_request: RoadmapUpdateRequest,
        user_id: str
    ) -> RoadmapResponse:
        """
        Update an existing roadmap based on user modifications
        
        This method orchestrates the roadmap update workflow:
        1. Gets existing roadmap (or uses provided one)
        2. Uses AI to modify roadmap based on user prompt
        3. Generates metadata
        4. Returns updated roadmap
        
        Args:
            roadmap_id: Unique identifier for the roadmap to update
            update_request: RoadmapUpdateRequest containing user prompt and optional existing roadmap
            user_id: Unique identifier for the user
            
        Returns:
            RoadmapResponse: Updated roadmap with metadata
            
        Raises:
            AIServiceError: If AI service fails to update roadmap
            ValueError: If roadmap not found or invalid
        """
        start_time = time.time()
        
        try:
            # Get existing roadmap
            existing_roadmap = update_request.existing_roadmap
            
            if not existing_roadmap:
                # TODO: In production, fetch from database using roadmap_id
                logger.warning("Roadmap not found in request, database lookup not implemented", 
                             roadmap_id=roadmap_id)
                raise ValueError(f"Roadmap {roadmap_id} not found. Please provide existing_roadmap in request.")
            
            # Business-level logging
            logger.info("Starting roadmap update", 
                       user_id=user_id,
                       roadmap_id=roadmap_id,
                       user_prompt=update_request.user_prompt[:100])  # Log first 100 chars
            
            # Update roadmap using AI service
            updated_roadmap = await self.ai_service.update_roadmap(
                existing_roadmap=existing_roadmap,
                user_prompt=update_request.user_prompt,
                user_id=user_id
            )
            
            # Preserve original roadmap ID
            updated_roadmap.id = roadmap_id
            updated_roadmap.user_id = user_id
            # Use timezone-aware datetime
            updated_roadmap.updated_at = datetime.now(timezone.utc)
            
            # Calculate update time
            update_time = time.time() - start_time
            
            # Get model info for metadata
            model_info = await self.ai_service.get_model_info()

            # Persist updated roadmap if DB is configured
            await self._save_roadmap_to_db(updated_roadmap, user_id)
            
            # Log successful update
            logger.info("Roadmap updated successfully", 
                       user_id=user_id,
                       roadmap_id=roadmap_id,
                       update_time_seconds=round(update_time, 2),
                       provider=model_info.get("provider"),
                       model=model_info.get("model"))
            
            # Generate metadata (business logic)
            metadata = self._generate_metadata(
                roadmap=updated_roadmap,
                generation_time=update_time,
                model_info=model_info
            )
            metadata["update_type"] = "modification"
            metadata["modification_prompt"] = update_request.user_prompt[:100]  # Store prompt preview
            
            # Create response
            response = RoadmapResponse(
                success=True,
                roadmap=updated_roadmap,
                metadata=metadata
            )
            
            return response
            
        except AIServiceError as e:
            # Re-raise AI service errors
            logger.error("AI service error during roadmap update", 
                        user_id=user_id,
                        roadmap_id=roadmap_id,
                        error=e.message,
                        provider=e.provider,
                        error_code=e.error_code)
            raise
            
        except Exception as e:
            # Wrap unexpected errors
            logger.error("Unexpected error during roadmap update", 
                        user_id=user_id,
                        roadmap_id=roadmap_id,
                        error=str(e))
            raise AIServiceError(
                message=f"Unexpected error during roadmap update: {str(e)}",
                provider=self.ai_service.get_provider_name(),
                error_code="UNEXPECTED_ERROR",
                original_error=e
            )
    
    async def get_roadmap(self, roadmap_id: str) -> Dict[str, Any]:
        """
        Get an existing roadmap by ID.
        
        If a Postgres (Supabase) database is configured, this will look up the
        roadmap in public.roadmaps and return the stored JSON. Otherwise it
        returns a not-implemented response.
        """
        logger.info("Get roadmap requested", roadmap_id=roadmap_id)

        pool = await self._get_db_pool()
        if pool is None:
            # DB not configured; keep behavior explicit
            logger.warning("Roadmap retrieval requested but database_url is not Postgres",
                           roadmap_id=roadmap_id)
            return {
                "message": "Roadmap retrieval requires Postgres/Supabase database configuration",
                "roadmap_id": roadmap_id,
                "status": "not_configured"
            }

        query = """
        select id,
               user_id,
               title,
               career_goal,
               estimated_weeks,
               difficulty_progression,
               roadmap_json,
               created_at,
               updated_at
          from public.roadmaps
         where id = $1
        """

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, roadmap_id)
        except Exception as e:
            logger.error("Database error while retrieving roadmap",
                         roadmap_id=roadmap_id,
                         error=str(e))
            return {
                "message": "Failed to retrieve roadmap from database",
                "roadmap_id": roadmap_id,
                "status": "error"
            }

        if not row:
            return {
                "message": "Roadmap not found",
                "roadmap_id": roadmap_id,
                "status": "not_found"
            }

        # roadmap_json is stored as text; decode and return
        roadmap_json_str = row["roadmap_json"]
        try:
            roadmap_data = json.loads(roadmap_json_str)
        except Exception:
            # Fallback: return raw field if decoding fails
            roadmap_data = row["roadmap_json"]

        return {
            "roadmap_id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "career_goal": row["career_goal"],
            "estimated_weeks": row["estimated_weeks"],
            "difficulty_progression": row["difficulty_progression"],
            "roadmap": roadmap_data,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "status": "ok"
        }
    
    async def update_roadmap_progress(
        self, 
        roadmap_id: str, 
        progress_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update progress on a roadmap
        
        Args:
            roadmap_id: Unique roadmap identifier
            progress_data: Progress update data
            
        Returns:
            Dict containing update status
            
        Note:
            This is a placeholder implementation. In production, you would
            update the database and possibly trigger roadmap adaptations.
        """
        # TODO: Implement progress tracking and database updates
        logger.info("Update roadmap progress requested", 
                   roadmap_id=roadmap_id,
                   progress_data=progress_data)
        return {
            "message": "Progress update not yet implemented",
            "roadmap_id": roadmap_id,
            "received_data": progress_data,
            "status": "placeholder"
        }
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about available AI providers
        
        Returns:
            Dict containing provider information
        """
        try:
            # Get current model info from AI service
            model_info = await self.ai_service.get_model_info()
            
            return {
                "current_provider": {
                    "name": model_info.get("provider"),
                    "model": model_info.get("model"),
                    "capabilities": model_info.get("capabilities", [])
                },
                "available_providers": [
                    {
                        "name": "openai",
                        "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                        "description": "OpenAI GPT models"
                    },
                    {
                        "name": "anthropic", 
                        "models": ["claude-3-sonnet", "claude-3-opus"],
                        "description": "Anthropic Claude models",
                        "status": "not_implemented"
                    },
                    {
                        "name": "google",
                        "models": ["gemini-pro", "gemini-pro-vision"],
                        "description": "Google Gemini models",
                        "status": "implemented"
                    },
                    {
                        "name": "ollama",
                        "models": ["llama2", "mistral", "codellama"],
                        "description": "Local Ollama models",
                        "status": "not_implemented"
                    }
                ]
            }
            
        except Exception as e:
            logger.error("Failed to get provider info", error=str(e))
            return {
                "error": "Failed to get provider information",
                "available_providers": ["openai"]
            }
    
    async def log_generation_metrics(
        self,
        user_id: str,
        goal: str,
        generation_time: float,
        provider: str
    ) -> None:
        """
        Log generation metrics for analytics
        
        Args:
            user_id: User identifier
            goal: Career goal
            generation_time: Time taken to generate roadmap
            provider: AI provider used
        """
        try:
            # In production, this would send to analytics service
            logger.info("Roadmap generation metrics", 
                       user_id=user_id,
                       career_goal=goal,
                       generation_time_seconds=round(generation_time, 2),
                       ai_provider=provider,
                       event_type="roadmap_generated")
        
        except Exception as e:
            logger.error("Failed to log generation metrics", error=str(e))
    
    def _generate_metadata(
        self,
        roadmap: Roadmap,
        generation_time: float,
        model_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate metadata for roadmap response
        
        This is business logic for creating response metadata.
        
        Args:
            roadmap: Generated roadmap
            generation_time: Time taken to generate roadmap
            model_info: Model information from AI service
            
        Returns:
            Dict containing metadata
        """
        return {
            "generation_time": f"{generation_time:.2f}s",
            "ai_provider": model_info.get("provider"),
            "ai_model": model_info.get("model"),
            "request_timestamp": time.time(),
            "modules_count": len(roadmap.modules),
            "total_estimated_hours": sum(m.estimated_hours for m in roadmap.modules)
        }

