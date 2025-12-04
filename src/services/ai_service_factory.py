"""
Factory for creating AI service instances based on configuration
"""

from typing import Dict, Any, Optional, Type
import structlog

from .ai_service_interface import AIServiceInterface, AIServiceError
from .providers.google_provider import GoogleProvider

# Optional imports for other providers
try:
    from .providers.openai_provider import OpenAIProvider
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAIProvider = None  # type: ignore
    OPENAI_AVAILABLE = False

logger = structlog.get_logger()


class AIServiceFactory:
    """Factory class for creating AI service providers"""
    
    # Registry of available providers (dynamically built)
    @classmethod
    def _get_providers(cls) -> Dict[str, Optional[Type[AIServiceInterface]]]:
        """Get registry of available providers"""
        providers: Dict[str, Optional[Type[AIServiceInterface]]] = {
            "google": GoogleProvider,
        }
        
        # Add OpenAI if available
        if OPENAI_AVAILABLE and OpenAIProvider:
            providers["openai"] = OpenAIProvider
        
        return providers
    
    @classmethod
    def create_ai_service(cls, provider: str, config: Dict[str, Any]) -> AIServiceInterface:
        """
        Create an AI service instance based on provider name
        
        Args:
            provider: Name of the AI provider (openai, anthropic, etc.)
            config: Provider-specific configuration
            
        Returns:
            AIServiceInterface: Configured AI service instance
            
        Raises:
            AIServiceError: If provider is not supported or configuration is invalid
        """
        providers = cls._get_providers()
        if provider not in providers:
            supported = ", ".join(providers.keys())
            raise AIServiceError(
                message=f"Unsupported AI provider: {provider}. Supported providers: {supported}",
                provider=provider,
                error_code="UNSUPPORTED_PROVIDER"
            )
        
        provider_class = providers[provider]
        if provider_class is None:
            raise AIServiceError(
                message=f"Provider {provider} is not available (missing dependencies)",
                provider=provider,
                error_code="PROVIDER_UNAVAILABLE"
            )
        
        try:
            service_instance = provider_class(config)
            
            logger.info("AI service created successfully", 
                       provider=provider, 
                       service_class=provider_class.__name__)
            
            return service_instance
            
        except Exception as e:
            logger.error("Failed to create AI service", 
                        provider=provider, 
                        error=str(e))
            raise AIServiceError(
                message=f"Failed to initialize {provider} service: {str(e)}",
                provider=provider,
                error_code="INITIALIZATION_ERROR",
                original_error=e
            )
    
    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported AI providers"""
        return list(cls._get_providers().keys())
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a new AI provider
        
        Args:
            name: Provider name
            provider_class: Class implementing AIServiceInterface
        
        Note:
            This method is kept for backward compatibility but providers
            are now dynamically loaded. Consider using direct imports instead.
        """
        if not issubclass(provider_class, AIServiceInterface):
            raise ValueError(f"Provider class must implement AIServiceInterface")
        
        # Note: This won't persist since _providers is now a method
        # In a real implementation, you'd want to maintain a class-level registry
        logger.info("New AI provider registered", provider=name, class_name=provider_class.__name__)


def create_ai_service_from_settings(settings) -> AIServiceInterface:
    """
    Create AI service instance from application settings
    
    Args:
        settings: Application settings object
        
    Returns:
        AIServiceInterface: Configured AI service instance
    """
    provider = settings.ai_provider.lower()
    
    # Build provider-specific config
    if provider == "openai":
        config = {
            "api_key": settings.openai_api_key,
            "model": settings.openai_model,
            "base_url": settings.openai_base_url,
            "max_tokens": settings.ai_max_tokens,
            "temperature": settings.ai_temperature,
            "timeout": settings.ai_timeout
        }
    elif provider == "anthropic":
        config = {
            "api_key": settings.anthropic_api_key,
            "model": settings.anthropic_model,
            "max_tokens": settings.ai_max_tokens,
            "temperature": settings.ai_temperature,
            "timeout": settings.ai_timeout
        }
    elif provider == "google":
        config = {
            "api_key": settings.google_api_key,
            "model": settings.google_model,
            "max_tokens": settings.ai_max_tokens,
            "temperature": settings.ai_temperature,
            "timeout": settings.ai_timeout
        }
    elif provider == "ollama":
        config = {
            "base_url": settings.ollama_base_url,
            "model": settings.ollama_model,
            "max_tokens": settings.ai_max_tokens,
            "temperature": settings.ai_temperature,
            "timeout": settings.ai_timeout
        }
    elif provider == "huggingface":
        config = {
            "api_key": settings.huggingface_api_key,
            "model": settings.huggingface_model,
            "max_tokens": settings.ai_max_tokens,
            "temperature": settings.ai_temperature,
            "timeout": settings.ai_timeout
        }
    else:
        raise AIServiceError(
            message=f"Unknown provider: {provider}",
            provider=provider,
            error_code="UNKNOWN_PROVIDER"
        )
    
    return AIServiceFactory.create_ai_service(provider, config)