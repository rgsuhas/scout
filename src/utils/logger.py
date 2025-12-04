"""
Logging configuration for the AI roadmap service
"""

import sys
import structlog
from typing import Any, Dict


def setup_logging(log_level: str = "info") -> None:
    """
    Configure structured logging for the application
    
    Args:
        log_level: Logging level (debug, info, warn, error)
    """
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level
            structlog.stdlib.add_log_level,
            
            # Add timestamp
            structlog.processors.TimeStamper(fmt="ISO", utc=True),
            
            # Stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            
            # Format exceptions
            structlog.dev.set_exc_info,
            
            # Add service name and version
            add_service_context,
            
            # JSON output for production, pretty print for development
            structlog.dev.ConsoleRenderer()
            if log_level.lower() == "debug"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_service_context(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add service context to all log messages
    
    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary
        
    Returns:
        Updated event dictionary with service context
    """
    event_dict["service"] = "ai-roadmap-service"
    event_dict["version"] = "1.0.0"
    return event_dict


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (optional)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)