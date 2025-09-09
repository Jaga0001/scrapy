"""
Simple configuration management for AI Web Scraper.
"""

import os
from typing import Dict, Any, List, Optional

class SimpleSettings:
    """Simple configuration management."""
    
    def __init__(self):
        # Application settings
        self.app_name = os.getenv("APP_NAME", "AI Web Scraper")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "true").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # API configuration
        self.api_host = os.getenv("API_HOST", "127.0.0.1")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.secret_key = os.getenv("SECRET_KEY", "simple_dev_key")
        self.encryption_master_key = os.getenv("ENCRYPTION_MASTER_KEY", "simple_encryption_key")
        
        # AI configuration
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # CORS settings
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8501")
        self.cors_allow_origins = [origin.strip() for origin in cors_origins.split(",")]
        
        # Scraper settings
        self.scraper_respect_robots_txt = os.getenv("SCRAPER_RESPECT_ROBOTS_TXT", "true").lower() == "true"
        self.scraper_user_agents = os.getenv("SCRAPER_USER_AGENTS", "Mozilla/5.0 (compatible; WebScraper/1.0)")
    
    def get_database_url(self) -> str:
        """Get database URL."""
        return os.getenv("DATABASE_URL", "sqlite:///webscraper.db")
    
    def get_user_agents(self) -> List[str]:
        """Get user agents list."""
        if self.scraper_user_agents:
            return [agent.strip() for agent in self.scraper_user_agents.split(",")]
        return ['Mozilla/5.0 (compatible; WebScraper/1.0)']
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


def get_settings() -> SimpleSettings:
    """Get settings instance."""
    return SimpleSettings()


# Global settings instance
settings = get_settings()