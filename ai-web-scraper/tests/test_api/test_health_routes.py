"""
Tests for health check API routes.

This module contains tests for all health check endpoints
including basic health, detailed stats, and probe endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.main import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    app = create_app()
    return TestClient(app)


class TestHealthRoutes:
    """Test cases for health check endpoints."""
    
    def test_basic_health_check(self, client):
        """Test the basic health check endpoint."""
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "database_connected" in data
        assert "redis_connected" in data
        assert "active_jobs" in data
        assert "system_metrics" in data
        
        # Check data types
        assert isinstance(data["uptime_seconds"], (int, float))
        assert isinstance(data["database_connected"], bool)
        assert isinstance(data["redis_connected"], bool)
        assert isinstance(data["active_jobs"], int)
        assert isinstance(data["system_metrics"], dict)
    
    @patch("src.api.routes.health.get_database_status")
    @patch("src.api.routes.health.get_redis_status")
    def test_health_check_with_db_failure(self, mock_redis, mock_db, client):
        """Test health check when database is down."""
        mock_db.return_value = False
        mock_redis.return_value = True
        
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["database_connected"] is False
        assert data["redis_connected"] is True
    
    @patch("src.api.routes.health.get_database_status")
    @patch("src.api.routes.health.get_redis_status")
    def test_health_check_with_redis_failure(self, mock_redis, mock_db, client):
        """Test health check when Redis is down."""
        mock_db.return_value = True
        mock_redis.return_value = False
        
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["database_connected"] is True
        assert data["redis_connected"] is False
    
    @patch("src.api.routes.health.get_database_status")
    def test_health_check_exception_handling(self, mock_db, client):
        """Test health check exception handling."""
        mock_db.side_effect = Exception("Database connection failed")
        
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
    
    def test_detailed_health_check(self, client):
        """Test the detailed health check endpoint."""
        try:
            response = client.get("/api/v1/health/detailed")
            
            if response.status_code == 503:
                # psutil not available, check error message
                data = response.json()
                assert "detail" in data
                return
            
            assert response.status_code == 200
            data = response.json()
            
            # Check required fields
            assert "cpu_usage" in data
            assert "memory_usage" in data
            assert "disk_usage" in data
            assert "active_connections" in data
            assert "queue_size" in data
            assert "worker_status" in data
            assert "recent_performance" in data
            
            # Check data types
            assert isinstance(data["cpu_usage"], (int, float))
            assert isinstance(data["memory_usage"], (int, float))
            assert isinstance(data["disk_usage"], (int, float))
            assert isinstance(data["active_connections"], int)
            assert isinstance(data["queue_size"], int)
            assert isinstance(data["worker_status"], dict)
            assert isinstance(data["recent_performance"], list)
            
        except ImportError:
            # psutil not available in test environment
            pass
    
    def test_readiness_probe(self, client):
        """Test the readiness probe endpoint."""
        response = client.get("/api/v1/health/readiness")
        
        # Should return 200 if ready, 503 if not ready
        assert response.status_code in [200, 503]
        
        data = response.json()
        if response.status_code == 200:
            assert data["status"] == "ready"
        else:
            assert "detail" in data
    
    @patch("src.api.routes.health.get_database_status")
    @patch("src.api.routes.health.get_redis_status")
    def test_readiness_probe_not_ready(self, mock_redis, mock_db, client):
        """Test readiness probe when dependencies are not ready."""
        mock_db.return_value = False
        mock_redis.return_value = False
        
        response = client.get("/api/v1/health/readiness")
        
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
    
    def test_liveness_probe(self, client):
        """Test the liveness probe endpoint."""
        response = client.get("/api/v1/health/liveness")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "alive"
        assert "timestamp" in data
    
    def test_version_info(self, client):
        """Test the version information endpoint."""
        response = client.get("/api/v1/health/version")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "version" in data
        assert "build_date" in data
        assert "git_commit" in data
        assert "python_version" in data
        assert "api_version" in data
        
        # Check values
        assert data["version"] == "1.0.0"
        assert data["api_version"] == "v1"


class TestHealthCheckHelpers:
    """Test cases for health check helper functions."""
    
    @pytest.mark.asyncio
    async def test_get_database_status_success(self):
        """Test database status check success."""
        from src.api.routes.health import get_database_status
        
        # This should return True for the placeholder implementation
        result = await get_database_status()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_get_redis_status_success(self):
        """Test Redis status check success."""
        from src.api.routes.health import get_redis_status
        
        # This should return True for the placeholder implementation
        result = await get_redis_status()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_get_active_jobs_count(self):
        """Test active jobs count retrieval."""
        from src.api.routes.health import get_active_jobs_count
        
        result = await get_active_jobs_count()
        assert isinstance(result, int)
        assert result >= -1  # -1 indicates error, >= 0 indicates count
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self):
        """Test system metrics retrieval."""
        from src.api.routes.health import get_system_metrics
        
        result = await get_system_metrics()
        assert isinstance(result, dict)
        
        # Should contain basic metrics even without psutil
        expected_keys = ["cpu_percent", "memory_percent", "disk_percent", "process_count"]
        for key in expected_keys:
            assert key in result


class TestHealthCheckIntegration:
    """Integration tests for health check endpoints."""
    
    def test_health_check_response_format(self, client):
        """Test that health check responses follow the expected format."""
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # Validate response schema matches HealthResponse model
        required_fields = [
            "status", "timestamp", "version", "uptime_seconds",
            "database_connected", "redis_connected", "active_jobs", "system_metrics"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_health_check_caching(self, client):
        """Test that health checks don't have caching headers."""
        response = client.get("/api/v1/health/")
        
        # Health checks should not be cached
        cache_control = response.headers.get("cache-control", "")
        assert "no-cache" in cache_control.lower() or "no-store" in cache_control.lower() or cache_control == ""
    
    def test_health_check_cors(self, client):
        """Test that health checks support CORS."""
        # OPTIONS request for CORS preflight
        response = client.options("/api/v1/health/")
        
        assert response.status_code in [200, 204]
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
    
    def test_multiple_health_checks(self, client):
        """Test multiple consecutive health checks."""
        responses = []
        
        for _ in range(3):
            response = client.get("/api/v1/health/")
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Uptime should be increasing (or at least not decreasing)
        uptimes = [r.json()["uptime_seconds"] for r in responses]
        for i in range(1, len(uptimes)):
            assert uptimes[i] >= uptimes[i-1]
    
    def test_health_check_under_load(self, client):
        """Test health checks under simulated load."""
        import concurrent.futures
        import threading
        
        def make_request():
            return client.get("/api/v1/health/")
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "status" in data


class TestHealthCheckErrorScenarios:
    """Test cases for health check error scenarios."""
    
    @patch("src.api.routes.health.get_system_metrics")
    def test_system_metrics_failure(self, mock_metrics, client):
        """Test health check when system metrics fail."""
        mock_metrics.side_effect = Exception("System metrics unavailable")
        
        response = client.get("/api/v1/health/")
        
        # Should still return 200 but with degraded status or empty metrics
        assert response.status_code in [200, 503]
    
    @patch("src.api.routes.health.get_active_jobs_count")
    def test_active_jobs_count_failure(self, mock_jobs, client):
        """Test health check when job count fails."""
        mock_jobs.return_value = -1  # Indicates error
        
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["active_jobs"] == -1
    
    def test_health_check_timeout_resilience(self, client):
        """Test that health checks are resilient to timeouts."""
        # This would test timeout scenarios in a real implementation
        # For now, just verify the endpoint responds quickly
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/health/")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 5.0  # Should respond within 5 seconds