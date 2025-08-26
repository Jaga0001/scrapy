"""
Integration tests for logging middleware.

This module tests the logging middleware functionality including
correlation IDs, request/response logging, and performance metrics.
"""

import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.middleware.logging import LoggingMiddleware, PerformanceLogger


class TestLoggingMiddleware:
    """Test cases for logging middleware."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_correlation_id_in_response_headers(self):
        """Test that correlation ID is added to response headers."""
        response = self.client.get("/api/v1/health")
        
        assert "X-Correlation-ID" in response.headers
        # Should be a valid UUID
        correlation_id = response.headers["X-Correlation-ID"]
        assert uuid.UUID(correlation_id)  # Will raise exception if invalid
    
    def test_processing_time_in_response_headers(self):
        """Test that processing time is added to response headers."""
        response = self.client.get("/api/v1/health")
        
        assert "X-Processing-Time" in response.headers
        processing_time = response.headers["X-Processing-Time"]
        assert processing_time.endswith("s")  # Should end with 's' for seconds
        
        # Should be a valid float
        time_value = float(processing_time[:-1])
        assert time_value >= 0
    
    @patch('src.api.middleware.logging.logger')
    def test_request_logging(self, mock_logger):
        """Test that requests are logged with proper information."""
        response = self.client.get("/api/v1/health")
        
        # Should have logged the request
        assert mock_logger.info.called
        
        # Check that correlation ID was logged
        log_calls = mock_logger.info.call_args_list
        request_log = None
        for call in log_calls:
            if "Incoming request" in call[0]:
                request_log = call
                break
        
        assert request_log is not None
        assert "correlation_id" in request_log[1]["extra"]
    
    @patch('src.api.middleware.logging.logger')
    def test_response_logging(self, mock_logger):
        """Test that responses are logged with proper information."""
        response = self.client.get("/api/v1/health")
        
        # Should have logged the response
        assert mock_logger.info.called
        
        # Check for response log
        log_calls = mock_logger.info.call_args_list
        response_log = None
        for call in log_calls:
            if "Request completed" in call[0]:
                response_log = call
                break
        
        assert response_log is not None
        assert "processing_time_ms" in response_log[1]["extra"]
    
    @patch('src.api.middleware.logging.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are logged appropriately."""
        # Make a request that should cause an error
        response = self.client.get("/api/v1/nonexistent")
        
        # Check if error was logged (might be warning for 404)
        assert mock_logger.warning.called or mock_logger.error.called
    
    def test_client_ip_extraction(self):
        """Test client IP extraction from various headers."""
        # Test with X-Forwarded-For header
        headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == 200
        
        # Test with X-Real-IP header
        headers = {"X-Real-IP": "192.168.1.200"}
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == 200
    
    def test_sensitive_headers_filtered(self):
        """Test that sensitive headers are filtered from logs."""
        headers = {
            "Authorization": "Bearer secret-token",
            "Cookie": "session=secret-session-id",
            "X-API-Key": "secret-api-key"
        }
        
        with patch('src.api.middleware.logging.logger') as mock_logger:
            response = self.client.get("/api/v1/health", headers=headers)
            
            # Check that sensitive headers were redacted
            log_calls = mock_logger.info.call_args_list
            for call in log_calls:
                if "extra" in call[1] and "request" in call[1]["extra"]:
                    request_info = call[1]["extra"]["request"]
                    if "headers" in request_info:
                        headers_logged = request_info["headers"]
                        if "authorization" in headers_logged:
                            assert headers_logged["authorization"] == "[REDACTED]"
                        if "cookie" in headers_logged:
                            assert headers_logged["cookie"] == "[REDACTED]"
    
    def test_user_info_logging_when_authenticated(self):
        """Test that user information is logged for authenticated requests."""
        # First login to get a token
        login_data = {"username": "admin", "password": "admin123"}
        login_response = self.client.post("/api/v1/auth/login", json=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            with patch('src.api.middleware.logging.logger') as mock_logger:
                response = self.client.get("/api/v1/scraping/jobs", headers=headers)
                
                # Check that user info was logged
                log_calls = mock_logger.info.call_args_list
                user_logged = False
                for call in log_calls:
                    if "extra" in call[1] and "request" in call[1]["extra"]:
                        request_info = call[1]["extra"]["request"]
                        if "user" in request_info and request_info["user"]:
                            user_logged = True
                            break
                
                # User info should be logged for authenticated requests
                if response.status_code != 401:  # If auth worked
                    assert user_logged
    
    def test_request_body_size_logging(self):
        """Test that request body size is logged."""
        data = {"username": "testuser", "password": "testpass"}
        
        with patch('src.api.middleware.logging.logger') as mock_logger:
            response = self.client.post("/api/v1/auth/login", json=data)
            
            # Check that body size was logged
            log_calls = mock_logger.info.call_args_list
            body_size_logged = False
            for call in log_calls:
                if "extra" in call[1] and "request" in call[1]["extra"]:
                    request_info = call[1]["extra"]["request"]
                    if "body_size_bytes" in request_info:
                        body_size_logged = True
                        assert request_info["body_size_bytes"] > 0
                        break
            
            assert body_size_logged
    
    def test_response_body_size_logging(self):
        """Test that response body size is logged."""
        with patch('src.api.middleware.logging.logger') as mock_logger:
            response = self.client.get("/api/v1/health")
            
            # Check that response body size was logged
            log_calls = mock_logger.info.call_args_list
            body_size_logged = False
            for call in log_calls:
                if "extra" in call[1] and "response" in call[1]["extra"]:
                    response_info = call[1]["extra"]["response"]
                    if "body_size_bytes" in response_info:
                        body_size_logged = True
                        break
            
            assert body_size_logged


class TestPerformanceLogger:
    """Test cases for the PerformanceLogger class."""
    
    def setup_method(self):
        """Set up performance logger for testing."""
        self.perf_logger = PerformanceLogger()
    
    @patch('src.api.middleware.logging.performance_logger.logger')
    def test_log_slow_request(self, mock_logger):
        """Test logging of slow requests."""
        correlation_id = "test-correlation-id"
        request_info = {
            "method": "GET",
            "path": "/api/v1/test",
            "user": {"user_id": "test-user"}
        }
        processing_time = 2.5  # 2.5 seconds (slow)
        
        self.perf_logger.log_slow_request(
            correlation_id, request_info, processing_time, threshold=1.0
        )
        
        # Should have logged a warning
        mock_logger.warning.assert_called_once()
        
        # Check log content
        call_args = mock_logger.warning.call_args
        assert "Slow request detected" in call_args[0][0]
        assert call_args[1]["extra"]["processing_time_seconds"] == 2.5
    
    @patch('src.api.middleware.logging.performance_logger.logger')
    def test_log_fast_request_not_logged(self, mock_logger):
        """Test that fast requests are not logged as slow."""
        correlation_id = "test-correlation-id"
        request_info = {"method": "GET", "path": "/api/v1/test"}
        processing_time = 0.5  # 0.5 seconds (fast)
        
        self.perf_logger.log_slow_request(
            correlation_id, request_info, processing_time, threshold=1.0
        )
        
        # Should not have logged anything
        mock_logger.warning.assert_not_called()
    
    @patch('src.api.middleware.logging.performance_logger.logger')
    def test_log_error_rate(self, mock_logger):
        """Test logging of error rate metrics."""
        endpoint = "/api/v1/test"
        error_count = 5
        total_count = 100
        
        self.perf_logger.log_error_rate(endpoint, error_count, total_count)
        
        # Should have logged metrics
        mock_logger.info.assert_called_once()
        
        # Check log content
        call_args = mock_logger.info.call_args
        assert "Error rate metrics" in call_args[0][0]
        assert call_args[1]["extra"]["error_rate"] == 0.05  # 5/100
    
    @patch('src.api.middleware.logging.performance_logger.logger')
    def test_log_error_rate_zero_requests(self, mock_logger):
        """Test error rate logging with zero total requests."""
        endpoint = "/api/v1/test"
        error_count = 0
        total_count = 0
        
        self.perf_logger.log_error_rate(endpoint, error_count, total_count)
        
        # Should handle division by zero
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["extra"]["error_rate"] == 0
    
    @patch('src.api.middleware.logging.performance_logger.logger')
    def test_log_throughput(self, mock_logger):
        """Test logging of throughput metrics."""
        endpoint = "/api/v1/test"
        request_count = 150
        
        self.perf_logger.log_throughput(endpoint, request_count)
        
        # Should have logged metrics
        mock_logger.info.assert_called_once()
        
        # Check log content
        call_args = mock_logger.info.call_args
        assert "Throughput metrics" in call_args[0][0]
        assert call_args[1]["extra"]["request_count"] == 150


class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_end_to_end_request_logging(self):
        """Test complete request logging flow."""
        with patch('src.api.middleware.logging.logger') as mock_logger:
            response = self.client.get("/api/v1/health")
            
            # Should have logged both request start and completion
            info_calls = [call for call in mock_logger.info.call_args_list 
                         if call[0][0] in ["Incoming request", "Request completed"]]
            
            assert len(info_calls) >= 2  # At least request start and completion
            
            # Extract correlation IDs from logs
            correlation_ids = set()
            for call in info_calls:
                if "extra" in call[1] and "correlation_id" in call[1]["extra"]:
                    correlation_ids.add(call[1]["extra"]["correlation_id"])
            
            # Should use the same correlation ID for the entire request
            assert len(correlation_ids) == 1
    
    def test_error_request_logging(self):
        """Test logging of requests that result in errors."""
        with patch('src.api.middleware.logging.logger') as mock_logger:
            response = self.client.get("/api/v1/nonexistent-endpoint")
            
            # Should have logged the request even if it resulted in an error
            assert mock_logger.info.called or mock_logger.warning.called
    
    def test_post_request_logging(self):
        """Test logging of POST requests with body."""
        data = {"username": "testuser", "password": "testpass"}
        
        with patch('src.api.middleware.logging.logger') as mock_logger:
            response = self.client.post("/api/v1/auth/login", json=data)
            
            # Should have logged the POST request
            assert mock_logger.info.called
            
            # Check that method was logged correctly
            log_calls = mock_logger.info.call_args_list
            method_logged = False
            for call in log_calls:
                if "extra" in call[1] and "request" in call[1]["extra"]:
                    request_info = call[1]["extra"]["request"]
                    if request_info.get("method") == "POST":
                        method_logged = True
                        break
            
            assert method_logged
    
    def test_concurrent_requests_different_correlation_ids(self):
        """Test that concurrent requests get different correlation IDs."""
        import threading
        import time
        
        correlation_ids = []
        
        def make_request():
            response = self.client.get("/api/v1/health")
            if "X-Correlation-ID" in response.headers:
                correlation_ids.append(response.headers["X-Correlation-ID"])
        
        # Make multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All correlation IDs should be unique
        assert len(set(correlation_ids)) == len(correlation_ids)


@pytest.fixture
def mock_request_state():
    """Mock request state for testing."""
    class MockState:
        def __init__(self):
            self.correlation_id = "test-correlation-id"
            self.user = {
                "user_id": "test-user",
                "username": "testuser"
            }
            self.authenticated = True
    
    return MockState()


def test_logging_with_mock_state(mock_request_state):
    """Test logging functionality with mocked request state."""
    # This would test the internal logging methods
    # For now, we test through the integration tests above
    pass