#!/usr/bin/env python3
"""
Schema Validation Script

This script performs comprehensive validation of all data schemas,
checks consistency across the application, and validates data
transformation functions.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.pydantic_models import (
    ScrapingConfig, ScrapingJob, ScrapedData, ScrapingResult,
    DataExportRequest, JobStatus, ContentType
)
from src.api.schemas import (
    CreateJobRequest, UpdateJobRequest, DataQueryRequest, BulkJobRequest,
    JobResponse, JobListResponse, DataResponse, DataSummaryResponse,
    ExportResponse, HealthResponse, ErrorResponse
)
from src.utils.type_hints import (
    is_valid_url, is_valid_confidence_score, is_valid_job_status,
    ensure_dict, ensure_list, ensure_string, ensure_float
)


class SchemaValidator:
    """Comprehensive schema validator for the web scraper project."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed_tests = 0
        self.total_tests = 0
    
    def log_error(self, test_name: str, error: str):
        """Log a validation error."""
        self.errors.append(f"❌ {test_name}: {error}")
    
    def log_warning(self, test_name: str, warning: str):
        """Log a validation warning."""
        self.warnings.append(f"⚠️  {test_name}: {warning}")
    
    def log_success(self, test_name: str):
        """Log a successful test."""
        self.passed_tests += 1
        print(f"✅ {test_name}")
    
    def run_test(self, test_name: str, test_func):
        """Run a test and handle exceptions."""
        self.total_tests += 1
        try:
            test_func()
            self.log_success(test_name)
        except Exception as e:
            self.log_error(test_name, str(e))
    
    def validate_pydantic_models(self):
        """Validate all Pydantic models."""
        print("\n🔍 Validating Pydantic Models...")
        
        # Test ScrapingConfig
        def test_scraping_config():
            config = ScrapingConfig()
            assert config.wait_time == 5
            assert config.max_retries == 3
            assert config.use_stealth is True
            
            # Test validation
            config_with_values = ScrapingConfig(
                wait_time=10,
                max_retries=5,
                custom_selectors={"title": "h1"},
                proxy_url="http://proxy.example.com:8080"
            )
            assert config_with_values.wait_time == 10
            assert config_with_values.custom_selectors == {"title": "h1"}
        
        self.run_test("ScrapingConfig creation and validation", test_scraping_config)
        
        # Test ScrapingJob
        def test_scraping_job():
            job = ScrapingJob(url="https://example.com")
            assert job.url == "https://example.com"
            assert job.status == JobStatus.PENDING
            assert isinstance(job.config, ScrapingConfig)
            assert len(job.id) > 0
            
            # Test with full data
            job_full = ScrapingJob(
                url="https://example.com",
                status=JobStatus.RUNNING,
                total_pages=100,
                pages_completed=50,
                tags=["test"],
                priority=3
            )
            assert job_full.pages_completed == 50
            assert job_full.priority == 3
        
        self.run_test("ScrapingJob creation and validation", test_scraping_job)
        
        # Test ScrapedData
        def test_scraped_data():
            data = ScrapedData(
                job_id="job-123",
                url="https://example.com",
                content={"title": "Test Page"}
            )
            assert data.job_id == "job-123"
            assert data.content == {"title": "Test Page"}
            assert data.confidence_score == 0.0
            assert data.ai_processed is False
            
            # Test with AI processing data
            ai_data = ScrapedData(
                job_id="job-123",
                url="https://example.com",
                content={"title": "Test"},
                confidence_score=0.95,
                ai_processed=True,
                ai_metadata={"model": "gemini-2.5"}
            )
            assert ai_data.confidence_score == 0.95
            assert ai_data.ai_processed is True
        
        self.run_test("ScrapedData creation and validation", test_scraped_data)
        
        # Test DataExportRequest
        def test_data_export_request():
            request = DataExportRequest(format="csv")
            assert request.format == "csv"
            assert request.min_confidence == 0.0
            assert request.include_raw_html is False
            
            # Test with full data
            full_request = DataExportRequest(
                format="json",
                job_ids=["job1", "job2"],
                min_confidence=0.8,
                fields=["url", "content"]
            )
            assert full_request.job_ids == ["job1", "job2"]
            assert full_request.min_confidence == 0.8
        
        self.run_test("DataExportRequest creation and validation", test_data_export_request)
    
    def validate_api_schemas(self):
        """Validate all API schemas."""
        print("\n🔍 Validating API Schemas...")
        
        # Test CreateJobRequest
        def test_create_job_request():
            request = CreateJobRequest(url="https://example.com")
            assert request.url == "https://example.com"
            assert request.priority == 5  # Default
            
            # Test with config
            config = ScrapingConfig(wait_time=10)
            request_with_config = CreateJobRequest(
                url="https://example.com",
                config=config,
                tags=["test"],
                priority=3
            )
            assert request_with_config.config.wait_time == 10
            assert request_with_config.tags == ["test"]
        
        self.run_test("CreateJobRequest validation", test_create_job_request)
        
        # Test DataQueryRequest
        def test_data_query_request():
            request = DataQueryRequest()
            assert request.page == 1
            assert request.page_size == 50
            assert request.sort_by == "extracted_at"
            
            # Test with filters
            filtered_request = DataQueryRequest(
                job_ids=["job1"],
                min_confidence=0.8,
                content_type=ContentType.HTML,
                page=2,
                page_size=25
            )
            assert filtered_request.job_ids == ["job1"]
            assert filtered_request.min_confidence == 0.8
            assert filtered_request.content_type == ContentType.HTML
        
        self.run_test("DataQueryRequest validation", test_data_query_request)
        
        # Test BulkJobRequest
        def test_bulk_job_request():
            urls = ["https://example1.com", "https://example2.com"]
            request = BulkJobRequest(urls=urls)
            assert request.urls == urls
            assert request.priority == 5  # Default
            
            # Test with config
            config = ScrapingConfig(wait_time=5)
            bulk_with_config = BulkJobRequest(
                urls=urls,
                config=config,
                tags=["bulk"],
                priority=7
            )
            assert bulk_with_config.config.wait_time == 5
            assert bulk_with_config.tags == ["bulk"]
        
        self.run_test("BulkJobRequest validation", test_bulk_job_request)
    
    def validate_response_schemas(self):
        """Validate response schemas."""
        print("\n🔍 Validating Response Schemas...")
        
        # Test JobResponse
        def test_job_response():
            job = ScrapingJob(url="https://example.com")
            response = JobResponse(job=job, message="Success")
            assert response.job == job
            assert response.message == "Success"
            
            # Test serialization
            response_dict = response.model_dump()
            assert "job" in response_dict
            assert "message" in response_dict
        
        self.run_test("JobResponse validation", test_job_response)
        
        # Test DataResponse
        def test_data_response():
            data = [ScrapedData(
                job_id="job-123",
                url="https://example.com",
                content={"title": "Test"}
            )]
            
            response = DataResponse(
                data=data,
                total_count=100,
                page=1,
                page_size=50,
                has_next=True,
                has_previous=False
            )
            assert len(response.data) == 1
            assert response.total_count == 100
            assert response.has_next is True
        
        self.run_test("DataResponse validation", test_data_response)
        
        # Test HealthResponse
        def test_health_response():
            response = HealthResponse(
                uptime_seconds=3600.0,
                database_connected=True,
                redis_connected=True,
                active_jobs=5
            )
            assert response.status == "healthy"
            assert response.uptime_seconds == 3600.0
            assert response.database_connected is True
            assert isinstance(response.timestamp, datetime)
        
        self.run_test("HealthResponse validation", test_health_response)
    
    def validate_schema_consistency(self):
        """Validate consistency between different schemas."""
        print("\n🔍 Validating Schema Consistency...")
        
        def test_job_model_api_consistency():
            # Create job with model
            job = ScrapingJob(
                url="https://example.com",
                status=JobStatus.RUNNING,
                tags=["test"],
                priority=3
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
        
        self.run_test("Job model-API consistency", test_job_model_api_consistency)
        
        def test_data_model_api_consistency():
            # Create data with model
            data = ScrapedData(
                job_id="job-123",
                url="https://example.com",
                content={"title": "Test"},
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
            assert data_dict["confidence_score"] == data.confidence_score
            assert data_dict["ai_processed"] == data.ai_processed
        
        self.run_test("Data model-API consistency", test_data_model_api_consistency)
    
    def validate_type_hints(self):
        """Validate type hint functions."""
        print("\n🔍 Validating Type Hints...")
        
        def test_url_validation():
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
                None
            ]
            for url in invalid_urls:
                assert is_valid_url(url) is False
        
        self.run_test("URL validation type guard", test_url_validation)
        
        def test_confidence_validation():
            # Valid scores
            valid_scores = [0.0, 0.5, 1.0, 0.85]
            for score in valid_scores:
                assert is_valid_confidence_score(score) is True
            
            # Invalid scores
            invalid_scores = [-0.1, 1.1, "0.5", None]
            for score in invalid_scores:
                assert is_valid_confidence_score(score) is False
        
        self.run_test("Confidence score validation", test_confidence_validation)
        
        def test_type_conversion():
            # Test ensure_dict
            assert ensure_dict({"key": "value"}) == {"key": "value"}
            assert ensure_dict(None) == {}
            assert ensure_dict("string") == {}
            
            # Test ensure_list
            assert ensure_list([1, 2, 3]) == [1, 2, 3]
            assert ensure_list(None) == []
            assert ensure_list("item") == ["item"]
            
            # Test ensure_string
            assert ensure_string("test") == "test"
            assert ensure_string(123) == "123"
            assert ensure_string(None) == ""
            
            # Test ensure_float
            assert ensure_float(3.14) == 3.14
            assert ensure_float(5) == 5.0
            assert ensure_float("invalid") == 0.0
        
        self.run_test("Type conversion utilities", test_type_conversion)
    
    def validate_serialization(self):
        """Validate serialization consistency."""
        print("\n🔍 Validating Serialization...")
        
        def test_job_serialization():
            original_job = ScrapingJob(
                url="https://example.com",
                config=ScrapingConfig(wait_time=10),
                status=JobStatus.RUNNING,
                tags=["test"],
                priority=3
            )
            
            # Serialize to JSON
            job_json = original_job.model_dump_json()
            
            # Deserialize from JSON
            restored_job = ScrapingJob.model_validate_json(job_json)
            
            # Verify consistency
            assert restored_job.url == original_job.url
            assert restored_job.config.wait_time == original_job.config.wait_time
            assert restored_job.status == original_job.status
            assert restored_job.tags == original_job.tags
            assert restored_job.priority == original_job.priority
        
        self.run_test("Job serialization roundtrip", test_job_serialization)
        
        def test_data_serialization():
            original_data = ScrapedData(
                job_id="job-123",
                url="https://example.com",
                content={"title": "Test", "items": ["a", "b"]},
                confidence_score=0.95,
                ai_processed=True,
                ai_metadata={"model": "gemini-2.5"}
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
        
        self.run_test("Data serialization roundtrip", test_data_serialization)
    
    def validate_edge_cases(self):
        """Validate edge cases and error conditions."""
        print("\n🔍 Validating Edge Cases...")
        
        def test_validation_errors():
            # Test invalid URL
            try:
                ScrapingJob(url="invalid-url")
                assert False, "Should have raised ValueError"
            except ValueError:
                pass  # Expected
            
            # Test invalid priority
            try:
                CreateJobRequest(url="https://example.com", priority=15)
                assert False, "Should have raised ValueError"
            except ValueError:
                pass  # Expected
            
            # Test invalid confidence
            try:
                DataQueryRequest(min_confidence=1.5)
                assert False, "Should have raised ValueError"
            except ValueError:
                pass  # Expected
            
            # Test invalid export format
            try:
                DataExportRequest(format="pdf")
                assert False, "Should have raised ValueError"
            except ValueError:
                pass  # Expected
        
        self.run_test("Validation error handling", test_validation_errors)
        
        def test_empty_content():
            # Test empty content validation
            try:
                ScrapedData(
                    job_id="job-123",
                    url="https://example.com",
                    content={}
                )
                assert False, "Should have raised ValueError for empty content"
            except ValueError:
                pass  # Expected
        
        self.run_test("Empty content validation", test_empty_content)
        
        def test_date_range_validation():
            # Test invalid date range
            try:
                DataQueryRequest(
                    date_from=datetime.now(),
                    date_to=datetime.now() - timedelta(days=1)
                )
                assert False, "Should have raised ValueError for invalid date range"
            except ValueError:
                pass  # Expected
        
        self.run_test("Date range validation", test_date_range_validation)
    
    def generate_report(self):
        """Generate validation report."""
        print("\n" + "="*60)
        print("SCHEMA VALIDATION REPORT")
        print("="*60)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {self.total_tests}")
        print(f"   Passed: {self.passed_tests}")
        print(f"   Failed: {len(self.errors)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   {warning}")
        
        if not self.errors and not self.warnings:
            print(f"\n✅ ALL VALIDATIONS PASSED!")
            print("   The schema validation is complete and successful.")
        elif not self.errors:
            print(f"\n✅ VALIDATION PASSED WITH WARNINGS")
            print("   All critical validations passed, but there are warnings to review.")
        else:
            print(f"\n❌ VALIDATION FAILED")
            print("   There are critical errors that need to be addressed.")
        
        print("\n" + "="*60)
        
        return len(self.errors) == 0


def main():
    """Main validation function."""
    print("🚀 Starting Schema Validation...")
    
    validator = SchemaValidator()
    
    # Run all validations
    validator.validate_pydantic_models()
    validator.validate_api_schemas()
    validator.validate_response_schemas()
    validator.validate_schema_consistency()
    validator.validate_type_hints()
    validator.validate_serialization()
    validator.validate_edge_cases()
    
    # Generate report
    success = validator.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()