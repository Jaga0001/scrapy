"""
Logging middleware for FastAPI.

This module provides comprehensive request/response logging middleware
with correlation IDs and performance metrics.
"""

import json
import time
import uuid
from typing import Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logging middleware for comprehensive request/response logging.
    
    This middleware logs all HTTP requests and responses with
    correlation IDs, performance metrics, and structured data.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and log request/response information.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response: The HTTP response
        """
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Record start time
        start_time = time.time()
        
        # Extract request information
        request_info = await self._extract_request_info(request)
        
        # Log incoming request
        logger.info(
            "Incoming request",
            extra={
                "correlation_id": correlation_id,
                "request": request_info,
                "event_type": "request_start"
            }
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Extract response information
            response_info = self._extract_response_info(response, processing_time)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
            
            # Log response
            log_level = "info" if response.status_code < 400 else "warning" if response.status_code < 500 else "error"
            
            getattr(logger, log_level)(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "request": request_info,
                    "response": response_info,
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "event_type": "request_complete"
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate processing time for failed requests
            processing_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "request": request_info,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "event_type": "request_error"
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """
        Extract relevant information from the HTTP request.
        
        Args:
            request: The HTTP request
            
        Returns:
            Dict[str, Any]: Request information
        """
        # Get client IP (considering proxy headers)
        client_ip = self._get_client_ip(request)
        
        # Extract user information if available
        user_info = None
        if hasattr(request.state, "user"):
            user_info = {
                "user_id": request.state.user.get("user_id"),
                "username": request.state.user.get("username")
            }
        
        # Extract query parameters
        query_params = dict(request.query_params) if request.query_params else None
        
        # Extract headers (excluding sensitive ones)
        headers = self._filter_headers(dict(request.headers))
        
        # Extract request body size
        content_length = request.headers.get("content-length")
        body_size = int(content_length) if content_length else 0
        
        return {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": query_params,
            "headers": headers,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent"),
            "user": user_info,
            "body_size_bytes": body_size,
            "content_type": request.headers.get("content-type")
        }
    
    def _extract_response_info(self, response: Response, processing_time: float) -> Dict[str, Any]:
        """
        Extract relevant information from the HTTP response.
        
        Args:
            response: The HTTP response
            processing_time: Request processing time in seconds
            
        Returns:
            Dict[str, Any]: Response information
        """
        # Extract response body size
        content_length = response.headers.get("content-length")
        body_size = int(content_length) if content_length else 0
        
        return {
            "status_code": response.status_code,
            "headers": self._filter_headers(dict(response.headers)),
            "body_size_bytes": body_size,
            "content_type": response.headers.get("content-type"),
            "processing_time_seconds": round(processing_time, 3)
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get the client IP address, considering proxy headers.
        
        Args:
            request: The HTTP request
            
        Returns:
            str: Client IP address
        """
        # Check for forwarded headers (in order of preference)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "x-client-ip",
            "cf-connecting-ip"  # Cloudflare
        ]
        
        for header in forwarded_headers:
            if header in request.headers:
                # X-Forwarded-For can contain multiple IPs, take the first one
                ip = request.headers[header].split(",")[0].strip()
                if ip:
                    return ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out sensitive headers from logging.
        
        Args:
            headers: Original headers dictionary
            
        Returns:
            Dict[str, str]: Filtered headers
        """
        # Headers to exclude from logging
        sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "proxy-authorization"
        }
        
        # Headers to truncate (show only first few characters)
        truncate_headers = {
            "user-agent": 100
        }
        
        filtered = {}
        
        for key, value in headers.items():
            key_lower = key.lower()
            
            if key_lower in sensitive_headers:
                filtered[key] = "[REDACTED]"
            elif key_lower in truncate_headers:
                max_length = truncate_headers[key_lower]
                filtered[key] = value[:max_length] + "..." if len(value) > max_length else value
            else:
                filtered[key] = value
        
        return filtered


class PerformanceLogger:
    """
    Performance logging utilities for tracking API metrics.
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.performance")
    
    def log_slow_request(self, correlation_id: str, request_info: Dict[str, Any], 
                        processing_time: float, threshold: float = 1.0):
        """
        Log slow requests that exceed the threshold.
        
        Args:
            correlation_id: Request correlation ID
            request_info: Request information
            processing_time: Processing time in seconds
            threshold: Slow request threshold in seconds
        """
        if processing_time > threshold:
            self.logger.warning(
                "Slow request detected",
                extra={
                    "correlation_id": correlation_id,
                    "request": request_info,
                    "processing_time_seconds": processing_time,
                    "threshold_seconds": threshold,
                    "event_type": "slow_request"
                }
            )
    
    def log_error_rate(self, endpoint: str, error_count: int, total_count: int, 
                      time_window: str = "1m"):
        """
        Log error rate metrics for endpoints.
        
        Args:
            endpoint: API endpoint
            error_count: Number of errors
            total_count: Total number of requests
            time_window: Time window for the metrics
        """
        error_rate = error_count / total_count if total_count > 0 else 0
        
        self.logger.info(
            "Error rate metrics",
            extra={
                "endpoint": endpoint,
                "error_count": error_count,
                "total_count": total_count,
                "error_rate": round(error_rate, 4),
                "time_window": time_window,
                "event_type": "error_rate_metrics"
            }
        )
    
    def log_throughput(self, endpoint: str, request_count: int, 
                      time_window: str = "1m"):
        """
        Log throughput metrics for endpoints.
        
        Args:
            endpoint: API endpoint
            request_count: Number of requests
            time_window: Time window for the metrics
        """
        self.logger.info(
            "Throughput metrics",
            extra={
                "endpoint": endpoint,
                "request_count": request_count,
                "time_window": time_window,
                "event_type": "throughput_metrics"
            }
        )


# Global performance logger instance
performance_logger = PerformanceLogger()