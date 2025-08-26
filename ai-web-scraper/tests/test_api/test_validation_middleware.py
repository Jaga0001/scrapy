"""
Integration tests for validation middleware.

This module tests the request validation and sanitization middleware
including input validation, security checks, and error handling.
"""

import pytest
import json
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.middleware.validation import InputSanitizer


class TestValidationMiddleware:
    """Test cases for validation middleware."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_normal_request_passes_validation(self):
        """Test that normal requests pass validation."""
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200
    
    def test_security_headers_added(self):
        """Test that security headers are added to responses."""
        response = self.client.get("/api/v1/health")
        
        # Check for security headers
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    def test_valid_json_request(self):
        """Test that valid JSON requests are accepted."""
        valid_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = self.client.post("/api/v1/auth/login", json=valid_data)
        # Should not be blocked by validation (might fail auth, but that's different)
        assert response.status_code != 400
    
    def test_large_request_body_rejected(self):
        """Test that overly large request bodies are rejected."""
        # Create a large payload (over 10MB)
        large_data = {"data": "x" * (11 * 1024 * 1024)}  # 11MB of data
        
        response = self.client.post(
            "/api/v1/auth/login", 
            data=json.dumps(large_data),
            headers={"Content-Type": "application/json"}
        )
        
        # Should be rejected due to size
        assert response.status_code == 413
    
    def test_suspicious_query_parameters(self):
        """Test that suspicious query parameters are blocked."""
        # Test XSS attempt in query parameter
        response = self.client.get("/api/v1/health?search=<script>alert('xss')</script>")
        assert response.status_code == 400
        assert "Invalid query parameter" in response.json()["detail"]
    
    def test_suspicious_url_path(self):
        """Test that suspicious URL paths are blocked."""
        # Test path traversal attempt
        response = self.client.get("/api/v1/../../../etc/passwd")
        assert response.status_code == 400
        assert "Invalid URL path" in response.json()["detail"]
    
    def test_suspicious_headers(self):
        """Test that suspicious headers are blocked."""
        headers = {
            "X-Custom-Header": "<script>alert('xss')</script>",
            "User-Agent": "Mozilla/5.0"
        }
        
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == 400
        assert "Invalid header content" in response.json()["detail"]
    
    def test_invalid_content_type(self):
        """Test that invalid content types are rejected."""
        headers = {"Content-Type": "application/xml"}
        data = "<xml>test</xml>"
        
        response = self.client.post("/api/v1/auth/login", data=data, headers=headers)
        assert response.status_code == 415
        assert "Unsupported content type" in response.json()["detail"]
    
    def test_malformed_json(self):
        """Test that malformed JSON is rejected."""
        headers = {"Content-Type": "application/json"}
        data = '{"invalid": json}'  # Invalid JSON
        
        response = self.client.post("/api/v1/auth/login", data=data, headers=headers)
        assert response.status_code == 400
        assert "Invalid JSON format" in response.json()["detail"]
    
    def test_deeply_nested_json(self):
        """Test that deeply nested JSON is rejected."""
        # Create deeply nested JSON
        nested_data = {"level1": {"level2": {"level3": {"level4": {"level5": {
            "level6": {"level7": {"level8": {"level9": {"level10": {
                "level11": {"level12": "too deep"}
            }}}}}}}}}}}
        
        response = self.client.post("/api/v1/auth/login", json=nested_data)
        assert response.status_code == 400
        assert "JSON structure too complex" in response.json()["detail"]
    
    def test_json_with_too_many_keys(self):
        """Test that JSON with too many keys is rejected."""
        # Create JSON with many keys
        large_json = {f"key_{i}": f"value_{i}" for i in range(150)}  # Over 100 keys
        
        response = self.client.post("/api/v1/auth/login", json=large_json)
        assert response.status_code == 400
        assert "JSON object too complex" in response.json()["detail"]
    
    def test_json_with_large_array(self):
        """Test that JSON with large arrays is rejected."""
        large_array = {"data": list(range(1500))}  # Over 1000 items
        
        response = self.client.post("/api/v1/auth/login", json=large_array)
        assert response.status_code == 400
        assert "JSON array too large" in response.json()["detail"]
    
    def test_suspicious_json_values(self):
        """Test that suspicious JSON values are blocked."""
        suspicious_data = {
            "username": "admin",
            "password": "<script>alert('xss')</script>"
        }
        
        response = self.client.post("/api/v1/auth/login", json=suspicious_data)
        assert response.status_code == 400
        assert "Invalid JSON string value" in response.json()["detail"]
    
    def test_sql_injection_attempt(self):
        """Test that SQL injection attempts are blocked."""
        sql_injection = {
            "username": "admin' OR '1'='1",
            "password": "password"
        }
        
        response = self.client.post("/api/v1/auth/login", json=sql_injection)
        assert response.status_code == 400
    
    def test_long_url_rejected(self):
        """Test that overly long URLs are rejected."""
        # Create a very long URL
        long_path = "/api/v1/health?" + "x" * 3000  # Over 2048 characters
        
        response = self.client.get(long_path)
        assert response.status_code == 414
        assert "Request URL too long" in response.json()["detail"]
    
    def test_long_header_rejected(self):
        """Test that overly long headers are rejected."""
        headers = {"X-Long-Header": "x" * 10000}  # Over 8192 characters
        
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == 400
        assert "too long" in response.json()["detail"]
    
    def test_null_bytes_in_input(self):
        """Test that null bytes in input are handled."""
        data = {"username": "admin\x00", "password": "password"}
        
        response = self.client.post("/api/v1/auth/login", json=data)
        # Should either be sanitized or rejected
        assert response.status_code in [200, 400, 401]  # Various valid responses


class TestInputSanitizer:
    """Test cases for the InputSanitizer class."""
    
    def setup_method(self):
        """Set up sanitizer for testing."""
        self.sanitizer = InputSanitizer()
    
    def test_sanitize_normal_string(self):
        """Test sanitizing normal strings."""
        result = self.sanitizer.sanitize_string("Hello World")
        assert result == "Hello World"
    
    def test_sanitize_string_with_null_bytes(self):
        """Test sanitizing strings with null bytes."""
        result = self.sanitizer.sanitize_string("Hello\x00World")
        assert result == "HelloWorld"
    
    def test_sanitize_string_with_control_chars(self):
        """Test sanitizing strings with control characters."""
        result = self.sanitizer.sanitize_string("Hello\x01\x02World")
        assert result == "HelloWorld"
    
    def test_sanitize_string_preserve_newlines_tabs(self):
        """Test that newlines and tabs are preserved."""
        result = self.sanitizer.sanitize_string("Hello\nWorld\tTest")
        assert result == "Hello\nWorld\tTest"
    
    def test_sanitize_string_truncate_long(self):
        """Test that long strings are truncated."""
        long_string = "x" * 1500
        result = self.sanitizer.sanitize_string(long_string, max_length=1000)
        assert len(result) == 1000
    
    def test_sanitize_string_strip_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        result = self.sanitizer.sanitize_string("  Hello World  ")
        assert result == "Hello World"
    
    def test_sanitize_url_normal(self):
        """Test sanitizing normal URLs."""
        result = self.sanitizer.sanitize_url("https://example.com")
        assert result == "https://example.com"
    
    def test_sanitize_url_add_https(self):
        """Test that https is added to URLs without protocol."""
        result = self.sanitizer.sanitize_url("example.com")
        assert result == "https://example.com"
    
    def test_sanitize_url_protocol_relative(self):
        """Test handling of protocol-relative URLs."""
        result = self.sanitizer.sanitize_url("//example.com")
        assert result == "https://example.com"
    
    def test_sanitize_url_dangerous_protocols(self):
        """Test that dangerous protocols are rejected."""
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "file:///etc/passwd"
        ]
        
        for url in dangerous_urls:
            with pytest.raises(ValueError):
                self.sanitizer.sanitize_url(url)
    
    def test_sanitize_filename_normal(self):
        """Test sanitizing normal filenames."""
        result = self.sanitizer.sanitize_filename("document.pdf")
        assert result == "document.pdf"
    
    def test_sanitize_filename_dangerous_chars(self):
        """Test sanitizing filenames with dangerous characters."""
        result = self.sanitizer.sanitize_filename("../../../etc/passwd")
        assert result == "______etc_passwd"
    
    def test_sanitize_filename_path_separators(self):
        """Test that path separators are removed."""
        result = self.sanitizer.sanitize_filename("folder/file.txt")
        assert result == "folder_file.txt"
        
        result = self.sanitizer.sanitize_filename("folder\\file.txt")
        assert result == "folder_file.txt"
    
    def test_sanitize_filename_empty(self):
        """Test handling of empty filenames."""
        result = self.sanitizer.sanitize_filename("")
        assert result == "unnamed_file"
        
        result = self.sanitizer.sanitize_filename("   ")
        assert result == "unnamed_file"
    
    def test_sanitize_filename_long(self):
        """Test truncating long filenames."""
        long_name = "x" * 300 + ".txt"
        result = self.sanitizer.sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")
    
    def test_sanitize_filename_dots_and_spaces(self):
        """Test handling of leading/trailing dots and spaces."""
        result = self.sanitizer.sanitize_filename("  ..file.txt..  ")
        assert result == "file.txt"
    
    def test_sanitize_filename_special_chars(self):
        """Test handling of special characters in filenames."""
        result = self.sanitizer.sanitize_filename('file<>:"|?*.txt')
        assert result == "file________.txt"


class TestValidationEdgeCases:
    """Test edge cases for validation middleware."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_empty_request_body(self):
        """Test handling of empty request bodies."""
        response = self.client.post("/api/v1/auth/login", data="")
        # Should handle empty body gracefully
        assert response.status_code in [400, 422]  # Validation error expected
    
    def test_binary_data_in_json_endpoint(self):
        """Test handling of binary data sent to JSON endpoint."""
        binary_data = b'\x00\x01\x02\x03\x04\x05'
        headers = {"Content-Type": "application/json"}
        
        response = self.client.post("/api/v1/auth/login", data=binary_data, headers=headers)
        assert response.status_code == 400
    
    def test_unicode_in_request(self):
        """Test handling of Unicode characters in requests."""
        unicode_data = {
            "username": "用户名",  # Chinese characters
            "password": "пароль"   # Cyrillic characters
        }
        
        response = self.client.post("/api/v1/auth/login", json=unicode_data)
        # Should handle Unicode gracefully (might fail auth, but not validation)
        assert response.status_code != 400
    
    def test_mixed_content_types(self):
        """Test handling of mixed content types."""
        # Send form data with JSON content type
        headers = {"Content-Type": "application/json"}
        data = "username=admin&password=password"
        
        response = self.client.post("/api/v1/auth/login", data=data, headers=headers)
        assert response.status_code == 400
    
    def test_request_without_content_type(self):
        """Test handling of requests without content type."""
        data = '{"username": "admin", "password": "password"}'
        
        response = self.client.post("/api/v1/auth/login", data=data)
        # Should handle missing content type
        assert response.status_code in [400, 422]


@pytest.fixture
def validation_test_data():
    """Provide test data for validation tests."""
    return {
        "normal_data": {"username": "testuser", "password": "testpass"},
        "xss_data": {"username": "<script>alert('xss')</script>", "password": "test"},
        "sql_injection": {"username": "admin' OR '1'='1", "password": "test"},
        "path_traversal": {"file": "../../../etc/passwd"},
        "large_data": {"data": "x" * 1000000},  # 1MB
        "nested_data": {"a": {"b": {"c": {"d": {"e": {"f": "deep"}}}}}},
    }


def test_validation_with_test_data(validation_test_data):
    """Test validation with various test data scenarios."""
    client = TestClient(app)
    
    # Normal data should pass validation
    response = client.post("/api/v1/auth/login", json=validation_test_data["normal_data"])
    assert response.status_code != 400  # Should not be blocked by validation
    
    # XSS data should be blocked
    response = client.post("/api/v1/auth/login", json=validation_test_data["xss_data"])
    assert response.status_code == 400
    
    # SQL injection should be blocked
    response = client.post("/api/v1/auth/login", json=validation_test_data["sql_injection"])
    assert response.status_code == 400