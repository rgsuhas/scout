"""
Google Gemini provider implementation for roadmap generation
"""

from datetime import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
import structlog

from ..ai_service_interface import AIServiceError, AIServiceInterface
from ...models.roadmap import (DifficultyLevel, LearningResource, Project,
                             Roadmap, RoadmapModule, RoadmapRequest,
                             ResourceType)

logger = structlog.get_logger(__name__)


class GoogleProvider(AIServiceInterface):
    """Google Gemini implementation of the AI service interface"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        self.api_key = config.get("api_key")
        self.model_name = config.get("model", "gemini-1.5-flash")  # Updated to current model name
        
        # Set model-specific defaults for max_tokens if not provided
        # Gemini models have these limits: gemini-pro/gemini-1.5-pro: 8192, gemini-1.5-flash: 8192, gemini-2.0-flash: 8192
        if "max_tokens" not in config:
            # Use maximum supported by most models
            self.max_tokens = 8192
        else:
            provided_tokens = config.get("max_tokens")
            # Cap at 8192 which is the limit for most Gemini models
            self.max_tokens = min(provided_tokens, 8192)
            
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 60)  # Increased timeout for longer generations
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Configure safety settings to be less restrictive
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        # Create generation config object
        # Note: max_output_tokens has limits: gemini-pro supports up to 8192, gemini-1.5-pro supports up to 8192
        generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            top_p=0.95,
            top_k=40,
            candidate_count=1
        )
        
        logger.info("Initializing Gemini model", 
                   model=self.model_name,
                   max_tokens=self.max_tokens,
                   temperature=self.temperature)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
    
    async def generate_roadmap(self, request: RoadmapRequest, user_id: str) -> Roadmap:
        """Generate roadmap using Google Gemini"""
        try:
            # Validate request
            self.validate_request(request)
            
            # Build prompt
            prompt = self._build_roadmap_prompt(request)
            system_prompt = self._get_system_prompt()
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Call Gemini API
            logger.info("Generating roadmap with Google Gemini", 
                       user_id=user_id, 
                       goal=request.user_goal,
                       model=self.model_name,
                       prompt_length=len(full_prompt))
            
            response = self.model.generate_content(full_prompt)
            
            # Log the raw response for debugging
            logger.debug("Raw Gemini response received",
                       candidates_count=len(response.candidates) if response.candidates else 0,
                       prompt_feedback=response.prompt_feedback if hasattr(response, 'prompt_feedback') else None)
            
            # Check if response was blocked
            if not response.candidates:
                logger.error("No candidates in response")
                raise AIServiceError(
                    message="Response was blocked by safety filters",
                    provider="google",
                    error_code="SAFETY_FILTER"
                )
            
            # Check finish reason
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason
            
            logger.info("Processing Gemini response",
                       finish_reason=finish_reason,
                       has_content=bool(candidate.content),
                       has_parts=bool(candidate.content and candidate.content.parts))
            
            # Try to get content, regardless of finish reason
            content = None
            try:
                # Check if content exists and has parts
                if candidate.content and hasattr(candidate.content, 'parts') and candidate.content.parts:
                    # Check if the parts list is not empty
                    if len(candidate.content.parts) > 0:
                        content = candidate.content.parts[0].text
                    else:
                        logger.warning("Content parts list is empty",
                                     finish_reason=finish_reason)
                elif hasattr(response, 'text'):
                    content = response.text
                
                if content:
                    logger.info("Successfully extracted response content",
                              content_length=len(content),
                              content_preview=content[:200])
            except (IndexError, AttributeError) as e:
                logger.error("Failed to extract content from response",
                           error=str(e),
                           error_type=type(e).__name__,
                           candidate_info=str(candidate),
                           has_content=hasattr(candidate, 'content'),
                           has_parts=hasattr(candidate.content, 'parts') if hasattr(candidate, 'content') else False)
            except Exception as e:
                logger.error("Failed to extract content from response",
                           error=str(e),
                           error_type=type(e).__name__,
                           candidate_info=str(candidate))
            
            # Handle different finish reasons
            # finish_reason: 0=UNSPECIFIED, 1=STOP, 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER
            if finish_reason == 3:  # SAFETY
                logger.error("Response blocked by safety filters",
                           safety_ratings=candidate.safety_ratings if hasattr(candidate, 'safety_ratings') else None)
                raise AIServiceError(
                    message="Response blocked by safety filters. Try adjusting the prompt.",
                    provider="google",
                    error_code="SAFETY_BLOCKED"
                )
            elif finish_reason == 2:  # MAX_TOKENS
                # If we have content, try to use it even if truncated
                if content:
                    logger.warning("Response hit max tokens limit but partial content available",
                                model=self.model_name,
                                max_tokens=self.max_tokens,
                                content_length=len(content))
                else:
                    logger.error("No content available in max tokens response")
                    raise AIServiceError(
                        message="Response exceeded token limit and no partial content available",
                        provider="google",
                        error_code="MAX_TOKENS_EXCEEDED"
                    )
            elif not content:
                logger.error("No content available in response")
                raise AIServiceError(
                    message="Failed to get content from response",
                    provider="google",
                    error_code="NO_CONTENT"
                )
            
            # Clean the content - remove markdown code blocks if present
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]  # Remove ```json
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]  # Remove ```
            
            # Remove trailing ```
            if cleaned_content.rstrip().endswith("```"):
                cleaned_content = cleaned_content.rstrip()[:-3].rstrip()
            
            # The response should be a valid JSON object
            try:
                roadmap_data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON content", 
                           error=str(e), 
                           content_preview=cleaned_content[:500],
                           original_preview=content[:200],
                           user_id=user_id)
                
                # If response was truncated, provide more helpful error
                if finish_reason == 2:  # MAX_TOKENS
                    raise AIServiceError(
                        message="Response was truncated due to token limit. Try reducing the prompt size or increasing max_tokens.",
                        provider="google",
                        error_code="TRUNCATED_RESPONSE",
                        original_error=e
                    )
                else:
                    raise AIServiceError(
                        message="Failed to parse AI response as JSON.",
                        provider="google",
                        error_code="PARSE_ERROR",
                        original_error=e
                    )
            
            # Create roadmap object
            roadmap = self._create_roadmap_from_response(roadmap_data, request, user_id)
            
            logger.info("Roadmap generated successfully", 
                       user_id=user_id,
                       roadmap_id=roadmap.id,
                       modules_count=len(roadmap.modules))
            
            return roadmap
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini response", error=str(e), user_id=user_id)
            raise AIServiceError(
                message="Failed to parse AI response as JSON",
                provider="google",
                error_code="PARSE_ERROR",
                original_error=e
            )
        except Exception as e:
            logger.error("Gemini roadmap generation failed", error=str(e), user_id=user_id)
            raise AIServiceError(
                message=f"Roadmap generation failed: {str(e)}",
                provider="google",
                error_code="GENERATION_ERROR",
                original_error=e
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Google Gemini service health"""
        try:
            # Make a simple API call to check connectivity
            response = self.model.generate_content("Hello")
            
            return {
                "status": "healthy",
                "provider": "google",
                "model": self.model_name,
                "api_accessible": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "google", 
                "model": self.model_name,
                "error": str(e),
                "api_accessible": False
            }
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get Google Gemini model information"""
        return {
            "provider": "google",
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "capabilities": [
                "text_generation",
                "json_structured_output",
                "context_understanding",
                "multimodal"
            ],
            "supported_languages": ["en", "multiple"],
            "api_endpoint": "https://generativelanguage.googleapis.com"
        }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for roadmap generation"""
        return """You are an expert learning path designer across ALL professional domains - technology, engineering, business, trades, arts, sciences, healthcare, finance, education, and any other field.

Your expertise spans:
- Software development and programming
- Engineering (mining, civil, mechanical, electrical, chemical)
- Business and entrepreneurship (MBA concepts, trading, management)
- Skilled trades (tailoring, carpentry, electrician)
- Creative fields (design, writing, photography)
- Professional services (legal, consulting, real estate)
- Sciences and research
- Healthcare and medicine
- Education and training

IMPORTANT: Carefully analyze the user's career goal and create a roadmap that matches their ACTUAL field of interest. Do not assume or default to programming unless the goal explicitly relates to software development.

Create practical, industry-relevant learning roadmaps in JSON format that reflect the real skills, knowledge, and resources needed for that specific career path."""

    def _build_roadmap_prompt(self, request: RoadmapRequest) -> str:
        """Build the user prompt for roadmap generation"""
        
        # Analyze skill gaps
        skill_analysis = self._analyze_skill_gaps(request.user_goal, request.user_skills)
        
        # Build skills summary (limit to top 5 most relevant)
        top_skills = sorted(request.user_skills, key=lambda x: x.score, reverse=True)[:5]
        skills_summary = "\n".join([
            f"- {skill.skill}: {skill.score}/10"
            for skill in top_skills
        ])
        
        # Provide flexible context that lets AI analyze the goal
        # Instead of hardcoding domain detection, we give the AI tools to analyze any field
        analysis_context = """\nIMPORTANT: Analyze the career goal carefully and create a learning path that matches the ACTUAL field:
- If it's a trade (tailor, carpenter, electrician) → focus on trade skills, apprenticeships, certifications
- If it's business (trader, MBA, entrepreneur) → focus on business concepts, finance, strategy, case studies
- If it's software/tech (developer, programmer, computer science) → focus on programming and tech skills
- If it's engineering (mining, civil, mechanical) → focus on engineering principles, safety, technical skills
- If it's creative (designer, writer, artist) → focus on creative skills, portfolio building, industry standards
- If it's professional (lawyer, doctor, consultant) → focus on professional education, certifications, ethics
- For any other field → analyze what skills and knowledge are actually needed in that profession

Use real, appropriate resources for the field (university courses, trade schools, professional organizations, industry certifications, etc.)."""
        
        return f"""Create a 6-module learning roadmap for {request.user_goal} at {request.experience_level} level.

{analysis_context}

REQUIREMENTS:
- Analyze what skills, knowledge, and competencies are actually needed for this career
- Use real, appropriate resources: university courses, trade schools, professional organizations, industry certifications, textbooks, online platforms relevant to the field
- Include prerequisites showing logical learning progression and module dependencies
- Provide specific, measurable assessment criteria relevant to the field
- Balance theoretical learning with practical application (projects, exercises, hands-on work, case studies, or field-specific activities)
- Include 2-3 learning resources per module from reputable sources in that field
- Ensure the content genuinely prepares someone for this career path

Output ONLY valid JSON, no markdown or code blocks:
{{
  "estimated_weeks": 12,
  "difficulty_progression": "beginner → intermediate → advanced",
  "modules": [
    {{
      "id": "module-1",
      "title": "Specific module title",
      "description": "What learner will achieve (2 sentences)",
      "estimated_hours": 30,
      "skills_taught": ["skill1", "skill2", "skill3"],
      "learning_objectives": ["objective 1", "objective 2", "objective 3"],
      "prerequisites": [],
      "resources": [
        {{"title": "Real Resource Name", "type": "documentation", "url": "https://developer.mozilla.org/en-US/docs/..."}},
        {{"title": "Actual Course Title", "type": "course", "url": "https://www.freecodecamp.org/..."}}
      ],
      "projects": [
        {{
          "title": "Specific project name",
          "description": "What to build and why",
          "deliverables": ["deliverable 1", "deliverable 2"],
          "estimated_hours": 10
        }}
      ]
    }}
  ]
}}"""
    
    def _analyze_skill_gaps(self, target_role: str, current_skills: List) -> str:
        """Analyze skill gaps for the target role"""
        # Simplified gap analysis
        current_skill_names = [s.skill.lower() for s in current_skills]
        strengths = [s.skill for s in current_skills if s.score >= 7][:2]
        
        gaps_str = "building foundation" if not strengths else f"{strengths[0]} ready"
        return gaps_str
    
    def _normalize_resource_type(self, resource_type: str) -> ResourceType:
        """Normalize resource type to valid enum value"""
        resource_type = resource_type.lower().strip()
        
        # Map invalid types to valid ones
        type_mapping = {
            "video": ResourceType.VIDEO,
            "article": ResourceType.ARTICLE,
            "documentation": ResourceType.DOCUMENTATION,
            "course": ResourceType.COURSE,
            "tutorial": ResourceType.TUTORIAL,
            "book": ResourceType.BOOK,
            "practice": ResourceType.PRACTICE,
            # Map common variations
            "doc": ResourceType.DOCUMENTATION,
            "docs": ResourceType.DOCUMENTATION,
            "tut": ResourceType.TUTORIAL,
            "tutorials": ResourceType.TUTORIAL,
            "articles": ResourceType.ARTICLE,
            "videos": ResourceType.VIDEO,
            "courses": ResourceType.COURSE,
            "books": ResourceType.BOOK,
            "practices": ResourceType.PRACTICE,
            # Map other common types
            "blog": ResourceType.ARTICLE,
            "blog post": ResourceType.ARTICLE,
            "youtube": ResourceType.VIDEO,
            "interactive": ResourceType.TUTORIAL,
            "game": ResourceType.TUTORIAL,
            "interactive game": ResourceType.TUTORIAL,
            "project": ResourceType.PRACTICE,
            "exercise": ResourceType.PRACTICE,
        }
        
        # Try direct mapping first
        if resource_type in type_mapping:
            return type_mapping[resource_type]
        
        # Try to match any enum value
        try:
            return ResourceType(resource_type)
        except ValueError:
            # Default to tutorial if can't determine
            logger.warning("Unknown resource type, defaulting to tutorial", 
                         resource_type=resource_type)
            return ResourceType.TUTORIAL
    
    def _create_roadmap_from_response(self, data: Dict[str, Any], request: RoadmapRequest, user_id: str) -> Roadmap:
        """Create a Roadmap object from Gemini response data"""
        
        # Generate unique ID
        roadmap_id = f"roadmap_{uuid.uuid4().hex[:8]}"
        
        # Process modules
        modules = []
        for i, module_data in enumerate(data.get("modules", [])):
            # Create resources
            resources = []
            for res_data in module_data.get("resources", []):
                # Normalize resource type
                resource_type_str = res_data.get("type", "article")
                try:
                    resource_type = self._normalize_resource_type(resource_type_str)
                except Exception as e:
                    logger.warning("Failed to normalize resource type, using default",
                                 resource_type=resource_type_str, error=str(e))
                    resource_type = ResourceType.TUTORIAL
                
                # Handle simplified resource format (title, type, url) or full format
                resource = LearningResource(
                    title=res_data.get("title", f"Resource {len(resources) + 1}"),
                    type=resource_type,
                    url=res_data.get("url", "#"),
                    duration=res_data.get("duration") or res_data.get("estimated_hours"),
                    difficulty=DifficultyLevel(res_data.get("difficulty", "beginner")),
                    why_recommended=res_data.get("why_recommended")
                )
                resources.append(resource)
            
            # Create projects if present
            projects = []
            for proj_data in module_data.get("projects", []):
                # If deliverables is a string or not provided, convert to list
                deliverables = proj_data.get("deliverables", ["Project completion"])
                if isinstance(deliverables, str):
                    deliverables = [deliverables]
                
                project = Project(
                    title=proj_data.get("title", f"Project {i + 1}"),
                    description=proj_data.get("description", "Hands-on project"),
                    deliverables=deliverables,
                    estimated_hours=proj_data.get("estimated_hours", 10)
                )
                projects.append(project)
            
            # Create single project object from first project if multiple
            project = projects[0] if projects else None
            
            # Create module with better assessment handling
            assessment = module_data.get("assessment")
            if not assessment or assessment == "Complete module exercises":
                # Generate a more specific assessment based on the module
                if project:
                    assessment = f"Complete {project.title.lower()} demonstrating mastery of {', '.join(module_data.get('skills_taught', [])[:2])}"
                else:
                    assessment = f"Demonstrate understanding of {', '.join(module_data.get('skills_taught', [])[:2])} through practical exercises"
            
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
                assessment=assessment
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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return roadmap
