"""
Comprehensive type hints for data transformation functions.

This module provides type definitions and type hints for all data transformation
operations in the web scraper project, ensuring type safety and consistency.
"""

from datetime import datetime
from typing import (
    Any, Dict, List, Optional, Union, Tuple, Callable, TypeVar, Generic,
    Protocol, runtime_checkable, Literal, TypedDict, NamedTuple
)
from uuid import UUID

from src.models.pydantic_models import (
    ScrapingJob, ScrapedData, ScrapingConfig, ScrapingResult,
    JobStatus, ContentType
)

# Type aliases for common data structures
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONDict = Dict[str, JSONValue]
JSONList = List[JSONValue]

# Content processing types
RawContent = Union[str, bytes]
ProcessedContent = Dict[str, Any]
ContentMetadata = Dict[str, Any]

# AI processing types
AIProcessingResult = Dict[str, Any]
ConfidenceScore = float  # 0.0 to 1.0
EntityList = List[Dict[str, Any]]
ClassificationResult = Dict[str, Any]

# Export types
ExportFormat = Literal["csv", "json", "xlsx"]
ExportData = List[Dict[str, Any]]
ExportFilters = Dict[str, Any]

# Database types
DatabaseRecord = Dict[str, Any]
QueryResult = List[DatabaseRecord]
QueryFilters = Dict[str, Any]

# API types
APIResponse = Dict[str, Any]
APIError = Dict[str, str]
PaginationInfo = Dict[str, Union[int, bool]]

# Job processing types
JobQueue = List[ScrapingJob]
JobResult = Union[ScrapingResult, Exception]
JobMetrics = Dict[str, Union[int, float]]

# Generic type variables
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class ContentProcessor(Protocol):
    """Protocol for content processing functions."""
    
    async def process(
        self,
        content: RawContent,
        content_type: ContentType,
        metadata: Optional[ContentMetadata] = None
    ) -> ProcessedContent:
        """Process raw content into structured data."""
        ...


class DataTransformer(Protocol):
    """Protocol for data transformation functions."""
    
    def transform(
        self,
        input_data: Dict[str, Any],
        transformation_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data according to rules."""
        ...


class DataValidator(Protocol):
    """Protocol for data validation functions."""
    
    def validate(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate data against schema, return (is_valid, errors)."""
        ...


class DataExporter(Protocol):
    """Protocol for data export functions."""
    
    async def export(
        self,
        data: ExportData,
        format: ExportFormat,
        options: Dict[str, Any]
    ) -> str:
        """Export data to specified format, return file path."""
        ...


# Typed dictionaries for structured data
class ScrapingJobDict(TypedDict):
    """Typed dictionary for scraping job data."""
    id: str
    url: str
    status: JobStatus
    config: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_pages: int
    pages_completed: int
    pages_failed: int
    error_message: Optional[str]
    retry_count: int
    user_id: Optional[str]
    tags: List[str]
    priority: int


class ScrapedDataDict(TypedDict):
    """Typed dictionary for scraped data."""
    id: str
    job_id: str
    url: str
    content: Dict[str, Any]
    raw_html: Optional[str]
    content_type: ContentType
    content_metadata: Dict[str, Any]
    confidence_score: float
    ai_processed: bool
    ai_metadata: Dict[str, Any]
    data_quality_score: float
    validation_errors: List[str]
    extracted_at: datetime
    processed_at: Optional[datetime]
    content_length: int
    load_time: float


class ExportRequestDict(TypedDict, total=False):
    """Typed dictionary for export request data."""
    format: ExportFormat
    job_ids: Optional[List[str]]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    min_confidence: float
    include_raw_html: bool
    fields: Optional[List[str]]


class APIResponseDict(TypedDict, total=False):
    """Typed dictionary for API response data."""
    data: Any
    message: str
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    filters_applied: Dict[str, Any]


class ValidationResult(NamedTuple):
    """Named tuple for validation results."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    data_quality_score: float


class ProcessingMetrics(NamedTuple):
    """Named tuple for processing metrics."""
    processing_time: float
    items_processed: int
    items_failed: int
    success_rate: float
    average_confidence: float


class ExportResult(NamedTuple):
    """Named tuple for export results."""
    file_path: str
    file_size: int
    records_exported: int
    format: ExportFormat
    generation_time: float


# Function type definitions
ContentProcessorFunc = Callable[[RawContent, ContentType], ProcessedContent]
DataTransformFunc = Callable[[Dict[str, Any]], Dict[str, Any]]
DataValidationFunc = Callable[[Dict[str, Any]], ValidationResult]
DataExportFunc = Callable[[ExportData, ExportFormat], ExportResult]
DataCleaningFunc = Callable[[Dict[str, Any]], Dict[str, Any]]
DataFilterFunc = Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]

# Async function type definitions
AsyncContentProcessorFunc = Callable[[RawContent, ContentType], Awaitable[ProcessedContent]]
AsyncDataTransformFunc = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
AsyncDataValidationFunc = Callable[[Dict[str, Any]], Awaitable[ValidationResult]]
AsyncDataExportFunc = Callable[[ExportData, ExportFormat], Awaitable[ExportResult]]

# Generic data processing types
DataProcessor = Callable[[T], T]
AsyncDataProcessor = Callable[[T], Awaitable[T]]
DataMapper = Callable[[T], K]
AsyncDataMapper = Callable[[T], Awaitable[K]]

# Batch processing types
BatchProcessor = Callable[[List[T]], List[K]]
AsyncBatchProcessor = Callable[[List[T]], Awaitable[List[K]]]

# Error handling types
ErrorHandler = Callable[[Exception], Optional[Any]]
AsyncErrorHandler = Callable[[Exception], Awaitable[Optional[Any]]]

# Configuration types
ProcessingConfig = Dict[str, Any]
ValidationConfig = Dict[str, Any]
ExportConfig = Dict[str, Any]
ScrapingConfigDict = Dict[str, Any]

# Monitoring and metrics types
MetricsCollector = Callable[[str, float], None]
PerformanceMonitor = Callable[[str, float], None]
HealthChecker = Callable[[], bool]
AsyncHealthChecker = Callable[[], Awaitable[bool]]

# Database operation types
DatabaseQuery = str
DatabaseParams = Dict[str, Any]
DatabaseResult = List[Dict[str, Any]]
DatabaseTransaction = Callable[[], Any]
AsyncDatabaseTransaction = Callable[[], Awaitable[Any]]

# Queue and job processing types
JobProcessor = Callable[[ScrapingJob], ScrapingResult]
AsyncJobProcessor = Callable[[ScrapingJob], Awaitable[ScrapingResult]]
QueueManager = Protocol
WorkerPool = Protocol

# AI processing types
AIModel = Protocol
AIProcessor = Protocol
EntityExtractor = Callable[[str], EntityList]
ContentClassifier = Callable[[str], ClassificationResult]
ConfidenceCalculator = Callable[[Dict[str, Any]], ConfidenceScore]

# Web scraping types
WebDriver = Protocol
WebElement = Protocol
ScrapingStrategy = Protocol
ContentExtractor = Callable[[str], Dict[str, Any]]
LinkFollower = Callable[[str], List[str]]

# Data quality types
QualityChecker = Callable[[Dict[str, Any]], float]
DataCleaner = Callable[[Dict[str, Any]], Dict[str, Any]]
DuplicateDetector = Callable[[List[Dict[str, Any]]], List[int]]
DataNormalizer = Callable[[Dict[str, Any]], Dict[str, Any]]

# Security and authentication types
AuthToken = str
UserID = str
PermissionChecker = Callable[[UserID, str], bool]
SecurityValidator = Callable[[Dict[str, Any]], bool]

# Logging and monitoring types
Logger = Protocol
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogMessage = str
LogContext = Dict[str, Any]

# Rate limiting types
RateLimiter = Protocol
RequestThrottler = Protocol
BackoffStrategy = Callable[[int], float]

# Caching types
CacheKey = str
CacheValue = Any
CacheManager = Protocol
CacheStrategy = Protocol


@runtime_checkable
class Serializable(Protocol):
    """Protocol for serializable objects."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary."""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Serializable':
        """Create object from dictionary."""
        ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for validatable objects."""
    
    def validate(self) -> ValidationResult:
        """Validate object and return result."""
        ...


@runtime_checkable
class Processable(Protocol):
    """Protocol for processable objects."""
    
    async def process(self) -> Any:
        """Process object and return result."""
        ...


# Generic container types
class DataContainer(Generic[T]):
    """Generic container for data with metadata."""
    
    def __init__(self, data: T, metadata: Optional[Dict[str, Any]] = None):
        self.data = data
        self.metadata = metadata or {}
    
    def get_data(self) -> T:
        """Get contained data."""
        return self.data
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata."""
        return self.metadata


class ProcessingResult(Generic[T]):
    """Generic result container for processing operations."""
    
    def __init__(
        self,
        result: Optional[T] = None,
        error: Optional[Exception] = None,
        metrics: Optional[ProcessingMetrics] = None
    ):
        self.result = result
        self.error = error
        self.metrics = metrics
    
    @property
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return self.error is None
    
    @property
    def is_failure(self) -> bool:
        """Check if processing failed."""
        return self.error is not None


# Type guards
def is_valid_url(value: Any) -> bool:
    """Type guard for valid URLs."""
    return isinstance(value, str) and (value.startswith('http://') or value.startswith('https://'))


def is_valid_confidence_score(value: Any) -> bool:
    """Type guard for valid confidence scores."""
    return isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def is_valid_job_status(value: Any) -> bool:
    """Type guard for valid job statuses."""
    return isinstance(value, str) and value in [status.value for status in JobStatus]


def is_valid_content_type(value: Any) -> bool:
    """Type guard for valid content types."""
    return isinstance(value, str) and value in [ct.value for ct in ContentType]


def is_valid_export_format(value: Any) -> bool:
    """Type guard for valid export formats."""
    return isinstance(value, str) and value in ["csv", "json", "xlsx"]


# Type conversion utilities
def ensure_dict(value: Any) -> Dict[str, Any]:
    """Ensure value is a dictionary."""
    if isinstance(value, dict):
        return value
    return {}


def ensure_list(value: Any) -> List[Any]:
    """Ensure value is a list."""
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def ensure_string(value: Any) -> str:
    """Ensure value is a string."""
    if isinstance(value, str):
        return value
    return str(value) if value is not None else ""


def ensure_float(value: Any) -> float:
    """Ensure value is a float."""
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def ensure_datetime(value: Any) -> Optional[datetime]:
    """Ensure value is a datetime or None."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None