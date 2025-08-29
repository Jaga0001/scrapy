"""
Secure configuration management for AI Web Scraper.
"""

import os
import warnings
from typing import Dict, Any, List, Optional
from pydantic import BaseSettings, Field, validator
from pathlib import Path


class SecureSettings(BaseSettings):
    """Secure configuration management with validation."""
    
    # Application settings
    app_name: str = Field(default="AI Web Scraper", env="APP_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    db_type: str = Field(default="sqlite", env="DB_TYPE")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="webscraper", env="DB_NAME")
    db_user: Optional[str] = Field(default=None, env="DB_USER")
    db_password: Optional[str] = Field(default=None, env="DB_PASSWORD")
    
    # API configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    secret_key: Optional[str] = Field(default=None, env="SECRET_KEY")
    encryption_master_key: Optional[str] = Field(default=None, env="ENCRYPTION_MASTER_KEY")
    
    # AI configuration
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", env="GEMINI_MODEL")
    
    # CORS settings
    cors_allow_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        env="CORS_ORIGINS",
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=False,
        env="CORS_ALLOW_CREDENTIALS",
        description="Allow credentials in CORS requests"
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="CORS_ALLOW_METHODS",
        description="Allowed HTTP methods for CORS"
    )
    cors_allow_headers: List[str] = Field(
        default=["Content-Type", "Authorization", "X-Requested-With"],
        env="CORS_ALLOW_HEADERS",
        description="Allowed headers for CORS"
    )
    
    # Security settings
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    session_timeout_minutes: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    
    # Scraper settings
    scraper_respect_robots_txt: bool = Field(default=True, env="SCRAPER_RESPECT_ROBOTS_TXT")
    scraper_user_agents: Optional[str] = Field(default=None, env="SCRAPER_USER_AGENTS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator('cors_allow_origins', pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @validator('cors_allow_origins')
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if "*" in v:
            warnings.warn(
                "CORS allows all origins (*). This may be insecure in production!",
                UserWarning
            )
        return v
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """Validate secret key strength."""
        if not v:
            return v
        
        # Check for insecure placeholder values
        insecure_patterns = [
            'dev_secret_key',
            'change_in_production',
            'your_secure_secret_key',
            'INSECURE_DEV_KEY',
            'ai_web_scraper_secret_key_2025_development_only'
        ]
        
        for pattern in insecure_patterns:
            if pattern.lower() in v.lower():
                raise ValueError(f"Insecure secret key detected. Please generate a secure key.")
        
        if len(v) < 32:
            warnings.warn("Secret key is shorter than recommended 32 characters", UserWarning)
        
        return v
    
    @validator('gemini_api_key')
    def validate_gemini_api_key(cls, v):
        """Validate Gemini API key."""
        if not v:
            return v
        
        # Check for placeholder values
        placeholder_patterns = [
            'your_api_key_here',
            'your_gemini_api_key_here',
            'your_actual_api_key_here',
            'your_actual_gemini_api_key'
        ]
        
        for pattern in placeholder_patterns:
            if pattern.lower() in v.lower():
                raise ValueError(f"Placeholder API key detected. Please set your actual Gemini API key.")
        
        return v
    
    def get_database_url(self) -> str:
        """Build secure database URL."""
        if self.db_type.lower() == "sqlite":
            db_path = self.db_name if self.db_name.endswith('.db') else f"{self.db_name}.db"
            return f"sqlite:///{db_path}"
        
        # For production databases, require credentials
        if not self.db_user or not self.db_password:
            raise ValueError(
                f"Database credentials required for {self.db_type}. "
                "Set DB_USER and DB_PASSWORD environment variables."
            )
        
        if self.db_type.lower() == "postgresql":
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        elif self.db_type.lower() == "mysql":
            return f"mysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_user_agents(self) -> List[str]:
        """Get secure user agents list."""
        if self.scraper_user_agents:
            agents = [agent.strip() for agent in self.scraper_user_agents.split(",")]
            return [agent for agent in agents if agent]
        
        # Default secure user agents (updated regularly)
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    def validate_security_config(self) -> bool:
        """Validate that all security requirements are met."""
        errors = []
        warnings_list = []
        
        # Check for required security settings in production
        if self.is_production():
            if not self.secret_key:
                errors.append("SECRET_KEY is required in production")
            
            if not self.encryption_master_key:
                errors.append("ENCRYPTION_MASTER_KEY is required in production")
            
            if not self.gemini_api_key:
                errors.append("GEMINI_API_KEY is required in production")
            
            if self.debug:
                warnings_list.append("DEBUG is enabled in production")
        
        # Check for insecure configurations
        if "*" in self.cors_allow_origins:
            warnings_list.append("CORS allows all origins")
        
        if self.cors_allow_credentials and "*" in self.cors_allow_origins:
            errors.append("CORS allows credentials with wildcard origins (security risk)")
        
        # Check key lengths
        if self.secret_key and len(self.secret_key) < 32:
            warnings_list.append("SECRET_KEY is shorter than recommended 32 characters")
        
        if self.encryption_master_key and len(self.encryption_master_key) < 32:
            warnings_list.append("ENCRYPTION_MASTER_KEY is shorter than recommended 32 characters")
        
        # Report issues
        if errors:
            error_msg = "Security validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)
        
        if warnings_list:
            warning_msg = "Security warnings:\n" + "\n".join(f"  - {warning}" for warning in warnings_list)
            warnings.warn(warning_msg, UserWarning)
        
        return True
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        }


def get_settings() -> SecureSettings:
    """Get validated settings instance."""
    settings = SecureSettings()
    
    # Validate security configuration
    try:
        settings.validate_security_config()
    except ValueError as e:
        print(f"❌ Security validation failed: {e}")
        print("🔧 Run 'python scripts/generate_secure_keys.py' to fix security issues")
        raise
    
    return settings


# Global settings instance
settings = get_settings()