"""
Custom exception classes for the web scraper system.

This module defines a hierarchy of custom exceptions that provide
specific error handling for different failure scenarios in the system.
"""

from typing import Any, Dict, Optional
from enum import Enum


class ErrorSeverity(str, Enum):
    """Error severity levels for notification and handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScraperBaseException(Exception):
    """
    Base exception class for all scraper-related errors.
    
    Provides common functionality for error tracking, severity levels,
    and context information.
    """
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_after: Optional[float] = None
    ):
        """
        Initialize base exception.
        
        Args:
            message: Human-readable error message
            severity: Error severity level
            context: Additional context information
            recoverable: Whether this error can be recovered from
            retry_after: Suggested retry delay in seconds
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.context = context or {}
        self.recoverable = recoverable
        self.retry_after = retry_after
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after
        }


# Scraping-related exceptions
class ScrapingException(ScraperBaseException):
    """Base class for scraping-related errors."""
    pass


class WebDriverException(ScrapingException):
    """WebDriver initialization or operation failures."""
    
    def __init__(
        self,
        message: str,
        driver_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context["driver_type"] = driver_type


class PageLoadException(ScrapingException):
    """Page loading failures."""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "url": url,
            "status_code": status_code
        })


class ElementNotFoundException(ScrapingException):
    """Element selection/interaction failures."""
    
    def __init__(
        self,
        message: str,
        selector: Optional[str] = None,
        element_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "selector": selector,
            "element_type": element_type
        })


class ContentExtractionException(ScrapingException):
    """Content extraction and parsing failures."""
    
    def __init__(
        self,
        message: str,
        content_type: Optional[str] = None,
        extraction_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "content_type": content_type,
            "extraction_method": extraction_method
        })


class AntiDetectionException(ScrapingException):
    """Anti-bot detection and blocking."""
    
    def __init__(
        self,
        message: str,
        detection_type: Optional[str] = None,
        blocked_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            retry_after=300.0,  # 5 minutes default
            **kwargs
        )
        self.context.update({
            "detection_type": detection_type,
            "blocked_url": blocked_url
        })


# AI Processing exceptions
class AIProcessingException(ScraperBaseException):
    """Base class for AI processing errors."""
    pass


class AIServiceException(AIProcessingException):
    """AI service API failures."""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        api_error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "service_name": service_name,
            "api_error_code": api_error_code
        })


class ContentProcessingException(AIProcessingException):
    """Content analysis and processing failures."""
    
    def __init__(
        self,
        message: str,
        processing_stage: Optional[str] = None,
        content_length: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "processing_stage": processing_stage,
            "content_length": content_length
        })


class ConfidenceThresholdException(AIProcessingException):
    """Low confidence score in AI processing results."""
    
    def __init__(
        self,
        message: str,
        confidence_score: Optional[float] = None,
        threshold: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            recoverable=True,
            **kwargs
        )
        self.context.update({
            "confidence_score": confidence_score,
            "threshold": threshold
        })


# Data processing exceptions
class DataProcessingException(ScraperBaseException):
    """Base class for data processing errors."""
    pass


class DataValidationException(DataProcessingException):
    """Data validation and schema errors."""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        field_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "validation_errors": validation_errors,
            "field_name": field_name
        })


class DataCleaningException(DataProcessingException):
    """Data cleaning and transformation errors."""
    
    def __init__(
        self,
        message: str,
        cleaning_stage: Optional[str] = None,
        data_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "cleaning_stage": cleaning_stage,
            "data_type": data_type
        })


class DuplicateDataException(DataProcessingException):
    """Duplicate data detection errors."""
    
    def __init__(
        self,
        message: str,
        duplicate_count: Optional[int] = None,
        similarity_score: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        self.context.update({
            "duplicate_count": duplicate_count,
            "similarity_score": similarity_score
        })


# Storage and database exceptions
class StorageException(ScraperBaseException):
    """Base class for storage-related errors."""
    pass


class DatabaseException(StorageException):
    """Database connection and operation errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "operation": operation,
            "table_name": table_name
        })


class ConnectionPoolException(DatabaseException):
    """Database connection pool errors."""
    
    def __init__(
        self,
        message: str,
        pool_size: Optional[int] = None,
        active_connections: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.context.update({
            "pool_size": pool_size,
            "active_connections": active_connections
        })


class FileStorageException(StorageException):
    """File system storage errors."""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "file_path": file_path,
            "operation": operation
        })


# API and network exceptions
class APIException(ScraperBaseException):
    """Base class for API-related errors."""
    pass


class RateLimitException(APIException):
    """Rate limiting errors."""
    
    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        reset_time: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            retry_after=reset_time,
            **kwargs
        )
        self.context.update({
            "limit": limit,
            "reset_time": reset_time
        })


class AuthenticationException(APIException):
    """Authentication and authorization errors."""
    
    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )
        self.context["auth_type"] = auth_type


class NetworkException(APIException):
    """Network connectivity and timeout errors."""
    
    def __init__(
        self,
        message: str,
        timeout: Optional[float] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "timeout": timeout,
            "endpoint": endpoint
        })


# Job and queue exceptions
class JobException(ScraperBaseException):
    """Base class for job processing errors."""
    pass


class JobQueueException(JobException):
    """Job queue operation errors."""
    
    def __init__(
        self,
        message: str,
        queue_name: Optional[str] = None,
        job_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "queue_name": queue_name,
            "job_id": job_id
        })


class JobTimeoutException(JobException):
    """Job execution timeout errors."""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        timeout_duration: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.context.update({
            "job_id": job_id,
            "timeout_duration": timeout_duration
        })


class ResourceExhaustionException(JobException):
    """System resource exhaustion errors."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        current_usage: Optional[float] = None,
        limit: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.context.update({
            "resource_type": resource_type,
            "current_usage": current_usage,
            "limit": limit
        })


# Configuration exceptions
class ConfigurationException(ScraperBaseException):
    """Configuration and setup errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            **kwargs
        )
        self.context.update({
            "config_key": config_key,
            "config_file": config_file
        })


# Export exceptions
class ExportException(ScraperBaseException):
    """Data export operation errors."""
    
    def __init__(
        self,
        message: str,
        export_format: Optional[str] = None,
        record_count: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.context.update({
            "export_format": export_format,
            "record_count": record_count
        })


def get_exception_by_severity(severity: ErrorSeverity) -> list:
    """
    Get all exception classes by severity level.
    
    Args:
        severity: Error severity level
        
    Returns:
        List of exception classes with the specified severity
    """
    import inspect
    
    exceptions = []
    for name, obj in globals().items():
        if (inspect.isclass(obj) and 
            issubclass(obj, ScraperBaseException) and 
            obj != ScraperBaseException):
            # Create instance to check default severity
            try:
                instance = obj("test")
                if instance.severity == severity:
                    exceptions.append(obj)
            except TypeError:
                # Skip if constructor requires additional args
                pass
    
    return exceptions


def is_recoverable_error(exception: Exception) -> bool:
    """
    Check if an exception is recoverable.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if the error is recoverable, False otherwise
    """
    if isinstance(exception, ScraperBaseException):
        return exception.recoverable
    
    # Default recovery rules for standard exceptions
    recoverable_types = (
        ConnectionError,
        TimeoutError,
        OSError,
        IOError
    )
    
    non_recoverable_types = (
        ValueError,
        TypeError,
        AttributeError,
        ImportError,
        SyntaxError
    )
    
    if isinstance(exception, recoverable_types):
        return True
    elif isinstance(exception, non_recoverable_types):
        return False
    
    # Default to recoverable for unknown exceptions
    return True


def get_retry_delay(exception: Exception) -> Optional[float]:
    """
    Get suggested retry delay for an exception.
    
    Args:
        exception: Exception to check
        
    Returns:
        Retry delay in seconds, or None if no specific delay suggested
    """
    if isinstance(exception, ScraperBaseException):
        return exception.retry_after
    
    # Default retry delays for common exceptions
    if isinstance(exception, ConnectionError):
        return 30.0  # 30 seconds for connection errors
    elif isinstance(exception, TimeoutError):
        return 60.0  # 1 minute for timeout errors
    
    return None