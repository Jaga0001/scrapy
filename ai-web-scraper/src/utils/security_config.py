"""
Simple configuration utilities for AI Web Scraper.
"""

import os
from typing import List, Dict, Any

class SecurityConfig:
    """Simple configuration manager."""
    
    @staticmethod
    def get_secure_secret_key() -> str:
        """Get secret key from environment."""
        return os.getenv("SECRET_KEY", "simple_dev_key")
    
    @staticmethod
    def get_encryption_key() -> str:
        """Get encryption key from environment."""
        return os.getenv("ENCRYPTION_MASTER_KEY", "simple_encryption_key")
    
    @staticmethod
    def get_secure_user_agents() -> List[str]:
        """Get user agents from environment."""
        user_agents_env = os.getenv("SCRAPER_USER_AGENTS", "")
        
        if user_agents_env:
            return [ua.strip() for ua in user_agents_env.split(",") if ua.strip()]
        
        return ['Mozilla/5.0 (compatible; WebScraper/1.0)']
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get CORS origins."""
        cors_origins = os.getenv("CORS_ORIGINS", "")
        
        if cors_origins:
            return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
        
        return ["http://localhost:8501"]
    
    @staticmethod
    def get_api_base_url() -> str:
        """Get API base URL."""
        api_base = os.getenv("API_BASE_URL")
        if api_base:
            return api_base
        
        host = os.getenv("API_HOST", "localhost")
        port = os.getenv("API_PORT", "8000")
        
        return f"http://{host}:{port}/api/v1"
    
    @staticmethod
    def get_scraper_config() -> Dict[str, Any]:
        """Get scraper configuration."""
        return {
            'respect_robots_txt': os.getenv("SCRAPER_RESPECT_ROBOTS_TXT", "true").lower() == "true",
            'delay_min': int(os.getenv("SCRAPER_DELAY_MIN", "1")),
            'delay_max': int(os.getenv("SCRAPER_DELAY_MAX", "3")),
            'timeout': int(os.getenv("SCRAPER_TIMEOUT", "10")),
            'max_retries': int(os.getenv("SCRAPER_MAX_RETRIES", "3")),
            'user_agents': SecurityConfig.get_secure_user_agents()
        }
    
    @staticmethod
    def get_rate_limit_config() -> Dict[str, int]:
        """Get rate limiting configuration."""
        return {
            'requests': int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            'window': int(os.getenv("RATE_LIMIT_WINDOW", "3600"))
        }

def validate_security_on_startup():
    """Simple startup validation - does nothing now."""
    pass