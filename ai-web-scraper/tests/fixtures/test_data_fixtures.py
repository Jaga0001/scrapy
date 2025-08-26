"""
Comprehensive test data fixtures for all testing scenarios.

This module provides fixtures for various test data scenarios including
edge cases, performance testing, and integration testing.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import uuid4

from src.models.pydantic_models import (
    ScrapingJob, ScrapedData, ScrapingConfig, JobStatus, ContentType,
    DataExportRequest, ScrapingResult
)


@pytest.fixture
def large_dataset_jobs():
    """Large dataset of scraping jobs for performance testing."""
    jobs = []
    
    for i in range(1000):
        job = ScrapingJob(
            id=f'perf-job-{i:04d}',
            url=f'https://performance-test.com/page{i}',
            config=ScrapingConfig(
                wait_time=2,
                max_retries=3,
                use_stealth=True,
                headless=True
            ),
            status=JobStatus.COMPLETED if i % 3 == 0 else JobStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(hours=i // 100),
            completed_at=datetime.utcnow() - timedelta(hours=i // 100 - 1) if i % 3 == 0 else None,
            total_pages=10 + (i % 50),
            pages_completed=10 + (i % 50) if i % 3 == 0 else i % 10,
            pages_failed=i % 5,
            priority=1 + (i % 10),
            tags=[f'category-{i % 5}', f'batch-{i // 100}'],
            user_id=f'user-{i % 20}'
        )
        jobs.append(job)
    
    return jobs


@pytest.fixture
def large_dataset_scraped_data():
    """Large dataset of scraped data for performance testing."""
    data_list = []
    
    for i in range(5000):
        data = ScrapedData(
            id=f'perf-data-{i:05d}',
            job_id=f'perf-job-{i // 5:04d}',
            url=f'https://performance-test.com/page{i // 5}/item{i % 5}',
            content={
                'title': f'Performance Test Item {i}',
                'description': f'This is test content for performance testing item {i}. ' * 10,
                'price': f'${(i % 1000) + 10}.99',
                'category': f'Category {i % 20}',
                'rating': round(1 + (i % 50) / 10, 1),
                'reviews': i % 500,
                'features': [f'feature-{j}' for j in range(i % 10)],
                'specifications': {
                    f'spec-{j}': f'value-{i}-{j}'
                    for j in range(i % 5)
                }
            },
            raw_html=f'<html><body>Mock HTML content for item {i}</body></html>' * 5,
            content_type=ContentType.HTML,
            content_metadata={
                'page_load_time': 1.0 + (i % 100) / 100,
                'dom_elements': 100 + (i % 500),
                'images_found': i % 20,
                'links_found': i % 50
            },
            confidence_score=0.5 + (i % 50) / 100,
            ai_processed=i % 3 == 0,
            ai_metadata={
                'processing_time': 0.5 + (i % 100) / 200,
                'entities_found': i % 15,
                'classification_confidence': 0.7 + (i % 30) / 100
            } if i % 3 == 0 else None,
            data_quality_score=0.6 + (i % 40) / 100,
            validation_errors=[f'error-{j}' for j in range(i % 3)],
            extracted_at=datetime.utcnow() - timedelta(minutes=i),
            processed_at=datetime.utcnow() - timedelta(minutes=i - 1) if i % 3 == 0 else None,
            content_length=500 + (i % 2000),
            load_time=0.5 + (i % 100) / 100
        )
        data_list.append(data)
    
    return data_list


@pytest.fixture
def edge_case_scraping_configs():
    """Edge case scraping configurations for testing."""
    return [
        # Minimal configuration
        ScrapingConfig(
            wait_time=1,
            max_retries=1,
            timeout=5
        ),
        
        # Maximum configuration
        ScrapingConfig(
            wait_time=60,
            max_retries=10,
            timeout=300,
            use_stealth=True,
            headless=False,
            user_agent="Custom User Agent String" * 10,  # Very long user agent
            extract_images=True,
            extract_links=True,
            follow_links=True,
            max_depth=10,
            custom_selectors={f'selector-{i}': f'css-selector-{i}' for i in range(50)},
            exclude_selectors=[f'exclude-{i}' for i in range(20)],
            delay_between_requests=10.0,
            respect_robots_txt=True,
            javascript_enabled=True,
            load_images=True,
            proxy_url="http://proxy.example.com:8080"
        ),
        
        # Invalid/problematic configuration
        ScrapingConfig(
            wait_time=0,  # Invalid wait time
            max_retries=0,  # No retries
            timeout=1,  # Very short timeout
            user_agent="",  # Empty user agent
            custom_selectors={},  # Empty selectors
            delay_between_requests=0.0  # No delay
        )
    ]


@pytest.fixture
def malformed_scraped_data():
    """Malformed scraped data for error handling testing."""
    return [
        # Missing required fields
        {
            'id': 'malformed-1',
            'url': 'https://test.com/malformed1',
            # Missing job_id, content, etc.
        },
        
        # Invalid data types
        {
            'id': 'malformed-2',
            'job_id': 123,  # Should be string
            'url': 'not-a-url',  # Invalid URL
            'content': "not-a-dict",  # Should be dict
            'confidence_score': "high",  # Should be float
            'extracted_at': "not-a-datetime"  # Should be datetime
        },
        
        # Extreme values
        {
            'id': 'malformed-3',
            'job_id': 'test-job',
            'url': 'https://test.com/extreme',
            'content': {'data': 'x' * 1000000},  # Very large content
            'confidence_score': 2.0,  # Invalid confidence score (>1.0)
            'content_length': -100,  # Negative length
            'load_time': -5.0,  # Negative time
            'extracted_at': datetime.utcnow()
        },
        
        # Unicode and special characters
        {
            'id': 'malformed-4',
            'job_id': 'test-job',
            'url': 'https://test.com/unicode',
            'content': {
                'title': '测试标题 🚀 émojis and ñoñó',
                'text': 'Content with\x00null\x01bytes\x02and\x03control\x04chars',
                'special': '\\n\\r\\t\\"\\\'',
                'unicode': '\u0000\u001f\u007f\u0080\u009f'
            },
            'confidence_score': 0.8,
            'extracted_at': datetime.utcnow()
        }
    ]


@pytest.fixture
def concurrent_test_scenarios():
    """Test scenarios for concurrent processing."""
    return {
        'light_load': {
            'num_jobs': 10,
            'concurrent_workers': 2,
            'processing_time': 0.01,
            'failure_rate': 0.0
        },
        'medium_load': {
            'num_jobs': 50,
            'concurrent_workers': 5,
            'processing_time': 0.05,
            'failure_rate': 0.1
        },
        'heavy_load': {
            'num_jobs': 200,
            'concurrent_workers': 10,
            'processing_time': 0.1,
            'failure_rate': 0.2
        },
        'stress_test': {
            'num_jobs': 1000,
            'concurrent_workers': 20,
            'processing_time': 0.02,
            'failure_rate': 0.3
        }
    }


@pytest.fixture
def export_test_scenarios():
    """Test scenarios for data export functionality."""
    return {
        'small_export': {
            'record_count': 100,
            'formats': ['csv', 'json'],
            'include_metadata': False,
            'expected_size_kb': 50
        },
        'medium_export': {
            'record_count': 10000,
            'formats': ['csv', 'json', 'xlsx'],
            'include_metadata': True,
            'expected_size_kb': 5000
        },
        'large_export': {
            'record_count': 100000,
            'formats': ['csv'],
            'include_metadata': False,
            'expected_size_kb': 50000
        },
        'filtered_export': {
            'record_count': 1000,
            'formats': ['json'],
            'filters': {
                'min_confidence': 0.8,
                'content_type': 'html',
                'date_range': {
                    'start': datetime.utcnow() - timedelta(days=7),
                    'end': datetime.utcnow()
                }
            },
            'expected_filtered_count': 500
        }
    }


@pytest.fixture
def api_test_scenarios():
    """Test scenarios for API endpoint testing."""
    return {
        'valid_requests': [
            {
                'endpoint': '/api/v1/jobs',
                'method': 'POST',
                'data': {
                    'url': 'https://test.com',
                    'config': {'wait_time': 5},
                    'tags': ['test']
                },
                'expected_status': 201
            },
            {
                'endpoint': '/api/v1/jobs/test-job-123',
                'method': 'GET',
                'expected_status': 200
            },
            {
                'endpoint': '/api/v1/data',
                'method': 'GET',
                'params': {'page': 1, 'page_size': 50},
                'expected_status': 200
            }
        ],
        'invalid_requests': [
            {
                'endpoint': '/api/v1/jobs',
                'method': 'POST',
                'data': {'invalid': 'data'},
                'expected_status': 422
            },
            {
                'endpoint': '/api/v1/jobs/nonexistent',
                'method': 'GET',
                'expected_status': 404
            },
            {
                'endpoint': '/api/v1/data',
                'method': 'GET',
                'params': {'page': -1},
                'expected_status': 422
            }
        ],
        'authentication_tests': [
            {
                'endpoint': '/api/v1/jobs',
                'method': 'POST',
                'headers': {},  # No auth header
                'expected_status': 401
            },
            {
                'endpoint': '/api/v1/jobs',
                'method': 'POST',
                'headers': {'Authorization': 'Bearer invalid-token'},
                'expected_status': 401
            }
        ]
    }


@pytest.fixture
def error_simulation_scenarios():
    """Scenarios for testing error handling and recovery."""
    return {
        'network_errors': [
            {'error_type': 'ConnectionError', 'retry_count': 3},
            {'error_type': 'TimeoutError', 'retry_count': 2},
            {'error_type': 'DNSError', 'retry_count': 1}
        ],
        'scraping_errors': [
            {'error_type': 'ElementNotFound', 'recovery_strategy': 'alternative_selector'},
            {'error_type': 'JavaScriptError', 'recovery_strategy': 'disable_js'},
            {'error_type': 'PageLoadError', 'recovery_strategy': 'retry_with_delay'}
        ],
        'ai_processing_errors': [
            {'error_type': 'APIRateLimitError', 'recovery_strategy': 'exponential_backoff'},
            {'error_type': 'ModelOverloadError', 'recovery_strategy': 'fallback_model'},
            {'error_type': 'ContentTooLargeError', 'recovery_strategy': 'chunk_content'}
        ],
        'database_errors': [
            {'error_type': 'ConnectionPoolExhausted', 'recovery_strategy': 'wait_and_retry'},
            {'error_type': 'DeadlockError', 'recovery_strategy': 'retry_transaction'},
            {'error_type': 'DiskFullError', 'recovery_strategy': 'cleanup_old_data'}
        ]
    }


@pytest.fixture
def performance_benchmarks():
    """Performance benchmarks for testing."""
    return {
        'scraping_performance': {
            'pages_per_minute': 60,
            'max_memory_usage_mb': 500,
            'max_cpu_usage_percent': 80,
            'max_response_time_ms': 2000
        },
        'ai_processing_performance': {
            'items_per_minute': 120,
            'max_processing_time_ms': 5000,
            'max_memory_per_item_mb': 50,
            'min_confidence_score': 0.7
        },
        'api_performance': {
            'max_response_time_ms': 500,
            'requests_per_second': 100,
            'max_concurrent_connections': 1000,
            'max_memory_usage_mb': 200
        },
        'database_performance': {
            'max_query_time_ms': 100,
            'max_connection_pool_size': 20,
            'max_transaction_time_ms': 1000,
            'min_throughput_ops_per_second': 1000
        }
    }


@pytest.fixture
def data_quality_test_cases():
    """Test cases for data quality validation."""
    return {
        'high_quality_data': [
            {
                'content': {
                    'title': 'Complete Product Information',
                    'description': 'Detailed product description with all necessary information.',
                    'price': '$99.99',
                    'availability': 'in_stock',
                    'rating': 4.5,
                    'reviews_count': 150
                },
                'expected_quality_score': 0.95,
                'expected_validation_errors': []
            }
        ],
        'medium_quality_data': [
            {
                'content': {
                    'title': 'Partial Product Info',
                    'price': '$99.99',
                    'availability': 'in_stock'
                    # Missing description, rating, reviews
                },
                'expected_quality_score': 0.7,
                'expected_validation_errors': ['missing_description']
            }
        ],
        'low_quality_data': [
            {
                'content': {
                    'title': '',  # Empty title
                    'description': 'x',  # Too short
                    'price': 'invalid price'  # Invalid format
                },
                'expected_quality_score': 0.3,
                'expected_validation_errors': ['empty_title', 'short_description', 'invalid_price']
            }
        ],
        'duplicate_detection_cases': [
            {
                'original': {
                    'title': 'Original Product',
                    'description': 'Original description',
                    'url': 'https://test.com/original'
                },
                'duplicate': {
                    'title': 'Original Product',  # Same title
                    'description': 'Original description',  # Same description
                    'url': 'https://test.com/duplicate'  # Different URL
                },
                'expected_duplicate': True,
                'similarity_threshold': 0.9
            }
        ]
    }


@pytest.fixture
def integration_test_workflows():
    """Complete workflows for integration testing."""
    return {
        'simple_workflow': {
            'steps': [
                {'action': 'create_job', 'url': 'https://test.com'},
                {'action': 'scrape_content', 'expected_pages': 1},
                {'action': 'process_ai', 'expected_confidence': 0.8},
                {'action': 'clean_data', 'expected_quality': 0.9},
                {'action': 'save_data', 'expected_records': 1}
            ],
            'expected_duration_seconds': 10,
            'expected_success_rate': 1.0
        },
        'complex_workflow': {
            'steps': [
                {'action': 'create_bulk_jobs', 'urls': [f'https://test.com/page{i}' for i in range(10)]},
                {'action': 'scrape_with_pagination', 'expected_pages': 50},
                {'action': 'process_ai_batch', 'batch_size': 10},
                {'action': 'clean_and_validate', 'validation_rules': ['required_fields', 'data_types']},
                {'action': 'save_with_deduplication', 'expected_unique_records': 45},
                {'action': 'export_results', 'format': 'csv'}
            ],
            'expected_duration_seconds': 60,
            'expected_success_rate': 0.9
        },
        'error_recovery_workflow': {
            'steps': [
                {'action': 'create_job', 'url': 'https://failing-site.com'},
                {'action': 'scrape_with_retries', 'max_retries': 3},
                {'action': 'handle_scraping_failure', 'fallback_strategy': 'alternative_method'},
                {'action': 'process_partial_data', 'min_confidence': 0.6},
                {'action': 'save_with_error_flags', 'mark_as_partial': True}
            ],
            'expected_duration_seconds': 30,
            'expected_success_rate': 0.7
        }
    }


@pytest.fixture
def security_test_scenarios():
    """Security testing scenarios."""
    return {
        'input_validation': [
            {'input': '<script>alert("xss")</script>', 'expected': 'sanitized'},
            {'input': '../../etc/passwd', 'expected': 'blocked'},
            {'input': 'DROP TABLE users;', 'expected': 'escaped'}
        ],
        'authentication_bypass': [
            {'method': 'missing_token', 'expected_status': 401},
            {'method': 'expired_token', 'expected_status': 401},
            {'method': 'malformed_token', 'expected_status': 401}
        ],
        'rate_limiting': [
            {'requests_per_second': 100, 'expected_status': 200},
            {'requests_per_second': 1000, 'expected_status': 429}
        ]
    }


# Utility functions for test data generation
def generate_random_content(size_kb: int) -> Dict[str, Any]:
    """Generate random content of specified size."""
    import random
    import string
    
    content_size = size_kb * 1024
    random_text = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=content_size))
    
    return {
        'title': f'Random Title {random.randint(1, 1000)}',
        'text': random_text,
        'metadata': {
            'generated_at': datetime.utcnow().isoformat(),
            'size_kb': size_kb,
            'random_seed': random.randint(1, 1000000)
        }
    }


def generate_test_urls(count: int, domain: str = 'test.com') -> List[str]:
    """Generate test URLs."""
    return [f'https://{domain}/page{i}' for i in range(count)]


def generate_time_series_data(
    start_time: datetime,
    end_time: datetime,
    interval_minutes: int = 5
) -> List[Dict[str, Any]]:
    """Generate time series test data."""
    import random
    
    data = []
    current_time = start_time
    
    while current_time <= end_time:
        data.append({
            'timestamp': current_time,
            'cpu_usage': random.uniform(20, 80),
            'memory_usage': random.uniform(40, 90),
            'active_jobs': random.randint(0, 20),
            'queue_size': random.randint(0, 100)
        })
        current_time += timedelta(minutes=interval_minutes)
    
    return data