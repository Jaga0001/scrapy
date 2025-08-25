"""
Security configuration and utilities for the web scraper.

This module provides security-focused configuration management,
credential validation, and secure defaults for scraping operations.
"""

import os
import secrets
import hashlib
from typing import Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseSettings, Field, validator


class SecuritySettings(BaseSettings):
    """Security-focused settings with environment variable support."""
    
    # API Security
    api_rate_limit_per_minute: int = Field(default=60, description="API rate limit per minute")
    api_max_request_size: int = Field(default=10485760, description="Max API request size (10MB)")
    
    # Scraping Security
    max_concurrent_requests: int = Field(default=5, description="Max concurrent requests per domain")
    min_request_delay: float = Field(default=1.0, description="Minimum delay between requests")
    max_page_size: int = Field(default=52428800, description="Max page size to scrape (50MB)")
    
    # User Agent Security
    rotate_user_agents: bool = Field(default=True, description="Enable user agent rotation")
    user_agent_pool: List[str] = Field(
        default_factory=lambda: [],
        description="Pool of user agents for rotation"
    )
    
    # Proxy Security
    validate_proxy_ssl: bool = Field(default=True, description="Validate proxy SSL certificates")
    proxy_timeout: int = Field(default=30, description="Proxy connection timeout")
    
    # Content Security
    allowed_content_types: List[str] = Field(
        default_factory=lambda: [
            "text/html", "text/plain", "application/json", 
            "application/xml", "text/xml"
        ],
        description="Allowed content types for scraping"
    )
    
    # Domain Security
    blocked_domains: List[str] = Field(
        default_factory=lambda: [],
        description="Domains to block from scraping"
    )
    
    allowed_domains: List[str] = Field(
        default_factory=lambda: [],
        description="Allowed domains for scraping (empty = all allowed)"
    )
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class CredentialManager:
    """Secure credential management utilities."""
    
    @staticmethod
    def generate_secure_key(length: int = 32) -> str:
        """Generate a cryptographically secure random key."""
        return secrets.token_hex(length)
    
    @staticmethod
    def validate_api_key(api_key: str, service_name: str) -> bool:
        """Validate API key format and strength."""
        if not api_key:
            return False
        
        # Basic length validation
        min_lengths = {
            "gemini": 32,
            "openai": 48,
            "default": 16
        }
        
        min_length = min_lengths.get(service_name.lower(), min_lengths["default"])
        if len(api_key) < min_length:
            return False
        
        # Check for obvious test/placeholder keys
        weak_patterns = [
            "test", "demo", "example", "placeholder", "your-key",
            "api-key", "change-me", "default", "sample"
        ]
        
        api_key_lower = api_key.lower()
        if any(pattern in api_key_lower for pattern in weak_patterns):
            return False
        
        return True
    
    @staticmethod
    def mask_credential(credential: str, visible_chars: int = 4) -> str:
        """Mask a credential for logging purposes."""
        if not credential or len(credential) <= visible_chars:
            return "*" * 8
        
        return credential[:visible_chars] + "*" * (len(credential) - visible_chars)
    
    @staticmethod
    def validate_database_url(db_url: str) -> tuple[bool, str]:
        """Validate database URL for security issues."""
        try:
            parsed = urlparse(db_url)
            
            # Check for missing components
            if not parsed.scheme:
                return False, "Database URL missing scheme"
            
            if not parsed.hostname:
                return False, "Database URL missing hostname"
            
            # Security checks
            if parsed.hostname in ["localhost", "127.0.0.1"] and "production" in os.getenv("ENVIRONMENT", "").lower():
                return False, "Localhost database not allowed in production"
            
            # Check for weak credentials in URL
            if parsed.username and parsed.password:
                weak_passwords = ["password", "admin", "root", "test", "123456"]
                if parsed.password.lower() in weak_passwords:
                    return False, "Weak password detected in database URL"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Invalid database URL: {str(e)}"


class DomainValidator:
    """Domain validation and security utilities."""
    
    def __init__(self, security_settings: SecuritySettings):
        self.settings = security_settings
    
    def is_domain_allowed(self, url: str) -> tuple[bool, str]:
        """Check if a domain is allowed for scraping."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check blocked domains
            if domain in [d.lower() for d in self.settings.blocked_domains]:
                return False, f"Domain {domain} is blocked"
            
            # Check allowed domains (if specified)
            if self.settings.allowed_domains:
                allowed_lower = [d.lower() for d in self.settings.allowed_domains]
                if domain not in allowed_lower:
                    return False, f"Domain {domain} not in allowed list"
            
            # Additional security checks
            if self._is_internal_domain(domain):
                return False, f"Internal domain {domain} not allowed"
            
            return True, "Domain allowed"
            
        except Exception as e:
            return False, f"Invalid URL: {str(e)}"
    
    def _is_internal_domain(self, domain: str) -> bool:
        """Check if domain is internal/private."""
        internal_patterns = [
            "localhost", "127.0.0.1", "0.0.0.0",
            "10.", "172.16.", "172.17.", "172.18.", "172.19.",
            "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
            "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
            "172.30.", "172.31.", "192.168.",
            ".local", ".internal", ".corp", ".lan"
        ]
        
        return any(pattern in domain for pattern in internal_patterns)


class SecureUserAgentManager:
    """Secure user agent management with rotation."""
    
    def __init__(self):
        self.user_agents = self._get_secure_user_agents()
        self._current_index = 0
    
    def _get_secure_user_agents(self) -> List[str]:
        """Get a list of secure, realistic user agents."""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent from the secure pool."""
        import random
        return random.choice(self.user_agents)
    
    def get_rotating_user_agent(self) -> str:
        """Get the next user agent in rotation."""
        user_agent = self.user_agents[self._current_index]
        self._current_index = (self._current_index + 1) % len(self.user_agents)
        return user_agent
    
    def get_daily_user_agent(self) -> str:
        """Get a user agent that changes daily."""
        import time
        day_seed = int(time.time() // 86400)
        index = day_seed % len(self.user_agents)
        return self.user_agents[index]


# Global instances
security_settings = SecuritySettings()
credential_manager = CredentialManager()
domain_validator = DomainValidator(security_settings)
user_agent_manager = SecureUserAgentManager()


def validate_scraping_config(config_dict: Dict) -> tuple[bool, List[str]]:
    """Validate scraping configuration for security issues."""
    errors = []
    
    # Check for hardcoded credentials
    sensitive_keys = ["password", "token", "key", "secret", "auth"]
    for key, value in config_dict.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            if isinstance(value, str) and value and not value.startswith("${"):
                errors.append(f"Potential hardcoded credential in {key}")
    
    # Check proxy configuration
    if "proxy_url" in config_dict and config_dict["proxy_url"]:
        proxy_url = config_dict["proxy_url"]
        if "@" in proxy_url and "://" in proxy_url:
            # Check for credentials in proxy URL
            try:
                parsed = urlparse(proxy_url)
                if parsed.username and parsed.password:
                    weak_passwords = ["password", "admin", "proxy", "123456"]
                    if parsed.password.lower() in weak_passwords:
                        errors.append("Weak proxy password detected")
            except:
                errors.append("Invalid proxy URL format")
    
    # Check user agent
    if "user_agent" in config_dict and config_dict["user_agent"]:
        ua = config_dict["user_agent"].lower()
        if "bot" in ua or "crawler" in ua or "scraper" in ua:
            errors.append("User agent contains bot-like keywords")
    
    return len(errors) == 0, errors


def get_secure_headers() -> Dict[str, str]:
    """Get secure HTTP headers for scraping requests."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }