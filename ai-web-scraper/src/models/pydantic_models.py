"""
Pydantic models for data validation and serialization.

This module contains the core Pydantic models used throughout the application
for data validation, serialization, and API request/response handling.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class JobStatus(str, Enum):
    """Enumeration of possible job statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentType(str, Enum):
    """Enumeration of content types that can be scraped."""
    HTML = "html"
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    IMAGE = "image"
    DOCUMENT = "document"


class ScrapingConfig(BaseModel):
    """Configuration model for scraping operations."""
    
    # Basic scraping settings
    wait_time: int = Field(default=5, ge=1, le=60, description="Time to wait for page load (seconds)")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum number of retry attempts")
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    
    # Browser settings
    use_stealth: bool = Field(default=True, description="Enable stealth mode to avoid detection")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    user_agent: Optional[str] = Field(default=None, description="Custom user agent string")
    
    # Content extraction settings
    extract_images: bool = Field(default=False, description="Extract image URLs and metadata")
    extract_links: bool = Field(default=False, description="Extract all links from the page")
    follow_links: bool = Field(default=False, description="Follow and scrape linked pages")
    max_depth: int = Field(default=1, ge=1, le=5, description="Maximum depth for link following")
    
    # Selectors and filters
    custom_selectors: Dict[str, str] = Field(
        default_factory=dict, 
        description="Custom CSS selectors for specific data extraction"
    )
    exclude_selectors: List[str] = Field(
        default_factory=list,
        description="CSS selectors for elements to exclude"
    )
    
    # Rate limiting and politeness
    delay_between_requests: float = Field(
        default=1.0, ge=0.1, le=10.0,
        description="Delay between requests in seconds"
    )
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt rules")
    
    # Advanced settings
    javascript_enabled: bool = Field(default=True, description="Enable JavaScript execution")
    load_images: bool = Field(default=False, description="Load images during scraping")
    proxy_url: Optional[str] = Field(default=None, description="Proxy server URL")
    
    @field_validator('custom_selectors')
    @classmethod
    def validate_selectors(cls, v):
        """Validate CSS selectors format."""
        if not isinstance(v, dict):
            raise ValueError("custom_selectors must be a dictionary")
        return v
    
    @field_validator('proxy_url')
    @classmethod
    def validate_proxy_url(cls, v):
        """Validate proxy URL format."""
        if v and not (v.startswith('http://') or v.startswith('https://') or v.startswith('socks://')):
            raise ValueError("proxy_url must start with http://, https://, or socks://")
        return v


class ScrapingJob(BaseModel):
    """Model representing a scraping job."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique job identifier")
    url: str = Field(..., description="Target URL to scrape")
    config: ScrapingConfig = Field(default_factory=ScrapingConfig, description="Scraping configuration")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion timestamp")
    
    # Results and metadata
    total_pages: int = Field(default=0, ge=0, description="Total number of pages to scrape")
    pages_completed: int = Field(default=0, ge=0, description="Number of pages completed")
    pages_failed: int = Field(default=0, ge=0, description="Number of pages that failed")
    
    # Error handling
    error_message: Optional[str] = Field(default=None, description="Error message if job failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts made")
    
    # Additional metadata
    user_id: Optional[str] = Field(default=None, description="User who created the job")
    tags: List[str] = Field(default_factory=list, description="Tags for job categorization")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1=highest, 10=lowest)")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @model_validator(mode='after')
    def validate_pages_completed(self):
        """Ensure pages_completed doesn't exceed total_pages."""
        if self.pages_completed > self.total_pages:
            raise ValueError("pages_completed cannot exceed total_pages")
        return self


class ScrapedData(BaseModel):
    """Model representing scraped data from a single page."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique data record identifier")
    job_id: str = Field(..., description="ID of the scraping job that produced this data")
    url: str = Field(..., description="URL where this data was scraped from")
    
    # Content data
    content: Dict[str, Any] = Field(..., description="Extracted content data")
    raw_html: Optional[str] = Field(default=None, description="Raw HTML content")
    content_type: ContentType = Field(default=ContentType.HTML, description="Type of content scraped")
    
    # Metadata
    content_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the scraping process"
    )
    
    # AI processing results
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="AI confidence score for extracted data quality"
    )
    ai_processed: bool = Field(default=False, description="Whether AI processing was applied")
    ai_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata from AI processing"
    )
    
    # Quality metrics
    data_quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Overall data quality score"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors found"
    )
    
    # Timestamps
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Data extraction timestamp")
    processed_at: Optional[datetime] = Field(default=None, description="AI processing timestamp")
    
    # Content metrics
    content_length: int = Field(default=0, ge=0, description="Length of extracted content")
    load_time: float = Field(default=0.0, ge=0.0, description="Page load time in seconds")
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate content is not empty."""
        if not v:
            raise ValueError("content cannot be empty")
        return v
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


class ScrapingResult(BaseModel):
    """Model representing the result of a scraping operation."""
    
    job_id: str = Field(..., description="ID of the scraping job")
    success: bool = Field(..., description="Whether the scraping was successful")
    data: Optional[List[ScrapedData]] = Field(default=None, description="Scraped data if successful")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Performance metrics
    total_time: float = Field(default=0.0, ge=0.0, description="Total scraping time in seconds")
    pages_scraped: int = Field(default=0, ge=0, description="Number of pages successfully scraped")
    pages_failed: int = Field(default=0, ge=0, description="Number of pages that failed")
    
    # Quality metrics
    average_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Average confidence score across all scraped data"
    )
    data_quality_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of data quality metrics"
    )


class DataExportRequest(BaseModel):
    """Model for data export requests."""
    
    format: str = Field(..., pattern="^(csv|json|xlsx)$", description="Export format")
    job_ids: Optional[List[str]] = Field(default=None, description="Specific job IDs to export")
    date_from: Optional[datetime] = Field(default=None, description="Start date for data range")
    date_to: Optional[datetime] = Field(default=None, description="End date for data range")
    
    # Filtering options
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


# Response models for API
class JobResponse(BaseModel):
    """Response model for job-related API endpoints."""
    job: ScrapingJob
    message: str = "Job processed successfully"


class DataResponse(BaseModel):
    """Response model for data retrieval API endpoints."""
    data: List[ScrapedData]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    database_connected: bool = True
    redis_connected: bool = True