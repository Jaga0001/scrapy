"""
Pydantic schemas for API request and response validation.

This module contains all the Pydantic models used for API request validation
and response serialization, separate from the core business models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.models.pydantic_models import (
    JobStatus, ContentType, ScrapingConfig, ScrapingJob, 
    ScrapedData, User, UserRole, JWTPayload
)


# Request schemas
class CreateJobRequest(BaseModel):
    """Request schema for creating a new scraping job."""
    
    url: str = Field(..., description="Target URL to scrape")
    config: Optional[ScrapingConfig] = Field(
        default=None, 
        description="Scraping configuration (uses defaults if not provided)"
    )
    tags: Optional[List[str]] = Field(
        default=None, 
        description="Tags for job categorization"
    )
    priority: Optional[int] = Field(
        default=5, 
        ge=1, 
        le=10, 
        description="Job priority (1=highest, 10=lowest)"
    )
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


class UpdateJobRequest(BaseModel):
    """Request schema for updating a scraping job."""
    
    status: Optional[JobStatus] = Field(default=None, description="New job status")
    priority: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=10, 
        description="New job priority"
    )
    tags: Optional[List[str]] = Field(default=None, description="Updated tags")


class DataQueryRequest(BaseModel):
    """Request schema for querying scraped data."""
    
    job_ids: Optional[List[str]] = Field(
        default=None, 
        description="Filter by specific job IDs"
    )
    urls: Optional[List[str]] = Field(
        default=None, 
        description="Filter by specific URLs"
    )
    date_from: Optional[datetime] = Field(
        default=None, 
        description="Start date for data range"
    )
    date_to: Optional[datetime] = Field(
        default=None, 
        description="End date for data range"
    )
    min_confidence: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Minimum confidence score"
    )
    content_type: Optional[ContentType] = Field(
        default=None, 
        description="Filter by content type"
    )
    ai_processed: Optional[bool] = Field(
        default=None, 
        description="Filter by AI processing status"
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=1000, description="Items per page")
    sort_by: Optional[str] = Field(
        default="extracted_at", 
        description="Field to sort by"
    )
    sort_order: Optional[str] = Field(
        default="desc", 
        pattern="^(asc|desc)$", 
        description="Sort order"
    )
    
    @field_validator('date_to')
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate date range is logical."""
        if v and info.data.get('date_from') and v < info.data['date_from']:
            raise ValueError("date_to must be after date_from")
        return v


class DataExportRequest(BaseModel):
    """Request schema for data export operations."""
    
    format: str = Field(..., pattern="^(csv|json|xlsx)$", description="Export format")
    job_ids: Optional[List[str]] = Field(default=None, description="Specific job IDs to export")
    date_from: Optional[datetime] = Field(default=None, description="Start date for data range")
    date_to: Optional[datetime] = Field(default=None, description="End date for data range")
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum confidence score")
    include_raw_html: bool = Field(default=False, description="Include raw HTML in export")
    fields: Optional[List[str]] = Field(default=None, description="Specific fields to include")
    
    @field_validator('date_to')
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate date range is logical."""
        if v and info.data.get('date_from') and v < info.data['date_from']:
            raise ValueError("date_to must be after date_from")
        return v


class BulkJobRequest(BaseModel):
    """Request schema for creating multiple scraping jobs."""
    
    urls: List[str] = Field(..., min_length=1, max_length=100, description="URLs to scrape")
    config: Optional[ScrapingConfig] = Field(
        default=None, 
        description="Common configuration for all jobs"
    )
    tags: Optional[List[str]] = Field(
        default=None, 
        description="Common tags for all jobs"
    )
    priority: Optional[int] = Field(
        default=5, 
        ge=1, 
        le=10, 
        description="Common priority for all jobs"
    )
    
    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v):
        """Validate all URLs are properly formatted."""
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format: {url}")
        return v


# Response schemas
class JobResponse(BaseModel):
    """Response schema for job-related endpoints."""
    
    job: ScrapingJob
    message: str = "Operation completed successfully"


class JobListResponse(BaseModel):
    """Response schema for job listing endpoints."""
    
    jobs: List[ScrapingJob]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


class DataResponse(BaseModel):
    """Response schema for data retrieval endpoints."""
    
    data: List[ScrapedData]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class DataSummaryResponse(BaseModel):
    """Response schema for data summary statistics."""
    
    total_records: int
    total_jobs: int
    average_confidence: float
    content_type_distribution: Dict[str, int]
    date_range: Dict[str, Optional[datetime]]
    quality_metrics: Dict[str, Any]


class ExportResponse(BaseModel):
    """Response schema for data export endpoints."""
    
    export_id: str
    status: str
    format: Optional[str] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    filename: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    message: str = "Export request processed"


class HealthResponse(BaseModel):
    """Response schema for health check endpoints."""
    
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    uptime_seconds: float
    database_connected: bool
    redis_connected: bool
    active_jobs: int
    system_metrics: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Response schema for error responses."""
    
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Response schema for validation error responses."""
    
    error: str = "Validation Error"
    message: str = "The request contains invalid data"
    details: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JobStatsResponse(BaseModel):
    """Response schema for job statistics."""
    
    total_jobs: int
    jobs_by_status: Dict[JobStatus, int]
    average_completion_time: Optional[float]
    success_rate: float
    most_common_errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


class SystemStatsResponse(BaseModel):
    """Response schema for system statistics."""
    
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    queue_size: int
    worker_status: Dict[str, Any]
    recent_performance: List[Dict[str, Any]]


# Authentication schemas
class LoginRequest(BaseModel):
    """Request schema for user login."""
    
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v.lower()


class LoginResponse(BaseModel):
    """Response schema for successful login."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: User = Field(..., description="User information")


class TokenRequest(BaseModel):
    """Request schema for authentication token."""
    
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    """Response schema for authentication token."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""
    
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Response schema for token refresh."""
    
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserRegistrationRequest(BaseModel):
    """Request schema for user registration."""
    
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    full_name: Optional[str] = Field(default=None, max_length=100, description="Full name")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        import re
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    """Response schema for user information."""
    
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(default=None, description="Full name")
    roles: List[str] = Field(..., description="User roles")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="User creation timestamp")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")


class TokenValidationResponse(BaseModel):
    """Response schema for token validation."""
    
    valid: bool = Field(..., description="Whether token is valid")
    token_type: Optional[str] = Field(default=None, description="Token type")
    user_id: Optional[str] = Field(default=None, description="User ID")
    username: Optional[str] = Field(default=None, description="Username")
    expires_at: Optional[int] = Field(default=None, description="Token expiration timestamp")


# Webhook schemas
class WebhookRequest(BaseModel):
    """Request schema for webhook configuration."""
    
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Events to subscribe to")
    secret: Optional[str] = Field(default=None, description="Webhook secret for verification")
    active: bool = Field(default=True, description="Whether webhook is active")
    
    @field_validator('url')
    @classmethod
    def validate_webhook_url(cls, v):
        """Validate webhook URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v


class WebhookResponse(BaseModel):
    """Response schema for webhook operations."""
    
    webhook_id: str
    url: str
    events: List[str]
    active: bool
    created_at: datetime
    message: str = "Webhook configured successfully"


# Batch operation schemas
class BatchOperationRequest(BaseModel):
    """Request schema for batch operations."""
    
    operation: str = Field(..., description="Operation to perform")
    job_ids: List[str] = Field(..., min_length=1, description="Job IDs to operate on")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional parameters for the operation"
    )


class BatchOperationResponse(BaseModel):
    """Response schema for batch operations."""
    
    operation_id: str
    operation: str
    total_items: int
    successful_items: int
    failed_items: int
    results: List[Dict[str, Any]]
    message: str = "Batch operation completed"