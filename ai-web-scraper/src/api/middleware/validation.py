"""
Request validation middleware for FastAPI.

This module provides comprehensive request validation, sanitization,
and error handling middleware for API security and data integrity.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation and sanitization middleware.
    
    This middleware provides comprehensive input validation, sanitization,
    and security checks for all incoming requests.
    """
    
    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024
    
    # Maximum URL length
    MAX_URL_LENGTH = 2048
    
    # Maximum header value length
    MAX_HEADER_LENGTH = 8192
    
    # Suspicious patterns that might indicate attacks
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # XSS
        r'on\w+\s*=',  # Event handlers
        r'union\s+select',  # SQL injection
        r'drop\s+table',  # SQL injection
        r'insert\s+into',  # SQL injection
        r'delete\s+from',  # SQL injection
        r'\.\./.*\.\.',  # Path traversal
        r'file://',  # File inclusion
        r'php://',  # PHP wrappers
        r'data://',  # Data URLs
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATTERNS]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and apply validation.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response: The HTTP response
        """
        try:
            # Validate request size and structure
            await self._validate_request_structure(request)
            
            # Validate and sanitize headers
            self._validate_headers(request)
            
            # Validate URL and query parameters
            self._validate_url_and_params(request)
            
            # Validate request body if present
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)
            
            # Process the request
            response = await call_next(request)
            
            # Add security headers to response
            self._add_security_headers(response)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request validation error"
            )
    
    async def _validate_request_structure(self, request: Request):
        """
        Validate basic request structure and size limits.
        
        Args:
            request: The HTTP request
        """
        # Check URL length
        if len(str(request.url)) > self.MAX_URL_LENGTH:
            logger.warning(f"Request URL too long: {len(str(request.url))} characters")
            raise HTTPException(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                detail="Request URL too long"
            )
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_BODY_SIZE:
                    logger.warning(f"Request body too large: {size} bytes")
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request body too large"
                    )
            except ValueError:
                logger.warning("Invalid content-length header")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid content-length header"
                )
    
    def _validate_headers(self, request: Request):
        """
        Validate and sanitize request headers.
        
        Args:
            request: The HTTP request
        """
        for name, value in request.headers.items():
            # Check header length
            if len(value) > self.MAX_HEADER_LENGTH:
                logger.warning(f"Header {name} too long: {len(value)} characters")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Header {name} too long"
                )
            
            # Check for suspicious patterns
            if self._contains_suspicious_content(value):
                logger.warning(f"Suspicious content in header {name}: {value[:100]}...")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid header content"
                )
        
        # Validate specific headers
        self._validate_content_type(request)
        self._validate_user_agent(request)
    
    def _validate_content_type(self, request: Request):
        """
        Validate Content-Type header for POST/PUT requests.
        
        Args:
            request: The HTTP request
        """
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            # List of allowed content types
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain"
            ]
            
            # Check if content type is allowed
            if content_type and not any(allowed in content_type.lower() for allowed in allowed_types):
                logger.warning(f"Unsupported content type: {content_type}")
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unsupported content type"
                )
    
    def _validate_user_agent(self, request: Request):
        """
        Validate User-Agent header.
        
        Args:
            request: The HTTP request
        """
        user_agent = request.headers.get("user-agent", "")
        
        # Block empty or suspicious user agents
        if not user_agent.strip():
            logger.warning("Empty user agent")
            # Don't block empty user agents, just log
        
        # Check for suspicious patterns in user agent
        if self._contains_suspicious_content(user_agent):
            logger.warning(f"Suspicious user agent: {user_agent[:100]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user agent"
            )
    
    def _validate_url_and_params(self, request: Request):
        """
        Validate URL path and query parameters.
        
        Args:
            request: The HTTP request
        """
        # Validate URL path
        path = unquote(request.url.path)
        if self._contains_suspicious_content(path):
            logger.warning(f"Suspicious URL path: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL path"
            )
        
        # Validate query parameters
        for key, value in request.query_params.items():
            # Decode URL-encoded parameters
            decoded_key = unquote(key)
            decoded_value = unquote(value)
            
            # Check for suspicious content
            if self._contains_suspicious_content(decoded_key) or self._contains_suspicious_content(decoded_value):
                logger.warning(f"Suspicious query parameter: {key}={value[:50]}...")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid query parameter"
                )
    
    async def _validate_request_body(self, request: Request):
        """
        Validate request body content.
        
        Args:
            request: The HTTP request
        """
        try:
            # Get request body
            body = await request.body()
            
            if not body:
                return
            
            # Check body size
            if len(body) > self.MAX_BODY_SIZE:
                logger.warning(f"Request body too large: {len(body)} bytes")
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Request body too large"
                )
            
            # Validate JSON content if applicable
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type.lower():
                await self._validate_json_body(body)
            
            # Check for suspicious patterns in body
            body_str = body.decode("utf-8", errors="ignore")
            if self._contains_suspicious_content(body_str):
                logger.warning("Suspicious content in request body")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request body content"
                )
                
        except UnicodeDecodeError:
            logger.warning("Invalid UTF-8 encoding in request body")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body encoding"
            )
    
    async def _validate_json_body(self, body: bytes):
        """
        Validate JSON request body.
        
        Args:
            body: Request body bytes
        """
        try:
            # Parse JSON
            json_data = json.loads(body)
            
            # Validate JSON structure
            self._validate_json_structure(json_data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request body: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format"
            )
    
    def _validate_json_structure(self, data: Any, depth: int = 0):
        """
        Recursively validate JSON structure.
        
        Args:
            data: JSON data to validate
            depth: Current recursion depth
        """
        # Prevent deeply nested structures
        if depth > 10:
            logger.warning("JSON structure too deeply nested")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON structure too complex"
            )
        
        if isinstance(data, dict):
            # Limit number of keys
            if len(data) > 100:
                logger.warning(f"Too many keys in JSON object: {len(data)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="JSON object too complex"
                )
            
            # Validate each key-value pair
            for key, value in data.items():
                if isinstance(key, str) and self._contains_suspicious_content(key):
                    logger.warning(f"Suspicious JSON key: {key}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid JSON key"
                    )
                
                self._validate_json_structure(value, depth + 1)
        
        elif isinstance(data, list):
            # Limit array size
            if len(data) > 1000:
                logger.warning(f"JSON array too large: {len(data)} items")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="JSON array too large"
                )
            
            # Validate each item
            for item in data:
                self._validate_json_structure(item, depth + 1)
        
        elif isinstance(data, str):
            # Check string content
            if self._contains_suspicious_content(data):
                logger.warning(f"Suspicious JSON string value: {data[:50]}...")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON string value"
                )
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """
        Check if content contains suspicious patterns.
        
        Args:
            content: Content to check
            
        Returns:
            bool: True if suspicious content is found
        """
        if not content:
            return False
        
        # Check against compiled patterns
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                return True
        
        return False
    
    def _add_security_headers(self, response: Response):
        """
        Add security headers to the response.
        
        Args:
            response: The HTTP response
        """
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        
        # Additional security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"


class InputSanitizer:
    """
    Input sanitization utilities.
    
    This class provides methods for sanitizing various types of input data
    to prevent injection attacks and ensure data integrity.
    """
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input.
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            
        Returns:
            str: Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\t')
        
        return value.strip()
    
    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        Sanitize URL input.
        
        Args:
            url: URL to sanitize
            
        Returns:
            str: Sanitized URL
        """
        if not url:
            return ""
        
        # Basic URL validation
        url = url.strip()
        
        # Ensure it starts with http or https
        if not url.startswith(('http://', 'https://')):
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith(('ftp://', 'file://')):
                url = 'https://' + url
        
        # Remove dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                raise ValueError(f"Dangerous protocol not allowed: {protocol}")
        
        return url
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename input.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            str: Sanitized filename
        """
        if not filename:
            return "unnamed_file"
        
        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\x00']
        
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure it's not empty
        if not filename:
            filename = "unnamed_file"
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 255 - len(ext) - 1 if ext else 255
            filename = name[:max_name_length] + ('.' + ext if ext else '')
        
        return filename


# Global sanitizer instance
sanitizer = InputSanitizer()