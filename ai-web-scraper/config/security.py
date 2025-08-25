"""
Security configuration and utilities for the web scraper.
"""

import secrets
import hashlib
import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class SecuritySettings(BaseSettings):
    """Security-focused configuration settings."""
    
    # API Security
    secret_key: str = Field(
        default="",
        description="JWT secret key - MUST be set via environment variable"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expire_minutes: int = Field(default=30, description="JWT token expiration")
    
    # CORS and Host Security
    allowed_hosts: List[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"],
        description="Allowed host headers"
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8501"],
        description="Allowed CORS origins"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, description="API rate limit per minute")
    
    # Scraping Security
    user_agent_rotation: bool = Field(default=True, description="Enable user agent rotation")
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt")
    max_concurrent_requests: int = Field(default=10, description="Max concurrent requests")
    
    # Data Security
    encrypt_stored_data: bool = Field(default=False, description="Encrypt scraped data at rest")
    data_retention_days: int = Field(default=30, description="Data retention period in days")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """Validate JWT secret key security."""
        if not v:
            # Generate a secure key if none provided (development only)
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                return secrets.token_hex(32)
            raise ValueError("SECRET_KEY must be set in production")
        
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        
        # Check for common weak keys
        weak_keys = [
            "your-secret-key",
            "change-me",
            "secret",
            "password",
            "12345",
            "generate-a-strong-secret-key-here"
        ]
        if v.lower() in [key.lower() for key in weak_keys]:
            raise ValueError("SECRET_KEY appears to be a default/weak value")
        
        return v
    
    @validator('allowed_hosts')
    def validate_allowed_hosts(cls, v):
        """Validate allowed hosts configuration."""
        if not v:
            raise ValueError("At least one allowed host must be specified")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Don't expose secret key in repr
        fields = {
            'secret_key': {'repr': False}
        }


def generate_secure_key() -> str:
    """Generate a cryptographically secure key."""
    return secrets.token_hex(32)


def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
    """Hash sensitive data with optional salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Use SHA-256 with salt
    hash_input = f"{salt}{data}".encode('utf-8')
    return hashlib.sha256(hash_input).hexdigest()


def validate_api_key_format(api_key: str, service: str) -> bool:
    """Validate API key format for different services."""
    patterns = {
        'gemini': lambda k: k.startswith('AIza') and len(k) == 39,
        'openai': lambda k: k.startswith('sk-') and len(k) >= 48,
        'anthropic': lambda k: k.startswith('sk-ant-') and len(k) >= 50,
    }
    
    validator_func = patterns.get(service.lower())
    if validator_func:
        return validator_func(api_key)
    
    # Generic validation - at least 20 characters
    return len(api_key) >= 20


class SecureUserAgentManager:
    """Manage user agents securely without exposing system information."""
    
    SAFE_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """Get a random safe user agent."""
        return secrets.choice(cls.SAFE_USER_AGENTS)
    
    @classmethod
    def is_safe_user_agent(cls, user_agent: str) -> bool:
        """Check if user agent doesn't expose sensitive system information."""
        # Check for potentially sensitive information
        sensitive_patterns = [
            'python-requests',
            'urllib',
            'scrapy',
            'selenium',
            'bot',
            'crawler',
            'spider'
        ]
        
        user_agent_lower = user_agent.lower()
        return not any(pattern in user_agent_lower for pattern in sensitive_patterns)


# Global security settings instance
security_settings = SecuritySettings()