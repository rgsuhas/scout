"""
Abstract interface for AI services to ensure model-agnostic implementation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from src.models.roadmap import RoadmapRequest, Roadmap


class AIServiceInterface(ABC):
    """Abstract base class for AI service providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI service with configuration
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.provider_name = self.__class__.__name__.lower().replace('aiservice', '')
    
    @abstractmethod
    async def generate_roadmap(self, request: RoadmapRequest, user_id: str) -> Roadmap:
        """
        Generate a learning roadmap based on user request
        
        Args:
            request: RoadmapRequest containing user goals, skills, and preferences
            user_id: Unique identifier for the user
            
        Returns:
            Roadmap: Generated learning roadmap
            
        Raises:
            AIServiceError: If roadmap generation fails
        """
        pass
    
    async def update_roadmap(self, existing_roadmap: Roadmap, user_prompt: str, user_id: str) -> Roadmap:
        """
        Update an existing roadmap based on user modifications
        
        This method modifies an existing roadmap according to user instructions.
        By default, it generates a new roadmap based on the existing one and modifications.
        Providers can override this for more sophisticated update logic.
        
        Args:
            existing_roadmap: The existing roadmap to modify
            user_prompt: User's instructions for modifications (e.g., "Add more Python modules", "Reduce timeline by 2 weeks")
            user_id: Unique identifier for the user
            
        Returns:
            Roadmap: Updated roadmap
            
        Raises:
            AIServiceError: If roadmap update fails
        """
        # Default implementation: generate a new roadmap based on existing one and modifications
        # Create a new request based on existing roadmap
        from src.models.roadmap import RoadmapRequest, SkillAssessment, DifficultyLevel
        
        # Extract skills from existing roadmap modules
        all_skills = []
        for module in existing_roadmap.modules:
            all_skills.extend(module.skills_taught)
        
        # Create unique skills with default scores
        unique_skills = list(set(all_skills))
        skill_assessments = [
            SkillAssessment(skill=skill, score=5, level=DifficultyLevel.INTERMEDIATE)
            for skill in unique_skills[:10]  # Limit to 10 skills
        ]
        
        # Create new request with modifications prompt
        modified_goal = f"{existing_roadmap.career_goal} - {user_prompt}"
        
        new_request = RoadmapRequest(
            user_goal=existing_roadmap.career_goal,
            user_skills=skill_assessments if skill_assessments else [
                SkillAssessment(skill="general", score=5, level=DifficultyLevel.BEGINNER)
            ],
            experience_level=DifficultyLevel.BEGINNER,
            preferences={"modifications": user_prompt, "existing_roadmap": existing_roadmap.model_dump()}
        )
        
        # Generate new roadmap
        return await self.generate_roadmap(new_request, user_id)
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the AI service is healthy and accessible
        
        Returns:
            Dict containing health status information
        """
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model
        
        Returns:
            Dict containing model information (name, version, capabilities, etc.)
        """
        pass
    
    def validate_request(self, request: RoadmapRequest) -> bool:
        """
        Validate the roadmap request (common validation logic)
        
        Args:
            request: The roadmap request to validate
            
        Returns:
            bool: True if valid, raises exception if invalid
        """
        if not request.user_goal:
            raise ValueError("user_goal is required")
        
        if not request.user_skills or len(request.user_skills) == 0:
            raise ValueError("user_skills cannot be empty")
        
        # Validate skill scores
        for skill in request.user_skills:
            if skill.score < 1 or skill.score > 10:
                raise ValueError(f"Skill score for {skill.skill} must be between 1 and 10")
        
        return True
    
    def get_provider_name(self) -> str:
        """Get the name of the AI provider"""
        return self.provider_name


class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    
    def __init__(self, message: str, provider: str, error_code: Optional[str] = None, original_error: Optional[Exception] = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "message": self.message,
            "provider": self.provider,
            "error_code": self.error_code,
            "has_original_error": self.original_error is not None
        }