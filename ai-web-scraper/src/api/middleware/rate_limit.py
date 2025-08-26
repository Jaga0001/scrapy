"""
Rate limiting middleware for FastAPI.

This module provides rate limiting functionality to prevent API abuse
and ensure fair usage across different users and endpoints.
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.
    
    This middleware implements rate limiting per IP address and per user
    with different limits for authenticated and unauthenticated requests.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and apply rate limiting.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response: The HTTP response
        """
        # Skip rate limiting for health checks
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)
        
        try:
            # Get client identifier
            client_id = self._get_client_identifier(request)
            
            # Get rate limit configuration
            limit_config = self._get_rate_limit_config(request)
            
            # Check rate limit
            allowed, retry_after = self.rate_limiter.is_allowed(
                client_id, 
                limit_config["requests"], 
                limit_config["window"]
            )
            
            if not allowed:
                # Log rate limit violation
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_id": client_id,
                        "endpoint": request.url.path,
                        "limit": limit_config["requests"],
                        "window": limit_config["window"],
                        "retry_after": retry_after,
                        "event_type": "rate_limit_exceeded"
                    }
                )
                
                # Return rate limit error
                return self._create_rate_limit_response(retry_after)
            
            # Process the request
            response = await call_next(request)
            
            # Add rate limit headers
            remaining = self.rate_limiter.get_remaining(
                client_id, 
                limit_config["requests"], 
                limit_config["window"]
            )
            
            response.headers["X-RateLimit-Limit"] = str(limit_config["requests"])
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + limit_config["window"]))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Continue processing if rate limiting fails
            return await call_next(request)
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client.
        
        Args:
            request: The HTTP request
            
        Returns:
            str: Client identifier
        """
        # Use user ID if authenticated
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user['user_id']}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _get_rate_limit_config(self, request: Request) -> Dict[str, int]:
        """
        Get rate limit configuration based on request context.
        
        Args:
            request: The HTTP request
            
        Returns:
            Dict[str, int]: Rate limit configuration
        """
        # Check if user is authenticated
        is_authenticated = hasattr(request.state, "authenticated") and request.state.authenticated
        
        # Different limits for different endpoints and user types
        if is_authenticated:
            # Higher limits for authenticated users
            if request.url.path.startswith("/api/v1/scraping/jobs"):
                return {"requests": 100, "window": 60}  # 100 requests per minute
            elif request.url.path.startswith("/api/v1/data"):
                return {"requests": 200, "window": 60}  # 200 requests per minute
            else:
                return {"requests": 150, "window": 60}  # Default for authenticated
        else:
            # Lower limits for unauthenticated users
            return {"requests": 20, "window": 60}  # 20 requests per minute
    
    def _create_rate_limit_response(self, retry_after: int) -> Response:
        """
        Create a rate limit exceeded response.
        
        Args:
            retry_after: Seconds to wait before retrying
            
        Returns:
            Response: HTTP 429 response
        """
        return Response(
            content='{"error": "Rate Limit Exceeded", "message": "Too many requests", "retry_after": ' + str(retry_after) + '}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={
                "Content-Type": "application/json",
                "Retry-After": str(retry_after)
            }
        )


class RateLimiter:
    """
    Token bucket rate limiter implementation.
    
    This class implements a token bucket algorithm for rate limiting
    with per-client tracking and configurable limits.
    """
    
    def __init__(self):
        # Store token buckets per client
        self.buckets: Dict[str, TokenBucket] = {}
        # Track request timestamps for sliding window
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque())
    
    def is_allowed(self, client_id: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        Check if a request is allowed for the given client.
        
        Args:
            client_id: Unique client identifier
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple[bool, int]: (allowed, retry_after_seconds)
        """
        current_time = time.time()
        
        # Clean up old requests
        self._cleanup_old_requests(client_id, current_time, window)
        
        # Get request history for this client
        history = self.request_history[client_id]
        
        # Check if limit is exceeded
        if len(history) >= limit:
            # Calculate retry after time
            oldest_request = history[0]
            retry_after = int(oldest_request + window - current_time) + 1
            return False, max(retry_after, 1)
        
        # Add current request to history
        history.append(current_time)
        
        return True, 0
    
    def get_remaining(self, client_id: str, limit: int, window: int) -> int:
        """
        Get the number of remaining requests for a client.
        
        Args:
            client_id: Unique client identifier
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            int: Number of remaining requests
        """
        current_time = time.time()
        
        # Clean up old requests
        self._cleanup_old_requests(client_id, current_time, window)
        
        # Get current request count
        current_count = len(self.request_history[client_id])
        
        return max(0, limit - current_count)
    
    def _cleanup_old_requests(self, client_id: str, current_time: float, window: int):
        """
        Remove old requests outside the time window.
        
        Args:
            client_id: Unique client identifier
            current_time: Current timestamp
            window: Time window in seconds
        """
        history = self.request_history[client_id]
        cutoff_time = current_time - window
        
        # Remove old requests
        while history and history[0] < cutoff_time:
            history.popleft()


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    
    This class implements a token bucket that refills at a constant rate
    and allows burst requests up to the bucket capacity.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed, False otherwise
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def _refill(self):
        """Refill the bucket based on elapsed time."""
        current_time = time.time()
        elapsed = current_time - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        
        self.last_refill = current_time


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts limits based on system load.
    
    This class implements an adaptive rate limiting strategy that
    can increase or decrease limits based on system performance.
    """
    
    def __init__(self, base_limit: int, window: int):
        """
        Initialize adaptive rate limiter.
        
        Args:
            base_limit: Base rate limit
            window: Time window in seconds
        """
        self.base_limit = base_limit
        self.window = window
        self.current_multiplier = 1.0
        self.last_adjustment = time.time()
    
    def get_current_limit(self) -> int:
        """
        Get the current rate limit based on system conditions.
        
        Returns:
            int: Current rate limit
        """
        return int(self.base_limit * self.current_multiplier)
    
    def adjust_limit(self, system_load: float, error_rate: float):
        """
        Adjust the rate limit based on system metrics.
        
        Args:
            system_load: Current system load (0.0 to 1.0)
            error_rate: Current error rate (0.0 to 1.0)
        """
        current_time = time.time()
        
        # Only adjust every 30 seconds
        if current_time - self.last_adjustment < 30:
            return
        
        # Decrease limit if system is under stress
        if system_load > 0.8 or error_rate > 0.1:
            self.current_multiplier = max(0.5, self.current_multiplier * 0.9)
        # Increase limit if system is performing well
        elif system_load < 0.5 and error_rate < 0.05:
            self.current_multiplier = min(2.0, self.current_multiplier * 1.1)
        
        self.last_adjustment = current_time
        
        logger.info(
            "Rate limit adjusted",
            extra={
                "base_limit": self.base_limit,
                "current_multiplier": self.current_multiplier,
                "current_limit": self.get_current_limit(),
                "system_load": system_load,
                "error_rate": error_rate,
                "event_type": "rate_limit_adjustment"
            }
        )