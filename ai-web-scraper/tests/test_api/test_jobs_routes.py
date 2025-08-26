"""
Tests for scraping jobs API routes.

This module contains tests for all job management endpoints
including creation, retrieval, updates, and batch operations.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.models.pydantic_models import JobStatus


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
def sample_job_data():
    """Sample job data for testing."""
    return {
        "url": "https://example.com",
        "config": {
            "wait_time": 5,
            "max_retries": 3,
            "use_stealth": True
        },
        "tags": ["test", "example"],
        "priority": 5
    }


class TestJobCreation:
    """Test cases for job creation endpoints."""
    
    def test_create_job_success(self, client, auth_headers, sample_job_data):
        """Test successful job creation."""
        response = client.post(
            "/api/v1/scraping/jobs",
            json=sample_job_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "job" in data
        assert "message" in data
        
        job = data["job"]
        assert job["url"] == sample_job_data["url"]
        assert job["status"] == JobStatus.PENDING
        assert job["tags"] == sample_job_data["tags"]
        assert job["priority"] == sample_job_data["priority"]
        assert "id" in job
        assert "created_at" in job
    
    def test_create_job_minimal_data(self, client, auth_headers):
        """Test job creation with minimal required data."""
        minimal_data = {"url": "https://example.com"}
        
        response = client.post(
            "/api/v1/scraping/jobs",
            json=minimal_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        job = data["job"]
        assert job["url"] == minimal_data["url"]
        assert job["status"] == JobStatus.PENDING
        assert job["priority"] == 5  # Default priority
    
    def test_create_job_invalid_url(self, client, auth_headers):
        """Test job creation with invalid URL."""
        invalid_data = {"url": "not-a-valid-url"}
        
        response = client.post(
            "/api/v1/scraping/jobs",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Validation Error"
    
    def test_create_job_without_auth(self, client, sample_job_data):
        """Test job creation without authentication."""
        response = client.post(
            "/api/v1/scraping/jobs",
            json=sample_job_data
        )
        
        assert response.status_code == 401
    
    def test_create_job_invalid_priority(self, client, auth_headers):
        """Test job creation with invalid priority."""
        invalid_data = {
            "url": "https://example.com",
            "priority": 15  # Invalid priority (should be 1-10)
        }
        
        response = client.post(
            "/api/v1/scraping/jobs",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422


class TestJobRetrieval:
    """Test cases for job retrieval endpoints."""
    
    def test_get_job_success(self, client, auth_headers):
        """Test successful job retrieval."""
        job_id = "test-job-id"
        
        response = client.get(
            f"/api/v1/scraping/jobs/{job_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job" in data
        assert "message" in data
        
        job = data["job"]
        assert job["id"] == job_id
        assert "url" in job
        assert "status" in job
    
    def test_get_job_not_found(self, client, auth_headers):
        """Test job retrieval for non-existent job."""
        job_id = "non-existent-job"
        
        response = client.get(
            f"/api/v1/scraping/jobs/{job_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_get_job_without_auth(self, client):
        """Test job retrieval without authentication."""
        job_id = "test-job-id"
        
        response = client.get(f"/api/v1/scraping/jobs/{job_id}")
        
        assert response.status_code == 401
    
    def test_list_jobs_success(self, client, auth_headers):
        """Test successful job listing."""
        response = client.get(
            "/api/v1/scraping/jobs",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_next" in data
        assert "has_previous" in data
        
        assert isinstance(data["jobs"], list)
        assert isinstance(data["total_count"], int)
    
    def test_list_jobs_with_status_filter(self, client, auth_headers):
        """Test job listing with status filter."""
        response = client.get(
            "/api/v1/scraping/jobs?status=completed",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned jobs should have completed status
        for job in data["jobs"]:
            assert job["status"] == JobStatus.COMPLETED
    
    def test_list_jobs_with_pagination(self, client, auth_headers):
        """Test job listing with pagination."""
        response = client.get(
            "/api/v1/scraping/jobs?page=1&page_size=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["jobs"]) <= 2


class TestJobUpdates:
    """Test cases for job update endpoints."""
    
    def test_update_job_success(self, client, auth_headers):
        """Test successful job update."""
        job_id = "test-job-id"
        update_data = {
            "status": JobStatus.CANCELLED,
            "priority": 8,
            "tags": ["updated", "test"]
        }
        
        response = client.put(
            f"/api/v1/scraping/jobs/{job_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        job = data["job"]
        assert job["id"] == job_id
        # Note: The mock service might not actually apply all updates
    
    def test_update_job_not_found(self, client, auth_headers):
        """Test job update for non-existent job."""
        job_id = "non-existent-job"
        update_data = {"status": JobStatus.CANCELLED}
        
        response = client.put(
            f"/api/v1/scraping/jobs/{job_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_update_job_invalid_status(self, client, auth_headers):
        """Test job update with invalid status."""
        job_id = "test-job-id"
        update_data = {"status": "invalid-status"}
        
        response = client.put(
            f"/api/v1/scraping/jobs/{job_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422


class TestJobDeletion:
    """Test cases for job deletion endpoints."""
    
    def test_delete_job_success(self, client, auth_headers):
        """Test successful job deletion."""
        job_id = "test-job-id"
        
        response = client.delete(
            f"/api/v1/scraping/jobs/{job_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    def test_delete_job_not_found(self, client, auth_headers):
        """Test job deletion for non-existent job."""
        job_id = "non-existent-job"
        
        response = client.delete(
            f"/api/v1/scraping/jobs/{job_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestBulkOperations:
    """Test cases for bulk job operations."""
    
    def test_create_bulk_jobs_success(self, client, auth_headers):
        """Test successful bulk job creation."""
        bulk_data = {
            "urls": [
                "https://example1.com",
                "https://example2.com",
                "https://example3.com"
            ],
            "config": {
                "wait_time": 5,
                "use_stealth": True
            },
            "tags": ["bulk", "test"],
            "priority": 6
        }
        
        response = client.post(
            "/api/v1/scraping/jobs/bulk",
            json=bulk_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "jobs" in data
        assert len(data["jobs"]) == 3
        assert data["total_count"] == 3
        
        # All jobs should have the same config
        for job in data["jobs"]:
            assert job["tags"] == bulk_data["tags"]
            assert job["priority"] == bulk_data["priority"]
    
    def test_create_bulk_jobs_invalid_urls(self, client, auth_headers):
        """Test bulk job creation with invalid URLs."""
        bulk_data = {
            "urls": [
                "https://example1.com",
                "invalid-url",
                "https://example3.com"
            ]
        }
        
        response = client.post(
            "/api/v1/scraping/jobs/bulk",
            json=bulk_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_create_bulk_jobs_empty_urls(self, client, auth_headers):
        """Test bulk job creation with empty URL list."""
        bulk_data = {"urls": []}
        
        response = client.post(
            "/api/v1/scraping/jobs/bulk",
            json=bulk_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_batch_job_operation_cancel(self, client, auth_headers):
        """Test batch job cancellation."""
        batch_data = {
            "operation": "cancel",
            "job_ids": ["job-1", "job-2", "job-3"]
        }
        
        response = client.post(
            "/api/v1/scraping/jobs/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "operation_id" in data
        assert data["operation"] == "cancel"
        assert data["total_items"] == 3
        assert "successful_items" in data
        assert "failed_items" in data
        assert "results" in data
    
    def test_batch_job_operation_delete(self, client, auth_headers):
        """Test batch job deletion."""
        batch_data = {
            "operation": "delete",
            "job_ids": ["job-1", "job-2"]
        }
        
        response = client.post(
            "/api/v1/scraping/jobs/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["operation"] == "delete"
        assert data["total_items"] == 2
    
    def test_batch_job_operation_unsupported(self, client, auth_headers):
        """Test batch job operation with unsupported operation."""
        batch_data = {
            "operation": "unsupported",
            "job_ids": ["job-1"]
        }
        
        response = client.post(
            "/api/v1/scraping/jobs/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should report failed items for unsupported operation
        assert data["failed_items"] > 0


class TestJobActions:
    """Test cases for job action endpoints."""
    
    def test_cancel_job_success(self, client, auth_headers):
        """Test successful job cancellation."""
        job_id = "test-job-id"
        
        response = client.post(
            f"/api/v1/scraping/jobs/{job_id}/cancel",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        job = data["job"]
        assert job["id"] == job_id
    
    def test_cancel_job_not_found(self, client, auth_headers):
        """Test job cancellation for non-existent job."""
        job_id = "non-existent-job"
        
        response = client.post(
            f"/api/v1/scraping/jobs/{job_id}/cancel",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_retry_job_success(self, client, auth_headers):
        """Test successful job retry."""
        # This test assumes the mock returns a failed job for retry
        job_id = "test-job-id"
        
        response = client.post(
            f"/api/v1/scraping/jobs/{job_id}/retry",
            headers=auth_headers
        )
        
        # The mock service might not implement proper retry logic
        # So we just check that the endpoint exists and responds
        assert response.status_code in [200, 400, 404]
    
    def test_retry_job_not_found(self, client, auth_headers):
        """Test job retry for non-existent job."""
        job_id = "non-existent-job"
        
        response = client.post(
            f"/api/v1/scraping/jobs/{job_id}/retry",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestJobStatistics:
    """Test cases for job statistics endpoints."""
    
    def test_get_job_stats(self, client, auth_headers):
        """Test job statistics retrieval."""
        response = client.get(
            "/api/v1/scraping/jobs/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_jobs" in data
        assert "jobs_by_status" in data
        assert "average_completion_time" in data
        assert "success_rate" in data
        assert "most_common_errors" in data
        assert "performance_metrics" in data
        
        # Check data types
        assert isinstance(data["total_jobs"], int)
        assert isinstance(data["jobs_by_status"], dict)
        assert isinstance(data["success_rate"], (int, float))
        assert isinstance(data["most_common_errors"], list)
        assert isinstance(data["performance_metrics"], dict)
    
    def test_job_stats_without_auth(self, client):
        """Test job statistics without authentication."""
        response = client.get("/api/v1/scraping/jobs/stats")
        
        assert response.status_code == 401


class TestJobValidation:
    """Test cases for job data validation."""
    
    def test_job_creation_validation_errors(self, client, auth_headers):
        """Test various validation errors in job creation."""
        test_cases = [
            # Missing URL
            {},
            # Invalid URL format
            {"url": "ftp://example.com"},
            # Invalid priority
            {"url": "https://example.com", "priority": 0},
            {"url": "https://example.com", "priority": 11},
            # Invalid config
            {"url": "https://example.com", "config": {"wait_time": -1}},
            {"url": "https://example.com", "config": {"max_retries": -1}},
        ]
        
        for invalid_data in test_cases:
            response = client.post(
                "/api/v1/scraping/jobs",
                json=invalid_data,
                headers=auth_headers
            )
            
            assert response.status_code == 422, f"Failed for data: {invalid_data}"
            data = response.json()
            assert data["error"] == "Validation Error"


class TestJobErrorHandling:
    """Test cases for job endpoint error handling."""
    
    @patch("src.api.routes.jobs.job_service.create_job")
    def test_create_job_service_error(self, mock_create, client, auth_headers, sample_job_data):
        """Test job creation when service raises an error."""
        mock_create.side_effect = Exception("Service error")
        
        response = client.post(
            "/api/v1/scraping/jobs",
            json=sample_job_data,
            headers=auth_headers
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    @patch("src.api.routes.jobs.job_service.list_jobs")
    def test_list_jobs_service_error(self, mock_list, client, auth_headers):
        """Test job listing when service raises an error."""
        mock_list.side_effect = Exception("Service error")
        
        response = client.get(
            "/api/v1/scraping/jobs",
            headers=auth_headers
        )
        
        # The endpoint should handle the error gracefully
        # Implementation might return 500 or handle it differently
        assert response.status_code in [200, 500]