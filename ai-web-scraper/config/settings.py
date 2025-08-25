"""
Application configuration management using Pydantic Settings.
"""
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = Field(default="AI Web Scraper", description="Application name")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Database
    database_url: str = Field(
        default="postgresql://localhost:5432/webscraper",
        description="PostgreSQL database URL"
    )
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="webscraper", description="Database name")
    db_user: str = Field(default="postgres", description="Database user")
    db_password: str = Field(default="", description="Database password")
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Database max overflow connections")
    db_echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # AI Configuration
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key"
    )
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    secret_key: str = Field(
        default="",
        description="JWT secret key - MUST be set via environment variable"
    )
    
    # Scraping Configuration
    max_concurrent_jobs: int = Field(default=10, description="Maximum concurrent scraping jobs")
    default_timeout: int = Field(default=30, description="Default request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # Dashboard Configuration
    dashboard_host: str = Field(default="0.0.0.0", description="Dashboard host")
    dashboard_port: int = Field(default=8501, description="Dashboard port")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """Ensure secret key is secure."""
        import os
        
        # In production, require explicit secret key
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            if not v or len(v) < 32:
                raise ValueError("SECRET_KEY must be explicitly set in production and be at least 32 characters long")
        
        # Generate secure key if not provided (development only)
        if not v or v in ["", "your-secret-key-change-in-production", "change-me"]:
            if cls.__name__ == "Settings":  # Only auto-generate for main settings
                if os.getenv("SECRET_KEY"):
                    return os.getenv("SECRET_KEY")
                # Auto-generate secure key for development only
                if os.getenv("ENVIRONMENT", "development").lower() != "production":
                    return secrets.token_hex(32)
                else:
                    raise ValueError("SECRET_KEY must be explicitly set in production")
        
        # Validate provided key
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        
        # Check for common weak keys
        weak_keys = [
            "your-secret-key", "secret", "password", "key", "token",
            "development", "test", "admin", "default", "changeme", "example"
        ]
        if any(weak in v.lower() for weak in weak_keys):
            raise ValueError("SECRET_KEY appears to be a weak or default value")
        
        # Ensure key has sufficient entropy
        if v == v.lower() or v == v.upper() or v.isdigit() or v.isalpha():
            raise ValueError("SECRET_KEY must contain mixed case letters, numbers, and special characters")
        
        return v
    
    @validator('database_url')
    def validate_database_url(cls, v):
        """Ensure database URL doesn't contain hardcoded credentials."""
        if "user:password" in v:
            raise ValueError("Database URL should not contain hardcoded credentials")
        return v
    
    @validator('gemini_api_key')
    def validate_gemini_api_key(cls, v):
        """Ensure Gemini API key is provided for production."""
        import os
        
        # In production, warn if API key is not set
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            if not v:
                import logging
                logging.getLogger(__name__).warning(
                    "GEMINI_API_KEY not set in production - AI features will be disabled"
                )
            elif any(placeholder in str(v).lower() for placeholder in ["your_", "example", "test", "demo"]):
                raise ValueError("GEMINI_API_KEY appears to be a placeholder value")
        
        return v
    
    def validate_security_config(self):
        """Validate security configuration after initialization."""
        from config.security_validator import SecurityConfigValidator
        
        validator = SecurityConfigValidator()
        results = validator.validate_production_config(self)
        
        if results["errors"]:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Security configuration errors found:")
            for error in results["errors"]:
                logger.error(f"  - {error}")
            
            if self.environment.lower() == "production":
                raise ValueError(f"Security configuration errors in production: {results['errors']}")
        
        if results["warnings"]:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Security configuration warnings:")
            for warning in results["warnings"]:
                logger.warning(f"  - {warning}")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings