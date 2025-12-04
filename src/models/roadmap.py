"""
Pydantic models for roadmap data structures
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    """Difficulty levels for content and modules"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ResourceType(str, Enum):
    """Types of learning resources"""
    VIDEO = "video"
    ARTICLE = "article"
    DOCUMENTATION = "documentation"
    COURSE = "course"
    TUTORIAL = "tutorial"
    BOOK = "book"
    PRACTICE = "practice"


class SkillAssessment(BaseModel):
    """User's current skill assessment"""
    skill: str = Field(..., description="Name of the skill")
    score: int = Field(..., ge=1, le=10, description="Skill score from 1-10")
    level: DifficultyLevel = Field(..., description="Assessed skill level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill": "javascript",
                "score": 7,
                "level": "intermediate"
            }
        }


class LearningResource(BaseModel):
    """Individual learning resource"""
    title: str = Field(..., description="Resource title")
    type: ResourceType = Field(..., description="Type of resource")
    url: str = Field(..., description="Resource URL")
    duration: Optional[str] = Field(None, description="Estimated time needed")
    difficulty: DifficultyLevel = Field(..., description="Resource difficulty")
    why_recommended: Optional[str] = Field(None, description="Why this resource is recommended")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "JavaScript Fundamentals",
                "type": "video",
                "url": "https://www.youtube.com/watch?v=example",
                "duration": "2 hours",
                "difficulty": "beginner",
                "why_recommended": "Excellent introduction to ES6+ features"
            }
        }


class Project(BaseModel):
    """Hands-on project for a module"""
    title: str = Field(..., description="Project title")
    description: str = Field(..., description="What the learner will build")
    deliverables: List[str] = Field(..., description="Expected project outcomes")
    estimated_hours: int = Field(..., ge=1, description="Hours needed to complete project")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Personal Portfolio Website",
                "description": "Build a responsive portfolio showcasing your skills",
                "deliverables": ["Responsive HTML/CSS layout", "JavaScript interactivity", "Deployed website"],
                "estimated_hours": 8
            }
        }


class RoadmapModule(BaseModel):
    """Individual learning module within a roadmap"""
    id: str = Field(..., description="Unique module identifier")
    title: str = Field(..., description="Module title")
    description: str = Field(..., description="What the learner will achieve")
    estimated_hours: int = Field(..., ge=1, description="Time needed to complete module")
    skills_taught: List[str] = Field(..., description="Skills learned in this module")
    learning_objectives: List[str] = Field(..., description="Specific learning outcomes")
    
    project: Optional[Project] = Field(None, description="Hands-on project for this module")
    resources: List[LearningResource] = Field(..., description="Learning resources")
    prerequisites: List[str] = Field(default_factory=list, description="Required previous modules")
    assessment: str = Field(..., description="How to verify completion")
    
    @validator('resources')
    def validate_resources(cls, v):
        if len(v) < 2:
            raise ValueError('Each module must have at least 2 learning resources')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "module-1",
                "title": "JavaScript Fundamentals",
                "description": "Master modern JavaScript ES6+ features and async programming",
                "estimated_hours": 40,
                "skills_taught": ["javascript", "es6", "async-programming", "dom-manipulation"],
                "learning_objectives": [
                    "Understand JavaScript variable scoping and closures",
                    "Master async/await and Promise handling",
                    "Manipulate DOM elements effectively"
                ],
                "project": {
                    "title": "Interactive Todo App",
                    "description": "Build a dynamic todo application with local storage",
                    "deliverables": ["CRUD functionality", "Local storage persistence", "Responsive design"],
                    "estimated_hours": 12
                },
                "resources": [
                    {
                        "title": "JavaScript: The Modern Parts",
                        "type": "documentation",
                        "url": "https://javascript.info/",
                        "duration": "20 hours",
                        "difficulty": "beginner",
                        "why_recommended": "Comprehensive coverage of modern JavaScript"
                    }
                ],
                "prerequisites": [],
                "assessment": "Complete 5 JavaScript coding challenges and build the todo app project"
            }
        }


class Roadmap(BaseModel):
    """Complete learning roadmap"""
    id: str = Field(..., description="Unique roadmap identifier")
    user_id: str = Field(..., description="User who owns this roadmap")
    title: str = Field(..., description="Roadmap title")
    career_goal: str = Field(..., description="Target career goal")
    estimated_weeks: int = Field(..., ge=1, le=104, description="Total estimated completion time in weeks")
    difficulty_progression: str = Field(default="beginner -> intermediate -> advanced", description="How difficulty progresses")
    
    modules: List[RoadmapModule] = Field(..., description="Learning modules in order")
    current_module: int = Field(default=0, description="Current active module index")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Overall completion percentage")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    @validator('modules')
    def validate_modules(cls, v):
        if len(v) != 6:
            raise ValueError('Roadmap must contain exactly 6 modules')
        return v
    
    @validator('estimated_weeks')
    def validate_estimated_weeks(cls, v, values):
        if 'modules' in values:
            total_hours = sum(module.estimated_hours for module in values['modules'])
            # Assume 10 hours of study per week
            calculated_weeks = max(1, (total_hours + 9) // 10)  # Round up
            if abs(v - calculated_weeks) > 4:  # Allow some flexibility
                raise ValueError(f'Estimated weeks ({v}) should be close to calculated weeks ({calculated_weeks})')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "roadmap-abc123",
                "user_id": "user-456",
                "title": "Full Stack Developer Learning Path",
                "career_goal": "Full Stack Developer",
                "estimated_weeks": 16,
                "difficulty_progression": "beginner -> intermediate -> advanced",
                "modules": [],  # Would contain 6 RoadmapModule objects
                "current_module": 0,
                "progress_percentage": 0
            }
        }


class RoadmapRequest(BaseModel):
    """Request to generate a new roadmap"""
    user_goal: str = Field(..., description="Target career goal (e.g., 'Full Stack Developer', 'Solana Developer', 'Cybersecurity Specialist', etc. - any career goal is supported)")
    user_skills: List[SkillAssessment] = Field(..., description="Current skill assessments")
    experience_level: DifficultyLevel = Field(default=DifficultyLevel.BEGINNER, description="Overall experience level")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Learning preferences")
    
    @validator('user_goal')
    def validate_user_goal(cls, v):
        """
        Validate user goal - accepts any string goal.
        The AI model can generate roadmaps for any career goal.
        """
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('User goal must be a non-empty string')
        
        # Normalize the goal (trim whitespace)
        v = v.strip()
        
        # Optional: Log if using a non-standard goal (for analytics)
        # Common goals (for reference, not enforced):
        # "Full Stack Developer", "Data Scientist", "Cloud Engineer", 
        # "DevOps Engineer", "Mobile Developer", "Machine Learning Engineer",
        # "Product Manager", "UX/UI Designer", "Solana Developer", etc.
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
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
        }


class RoadmapUpdateRequest(BaseModel):
    """Request to update an existing roadmap"""
    user_prompt: str = Field(..., description="User's prompt describing how to modify the roadmap (e.g., 'Add more Python modules', 'Make it more focused on backend', 'Reduce the timeline by 2 weeks')")
    existing_roadmap: Optional[Roadmap] = Field(None, description="The existing roadmap to modify. If not provided, roadmap will be retrieved by ID")
    
    @validator('user_prompt')
    def validate_user_prompt(cls, v):
        """Validate user prompt"""
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('User prompt must be a non-empty string')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_prompt": "Add more Python modules and focus on backend development. Reduce the timeline by 2 weeks.",
                "existing_roadmap": None  # Will be retrieved by roadmap_id
            }
        }


class RoadmapResponse(BaseModel):
    """Response containing the generated roadmap"""
    success: bool = Field(default=True, description="Whether the generation was successful")
    roadmap: Roadmap = Field(..., description="The generated roadmap")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "roadmap": {
                    "id": "roadmap-abc123",
                    "user_id": "user-456",
                    "title": "Full Stack Developer Learning Path",
                    "career_goal": "Full Stack Developer",
                    "estimated_weeks": 16,
                    "modules": []
                },
                "metadata": {
                    "generation_time": "2.3s",
                    "ai_model": "gpt-3.5-turbo"
                }
            }
        }