"""
Secure database configuration with credential protection.
"""

import os
import logging
from typing import Optional
from urllib.parse import quote_plus
from pydantic import Field, validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class SecureDatabaseSettings(BaseSettings):
    """Secure database settings with credential protection."""
    
    # Use full DATABASE_URL for production
    database_url: Optional[str] = Field(
        default=None,
        description="Complete database URL (preferred for production)"
    )
    
    # Individual components for development
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="webscraper")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="")
    
    @validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format and security."""
        if v:
            # Ensure no credentials in plain text logs
            if any(keyword in v.lower() for keyword in ['password=', 'pwd=']):
                logger.warning("Database URL contains credentials - ensure proper logging configuration")
        return v
    
    def get_secure_database_url(self) -> str:
        """Get database URL with proper credential encoding."""
        if self.database_url:
            return self.database_url
        
        # URL-encode credentials to handle special characters
        encoded_user = quote_plus(self.db_user)
        encoded_password = quote_plus(self.db_password)
        
        return (
            f"postgresql://{encoded_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    def get_async_database_url(self) -> str:
        """Get async database URL with proper credential encoding."""
        base_url = self.get_secure_database_url()
        return base_url.replace("postgresql://", "postgresql+asyncpg://")
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False
        # Don't expose sensitive fields in repr
        fields = {
            'db_password': {'repr': False},
            'database_url': {'repr': False}
        }