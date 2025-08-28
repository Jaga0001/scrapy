"""
Pydantic models for data validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, model_validator
import re


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
    PDF = "pdf"
    CSV = "csv"


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
    
    # Rate limiting and politeness
    delay_between_requests: float = Field(
        default=1.0, ge=0.1, le=10.0,
        description="Delay between requests in seconds"
    )
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt rules")
    
    # Job metadata (added for consistency with API)
    name: Optional[str] = Field(default=None, description="Human-readable job name")
    max_pages: int = Field(default=10, ge=1, le=1000, description="Maximum pages to scrape")
    
    # Custom selectors for targeted extraction
    custom_selectors: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom CSS selectors for targeted content extraction"
    )
    
    # Exclude selectors to remove unwanted content
    exclude_selectors: List[str] = Field(
        default_factory=list,
        description="CSS selectors for content to exclude from extraction"
    )
    
    # JavaScript execution settings
    javascript_enabled: bool = Field(default=True, description="Enable JavaScript execution in browser")
    
    @field_validator('user_agent')
    @classmethod
    def validate_user_agent(cls, v):
        """Validate user agent string format."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("User agent cannot be empty string")
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
        
        # Additional URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError("Invalid URL format")
        
        return v
    
    @model_validator(mode='after')
    def validate_job_consistency(self):
        """Validate job data consistency."""
        # Ensure pages_completed doesn't exceed total_pages
        if self.total_pages > 0 and self.pages_completed > self.total_pages:
            raise ValueError("pages_completed cannot exceed total_pages")
        
        # Ensure status transitions are logical
        if self.status == JobStatus.COMPLETED and self.completed_at is None:
            self.completed_at = datetime.utcnow()
        
        if self.status == JobStatus.RUNNING and self.started_at is None:
            self.started_at = datetime.utcnow()
        
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
    
    # Content metadata (added for consistency with database model)
    content_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the content"
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
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate content structure."""
        if not isinstance(v, dict):
            raise ValueError("Content must be a dictionary")
        
        # Ensure required content fields
        required_fields = ['title', 'text']
        for field in required_fields:
            if field not in v:
                v[field] = ""  # Set default empty values
        
        return v
    
    @model_validator(mode='after')
    def validate_data_consistency(self):
        """Validate scraped data consistency."""
        # Update content_length based on actual content
        if self.content and 'text' in self.content:
            self.content_length = len(str(self.content['text']))
        
        # Set processed_at if AI processing was applied
        if self.ai_processed and self.processed_at is None:
            self.processed_at = datetime.utcnow()
        
        # Validate quality scores consistency
        if self.confidence_score > 0 and not self.ai_processed:
            self.ai_processed = True
        
        return self


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


# Response models for API
class JobResponse(BaseModel):
    """Response model for job-related API endpoints."""
    job: Union[Dict[str, Any], ScrapingJob]
    message: str = "Job processed successfully"
    
    class Config:
        arbitrary_types_allowed = True


class JobListResponse(BaseModel):
    """Response model for job listing API endpoints."""
    jobs: List[Dict[str, Any]]
    total: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False


class DataResponse(BaseModel):
    """Response model for data retrieval API endpoints."""
    data: List[Dict[str, Any]]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False


class DataListResponse(BaseModel):
    """Response model for scraped data listing."""
    data: List[Dict[str, Any]]
    total: int


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    database_connected: bool = True
    services: Dict[str, str] = Field(default_factory=dict)


class ScrapingResult(BaseModel):
    """Model representing the result of a scraping operation."""
    
    job_id: str = Field(..., description="Unique job identifier")
    success: bool = Field(..., description="Whether the scraping operation was successful")
    data: List[ScrapedData] = Field(default_factory=list, description="List of scraped data")
    
    # Timing and performance metrics
    total_time: float = Field(default=0.0, ge=0.0, description="Total processing time in seconds")
    pages_scraped: int = Field(default=0, ge=0, description="Number of pages successfully scraped")
    pages_failed: int = Field(default=0, ge=0, description="Number of pages that failed to scrape")
    
    # Quality metrics
    average_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Average confidence score across all scraped data"
    )
    
    # Error handling
    error_message: Optional[str] = Field(default=None, description="Error message if operation failed")
    
    # Additional metadata
    data_quality_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of data quality metrics"
    )
    
    @model_validator(mode='after')
    def validate_result_consistency(self):
        """Validate scraping result consistency."""
        # Ensure data count matches pages_scraped
        if len(self.data) != self.pages_scraped:
            # Allow some flexibility for partial failures
            if self.success and len(self.data) == 0:
                self.success = False
                if not self.error_message:
                    self.error_message = "No data scraped despite success flag"
        
        # Calculate average confidence if not set
        if self.data and self.average_confidence == 0.0:
            self.average_confidence = sum(item.confidence_score for item in self.data) / len(self.data)
        
        return self


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)