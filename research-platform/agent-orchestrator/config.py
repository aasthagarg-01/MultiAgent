# agent-orchestrator/config.py
"""Configuration and environment validation for Agent Orchestrator."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager with environment validation."""
    
    REQUIRED_ENV_VARS = {
        'GROQ_API_KEY': 'Groq API key for LLM',
        'TAVILY_API_KEY': 'Tavily API key for web search',
        'DATABASE_URL': 'PostgreSQL database connection URL',
        'TASK_SERVICE_URL': 'Task Service base URL',
    }
    
    OPTIONAL_ENV_VARS = {
        'LOG_LEVEL': 'INFO',
        'GROQ_MODEL': 'llama-3.3-70b-versatile',
    }
    
    @staticmethod
    def validate_on_startup() -> bool:
        """
        Validate all required environment variables are set.
        
        Returns:
            bool: True if all required vars are set, False otherwise
        """
        missing_vars = []
        
        for var_name, description in Config.REQUIRED_ENV_VARS.items():
            if not os.getenv(var_name):
                missing_vars.append(f"{var_name} ({description})")
                logger.error(f"Missing required environment variable: {var_name}")
        
        if missing_vars:
            logger.error(f"Cannot start - missing {len(missing_vars)} required environment variables:")
            for var in missing_vars:
                logger.error(f"  - {var}")
            return False
        
        logger.info("All required environment variables are set")
        return True
    
    @staticmethod
    def get(key: str, default: Optional[str] = None) -> str:
        """Get environment variable with fallback."""
        value = os.getenv(key, default)
        if value is None:
            logger.warning(f"Environment variable {key} not found and no default provided")
        return value
