"""
Configuration settings for the AI Roadmap Service
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    service_name: str = "ai-roadmap-service"
    service_version: str = "1.0.0"
    port: int = 8003
    environment: str = "development"
    log_level: str = "info"
    debug: bool = False
    reload: bool = True
    
    # AI Provider Configuration
    ai_provider: str = "google"  # google (default), openai (optional, requires openai package)
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_base_url: Optional[str] = None  # For Azure OpenAI or custom endpoints
    
    # Anthropic Configuration
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    
    # Google (Gemini) Configuration
    google_api_key: Optional[str] = None
    google_model: str = "gemini-1.5-flash"  # Updated to current model name
    
    # Ollama Configuration (Local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    
    # Hugging Face Configuration
    huggingface_api_key: Optional[str] = None
    huggingface_model: str = "microsoft/DialoGPT-medium"
    
    # Common AI Parameters
    ai_max_tokens: int = 8192  # Increased for roadmap generation
    ai_temperature: float = 0.7
    ai_timeout: int = 30
    
    # External Service URLs
    auth_service_url: str = "http://localhost:8001"
    profile_service_url: str = "http://localhost:8002"
    frontend_url: str = "http://localhost:3000"
    
    # Database Configuration
    database_url: Optional[str] = "sqlite:///./roadmaps.db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1 hour in seconds
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour in seconds
    
    # Security
    jwt_secret: str = "demo-jwt-secret"
    api_key: Optional[str] = None
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # CORS Settings
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validate AI provider configuration
        if self.environment != "test":
            self._validate_ai_provider()
        
        # Add frontend URL to allowed origins if not already present
        if self.frontend_url not in self.allowed_origins:
            self.allowed_origins.append(self.frontend_url)
    
    def _validate_ai_provider(self):
        """Validate that the selected AI provider has required credentials"""
        provider_validations = {
            "openai": lambda: self.openai_api_key is not None,
            "anthropic": lambda: self.anthropic_api_key is not None,
            "google": lambda: self.google_api_key is not None,
            "ollama": lambda: True,  # Local, no API key needed
            "huggingface": lambda: self.huggingface_api_key is not None,
        }
        
        if self.ai_provider not in provider_validations:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}. "
                           f"Supported: {', '.join(provider_validations.keys())}")
        
        if not provider_validations[self.ai_provider]():
            raise ValueError(f"API key required for {self.ai_provider} provider")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test mode"""
        return self.environment.lower() == "test"


# Global settings instance
settings = Settings()