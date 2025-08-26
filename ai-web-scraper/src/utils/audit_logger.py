"""
Audit logging system for security-relevant operations.

This module provides comprehensive audit logging with tamper protection
for tracking security-relevant operations and maintaining compliance.
"""

import hashlib
import json
import os
import threading
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, JSON, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from src.utils.logger import get_logger
from src.utils.security import encryption_manager

logger = get_logger(__name__)

# Audit log database model
AuditBase = declarative_base()


class AuditEventType(str, Enum):
    """Enumeration of audit event types."""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    
    # Data access events
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGE = "config_change"
    SECURITY_ALERT = "security_alert"
    
    # Scraping events
    SCRAPING_JOB_START = "scraping_job_start"
    SCRAPING_JOB_COMPLETE = "scraping_job_complete"
    SCRAPING_JOB_FAIL = "scraping_job_fail"
    
    # API events
    API_REQUEST = "api_request"
    API_ERROR = "api_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class AuditSeverity(str, Enum):
    """Enumeration of audit event severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLogORM(AuditBase):
    """SQLAlchemy model for audit logs table."""
    
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # Event information
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    event_description = Column(Text, nullable=False)
    
    # Actor information
    user_id = Column(String(36), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    
    # Resource information
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    resource_name = Column(String(200), nullable=True)
    
    # Request information
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_params = Column(JSON, default=dict, nullable=False)
    
    # Response information
    response_status = Column(String(10), nullable=True)
    response_message = Column(Text, nullable=True)
    
    # Additional context
    metadata = Column(JSON, default=dict, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    
    # Tamper protection
    checksum = Column(String(64), nullable=False)
    previous_checksum = Column(String(64), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Retention
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_audit_event_timestamp', 'event_type', 'timestamp'),
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_severity_timestamp', 'severity', 'timestamp'),
        Index('idx_audit_resource_timestamp', 'resource_type', 'resource_id', 'timestamp'),
        Index('idx_audit_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"


class AuditLogger:
    """
    Audit logger with tamper protection and secure storage.
    
    This class provides comprehensive audit logging capabilities with
    cryptographic integrity protection and secure storage.
    """
    
    def __init__(self, db_session_factory=None):
        """
        Initialize audit logger.
        
        Args:
            db_session_factory: Database session factory for audit log storage
        """
        self.db_session_factory = db_session_factory
        self._lock = threading.Lock()
        self._last_checksum = self._get_last_checksum()
        
        # Initialize audit log file backup
        self.audit_file_path = os.getenv("AUDIT_LOG_FILE", "logs/audit.log")
        self._ensure_audit_file_exists()
    
    def log_event(
        self,
        event_type: AuditEventType,
        event_description: str,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        request_params: Optional[Dict[str, Any]] = None,
        response_status: Optional[str] = None,
        response_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Log an audit event with tamper protection.
        
        Args:
            event_type: Type of audit event
            event_description: Description of the event
            severity: Severity level of the event
            user_id: ID of the user who performed the action
            username: Username of the user
            ip_address: IP address of the request
            user_agent: User agent string
            resource_type: Type of resource affected
            resource_id: ID of the resource affected
            resource_name: Name of the resource affected
            request_method: HTTP method of the request
            request_path: Path of the request
            request_params: Request parameters
            response_status: Response status code
            response_message: Response message
            metadata: Additional metadata
            tags: Event tags for categorization
            
        Returns:
            str: Audit log entry ID
        """
        try:
            with self._lock:
                # Generate unique ID
                audit_id = str(uuid4())
                
                # Prepare audit data
                audit_data = {
                    "id": audit_id,
                    "event_type": event_type.value,
                    "severity": severity.value,
                    "event_description": event_description,
                    "user_id": user_id,
                    "username": username,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "resource_name": resource_name,
                    "request_method": request_method,
                    "request_path": request_path,
                    "request_params": request_params or {},
                    "response_status": response_status,
                    "response_message": response_message,
                    "metadata": metadata or {},
                    "tags": tags or [],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Calculate checksum for tamper protection
                checksum = self._calculate_checksum(audit_data)
                audit_data["checksum"] = checksum
                audit_data["previous_checksum"] = self._last_checksum
                
                # Store in database
                if self.db_session_factory:
                    self._store_in_database(audit_data)
                
                # Store in file as backup
                self._store_in_file(audit_data)
                
                # Update last checksum
                self._last_checksum = checksum
                
                logger.info(f"Audit event logged: {event_type.value} (ID: {audit_id})")
                
                return audit_id
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Still try to log to file as fallback
            try:
                self._store_emergency_log(event_type, event_description, str(e))
            except Exception:
                pass
            raise
    
    def log_authentication_event(
        self,
        event_type: AuditEventType,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log authentication-related events.
        
        Args:
            event_type: Authentication event type
            username: Username attempting authentication
            ip_address: IP address of the request
            user_agent: User agent string
            success: Whether authentication was successful
            error_message: Error message if authentication failed
            metadata: Additional metadata
            
        Returns:
            str: Audit log entry ID
        """
        severity = AuditSeverity.MEDIUM if success else AuditSeverity.HIGH
        description = f"Authentication attempt for user '{username}'"
        
        if not success and error_message:
            description += f" failed: {error_message}"
        elif success:
            description += " succeeded"
        
        return self.log_event(
            event_type=event_type,
            event_description=description,
            severity=severity,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            response_status="200" if success else "401",
            response_message=error_message,
            metadata=metadata,
            tags=["authentication"]
        )
    
    def log_data_access_event(
        self,
        event_type: AuditEventType,
        resource_type: str,
        resource_id: str,
        user_id: str,
        username: str,
        ip_address: str,
        operation_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log data access events.
        
        Args:
            event_type: Data access event type
            resource_type: Type of resource accessed
            resource_id: ID of the resource
            user_id: ID of the user accessing the data
            username: Username of the user
            ip_address: IP address of the request
            operation_details: Details about the operation
            metadata: Additional metadata
            
        Returns:
            str: Audit log entry ID
        """
        description = f"User '{username}' performed {event_type.value} on {resource_type} '{resource_id}'"
        if operation_details:
            description += f": {operation_details}"
        
        return self.log_event(
            event_type=event_type,
            event_description=description,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            tags=["data_access"]
        )
    
    def log_security_alert(
        self,
        alert_type: str,
        description: str,
        severity: AuditSeverity,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log security alerts and suspicious activities.
        
        Args:
            alert_type: Type of security alert
            description: Description of the security event
            severity: Severity of the alert
            ip_address: IP address associated with the alert
            user_id: User ID if applicable
            metadata: Additional metadata
            
        Returns:
            str: Audit log entry ID
        """
        return self.log_event(
            event_type=AuditEventType.SECURITY_ALERT,
            event_description=f"Security Alert ({alert_type}): {description}",
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
            tags=["security", "alert", alert_type.lower()]
        )
    
    def verify_log_integrity(self, audit_id: str) -> bool:
        """
        Verify the integrity of an audit log entry.
        
        Args:
            audit_id: ID of the audit log entry to verify
            
        Returns:
            bool: True if the log entry is intact
        """
        try:
            if not self.db_session_factory:
                return False
            
            session = self.db_session_factory()
            try:
                audit_log = session.query(AuditLogORM).filter_by(id=audit_id).first()
                
                if not audit_log:
                    return False
                
                # Reconstruct audit data for checksum verification
                audit_data = {
                    "id": audit_log.id,
                    "event_type": audit_log.event_type,
                    "severity": audit_log.severity,
                    "event_description": audit_log.event_description,
                    "user_id": audit_log.user_id,
                    "username": audit_log.username,
                    "ip_address": audit_log.ip_address,
                    "user_agent": audit_log.user_agent,
                    "resource_type": audit_log.resource_type,
                    "resource_id": audit_log.resource_id,
                    "resource_name": audit_log.resource_name,
                    "request_method": audit_log.request_method,
                    "request_path": audit_log.request_path,
                    "request_params": audit_log.request_params,
                    "response_status": audit_log.response_status,
                    "response_message": audit_log.response_message,
                    "metadata": audit_log.metadata,
                    "tags": audit_log.tags,
                    "timestamp": audit_log.timestamp.isoformat()
                }
                
                # Calculate expected checksum
                expected_checksum = self._calculate_checksum(audit_data)
                
                # Compare with stored checksum
                return expected_checksum == audit_log.checksum
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to verify log integrity for {audit_id}: {e}")
            return False
    
    def _calculate_checksum(self, audit_data: Dict[str, Any]) -> str:
        """
        Calculate tamper-proof checksum for audit data.
        
        Args:
            audit_data: Audit data dictionary
            
        Returns:
            str: SHA-256 checksum
        """
        # Create deterministic string representation
        data_copy = audit_data.copy()
        data_copy.pop("checksum", None)  # Remove checksum from calculation
        data_copy.pop("previous_checksum", None)  # Remove previous checksum
        
        # Sort keys for consistent ordering
        sorted_data = json.dumps(data_copy, sort_keys=True, separators=(',', ':'))
        
        # Add secret salt for additional security
        salt = os.getenv("AUDIT_CHECKSUM_SALT", "default_audit_salt_2024")
        salted_data = f"{sorted_data}{salt}"
        
        # Calculate SHA-256 hash
        return hashlib.sha256(salted_data.encode('utf-8')).hexdigest()
    
    def _get_last_checksum(self) -> Optional[str]:
        """
        Get the checksum of the last audit log entry.
        
        Returns:
            Optional[str]: Last checksum or None if no entries exist
        """
        try:
            if not self.db_session_factory:
                return None
            
            session = self.db_session_factory()
            try:
                last_entry = session.query(AuditLogORM).order_by(
                    AuditLogORM.timestamp.desc()
                ).first()
                
                return last_entry.checksum if last_entry else None
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to get last checksum: {e}")
            return None
    
    def _store_in_database(self, audit_data: Dict[str, Any]) -> None:
        """
        Store audit log entry in database.
        
        Args:
            audit_data: Audit data to store
        """
        session = self.db_session_factory()
        try:
            # Calculate expiration date based on retention policy
            from src.utils.security import data_protection_manager
            retention_period = data_protection_manager.get_retention_policy("audit_logs")
            expires_at = datetime.utcnow() + retention_period
            
            audit_log = AuditLogORM(
                id=audit_data["id"],
                event_type=audit_data["event_type"],
                severity=audit_data["severity"],
                event_description=audit_data["event_description"],
                user_id=audit_data["user_id"],
                username=audit_data["username"],
                ip_address=audit_data["ip_address"],
                user_agent=audit_data["user_agent"],
                resource_type=audit_data["resource_type"],
                resource_id=audit_data["resource_id"],
                resource_name=audit_data["resource_name"],
                request_method=audit_data["request_method"],
                request_path=audit_data["request_path"],
                request_params=audit_data["request_params"],
                response_status=audit_data["response_status"],
                response_message=audit_data["response_message"],
                metadata=audit_data["metadata"],
                tags=audit_data["tags"],
                checksum=audit_data["checksum"],
                previous_checksum=audit_data["previous_checksum"],
                expires_at=expires_at
            )
            
            session.add(audit_log)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store audit log in database: {e}")
            raise
        finally:
            session.close()
    
    def _store_in_file(self, audit_data: Dict[str, Any]) -> None:
        """
        Store audit log entry in file as backup.
        
        Args:
            audit_data: Audit data to store
        """
        try:
            # Encrypt sensitive data before writing to file
            encrypted_data = encryption_manager.encrypt_dict(audit_data)
            
            # Write to file with timestamp
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "encrypted_data": encrypted_data
            }
            
            with open(self.audit_file_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
        except Exception as e:
            logger.error(f"Failed to store audit log in file: {e}")
            raise
    
    def _store_emergency_log(self, event_type: AuditEventType, description: str, error: str) -> None:
        """
        Store emergency log entry when normal logging fails.
        
        Args:
            event_type: Event type
            description: Event description
            error: Error that occurred
        """
        try:
            emergency_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type.value,
                "description": description,
                "error": error,
                "emergency": True
            }
            
            emergency_file = os.path.join(os.path.dirname(self.audit_file_path), "emergency_audit.log")
            with open(emergency_file, 'a') as f:
                f.write(json.dumps(emergency_entry) + '\n')
                
        except Exception:
            # Last resort - log to system logger
            logger.critical(f"EMERGENCY AUDIT LOG FAILURE: {event_type.value} - {description} - {error}")
    
    def _ensure_audit_file_exists(self) -> None:
        """Ensure audit log file and directory exist."""
        try:
            os.makedirs(os.path.dirname(self.audit_file_path), exist_ok=True)
            
            if not os.path.exists(self.audit_file_path):
                with open(self.audit_file_path, 'w') as f:
                    f.write("")  # Create empty file
            
            # Set restrictive permissions
            os.chmod(self.audit_file_path, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to ensure audit file exists: {e}")


# Global audit logger instance
audit_logger = AuditLogger()