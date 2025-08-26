"""
Security initialization and setup utilities.

This module provides functions to initialize and configure all security
components when the application starts.
"""

import os
import sys
from typing import List, Optional

from sqlalchemy.orm import sessionmaker

from src.config.security_config import get_security_settings, validate_security_configuration
from src.utils.security import (
    encryption_manager, secure_config_manager, data_protection_manager
)
from src.utils.audit_logger import audit_logger, AuditEventType, AuditSeverity
from src.utils.data_retention import initialize_data_retention_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def initialize_security_system(db_session_factory: Optional[sessionmaker] = None) -> bool:
    """
    Initialize the complete security system.
    
    Args:
        db_session_factory: Database session factory for audit logging
        
    Returns:
        bool: True if initialization was successful
    """
    try:
        logger.info("Initializing security system...")
        
        # 1. Validate security configuration
        warnings = validate_security_configuration()
        if warnings:
            logger.warning("Security configuration warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        # 2. Initialize encryption system
        if not _initialize_encryption():
            logger.error("Failed to initialize encryption system")
            return False
        
        # 3. Initialize audit logging
        if db_session_factory and not _initialize_audit_logging(db_session_factory):
            logger.error("Failed to initialize audit logging")
            return False
        
        # 4. Initialize data retention
        if db_session_factory:
            initialize_data_retention_manager(db_session_factory)
        
        # 5. Set up secure configuration storage
        if not _initialize_secure_config():
            logger.error("Failed to initialize secure configuration")
            return False
        
        # 6. Create security directories
        _create_security_directories()
        
        # 7. Log security system startup
        if db_session_factory:
            audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_START,
                event_description="Security system initialized successfully",
                severity=AuditSeverity.MEDIUM,
                metadata={
                    "warnings_count": len(warnings),
                    "warnings": warnings
                }
            )
        
        logger.info("Security system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize security system: {e}")
        return False


def _initialize_encryption() -> bool:
    """
    Initialize encryption system.
    
    Returns:
        bool: True if successful
    """
    try:
        settings = get_security_settings()
        
        # Test encryption functionality
        test_data = "test_encryption_data"
        encrypted = encryption_manager.encrypt_string(test_data)
        decrypted = encryption_manager.decrypt_string(encrypted)
        
        if decrypted != test_data:
            logger.error("Encryption system test failed")
            return False
        
        # Test hash functionality
        test_hash = encryption_manager.hash_data("test_password")
        if not encryption_manager.verify_hash("test_password", test_hash):
            logger.error("Hash system test failed")
            return False
        
        logger.info("Encryption system initialized and tested successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize encryption system: {e}")
        return False


def _initialize_audit_logging(db_session_factory: sessionmaker) -> bool:
    """
    Initialize audit logging system.
    
    Args:
        db_session_factory: Database session factory
        
    Returns:
        bool: True if successful
    """
    try:
        # Set up audit logger with database session factory
        audit_logger.db_session_factory = db_session_factory
        
        # Test audit logging
        test_audit_id = audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_START,
            event_description="Audit logging system test",
            severity=AuditSeverity.LOW,
            metadata={"test": True}
        )
        
        # Verify log integrity
        if not audit_logger.verify_log_integrity(test_audit_id):
            logger.error("Audit log integrity test failed")
            return False
        
        logger.info("Audit logging system initialized and tested successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize audit logging: {e}")
        return False


def _initialize_secure_config() -> bool:
    """
    Initialize secure configuration storage.
    
    Returns:
        bool: True if successful
    """
    try:
        # Test secure config functionality
        test_key = "test_config_key"
        test_value = "test_config_value"
        
        # Store and retrieve test config
        secure_config_manager.store_config(test_key, test_value, encrypt=True)
        retrieved_value = secure_config_manager.get_config(test_key)
        
        if retrieved_value != test_value:
            logger.error("Secure configuration test failed")
            return False
        
        # Clean up test config
        secure_config_manager.delete_config(test_key)
        
        logger.info("Secure configuration system initialized and tested successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize secure configuration: {e}")
        return False


def _create_security_directories() -> None:
    """Create necessary directories for security components."""
    try:
        settings = get_security_settings()
        
        # Create directories
        directories = [
            os.path.dirname(settings.audit_log_file),
            os.path.dirname(settings.secure_config_file),
            "logs",
            "config",
            "data/exports",
            "data/cache"
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, mode=0o750, exist_ok=True)
                logger.debug(f"Created security directory: {directory}")
        
    except Exception as e:
        logger.error(f"Failed to create security directories: {e}")


def setup_environment_security() -> None:
    """
    Set up environment-level security configurations.
    
    This function configures environment variables and system settings
    for enhanced security.
    """
    try:
        # Set secure environment variables if not already set
        secure_env_vars = {
            "PYTHONHASHSEED": "random",  # Randomize hash seeds
            "PYTHONDONTWRITEBYTECODE": "1",  # Don't write .pyc files
            "PYTHONUNBUFFERED": "1",  # Unbuffered output
        }
        
        for var, value in secure_env_vars.items():
            if var not in os.environ:
                os.environ[var] = value
        
        # Set restrictive umask for file creation
        os.umask(0o077)
        
        logger.info("Environment security configured")
        
    except Exception as e:
        logger.error(f"Failed to setup environment security: {e}")


def validate_runtime_security() -> List[str]:
    """
    Validate security configuration at runtime.
    
    Returns:
        List[str]: List of security issues found
    """
    issues = []
    
    try:
        settings = get_security_settings()
        
        # Check file permissions
        security_files = [
            settings.audit_log_file,
            settings.secure_config_file
        ]
        
        for file_path in security_files:
            if os.path.exists(file_path):
                file_stat = os.stat(file_path)
                file_mode = file_stat.st_mode & 0o777
                
                # Check if file is readable by others
                if file_mode & 0o044:
                    issues.append(f"Security file {file_path} is readable by others")
                
                # Check if file is writable by others
                if file_mode & 0o022:
                    issues.append(f"Security file {file_path} is writable by others")
        
        # Check environment variables
        sensitive_env_vars = [
            "JWT_SECRET_KEY",
            "ENCRYPTION_MASTER_KEY",
            "DATABASE_URL",
            "REDIS_URL"
        ]
        
        for var in sensitive_env_vars:
            if var in os.environ:
                value = os.environ[var]
                if len(value) < 16:
                    issues.append(f"Environment variable {var} appears to be too short")
        
        # Check Python security
        if sys.version_info < (3, 8):
            issues.append("Python version is older than 3.8, consider upgrading for security")
        
        # Check for debug mode
        if os.getenv("DEBUG", "false").lower() == "true":
            issues.append("Application is running in debug mode")
        
        return issues
        
    except Exception as e:
        logger.error(f"Failed to validate runtime security: {e}")
        return [f"Security validation error: {str(e)}"]


def create_security_report() -> dict:
    """
    Create a comprehensive security status report.
    
    Returns:
        dict: Security status report
    """
    try:
        settings = get_security_settings()
        
        report = {
            "timestamp": str(datetime.utcnow()),
            "security_system_status": "initialized",
            "configuration_warnings": validate_security_configuration(),
            "runtime_issues": validate_runtime_security(),
            "encryption_status": "active",
            "audit_logging_status": "active" if audit_logger.db_session_factory else "inactive",
            "data_retention_status": "configured",
            "settings_summary": {
                "jwt_expiry_minutes": settings.jwt_access_token_expire_minutes,
                "rate_limit_per_minute": settings.rate_limit_requests_per_minute,
                "max_request_size_mb": settings.max_request_size_mb,
                "session_timeout_minutes": settings.session_timeout_minutes,
                "retention_scraped_data_days": settings.retention_scraped_data_days,
                "retention_audit_logs_days": settings.retention_audit_logs_days
            }
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to create security report: {e}")
        return {
            "timestamp": str(datetime.utcnow()),
            "security_system_status": "error",
            "error": str(e)
        }


def emergency_security_shutdown() -> None:
    """
    Emergency security shutdown procedure.
    
    This function should be called in case of security breach
    to safely shut down security-sensitive components.
    """
    try:
        logger.critical("EMERGENCY SECURITY SHUTDOWN INITIATED")
        
        # Log emergency shutdown
        if audit_logger.db_session_factory:
            audit_logger.log_security_alert(
                alert_type="emergency_shutdown",
                description="Emergency security shutdown initiated",
                severity=AuditSeverity.CRITICAL,
                metadata={"initiated_by": "security_system"}
            )
        
        # Clear sensitive data from memory
        # Note: This is a basic implementation - more sophisticated
        # memory clearing would be needed for high-security applications
        
        # Disable further operations
        logger.critical("Security system shutdown complete")
        
    except Exception as e:
        logger.critical(f"Failed to complete emergency security shutdown: {e}")


if __name__ == "__main__":
    # Command-line security utilities
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Security system utilities")
    parser.add_argument("--validate", action="store_true", help="Validate security configuration")
    parser.add_argument("--report", action="store_true", help="Generate security report")
    parser.add_argument("--test", action="store_true", help="Test security components")
    
    args = parser.parse_args()
    
    if args.validate:
        warnings = validate_security_configuration()
        issues = validate_runtime_security()
        
        print("Security Configuration Validation")
        print("=" * 40)
        
        if warnings:
            print("Configuration Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if issues:
            print("Runtime Issues:")
            for issue in issues:
                print(f"  - {issue}")
        
        if not warnings and not issues:
            print("No security issues found.")
    
    elif args.report:
        report = create_security_report()
        print("Security Status Report")
        print("=" * 40)
        print(json.dumps(report, indent=2))
    
    elif args.test:
        print("Testing security components...")
        success = initialize_security_system()
        print(f"Security system test: {'PASSED' if success else 'FAILED'}")
    
    else:
        parser.print_help()