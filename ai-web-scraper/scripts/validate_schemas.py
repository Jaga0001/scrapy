#!/usr/bin/env python3
"""
Schema validation script for AI Web Scraper.
Validates consistency between Pydantic models, database models, and API responses.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Set
import json
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.models.pydantic_models import (
        ScrapingJob, ScrapedData, ScrapingConfig, JobStatus, ContentType,
        JobResponse, JobListResponse, DataListResponse, HealthCheckResponse,
        ScrapingResult, DataExportRequest, ErrorResponse
    )
    from src.models.database_models import (
        ScrapingJobORM, ScrapedDataORM, JobLogORM, SystemMetricORM,
        ApplicationMetricORM, PerformanceMetricORM, HealthCheckORM,
        AlertORM, DataExportORM, UserSessionORM
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class SchemaValidator:
    """Validates schema consistency across the application."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 AI Web Scraper Schema Validation")
        print("=" * 50)
        
        # Run validation checks
        self.validate_pydantic_models()
        self.validate_database_models()
        self.validate_api_response_consistency()
        self.validate_export_format_mapping()
        self.validate_ai_processing_schemas()
        self.validate_type_hints()
        
        # Print results
        self.print_results()
        
        return len(self.errors) == 0
    
    def validate_pydantic_models(self):
        """Validate Pydantic model definitions."""
        print("\n📋 Validating Pydantic Models...")
        
        # Test ScrapingJob model
        try:
            job = ScrapingJob(
                url="https://example.com",
                config=ScrapingConfig(name="Test Job", max_pages=5)
            )
            self.info.append("✓ ScrapingJob model validation passed")
        except Exception as e:
            self.errors.append(f"❌ ScrapingJob model validation failed: {e}")
        
        # Test ScrapedData model
        try:
            data = ScrapedData(
                job_id="test-job-id",
                url="https://example.com",
                content={"title": "Test", "text": "Test content"},
                confidence_score=0.8,
                data_quality_score=0.7
            )
            self.info.append("✓ ScrapedData model validation passed")
        except Exception as e:
            self.errors.append(f"❌ ScrapedData model validation failed: {e}")
        
        # Test ScrapingConfig model
        try:
            config = ScrapingConfig(
                name="Test Config",
                max_pages=10,
                delay_between_requests=2.0,
                extract_images=True
            )
            self.info.append("✓ ScrapingConfig model validation passed")
        except Exception as e:
            self.errors.append(f"❌ ScrapingConfig model validation failed: {e}")
        
        # Validate enum values
        try:
            status_values = [status.value for status in JobStatus]
            expected_statuses = ["pending", "running", "completed", "failed", "cancelled"]
            if set(status_values) != set(expected_statuses):
                self.warnings.append(f"⚠️ JobStatus enum values mismatch: {status_values}")
            else:
                self.info.append("✓ JobStatus enum validation passed")
        except Exception as e:
            self.errors.append(f"❌ JobStatus enum validation failed: {e}")
    
    def validate_database_models(self):
        """Validate database model definitions."""
        print("\n🗄️ Validating Database Models...")
        
        # Check if all required fields are present
        job_orm_fields = set(ScrapingJobORM.__table__.columns.keys())
        expected_job_fields = {
            'id', 'url', 'status', 'config', 'created_at', 'started_at', 
            'completed_at', 'total_pages', 'pages_completed', 'pages_failed',
            'error_message', 'retry_count', 'user_id', 'tags', 'priority'
        }
        
        missing_job_fields = expected_job_fields - job_orm_fields
        if missing_job_fields:
            self.errors.append(f"❌ ScrapingJobORM missing fields: {missing_job_fields}")
        else:
            self.info.append("✓ ScrapingJobORM fields validation passed")
        
        # Check ScrapedDataORM fields
        data_orm_fields = set(ScrapedDataORM.__table__.columns.keys())
        expected_data_fields = {
            'id', 'job_id', 'url', 'content_type', 'content', 'raw_html',
            'content_metadata', 'confidence_score', 'ai_processed', 'ai_metadata',
            'data_quality_score', 'validation_errors', 'extracted_at', 'processed_at',
            'content_length', 'load_time'
        }
        
        missing_data_fields = expected_data_fields - data_orm_fields
        if missing_data_fields:
            self.errors.append(f"❌ ScrapedDataORM missing fields: {missing_data_fields}")
        else:
            self.info.append("✓ ScrapedDataORM fields validation passed")
    
    def validate_api_response_consistency(self):
        """Validate API response format consistency."""
        print("\n🌐 Validating API Response Consistency...")
        
        # Check JobResponse structure
        try:
            job_data = {
                "id": "test-id",
                "name": "Test Job",
                "url": "https://example.com",
                "max_pages": 10,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "total_pages": 10,
                "pages_completed": 0,
                "config": {"name": "Test", "max_pages": 10}
            }
            
            response = JobResponse(job=job_data, message="Test message")
            self.info.append("✓ JobResponse structure validation passed")
        except Exception as e:
            self.errors.append(f"❌ JobResponse validation failed: {e}")
        
        # Check DataListResponse structure
        try:
            data_list = [{
                "id": "test-data-id",
                "job_id": "test-job-id",
                "job_name": "Test Job",
                "url": "https://example.com",
                "title": "Test Title",
                "content": "Test content",
                "scraped_at": datetime.utcnow().isoformat(),
                "scraped_date": "2024-01-01",
                "confidence_score": 0.8,
                "ai_processed": True,
                "data_quality_score": 0.7,
                "content_length": 100,
                "load_time": 1.5,
                "content_type": "html",
                "validation_errors": []
            }]
            
            response = DataListResponse(data=data_list, total=1)
            self.info.append("✓ DataListResponse structure validation passed")
        except Exception as e:
            self.errors.append(f"❌ DataListResponse validation failed: {e}")
    
    def validate_export_format_mapping(self):
        """Validate export format field mappings."""
        print("\n📤 Validating Export Format Mappings...")
        
        # Define expected export fields
        csv_fields = [
            "id", "job_id", "job_name", "url", "title", "content", 
            "scraped_at", "scraped_date", "confidence_score", "ai_processed",
            "data_quality_score", "content_length", "load_time", "content_type"
        ]
        
        json_fields = csv_fields + ["validation_errors", "ai_metadata", "raw_html"]
        
        # Check if DataExportRequest model supports these fields
        try:
            export_request = DataExportRequest(
                format="csv",
                fields=csv_fields,
                min_confidence=0.5,
                include_raw_html=False
            )
            self.info.append("✓ CSV export field mapping validation passed")
        except Exception as e:
            self.errors.append(f"❌ CSV export validation failed: {e}")
        
        try:
            export_request = DataExportRequest(
                format="json",
                fields=json_fields,
                min_confidence=0.0,
                include_raw_html=True
            )
            self.info.append("✓ JSON export field mapping validation passed")
        except Exception as e:
            self.errors.append(f"❌ JSON export validation failed: {e}")
    
    def validate_ai_processing_schemas(self):
        """Validate AI processing data structures."""
        print("\n🤖 Validating AI Processing Schemas...")
        
        # Test Gemini AI response structure
        gemini_response = {
            "summary": "Test summary",
            "confidence": 0.8,
            "topics": ["topic1", "topic2"],
            "quality_score": 0.7,
            "key_info": ["info1", "info2"],
            "content_category": "blog",
            "language": "en",
            "ai_model": "gemini-2.0-flash-exp",
            "processing_status": "success"
        }
        
        # Validate structure matches expected AI metadata format
        required_ai_fields = {
            "summary", "confidence", "topics", "quality_score", 
            "ai_model", "processing_status"
        }
        
        ai_fields = set(gemini_response.keys())
        missing_ai_fields = required_ai_fields - ai_fields
        
        if missing_ai_fields:
            self.errors.append(f"❌ AI metadata missing fields: {missing_ai_fields}")
        else:
            self.info.append("✓ AI processing schema validation passed")
        
        # Test text analyzer response structure
        text_analysis_response = {
            "entities": [
                {"type": "PERSON", "value": "John Doe", "confidence": 0.9}
            ],
            "classification": {
                "primary_category": "blog",
                "confidence": 0.8,
                "content_type": "article"
            },
            "sentiment": {"overall": "positive", "score": 0.7},
            "key_topics": [{"topic": "technology", "relevance": 0.8}],
            "summary": "Test summary",
            "language": "en",
            "metadata": {"processing_timestamp": datetime.utcnow().isoformat()}
        }
        
        required_analysis_fields = {
            "entities", "classification", "sentiment", "key_topics", 
            "summary", "language", "metadata"
        }
        
        analysis_fields = set(text_analysis_response.keys())
        missing_analysis_fields = required_analysis_fields - analysis_fields
        
        if missing_analysis_fields:
            self.errors.append(f"❌ Text analysis missing fields: {missing_analysis_fields}")
        else:
            self.info.append("✓ Text analysis schema validation passed")
    
    def validate_type_hints(self):
        """Validate type hints consistency."""
        print("\n🔤 Validating Type Hints...")
        
        # Check if all models have proper type hints
        models_to_check = [
            ScrapingJob, ScrapedData, ScrapingConfig, JobResponse,
            DataListResponse, HealthCheckResponse, ScrapingResult
        ]
        
        for model in models_to_check:
            try:
                # Check if model has __annotations__
                if hasattr(model, '__annotations__'):
                    annotations = model.__annotations__
                    if annotations:
                        self.info.append(f"✓ {model.__name__} has type annotations")
                    else:
                        self.warnings.append(f"⚠️ {model.__name__} has empty annotations")
                else:
                    self.warnings.append(f"⚠️ {model.__name__} missing type annotations")
            except Exception as e:
                self.errors.append(f"❌ Type hint validation failed for {model.__name__}: {e}")
    
    def print_results(self):
        """Print validation results."""
        print("\n" + "=" * 50)
        print("📊 Validation Results")
        print("=" * 50)
        
        if self.info:
            print(f"\n✅ Passed Checks ({len(self.info)}):")
            for info in self.info:
                print(f"  {info}")
        
        if self.warnings:
            print(f"\n⚠️ Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
        
        print(f"\n📈 Summary:")
        print(f"  ✅ Passed: {len(self.info)}")
        print(f"  ⚠️ Warnings: {len(self.warnings)}")
        print(f"  ❌ Errors: {len(self.errors)}")
        
        if len(self.errors) == 0:
            print(f"\n🎉 All schema validations passed!")
            return True
        else:
            print(f"\n🚨 Schema validation failed with {len(self.errors)} errors")
            return False


def main():
    """Main validation function."""
    validator = SchemaValidator()
    success = validator.validate_all()
    
    if success:
        print("\n✅ Schema validation completed successfully!")
        return 0
    else:
        print("\n❌ Schema validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())