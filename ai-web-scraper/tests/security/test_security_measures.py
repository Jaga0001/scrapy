"""
Comprehensive security tests for authentication, authorization, and data protection.

This module contains tests for all security measures including input validation,
encryption, audit logging, and data protection mechanisms.
"""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.utils.security import (
    EncryptionManager, SecureConfigManager, DataProtectionManager,
    encryption_manager, secure_config_manager, data_protection_manager
)
from src.utils.audit_logger import (
    AuditLogger, AuditEventType, AuditSeverity, AuditLogORM
)
from src.utils.input_validator import SecurityValidator, ValidationResult
from src.utils.data_retention import DataRetentionManager
from src.api.middleware.auth import AuthMiddleware, JWTManager
from src.api.middleware.validation import ValidationMiddleware


class TestEncryptionManager:
    """Test encryption and decryption functionality."""
    
    def setup_method(self):
        """Set up test encryption manager."""
        self.encryption_manager = EncryptionManager("test_master_key_2024")
    
    def test_string_encryption_decryption(self):
        """Test string encryption and decryption."""
        original_text = "This is a secret message"
        
        # Encrypt
        encrypted = self.encryption_manager.encrypt_string(original_text)
        assert encrypted != original_text
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = self.encryption_manager.decrypt_string(encrypted)
        assert decrypted == original_text
    
    def test_dict_encryption_decryption(self):
        """Test dictionary encryption and decryption."""
        original_dict = {
            "api_key": "secret_key_123",
            "database_url": "postgresql://user:pass@localhost/db",
            "nested": {
                "value": "nested_secret"
            }
        }
        
        # Encrypt
        encrypted = self.encryption_manager.encrypt_dict(original_dict)
        assert encrypted != json.dumps(original_dict)
        
        # Decrypt
        decrypted = self.encryption_manager.decrypt_dict(encrypted)
        assert decrypted == original_dict
    
    def test_hash_verification(self):
        """Test data hashing and verification."""
        data = "password123"
        
        # Create hash
        hash_with_salt = self.encryption_manager.hash_data(data)
        assert ":" in hash_with_salt  # Should contain salt
        
        # Verify correct data
        assert self.encryption_manager.verify_hash(data, hash_with_salt)
        
        # Verify incorrect data
        assert not self.encryption_manager.verify_hash("wrong_password", hash_with_salt)
    
    def test_encryption_with_invalid_data(self):
        """Test encryption error handling."""
        with pytest.raises(Exception):
            self.encryption_manager.decrypt_string("invalid_encrypted_data")


class TestSecureConfigManager:
    """Test secure configuration management."""
    
    def setup_method(self):
        """Set up test secure config manager."""
        self.encryption_manager = EncryptionManager("test_master_key_2024")
        
        # Use temporary file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.enc")
        
        with patch.dict(os.environ, {"SECURE_CONFIG_FILE": self.config_file}):
            self.config_manager = SecureConfigManager(self.encryption_manager)
    
    def teardown_method(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_and_retrieve_string_config(self):
        """Test storing and retrieving encrypted string configuration."""
        key = "api_key"
        value = "secret_api_key_123"
        
        # Store encrypted
        self.config_manager.store_config(key, value, encrypt=True)
        
        # Retrieve
        retrieved = self.config_manager.get_config(key)
        assert retrieved == value
    
    def test_store_and_retrieve_dict_config(self):
        """Test storing and retrieving encrypted dictionary configuration."""
        key = "database_config"
        value = {
            "host": "localhost",
            "port": 5432,
            "username": "user",
            "password": "secret_password"
        }
        
        # Store encrypted
        self.config_manager.store_config(key, value, encrypt=True)
        
        # Retrieve
        retrieved = self.config_manager.get_config(key)
        assert retrieved == value
    
    def test_store_unencrypted_config(self):
        """Test storing unencrypted configuration."""
        key = "public_setting"
        value = "public_value"
        
        # Store unencrypted
        self.config_manager.store_config(key, value, encrypt=False)
        
        # Retrieve
        retrieved = self.config_manager.get_config(key)
        assert retrieved == value
    
    def test_get_nonexistent_config(self):
        """Test retrieving non-existent configuration."""
        result = self.config_manager.get_config("nonexistent_key", "default_value")
        assert result == "default_value"
    
    def test_delete_config(self):
        """Test deleting configuration."""
        key = "temp_config"
        value = "temp_value"
        
        # Store
        self.config_manager.store_config(key, value)
        assert self.config_manager.get_config(key) == value
        
        # Delete
        assert self.config_manager.delete_config(key)
        assert self.config_manager.get_config(key) is None
    
    def test_list_config_keys(self):
        """Test listing configuration keys."""
        configs = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        # Store multiple configs
        for key, value in configs.items():
            self.config_manager.store_config(key, value)
        
        # List keys
        keys = self.config_manager.list_config_keys()
        assert set(keys) == set(configs.keys())


class TestDataProtectionManager:
    """Test data protection and encryption for scraped content."""
    
    def setup_method(self):
        """Set up test data protection manager."""
        self.encryption_manager = EncryptionManager("test_master_key_2024")
        self.protection_manager = DataProtectionManager(self.encryption_manager)
    
    def test_encrypt_sensitive_content(self):
        """Test encryption of sensitive fields in scraped content."""
        content = {
            "title": "Public Title",
            "email": "user@example.com",
            "phone": "123-456-7890",
            "address": "123 Main St",
            "description": "Public description",
            "nested": {
                "api_key": "secret_key_123",
                "public_info": "Not sensitive"
            }
        }
        
        # Encrypt sensitive content
        encrypted_content = self.protection_manager.encrypt_scraped_content(content)
        
        # Check that sensitive fields are encrypted
        assert encrypted_content["email"]["_encrypted"] is True
        assert encrypted_content["phone"]["_encrypted"] is True
        assert encrypted_content["address"]["_encrypted"] is True
        assert encrypted_content["nested"]["api_key"]["_encrypted"] is True
        
        # Check that non-sensitive fields are not encrypted
        assert encrypted_content["title"] == "Public Title"
        assert encrypted_content["description"] == "Public description"
        assert encrypted_content["nested"]["public_info"] == "Not sensitive"
    
    def test_decrypt_sensitive_content(self):
        """Test decryption of sensitive fields in scraped content."""
        original_content = {
            "title": "Public Title",
            "email": "user@example.com",
            "phone": "123-456-7890",
            "nested": {
                "password": "secret_password",
                "public_info": "Not sensitive"
            }
        }
        
        # Encrypt then decrypt
        encrypted_content = self.protection_manager.encrypt_scraped_content(original_content)
        decrypted_content = self.protection_manager.decrypt_scraped_content(encrypted_content)
        
        # Should match original
        assert decrypted_content == original_content
    
    def test_retention_policy_check(self):
        """Test data retention policy checking."""
        # Test data that should be retained
        recent_date = datetime.utcnow() - timedelta(days=30)
        assert self.protection_manager.should_retain_data("scraped_data", recent_date)
        
        # Test data that should be deleted (assuming 365 day retention)
        old_date = datetime.utcnow() - timedelta(days=400)
        assert not self.protection_manager.should_retain_data("scraped_data", old_date)


class TestSecurityValidator:
    """Test input validation and sanitization."""
    
    def setup_method(self):
        """Set up test security validator."""
        self.validator = SecurityValidator()
    
    def test_validate_safe_string(self):
        """Test validation of safe string input."""
        result = self.validator.validate_string("Hello World", max_length=50)
        
        assert result.is_valid
        assert result.sanitized_value == "Hello World"
        assert len(result.errors) == 0
    
    def test_validate_dangerous_string(self):
        """Test validation of dangerous string input."""
        dangerous_input = "<script>alert('xss')</script>"
        result = self.validator.validate_string(dangerous_input)
        
        assert not result.is_valid
        assert "dangerous content" in result.errors[0].lower()
    
    def test_validate_sql_injection_attempt(self):
        """Test detection of SQL injection attempts."""
        sql_injection = "'; DROP TABLE users; --"
        result = self.validator.validate_string(sql_injection)
        
        assert not result.is_valid
        assert "dangerous content" in result.errors[0].lower()
    
    def test_validate_long_string(self):
        """Test validation of overly long strings."""
        long_string = "A" * 2000
        result = self.validator.validate_string(long_string, max_length=100)
        
        assert not result.is_valid
        assert "exceeds maximum length" in result.errors[0]
        assert len(result.sanitized_value) == 100
    
    def test_validate_valid_url(self):
        """Test validation of valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://subdomain.example.com/path",
            "https://example.com/path?param=value"
        ]
        
        for url in valid_urls:
            result = self.validator.validate_url(url)
            assert result.is_valid, f"URL should be valid: {url}"
    
    def test_validate_dangerous_url(self):
        """Test validation of dangerous URLs."""
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')"
        ]
        
        for url in dangerous_urls:
            result = self.validator.validate_url(url)
            assert not result.is_valid, f"URL should be invalid: {url}"
    
    def test_validate_valid_email(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@subdomain.example.org"
        ]
        
        for email in valid_emails:
            result = self.validator.validate_email(email)
            assert result.is_valid, f"Email should be valid: {email}"
    
    def test_validate_invalid_email(self):
        """Test validation of invalid email addresses."""
        invalid_emails = [
            "not-an-email",
            "@domain.com",
            "user@",
            "user space@domain.com"
        ]
        
        for email in invalid_emails:
            result = self.validator.validate_email(email)
            assert not result.is_valid, f"Email should be invalid: {email}"
    
    def test_validate_filename(self):
        """Test filename validation and sanitization."""
        # Valid filename
        result = self.validator.validate_filename("document.pdf")
        assert result.is_valid
        assert result.sanitized_value == "document.pdf"
        
        # Dangerous filename
        dangerous_filename = "../../../etc/passwd"
        result = self.validator.validate_filename(dangerous_filename)
        assert result.is_valid  # Should be sanitized, not rejected
        assert ".." not in result.sanitized_value
        assert "/" not in result.sanitized_value
    
    def test_validate_json(self):
        """Test JSON validation."""
        # Valid JSON
        valid_json = {"key": "value", "number": 123}
        result = self.validator.validate_json(valid_json)
        assert result.is_valid
        
        # Invalid JSON structure (too deep)
        deep_json = {"level1": {"level2": {"level3": {"level4": {"level5": {}}}}}}
        result = self.validator.validate_json(deep_json, max_depth=3)
        assert not result.is_valid


class TestAuditLogger:
    """Test audit logging functionality."""
    
    def setup_method(self):
        """Set up test audit logger."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        
        # Create audit log table
        from src.utils.audit_logger import AuditBase
        AuditBase.metadata.create_all(self.engine)
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        
        # Create audit logger
        self.audit_logger = AuditLogger(self.session_factory)
    
    def test_log_authentication_event(self):
        """Test logging authentication events."""
        audit_id = self.audit_logger.log_authentication_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            username="testuser",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            success=True
        )
        
        assert audit_id is not None
        
        # Verify log was stored
        session = self.session_factory()
        try:
            audit_log = session.query(AuditLogORM).filter_by(id=audit_id).first()
            assert audit_log is not None
            assert audit_log.event_type == AuditEventType.LOGIN_SUCCESS.value
            assert audit_log.username == "testuser"
            assert audit_log.ip_address == "192.168.1.100"
        finally:
            session.close()
    
    def test_log_data_access_event(self):
        """Test logging data access events."""
        audit_id = self.audit_logger.log_data_access_event(
            event_type=AuditEventType.DATA_READ,
            resource_type="scraped_data",
            resource_id="data123",
            user_id="user456",
            username="testuser",
            ip_address="192.168.1.100"
        )
        
        assert audit_id is not None
        
        # Verify log was stored
        session = self.session_factory()
        try:
            audit_log = session.query(AuditLogORM).filter_by(id=audit_id).first()
            assert audit_log is not None
            assert audit_log.event_type == AuditEventType.DATA_READ.value
            assert audit_log.resource_type == "scraped_data"
            assert audit_log.resource_id == "data123"
        finally:
            session.close()
    
    def test_log_security_alert(self):
        """Test logging security alerts."""
        audit_id = self.audit_logger.log_security_alert(
            alert_type="suspicious_activity",
            description="Multiple failed login attempts",
            severity=AuditSeverity.HIGH,
            ip_address="192.168.1.100"
        )
        
        assert audit_id is not None
        
        # Verify log was stored
        session = self.session_factory()
        try:
            audit_log = session.query(AuditLogORM).filter_by(id=audit_id).first()
            assert audit_log is not None
            assert audit_log.event_type == AuditEventType.SECURITY_ALERT.value
            assert audit_log.severity == AuditSeverity.HIGH.value
        finally:
            session.close()
    
    def test_log_integrity_verification(self):
        """Test audit log integrity verification."""
        # Log an event
        audit_id = self.audit_logger.log_event(
            event_type=AuditEventType.DATA_CREATE,
            event_description="Test event for integrity check",
            severity=AuditSeverity.MEDIUM
        )
        
        # Verify integrity
        assert self.audit_logger.verify_log_integrity(audit_id)
        
        # Tamper with the log and verify it fails
        session = self.session_factory()
        try:
            audit_log = session.query(AuditLogORM).filter_by(id=audit_id).first()
            audit_log.event_description = "Tampered description"
            session.commit()
            
            # Should fail integrity check
            assert not self.audit_logger.verify_log_integrity(audit_id)
        finally:
            session.close()


class TestAuthenticationMiddleware:
    """Test authentication middleware."""
    
    def setup_method(self):
        """Set up test authentication middleware."""
        self.jwt_manager = JWTManager("test_secret_key")
    
    def test_create_and_validate_access_token(self):
        """Test JWT token creation and validation."""
        user_data = {
            "user_id": "user123",
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user"]
        }
        
        # Create token
        token = self.jwt_manager.create_access_token(user_data)
        assert token is not None
        
        # Validate token
        payload = self.jwt_manager.validate_token(token)
        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["username"] == "testuser"
    
    def test_token_expiration(self):
        """Test token expiration handling."""
        user_data = {"user_id": "user123", "username": "testuser"}
        
        # Create token with short expiration
        token = self.jwt_manager.create_access_token(user_data, expires_delta=1)
        
        # Should be valid immediately
        payload = self.jwt_manager.validate_token(token)
        assert payload is not None
        
        # Wait for expiration
        time.sleep(2)
        
        # Should be invalid after expiration
        payload = self.jwt_manager.validate_token(token)
        assert payload is None
    
    def test_refresh_token_flow(self):
        """Test refresh token creation and usage."""
        user_id = "user123"
        
        # Create refresh token
        refresh_token = self.jwt_manager.create_refresh_token(user_id)
        assert refresh_token is not None
        
        # Use refresh token to get new access token
        new_access_token = self.jwt_manager.refresh_access_token(refresh_token)
        assert new_access_token is not None
        
        # Validate new access token
        payload = self.jwt_manager.validate_token(new_access_token)
        assert payload is not None
        assert payload["user_id"] == user_id


class TestDataRetentionManager:
    """Test data retention and cleanup functionality."""
    
    def setup_method(self):
        """Set up test data retention manager."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        
        # Create all tables
        from src.models.database_models import Base
        from src.utils.audit_logger import AuditBase
        Base.metadata.create_all(self.engine)
        AuditBase.metadata.create_all(self.engine)
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        
        # Create retention manager with short retention periods for testing
        with patch.dict(os.environ, {
            "RETENTION_SCRAPED_DATA_DAYS": "1",
            "RETENTION_JOB_LOGS_DAYS": "1",
            "RETENTION_DRY_RUN": "true"
        }):
            self.retention_manager = DataRetentionManager(self.session_factory)
    
    def test_retention_policy_loading(self):
        """Test loading of retention policies from environment."""
        policies = self.retention_manager.retention_policies
        
        assert "scraped_data" in policies
        assert "job_logs" in policies
        assert policies["scraped_data"].days == 1  # From environment override
    
    def test_get_retention_summary(self):
        """Test getting retention summary."""
        summary = self.retention_manager.get_retention_summary()
        
        assert isinstance(summary, dict)
        assert "scraped_data" in summary
        assert "job_logs" in summary
        
        # Check summary structure
        for data_type, info in summary.items():
            if "error" not in info:
                assert "retention_days" in info
                assert "total_records" in info
                assert "expired_records" in info
    
    def test_cleanup_dry_run(self):
        """Test cleanup in dry run mode."""
        # Run cleanup (should be dry run based on setup)
        results = self.retention_manager.run_cleanup(["scraped_data", "job_logs"])
        
        assert isinstance(results, dict)
        # In dry run mode, should return counts but not actually delete


class TestIntegrationSecurity:
    """Integration tests for security measures."""
    
    def test_end_to_end_security_flow(self):
        """Test complete security flow from input to storage."""
        # 1. Validate input
        validator = SecurityValidator()
        input_data = {
            "url": "https://example.com",
            "email": "user@example.com",
            "description": "Safe description"
        }
        
        validated_data = {}
        for key, value in input_data.items():
            if key == "url":
                result = validator.validate_url(value)
            elif key == "email":
                result = validator.validate_email(value)
            else:
                result = validator.validate_string(value)
            
            assert result.is_valid
            validated_data[key] = result.sanitized_value
        
        # 2. Encrypt sensitive data
        encryption_manager = EncryptionManager("test_key")
        protection_manager = DataProtectionManager(encryption_manager)
        
        encrypted_data = protection_manager.encrypt_scraped_content(validated_data)
        
        # 3. Verify encryption worked
        assert encrypted_data["email"]["_encrypted"] is True
        
        # 4. Decrypt and verify
        decrypted_data = protection_manager.decrypt_scraped_content(encrypted_data)
        assert decrypted_data["email"] == input_data["email"]
    
    @patch('src.utils.audit_logger.audit_logger')
    def test_security_alert_integration(self, mock_audit_logger):
        """Test security alert integration."""
        validator = SecurityValidator()
        
        # Try to validate dangerous input
        dangerous_input = "<script>alert('xss')</script>"
        result = validator.validate_string(dangerous_input, field_name="test_field")
        
        # Should be invalid
        assert not result.is_valid
        
        # Should have triggered security alert
        mock_audit_logger.log_security_alert.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])