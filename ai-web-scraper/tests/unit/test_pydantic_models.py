"""
Unit tests for Pydantic models.

This module contains comprehensive tests for all Pydantic models used in the application,
including validation, serialization, and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any

from src.models.pydantic_models import (
    ScrapingConfig,
    ScrapingJob,
    ScrapedData,
    ScrapingResult,
    DataExportRequest,
    JobResponse,
    DataResponse,
    HealthCheckResponse,
    JobStatus,
    ContentType
)


class TestScrapingConfig:
    """Test cases for ScrapingConfig model."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ScrapingConfig()
        
        assert config.wait_time == 5
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.use_stealth is True
        assert config.headless is True
        assert config.user_agent is None
        assert config.extract_images is False
        assert config.extract_links is False
        assert config.follow_links is False
        assert config.max_depth == 1
        assert config.custom_selectors == {}
        assert config.exclude_selectors == []
        assert config.delay_between_requests == 1.0
        assert config.respect_robots_txt is True
        assert config.javascript_enabled is True
        assert config.load_images is False
        assert config.proxy_url is None
    
    def test_valid_configuration(self):
        """Test creating a valid configuration."""
        config = ScrapingConfig(
            wait_time=10,
            max_retries=5,
            timeout=60,
            use_stealth=False,
            headless=False,
            user_agent="Custom User Agent",
            extract_images=True,
            extract_links=True,
            follow_links=True,
            max_depth=3,
            custom_selectors={"title": "h1", "content": ".content"},
            exclude_selectors=[".ads", ".sidebar"],
            delay_between_requests=2.5,
            respect_robots_txt=False,
            javascript_enabled=False,
            load_images=True,
            proxy_url="http://proxy.example.com:8080"
        )
        
        assert config.wait_time == 10
        assert config.max_retries == 5
        assert config.timeout == 60
        assert config.use_stealth is False
        assert config.headless is False
        assert config.user_agent == "Custom User Agent"
        assert config.extract_images is True
        assert config.extract_links is True
        assert config.follow_links is True
        assert config.max_depth == 3
        assert config.custom_selectors == {"title": "h1", "content": ".content"}
        assert config.exclude_selectors == [".ads", ".sidebar"]
        assert config.delay_between_requests == 2.5
        assert config.respect_robots_txt is False
        assert config.javascript_enabled is False
        assert config.load_images is True
        assert config.proxy_url == "http://proxy.example.com:8080"
    
    def test_validation_errors(self):
        """Test validation errors for invalid values."""
        # Test wait_time validation
        with pytest.raises(ValueError):
            ScrapingConfig(wait_time=0)
        
        with pytest.raises(ValueError):
            ScrapingConfig(wait_time=61)
        
        # Test max_retries validation
        with pytest.raises(ValueError):
            ScrapingConfig(max_retries=-1)
        
        with pytest.raises(ValueError):
            ScrapingConfig(max_retries=11)
        
        # Test timeout validation
        with pytest.raises(ValueError):
            ScrapingConfig(timeout=4)
        
        with pytest.raises(ValueError):
            ScrapingConfig(timeout=301)
        
        # Test max_depth validation
        with pytest.raises(ValueError):
            ScrapingConfig(max_depth=0)
        
        with pytest.raises(ValueError):
            ScrapingConfig(max_depth=6)
        
        # Test delay_between_requests validation
        with pytest.raises(ValueError):
            ScrapingConfig(delay_between_requests=0.05)
        
        with pytest.raises(ValueError):
            ScrapingConfig(delay_between_requests=11.0)
    
    def test_proxy_url_validation(self):
        """Test proxy URL validation."""
        # Valid proxy URLs
        valid_urls = [
            "http://proxy.example.com:8080",
            "https://secure-proxy.example.com:3128",
            "socks://socks-proxy.example.com:1080"
        ]
        
        for url in valid_urls:
            config = ScrapingConfig(proxy_url=url)
            assert config.proxy_url == url
        
        # Invalid proxy URLs
        invalid_urls = [
            "ftp://invalid.example.com",
            "proxy.example.com:8080",
            "invalid-protocol://proxy.example.com"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                ScrapingConfig(proxy_url=url)
    
    def test_custom_selectors_validation(self):
        """Test custom selectors validation."""
        # Valid selectors
        config = ScrapingConfig(custom_selectors={"title": "h1", "content": ".content"})
        assert config.custom_selectors == {"title": "h1", "content": ".content"}
        
        # Invalid selectors (not a dict)
        with pytest.raises(ValueError):
            ScrapingConfig(custom_selectors=["h1", ".content"])


class TestScrapingJob:
    """Test cases for ScrapingJob model."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        job = ScrapingJob(url="https://example.com")
        
        assert job.url == "https://example.com"
        assert job.status == JobStatus.PENDING
        assert isinstance(job.config, ScrapingConfig)
        assert isinstance(job.created_at, datetime)
        assert job.started_at is None
        assert job.completed_at is None
        assert job.total_pages == 0
        assert job.pages_completed == 0
        assert job.pages_failed == 0
        assert job.error_message is None
        assert job.retry_count == 0
        assert job.user_id is None
        assert job.tags == []
        assert job.priority == 5
    
    def test_valid_job_creation(self):
        """Test creating a valid scraping job."""
        config = ScrapingConfig(wait_time=10, max_retries=5)
        job = ScrapingJob(
            url="https://example.com",
            config=config,
            status=JobStatus.RUNNING,
            total_pages=100,
            pages_completed=50,
            pages_failed=5,
            error_message="Some error",
            retry_count=2,
            user_id="user123",
            tags=["test", "example"],
            priority=3
        )
        
        assert job.url == "https://example.com"
        assert job.config == config
        assert job.status == JobStatus.RUNNING
        assert job.total_pages == 100
        assert job.pages_completed == 50
        assert job.pages_failed == 5
        assert job.error_message == "Some error"
        assert job.retry_count == 2
        assert job.user_id == "user123"
        assert job.tags == ["test", "example"]
        assert job.priority == 3
    
    def test_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://subdomain.example.com/path?query=value"
        ]
        
        for url in valid_urls:
            job = ScrapingJob(url=url)
            assert job.url == url
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",
            "example.com",
            "www.example.com",
            ""
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                ScrapingJob(url=url)
    
    def test_pages_completed_validation(self):
        """Test pages_completed validation."""
        # Valid case
        job = ScrapingJob(url="https://example.com", total_pages=100, pages_completed=50)
        assert job.pages_completed == 50
        
        # Invalid case - pages_completed exceeds total_pages
        with pytest.raises(ValueError):
            ScrapingJob(url="https://example.com", total_pages=50, pages_completed=100)
    
    def test_id_generation(self):
        """Test that unique IDs are generated."""
        job1 = ScrapingJob(url="https://example.com")
        job2 = ScrapingJob(url="https://example.com")
        
        assert job1.id != job2.id
        assert len(job1.id) > 0
        assert len(job2.id) > 0


class TestScrapedData:
    """Test cases for ScrapedData model."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        data = ScrapedData(
            job_id="job123",
            url="https://example.com",
            content={"title": "Test Page"}
        )
        
        assert data.job_id == "job123"
        assert data.url == "https://example.com"
        assert data.content == {"title": "Test Page"}
        assert data.raw_html is None
        assert data.content_type == ContentType.HTML
        assert data.content_metadata == {}
        assert data.confidence_score == 0.0
        assert data.ai_processed is False
        assert data.ai_metadata == {}
        assert data.data_quality_score == 0.0
        assert data.validation_errors == []
        assert isinstance(data.extracted_at, datetime)
        assert data.processed_at is None
        assert data.content_length == 0
        assert data.load_time == 0.0
    
    def test_valid_data_creation(self):
        """Test creating valid scraped data."""
        now = datetime.utcnow()
        data = ScrapedData(
            job_id="job123",
            url="https://example.com",
            content={"title": "Test Page", "text": "Content"},
            raw_html="<html><body>Test</body></html>",
            content_type=ContentType.JSON,
            content_metadata={"source": "api"},
            confidence_score=0.95,
            ai_processed=True,
            ai_metadata={"model": "gemini-2.5"},
            data_quality_score=0.88,
            validation_errors=["missing field"],
            processed_at=now,
            content_length=1024,
            load_time=2.5
        )
        
        assert data.job_id == "job123"
        assert data.url == "https://example.com"
        assert data.content == {"title": "Test Page", "text": "Content"}
        assert data.raw_html == "<html><body>Test</body></html>"
        assert data.content_type == ContentType.JSON
        assert data.content_metadata == {"source": "api"}
        assert data.confidence_score == 0.95
        assert data.ai_processed is True
        assert data.ai_metadata == {"model": "gemini-2.5"}
        assert data.data_quality_score == 0.88
        assert data.validation_errors == ["missing field"]
        assert data.processed_at == now
        assert data.content_length == 1024
        assert data.load_time == 2.5
    
    def test_content_validation(self):
        """Test content validation."""
        # Valid content
        data = ScrapedData(
            job_id="job123",
            url="https://example.com",
            content={"title": "Test"}
        )
        assert data.content == {"title": "Test"}
        
        # Invalid content (empty)
        with pytest.raises(ValueError):
            ScrapedData(
                job_id="job123",
                url="https://example.com",
                content={}
            )
    
    def test_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com/path"
        ]
        
        for url in valid_urls:
            data = ScrapedData(
                job_id="job123",
                url=url,
                content={"title": "Test"}
            )
            assert data.url == url
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",
            "example.com",
            ""
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                ScrapedData(
                    job_id="job123",
                    url=url,
                    content={"title": "Test"}
                )


class TestScrapingResult:
    """Test cases for ScrapingResult model."""
    
    def test_successful_result(self):
        """Test creating a successful scraping result."""
        data = [
            ScrapedData(
                job_id="job123",
                url="https://example.com",
                content={"title": "Test"}
            )
        ]
        
        result = ScrapingResult(
            job_id="job123",
            success=True,
            data=data,
            total_time=10.5,
            pages_scraped=1,
            pages_failed=0,
            average_confidence=0.95,
            data_quality_summary={"avg_quality": 0.9}
        )
        
        assert result.job_id == "job123"
        assert result.success is True
        assert result.data == data
        assert result.error_message is None
        assert result.total_time == 10.5
        assert result.pages_scraped == 1
        assert result.pages_failed == 0
        assert result.average_confidence == 0.95
        assert result.data_quality_summary == {"avg_quality": 0.9}
    
    def test_failed_result(self):
        """Test creating a failed scraping result."""
        result = ScrapingResult(
            job_id="job123",
            success=False,
            error_message="Connection timeout",
            total_time=30.0,
            pages_scraped=0,
            pages_failed=1
        )
        
        assert result.job_id == "job123"
        assert result.success is False
        assert result.data is None
        assert result.error_message == "Connection timeout"
        assert result.total_time == 30.0
        assert result.pages_scraped == 0
        assert result.pages_failed == 1
        assert result.average_confidence == 0.0
        assert result.data_quality_summary == {}


class TestDataExportRequest:
    """Test cases for DataExportRequest model."""
    
    def test_valid_export_request(self):
        """Test creating a valid export request."""
        date_from = datetime.utcnow() - timedelta(days=7)
        date_to = datetime.utcnow()
        
        request = DataExportRequest(
            format="csv",
            job_ids=["job1", "job2"],
            date_from=date_from,
            date_to=date_to,
            min_confidence=0.8,
            include_raw_html=True,
            fields=["title", "content"]
        )
        
        assert request.format == "csv"
        assert request.job_ids == ["job1", "job2"]
        assert request.date_from == date_from
        assert request.date_to == date_to
        assert request.min_confidence == 0.8
        assert request.include_raw_html is True
        assert request.fields == ["title", "content"]
    
    def test_format_validation(self):
        """Test format validation."""
        # Valid formats
        valid_formats = ["csv", "json", "xlsx"]
        
        for fmt in valid_formats:
            request = DataExportRequest(format=fmt)
            assert request.format == fmt
        
        # Invalid format
        with pytest.raises(ValueError):
            DataExportRequest(format="pdf")
    
    def test_date_range_validation(self):
        """Test date range validation."""
        date_from = datetime.utcnow()
        date_to = date_from - timedelta(days=1)  # Invalid: to before from
        
        with pytest.raises(ValueError):
            DataExportRequest(
                format="csv",
                date_from=date_from,
                date_to=date_to
            )


class TestResponseModels:
    """Test cases for API response models."""
    
    def test_job_response(self):
        """Test JobResponse model."""
        job = ScrapingJob(url="https://example.com")
        response = JobResponse(job=job, message="Job created successfully")
        
        assert response.job == job
        assert response.message == "Job created successfully"
    
    def test_data_response(self):
        """Test DataResponse model."""
        data = [
            ScrapedData(
                job_id="job123",
                url="https://example.com",
                content={"title": "Test"}
            )
        ]
        
        response = DataResponse(
            data=data,
            total_count=100,
            page=2,
            page_size=25,
            has_next=True
        )
        
        assert response.data == data
        assert response.total_count == 100
        assert response.page == 2
        assert response.page_size == 25
        assert response.has_next is True
    
    def test_health_check_response(self):
        """Test HealthCheckResponse model."""
        response = HealthCheckResponse(
            status="healthy",
            version="2.0.0",
            database_connected=True,
            redis_connected=False
        )
        
        assert response.status == "healthy"
        assert response.version == "2.0.0"
        assert response.database_connected is True
        assert response.redis_connected is False
        assert isinstance(response.timestamp, datetime)


class TestEnums:
    """Test cases for enum values."""
    
    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
    
    def test_content_type_enum(self):
        """Test ContentType enum values."""
        assert ContentType.HTML == "html"
        assert ContentType.TEXT == "text"
        assert ContentType.JSON == "json"
        assert ContentType.XML == "xml"
        assert ContentType.IMAGE == "image"
        assert ContentType.DOCUMENT == "document"


class TestSerialization:
    """Test cases for model serialization and deserialization."""
    
    def test_scraping_config_serialization(self):
        """Test ScrapingConfig serialization."""
        config = ScrapingConfig(
            wait_time=10,
            max_retries=5,
            custom_selectors={"title": "h1"}
        )
        
        # Test dict conversion
        config_dict = config.model_dump()
        assert config_dict["wait_time"] == 10
        assert config_dict["max_retries"] == 5
        assert config_dict["custom_selectors"] == {"title": "h1"}
        
        # Test JSON serialization
        config_json = config.model_dump_json()
        assert isinstance(config_json, str)
        
        # Test deserialization
        config_restored = ScrapingConfig.model_validate_json(config_json)
        assert config_restored.wait_time == 10
        assert config_restored.max_retries == 5
        assert config_restored.custom_selectors == {"title": "h1"}
    
    def test_scraping_job_serialization(self):
        """Test ScrapingJob serialization."""
        job = ScrapingJob(
            url="https://example.com",
            status=JobStatus.RUNNING,
            total_pages=100
        )
        
        # Test dict conversion
        job_dict = job.model_dump()
        assert job_dict["url"] == "https://example.com"
        assert job_dict["status"] == "running"
        assert job_dict["total_pages"] == 100
        
        # Test JSON serialization
        job_json = job.model_dump_json()
        assert isinstance(job_json, str)
        
        # Test deserialization
        job_restored = ScrapingJob.model_validate_json(job_json)
        assert job_restored.url == "https://example.com"
        assert job_restored.status == JobStatus.RUNNING
        assert job_restored.total_pages == 100
    
    def test_scraped_data_serialization(self):
        """Test ScrapedData serialization."""
        data = ScrapedData(
            job_id="job123",
            url="https://example.com",
            content={"title": "Test Page"},
            confidence_score=0.95
        )
        
        # Test dict conversion
        data_dict = data.model_dump()
        assert data_dict["job_id"] == "job123"
        assert data_dict["url"] == "https://example.com"
        assert data_dict["content"] == {"title": "Test Page"}
        assert data_dict["confidence_score"] == 0.95
        
        # Test JSON serialization
        data_json = data.model_dump_json()
        assert isinstance(data_json, str)
        
        # Test deserialization
        data_restored = ScrapedData.model_validate_json(data_json)
        assert data_restored.job_id == "job123"
        assert data_restored.url == "https://example.com"
        assert data_restored.content == {"title": "Test Page"}
        assert data_restored.confidence_score == 0.95