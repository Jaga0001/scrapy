"""
Security configuration validator for the web scraper application.

This module provides validation for security-sensitive configuration
to prevent common security misconfigurations.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SecurityConfigValidator:
    """Validates security configuration settings."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_production_config(self, settings) -> Dict[str, List[str]]:
        """
        Validate configuration for production deployment.
        
        Args:
            settings: Application settings object
            
        Returns:
            Dict containing 'errors' and 'warnings' lists
        """
        self.errors = []
        self.warnings = []
        
        # Validate secret key
        self._validate_secret_key(settings.secret_key)
        
        # Validate API keys
        self._validate_gemini_api_key(getattr(settings, 'gemini_api_key', None))
        
        # Validate database configuration
        self._validate_database_config(settings)
        
        # Validate environment settings
        self._validate_environment_settings(settings)
        
        # Validate security headers and CORS
        self._validate_security_headers(settings)
        
        return {
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    def _validate_secret_key(self, secret_key: str) -> None:
        """Validate JWT secret key security."""
        if not secret_key:
            self.errors.append("SECRET_KEY is not set")
            return
        
        # Check length
        if len(secret_key) < 32:
            self.errors.append("SECRET_KEY must be at least 32 characters long")
        
        # Check for weak patterns
        weak_patterns = [
            "secret", "password", "key", "token", "admin", "test", "demo",
            "development", "example", "changeme", "change_me", "your_"
        ]
        
        if any(pattern in secret_key.lower() for pattern in weak_patterns):
            self.errors.append("SECRET_KEY appears to contain weak or placeholder text")
        
        # Check entropy
        if secret_key == secret_key.lower() or secret_key == secret_key.upper():
            self.warnings.append("SECRET_KEY should contain mixed case characters")
        
        if secret_key.isdigit() or secret_key.isalpha():
            self.warnings.append("SECRET_KEY should contain mixed character types")
        
        # Check for common weak keys
        common_weak_keys = [
            "your-secret-key-change-in-production",
            "change-me",
            "secret-key",
            "jwt-secret",
            "development-key"
        ]
        
        if secret_key.lower() in [key.lower() for key in common_weak_keys]:
            self.errors.append("SECRET_KEY is using a known weak default value")
    
    def _validate_gemini_api_key(self, api_key: Optional[str]) -> None:
        """Validate Gemini API key."""
        if not api_key:
            self.warnings.append("GEMINI_API_KEY is not set - AI features will be disabled")
            return
        
        # Check for placeholder values
        placeholder_patterns = [
            "your_", "example", "test", "demo", "change_me", "placeholder",
            "api_key_here", "insert_", "replace_"
        ]
        
        if any(pattern in api_key.lower() for pattern in placeholder_patterns):
            self.errors.append("GEMINI_API_KEY appears to be a placeholder value")
        
        # Validate Google API key format
        if not api_key.startswith('AIza'):
            self.warnings.append("GEMINI_API_KEY does not match expected Google API key format")
        
        if len(api_key) != 39:
            self.warnings.append("GEMINI_API_KEY length does not match expected Google API key length")
        
        # Check for valid character set
        if not re.match(r'^AIza[0-9A-Za-z_-]{35}$', api_key):
            self.warnings.append("GEMINI_API_KEY contains invalid characters for Google API key")
    
    def _validate_database_config(self, settings) -> None:
        """Validate database configuration security."""
        # Check for hardcoded credentials in URL
        if hasattr(settings, 'database_url') and settings.database_url:
            if "user:password" in settings.database_url.lower():
                self.errors.append("Database URL contains hardcoded credentials")
        
        # Validate individual database settings
        if hasattr(settings, 'db_password') and settings.db_password:
            password = settings.db_password
            if isinstance(password, str):
                self._validate_database_password(password)
        
        # Check SSL mode
        if hasattr(settings, 'db_ssl_mode'):
            if not settings.db_ssl_mode or settings.db_ssl_mode == 'disable':
                self.warnings.append("Database SSL is disabled - consider enabling for production")
    
    def _validate_database_password(self, password: str) -> None:
        """Validate database password strength."""
        if len(password) < 12:
            self.warnings.append("Database password should be at least 12 characters long")
        
        weak_passwords = [
            "password", "admin", "root", "postgres", "user", "test",
            "123456", "password123", "admin123"
        ]
        
        if password.lower() in weak_passwords:
            self.errors.append("Database password is too weak")
        
        # Check character diversity
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            self.warnings.append("Database password should contain uppercase, lowercase, digits, and special characters")
    
    def _validate_environment_settings(self, settings) -> None:
        """Validate environment-specific settings."""
        if hasattr(settings, 'environment'):
            env = settings.environment.lower()
            
            if env == 'production':
                # Production-specific validations
                if hasattr(settings, 'debug') and settings.debug:
                    self.errors.append("DEBUG mode should be disabled in production")
                
                if hasattr(settings, 'log_level') and settings.log_level.upper() == 'DEBUG':
                    self.warnings.append("DEBUG log level in production may expose sensitive information")
        
        # Check for development settings in production
        if os.getenv('ENVIRONMENT', '').lower() == 'production':
            dev_indicators = ['localhost', '127.0.0.1', 'test', 'dev', 'development']
            
            for attr_name in ['api_host', 'db_host', 'redis_host']:
                if hasattr(settings, attr_name):
                    value = getattr(settings, attr_name, '')
                    if any(indicator in str(value).lower() for indicator in dev_indicators):
                        self.warnings.append(f"{attr_name} appears to use development values in production")
    
    def _validate_security_headers(self, settings) -> None:
        """Validate security headers and CORS configuration."""
        # Check CORS origins
        if hasattr(settings, 'cors_origins'):
            cors_origins = getattr(settings, 'cors_origins', '')
            if isinstance(cors_origins, str):
                origins = [origin.strip() for origin in cors_origins.split(',')]
                
                for origin in origins:
                    if origin == '*':
                        self.errors.append("CORS origins should not use wildcard (*) in production")
                    elif origin.startswith('http://') and not origin.startswith('http://localhost'):
                        self.warnings.append(f"CORS origin {origin} uses HTTP instead of HTTPS")
        
        # Check allowed hosts
        if hasattr(settings, 'allowed_hosts'):
            allowed_hosts = getattr(settings, 'allowed_hosts', '')
            if isinstance(allowed_hosts, str):
                hosts = [host.strip() for host in allowed_hosts.split(',')]
                
                if '*' in hosts:
                    self.errors.append("ALLOWED_HOSTS should not use wildcard (*) in production")
    
    def validate_proxy_configuration(self, proxy_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate proxy configuration for security issues.
        
        Args:
            proxy_config: Dictionary containing proxy configuration
            
        Returns:
            Dict containing 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        proxy_url = proxy_config.get('proxy_url', '')
        if proxy_url:
            parsed = urlparse(proxy_url)
            
            # Check for credentials in URL
            if parsed.username or parsed.password:
                warnings.append("Proxy credentials in URL may be logged - consider using separate auth fields")
            
            # Check protocol security
            if parsed.scheme == 'http':
                warnings.append("HTTP proxy may transmit credentials in plain text - consider HTTPS")
            
            # Validate proxy host
            if parsed.hostname in ['localhost', '127.0.0.1']:
                warnings.append("Proxy configuration points to localhost")
        
        return {"errors": errors, "warnings": warnings}
    
    def validate_user_agent_configuration(self, user_agents: List[str]) -> Dict[str, List[str]]:
        """
        Validate user agent configuration for security and privacy.
        
        Args:
            user_agents: List of user agent strings
            
        Returns:
            Dict containing 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        for ua in user_agents:
            # Check for system-specific information
            system_indicators = [
                'Windows NT 10.0', 'Windows NT 6.1', 'Mac OS X', 'Ubuntu',
                'Intel Mac OS X', 'Win64; x64', 'WOW64'
            ]
            
            if any(indicator in ua for indicator in system_indicators):
                warnings.append(f"User agent contains system-specific information: {ua[:50]}...")
            
            # Check for browser version specificity
            version_patterns = [
                r'Chrome/\d+\.\d+\.\d+\.\d+',
                r'Firefox/\d+\.\d+',
                r'Safari/\d+\.\d+'
            ]
            
            if any(re.search(pattern, ua) for pattern in version_patterns):
                warnings.append("User agent contains specific browser version that may aid fingerprinting")
            
            # Recommend generic user agents
            if not any(generic in ua for generic in ['compatible', 'Bot', 'Crawler', 'Scraper']):
                warnings.append("Consider using generic user agents to reduce fingerprinting")
        
        return {"errors": errors, "warnings": warnings}


def validate_environment_file(env_file_path: str = '.env') -> Dict[str, List[str]]:
    """
    Validate .env file for security issues.
    
    Args:
        env_file_path: Path to the .env file
        
    Returns:
        Dict containing 'errors' and 'warnings' lists
    """
    errors = []
    warnings = []
    
    if not os.path.exists(env_file_path):
        warnings.append(f"Environment file {env_file_path} not found")
        return {"errors": errors, "warnings": warnings}
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for weak secret keys
        if "your-secret-key-change-in-production" in content:
            errors.append("Default secret key found in .env - generate a secure key")
        
        # Check for placeholder values
        placeholder_patterns = [
            "your_gemini_api_key_here",
            "your_db_password",
            "change_me",
            "placeholder",
            "example.com"
        ]
        
        for pattern in placeholder_patterns:
            if pattern in content.lower():
                errors.append(f"Placeholder value '{pattern}' found in .env file")
        
        # Check for hardcoded credentials
        if "user:password" in content:
            errors.append("Hardcoded database credentials found in .env")
        
        # Check for HTTP URLs in production settings
        if "ENVIRONMENT=production" in content and "http://" in content:
            warnings.append("HTTP URLs found in production environment file")
        
        # Check file permissions (Unix-like systems)
        if hasattr(os, 'stat'):
            import stat
            file_stat = os.stat(env_file_path)
            file_mode = stat.filemode(file_stat.st_mode)
            
            # Check if file is readable by others
            if file_stat.st_mode & stat.S_IROTH:
                warnings.append(f".env file is readable by others - consider restricting permissions")
            
            if file_stat.st_mode & stat.S_IWOTH:
                errors.append(f".env file is writable by others - this is a security risk")
    
    except Exception as e:
        errors.append(f"Failed to validate .env file: {e}")
    
    return {"errors": errors, "warnings": warnings}


if __name__ == "__main__":
    # Example usage
    validator = SecurityConfigValidator()
    
    # Validate .env file
    env_results = validate_environment_file()
    
    print("Environment File Validation Results:")
    print("Errors:", env_results["errors"])
    print("Warnings:", env_results["warnings"])