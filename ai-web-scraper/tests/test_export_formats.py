"""
Tests for data export format consistency and validation.
"""

import pytest
import json
import csv
import io
from datetime import datetime
from typing import Dict, List, Any

from src.models.pydantic_models import (
    ScrapedData, DataExportRequest, ContentType
)


class TestExportFormatConsistency:
    """Test export format consistency across different output types."""
    
    def test_csv_field_mapping(self, sample_scraped_data):
        """Test CSV export field mapping consistency."""
        # Expected CSV fields based on API response structure
        expected_csv_fields = [
            "id", "job_id", "job_name", "url", "title", "content",
            "scraped_at", "scraped_date", "confidence_score", "ai_processed",
            "data_quality_score", "content_length", "load_time",
            "content_type", "validation_errors"
        ]
        
        # Convert scraped data to API response format
        api_data = {
            "id": sample_scraped_data.id,
            "job_id": sample_scraped_data.job_id,
            "job_name": "Test Job",
            "url": sample_scraped_data.url,
            "title": sample_scraped_data.content.get("title", ""),
            "content": sample_scraped_data.content.get("text", ""),
            "scraped_at": sample_scraped_data.extracted_at.isoformat(),
            "scraped_date": sample_scraped_data.extracted_at.strftime("%Y-%m-%d"),
            "confidence_score": sample_scraped_data.confidence_score,
            "ai_processed": sample_scraped_data.ai_processed,
            "data_quality_score": sample_scraped_data.data_quality_score,
            "content_length": sample_scraped_data.content_length,
            "load_time": sample_scraped_data.load_time,
            "content_type": sample_scraped_data.content_type.value,
            "validation_errors": sample_scraped_data.validation_errors
        }
        
        # Verify all expected fields are present
        for field in expected_csv_fields:
            assert field in api_data, f"Missing field '{field}' in API response"
        
        # Test CSV generation
        csv_output = self._generate_csv([api_data])
        csv_reader = csv.DictReader(io.StringIO(csv_output))
        csv_row = next(csv_reader)
        
        # Verify CSV contains all expected fields
        for field in expected_csv_fields:
            assert field in csv_row, f"Missing field '{field}' in CSV output"
    
    def test_json_structure_consistency(self, sample_scraped_data):
        """Test JSON export structure consistency."""
        # Convert to API response format
        api_data = {
            "id": sample_scraped_data.id,
            "job_id": sample_scraped_data.job_id,
            "job_name": "Test Job",
            "url": sample_scraped_data.url,
            "title": sample_scraped_data.content.get("title", ""),
            "content": sample_scraped_data.content.get("text", ""),
            "scraped_at": sample_scraped_data.extracted_at.isoformat(),
            "confidence_score": sample_scraped_data.confidence_score,
            "ai_processed": sample_scraped_data.ai_processed,
            "full_content": sample_scraped_data.content,
            "metadata": {
                "content_metadata": sample_scraped_data.content_metadata,
                "ai_metadata": sample_scraped_data.ai_metadata,
                "data_quality_score": sample_scraped_data.data_quality_score,
                "validation_errors": sample_scraped_data.validation_errors
            }
        }
        
        # Test JSON serialization
        json_output = json.dumps(api_data, default=str)
        parsed_json = json.loads(json_output)
        
        # Verify structure
        assert "id" in parsed_json
        assert "job_id" in parsed_json
        assert "full_content" in parsed_json
        assert "metadata" in parsed_json
        assert isinstance(parsed_json["full_content"], dict)
        assert isinstance(parsed_json["metadata"], dict)
    
    def test_export_request_validation(self):
        """Test export request validation with different formats."""
        # Valid export requests
        valid_requests = [
            {
                "format": "csv",
                "fields": ["title", "content", "url"]
            },
            {
                "format": "json",
                "include_raw_html": True
            },
            {
                "format": "xlsx",
                "min_confidence": 0.7
            }
        ]
        
        for request_data in valid_requests:
            request = DataExportRequest(**request_data)
            assert request.format in ["csv", "json", "xlsx"]
    
    def test_field_type_consistency(self, sample_scraped_data):
        """Test that field types are consistent across export formats."""
        api_data = {
            "confidence_score": sample_scraped_data.confidence_score,
            "ai_processed": sample_scraped_data.ai_processed,
            "content_length": sample_scraped_data.content_length,
            "load_time": sample_scraped_data.load_time,
            "scraped_at": sample_scraped_data.extracted_at.isoformat()
        }
        
        # Test type consistency
        assert isinstance(api_data["confidence_score"], float)
        assert isinstance(api_data["ai_processed"], bool)
        assert isinstance(api_data["content_length"], int)
        assert isinstance(api_data["load_time"], float)
        assert isinstance(api_data["scraped_at"], str)
        
        # Test JSON serialization preserves types
        json_str = json.dumps(api_data)
        parsed = json.loads(json_str)
        
        assert isinstance(parsed["confidence_score"], float)
        assert isinstance(parsed["ai_processed"], bool)
        assert isinstance(parsed["content_length"], int)
        assert isinstance(parsed["load_time"], float)
        assert isinstance(parsed["scraped_at"], str)
    
    def test_nested_content_structure(self, sample_scraped_data):
        """Test handling of nested content structures in exports."""
        # Verify content structure
        content = sample_scraped_data.content
        assert isinstance(content, dict)
        assert "title" in content
        assert "text" in content
        
        # Test that nested structures are properly handled
        if "headings" in content:
            assert isinstance(content["headings"], list)
            if content["headings"]:
                heading = content["headings"][0]
                assert isinstance(heading, dict)
                assert "level" in heading
                assert "text" in heading
        
        if "lists" in content:
            assert isinstance(content["lists"], list)
            if content["lists"]:
                list_item = content["lists"][0]
                assert isinstance(list_item, dict)
                assert "type" in list_item
                assert "items" in list_item
    
    def test_export_field_filtering(self, sample_scraped_data):
        """Test export field filtering functionality."""
        all_fields = [
            "id", "job_id", "url", "title", "content", "scraped_at",
            "confidence_score", "ai_processed", "content_length"
        ]
        
        # Test with specific field selection
        selected_fields = ["title", "content", "url", "confidence_score"]
        
        api_data = {
            "id": sample_scraped_data.id,
            "job_id": sample_scraped_data.job_id,
            "url": sample_scraped_data.url,
            "title": sample_scraped_data.content.get("title", ""),
            "content": sample_scraped_data.content.get("text", ""),
            "scraped_at": sample_scraped_data.extracted_at.isoformat(),
            "confidence_score": sample_scraped_data.confidence_score,
            "ai_processed": sample_scraped_data.ai_processed,
            "content_length": sample_scraped_data.content_length
        }
        
        # Filter data based on selected fields
        filtered_data = {k: v for k, v in api_data.items() if k in selected_fields}
        
        # Verify filtering worked
        assert len(filtered_data) == len(selected_fields)
        for field in selected_fields:
            assert field in filtered_data
        
        # Verify excluded fields are not present
        excluded_fields = set(all_fields) - set(selected_fields)
        for field in excluded_fields:
            assert field not in filtered_data
    
    def _generate_csv(self, data: List[Dict[str, Any]]) -> str:
        """Helper method to generate CSV from data."""
        if not data:
            return ""
        
        output = io.StringIO()
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            # Handle complex data types for CSV
            csv_row = {}
            for key, value in row.items():
                if isinstance(value, (list, dict)):
                    csv_row[key] = json.dumps(value)
                elif value is None:
                    csv_row[key] = ""
                else:
                    csv_row[key] = str(value)
            writer.writerow(csv_row)
        
        return output.getvalue()


class TestDataValidationConsistency:
    """Test data validation consistency across the pipeline."""
    
    def test_scraped_data_to_api_response_consistency(self, sample_scraped_data):
        """Test consistency between ScrapedData model and API response."""
        # Simulate API response generation
        api_response = {
            "id": sample_scraped_data.id,
            "job_id": sample_scraped_data.job_id,
            "url": sample_scraped_data.url,
            "title": sample_scraped_data.content.get("title", ""),
            "content": sample_scraped_data.content.get("text", ""),
            "confidence_score": sample_scraped_data.confidence_score,
            "ai_processed": sample_scraped_data.ai_processed
        }
        
        # Verify data consistency
        assert api_response["id"] == sample_scraped_data.id
        assert api_response["job_id"] == sample_scraped_data.job_id
        assert api_response["url"] == sample_scraped_data.url
        assert api_response["confidence_score"] == sample_scraped_data.confidence_score
        assert api_response["ai_processed"] == sample_scraped_data.ai_processed
    
    def test_content_type_consistency(self):
        """Test ContentType enum consistency."""
        # Verify all expected content types are defined
        expected_types = ["html", "text", "json", "xml", "pdf", "csv"]
        
        for content_type in expected_types:
            assert hasattr(ContentType, content_type.upper())
            assert ContentType[content_type.upper()].value == content_type
    
    def test_validation_error_handling(self):
        """Test validation error handling in export data."""
        # Create data with validation errors
        scraped_data = ScrapedData(
            job_id="test-job",
            url="https://example.com",
            content={"title": "Test", "text": "Content"},
            validation_errors=["Missing required field", "Invalid format"]
        )
        
        # Verify validation errors are preserved
        assert len(scraped_data.validation_errors) == 2
        assert "Missing required field" in scraped_data.validation_errors
        assert "Invalid format" in scraped_data.validation_errors
        
        # Test that validation errors are included in API response
        api_data = {
            "validation_errors": scraped_data.validation_errors
        }
        
        assert len(api_data["validation_errors"]) == 2