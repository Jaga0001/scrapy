"""
Tests for authentication-related Pydantic models.

This module tests the User, JWTPayload, and related authentication models
for proper validation, serialization, and business logic.
"""

import pytest
import time
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.pydantic_models import User, UserRole, JWTPayload
from tests.fixtures.auth_fixtures import (
    sample_user_data, sample_admin_data, sample_jwt_payload,
    expired_jwt_payload, schema_validation_data
)


class TestUserModel:
    """Test cases for the User model."""
    
    def test_user_model_creation_valid(self, sample_user_data):
        """Test creating a valid User model."""
        user = User(**sample_user_data)
        
        assert user.user_id == sample_user_data["user_id"]
        assert user.username == sample_user_data["username"].lower()
        assert user.email == sample_user_data["email"].lower()
        assert user.is_active is True
        assert UserRole.USER in user.roles
    
    def test_user_model_email_validation(self):
        """Test email validation in User model."""
        # Valid email
        user_data = {
            "user_id": "test-001",
            "username": "testuser",
            "email": "Test@Example.COM",  # Mixed case
            "roles": [UserRole.USER]
        }
        user = User(**user_data)
        assert user.email == "test@example.com"  # Should be lowercase
        
        # Invalid email
        with pytest.raises(ValidationError) as exc_info:
            User(
                user_id="test-001",
                username="testuser",
                email="invalid-email",
                roles=[UserRole.USER]
            )
        assert "Invalid email format" in str(exc_info.value)
    
    def test_user_model_username_validation(self):
        """Test username validation in User model."""
        # Valid username
        user_data = {
            "user_id": "test-001",
            "username": "Valid_User-123",
            "email": "test@example.com",
            "roles": [UserRole.USER]
        }
        user = User(**user_data)
        assert user.username == "valid_user-123"  # Should be lowercase
        
        # Invalid username with special characters
        with pytest.raises(ValidationError) as exc_info:
            User(
                user_id="test-001",
                username="invalid@user!",
                email="test@example.com",
                roles=[UserRole.USER]
            )
        assert "Username can only contain" in str(exc_info.value)


class TestJWTPayloadModel:
    """Test cases for the JWTPayload model."""
    
    def test_jwt_payload_creation_valid(self, sample_jwt_payload):
        """Test creating a valid JWTPayload model."""
        payload = JWTPayload(**sample_jwt_payload)
        
        assert payload.user_id == sample_jwt_payload["user_id"]
        assert payload.username == sample_jwt_payload["username"]
        assert payload.type == "access"
        assert payload.exp == sample_jwt_payload["exp"]
    
    def test_jwt_payload_expired_validation(self, expired_jwt_payload):
        """Test validation of expired JWT payload."""
        with pytest.raises(ValidationError) as exc_info:
            JWTPayload(**expired_jwt_payload)
        assert "Token has expired" in str(exc_info.value)
    
    def test_jwt_payload_type_validation(self, sample_jwt_payload):
        """Test JWT payload type validation."""
        # Valid types
        for token_type in ["access", "refresh"]:
            payload_data = {**sample_jwt_payload, "type": token_type}
            payload = JWTPayload(**payload_data)
            assert payload.type == token_type
        
        # Invalid type
        with pytest.raises(ValidationError) as exc_info:
            invalid_payload = {**sample_jwt_payload, "type": "invalid"}
            JWTPayload(**invalid_payload)
        assert "does not match" in str(exc_info.value)


class TestUserRoleEnum:
    """Test cases for the UserRole enum."""
    
    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.USER == "user"
        assert UserRole.VIEWER == "viewer"
    
    def test_user_role_in_user_model(self):
        """Test UserRole usage in User model."""
        user = User(
            user_id="test-001",
            username="testuser",
            email="test@example.com",
            roles=[UserRole.ADMIN, UserRole.USER]
        )
        
        assert UserRole.ADMIN in user.roles
        assert UserRole.USER in user.roles
        assert UserRole.VIEWER not in user.roles