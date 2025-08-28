"""
Tests for Pydantic models and data validation.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from pydantic import ValidationError

from src.models.pydantic_models import (
    ScrapingConfig, ScrapingJob, ScrapedData, ScrapingResult,
    JobStatus, ContentType, DataExportRequest,
    JobResponse, JobListResponse, DataResponse, HealthCheckResponse
)


class TestScrapingConfig:
    """Test ScrapingConfig model validation."""
    
    def test_default_config_creation(self):
        """Test creating config with default values."""
        config = ScrapingConfig()
        
        assert config.wait_time == 5
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.use_stealth is True
        assert config.headless is True
        assert config.extract_images is False
        assert config.extract_links is False
        assert config.follow_links is False
        assert config.max_depth == 1
        assert config.delay_between_requests == 1.0
        assert config.respect_robots_txt is True
        assert config.name is None
        assert config.max_pages == 10
        assert config.custom_selectors == {}
        assert config.exclude_selectors == []
        assert config.javascript_enabled is True
    
    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = ScrapingConfig(
            name="Custom Job",
            max_pages=20,
            wait_time=10,
            max_retries=5,
            timeout=60,
            use_stealth=False,
            headless=False,
            extract_images=True,
            extract_links=True,
            follow_links=True,
            max_depth=3,
            delay_between_requests=2.5,
            respect_robots_txt=False,
            custom_selectors={"title": "h1", "price": ".price"},
            exclude_selectors=[".ad", ".popup"],
            javascript_enabled=False
        )
        
        assert config.name == "Custom Job"
        assert config.max_pages == 20
        assert config.wait_time == 10
        assert config.max_retries == 5
        assert config.timeout == 60
        assert config.use_stealth is False
        assert config.headless is False
        assert config.extract_images is True
        assert config.extract_links is True
        assert config.follow_links is True
        assert config.max_depth == 3
        assert config.delay_between_requests == 2.5
        assert config.respect_robots_txt is False
        assert config.custom_selectors == {"title": "h1", "price": ".price"}
        assert config.exclude_selectors == [".ad", ".popup"]
        assert config.javascript_enabled is False
    
    def test_config_validation_errors(self):
        """Test config validation with invalid values."""
        # Test invalid wait_time
        with pytest.raises(ValidationError):
            ScrapingConfig(wait_time=0)
        
        with pytest.raises(ValidationError):
            ScrapingConfig(wait_time=61)
        
        # Test invalid max_retries
        with pytest.raises(ValidationError):
            ScrapingConfig(max_retries=-1)
        
        with pytest.raises(ValidationError):
            ScrapingConfig(max_retries=11)
        
        # Test invalid timeout
        with pytest.raises(ValidationError):
            ScrapingConfig(timeout=4)
        
        with pytest.raises(ValidationError):
            ScrapingConfig(timeout=301)
        
        # Test invalid max_depth
        with pytest.raises(ValidationError):
            ScrapingConfig(max_depth=0)
        
        with pytest.raises(ValidationError):
            ScrapingConfig(max_depth=6)
        
        # Test invalid delay_between_requests
        with pytest.raises(ValidationError):
            ScrapingConfig(delay_between_requests=0.05)
        
        with pytest.raises(ValidationError):
            ScrapingConfig(delay_between_requests=11.0)
        
        # Test invalid max_pages
        with pytest.raises(ValidationError):
            ScrapingConfig(max_pages=0)
        
        with pytest.raises(ValidationError):
            ScrapingConfig(max_pages=1001)
    
    def test_user_agent_validation(self):
        """Test user agent validation."""
        # Valid user agent
        config = ScrapingConfig(user_agent="Mozilla/5.0 (Test Browser)")
        assert config.user_agent == "Mozilla/5.0 (Test Browser)"
        
        # Empty string should raise error
        with pytest.raises(ValidationError):
            ScrapingConfig(user_agent="")
        
        # None should be allowed
        config = ScrapingConfig(user_agent=None)
        assert config.user_agent is None


class TestScrapingJob:
    """Test ScrapingJob model validation."""
    
    def test_job_creation_with_defaults(self, sample_scraping_config):
        """Test creating job with default values."""
        job = ScrapingJob(
            url="https://example.com",
            config=sample_scraping_config
        )
        
        assert job.url == "https://example.com"
        assert job.config == sample_scraping_config
        assert job.status == JobStatus.PENDING
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
    
    def test_job_url_validation(self, sample_scraping_config):
        """Test URL validation in job creation."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://subdomain.example.com/path",
            "http://localhost:8000",
            "https://192.168.1.1:3000/api"
        ]
        
        for url in valid_urls:
            job = ScrapingJob(url=url, config=sample_scraping_config)
            assert job.url == url
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",
            "example.com",
            "www.example.com",
            "javascript:alert('test')",
            ""
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                ScrapingJob(url=url, config=sample_scraping_config)
    
    def test_job_status_transitions(self, sample_scraping_config):
        """Test job status transitions and timestamp updates."""
        job = ScrapingJob(
            url="https://example.com",
            config=sample_scraping_config,
            status=JobStatus.RUNNING
        )
        
        # Should set started_at when status is RUNNING
        assert job.started_at is not None
        
        # Test completion
        job.status = JobStatus.COMPLETED
        job = ScrapingJob(**job.model_dump())  # Re-validate
        assert job.completed_at is not None
    
    def test_job_consistency_validation(self, sample_scraping_config):
        """Test job data consistency validation."""
        # pages_completed should not exceed total_pages
        with pytest.raises(ValidationError):
            ScrapingJob(
                url="https://example.com",
                config=sample_scraping_config,
                total_pages=5,
                pages_completed=10
            )


class TestScrapedData:
    """Test ScrapedData model validation."""
    
    def test_scraped_data_creation(self):
        """Test creating scraped data with valid values."""
        data = ScrapedData(
            job_id=str(uuid4()),
            url="https://example.com/page1",
            content={
                "title": "Test Page",
                "text": "Sample content"
            }
        )
        
        assert data.job_id
        assert data.url == "https://example.com/page1"
        assert data.content["title"] == "Test Page"
        assert data.content["text"] == "Sample content"
        assert data.content_type == ContentType.HTML
        assert data.confidence_score == 0.0
        assert data.ai_processed is False
        assert isinstance(data.extracted_at, datetime)
    
    def test_scraped_data_url_validation(self):
        """Test URL validation in scraped data."""
        job_id = str(uuid4())
        
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://subdomain.example.com:8080/api/data"
        ]
        
        for url in valid_urls:
            data = ScrapedData(
                job_id=job_id,
                url=url,
                content={"title": "Test", "text": "Content"}
            )
            assert data.url == url
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",
            "example.com",
            "javascript:void(0)"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                ScrapedData(
                    job_id=job_id,
                    url=url,
                    content={"title": "Test", "text": "Content"}
                )
    
    def test_content_validation(self):
        """Test content structure validation."""
        job_id = str(uuid4())
        url = "https://example.com"
        
        # Valid content structures
        valid_contents = [
            {"title": "Test", "text": "Content"},
            {"title": "", "text": ""},  # Empty strings should be allowed
            {"title": "Test", "text": "Content", "extra": "data"}
        ]
        
        for content in valid_contents:
            data = ScrapedData(job_id=job_id, url=url, content=content)
            assert "title" in data.content
            assert "text" in data.content
        
        # Invalid content (non-dict)
        with pytest.raises(ValidationError):
            ScrapedData(job_id=job_id, url=url, content="string content")
        
        # Missing required fields should be auto-added
        data = ScrapedData(
            job_id=job_id,
            url=url,
            content={"custom_field": "value"}
        )
        assert data.content["title"] == ""
        assert data.content["text"] == ""
    
    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        job_id = str(uuid4())
        url = "https://example.com"
        content = {"title": "Test", "text": "Content"}
        
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 1.0, 0.85]
        
        for score in valid_scores:
            data = ScrapedData(
                job_id=job_id,
                url=url,
                content=content,
                confidence_score=score
            )
            assert data.confidence_score == score
        
        # Invalid confidence scores
        invalid_scores = [-0.1, 1.1, 2.0]
        
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                ScrapedData(
                    job_id=job_id,
                    url=url,
                    content=content,
                    confidence_score=score
                )
    
    def test_data_consistency_validation(self):
        """Test scraped data consistency validation."""
        job_id = str(uuid4())
        url = "https://example.com"
        content = {"title": "Test", "text": "Sample content text"}
        
        data = ScrapedData(
            job_id=job_id,
            url=url,
            content=content,
            ai_processed=True
        )
        
        # Should set processed_at when ai_processed is True
        assert data.processed_at is not None
        
        # Should calculate content_length
        assert data.content_length > 0


class TestScrapingResult:
    """Test ScrapingResult model validation."""
    
    def test_result_creation(self, sample_scraped_data):
        """Test creating scraping result."""
        result = ScrapingResult(
            job_id=str(uuid4()),
            success=True,
            data=[sample_scraped_data],
            total_time=5.2,
            pages_scraped=1,
            pages_failed=0
        )
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.total_time == 5.2
        assert result.pages_scraped == 1
        assert result.pages_failed == 0
        assert result.average_confidence > 0
    
    def test_result_consistency_validation(self, sample_scraped_data):
        """Test result consistency validation."""
        # Test automatic confidence calculation
        result = ScrapingResult(
            job_id=str(uuid4()),
            success=True,
            data=[sample_scraped_data],
            pages_scraped=1
        )
        
        assert result.average_confidence == sample_scraped_data.confidence_score
        
        # Test success flag correction
        result = ScrapingResult(
            job_id=str(uuid4()),
            success=True,
            data=[],
            pages_scraped=0
        )
        
        assert result.success is False
        assert result.error_message is not None


class TestDataExportRequest:
    """Test DataExportRequest model validation."""
    
    def test_export_request_creation(self):
        """Test creating export request with valid data."""
        request = DataExportRequest(
            format="csv",
            job_ids=[str(uuid4())],
            date_from=datetime.utcnow() - timedelta(days=7),
            date_to=datetime.utcnow(),
            min_confidence=0.5,
            include_raw_html=False,
            fields=["title", "content", "url"]
        )
        
        assert request.format == "csv"
        assert len(request.job_ids) == 1
        assert request.min_confidence == 0.5
        assert request.include_raw_html is False
        assert "title" in request.fields
    
    def test_export_format_validation(self):
        """Test export format validation."""
        # Valid formats
        valid_formats = ["csv", "json", "xlsx"]
        
        for format_type in valid_formats:
            request = DataExportRequest(format=format_type)
            assert request.format == format_type
        
        # Invalid formats
        invalid_formats = ["pdf", "xml", "txt", ""]
        
        for format_type in invalid_formats:
            with pytest.raises(ValidationError):
                DataExportRequest(format=format_type)
    
    def test_confidence_validation(self):
        """Test min_confidence validation."""
        # Valid confidence values
        valid_confidences = [0.0, 0.5, 1.0]
        
        for confidence in valid_confidences:
            request = DataExportRequest(
                format="csv",
                min_confidence=confidence
            )
            assert request.min_confidence == confidence
        
        # Invalid confidence values
        invalid_confidences = [-0.1, 1.1, 2.0]
        
        for confidence in invalid_confidences:
            with pytest.raises(ValidationError):
                DataExportRequest(
                    format="csv",
                    min_confidence=confidence
                )


class TestResponseModels:
    """Test API response models."""
    
    def test_job_response(self, sample_scraping_job):
        """Test JobResponse model."""
        response = JobResponse(
            job=sample_scraping_job.model_dump(),
            message="Job created successfully"
        )
        
        assert response.message == "Job created successfully"
        assert response.job is not None
    
    def test_job_list_response(self, sample_scraping_job):
        """Test JobListResponse model."""
        jobs_data = [sample_scraping_job.model_dump()]
        
        response = JobListResponse(
            jobs=jobs_data,
            total=1,
            page=1,
            page_size=50,
            has_next=False
        )
        
        assert len(response.jobs) == 1
        assert response.total == 1
        assert response.has_next is False
    
    def test_health_check_response(self):
        """Test HealthCheckResponse model."""
        response = HealthCheckResponse(
            status="healthy",
            database_connected=True,
            services={
                "api": "healthy",
                "database": "healthy",
                "ai_service": "healthy"
            }
        )
        
        assert response.status == "healthy"
        assert response.database_connected is True
        assert "api" in response.services
        assert isinstance(response.timestamp, datetime)