"""
Tests for the main FastAPI application.

This module contains tests for the main application setup,
middleware configuration, and global exception handling.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user for testing."""
    return {
        "user_id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"]
    }


class TestMainApplication:
    """Test cases for the main FastAPI application."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns API information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Intelligent Web Scraper API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "redoc" in data
        assert "openapi" in data
    
    def test_openapi_schema(self, client):
        """Test that OpenAPI schema is generated correctly."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Intelligent Web Scraper API"
        assert schema["info"]["version"] == "1.0.0"
        assert "paths" in schema
        assert "components" in schema
    
    def test_docs_endpoint(self, client):
        """Test that API documentation is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_endpoint(self, client):
        """Test that ReDoc documentation is accessible."""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.options("/api/v1/health/")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_security_headers(self, client):
        """Test that security headers are added to responses."""
        response = client.get("/api/v1/health/")
        
        # Security headers should be present
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-xss-protection") == "1; mode=block"
    
    def test_correlation_id_header(self, client):
        """Test that correlation ID is added to responses."""
        response = client.get("/api/v1/health/")
        
        assert "x-correlation-id" in response.headers
        assert "x-processing-time" in response.headers
    
    def test_validation_error_handling(self, client):
        """Test that validation errors are handled properly."""
        # Send invalid data to an endpoint that expects validation
        response = client.post(
            "/api/v1/scraping/jobs",
            json={"invalid": "data"},
            headers={"Authorization": "Bearer demo-token"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Validation Error"
        assert "details" in data
    
    def test_general_exception_handling(self, client):
        """Test that general exceptions are handled gracefully."""
        # This would test a scenario that causes an unhandled exception
        # For now, we'll test that the handler structure is in place
        with patch("src.api.routes.health.get_database_status") as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            response = client.get("/api/v1/health/")
            
            # Should return 503 for health check failures
            assert response.status_code == 503


class TestMiddleware:
    """Test cases for middleware functionality."""
    
    def test_logging_middleware(self, client):
        """Test that logging middleware adds correlation ID."""
        response = client.get("/api/v1/health/")
        
        # Correlation ID should be present
        assert "x-correlation-id" in response.headers
        correlation_id = response.headers["x-correlation-id"]
        assert len(correlation_id) > 0
    
    def test_rate_limiting_middleware(self, client):
        """Test that rate limiting middleware adds headers."""
        response = client.get("/api/v1/health/")
        
        # Rate limit headers should be present for non-health endpoints
        # Health endpoints are exempt, so test with a different endpoint
        response = client.get("/api/v1/data/", headers={"Authorization": "Bearer demo-token"})
        
        if response.status_code != 401:  # Skip if auth fails
            assert "x-ratelimit-limit" in response.headers
            assert "x-ratelimit-remaining" in response.headers
            assert "x-ratelimit-reset" in response.headers
    
    def test_auth_middleware_exempt_paths(self, client):
        """Test that authentication middleware exempts certain paths."""
        # Health endpoints should not require authentication
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        
        # Root endpoint should not require authentication
        response = client.get("/")
        assert response.status_code == 200
        
        # Docs should not require authentication
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_auth_middleware_protected_paths(self, client):
        """Test that authentication middleware protects API endpoints."""
        # API endpoints should require authentication
        response = client.get("/api/v1/scraping/jobs")
        assert response.status_code == 401
        
        response = client.get("/api/v1/data/")
        assert response.status_code == 401
    
    def test_auth_middleware_with_valid_token(self, client):
        """Test that valid tokens are accepted."""
        headers = {"Authorization": "Bearer demo-token"}
        
        # Should be able to access protected endpoints with valid token
        response = client.get("/api/v1/scraping/jobs", headers=headers)
        # Should not return 401 (might return other status codes based on implementation)
        assert response.status_code != 401


class TestApplicationLifespan:
    """Test cases for application lifespan events."""
    
    @patch("src.api.main.logger")
    def test_startup_logging(self, mock_logger):
        """Test that startup events are logged."""
        # Create app to trigger lifespan events
        app = create_app()
        client = TestClient(app)
        
        # Make a request to ensure app is started
        client.get("/")
        
        # Check that startup was logged
        mock_logger.info.assert_any_call("Starting FastAPI application")
    
    def test_app_creation(self):
        """Test that the application is created successfully."""
        app = create_app()
        
        assert app.title == "Intelligent Web Scraper API"
        assert app.version == "1.0.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"


class TestErrorResponses:
    """Test cases for error response formats."""
    
    def test_404_error_format(self, client):
        """Test that 404 errors return proper format."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        # FastAPI returns a standard 404 format
        data = response.json()
        assert "detail" in data
    
    def test_method_not_allowed_format(self, client):
        """Test that 405 errors return proper format."""
        # Try to POST to a GET-only endpoint
        response = client.post("/api/v1/health/")
        
        assert response.status_code == 405
        data = response.json()
        assert "detail" in data
    
    def test_validation_error_format(self, client):
        """Test that validation errors return consistent format."""
        response = client.post(
            "/api/v1/scraping/jobs",
            json={"url": "invalid-url"},  # Invalid URL format
            headers={"Authorization": "Bearer demo-token"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Validation Error"
        assert data["message"] == "The request contains invalid data"
        assert "details" in data
        assert isinstance(data["details"], list)


class TestOpenAPICustomization:
    """Test cases for OpenAPI schema customization."""
    
    def test_security_scheme_in_openapi(self, client):
        """Test that security scheme is properly defined in OpenAPI."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Check that security scheme is defined
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
        assert "BearerAuth" in schema["components"]["securitySchemes"]
        
        bearer_auth = schema["components"]["securitySchemes"]["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"
    
    def test_api_description_in_openapi(self, client):
        """Test that API description is properly set."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert "info" in schema
        assert "description" in schema["info"]
        description = schema["info"]["description"]
        
        # Check that description contains key information
        assert "Overview" in description
        assert "Authentication" in description
        assert "Rate Limiting" in description
        assert "Error Handling" in description