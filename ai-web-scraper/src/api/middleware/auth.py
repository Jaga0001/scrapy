"""
Authentication middleware for FastAPI.

This module provides JWT-based authentication middleware for securing API endpoints.
"""

import time
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token validation.
    
    This middleware validates JWT tokens for protected endpoints
    and adds user information to the request context.
    """
    
    # Endpoints that don't require authentication
    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/health/",
        "/api/v1/health/liveness",
        "/api/v1/health/readiness",
        "/api/v1/health/version",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh"
    }
    
    def __init__(self, app):
        super().__init__(app)
        self.security = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and validate authentication if required.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response: The HTTP response
        """
        # Skip authentication for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Extract and validate token
            token = await self._extract_token(request)
            
            if token:
                user_info = await self._validate_token(token)
                if user_info:
                    # Add user info to request state
                    request.state.user = user_info
                    request.state.authenticated = True
                else:
                    return self._create_auth_error_response("Invalid or expired token")
            else:
                # Check if endpoint requires authentication
                if self._requires_auth(request.url.path):
                    return self._create_auth_error_response("Authentication required")
                else:
                    request.state.authenticated = False
            
            # Process the request
            response = await call_next(request)
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            return response
            
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return self._create_auth_error_response("Authentication error")
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from the Authorization header.
        
        Args:
            request: The HTTP request
            
        Returns:
            Optional[str]: The JWT token if present
        """
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return None
        
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    async def _validate_token(self, token: str) -> Optional[dict]:
        """
        Validate JWT token and extract user information.
        
        Args:
            token: The JWT token to validate
            
        Returns:
            Optional[dict]: User information if token is valid
        """
        try:
            # Use the global JWT manager for validation
            payload = get_jwt_manager().validate_token(token)
            
            if payload and payload.get("type") == "access":
                # Check if token is expired
                exp = payload.get("exp", 0)
                if exp < time.time():
                    logger.warning("Token has expired")
                    return None
                
                return {
                    "user_id": payload.get("user_id"),
                    "username": payload.get("username"),
                    "email": payload.get("email"),
                    "roles": payload.get("roles", ["user"]),
                    "exp": exp
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None
    
    def _requires_auth(self, path: str) -> bool:
        """
        Check if a path requires authentication.
        
        Args:
            path: The request path
            
        Returns:
            bool: True if authentication is required
        """
        # Most API endpoints require authentication
        if path.startswith("/api/v1/"):
            # Health endpoints are exempt
            if path.startswith("/api/v1/health"):
                return False
            return True
        
        return False
    
    def _create_auth_error_response(self, message: str) -> Response:
        """
        Create an authentication error response.
        
        Args:
            message: The error message
            
        Returns:
            Response: HTTP 401 response
        """
        return Response(
            content=f'{{"error": "Authentication Error", "message": "{message}"}}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"Content-Type": "application/json"}
        )


class JWTManager:
    """
    JWT token management utilities.
    
    This class provides methods for creating, validating, and refreshing JWT tokens.
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT manager.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT signing algorithm
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_access_token(self, user_data: dict, expires_delta: int = 3600) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_data: User information to encode in token
            expires_delta: Token expiration time in seconds
            
        Returns:
            str: JWT access token
        """
        try:
            from jose import jwt
            from datetime import datetime, timedelta, timezone
            
            payload = {
                **user_data,
                "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_delta),
                "iat": datetime.now(timezone.utc),
                "type": "access"
            }
            
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
        except ImportError:
            logger.error("python-jose not installed - using placeholder token")
            return "placeholder-token"
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise
    
    def create_refresh_token(self, user_id: str, expires_delta: int = 604800) -> str:
        """
        Create a JWT refresh token.
        
        Args:
            user_id: User ID
            expires_delta: Token expiration time in seconds (default: 7 days)
            
        Returns:
            str: JWT refresh token
        """
        try:
            from jose import jwt
            from datetime import datetime, timedelta, timezone
            
            payload = {
                "user_id": user_id,
                "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_delta),
                "iat": datetime.now(timezone.utc),
                "type": "refresh"
            }
            
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
        except ImportError:
            logger.error("python-jose not installed - using placeholder token")
            return "placeholder-refresh-token"
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise
    
    def validate_token(self, token: str) -> Optional[dict]:
        """
        Validate and decode a JWT token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Optional[dict]: Decoded token payload if valid
        """
        try:
            from jose import jwt, JWTError
            
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            return payload
            
        except ImportError:
            logger.error("python-jose not installed - using placeholder validation")
            # Return placeholder for demo tokens
            if token in ["demo-token", "test-token"]:
                return {
                    "user_id": "user123",
                    "username": "testuser",
                    "type": "access"
                }
            return None
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Create a new access token from a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Optional[str]: New access token if refresh token is valid
        """
        try:
            payload = self.validate_token(refresh_token)
            
            if not payload or payload.get("type") != "refresh":
                return None
            
            # Create new access token
            user_data = {
                "user_id": payload["user_id"],
                "username": payload.get("username"),
                "email": payload.get("email"),
                "roles": payload.get("roles", [])
            }
            
            return self.create_access_token(user_data)
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return None


# Global JWT manager instance
def get_jwt_manager() -> JWTManager:
    """Get JWT manager with configuration from environment."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    
    return JWTManager(secret_key, algorithm)

jwt_manager = get_jwt_manager()