"""
Authentication routes for the FastAPI application.

This module provides endpoints for user authentication, token management,
and user registration.
"""

from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.api.middleware.auth import get_jwt_manager
from src.api.schemas import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    UserRegistrationRequest, UserResponse, TokenValidationResponse
)
from src.models.pydantic_models import User, UserRole
from src.utils.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer()

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user and return JWT tokens.
    
    Args:
        login_data: User login credentials
        
    Returns:
        LoginResponse: JWT tokens and user information
    """
    try:
        # In a real implementation, you would:
        # 1. Validate credentials against database
        # 2. Check if user is active
        # 3. Hash password comparison
        
        # For demo purposes, accept specific credentials
        if login_data.username == "admin" and login_data.password == "admin123":
            user_data = {
                "user_id": "admin-001",
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "System Administrator",
                "roles": ["admin", "user"]
            }
        elif login_data.username == "user" and login_data.password == "user123":
            user_data = {
                "user_id": "user-001",
                "username": "user",
                "email": "user@example.com",
                "full_name": "Regular User",
                "roles": ["user"]
            }
        else:
            logger.warning(f"Failed login attempt for username: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create tokens
        jwt_manager = get_jwt_manager()
        access_token = jwt_manager.create_access_token(user_data, expires_delta=3600)
        refresh_token = jwt_manager.create_refresh_token(user_data["user_id"])
        
        # Create User model for response
        user = User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            roles=[UserRole(role) for role in user_data["roles"]],
            last_login=datetime.now(timezone.utc)
        )
        
        logger.info(f"User {login_data.username} logged in successfully")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token request
        
    Returns:
        RefreshResponse: New access token
    """
    try:
        jwt_manager = get_jwt_manager()
        new_access_token = jwt_manager.refresh_access_token(refresh_data.refresh_token)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        logger.info("Access token refreshed successfully")
        
        return RefreshTokenResponse(
            access_token=new_access_token,
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error"
        )


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserRegistrationRequest):
    """
    Register a new user account.
    
    Args:
        user_data: User registration information
        
    Returns:
        UserResponse: Created user information
    """
    try:
        # In a real implementation, you would:
        # 1. Check if username/email already exists
        # 2. Hash the password
        # 3. Save user to database
        # 4. Send verification email
        
        # For demo purposes, simulate user creation
        logger.info(f"User registration attempt for: {user_data.username}")
        
        # Simulate checking for existing user
        if user_data.username in ["admin", "user", "test"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        
        # Simulate user creation
        new_user = {
            "user_id": f"user-{hash(user_data.username) % 10000:04d}",
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "roles": ["user"],
            "created_at": datetime.now(timezone.utc),
            "is_active": True
        }
        
        logger.info(f"User {user_data.username} registered successfully")
        
        return UserResponse(**new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration service error"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user information.
    
    Args:
        credentials: JWT token from Authorization header
        
    Returns:
        UserResponse: Current user information
    """
    try:
        # Validate token
        jwt_manager = get_jwt_manager()
        payload = jwt_manager.validate_token(credentials.credentials)
        
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Return user information from token
        user_info = {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "full_name": payload.get("full_name"),
            "roles": payload.get("roles", ["user"]),
            "created_at": datetime.now(timezone.utc),  # Would come from database
            "is_active": True
        }
        
        return UserResponse(**user_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User service error"
        )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user and invalidate token.
    
    Args:
        credentials: JWT token from Authorization header
        
    Returns:
        dict: Logout confirmation
    """
    try:
        # In a real implementation, you would:
        # 1. Add token to blacklist
        # 2. Clear any session data
        # 3. Log the logout event
        
        jwt_manager = get_jwt_manager()
        payload = jwt_manager.validate_token(credentials.credentials)
        
        if payload:
            username = payload.get("username", "unknown")
            logger.info(f"User {username} logged out")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Don't fail logout even if token is invalid
        return {"message": "Logged out"}


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate JWT token and return token information.
    
    Args:
        credentials: JWT token from Authorization header
        
    Returns:
        TokenValidationResponse: Token validation result
    """
    try:
        jwt_manager = get_jwt_manager()
        payload = jwt_manager.validate_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        return TokenValidationResponse(
            valid=True,
            token_type=payload.get("type"),
            user_id=payload.get("user_id"),
            username=payload.get("username"),
            expires_at=payload.get("exp")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation service error"
        )