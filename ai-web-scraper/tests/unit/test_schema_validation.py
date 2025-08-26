"""
Unit tests for schema validation and data consistency.

This module contains comprehensive tests for validating data schemas,
ensuring consistency across API requests/responses, and testing
data transformation functions.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import uuid4

from src.api.schemas import (
    CreateJobRequest, UpdateJobRequest, DataQueryRequest, BulkJobRequest,
    JobResponse, JobListResponse, DataResponse, DataSummaryResponse,
    ExportResponse, HealthResponse, ErrorResponse, ValidationErrorResponse,
    JobStatsResponse, SystemStatsResponse, TokenRequest, TokenResponse,
    WebhookRequest, WebhookResponse, BatchOperationRequest, BatchOperationResponse
)
from src.models.pydantic_models import (
    ScrapingConfig, ScrapingJob, ScrapedData, ScrapingResult,
    DataExportRequest, JobStatus, ContentType
)
from src.utils.type_hints import (
    ValidationResult, ProcessingMetrics, ExportResult,
    is_valid_url, is_valid_confidence_score, is_valid_job_status,
    ensure_dict, ensure_list, ensure_string, ensure_float
)
from tests.fixtures.schema_fixtures import *


class TestAPISchemaValidation:
    """Test cases for API schema validation."""
    
    def test_create_job_request_validation(self):
        """Test CreateJobRequest validation."""
        # Valid request
        valid_request = CreateJobRequest(
            url="https://example.com",
            config=ScrapingConfig(wait_time=10),
            tags=["test", "example"],
            priority=5
        )
        
        assert valid_request.url == "https://example.com"
        assert valid_request.priority == 5
        assert valid_request.tags == ["test", "example"]
    
    def test_create_job_request_url_validation(self):
        """Test URL validation in CreateJobRequest."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://subdomain.example.com/path?query=value"
        ]
        
        for url in valid_urls:
            request = CreateJobRequest(url=url)
            assert request.url == url
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",
            "example.com",
            "not-a-url"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                CreateJobRequest(url=url)
    
    def test_create_job_request_priority_validation(self):
        """Test priority validation in CreateJobRequest."""
        # Valid priorities
        for priority in range(1, 11):
            request = CreateJobRequest(url="https://example.com", priority=priority)
            assert request.priority == priority
        
        # Invalid priorities
        invalid_priorities = [0, 11, -1, 15]
        
        for priority in invalid_priorities:
            with pytest.raises(ValueError):
                CreateJobRequest(url="https://example.com", priority=priority)
    
    def test_data_query_request_validation(self):
        """Test DataQueryRequest validation."""
        # Valid request
        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()
        
        request = DataQueryRequest(
            job_ids=["job1", "job2"],
            urls=["https://example1.com", "https://example2.com"],
            date_from=date_from,
            date_to=date_to,
            min_confidence=0.8,
            content_type=ContentType.HTML,
            ai_processed=True,
            page=1,
            page_size=50,
            sort_by="extracted_at",
            sort_order="desc"
        )
        
        assert request.job_ids == ["job1", "job2"]
        assert request.min_confidence == 0.8
        assert request.content_type == ContentType.HTML
        assert request.ai_processed is True
    
    def test_data_query_request_date_validation(self):
        """Test date range validation in DataQueryRequest."""
        # Valid date range
        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()
        
        request = DataQueryRequest(date_from=date_from, date_to=date_to)
        assert request.date_from == date_from
        assert request.date_to == date_to
        
        # Invalid date range (to before from)
        with pytest.raises(ValueError):
            DataQueryRequest(
                date_from=datetime.now(),
                date_to=datetime.now() - timedelta(days=1)
            )
    
    def test_data_query_request_pagination_validation(self):
        """Test pagination validation in DataQueryRequest."""
        # Valid pagination
        request = DataQueryRequest(page=1, page_size=50)
        assert request.page == 1
        assert request.page_size == 50
        
        # Invalid page
        with pytest.raises(ValueError):
            DataQueryRequest(page=0)
        
        # Invalid page_size
        with pytest.raises(ValueError):
            DataQueryRequest(page_size=0)
        
        with pytest.raises(ValueError):
            DataQueryRequest(page_size=1001)  # Exceeds maximum
    
    def test_bulk_job_request_validation(self):
        """Test BulkJobRequest validation."""
        # Valid request
        urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com"
        ]
        
        request = BulkJobRequest(
            urls=urls,
            config=ScrapingConfig(wait_time=5),
            tags=["bulk", "test"],
            priority=6
        )
        
        assert request.urls == urls
        assert request.priority == 6
        assert request.tags == ["bulk", "test"]
    
    def test_bulk_job_request_url_validation(self):
        """Test URL validation in BulkJobRequest."""
        # Valid URLs
        valid_urls = ["https://example1.com", "https://example2.com"]
        request = BulkJobRequest(urls=valid_urls)
        assert request.urls == valid_urls
        
        # Invalid URLs in list
        invalid_urls = ["https://example1.com", "invalid-url"]
        with pytest.raises(ValueError):
            BulkJobRequest(urls=invalid_urls)
        
        # Empty URL list
        with pytest.raises(ValueError):
            BulkJobRequest(urls=[])
        
        # Too many URLs
        too_many_urls = [f"https://example{i}.com" for i in range(101)]
        with pytest.raises(ValueError):
            BulkJobRequest(urls=too_many_urls)


class TestResponseSchemaValidation:
    """Test cases for response schema validation."""
    
    def test_job_response_schema(self):
        """Test JobResponse schema."""
        job = ScrapingJob(url="https://example.com")
        response = JobResponse(job=job, message="Success")
        
        assert response.job == job
        assert response.message == "Success"
        
        # Test serialization
        response_dict = response.model_dump()
        assert "job" in response_dict
        assert "message" in response_dict
    
    def test_job_list_response_schema(self):
        """Test JobListResponse schema."""
        jobs = [
            ScrapingJob(url="https://example1.com"),
            ScrapingJob(url="https://example2.com")
        ]
        
        response = JobListResponse(
            jobs=jobs,
            total_count=100,
            page=1,
            page_size=50,
            has_next=True,
            has_previous=False
        )
        
        assert len(response.jobs) == 2
        assert response.total_count == 100
        assert response.has_next is True
        assert response.has_previous is False
    
    def test_data_response_schema(self):
        """Test DataResponse schema."""
        data = [
            ScrapedData(
                job_id="job1",
                url="https://example1.com",
                content={"title": "Test 1"}
            ),
            ScrapedData(
                job_id="job2",
                url="https://example2.com",
                content={"title": "Test 2"}
            )
        ]
        
        response = DataResponse(
            data=data,
            total_count=200,
            page=2,
            page_size=25,
            has_next=True,
            has_previous=True,
            filters_applied={"min_confidence": 0.8}
        )
        
        assert len(response.data) == 2
        assert response.total_count == 200
        assert response.page == 2
        assert response.filters_applied == {"min_confidence": 0.8}
    
    def test_error_response_schema(self):
        """Test ErrorResponse schema."""
        response = ErrorResponse(
            error="ValidationError",
            message="Invalid input data",
            details={"field": "url", "issue": "invalid format"}
        )
        
        assert response.error == "ValidationError"
        assert response.message == "Invalid input data"
        assert response.details == {"field": "url", "issue": "invalid format"}
        assert isinstance(response.timestamp, datetime)
    
    def test_validation_error_response_schema(self):
        """Test ValidationErrorResponse schema."""
        response = ValidationErrorResponse(
            details=[
                {"field": "url", "message": "Invalid URL format"},
                {"field": "priority", "message": "Must be between 1 and 10"}
            ]
        )
        
        assert response.error == "Validation Error"
        assert response.message == "The request contains invalid data"
        assert len(response.details) == 2
        assert isinstance(response.timestamp, datetime)


class TestDataExportSchemaValidation:
    """Test cases for data export schema validation."""
    
    def test_data_export_request_validation(self):
        """Test DataExportRequest validation."""
        # Valid request
        request = DataExportRequest(
            format="csv",
            job_ids=["job1", "job2"],
            date_from=datetime.now() - timedelta(days=7),
            date_to=datetime.now(),
            min_confidence=0.8,
            include_raw_html=False,
            fields=["url", "content", "confidence_score"]
        )
        
        assert request.format == "csv"
        assert request.job_ids == ["job1", "job2"]
        assert request.min_confidence == 0.8
        assert request.include_raw_html is False
        assert request.fields == ["url", "content", "confidence_score"]
    
    def test_data_export_format_validation(self):
        """Test export format validation."""
        # Valid formats
        valid_formats = ["csv", "json", "xlsx"]
        
        for fmt in valid_formats:
            request = DataExportRequest(format=fmt)
            assert request.format == fmt
        
        # Invalid format
        with pytest.raises(ValueError):
            DataExportRequest(format="pdf")
    
    def test_data_export_confidence_validation(self):
        """Test confidence score validation in export request."""
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 1.0, 0.85]
        
        for score in valid_scores:
            request = DataExportRequest(format="csv", min_confidence=score)
            assert request.min_confidence == score
        
        # Invalid confidence scores
        invalid_scores = [-0.1, 1.1, 2.0]
        
        for score in invalid_scores:
            with pytest.raises(ValueError):
                DataExportRequest(format="csv", min_confidence=score)
    
    def test_export_response_schema(self):
        """Test ExportResponse schema."""
        response = ExportResponse(
            export_id="export-123",
            status="completed",
            download_url="/api/v1/data/exports/export-123/download",
            file_size=1024000,
            created_at=datetime.now()
        )
        
        assert response.export_id == "export-123"
        assert response.status == "completed"
        assert response.file_size == 1024000
        assert isinstance(response.created_at, datetime)


class TestSchemaConsistency:
    """Test cases for schema consistency across the application."""
    
    def test_job_model_api_consistency(self):
        """Test consistency between job models and API schemas."""
        # Create a job using the model
        job = ScrapingJob(
            url="https://example.com",
            config=ScrapingConfig(wait_time=10),
            status=JobStatus.PENDING,
            tags=["test"],
            priority=5
        )
        
        # Create API response
        response = JobResponse(job=job, message="Success")
        
        # Verify consistency
        response_dict = response.model_dump()
        job_dict = response_dict["job"]
        
        assert job_dict["url"] == job.url
        assert job_dict["status"] == job.status.value
        assert job_dict["tags"] == job.tags
        assert job_dict["priority"] == job.priority
    
    def test_data_model_api_consistency(self):
        """Test consistency between data models and API schemas."""
        # Create scraped data using the model
        data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test Page", "text": "Content"},
            confidence_score=0.95,
            ai_processed=True
        )
        
        # Create API response
        response = DataResponse(
            data=[data],
            total_count=1,
            page=1,
            page_size=50,
            has_next=False,
            has_previous=False
        )
        
        # Verify consistency
        response_dict = response.model_dump()
        data_dict = response_dict["data"][0]
        
        assert data_dict["job_id"] == data.job_id
        assert data_dict["url"] == data.url
        assert data_dict["content"] == data.content
        assert data_dict["confidence_score"] == data.confidence_score
        assert data_dict["ai_processed"] == data.ai_processed
    
    def test_export_request_consistency(self):
        """Test consistency between export request schemas."""
        # Create export request using API schema
        api_request = {
            "format": "csv",
            "job_ids": ["job1", "job2"],
            "min_confidence": 0.8,
            "include_raw_html": False,
            "fields": ["url", "content"]
        }
        
        # Validate with API schema
        validated_request = DataExportRequest(**api_request)
        
        # Convert to core model
        core_request = DataExportRequest(
            format=validated_request.format,
            job_ids=validated_request.job_ids,
            min_confidence=validated_request.min_confidence,
            include_raw_html=validated_request.include_raw_html,
            fields=validated_request.fields
        )
        
        # Verify consistency
        assert core_request.format == validated_request.format
        assert core_request.job_ids == validated_request.job_ids
        assert core_request.min_confidence == validated_request.min_confidence
        assert core_request.include_raw_html == validated_request.include_raw_html
        assert core_request.fields == validated_request.fields


class TestTypeHintValidation:
    """Test cases for type hint validation functions."""
    
    def test_url_validation(self):
        """Test URL validation type guard."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://subdomain.example.com/path"
        ]
        
        for url in valid_urls:
            assert is_valid_url(url) is True
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",
            "example.com",
            "not-a-url",
            123,
            None,
            []
        ]
        
        for url in invalid_urls:
            assert is_valid_url(url) is False
    
    def test_confidence_score_validation(self):
        """Test confidence score validation type guard."""
        # Valid scores
        valid_scores = [0.0, 0.5, 1.0, 0.85, 0, 1]
        
        for score in valid_scores:
            assert is_valid_confidence_score(score) is True
        
        # Invalid scores
        invalid_scores = [-0.1, 1.1, 2.0, "0.5", None, []]
        
        for score in invalid_scores:
            assert is_valid_confidence_score(score) is False
    
    def test_job_status_validation(self):
        """Test job status validation type guard."""
        # Valid statuses
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        
        for status in valid_statuses:
            assert is_valid_job_status(status) is True
        
        # Invalid statuses
        invalid_statuses = ["invalid", "PENDING", 123, None, []]
        
        for status in invalid_statuses:
            assert is_valid_job_status(status) is False
    
    def test_type_conversion_utilities(self):
        """Test type conversion utility functions."""
        # Test ensure_dict
        assert ensure_dict({"key": "value"}) == {"key": "value"}
        assert ensure_dict(None) == {}
        assert ensure_dict("string") == {}
        assert ensure_dict(123) == {}
        
        # Test ensure_list
        assert ensure_list([1, 2, 3]) == [1, 2, 3]
        assert ensure_list(None) == []
        assert ensure_list("item") == ["item"]
        assert ensure_list(123) == [123]
        
        # Test ensure_string
        assert ensure_string("test") == "test"
        assert ensure_string(123) == "123"
        assert ensure_string(None) == ""
        assert ensure_string(True) == "True"
        
        # Test ensure_float
        assert ensure_float(3.14) == 3.14
        assert ensure_float(5) == 5.0
        assert ensure_float("invalid") == 0.0
        assert ensure_float(None) == 0.0


class TestValidationResult:
    """Test cases for ValidationResult named tuple."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation and properties."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Minor issue"],
            data_quality_score=0.95
        )
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["Minor issue"]
        assert result.data_quality_score == 0.95
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult with validation errors."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing required field", "Invalid format"],
            warnings=[],
            data_quality_score=0.3
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.warnings == []
        assert result.data_quality_score == 0.3


class TestProcessingMetrics:
    """Test cases for ProcessingMetrics named tuple."""
    
    def test_processing_metrics_creation(self):
        """Test ProcessingMetrics creation and calculations."""
        metrics = ProcessingMetrics(
            processing_time=10.5,
            items_processed=100,
            items_failed=5,
            success_rate=0.95,
            average_confidence=0.87
        )
        
        assert metrics.processing_time == 10.5
        assert metrics.items_processed == 100
        assert metrics.items_failed == 5
        assert metrics.success_rate == 0.95
        assert metrics.average_confidence == 0.87


class TestExportResult:
    """Test cases for ExportResult named tuple."""
    
    def test_export_result_creation(self):
        """Test ExportResult creation and properties."""
        result = ExportResult(
            file_path="/tmp/export_123.csv",
            file_size=1024000,
            records_exported=500,
            format="csv",
            generation_time=5.2
        )
        
        assert result.file_path == "/tmp/export_123.csv"
        assert result.file_size == 1024000
        assert result.records_exported == 500
        assert result.format == "csv"
        assert result.generation_time == 5.2


class TestSchemaSerializationConsistency:
    """Test cases for schema serialization consistency."""
    
    def test_job_serialization_roundtrip(self):
        """Test job serialization and deserialization consistency."""
        original_job = ScrapingJob(
            url="https://example.com",
            config=ScrapingConfig(wait_time=10, max_retries=5),
            status=JobStatus.RUNNING,
            tags=["test", "example"],
            priority=3
        )
        
        # Serialize to JSON
        job_json = original_job.model_dump_json()
        
        # Deserialize from JSON
        restored_job = ScrapingJob.model_validate_json(job_json)
        
        # Verify consistency
        assert restored_job.url == original_job.url
        assert restored_job.config.wait_time == original_job.config.wait_time
        assert restored_job.config.max_retries == original_job.config.max_retries
        assert restored_job.status == original_job.status
        assert restored_job.tags == original_job.tags
        assert restored_job.priority == original_job.priority
    
    def test_data_serialization_roundtrip(self):
        """Test scraped data serialization and deserialization consistency."""
        original_data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test Page", "links": ["link1", "link2"]},
            confidence_score=0.95,
            ai_processed=True,
            ai_metadata={"model": "gemini-2.5", "version": "1.0"}
        )
        
        # Serialize to JSON
        data_json = original_data.model_dump_json()
        
        # Deserialize from JSON
        restored_data = ScrapedData.model_validate_json(data_json)
        
        # Verify consistency
        assert restored_data.job_id == original_data.job_id
        assert restored_data.url == original_data.url
        assert restored_data.content == original_data.content
        assert restored_data.confidence_score == original_data.confidence_score
        assert restored_data.ai_processed == original_data.ai_processed
        assert restored_data.ai_metadata == original_data.ai_metadata
    
    def test_api_response_serialization(self):
        """Test API response serialization consistency."""
        job = ScrapingJob(url="https://example.com")
        response = JobResponse(job=job, message="Success")
        
        # Serialize to dictionary
        response_dict = response.model_dump()
        
        # Verify structure
        assert "job" in response_dict
        assert "message" in response_dict
        assert response_dict["message"] == "Success"
        
        # Verify job data is properly nested
        job_data = response_dict["job"]
        assert job_data["url"] == "https://example.com"
        assert "id" in job_data
        assert "status" in job_data
        assert "created_at" in job_data


class TestFieldMappingConsistency:
    """Test cases for field mapping consistency across formats."""
    
    def test_csv_json_field_mapping(self):
        """Test field mapping consistency between CSV and JSON exports."""
        # Sample data
        sample_data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test", "description": "Test description"},
            confidence_score=0.95,
            ai_processed=True
        )
        
        # Convert to dictionary (as would be done for export)
        data_dict = sample_data.model_dump()
        
        # Verify all expected fields are present
        expected_fields = [
            "id", "job_id", "url", "content", "confidence_score",
            "ai_processed", "extracted_at", "content_type"
        ]
        
        for field in expected_fields:
            assert field in data_dict, f"Missing field: {field}"
        
        # Verify nested content structure
        assert isinstance(data_dict["content"], dict)
        assert "title" in data_dict["content"]
        assert "description" in data_dict["content"]
    
    def test_ai_processing_field_consistency(self):
        """Test AI processing field consistency across schemas."""
        # Create data with AI processing results
        ai_metadata = {
            "model": "gemini-2.5",
            "processing_time": 2.5,
            "entities_found": 10,
            "confidence_breakdown": {"text": 0.95, "structure": 0.90}
        }
        
        data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test"},
            confidence_score=0.92,
            ai_processed=True,
            ai_metadata=ai_metadata
        )
        
        # Verify AI fields are consistent
        data_dict = data.model_dump()
        
        assert data_dict["ai_processed"] is True
        assert data_dict["confidence_score"] == 0.92
        assert data_dict["ai_metadata"] == ai_metadata
        
        # Verify AI metadata structure
        assert "model" in data_dict["ai_metadata"]
        assert "processing_time" in data_dict["ai_metadata"]
        assert "entities_found" in data_dict["ai_metadata"]