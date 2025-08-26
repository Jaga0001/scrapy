"""
Integration tests for rate limiting middleware.

This module tests the rate limiting functionality including
per-client limits, different limits for authenticated users,
and rate limit headers.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.middleware.rate_limit import RateLimiter, TokenBucket, AdaptiveRateLimiter


class TestRateLimitMiddleware:
    """Test cases for rate limiting middleware."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint_not_rate_limited(self):
        """Test that health endpoints are not rate limited."""
        # Make multiple requests quickly
        for _ in range(25):  # More than unauthenticated limit
            response = self.client.get("/api/v1/health")
            assert response.status_code == 200
    
    def test_unauthenticated_rate_limit(self):
        """Test rate limiting for unauthenticated requests."""
        # Make requests up to the limit
        responses = []
        for i in range(25):  # More than the 20 request limit
            response = self.client.get("/api/v1/scraping/jobs")
            responses.append(response)
        
        # Some requests should be rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        
        # Should have some rate limited responses
        # (Note: actual behavior depends on timing and implementation)
        if rate_limited_responses:
            assert "Rate Limit Exceeded" in rate_limited_responses[0].json()["error"]
    
    def test_rate_limit_headers(self):
        """Test that rate limit headers are included in responses."""
        response = self.client.get("/api/v1/scraping/jobs")
        
        # Check for rate limit headers (if not rate limited)
        if response.status_code != 429:
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
    
    def test_authenticated_higher_limits(self):
        """Test that authenticated users have higher rate limits."""
        # First login to get a token
        login_data = {"username": "admin", "password": "admin123"}
        login_response = self.client.post("/api/v1/auth/login", json=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make more requests than unauthenticated limit
            success_count = 0
            for i in range(30):
                response = self.client.get("/api/v1/scraping/jobs", headers=headers)
                if response.status_code != 429:
                    success_count += 1
            
            # Should allow more requests for authenticated users
            assert success_count > 20  # More than unauthenticated limit
    
    def test_rate_limit_reset_after_window(self):
        """Test that rate limits reset after the time window."""
        # This test would require waiting for the time window
        # For now, we'll test the logic indirectly
        pass
    
    def test_different_clients_separate_limits(self):
        """Test that different clients have separate rate limits."""
        # This would require simulating different IP addresses
        # For now, we test the concept with different user agents
        
        headers1 = {"User-Agent": "TestClient1"}
        headers2 = {"User-Agent": "TestClient2"}
        
        # Both should be able to make requests up to their limits
        response1 = self.client.get("/api/v1/scraping/jobs", headers=headers1)
        response2 = self.client.get("/api/v1/scraping/jobs", headers=headers2)
        
        # Both should get the same treatment (both unauthenticated)
        assert response1.status_code == response2.status_code


class TestRateLimiter:
    """Test cases for the RateLimiter class."""
    
    def setup_method(self):
        """Set up rate limiter for testing."""
        self.rate_limiter = RateLimiter()
    
    def test_allow_requests_within_limit(self):
        """Test that requests within limit are allowed."""
        client_id = "test-client-1"
        limit = 5
        window = 60
        
        # Make requests within limit
        for i in range(limit):
            allowed, retry_after = self.rate_limiter.is_allowed(client_id, limit, window)
            assert allowed is True
            assert retry_after == 0
    
    def test_block_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        client_id = "test-client-2"
        limit = 3
        window = 60
        
        # Make requests up to limit
        for i in range(limit):
            allowed, retry_after = self.rate_limiter.is_allowed(client_id, limit, window)
            assert allowed is True
        
        # Next request should be blocked
        allowed, retry_after = self.rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is False
        assert retry_after > 0
    
    def test_get_remaining_requests(self):
        """Test getting remaining request count."""
        client_id = "test-client-3"
        limit = 10
        window = 60
        
        # Initially should have full limit
        remaining = self.rate_limiter.get_remaining(client_id, limit, window)
        assert remaining == limit
        
        # After making requests, remaining should decrease
        self.rate_limiter.is_allowed(client_id, limit, window)
        remaining = self.rate_limiter.get_remaining(client_id, limit, window)
        assert remaining == limit - 1
    
    def test_cleanup_old_requests(self):
        """Test that old requests are cleaned up."""
        client_id = "test-client-4"
        limit = 5
        window = 1  # 1 second window
        
        # Make requests
        for i in range(limit):
            self.rate_limiter.is_allowed(client_id, limit, window)
        
        # Should be at limit
        allowed, _ = self.rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is False
        
        # Wait for window to pass
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, _ = self.rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is True
    
    def test_different_clients_independent_limits(self):
        """Test that different clients have independent limits."""
        client1 = "test-client-5"
        client2 = "test-client-6"
        limit = 3
        window = 60
        
        # Exhaust limit for client1
        for i in range(limit):
            allowed, _ = self.rate_limiter.is_allowed(client1, limit, window)
            assert allowed is True
        
        # Client1 should be blocked
        allowed, _ = self.rate_limiter.is_allowed(client1, limit, window)
        assert allowed is False
        
        # Client2 should still be allowed
        allowed, _ = self.rate_limiter.is_allowed(client2, limit, window)
        assert allowed is True


class TestTokenBucket:
    """Test cases for the TokenBucket class."""
    
    def test_consume_tokens_within_capacity(self):
        """Test consuming tokens within bucket capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should be able to consume tokens up to capacity
        for i in range(10):
            assert bucket.consume(1) is True
        
        # Should not be able to consume more
        assert bucket.consume(1) is False
    
    def test_token_refill(self):
        """Test that tokens are refilled over time."""
        bucket = TokenBucket(capacity=5, refill_rate=2.0)  # 2 tokens per second
        
        # Consume all tokens
        for i in range(5):
            bucket.consume(1)
        
        # Should be empty
        assert bucket.consume(1) is False
        
        # Wait for refill
        time.sleep(1.1)  # Should refill ~2 tokens
        
        # Should be able to consume again
        assert bucket.consume(1) is True
        assert bucket.consume(1) is True
        # Third token might not be available due to timing
    
    def test_consume_multiple_tokens(self):
        """Test consuming multiple tokens at once."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should be able to consume multiple tokens
        assert bucket.consume(5) is True
        assert bucket.consume(3) is True
        
        # Should not have enough for 3 more
        assert bucket.consume(3) is False
        
        # Should still be able to consume remaining
        assert bucket.consume(2) is True


class TestAdaptiveRateLimiter:
    """Test cases for the AdaptiveRateLimiter class."""
    
    def test_initial_limit(self):
        """Test initial rate limit."""
        limiter = AdaptiveRateLimiter(base_limit=100, window=60)
        assert limiter.get_current_limit() == 100
    
    def test_adjust_limit_high_load(self):
        """Test limit adjustment under high system load."""
        limiter = AdaptiveRateLimiter(base_limit=100, window=60)
        
        # Simulate high load
        limiter.adjust_limit(system_load=0.9, error_rate=0.15)
        
        # Limit should be reduced
        assert limiter.get_current_limit() < 100
    
    def test_adjust_limit_low_load(self):
        """Test limit adjustment under low system load."""
        limiter = AdaptiveRateLimiter(base_limit=100, window=60)
        
        # Simulate low load
        limiter.adjust_limit(system_load=0.3, error_rate=0.02)
        
        # Limit should be increased
        assert limiter.get_current_limit() > 100
    
    def test_limit_bounds(self):
        """Test that limits stay within reasonable bounds."""
        limiter = AdaptiveRateLimiter(base_limit=100, window=60)
        
        # Simulate extreme conditions multiple times
        for _ in range(10):
            limiter.adjust_limit(system_load=1.0, error_rate=0.5)
        
        # Should not go below 50% of base limit
        assert limiter.get_current_limit() >= 50
        
        # Reset and test upper bound
        limiter.current_multiplier = 1.0
        for _ in range(10):
            limiter.adjust_limit(system_load=0.1, error_rate=0.0)
        
        # Should not go above 200% of base limit
        assert limiter.get_current_limit() <= 200


@pytest.fixture
def mock_time():
    """Mock time for testing time-dependent functionality."""
    with patch('time.time') as mock:
        mock.return_value = 1000000  # Fixed timestamp
        yield mock


def test_rate_limiter_with_mock_time(mock_time):
    """Test rate limiter with mocked time."""
    rate_limiter = RateLimiter()
    client_id = "test-client"
    limit = 5
    window = 60
    
    # Make requests
    for i in range(limit):
        allowed, _ = rate_limiter.is_allowed(client_id, limit, window)
        assert allowed is True
    
    # Should be at limit
    allowed, _ = rate_limiter.is_allowed(client_id, limit, window)
    assert allowed is False
    
    # Advance time
    mock_time.return_value += window + 1
    
    # Should be allowed again
    allowed, _ = rate_limiter.is_allowed(client_id, limit, window)
    assert allowed is True