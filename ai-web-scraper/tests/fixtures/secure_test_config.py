"""
Secure test configuration to prevent information leakage in tests.
"""

import os
from typing import List, Dict, Any


class SecureTestConfig:
    """Secure configuration for tests that prevents information leakage."""
    
    # Generic test URLs that don't reveal system information
    TEST_URLS = {
        'single': 'https://httpbin.org/html',
        'multiple': [
            'https://httpbin.org/json',
            'https://httpbin.org/xml',
            'https://httpbin.org/robots.txt'
        ],
        'pagination_base': 'https://httpbin.org/anything',
        'error_prone': 'https://httpbin.org/status/500'
    }
    
    # Generic user agents for testing
    TEST_USER_AGENTS = [
        "Mozilla/5.0 (compatible; TestBot/1.0)",
        "Mozilla/5.0 (compatible; IntegrationTest/1.0)",
        "Mozilla/5.0 (compatible; QABot/1.0)"
    ]
    
    # Safe test credentials (never use in production)
    TEST_CREDENTIALS = {
        'db_user': 'test_user',
        'db_password': 'test_password_' + os.urandom(8).hex(),
        'api_key': 'test-api-key-' + os.urandom(16).hex()
    }
    
    @classmethod
    def get_test_database_url(cls) -> str:
        """Get test database URL from environment or generate safe default."""
        return os.getenv(
            'TEST_DATABASE_URL',
            f"postgresql://{cls.TEST_CREDENTIALS['db_user']}:{cls.TEST_CREDENTIALS['db_password']}@localhost:5432/test_webscraper"
        )
    
    @classmethod
    def get_test_redis_url(cls) -> str:
        """Get test Redis URL from environment or generate safe default."""
        return os.getenv('TEST_REDIS_URL', 'redis://localhost:6379/0')
    
    @classmethod
    def get_test_api_key(cls) -> str:
        """Get test API key from environment or generate safe default."""
        return os.getenv('TEST_GEMINI_API_KEY', cls.TEST_CREDENTIALS['api_key'])
    
    @classmethod
    def get_safe_scraping_config(cls) -> Dict[str, Any]:
        """Get safe scraping configuration for tests."""
        return {
            'wait_time': 1,  # Faster for tests
            'max_retries': 2,
            'timeout': 10,  # Shorter timeout for tests
            'use_stealth': False,  # Disable stealth for faster tests
            'headless': True,
            'javascript_enabled': False,  # Disable JS for faster tests
            'follow_links': False,  # Prevent uncontrolled crawling
            'max_depth': 1,
            'respect_robots_txt': True,
            'delay_between_requests': 0.1,  # Minimal delay for tests
            'user_agents': cls.TEST_USER_AGENTS
        }
    
    @classmethod
    def sanitize_test_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize test data to remove any potentially sensitive information."""
        sanitized = data.copy()
        
        # Remove or mask sensitive fields
        sensitive_fields = ['password', 'token', 'key', 'secret', 'credential']
        
        for key, value in sanitized.items():
            if any(field in key.lower() for field in sensitive_fields):
                if isinstance(value, str):
                    sanitized[key] = '[REDACTED]'
                elif isinstance(value, dict):
                    sanitized[key] = cls.sanitize_test_data(value)
        
        return sanitized