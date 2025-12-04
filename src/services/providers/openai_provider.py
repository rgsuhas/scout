"""
OpenAI provider implementation for roadmap generation
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import structlog

from ..ai_service_interface import AIServiceInterface, AIServiceError
from ...models.roadmap import RoadmapRequest, Roadmap, RoadmapModule, LearningResource, Project, DifficultyLevel, ResourceType

logger = structlog.get_logger()


class OpenAIProvider(AIServiceInterface):
    """OpenAI implementation of the AI service interface"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.base_url = config.get("base_url")  # For Azure OpenAI
        self.max_tokens = config.get("max_tokens", 2000)
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 30)
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    async def generate_roadmap(self, request: RoadmapRequest, user_id: str) -> Roadmap:
        """Generate roadmap using OpenAI"""
        try:
            # Validate request
            self.validate_request(request)
            
            # Build prompt
            prompt = self._build_roadmap_prompt(request)
            
            # Call OpenAI API
            logger.info("Generating roadmap with OpenAI", 
                       user_id=user_id, 
                       goal=request.user_goal,
                       model=self.model)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            roadmap_data = json.loads(content)
            
            # Create roadmap object
            roadmap = self._create_roadmap_from_response(roadmap_data, request, user_id)
            
            logger.info("Roadmap generated successfully", 
                       user_id=user_id,
                       roadmap_id=roadmap.id,
                       modules_count=len(roadmap.modules))
            
            return roadmap
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI response", error=str(e), user_id=user_id)
            raise AIServiceError(
                message="Failed to parse AI response as JSON",
                provider="openai",
                error_code="PARSE_ERROR",
                original_error=e
            )
        except Exception as e:
            logger.error("OpenAI roadmap generation failed", error=str(e), user_id=user_id)
            raise AIServiceError(
                message=f"Roadmap generation failed: {str(e)}",
                provider="openai",
                error_code="GENERATION_ERROR",
                original_error=e
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI service health"""
        try:
            # Make a simple API call to check connectivity
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            return {
                "status": "healthy",
                "provider": "openai",
                "model": self.model,
                "response_time_ms": 0,  # Could add timing here
                "api_accessible": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "openai", 
                "model": self.model,
                "error": str(e),
                "api_accessible": False
            }
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "provider": "openai",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "capabilities": [
                "text_generation",
                "json_structured_output",
                "context_understanding"
            ],
            "supported_languages": ["en"],  # Could expand this
            "base_url": self.base_url or "https://api.openai.com/v1"
        }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for roadmap generation"""
        return """You are an expert learning path designer and career mentor. Your role is to create highly practical, industry-relevant learning roadmaps.

Key principles:
1. Focus on hands-on projects and real-world applications
2. Build skills progressively from current level
3. Include industry best practices and current technologies
4. Provide measurable learning outcomes
5. Create time-efficient learning paths

You must respond with valid JSON only, following the exact structure specified in the user prompt.
Each roadmap must contain exactly 6 modules with practical projects and curated resources."""
    
    def _build_roadmap_prompt(self, request: RoadmapRequest) -> str:
        """Build the user prompt for roadmap generation"""
        
        # Analyze skill gaps
        skill_analysis = self._analyze_skill_gaps(request.user_goal, request.user_skills)
        
        # Build skills summary
        skills_summary = "\n".join([
            f"- {skill.skill}: {skill.score}/10 ({skill.level})"
            for skill in request.user_skills
        ])
        
        return f"""Create a personalized learning roadmap for someone who wants to become a {request.user_goal}.

LEARNER PROFILE:
- Target Role: {request.user_goal}
- Experience Level: {request.experience_level}
- Current Skills:
{skills_summary}
- Skill Gaps: {skill_analysis}
- Learning Preferences: {request.preferences or 'Not specified'}

REQUIREMENTS:
- Create exactly 6 learning modules
- Each module should build on previous knowledge
- Include practical projects for hands-on learning
- Provide 3-4 learning resources per module
- Focus on industry-relevant skills
- Progressive difficulty (beginner → intermediate → advanced)

RESPONSE FORMAT (JSON only):
{{
    "estimated_weeks": 12-24,
    "difficulty_progression": "beginner -> intermediate -> advanced",
    "modules": [
        {{
            "id": "module-1",
            "title": "Specific, actionable module title",
            "description": "What they'll learn and achieve (2-3 sentences)",
            "estimated_hours": 20-50,
            "skills_taught": ["specific", "technical", "skills"],
            "learning_objectives": [
                "Specific measurable outcome 1",
                "Specific measurable outcome 2",
                "Specific measurable outcome 3"
            ],
            "project": {{
                "title": "Hands-on project name",
                "description": "What they'll build and learn",
                "deliverables": ["outcome1", "outcome2", "outcome3"],
                "estimated_hours": 8-20
            }},
            "resources": [
                {{
                    "title": "Specific resource name",
                    "type": "video|article|documentation|course|tutorial",
                    "url": "https://realistic-url-or-domain.com",
                    "duration": "X hours",
                    "difficulty": "beginner|intermediate|advanced",
                    "why_recommended": "Brief explanation of value"
                }}
            ],
            "prerequisites": ["previous-module-ids"],
            "assessment": "How to verify completion and understanding"
        }}
    ]
}}

Focus on {request.user_goal} role requirements and consider their {request.experience_level} level."""
    
    def _analyze_skill_gaps(self, target_role: str, current_skills: List) -> str:
        """Analyze skill gaps for the target role"""
        role_requirements = {
            "Full Stack Developer": ["javascript", "react", "nodejs", "databases", "api-design", "deployment", "git"],
            "Data Scientist": ["python", "statistics", "machine-learning", "data-visualization", "sql", "pandas", "numpy"],
            "Cloud Engineer": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "linux", "networking"],
            "DevOps Engineer": ["linux", "docker", "kubernetes", "ci-cd", "monitoring", "scripting", "cloud"],
            "Mobile Developer": ["react-native", "flutter", "ios", "android", "mobile-ui", "api-integration"],
            "Machine Learning Engineer": ["python", "tensorflow", "pytorch", "mlops", "data-engineering", "statistics"],
            "Product Manager": ["product-strategy", "user-research", "analytics", "roadmapping", "stakeholder-management"],
            "UX/UI Designer": ["figma", "user-research", "prototyping", "design-systems", "usability-testing"]
        }
        
        required_skills = role_requirements.get(target_role, [])
        current_skill_names = [skill.skill.lower() for skill in current_skills]
        
        gaps = [skill for skill in required_skills if skill not in current_skill_names]
        strengths = [skill.skill for skill in current_skills if skill.score >= 7]
        
        return f"Missing: {', '.join(gaps[:5]) if gaps else 'None major gaps'}. Strengths: {', '.join(strengths[:3]) if strengths else 'Building foundation'}"
    
    def _create_roadmap_from_response(self, data: Dict[str, Any], request: RoadmapRequest, user_id: str) -> Roadmap:
        """Create a Roadmap object from OpenAI response data"""
        
        # Generate unique ID
        roadmap_id = f"roadmap_{uuid.uuid4().hex[:8]}"
        
        # Process modules
        modules = []
        for i, module_data in enumerate(data.get("modules", [])):
            # Create resources
            resources = []
            for res_data in module_data.get("resources", []):
                resource = LearningResource(
                    title=res_data.get("title", f"Resource {len(resources) + 1}"),
                    type=ResourceType(res_data.get("type", "article")),
                    url=res_data.get("url", "#"),
                    duration=res_data.get("duration"),
                    difficulty=DifficultyLevel(res_data.get("difficulty", "beginner")),
                    why_recommended=res_data.get("why_recommended")
                )
                resources.append(resource)
            
            # Create project if present
            project = None
            if "project" in module_data:
                proj_data = module_data["project"]
                project = Project(
                    title=proj_data.get("title", f"Project {i + 1}"),
                    description=proj_data.get("description", "Hands-on project"),
                    deliverables=proj_data.get("deliverables", ["Project completion"]),
                    estimated_hours=proj_data.get("estimated_hours", 10)
                )
            
            # Create module
            module = RoadmapModule(
                id=module_data.get("id", f"module-{i + 1}"),
                title=module_data.get("title", f"Module {i + 1}"),
                description=module_data.get("description", "Learning module"),
                estimated_hours=module_data.get("estimated_hours", 30),
                skills_taught=module_data.get("skills_taught", []),
                learning_objectives=module_data.get("learning_objectives", []),
                project=project,
                resources=resources,
                prerequisites=module_data.get("prerequisites", []),
                assessment=module_data.get("assessment", "Complete module exercises")
            )
            modules.append(module)
        
        # Create roadmap
        roadmap = Roadmap(
            id=roadmap_id,
            user_id=user_id,
            title=f"{request.user_goal} Learning Path",
            career_goal=request.user_goal,
            estimated_weeks=data.get("estimated_weeks", 16),
            difficulty_progression=data.get("difficulty_progression", "beginner -> intermediate -> advanced"),
            modules=modules,
            current_module=0,
            progress_percentage=0,
            created_at=datetime.utcnow()
        )
        
        return roadmap