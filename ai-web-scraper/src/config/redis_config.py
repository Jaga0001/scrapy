"""
Secure Redis configuration management for the web scraper.

This module provides secure Redis configuration with credential protection,
SSL/TLS support, and connection pooling for production environments.
"""

import os
from typing import Optional
from pydantic import BaseSettings, SecretStr, Field, validator


class RedisSettings(BaseSettings):
    """
    Secure Redis configuration with credential protection.
    
    This class manages Redis connection settings with proper credential
    handling and validation for production environments.
    """
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    db: int = Field(default=0, ge=0, description="Redis database number")
    username: Optional[str] = Field(default=None, description="Redis username")
    password: Optional[SecretStr] = Field(default=None, description="Redis password")
    ssl: bool = Field(default=False, description="Use SSL/TLS connection")
    ssl_cert_reqs: str = Field(default="required", description="SSL certificate requirements")
    ssl_ca_certs: Optional[str] = Field(default=None, description="Path to CA certificates")
    ssl_certfile: Optional[str] = Field(default=None, description="Path to client certificate")
    ssl_keyfile: Optional[str] = Field(default=None, description="Path to client private key")
    
    # Connection settings
    connection_timeout: int = Field(default=30, ge=1, description="Connection timeout in seconds")
    socket_timeout: int = Field(default=30, ge=1, description="Socket timeout in seconds")
    socket_keepalive: bool = Field(default=True, description="Enable socket keepalive")
    max_connections: int = Field(default=20, ge=1, description="Maximum connections in pool")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    health_check_interval: int = Field(default=30, ge=0, description="Health check interval in seconds")
    
    class Config:
        env_prefix = "REDIS_"
        case_sensitive = False
        
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate Redis password strength."""
        if v is not None:
            password_value = v.get_secret_value()
            if len(password_value) < 12:
                raise ValueError("Redis password must be at least 12 characters long")
            if password_value.lower() in ['password', 'redis', 'admin', 'root']:
                raise ValueError("Redis password cannot be a common weak password")
        return v
    
    @validator('ssl_cert_reqs')
    def validate_ssl_cert_reqs(cls, v):
        """Validate SSL certificate requirements."""
        valid_values = ['none', 'optional', 'required']
        if v.lower() not in valid_values:
            raise ValueError(f"ssl_cert_reqs must be one of: {valid_values}")
        return v.lower()
    
    @property
    def connection_url(self) -> str:
        """
        Build Redis connection URL with credentials.
        
        Returns:
            str: Complete Redis connection URL
        """
        scheme = "rediss" if self.ssl else "redis"
        
        # Build authentication part
        if self.username and self.password:
            password_value = self.password.get_secret_value()
            auth = f"{self.username}:{password_value}@"
        elif self.password:
            password_value = self.password.get_secret_value()
            auth = f":{password_value}@"
        else:
            auth = ""
        
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"
    
    @property
    def safe_connection_info(self) -> str:
        """
        Get connection info safe for logging (without credentials).
        
        Returns:
            str: Safe connection info for logging
        """
        scheme = "rediss" if self.ssl else "redis"
        auth_info = f"user:{self.username}" if self.username else "no-auth"
        return f"{scheme}://{auth_info}@{self.host}:{self.port}/{self.db}"
    
    def get_connection_kwargs(self) -> dict:
        """
        Get Redis connection keyword arguments.
        
        Returns:
            dict: Connection parameters for redis.Redis()
        """
        kwargs = {
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'socket_connect_timeout': self.connection_timeout,
            'socket_timeout': self.socket_timeout,
            'socket_keepalive': self.socket_keepalive,
            'retry_on_timeout': self.retry_on_timeout,
            'health_check_interval': self.health_check_interval,
            'decode_responses': True
        }
        
        # Add authentication if provided
        if self.username:
            kwargs['username'] = self.username
        if self.password:
            kwargs['password'] = self.password.get_secret_value()
        
        # Add SSL configuration if enabled
        if self.ssl:
            kwargs['ssl'] = True
            kwargs['ssl_cert_reqs'] = self.ssl_cert_reqs
            
            if self.ssl_ca_certs:
                kwargs['ssl_ca_certs'] = self.ssl_ca_certs
            if self.ssl_certfile:
                kwargs['ssl_certfile'] = self.ssl_certfile
            if self.ssl_keyfile:
                kwargs['ssl_keyfile'] = self.ssl_keyfile
        
        return kwargs
    
    def get_connection_pool_kwargs(self) -> dict:
        """
        Get Redis connection pool keyword arguments.
        
        Returns:
            dict: Connection pool parameters
        """
        kwargs = self.get_connection_kwargs()
        kwargs['max_connections'] = self.max_connections
        return kwargs


def validate_redis_configuration() -> None:
    """
    Validate Redis configuration on application startup.
    
    Raises:
        ValueError: If configuration is invalid or insecure
    """
    try:
        settings = RedisSettings()
        
        # Check for production security requirements
        if os.getenv('ENVIRONMENT', 'dev').lower() == 'production':
            if not settings.password:
                raise ValueError("Redis password is required in production environment")
            
            if not settings.ssl and settings.host not in ['localhost', '127.0.0.1']:
                raise ValueError("SSL/TLS is required for remote Redis connections in production")
        
        # Test connection
        import redis
        client = redis.Redis(**settings.get_connection_kwargs())
        client.ping()
        
    except Exception as e:
        raise ValueError(f"Redis configuration validation failed: {str(e)}")


# Global Redis settings instance
redis_settings = RedisSettings()