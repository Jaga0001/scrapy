"""
Test fixtures for authentication-related tests.

This module provides test data and fixtures for authentication,
user management, and JWT token testing.
"""

import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any

from src.models.pydantic_models import User, UserRole, JWTPayload
from src.api.schemas import (
    LoginRequest, LoginResponse, UserRegistrationRequest, 
    UserResponse, TokenValidationResponse
)


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing."""
    return {
        "user_id": "test-user-001",
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "roles": ["user"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None
    }


@pytest.fixture
def sample_admin_data() -> Dict[str, Any]:
    """Sample admin user data for testing."""
    return {
        "user_id": "admin-001",
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "System Administrator",
        "roles": ["admin", "user"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_user_model(sample_user_data) -> User:
    """Sample User model instance."""
    return User(**sample_user_data)


@pytest.fixture
def sample_admin_model(sample_admin_data) -> User:
    """Sample admin User model instance."""
    return User(**sample_admin_data)


@pytest.fixture
def valid_login_request() -> LoginRequest:
    """Valid login request for testing."""
    return LoginRequest(
        username="testuser",
        password="TestPass123!"
    )


@pytest.fixture
def invalid_login_request() -> LoginRequest:
    """Invalid login request for testing."""
    return LoginRequest(
        username="invalid",
        password="wrong"
    )


@pytest.fixture
def valid_registration_request() -> UserRegistrationRequest:
    """Valid user registration request."""
    return UserRegistrationRequest(
        username="newuser",
        email="newuser@example.com",
        password="NewPass123!",
        full_name="New User"
    )


@pytest.fixture
def invalid_registration_request() -> UserRegistrationRequest:
    """Invalid user registration request (weak password)."""
    return UserRegistrationRequest(
        username="newuser",
        email="newuser@example.com",
        password="weak",  # Too weak
        full_name="New User"
    )


@pytest.fixture
def sample_jwt_payload() -> Dict[str, Any]:
    """Sample JWT payload for testing."""
    current_time = int(time.time())
    return {
        "user_id": "test-user-001",
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "roles": ["user"],
        "exp": current_time + 3600,  # 1 hour from now
        "iat": current_time,
        "type": "access"
    }


@pytest.fixture
def expired_jwt_payload() -> Dict[str, Any]:
    """Expired JWT payload for testing."""
    current_time = int(time.time())
    return {
        "user_id": "test-user-001",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "exp": current_time - 3600,  # 1 hour ago (expired)
        "iat": current_time - 7200,  # 2 hours ago
        "type": "access"
    }


@pytest.fixture
def refresh_jwt_payload() -> Dict[str, Any]:
    """Refresh JWT payload for testing."""
    current_time = int(time.time())
    return {
        "user_id": "test-user-001",
        "exp": current_time + 604800,  # 7 days from now
        "iat": current_time,
        "type": "refresh"
    }


@pytest.fixture
def sample_login_response(sample_user_model) -> LoginResponse:
    """Sample login response for testing."""
    return LoginResponse(
        access_token="sample-access-token",
        refresh_token="sample-refresh-token",
        token_type="bearer",
        expires_in=3600,
        user=sample_user_model
    )


@pytest.fixture
def sample_token_validation_response() -> TokenValidationResponse:
    """Sample token validation response."""
    return TokenValidationResponse(
        valid=True,
        token_type="access",
        user_id="test-user-001",
        username="testuser",
        expires_at=int(time.time()) + 3600
    )


@pytest.fixture
def invalid_token_validation_response() -> TokenValidationResponse:
    """Invalid token validation response."""
    return TokenValidationResponse(
        valid=False,
        token_type=None,
        user_id=None,
        username=None,
        expires_at=None
    )


# Test data for various scenarios
@pytest.fixture
def auth_test_scenarios():
    """Various authentication test scenarios."""
    return {
        "valid_credentials": [
            {"username": "admin", "password": "admin123"},
            {"username": "user", "password": "user123"},
            {"username": "testuser", "password": "TestPass123!"}
        ],
        "invalid_credentials": [
            {"username": "admin", "password": "wrong"},
            {"username": "nonexistent", "password": "password"},
            {"username": "", "password": "password"},
            {"username": "admin", "password": ""}
        ],
        "malformed_requests": [
            {"username": "admin"},  # Missing password
            {"password": "password"},  # Missing username
            {},  # Empty request
            {"username": "admin", "password": "pass", "extra": "field"}  # Extra field
        ],
        "edge_cases": [
            {"username": "a" * 100, "password": "password"},  # Long username
            {"username": "admin", "password": "p" * 200},  # Long password
            {"username": "admin\x00", "password": "password"},  # Null byte
            {"username": "admin", "password": "password\n"},  # Newline
        ]
    }


@pytest.fixture
def user_registration_scenarios():
    """Various user registration test scenarios."""
    return {
        "valid_registrations": [
            {
                "username": "newuser1",
                "email": "user1@example.com",
                "password": "StrongPass123!",
                "full_name": "New User One"
            },
            {
                "username": "newuser2",
                "email": "user2@example.com",
                "password": "AnotherPass456@",
                "full_name": None
            }
        ],
        "invalid_registrations": [
            {
                "username": "nu",  # Too short
                "email": "user@example.com",
                "password": "StrongPass123!",
                "full_name": "User"
            },
            {
                "username": "newuser",
                "email": "invalid-email",  # Invalid email
                "password": "StrongPass123!",
                "full_name": "User"
            },
            {
                "username": "newuser",
                "email": "user@example.com",
                "password": "weak",  # Weak password
                "full_name": "User"
            },
            {
                "username": "admin",  # Already exists
                "email": "admin@example.com",
                "password": "StrongPass123!",
                "full_name": "Admin"
            }
        ]
    }


@pytest.fixture
def jwt_token_scenarios():
    """Various JWT token test scenarios."""
    current_time = int(time.time())
    
    return {
        "valid_tokens": [
            {
                "user_id": "user-001",
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["user"],
                "exp": current_time + 3600,
                "iat": current_time,
                "type": "access"
            },
            {
                "user_id": "admin-001",
                "username": "admin",
                "email": "admin@example.com",
                "roles": ["admin", "user"],
                "exp": current_time + 3600,
                "iat": current_time,
                "type": "access"
            }
        ],
        "invalid_tokens": [
            {
                "user_id": "user-001",
                "username": "testuser",
                "exp": current_time - 3600,  # Expired
                "iat": current_time - 7200,
                "type": "access"
            },
            {
                "user_id": "user-001",
                "username": "testuser",
                "exp": current_time + 3600,
                "iat": current_time,
                "type": "invalid"  # Invalid type
            },
            {
                # Missing required fields
                "username": "testuser",
                "exp": current_time + 3600,
                "type": "access"
            }
        ],
        "refresh_tokens": [
            {
                "user_id": "user-001",
                "exp": current_time + 604800,  # 7 days
                "iat": current_time,
                "type": "refresh"
            }
        ]
    }


# Mock data for external dependencies
@pytest.fixture
def mock_database_users():
    """Mock database users for testing."""
    return {
        "admin": {
            "user_id": "admin-001",
            "username": "admin",
            "email": "admin@example.com",
            "password_hash": "$2b$12$hashed_password_here",
            "full_name": "System Administrator",
            "roles": ["admin", "user"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "last_login": None
        },
        "user": {
            "user_id": "user-001",
            "username": "user",
            "email": "user@example.com",
            "password_hash": "$2b$12$another_hashed_password",
            "full_name": "Regular User",
            "roles": ["user"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "last_login": None
        },
        "inactive": {
            "user_id": "inactive-001",
            "username": "inactive",
            "email": "inactive@example.com",
            "password_hash": "$2b$12$inactive_user_password",
            "full_name": "Inactive User",
            "roles": ["user"],
            "is_active": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None
        }
    }


@pytest.fixture
def auth_headers():
    """Authentication headers for testing."""
    return {
        "valid_bearer": {"Authorization": "Bearer valid-token-here"},
        "invalid_bearer": {"Authorization": "Bearer invalid-token"},
        "malformed_auth": {"Authorization": "InvalidFormat token"},
        "missing_bearer": {"Authorization": "token-without-bearer"},
        "empty_auth": {"Authorization": ""},
        "no_auth": {}
    }


# Validation test data
@pytest.fixture
def schema_validation_data():
    """Data for testing schema validation."""
    return {
        "user_model_valid": [
            {
                "user_id": "user-001",
                "username": "validuser",
                "email": "valid@example.com",
                "roles": ["user"]
            }
        ],
        "user_model_invalid": [
            {
                "user_id": "",  # Empty user_id
                "username": "validuser",
                "email": "valid@example.com",
                "roles": ["user"]
            },
            {
                "user_id": "user-001",
                "username": "ab",  # Too short username
                "email": "valid@example.com",
                "roles": ["user"]
            },
            {
                "user_id": "user-001",
                "username": "validuser",
                "email": "invalid-email",  # Invalid email
                "roles": ["user"]
            },
            {
                "user_id": "user-001",
                "username": "validuser",
                "email": "valid@example.com",
                "roles": ["invalid_role"]  # Invalid role
            }
        ],
        "jwt_payload_valid": [
            {
                "user_id": "user-001",
                "username": "testuser",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "type": "access"
            }
        ],
        "jwt_payload_invalid": [
            {
                "user_id": "user-001",
                "username": "testuser",
                "exp": int(time.time()) - 3600,  # Expired
                "iat": int(time.time()),
                "type": "access"
            },
            {
                "user_id": "user-001",
                "username": "testuser",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "type": "invalid"  # Invalid type
            }
        ]
    }