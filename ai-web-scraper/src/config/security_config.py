"""
Security configuration and settings.

This module centralizes all security-related configuration settings
and provides secure defaults for the application.
"""

import os
from typing import Dict, List, Optional
from datetime import timedelta

from pydantic import BaseSettings, Field, validator


class SecuritySettings(BaseSettings):
    """
    Security configuration settings.
    
    This class defines all security-related configuration options
    with secure defaults and validation.
    """
    
    # Encryption settings
    encryption_master_key: str = Field(
        default="",
        description="Master encryption key for data protection"
    )
    encryption_algorithm: str = Field(
        default="AES-256-GCM",
        description="Encryption algorithm to use"
    )
    
    # JWT settings
    jwt_secret_key: str = Field(
        default="change-this-in-production",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        description="Access token expiration time in minutes"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )
    
    # Password security
    password_min_length: int = Field(
        default=8,
        description="Minimum password length"
    )
    password_require_uppercase: bool = Field(
        default=True,
        description="Require uppercase letters in passwords"
    )
    password_require_lowercase: bool = Field(
        default=True,
        description="Require lowercase letters in passwords"
    )
    password_require_numbers: bool = Field(
        default=True,
        description="Require numbers in passwords"
    )
    password_require_special: bool = Field(
        default=True,
        description="Require special characters in passwords"
    )
    
    # Rate limiting
    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Maximum requests per minute per IP"
    )
    rate_limit_burst_size: int = Field(
        default=10,
        description="Burst size for rate limiting"
    )
    
    # Input validation
    max_request_size_mb: int = Field(
        default=10,
        description="Maximum request size in MB"
    )
    max_url_length: int = Field(
        default=2048,
        description="Maximum URL length"
    )
    max_header_length: int = Field(
        default=8192,
        description="Maximum header value length"
    )
    max_json_depth: int = Field(
        default=10,
        description="Maximum JSON nesting depth"
    )
    max_json_keys: int = Field(
        default=100,
        description="Maximum keys per JSON object"
    )
    
    # Session security
    session_timeout_minutes: int = Field(
        default=30,
        description="Session timeout in minutes"
    )
    session_secure_cookies: bool = Field(
        default=True,
        description="Use secure cookies for sessions"
    )
    session_httponly_cookies: bool = Field(
        default=True,
        description="Use HTTP-only cookies"
    )
    session_samesite: str = Field(
        default="strict",
        description="SameSite cookie attribute"
    )
    
    # CORS settings
    cors_allow_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods for CORS"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed headers for CORS"
    )
    
    # Content Security Policy
    csp_default_src: List[str] = Field(
        default=["'self'"],
        description="CSP default-src directive"
    )
    csp_script_src: List[str] = Field(
        default=["'self'", "'unsafe-inline'"],
        description="CSP script-src directive"
    )
    csp_style_src: List[str] = Field(
        default=["'self'", "'unsafe-inline'"],
        description="CSP style-src directive"
    )
    csp_img_src: List[str] = Field(
        default=["'self'", "data:", "https:"],
        description="CSP img-src directive"
    )
    
    # Audit logging
    audit_log_file: str = Field(
        default="logs/audit.log",
        description="Audit log file path"
    )
    audit_log_max_size_mb: int = Field(
        default=100,
        description="Maximum audit log file size in MB"
    )
    audit_log_backup_count: int = Field(
        default=5,
        description="Number of audit log backup files to keep"
    )
    audit_checksum_salt: str = Field(
        default="default_audit_salt_2024",
        description="Salt for audit log checksums"
    )
    
    # Data retention
    retention_scraped_data_days: int = Field(
        default=365,
        description="Retention period for scraped data in days"
    )
    retention_job_logs_days: int = Field(
        default=90,
        description="Retention period for job logs in days"
    )
    retention_system_metrics_days: int = Field(
        default=30,
        description="Retention period for system metrics in days"
    )
    retention_audit_logs_days: int = Field(
        default=2555,  # 7 years
        description="Retention period for audit logs in days"
    )
    retention_user_sessions_days: int = Field(
        default=30,
        description="Retention period for user sessions in days"
    )
    retention_cleanup_batch_size: int = Field(
        default=1000,
        description="Batch size for retention cleanup operations"
    )
    retention_dry_run: bool = Field(
        default=False,
        description="Run retention cleanup in dry-run mode"
    )
    
    # Secure file storage
    secure_config_file: str = Field(
        default="config/secure_config.enc",
        description="Path to encrypted configuration file"
    )
    file_upload_max_size_mb: int = Field(
        default=50,
        description="Maximum file upload size in MB"
    )
    allowed_file_extensions: List[str] = Field(
        default=[".txt", ".csv", ".json", ".xml", ".html"],
        description="Allowed file extensions for uploads"
    )
    
    # API security
    api_key_length: int = Field(
        default=32,
        description="Length of generated API keys"
    )
    api_key_expiry_days: int = Field(
        default=90,
        description="API key expiry period in days"
    )
    
    # Scraping security
    scraping_user_agents: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ],
        description="User agents for scraping rotation"
    )
    scraping_respect_robots_txt: bool = Field(
        default=True,
        description="Respect robots.txt files during scraping"
    )
    scraping_max_concurrent_requests: int = Field(
        default=10,
        description="Maximum concurrent scraping requests"
    )
    scraping_request_delay_seconds: float = Field(
        default=1.0,
        description="Delay between scraping requests in seconds"
    )
    
    # Database security
    db_connection_timeout: int = Field(
        default=30,
        description="Database connection timeout in seconds"
    )
    db_pool_size: int = Field(
        default=10,
        description="Database connection pool size"
    )
    db_max_overflow: int = Field(
        default=20,
        description="Maximum database connection overflow"
    )
    db_encrypt_sensitive_fields: bool = Field(
        default=True,
        description="Encrypt sensitive fields in database"
    )
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False
        env_file = ".env"
    
    @validator('jwt_secret_key')
    def validate_jwt_secret_key(cls, v):
        """Validate JWT secret key strength."""
        if v == "change-this-in-production":
            import warnings
            warnings.warn(
                "Using default JWT secret key. Change this in production!",
                UserWarning
            )
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v
    
    @validator('encryption_master_key')
    def validate_encryption_master_key(cls, v):
        """Validate encryption master key."""
        if not v:
            import warnings
            warnings.warn(
                "No encryption master key provided. Data encryption will use temporary key!",
                UserWarning
            )
        return v
    
    @validator('cors_allow_origins')
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if "*" in v:
            import warnings
            warnings.warn(
                "CORS allows all origins (*). This may be insecure in production!",
                UserWarning
            )
        return v
    
    def get_csp_header(self) -> str:
        """
        Generate Content Security Policy header value.
        
        Returns:
            str: CSP header value
        """
        csp_directives = [
            f"default-src {' '.join(self.csp_default_src)}",
            f"script-src {' '.join(self.csp_script_src)}",
            f"style-src {' '.join(self.csp_style_src)}",
            f"img-src {' '.join(self.csp_img_src)}",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        return "; ".join(csp_directives)
    
    def get_retention_policies(self) -> Dict[str, timedelta]:
        """
        Get data retention policies as timedelta objects.
        
        Returns:
            Dict[str, timedelta]: Retention policies by data type
        """
        return {
            "scraped_data": timedelta(days=self.retention_scraped_data_days),
            "job_logs": timedelta(days=self.retention_job_logs_days),
            "system_metrics": timedelta(days=self.retention_system_metrics_days),
            "audit_logs": timedelta(days=self.retention_audit_logs_days),
            "user_sessions": timedelta(days=self.retention_user_sessions_days)
        }
    
    def is_production(self) -> bool:
        """
        Check if running in production environment.
        
        Returns:
            bool: True if in production
        """
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    def get_security_headers(self) -> Dict[str, str]:
        """
        Get security headers for HTTP responses.
        
        Returns:
            Dict[str, str]: Security headers
        """
        return {
            "Content-Security-Policy": self.get_csp_header(),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if self.is_production() else ""
        }


# Global security settings instance
security_settings = SecuritySettings()


def get_security_settings() -> SecuritySettings:
    """
    Get the global security settings instance.
    
    Returns:
        SecuritySettings: Security settings instance
    """
    return security_settings


def validate_security_configuration() -> List[str]:
    """
    Validate security configuration and return warnings.
    
    Returns:
        List[str]: List of security warnings
    """
    warnings = []
    settings = get_security_settings()
    
    # Check for insecure defaults
    if settings.jwt_secret_key == "change-this-in-production":
        warnings.append("JWT secret key is using default value")
    
    if not settings.encryption_master_key:
        warnings.append("No encryption master key configured")
    
    if "*" in settings.cors_allow_origins:
        warnings.append("CORS allows all origins")
    
    if not settings.is_production():
        warnings.append("Running in development mode")
    
    if settings.retention_dry_run:
        warnings.append("Data retention cleanup is in dry-run mode")
    
    # Check password policy strength
    if settings.password_min_length < 8:
        warnings.append("Password minimum length is less than 8 characters")
    
    if not all([
        settings.password_require_uppercase,
        settings.password_require_lowercase,
        settings.password_require_numbers,
        settings.password_require_special
    ]):
        warnings.append("Password policy is not enforcing all character types")
    
    # Check rate limiting
    if settings.rate_limit_requests_per_minute > 1000:
        warnings.append("Rate limiting allows very high request rates")
    
    return warnings