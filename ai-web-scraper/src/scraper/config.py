"""
Scraping configuration management module.

This module provides configuration management for scraping operations,
including validation, defaults, and environment-based settings.
"""

import os
from typing import Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from ..models.pydantic_models import ScrapingConfig


class ScrapingSettings(BaseSettings):
    """Environment-based scraping settings."""
    
    # Default browser settings
    default_headless: bool = Field(default=True, description="Default headless mode")
    default_stealth: bool = Field(default=True, description="Default stealth mode")
    default_timeout: int = Field(default=30, ge=5, le=300, description="Default timeout")
    default_wait_time: int = Field(default=5, ge=1, le=60, description="Default wait time")
    
    # Rate limiting defaults
    default_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Default delay between requests")
    max_concurrent_jobs: int = Field(default=10, ge=1, le=100, description="Maximum concurrent scraping jobs")
    
    # Browser executable paths
    chrome_binary_path: Optional[str] = Field(default=None, description="Path to Chrome binary")
    firefox_binary_path: Optional[str] = Field(default=None, description="Path to Firefox binary")
    
    # Proxy settings
    default_proxy_url: Optional[str] = Field(default=None, description="Default proxy URL")
    proxy_rotation_enabled: bool = Field(default=False, description="Enable proxy rotation")
    
    # User agent settings
    user_agent_rotation: bool = Field(default=True, description="Enable user agent rotation")
    custom_user_agents: List[str] = Field(
        default_factory=lambda: [],  # Load from environment or use secure defaults
        description="List of user agents for rotation"
    )
    default_user_agent: Optional[str] = Field(
        default=None, 
        description="Default user agent - should be set via SCRAPER_DEFAULT_USER_AGENT env var"
    )
    
    # Security settings
    validate_ssl: bool = Field(default=True, description="Validate SSL certificates")
    allow_redirects: bool = Field(default=True, description="Allow HTTP redirects")
    max_redirects: int = Field(default=5, description="Maximum number of redirects to follow")
    
    # Security settings
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt by default")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    
    class Config:
        env_prefix = "SCRAPER_"
        case_sensitive = False


class ConfigManager:
    """Manages scraping configurations with validation and defaults."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.settings = ScrapingSettings()
        self._default_config = None
    
    def get_default_config(self) -> ScrapingConfig:
        """Get the default scraping configuration."""
        if self._default_config is None:
            self._default_config = ScrapingConfig(
                wait_time=self.settings.default_wait_time,
                max_retries=self.settings.max_retries,
                timeout=self.settings.default_timeout,
                use_stealth=self.settings.default_stealth,
                headless=self.settings.default_headless,
                delay_between_requests=self.settings.default_delay,
                respect_robots_txt=self.settings.respect_robots_txt,
                proxy_url=self.settings.default_proxy_url
            )
        return self._default_config.model_copy()
    
    def create_config(
        self,
        url: str,
        custom_settings: Optional[Dict] = None,
        **kwargs
    ) -> ScrapingConfig:
        """
        Create a scraping configuration with custom settings.
        
        Args:
            url: Target URL for scraping
            custom_settings: Dictionary of custom configuration settings
            **kwargs: Additional configuration parameters
            
        Returns:
            ScrapingConfig: Validated scraping configuration
        """
        # Start with default configuration
        config_data = self.get_default_config().model_dump()
        
        # Apply custom settings
        if custom_settings:
            config_data.update(custom_settings)
        
        # Apply keyword arguments
        config_data.update(kwargs)
        
        # Create and validate configuration
        config = ScrapingConfig(**config_data)
        
        # Apply URL-specific optimizations
        config = self._optimize_for_url(config, url)
        
        return config
    
    def _optimize_for_url(self, config: ScrapingConfig, url: str) -> ScrapingConfig:
        """
        Optimize configuration based on the target URL.
        
        Args:
            config: Base configuration
            url: Target URL
            
        Returns:
            ScrapingConfig: Optimized configuration
        """
        # Create a copy to avoid modifying the original
        optimized_data = config.model_dump()
        
        # Apply domain-specific optimizations
        if "amazon.com" in url.lower():
            # Amazon requires longer wait times and stealth mode
            optimized_data.update({
                "wait_time": max(config.wait_time, 8),
                "use_stealth": True,
                "delay_between_requests": max(config.delay_between_requests, 2.0),
                "javascript_enabled": True
            })
        elif "linkedin.com" in url.lower():
            # LinkedIn has strict anti-bot measures
            optimized_data.update({
                "use_stealth": True,
                "delay_between_requests": max(config.delay_between_requests, 3.0),
                "max_retries": min(config.max_retries, 2)
            })
        elif "twitter.com" in url.lower() or "x.com" in url.lower():
            # Twitter/X requires JavaScript and longer waits
            optimized_data.update({
                "javascript_enabled": True,
                "wait_time": max(config.wait_time, 10),
                "use_stealth": True
            })
        
        return ScrapingConfig(**optimized_data)
    
    def validate_config(self, config: ScrapingConfig) -> tuple[bool, List[str]]:
        """
        Validate a scraping configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Pydantic validation
            config.model_validate(config.model_dump())
        except Exception as e:
            errors.append(f"Pydantic validation error: {str(e)}")
        
        # Custom validation rules
        if config.max_depth > 3 and config.follow_links:
            errors.append("max_depth should not exceed 3 when follow_links is enabled")
        
        if config.delay_between_requests < 0.5 and not config.use_stealth:
            errors.append("delay_between_requests should be at least 0.5 seconds without stealth mode")
        
        if config.timeout < config.wait_time:
            errors.append("timeout should be greater than wait_time")
        
        return len(errors) == 0, errors
    
    def get_user_agent(self, config: ScrapingConfig) -> str:
        """
        Get an appropriate user agent for the configuration.
        
        Args:
            config: Scraping configuration
            
        Returns:
            str: User agent string
        """
        if config.user_agent:
            return config.user_agent
        
        if self.settings.user_agent_rotation and self.settings.custom_user_agents:
            import random
            return random.choice(self.settings.custom_user_agents)
        
        # Default user agent from environment or secure fallback
        if self.settings.default_user_agent:
            return self.settings.default_user_agent
        
        return self.settings.custom_user_agents[0] if self.settings.custom_user_agents else \
               self._get_secure_default_user_agent()
    
    def _get_secure_default_user_agent(self) -> str:
        """Get a secure default user agent that rotates based on system time."""
        import hashlib
        import time
        
        # Rotate user agent daily to avoid detection
        day_seed = int(time.time() // 86400)  # Changes every 24 hours
        
        secure_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]
        
        # Select user agent based on day seed for consistent daily rotation
        index = day_seed % len(secure_user_agents)
        return secure_user_agents[index]
    
    def update_settings(self, **kwargs) -> None:
        """
        Update global scraping settings.
        
        Args:
            **kwargs: Settings to update
        """
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        
        # Reset default config to pick up new settings
        self._default_config = None


# Global configuration manager instance
config_manager = ConfigManager()