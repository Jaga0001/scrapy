"""
Enhanced input validation and sanitization utilities.

This module provides comprehensive input validation and sanitization
for all user inputs to prevent injection attacks and ensure data integrity.
"""

import html
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ValidationError, field_validator
import bleach

from src.utils.logger import get_logger
from src.utils.audit_logger import audit_logger, AuditEventType, AuditSeverity

logger = get_logger(__name__)


class ValidationResult(BaseModel):
    """Result of input validation."""
    
    is_valid: bool
    sanitized_value: Any
    errors: List[str] = []
    warnings: List[str] = []
    original_value: Any = None


class SecurityValidator:
    """
    Comprehensive security validator for all user inputs.
    
    This class provides validation and sanitization methods for various
    types of user input to prevent security vulnerabilities.
    """
    
    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        # SQL Injection patterns
        r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)',
        r'(--|#|/\*|\*/)',
        r'(\bor\b\s+\d+\s*=\s*\d+)',
        r'(\band\b\s+\d+\s*=\s*\d+)',
        
        # XSS patterns
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        
        # Command injection patterns
        r'[;&|`$(){}[\]\\]',
        r'\b(cat|ls|dir|type|copy|move|del|rm|chmod|chown|sudo|su)\b',
        
        # Path traversal patterns
        r'\.\./.*\.\.',
        r'\.\.[\\/]',
        r'[\\/]\.\.[\\/]',
        
        # LDAP injection patterns
        r'[()&|!]',
        r'\*.*\*',
        
        # XML injection patterns
        r'<!DOCTYPE',
        r'<!ENTITY',
        r'<!\[CDATA\[',
        
        # NoSQL injection patterns
        r'\$where',
        r'\$ne',
        r'\$gt',
        r'\$lt',
        r'\$regex',
    ]
    
    # Allowed HTML tags for content that may contain HTML
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'i', 'b',
        'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'code', 'pre'
    ]
    
    # Allowed HTML attributes
    ALLOWED_HTML_ATTRIBUTES = {
        '*': ['class', 'id'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title', 'width', 'height']
    }
    
    def __init__(self):
        """Initialize security validator."""
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.DANGEROUS_PATTERNS
        ]
    
    def validate_string(
        self,
        value: Any,
        max_length: int = 1000,
        min_length: int = 0,
        allow_html: bool = False,
        allow_special_chars: bool = True,
        required: bool = False,
        field_name: str = "input"
    ) -> ValidationResult:
        """
        Validate and sanitize string input.
        
        Args:
            value: Input value to validate
            max_length: Maximum allowed length
            min_length: Minimum required length
            allow_html: Whether to allow HTML content
            allow_special_chars: Whether to allow special characters
            required: Whether the field is required
            field_name: Name of the field for logging
            
        Returns:
            ValidationResult: Validation result with sanitized value
        """
        errors = []
        warnings = []
        original_value = value
        
        # Convert to string if not already
        if value is None:
            if required:
                errors.append(f"{field_name} is required")
                return ValidationResult(
                    is_valid=False,
                    sanitized_value=None,
                    errors=errors,
                    original_value=original_value
                )
            value = ""
        else:
            value = str(value)
        
        # Check length constraints
        if len(value) > max_length:
            errors.append(f"{field_name} exceeds maximum length of {max_length} characters")
            value = value[:max_length]
            warnings.append(f"{field_name} was truncated to {max_length} characters")
        
        if len(value) < min_length:
            errors.append(f"{field_name} must be at least {min_length} characters long")
        
        # Check for dangerous patterns
        dangerous_found = self._check_dangerous_patterns(value)
        if dangerous_found:
            errors.append(f"{field_name} contains potentially dangerous content")
            # Log security alert
            audit_logger.log_security_alert(
                alert_type="dangerous_input",
                description=f"Dangerous pattern detected in {field_name}: {dangerous_found[:100]}",
                severity=AuditSeverity.HIGH,
                metadata={"field_name": field_name, "pattern": dangerous_found}
            )
        
        # Sanitize based on options
        if allow_html:
            # Clean HTML but allow safe tags
            value = bleach.clean(
                value,
                tags=self.ALLOWED_HTML_TAGS,
                attributes=self.ALLOWED_HTML_ATTRIBUTES,
                strip=True
            )
        else:
            # Escape HTML entities
            value = html.escape(value)
        
        # Remove or escape special characters if not allowed
        if not allow_special_chars:
            # Keep only alphanumeric, spaces, and basic punctuation
            value = re.sub(r'[^\w\s\-_.,!?]', '', value)
        
        # Remove null bytes and control characters
        value = value.replace('\x00', '')
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\t\r')
        
        # Normalize whitespace
        value = ' '.join(value.split())
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=value,
            errors=errors,
            warnings=warnings,
            original_value=original_value
        )
    
    def validate_url(
        self,
        value: Any,
        allowed_schemes: List[str] = None,
        required: bool = False,
        field_name: str = "url"
    ) -> ValidationResult:
        """
        Validate and sanitize URL input.
        
        Args:
            value: URL value to validate
            allowed_schemes: List of allowed URL schemes
            required: Whether the field is required
            field_name: Name of the field for logging
            
        Returns:
            ValidationResult: Validation result with sanitized URL
        """
        errors = []
        warnings = []
        original_value = value
        
        if value is None:
            if required:
                errors.append(f"{field_name} is required")
            return ValidationResult(
                is_valid=not required,
                sanitized_value=None,
                errors=errors,
                original_value=original_value
            )
        
        value = str(value).strip()
        
        if not value:
            if required:
                errors.append(f"{field_name} cannot be empty")
            return ValidationResult(
                is_valid=not required,
                sanitized_value="",
                errors=errors,
                original_value=original_value
            )
        
        # Set default allowed schemes
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        try:
            # Parse URL
            parsed = urllib.parse.urlparse(value)
            
            # Validate scheme
            if parsed.scheme.lower() not in [s.lower() for s in allowed_schemes]:
                errors.append(f"{field_name} must use one of these schemes: {', '.join(allowed_schemes)}")
            
            # Check for dangerous schemes
            dangerous_schemes = ['javascript', 'data', 'vbscript', 'file', 'ftp']
            if parsed.scheme.lower() in dangerous_schemes:
                errors.append(f"{field_name} uses dangerous scheme: {parsed.scheme}")
                audit_logger.log_security_alert(
                    alert_type="dangerous_url_scheme",
                    description=f"Dangerous URL scheme detected: {parsed.scheme}",
                    severity=AuditSeverity.HIGH,
                    metadata={"field_name": field_name, "url": value[:100]}
                )
            
            # Validate hostname
            if not parsed.netloc:
                errors.append(f"{field_name} must include a valid hostname")
            
            # Check for suspicious patterns in URL
            dangerous_found = self._check_dangerous_patterns(value)
            if dangerous_found:
                errors.append(f"{field_name} contains potentially dangerous content")
                warnings.append("URL contains suspicious patterns")
            
            # Reconstruct clean URL
            if not errors:
                # URL encode components properly
                clean_path = urllib.parse.quote(parsed.path, safe='/')
                clean_query = urllib.parse.quote(parsed.query, safe='&=')
                clean_fragment = urllib.parse.quote(parsed.fragment, safe='')
                
                value = urllib.parse.urlunparse((
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    clean_path,
                    parsed.params,
                    clean_query,
                    clean_fragment
                ))
            
        except Exception as e:
            errors.append(f"{field_name} is not a valid URL: {str(e)}")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=value if is_valid else None,
            errors=errors,
            warnings=warnings,
            original_value=original_value
        )
    
    def validate_email(
        self,
        value: Any,
        required: bool = False,
        field_name: str = "email"
    ) -> ValidationResult:
        """
        Validate and sanitize email input.
        
        Args:
            value: Email value to validate
            required: Whether the field is required
            field_name: Name of the field for logging
            
        Returns:
            ValidationResult: Validation result with sanitized email
        """
        errors = []
        warnings = []
        original_value = value
        
        if value is None:
            if required:
                errors.append(f"{field_name} is required")
            return ValidationResult(
                is_valid=not required,
                sanitized_value=None,
                errors=errors,
                original_value=original_value
            )
        
        value = str(value).strip().lower()
        
        if not value:
            if required:
                errors.append(f"{field_name} cannot be empty")
            return ValidationResult(
                is_valid=not required,
                sanitized_value="",
                errors=errors,
                original_value=original_value
            )
        
        # Basic email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, value):
            errors.append(f"{field_name} is not a valid email address")
        
        # Check for dangerous patterns
        dangerous_found = self._check_dangerous_patterns(value)
        if dangerous_found:
            errors.append(f"{field_name} contains potentially dangerous content")
            audit_logger.log_security_alert(
                alert_type="dangerous_email",
                description=f"Dangerous pattern in email: {dangerous_found[:50]}",
                severity=AuditSeverity.MEDIUM,
                metadata={"field_name": field_name, "email": value[:50]}
            )
        
        # Additional email security checks
        if len(value) > 254:  # RFC 5321 limit
            errors.append(f"{field_name} exceeds maximum email length")
        
        # Check for suspicious TLDs or domains
        suspicious_domains = ['.tk', '.ml', '.ga', '.cf', 'tempmail', 'guerrillamail']
        if any(domain in value for domain in suspicious_domains):
            warnings.append(f"{field_name} uses a suspicious domain")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=value if is_valid else None,
            errors=errors,
            warnings=warnings,
            original_value=original_value
        )
    
    def validate_filename(
        self,
        value: Any,
        max_length: int = 255,
        required: bool = False,
        field_name: str = "filename"
    ) -> ValidationResult:
        """
        Validate and sanitize filename input.
        
        Args:
            value: Filename value to validate
            max_length: Maximum filename length
            required: Whether the field is required
            field_name: Name of the field for logging
            
        Returns:
            ValidationResult: Validation result with sanitized filename
        """
        errors = []
        warnings = []
        original_value = value
        
        if value is None:
            if required:
                errors.append(f"{field_name} is required")
            return ValidationResult(
                is_valid=not required,
                sanitized_value=None,
                errors=errors,
                original_value=original_value
            )
        
        value = str(value).strip()
        
        if not value:
            if required:
                errors.append(f"{field_name} cannot be empty")
            return ValidationResult(
                is_valid=not required,
                sanitized_value="",
                errors=errors,
                original_value=original_value
            )
        
        # Remove dangerous characters
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x00']
        for char in dangerous_chars:
            if char in value:
                value = value.replace(char, '_')
                warnings.append(f"Replaced dangerous character '{char}' with '_'")
        
        # Remove path traversal attempts
        if '..' in value:
            value = value.replace('..', '_')
            warnings.append("Removed path traversal attempt")
        
        # Remove leading/trailing dots and spaces
        value = value.strip('. ')
        
        # Ensure filename is not empty after cleaning
        if not value:
            value = "unnamed_file"
            warnings.append("Generated default filename")
        
        # Check length
        if len(value) > max_length:
            # Try to preserve extension
            if '.' in value:
                name, ext = value.rsplit('.', 1)
                max_name_length = max_length - len(ext) - 1
                value = name[:max_name_length] + '.' + ext
            else:
                value = value[:max_length]
            warnings.append(f"Truncated filename to {max_length} characters")
        
        # Check for reserved names (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = value.split('.')[0].upper()
        if name_without_ext in reserved_names:
            value = f"file_{value}"
            warnings.append("Added prefix to avoid reserved filename")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=value,
            errors=errors,
            warnings=warnings,
            original_value=original_value
        )
    
    def validate_json(
        self,
        value: Any,
        max_depth: int = 10,
        max_keys: int = 100,
        required: bool = False,
        field_name: str = "json_data"
    ) -> ValidationResult:
        """
        Validate and sanitize JSON input.
        
        Args:
            value: JSON value to validate
            max_depth: Maximum nesting depth
            max_keys: Maximum number of keys per object
            required: Whether the field is required
            field_name: Name of the field for logging
            
        Returns:
            ValidationResult: Validation result with sanitized JSON
        """
        errors = []
        warnings = []
        original_value = value
        
        if value is None:
            if required:
                errors.append(f"{field_name} is required")
            return ValidationResult(
                is_valid=not required,
                sanitized_value=None,
                errors=errors,
                original_value=original_value
            )
        
        try:
            # If it's already a dict/list, convert to JSON string first
            if isinstance(value, (dict, list)):
                import json
                json_str = json.dumps(value)
            else:
                json_str = str(value)
            
            # Parse JSON
            import json
            parsed_json = json.loads(json_str)
            
            # Validate structure
            self._validate_json_structure(parsed_json, max_depth, max_keys, 0)
            
            # Sanitize string values in JSON
            sanitized_json = self._sanitize_json_values(parsed_json)
            
            return ValidationResult(
                is_valid=True,
                sanitized_value=sanitized_json,
                errors=errors,
                warnings=warnings,
                original_value=original_value
            )
            
        except json.JSONDecodeError as e:
            errors.append(f"{field_name} is not valid JSON: {str(e)}")
        except ValueError as e:
            errors.append(f"{field_name} validation failed: {str(e)}")
        except Exception as e:
            errors.append(f"{field_name} processing error: {str(e)}")
        
        return ValidationResult(
            is_valid=False,
            sanitized_value=None,
            errors=errors,
            warnings=warnings,
            original_value=original_value
        )
    
    def validate_uuid(
        self,
        value: Any,
        required: bool = False,
        field_name: str = "uuid"
    ) -> ValidationResult:
        """
        Validate UUID input.
        
        Args:
            value: UUID value to validate
            required: Whether the field is required
            field_name: Name of the field for logging
            
        Returns:
            ValidationResult: Validation result with validated UUID
        """
        errors = []
        warnings = []
        original_value = value
        
        if value is None:
            if required:
                errors.append(f"{field_name} is required")
            return ValidationResult(
                is_valid=not required,
                sanitized_value=None,
                errors=errors,
                original_value=original_value
            )
        
        try:
            # Convert to string and validate UUID format
            uuid_str = str(value).strip()
            uuid_obj = UUID(uuid_str)
            
            # Return canonical string representation
            return ValidationResult(
                is_valid=True,
                sanitized_value=str(uuid_obj),
                errors=errors,
                warnings=warnings,
                original_value=original_value
            )
            
        except ValueError:
            errors.append(f"{field_name} is not a valid UUID")
        
        return ValidationResult(
            is_valid=False,
            sanitized_value=None,
            errors=errors,
            warnings=warnings,
            original_value=original_value
        )
    
    def _check_dangerous_patterns(self, value: str) -> Optional[str]:
        """
        Check if value contains dangerous patterns.
        
        Args:
            value: Value to check
            
        Returns:
            Optional[str]: First dangerous pattern found, or None
        """
        for pattern in self.compiled_patterns:
            match = pattern.search(value)
            if match:
                return match.group(0)
        return None
    
    def _validate_json_structure(
        self,
        data: Any,
        max_depth: int,
        max_keys: int,
        current_depth: int
    ) -> None:
        """
        Recursively validate JSON structure.
        
        Args:
            data: JSON data to validate
            max_depth: Maximum allowed depth
            max_keys: Maximum keys per object
            current_depth: Current recursion depth
        """
        if current_depth > max_depth:
            raise ValueError(f"JSON structure exceeds maximum depth of {max_depth}")
        
        if isinstance(data, dict):
            if len(data) > max_keys:
                raise ValueError(f"JSON object has too many keys (max: {max_keys})")
            
            for key, value in data.items():
                # Validate key
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be strings")
                
                if self._check_dangerous_patterns(key):
                    raise ValueError(f"Dangerous pattern in JSON key: {key}")
                
                # Recursively validate value
                self._validate_json_structure(value, max_depth, max_keys, current_depth + 1)
        
        elif isinstance(data, list):
            if len(data) > 1000:  # Reasonable limit for arrays
                raise ValueError("JSON array is too large")
            
            for item in data:
                self._validate_json_structure(item, max_depth, max_keys, current_depth + 1)
        
        elif isinstance(data, str):
            if self._check_dangerous_patterns(data):
                raise ValueError(f"Dangerous pattern in JSON string: {data[:50]}")
    
    def _sanitize_json_values(self, data: Any) -> Any:
        """
        Recursively sanitize string values in JSON data.
        
        Args:
            data: JSON data to sanitize
            
        Returns:
            Any: Sanitized JSON data
        """
        if isinstance(data, dict):
            return {
                key: self._sanitize_json_values(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_json_values(item) for item in data]
        elif isinstance(data, str):
            # Basic sanitization for string values
            sanitized = html.escape(data)
            sanitized = sanitized.replace('\x00', '')  # Remove null bytes
            return sanitized
        else:
            return data


# Global validator instance
security_validator = SecurityValidator()