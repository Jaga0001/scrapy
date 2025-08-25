"""
Security configuration validator for the AI Web Scraper.

This module provides utilities to validate security configurations
and ensure production deployments meet security requirements.
"""

import logging
import os
import re
from typing import Dict, List, Optional

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
            settings: Application settings instance
            
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        self.errors = []
        self.warnings = []
        
        # Check environment
        if settings.environment.lower() == "production":
            self._validate_production_secrets(settings)
            self._validate_production_database(settings)
            self._validate_production_api(settings)
            self._validate_production_security(settings)
        
        return {
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    def _validate_production_secrets(self, settings):
        """Validate secret keys and API keys for production."""
        # Validate SECRET_KEY
        if not settings.secret_key or len(settings.secret_key) < 32:
            self.errors.append("SECRET_KEY must be at least 32 characters in production")
        
        # Check for weak secret patterns
        weak_patterns = [
            r"test|example|demo|change|default",
            r"^[a-z]+$|^[A-Z]+$|^\d+$",  # Only lowercase, uppercase, or digits
            r"^(.)\1{10,}",  # Repeated characters
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, settings.secret_key, re.IGNORECASE):
                self.errors.append(f"SECRET_KEY appears to be weak (matches pattern: {pattern})")
        
        # Validate Gemini API key
        if not settings.gemini_api_key:
            self.warnings.append("GEMINI_API_KEY not set - AI features will be disabled")
        elif "your_" in settings.gemini_api_key.lower() or "example" in settings.gemini_api_key.lower():
            self.errors.append("GEMINI_API_KEY appears to be a placeholder value")
    
    def _validate_production_database(self, settings):
        """Validate database configuration for production."""
        # Check for default database credentials
        if settings.db_user in ["postgres", "root", "admin", "user"]:
            self.warnings.append(f"Database user '{settings.db_user}' appears to be a default value")
        
        if settings.db_password in ["", "password", "admin", "root"]:
            self.errors.append("Database password appears to be weak or default")
        
        if settings.db_host in ["localhost", "127.0.0.1"]:
            self.warnings.append("Database host is localhost - ensure this is correct for production")
    
    def _validate_production_api(self, settings):
        """Validate API configuration for production."""
        # Check debug mode
        if settings.debug:
            self.errors.append("DEBUG mode must be disabled in production")
        
        # Check API host
        if settings.api_host == "0.0.0.0":
            self.warnings.append("API host is 0.0.0.0 - ensure proper firewall rules are in place")
    
    def _validate_production_security(self, settings):
        """Validate security settings for production."""
        # Check if running with proper security headers
        if not hasattr(settings, 'cors_origins') or not settings.cors_origins:
            self.warnings.append("CORS origins not configured - may cause security issues")
        
        # Check rate limiting
        if not hasattr(settings, 'rate_limit_per_minute'):
            self.warnings.append("Rate limiting not configured")


def validate_environment_variables() -> Dict[str, List[str]]:
    """
    Validate critical environment variables are set.
    
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    # Critical environment variables
    critical_vars = [
        "SECRET_KEY",
        "DB_PASSWORD",
    ]
    
    # Important environment variables
    important_vars = [
        "GEMINI_API_KEY",
        "REDIS_URL",
        "DATABASE_URL",
    ]
    
    # Check critical variables
    for var in critical_vars:
        if not os.getenv(var):
            errors.append(f"Critical environment variable {var} is not set")
    
    # Check important variables
    for var in important_vars:
        if not os.getenv(var):
            warnings.append(f"Important environment variable {var} is not set")
    
    return {
        "errors": errors,
        "warnings": warnings
    }


def check_file_permissions() -> Dict[str, List[str]]:
    """
    Check file permissions for security-sensitive files.
    
    Returns:
        Dictionary with permission check results
    """
    errors = []
    warnings = []
    
    # Files that should have restricted permissions
    sensitive_files = [
        ".env",
        "config/settings.py",
        "data/exports/",
    ]
    
    for file_path in sensitive_files:
        if os.path.exists(file_path):
            try:
                stat_info = os.stat(file_path)
                permissions = oct(stat_info.st_mode)[-3:]
                
                # Check if file is world-readable (last digit > 0)
                if int(permissions[-1]) > 0:
                    warnings.append(f"File {file_path} is world-readable (permissions: {permissions})")
                
                # Check if file is group-writable (middle digit >= 2)
                if int(permissions[-2]) >= 2:
                    warnings.append(f"File {file_path} is group-writable (permissions: {permissions})")
                    
            except OSError as e:
                warnings.append(f"Could not check permissions for {file_path}: {e}")
    
    return {
        "errors": errors,
        "warnings": warnings
    }


def run_security_audit(settings) -> Dict[str, any]:
    """
    Run a comprehensive security audit.
    
    Args:
        settings: Application settings instance
        
    Returns:
        Dictionary with audit results
    """
    validator = SecurityConfigValidator()
    
    # Run all validation checks
    config_results = validator.validate_production_config(settings)
    env_results = validate_environment_variables()
    file_results = check_file_permissions()
    
    # Combine results
    all_errors = config_results["errors"] + env_results["errors"] + file_results["errors"]
    all_warnings = config_results["warnings"] + env_results["warnings"] + file_results["warnings"]
    
    # Determine overall security status
    security_status = "SECURE"
    if all_errors:
        security_status = "CRITICAL_ISSUES"
    elif len(all_warnings) > 5:
        security_status = "NEEDS_ATTENTION"
    elif all_warnings:
        security_status = "MINOR_ISSUES"
    
    return {
        "status": security_status,
        "errors": all_errors,
        "warnings": all_warnings,
        "recommendations": _generate_recommendations(all_errors, all_warnings),
        "audit_timestamp": logger.info("Security audit completed")
    }


def _generate_recommendations(errors: List[str], warnings: List[str]) -> List[str]:
    """Generate security recommendations based on findings."""
    recommendations = []
    
    if any("SECRET_KEY" in error for error in errors):
        recommendations.append("Generate a new SECRET_KEY using: openssl rand -hex 32")
    
    if any("password" in error.lower() for error in errors):
        recommendations.append("Use strong, unique passwords for all database accounts")
    
    if any("DEBUG" in error for error in errors):
        recommendations.append("Set DEBUG=false in production environment")
    
    if any("API_KEY" in error for error in errors):
        recommendations.append("Obtain valid API keys from service providers")
    
    if any("permissions" in warning.lower() for warning in warnings):
        recommendations.append("Review and restrict file permissions: chmod 600 .env")
    
    if any("CORS" in warning for warning in warnings):
        recommendations.append("Configure CORS_ORIGINS to restrict API access")
    
    return recommendations