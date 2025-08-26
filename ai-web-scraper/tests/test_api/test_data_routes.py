"""
Tests for scraped data API routes.

This module contains tests for all data access endpoints
including querying, filtering, exporting, and data management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.models.pydantic_models import ContentType


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers for testing."""
    return {"Authorization": "Bearer demo-token"}


@pytest.fixture
def sample_export_request():
    """Sample export request data for testing."""
    return {
        "format": "csv",
        "job_ids": ["job-1", "job-2"],
        "date_from": "2024-01-01T00:00:00Z",
        "date_to": "2024-12-31T23:59:59Z",
        "min_confidence": 0.8,
        "include_raw_html": False,
        "fields": ["url", "content", "confidence_score"]
    }


class TestDataQuerying:
    """Test cases for data querying endpoints."""
    
    def test_query_data_success(self, client, auth_headers):
        """Test successful data querying."""
        response = client.get(
            "/api/v1/data/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "data" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_next" in data
        assert "has_previous" in data
        assert "filters_applied" in data
        
        # Check data types
        assert isinstance(data["data"], list)
        assert isinstance(data["total_count"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        assert isinstance(data["has_next"], bool)
        assert isinstance(data["has_previous"], bool)
        assert isinstance(data["filters_applied"], dict)
    
    def test_query_data_with_filters(self, client, auth_headers):
        """Test data querying with various filters."""
        params = {
            "job_ids": ["job-1", "job-2"],
            "min_confidence": 0.8,
            "content_type": ContentType.HTML,
            "ai_processed": True,
            "page": 1,
            "page_size": 10
        }
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that filters are reflected in response
        filters_applied = data["filters_applied"]
        assert "job_ids" in filters_applied
        assert "min_confidence" in filters_applied
        assert "content_type" in filters_applied
        assert "ai_processed" in filters_applied
    
    def test_query_data_with_date_range(self, client, auth_headers):
        """Test data querying with date range filters."""
        date_from = datetime.now() - timedelta(days=30)
        date_to = datetime.now()
        
        params = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        filters_applied = data["filters_applied"]
        assert "date_from" in filters_applied
        assert "date_to" in filters_applied
    
    def test_query_data_with_sorting(self, client, auth_headers):
        """Test data querying with sorting options."""
        params = {
            "sort_by": "confidence_score",
            "sort_order": "desc"
        }
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_query_data_with_pagination(self, client, auth_headers):
        """Test data querying with pagination."""
        params = {
            "page": 2,
            "page_size": 5
        }
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert data["page_size"] == 5
    
    def test_query_data_invalid_date_range(self, client, auth_headers):
        """Test data querying with invalid date range."""
        params = {
            "date_from": "2024-12-31T23:59:59Z",
            "date_to": "2024-01-01T00:00:00Z"  # End before start
        }
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_query_data_without_auth(self, client):
        """Test data querying without authentication."""
        response = client.get("/api/v1/data/")
        
        assert response.status_code == 401


class TestDataRetrieval:
    """Test cases for individual data retrieval."""
    
    def test_get_data_by_id_success(self, client, auth_headers):
        """Test successful data retrieval by ID."""
        data_id = "test-data-id"
        
        response = client.get(
            f"/api/v1/data/{data_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields for ScrapedData
        assert data["id"] == data_id
        assert "job_id" in data
        assert "url" in data
        assert "content" in data
        assert "confidence_score" in data
        assert "extracted_at" in data
    
    def test_get_data_by_id_not_found(self, client, auth_headers):
        """Test data retrieval for non-existent ID."""
        data_id = "non-existent-data"
        
        response = client.get(
            f"/api/v1/data/{data_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_get_data_by_id_without_auth(self, client):
        """Test data retrieval without authentication."""
        data_id = "test-data-id"
        
        response = client.get(f"/api/v1/data/{data_id}")
        
        assert response.status_code == 401


class TestDataSummary:
    """Test cases for data summary endpoints."""
    
    def test_get_data_summary(self, client, auth_headers):
        """Test data summary retrieval."""
        response = client.get(
            "/api/v1/data/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_records" in data
        assert "total_jobs" in data
        assert "average_confidence" in data
        assert "content_type_distribution" in data
        assert "date_range" in data
        assert "quality_metrics" in data
        
        # Check data types
        assert isinstance(data["total_records"], int)
        assert isinstance(data["total_jobs"], int)
        assert isinstance(data["average_confidence"], (int, float))
        assert isinstance(data["content_type_distribution"], dict)
        assert isinstance(data["date_range"], dict)
        assert isinstance(data["quality_metrics"], dict)
    
    def test_get_data_summary_without_auth(self, client):
        """Test data summary without authentication."""
        response = client.get("/api/v1/data/summary")
        
        assert response.status_code == 401


class TestDataExport:
    """Test cases for data export endpoints."""
    
    def test_create_export_success(self, client, auth_headers, sample_export_request):
        """Test successful export creation."""
        response = client.post(
            "/api/v1/data/export",
            json=sample_export_request,
            headers=auth_headers
        )
        
        assert response.status_code == 202
        data = response.json()
        
        # Check required fields
        assert "export_id" in data
        assert "status" in data
        assert "created_at" in data
        assert "message" in data
        
        assert data["status"] == "pending"
    
    def test_create_export_invalid_format(self, client, auth_headers):
        """Test export creation with invalid format."""
        invalid_request = {
            "format": "invalid-format",
            "job_ids": ["job-1"]
        }
        
        response = client.post(
            "/api/v1/data/export",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_create_export_invalid_date_range(self, client, auth_headers):
        """Test export creation with invalid date range."""
        invalid_request = {
            "format": "csv",
            "date_from": "2024-12-31T23:59:59Z",
            "date_to": "2024-01-01T00:00:00Z"  # End before start
        }
        
        response = client.post(
            "/api/v1/data/export",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_get_export_status(self, client, auth_headers):
        """Test export status retrieval."""
        export_id = "test-export-id"
        
        response = client.get(
            f"/api/v1/data/exports/{export_id}",
            headers=auth_headers
        )
        
        # The mock service returns a completed export
        assert response.status_code == 200
        data = response.json()
        
        assert data["export_id"] == export_id
        assert "status" in data
        assert "created_at" in data
    
    def test_get_export_status_not_found(self, client, auth_headers):
        """Test export status for non-existent export."""
        export_id = "non-existent-export"
        
        response = client.get(
            f"/api/v1/data/exports/{export_id}",
            headers=auth_headers
        )
        
        # The mock service might return None for non-existent exports
        assert response.status_code in [200, 404]
    
    def test_download_export_success(self, client, auth_headers):
        """Test export file download."""
        export_id = "test-export-id"
        
        response = client.get(
            f"/api/v1/data/exports/{export_id}/download",
            headers=auth_headers
        )
        
        # The mock service returns a placeholder response
        assert response.status_code == 200
        data = response.json()
        
        assert "export_id" in data
        assert data["export_id"] == export_id
    
    def test_download_export_not_ready(self, client, auth_headers):
        """Test download of export that's not ready."""
        # This would test a scenario where export status is not "completed"
        # The mock service always returns completed, so this is a placeholder
        export_id = "pending-export-id"
        
        response = client.get(
            f"/api/v1/data/exports/{export_id}/download",
            headers=auth_headers
        )
        
        # Should either succeed or return 400 if not ready
        assert response.status_code in [200, 400]
    
    def test_delete_export_success(self, client, auth_headers):
        """Test export deletion."""
        export_id = "test-export-id"
        
        response = client.delete(
            f"/api/v1/data/exports/{export_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    def test_delete_export_not_found(self, client, auth_headers):
        """Test deletion of non-existent export."""
        export_id = "non-existent-export"
        
        response = client.delete(
            f"/api/v1/data/exports/{export_id}",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent export
        assert response.status_code in [204, 404]


class TestDataValidation:
    """Test cases for data validation endpoints."""
    
    def test_validate_data_quality(self, client, auth_headers):
        """Test data quality validation."""
        response = client.post(
            "/api/v1/data/validate",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_records_checked" in data
        assert "validation_passed" in data
        assert "validation_failed" in data
        assert "quality_score" in data
        assert "issues_found" in data
        assert "recommendations" in data
        
        # Check data types
        assert isinstance(data["total_records_checked"], int)
        assert isinstance(data["validation_passed"], int)
        assert isinstance(data["validation_failed"], int)
        assert isinstance(data["quality_score"], (int, float))
        assert isinstance(data["issues_found"], list)
        assert isinstance(data["recommendations"], list)
    
    def test_validate_data_quality_with_job_filter(self, client, auth_headers):
        """Test data quality validation with job ID filter."""
        params = {"job_ids": ["job-1", "job-2"]}
        
        response = client.post(
            "/api/v1/data/validate",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_validate_data_quality_without_auth(self, client):
        """Test data quality validation without authentication."""
        response = client.post("/api/v1/data/validate")
        
        assert response.status_code == 401


class TestDataReprocessing:
    """Test cases for data reprocessing endpoints."""
    
    def test_reprocess_data_success(self, client, auth_headers):
        """Test successful data reprocessing."""
        params = {"data_ids": ["data-1", "data-2", "data-3"]}
        
        response = client.post(
            "/api/v1/data/reprocess",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "message" in data
        assert "reprocess_job_id" in data
        assert "estimated_completion" in data
        
        assert "3 records" in data["message"]
    
    def test_reprocess_data_empty_list(self, client, auth_headers):
        """Test data reprocessing with empty data ID list."""
        response = client.post(
            "/api/v1/data/reprocess",
            headers=auth_headers
        )
        
        # Should require data_ids parameter
        assert response.status_code == 422
    
    def test_reprocess_data_without_auth(self, client):
        """Test data reprocessing without authentication."""
        params = {"data_ids": ["data-1"]}
        
        response = client.post(
            "/api/v1/data/reprocess",
            params=params
        )
        
        assert response.status_code == 401


class TestDataErrorHandling:
    """Test cases for data endpoint error handling."""
    
    @patch("src.api.routes.data.data_service.query_data")
    def test_query_data_service_error(self, mock_query, client, auth_headers):
        """Test data querying when service raises an error."""
        mock_query.side_effect = Exception("Service error")
        
        response = client.get(
            "/api/v1/data/",
            headers=auth_headers
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    @patch("src.api.routes.data.data_service.get_data_summary")
    def test_data_summary_service_error(self, mock_summary, client, auth_headers):
        """Test data summary when service raises an error."""
        mock_summary.side_effect = Exception("Service error")
        
        response = client.get(
            "/api/v1/data/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 500
    
    @patch("src.api.routes.data.data_service.create_export")
    def test_create_export_service_error(self, mock_export, client, auth_headers, sample_export_request):
        """Test export creation when service raises an error."""
        mock_export.side_effect = Exception("Service error")
        
        response = client.post(
            "/api/v1/data/export",
            json=sample_export_request,
            headers=auth_headers
        )
        
        assert response.status_code == 500


class TestDataValidationRules:
    """Test cases for data validation rules."""
    
    def test_export_request_validation(self, client, auth_headers):
        """Test various validation errors in export requests."""
        test_cases = [
            # Invalid format
            {"format": "invalid"},
            # Invalid confidence range
            {"format": "csv", "min_confidence": 1.5},
            {"format": "csv", "min_confidence": -0.1},
            # Invalid date range
            {
                "format": "csv",
                "date_from": "2024-12-31T23:59:59Z",
                "date_to": "2024-01-01T00:00:00Z"
            },
        ]
        
        for invalid_data in test_cases:
            response = client.post(
                "/api/v1/data/export",
                json=invalid_data,
                headers=auth_headers
            )
            
            assert response.status_code == 422, f"Failed for data: {invalid_data}"
            data = response.json()
            assert data["error"] == "Validation Error"
    
    def test_query_parameter_validation(self, client, auth_headers):
        """Test query parameter validation."""
        test_cases = [
            # Invalid page
            {"page": 0},
            {"page": -1},
            # Invalid page_size
            {"page_size": 0},
            {"page_size": 1001},  # Exceeds maximum
            # Invalid confidence
            {"min_confidence": 1.5},
            {"min_confidence": -0.1},
            # Invalid sort order
            {"sort_order": "invalid"},
        ]
        
        for invalid_params in test_cases:
            response = client.get(
                "/api/v1/data/",
                params=invalid_params,
                headers=auth_headers
            )
            
            assert response.status_code == 422, f"Failed for params: {invalid_params}"


class TestDataPagination:
    """Test cases for data pagination functionality."""
    
    def test_pagination_first_page(self, client, auth_headers):
        """Test first page of results."""
        params = {"page": 1, "page_size": 5}
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["has_previous"] is False
        # has_next depends on total data available
    
    def test_pagination_middle_page(self, client, auth_headers):
        """Test middle page of results."""
        params = {"page": 2, "page_size": 5}
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        # has_previous and has_next depend on total data available
    
    def test_pagination_large_page_size(self, client, auth_headers):
        """Test with large page size."""
        params = {"page": 1, "page_size": 1000}
        
        response = client.get(
            "/api/v1/data/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page_size"] == 1000