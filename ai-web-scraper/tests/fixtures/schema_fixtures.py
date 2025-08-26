"""
Test fixtures for schema validation and data consistency tests.

This module provides comprehensive test fixtures for all data models,
API schemas, and data transformation scenarios.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import uuid4

from src.models.pydantic_models import (
    ScrapingConfig, ScrapingJob, ScrapedData, ScrapingResult,
    DataExportRequest, JobStatus, ContentType
)
from src.api.schemas import (
    CreateJobRequest, UpdateJobRequest, DataQueryRequest, BulkJobRequest,
    JobResponse, JobListResponse, DataResponse, DataSummaryResponse,
    ExportResponse, HealthResponse, ErrorResponse
)


@pytest.fixture
def sample_scraping_config():
    """Sample scraping configuration for testing."""
    return ScrapingConfig(
        wait_time=10,
        max_retries=3,
        timeout=60,
        use_stealth=True,
        headless=True,
        user_agent="Mozilla/5.0 (compatible; WebScraper/1.0)",
        extract_images=True,
        extract_links=True,
        follow_links=False,
        max_depth=2,
        custom_selectors={
            "title": "h1, .title",
            "content": ".content, .main-text",
            "price": ".price, .cost"
        },
        exclude_selectors=[".ads", ".sidebar", ".footer"],
        delay_between_requests=2.0,
        respect_robots_txt=True,
        javascript_enabled=True,
        load_images=False,
        proxy_url="http://proxy.example.com:8080"
    )


@pytest.fixture
def sample_scraping_job(sample_scraping_config):
    """Sample scraping job for testing."""
    return ScrapingJob(
        id=str(uuid4()),
        url="https://example.com/products",
        config=sample_scraping_config,
        status=JobStatus.RUNNING,
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow() - timedelta(minutes=5),
        total_pages=100,
        pages_completed=45,
        pages_failed=2,
        retry_count=1,
        user_id="user-123",
        tags=["ecommerce", "products", "test"],
        priority=3
    )


@pytest.fixture
def sample_scraped_data():
    """Sample scraped data for testing."""
    return ScrapedData(
        id=str(uuid4()),
        job_id="job-123",
        url="https://example.com/product/123",
        content={
            "title": "Premium Wireless Headphones",
            "price": "$199.99",
            "description": "High-quality wireless headphones with noise cancellation",
            "rating": 4.5,
            "reviews_count": 1250,
            "availability": "in_stock",
            "features": [
                "Noise cancellation",
                "30-hour battery life",
                "Bluetooth 5.0",
                "Quick charge"
            ],
            "specifications": {
                "weight": "250g",
                "frequency_response": "20Hz - 20kHz",
                "impedance": "32 ohms"
            }
        },
        raw_html="<html><head><title>Premium Wireless Headphones</title></head><body>...</body></html>",
        content_type=ContentType.HTML,
        content_metadata={
            "page_load_time": 2.3,
            "dom_elements": 450,
            "images_found": 8,
            "links_found": 25
        },
        confidence_score=0.95,
        ai_processed=True,
        ai_metadata={
            "model": "gemini-2.5",
            "processing_time": 1.8,
            "entities_found": 12,
            "classification": {
                "category": "ecommerce",
                "subcategory": "electronics",
                "confidence": 0.98
            },
            "sentiment": {
                "overall": "positive",
                "score": 0.85
            }
        },
        data_quality_score=0.92,
        validation_errors=[],
        extracted_at=datetime.utcnow(),
        processed_at=datetime.utcnow() - timedelta(seconds=30),
        content_length=2048,
        load_time=2.3
    )


@pytest.fixture
def sample_scraped_data_list():
    """List of sample scraped data for testing."""
    base_data = {
        "job_id": "job-123",
        "content_type": ContentType.HTML,
        "ai_processed": True,
        "extracted_at": datetime.utcnow()
    }
    
    return [
        ScrapedData(
            id=str(uuid4()),
            url="https://example.com/product/1",
            content={
                "title": "Product 1",
                "price": "$99.99",
                "category": "Electronics"
            },
            confidence_score=0.95,
            **base_data
        ),
        ScrapedData(
            id=str(uuid4()),
            url="https://example.com/product/2",
            content={
                "title": "Product 2",
                "price": "$149.99",
                "category": "Electronics"
            },
            confidence_score=0.88,
            **base_data
        ),
        ScrapedData(
            id=str(uuid4()),
            url="https://example.com/article/1",
            content={
                "title": "Tech News Article",
                "author": "John Doe",
                "content": "Latest technology trends..."
            },
            confidence_score=0.92,
            content_type=ContentType.TEXT,
            **base_data
        )
    ]


@pytest.fixture
def sample_scraping_result(sample_scraped_data_list):
    """Sample scraping result for testing."""
    return ScrapingResult(
        job_id="job-123",
        success=True,
        data=sample_scraped_data_list,
        total_time=45.5,
        pages_scraped=3,
        pages_failed=0,
        average_confidence=0.92,
        data_quality_summary={
            "total_records": 3,
            "high_confidence_records": 3,
            "validation_errors": 0,
            "average_content_length": 1024,
            "content_types": {
                "html": 2,
                "text": 1
            }
        }
    )


@pytest.fixture
def sample_export_request():
    """Sample data export request for testing."""
    return DataExportRequest(
        format="csv",
        job_ids=["job-123", "job-456"],
        date_from=datetime.utcnow() - timedelta(days=7),
        date_to=datetime.utcnow(),
        min_confidence=0.8,
        include_raw_html=False,
        fields=["url", "content", "confidence_score", "extracted_at"]
    )


@pytest.fixture
def sample_create_job_request(sample_scraping_config):
    """Sample create job request for testing."""
    return CreateJobRequest(
        url="https://example.com/products",
        config=sample_scraping_config,
        tags=["ecommerce", "test"],
        priority=5
    )


@pytest.fixture
def sample_update_job_request():
    """Sample update job request for testing."""
    return UpdateJobRequest(
        status=JobStatus.CANCELLED,
        priority=8,
        tags=["updated", "cancelled"]
    )


@pytest.fixture
def sample_data_query_request():
    """Sample data query request for testing."""
    return DataQueryRequest(
        job_ids=["job-123", "job-456"],
        urls=["https://example.com/product/1", "https://example.com/product/2"],
        date_from=datetime.utcnow() - timedelta(days=30),
        date_to=datetime.utcnow(),
        min_confidence=0.8,
        content_type=ContentType.HTML,
        ai_processed=True,
        page=1,
        page_size=50,
        sort_by="confidence_score",
        sort_order="desc"
    )


@pytest.fixture
def sample_bulk_job_request(sample_scraping_config):
    """Sample bulk job request for testing."""
    return BulkJobRequest(
        urls=[
            "https://example.com/product/1",
            "https://example.com/product/2",
            "https://example.com/product/3",
            "https://example.com/category/electronics",
            "https://example.com/category/books"
        ],
        config=sample_scraping_config,
        tags=["bulk", "products"],
        priority=6
    )


@pytest.fixture
def sample_job_response(sample_scraping_job):
    """Sample job response for testing."""
    return JobResponse(
        job=sample_scraping_job,
        message="Job created successfully"
    )


@pytest.fixture
def sample_job_list_response():
    """Sample job list response for testing."""
    jobs = [
        ScrapingJob(
            id=f"job-{i}",
            url=f"https://example.com/page/{i}",
            status=JobStatus.COMPLETED if i % 2 == 0 else JobStatus.RUNNING,
            created_at=datetime.utcnow() - timedelta(hours=i)
        )
        for i in range(1, 6)
    ]
    
    return JobListResponse(
        jobs=jobs,
        total_count=25,
        page=1,
        page_size=5,
        has_next=True,
        has_previous=False
    )


@pytest.fixture
def sample_data_response(sample_scraped_data_list):
    """Sample data response for testing."""
    return DataResponse(
        data=sample_scraped_data_list,
        total_count=150,
        page=2,
        page_size=50,
        has_next=True,
        has_previous=True,
        filters_applied={
            "min_confidence": 0.8,
            "content_type": "html",
            "ai_processed": True
        }
    )


@pytest.fixture
def sample_data_summary_response():
    """Sample data summary response for testing."""
    return DataSummaryResponse(
        total_records=1500,
        total_jobs=45,
        average_confidence=0.87,
        content_type_distribution={
            "html": 1200,
            "json": 200,
            "text": 100
        },
        date_range={
            "earliest": datetime.utcnow() - timedelta(days=30),
            "latest": datetime.utcnow()
        },
        quality_metrics={
            "high_confidence_records": 1350,
            "ai_processed_records": 1450,
            "validation_errors": 25,
            "average_content_length": 2048,
            "duplicate_records": 15
        }
    )


@pytest.fixture
def sample_export_response():
    """Sample export response for testing."""
    return ExportResponse(
        export_id="export-123",
        status="completed",
        download_url="/api/v1/data/exports/export-123/download",
        file_size=2048000,
        created_at=datetime.utcnow() - timedelta(minutes=10),
        estimated_completion=None,
        message="Export completed successfully"
    )


@pytest.fixture
def sample_health_response():
    """Sample health response for testing."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        uptime_seconds=86400.0,
        database_connected=True,
        redis_connected=True,
        active_jobs=5,
        system_metrics={
            "cpu_usage": 45.2,
            "memory_usage": 68.5,
            "disk_usage": 32.1,
            "active_connections": 25,
            "queue_size": 12
        }
    )


@pytest.fixture
def sample_error_response():
    """Sample error response for testing."""
    return ErrorResponse(
        error="ValidationError",
        message="The provided data is invalid",
        details={
            "field": "url",
            "issue": "Invalid URL format",
            "provided_value": "not-a-url"
        },
        request_id="req-123"
    )


@pytest.fixture
def sample_ai_processing_data():
    """Sample AI processing data for testing."""
    return {
        "entities": [
            {
                "type": "PRODUCT",
                "value": "Wireless Headphones",
                "confidence": 0.95,
                "context": "Premium Wireless Headphones with noise cancellation"
            },
            {
                "type": "PRICE",
                "value": "$199.99",
                "confidence": 0.98,
                "context": "Price: $199.99"
            },
            {
                "type": "RATING",
                "value": "4.5",
                "confidence": 0.92,
                "context": "Rating: 4.5 out of 5 stars"
            }
        ],
        "classification": {
            "primary_category": "ecommerce",
            "subcategories": ["electronics", "audio"],
            "confidence": 0.96,
            "content_type": "product_listing"
        },
        "sentiment": {
            "overall": "positive",
            "score": 0.85,
            "aspects": [
                {"aspect": "quality", "sentiment": "positive", "score": 0.9},
                {"aspect": "price", "sentiment": "neutral", "score": 0.6},
                {"aspect": "features", "sentiment": "positive", "score": 0.95}
            ]
        },
        "key_topics": [
            {"topic": "audio_quality", "relevance": 0.9, "keywords": ["sound", "audio", "quality"]},
            {"topic": "battery_life", "relevance": 0.8, "keywords": ["battery", "30-hour", "charge"]},
            {"topic": "connectivity", "relevance": 0.7, "keywords": ["bluetooth", "wireless", "connection"]}
        ],
        "summary": "Premium wireless headphones with advanced noise cancellation technology and 30-hour battery life.",
        "language": "en",
        "metadata": {
            "word_count": 245,
            "reading_level": "intermediate",
            "content_quality": "high",
            "processing_timestamp": datetime.utcnow().isoformat(),
            "model_version": "gemini-2.5"
        }
    }


@pytest.fixture
def sample_structured_data():
    """Sample structured data extraction results for testing."""
    return {
        "structured_data": {
            "products": [
                {
                    "name": "Wireless Headphones",
                    "price": "$199.99",
                    "description": "Premium wireless headphones with noise cancellation",
                    "availability": "in_stock",
                    "rating": 4.5,
                    "reviews_count": 1250,
                    "features": [
                        "Noise cancellation",
                        "30-hour battery life",
                        "Bluetooth 5.0"
                    ]
                }
            ],
            "contacts": [
                {
                    "type": "email",
                    "value": "support@example.com",
                    "label": "Customer Support"
                },
                {
                    "type": "phone",
                    "value": "+1-800-555-0123",
                    "label": "Sales"
                }
            ],
            "navigation": [
                {"text": "Home", "url": "/", "level": 1},
                {"text": "Products", "url": "/products", "level": 1},
                {"text": "Electronics", "url": "/products/electronics", "level": 2}
            ],
            "media": [
                {
                    "type": "image",
                    "src": "/images/headphones-main.jpg",
                    "alt": "Wireless Headphones",
                    "caption": "Premium Wireless Headphones"
                }
            ]
        },
        "metadata": {
            "page_title": "Premium Wireless Headphones - Example Store",
            "meta_description": "Shop premium wireless headphones with advanced features",
            "keywords": ["headphones", "wireless", "audio", "electronics"],
            "language": "en",
            "structure_complexity": "moderate",
            "data_richness": "high",
            "processing_timestamp": datetime.utcnow().isoformat(),
            "extraction_method": "gemini_ai"
        }
    }


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for testing."""
    return [
        {
            "field": "url",
            "message": "Invalid URL format",
            "code": "invalid_format",
            "provided_value": "not-a-url"
        },
        {
            "field": "priority",
            "message": "Priority must be between 1 and 10",
            "code": "out_of_range",
            "provided_value": 15
        },
        {
            "field": "config.wait_time",
            "message": "Wait time must be between 1 and 60 seconds",
            "code": "out_of_range",
            "provided_value": 0
        }
    ]


@pytest.fixture
def sample_export_data():
    """Sample data for export testing."""
    return [
        {
            "id": "data-1",
            "job_id": "job-123",
            "url": "https://example.com/product/1",
            "content_title": "Product 1",
            "content_price": "$99.99",
            "confidence_score": 0.95,
            "ai_processed": True,
            "extracted_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "data-2",
            "job_id": "job-123",
            "url": "https://example.com/product/2",
            "content_title": "Product 2",
            "content_price": "$149.99",
            "confidence_score": 0.88,
            "ai_processed": True,
            "extracted_at": "2024-01-15T10:35:00Z"
        },
        {
            "id": "data-3",
            "job_id": "job-456",
            "url": "https://example.com/article/1",
            "content_title": "Tech Article",
            "content_author": "John Doe",
            "confidence_score": 0.92,
            "ai_processed": True,
            "extracted_at": "2024-01-15T11:00:00Z"
        }
    ]


@pytest.fixture
def sample_performance_metrics():
    """Sample performance metrics for testing."""
    return {
        "processing_time": 45.2,
        "items_processed": 150,
        "items_failed": 3,
        "success_rate": 0.98,
        "average_confidence": 0.89,
        "throughput_per_minute": 25.5,
        "memory_usage_mb": 256.8,
        "cpu_usage_percent": 42.3,
        "queue_size": 12,
        "active_workers": 4,
        "error_rate": 0.02,
        "retry_rate": 0.05
    }


@pytest.fixture
def sample_database_records():
    """Sample database records for testing."""
    return [
        {
            "id": "job-1",
            "url": "https://example.com/page1",
            "status": "completed",
            "created_at": datetime.utcnow() - timedelta(hours=2),
            "completed_at": datetime.utcnow() - timedelta(hours=1),
            "pages_completed": 10,
            "pages_failed": 0
        },
        {
            "id": "job-2",
            "url": "https://example.com/page2",
            "status": "running",
            "created_at": datetime.utcnow() - timedelta(minutes=30),
            "started_at": datetime.utcnow() - timedelta(minutes=25),
            "pages_completed": 5,
            "pages_failed": 1
        },
        {
            "id": "job-3",
            "url": "https://example.com/page3",
            "status": "failed",
            "created_at": datetime.utcnow() - timedelta(hours=3),
            "started_at": datetime.utcnow() - timedelta(hours=3),
            "error_message": "Connection timeout",
            "pages_completed": 0,
            "pages_failed": 1
        }
    ]


# Parameterized fixtures for testing different scenarios
@pytest.fixture(params=["csv", "json", "xlsx"])
def export_format(request):
    """Parameterized fixture for different export formats."""
    return request.param


@pytest.fixture(params=[
    JobStatus.PENDING,
    JobStatus.RUNNING,
    JobStatus.COMPLETED,
    JobStatus.FAILED,
    JobStatus.CANCELLED
])
def job_status(request):
    """Parameterized fixture for different job statuses."""
    return request.param


@pytest.fixture(params=[
    ContentType.HTML,
    ContentType.TEXT,
    ContentType.JSON,
    ContentType.XML
])
def content_type(request):
    """Parameterized fixture for different content types."""
    return request.param


@pytest.fixture(params=[0.0, 0.5, 0.8, 0.9, 1.0])
def confidence_score(request):
    """Parameterized fixture for different confidence scores."""
    return request.param


@pytest.fixture(params=[1, 5, 10, 25, 50, 100])
def page_size(request):
    """Parameterized fixture for different page sizes."""
    return request.param