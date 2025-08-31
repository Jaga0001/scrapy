"""
Security configuration utilities for AI Web Scraper.
Provides secure defaults and configuration validation.
"""

import os
import secrets
import string
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration manager with secure defaults."""
    
    @staticmethod
    def get_secure_secret_key() -> str:
        """Get or generate a secure secret key."""
        secret_key = os.getenv("SECRET_KEY")
        
        if not secret_key or len(secret_key) < 32:
            logger.warning("SECRET_KEY not found or too short. Using generated key for this session.")
            # Generate a secure key for this session
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(64))
        
        return secret_key
    
    @staticmethod
    def get_encryption_key() -> str:
        """Get or generate a secure encryption key."""
        encryption_key = os.getenv("ENCRYPTION_MASTER_KEY")
        
        if not encryption_key or len(encryption_key) < 32:
            logger.warning("ENCRYPTION_MASTER_KEY not found or too short. Using generated key for this session.")
            return secrets.token_urlsafe(32)
        
        return encryption_key
    
    @staticmethod
    def get_secure_user_agents() -> List[str]:
        """Get secure user agents from environment or generate generic ones."""
        user_agents_env = os.getenv("SCRAPER_USER_AGENTS", "")
        
        if user_agents_env:
            agents = [ua.strip() for ua in user_agents_env.split(",") if ua.strip()]
            if agents:
                return agents
        
        # Return generic, non-identifying user agents
        return [
            'Mozilla/5.0 (compatible; WebScraper/1.0; +http://example.com/bot)',
            'Mozilla/5.0 (compatible; DataCollector/1.0)',
            'Mozilla/5.0 (compatible; ContentAnalyzer/1.0)'
        ]
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get CORS origins with secure defaults."""
        cors_origins = os.getenv("CORS_ORIGINS", "")
        
        if cors_origins:
            origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
            # Validate origins
            valid_origins = []
            for origin in origins:
                try:
                    parsed = urlparse(origin)
                    if parsed.scheme in ['http', 'https'] and parsed.netloc:
                        valid_origins.append(origin)
                    else:
                        logger.warning(f"Invalid CORS origin: {origin}")
                except Exception as e:
                    logger.warning(f"Error parsing CORS origin {origin}: {e}")
            
            return valid_origins if valid_origins else ["http://localhost:8501"]
        
        return ["http://localhost:8501"]
    
    @staticmethod
    def get_api_base_url() -> str:
        """Get API base URL with secure configuration."""
        # Check for explicit API_BASE_URL first
        api_base = os.getenv("API_BASE_URL")
        if api_base:
            return api_base
        
        # Build from components
        protocol = os.getenv("API_PROTOCOL", "http")
        host = os.getenv("API_HOST", "localhost")
        port = os.getenv("API_PORT", "8000")
        
        # Validate protocol
        if protocol not in ['http', 'https']:
            logger.warning(f"Invalid API_PROTOCOL: {protocol}. Using 'http'")
            protocol = 'http'
        
        return f"{protocol}://{host}:{port}/api/v1"
    
    @staticmethod
    def get_scraper_config() -> Dict[str, Any]:
        """Get scraper configuration with secure defaults."""
        return {
            'respect_robots_txt': os.getenv("SCRAPER_RESPECT_ROBOTS_TXT", "true").lower() == "true",
            'delay_min': int(os.getenv("SCRAPER_DELAY_MIN", "1")),
            'delay_max': int(os.getenv("SCRAPER_DELAY_MAX", "3")),
            'timeout': int(os.getenv("SCRAPER_TIMEOUT", "10")),
            'max_retries': int(os.getenv("SCRAPER_MAX_RETRIES", "3")),
            'user_agents': SecurityConfig.get_secure_user_agents()
        }
    
    @staticmethod
    def validate_environment() -> Dict[str, List[str]]:
        """Validate environment configuration for security issues."""
        issues = {
            'critical': [],
            'warnings': [],
            'info': []
        }
        
        # Check for placeholder values and insecure defaults
        insecure_patterns = [
            'your_api_key_here',
            'your_gemini_api_key_here',
            'your_actual_gemini_api_key_here',
            'dev_secret_key',
            'change_in_production',
            'change_prod',
            'generate_secure_key_using_script',
            'generate_user_agents_using_script',
            'insecure_dev_key',
            'replace_in_production',
            'development_only'
        ]
        
        # Check all environment variables for security issues
        for key, value in os.environ.items():
            if key.startswith(('SECRET_', 'API_KEY', 'PASSWORD', 'TOKEN', 'GEMINI_API_KEY', 'ENCRYPTION_')):
                # Check for placeholder patterns
                for pattern in insecure_patterns:
                    if pattern.lower() in value.lower():
                        issues['critical'].append(f"{key} contains insecure placeholder: '{pattern}'")
                
                # Check key length
                if len(value) < 16:
                    issues['critical'].append(f"{key} is too short for security (minimum 16 characters)")
                elif len(value) < 32:
                    issues['warnings'].append(f"{key} should be at least 32 characters for better security")
        
        # Check CORS configuration
        cors_origins = SecurityConfig.get_cors_origins()
        if "*" in cors_origins:
            issues['critical'].append("CORS allows all origins (*) - major security risk")
        
        # Check for localhost/development URLs in production
        if SecurityConfig.is_production():
            api_base = os.getenv("API_BASE_URL", "")
            if "localhost" in api_base or "127.0.0.1" in api_base:
                issues['critical'].append("Production environment using localhost URLs")
            
            for origin in cors_origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    issues['warnings'].append(f"Production CORS includes localhost: {origin}")
        
        # Check debug mode
        if os.getenv("DEBUG", "false").lower() == "true":
            if SecurityConfig.is_production():
                issues['critical'].append("DEBUG mode enabled in production environment")
            else:
                issues['warnings'].append("DEBUG mode is enabled")
        
        # Check API host binding
        api_host = os.getenv("API_HOST", "localhost")
        if api_host == "0.0.0.0":
            issues['warnings'].append("API bound to 0.0.0.0 - ensure proper firewall/proxy protection")
        
        # Check for HTTPS enforcement
        api_base = os.getenv("API_BASE_URL", "")
        if SecurityConfig.is_production() and api_base.startswith("http://"):
            issues['critical'].append("Production environment not using HTTPS")
        
        # Check user agents for identifying information
        user_agents = os.getenv("SCRAPER_USER_AGENTS", "")
        if "Chrome/" in user_agents and "Safari/" in user_agents:
            # Check if using specific version numbers that could be fingerprinted
            import re
            if re.search(r'Chrome/\d{3}\.\d+\.\d+\.\d+', user_agents):
                issues['info'].append("User agents contain specific version numbers - consider using generic agents")
        
        return issues
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @staticmethod
    def get_rate_limit_config() -> Dict[str, int]:
        """Get rate limiting configuration."""
        return {
            'requests': int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            'window': int(os.getenv("RATE_LIMIT_WINDOW", "3600"))
        }

def validate_security_on_startup():
    """Validate security configuration on application startup."""
    issues = SecurityConfig.validate_environment()
    
    if issues['critical']:
        logger.error("Critical security issues found:")
        for issue in issues['critical']:
            logger.error(f"  - {issue}")
        
        if SecurityConfig.is_production():
            raise RuntimeError("Critical security issues found in production environment")
    
    if issues['warnings']:
        logger.warning("Security warnings:")
        for warning in issues['warnings']:
            logger.warning(f"  - {warning}")
    
    logger.info("Security configuration validation completed")