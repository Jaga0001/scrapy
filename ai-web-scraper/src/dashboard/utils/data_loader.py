"""
Data loader utility for the Streamlit dashboard.

This module provides centralized data loading functionality for the dashboard,
handling caching, error handling, and data transformation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache

import streamlit as st

from src.pipeline.repository import DataRepository
from src.models.pydantic_models import JobStatus, ScrapingJob, ScrapedData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DashboardDataLoader:
    """
    Centralized data loader for dashboard components.
    
    Provides caching, error handling, and data transformation
    for all dashboard data needs.
    """
    
    def __init__(self):
        """Initialize the data loader."""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.repository = DataRepository()
        self._cache_timeout = 30  # seconds
    
    @st.cache_data(ttl=30)
    def get_job_statistics(_self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get job statistics with caching.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dictionary containing job statistics
        """
        try:
            # This would typically call the repository
            # For now, return mock data
            return {
                'total_jobs': 1250,
                'completed_jobs': 1180,
                'failed_jobs': 45,
                'running_jobs': 15,
                'pending_jobs': 10,
                'success_rate': 94.4,
                'average_pages_per_job': 45.2,
                'total_pages_scraped': 53340,
                'average_job_duration': 125.5
            }
        except Exception as e:
            _self.logger.error(f"Error getting job statistics: {e}")
            return {}
    
    @st.cache_data(ttl=60)
    def get_data_quality_metrics(_self) -> Dict[str, Any]:
        """
        Get data quality metrics with caching.
        
        Returns:
            Dictionary containing data quality metrics
        """
        try:
            # This would typically call the repository
            return {
                'total_records': 15420,
                'average_confidence_score': 0.87,
                'average_quality_score': 0.91,
                'ai_processed_percentage': 94.2,
                'records_with_errors': 156,
                'error_rate': 1.01,
                'duplicate_records': 23,
                'validation_errors_by_type': {
                    'Missing Required Field': 45,
                    'Invalid Format': 32,
                    'Low Confidence': 51,
                    'Duplicate Content': 28
                }
            }
        except Exception as e:
            _self.logger.error(f"Error getting data quality metrics: {e}")
            return {}
    
    @st.cache_data(ttl=15)
    def get_system_health(_self) -> Dict[str, Any]:
        """
        Get system health information with caching.
        
        Returns:
            Dictionary containing system health data
        """
        try:
            # This would typically check actual system health
            return {
                'overall_status': 'healthy',
                'services': {
                    'api': {'status': 'healthy', 'response_time': 45},
                    'database': {'status': 'warning', 'response_time': 120},
                    'redis': {'status': 'healthy', 'response_time': 2},
                    'workers': {'status': 'healthy', 'active_count': 4}
                },
                'system_resources': {
                    'cpu_usage': 35.2,
                    'memory_usage': 68.5,
                    'disk_usage': 45.8,
                    'network_io': {'sent': 1250000, 'received': 2340000}
                },
                'performance_metrics': {
                    'scraping_rate': 45.2,
                    'queue_size': 12,
                    'average_response_time': 250,
                    'error_rate': 0.8
                }
            }
        except Exception as e:
            _self.logger.error(f"Error getting system health: {e}")
            return {}
    
    async def get_active_jobs(
        self,
        status_filter: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get active jobs with filtering.
        
        Args:
            status_filter: List of statuses to filter by
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of job dictionaries
        """
        try:
            # This would typically call the repository
            # For now, return mock data
            mock_jobs = [
                {
                    'id': 'job-001',
                    'url': 'https://example.com/products',
                    'status': 'running',
                    'pages_completed': 45,
                    'pages_failed': 2,
                    'total_pages': 100,
                    'created_at': datetime.now() - timedelta(hours=2),
                    'started_at': datetime.now() - timedelta(hours=1, minutes=45),
                    'priority': 3,
                    'tags': ['ecommerce', 'products'],
                    'progress_percentage': 45.0
                },
                {
                    'id': 'job-002',
                    'url': 'https://news.example.com',
                    'status': 'pending',
                    'pages_completed': 0,
                    'pages_failed': 0,
                    'total_pages': 50,
                    'created_at': datetime.now() - timedelta(minutes=30),
                    'started_at': None,
                    'priority': 5,
                    'tags': ['news', 'articles'],
                    'progress_percentage': 0.0
                },
                {
                    'id': 'job-003',
                    'url': 'https://blog.example.com',
                    'status': 'completed',
                    'pages_completed': 25,
                    'pages_failed': 1,
                    'total_pages': 25,
                    'created_at': datetime.now() - timedelta(hours=4),
                    'started_at': datetime.now() - timedelta(hours=3, minutes=45),
                    'completed_at': datetime.now() - timedelta(hours=3),
                    'priority': 7,
                    'tags': ['blog', 'content'],
                    'progress_percentage': 100.0
                }
            ]
            
            # Apply status filter if provided
            if status_filter:
                mock_jobs = [job for job in mock_jobs if job['status'] in status_filter]
            
            # Apply pagination
            return mock_jobs[offset:offset + limit]
            
        except Exception as e:
            self.logger.error(f"Error getting active jobs: {e}")
            return []
    
    async def get_scraped_data(
        self,
        job_id: Optional[str] = None,
        min_confidence: float = 0.0,
        min_quality: float = 0.0,
        ai_processed_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get scraped data with filtering and pagination.
        
        Args:
            job_id: Filter by specific job ID
            min_confidence: Minimum confidence score
            min_quality: Minimum quality score
            ai_processed_only: Only return AI-processed data
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            Tuple of (data_list, total_count)
        """
        try:
            # This would typically call the repository
            mock_data = [
                {
                    'id': f'data-{i:03d}',
                    'job_id': 'job-001',
                    'url': f'https://example.com/page{i}',
                    'confidence_score': 0.8 + (i % 20) * 0.01,
                    'data_quality_score': 0.85 + (i % 15) * 0.01,
                    'ai_processed': i % 3 == 0,
                    'extracted_at': datetime.now() - timedelta(hours=i),
                    'content': {
                        'title': f'Sample Title {i}',
                        'content': f'Sample content for page {i}...',
                        'price': f'${10 + i}.99' if i % 5 == 0 else None
                    },
                    'content_length': 1000 + i * 50,
                    'validation_errors': [] if i % 10 != 0 else ['Missing required field: description']
                }
                for i in range(1, 201)
            ]
            
            # Apply filters
            filtered_data = mock_data
            
            if job_id:
                filtered_data = [d for d in filtered_data if d['job_id'] == job_id]
            
            if min_confidence > 0:
                filtered_data = [d for d in filtered_data if d['confidence_score'] >= min_confidence]
            
            if min_quality > 0:
                filtered_data = [d for d in filtered_data if d['data_quality_score'] >= min_quality]
            
            if ai_processed_only:
                filtered_data = [d for d in filtered_data if d['ai_processed']]
            
            total_count = len(filtered_data)
            
            # Apply pagination
            paginated_data = filtered_data[offset:offset + limit]
            
            return paginated_data, total_count
            
        except Exception as e:
            self.logger.error(f"Error getting scraped data: {e}")
            return [], 0
    
    @st.cache_data(ttl=300)
    def get_analytics_data(_self, time_range: str = "24h") -> Dict[str, Any]:
        """
        Get analytics data for charts and visualizations.
        
        Args:
            time_range: Time range for analytics (1h, 6h, 24h, 7d, 30d)
            
        Returns:
            Dictionary containing analytics data
        """
        try:
            # Time range mapping
            hours_map = {
                "1h": 1,
                "6h": 6,
                "24h": 24,
                "7d": 168,
                "30d": 720
            }
            
            hours = hours_map.get(time_range, 24)
            
            # Generate mock time series data
            volume_data = [
                {
                    'timestamp': datetime.now() - timedelta(hours=i),
                    'count': max(0, 100 + (i % 50) - 25),
                    'success_count': max(0, 95 + (i % 45) - 20),
                    'error_count': max(0, 5 + (i % 10) - 5)
                }
                for i in range(hours, 0, -1)
            ]
            
            performance_data = [
                {
                    'timestamp': datetime.now() - timedelta(hours=i),
                    'pages_per_minute': max(10, 45 + (i % 30) - 15),
                    'response_time': max(50, 200 + (i % 100) - 50),
                    'cpu_usage': max(10, 35 + (i % 40) - 20),
                    'memory_usage': max(20, 60 + (i % 30) - 15)
                }
                for i in range(hours, 0, -1)
            ]
            
            return {
                'volume_data': volume_data,
                'performance_data': performance_data,
                'domain_distribution': {
                    'example.com': 5420,
                    'test.com': 3210,
                    'sample.org': 2890,
                    'demo.net': 1560,
                    'other': 2340
                },
                'content_type_distribution': {
                    'html': 12000,
                    'json': 2500,
                    'xml': 920,
                    'text': 450
                },
                'quality_distribution': {
                    f'0.{i}': max(0, 100 + (i * 20) - 50)
                    for i in range(10)
                },
                'error_types': {
                    'Network Error': 45,
                    'Parsing Error': 32,
                    'Validation Error': 28,
                    'Timeout Error': 15,
                    'Other': 12
                }
            }
            
        except Exception as e:
            _self.logger.error(f"Error getting analytics data: {e}")
            return {}
    
    async def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job details dictionary or None if not found
        """
        try:
            # This would typically call the repository
            if job_id == 'job-001':
                return {
                    'id': job_id,
                    'url': 'https://example.com/products',
                    'status': 'running',
                    'pages_completed': 45,
                    'pages_failed': 2,
                    'total_pages': 100,
                    'created_at': datetime.now() - timedelta(hours=2),
                    'started_at': datetime.now() - timedelta(hours=1, minutes=45),
                    'priority': 3,
                    'tags': ['ecommerce', 'products'],
                    'config': {
                        'wait_time': 5,
                        'max_retries': 3,
                        'use_stealth': True,
                        'extract_images': True,
                        'custom_selectors': {
                            'title': '.product-title',
                            'price': '.price',
                            'description': '.product-description'
                        }
                    },
                    'logs': [
                        {
                            'timestamp': datetime.now() - timedelta(minutes=30),
                            'level': 'INFO',
                            'message': 'Started scraping page 45'
                        },
                        {
                            'timestamp': datetime.now() - timedelta(minutes=35),
                            'level': 'WARNING',
                            'message': 'Slow response from server, retrying...'
                        }
                    ],
                    'metrics': {
                        'average_page_load_time': 2.5,
                        'success_rate': 95.7,
                        'data_quality_score': 0.89
                    }
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting job details: {e}")
            return None
    
    async def get_system_metrics(
        self,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get system metrics data.
        
        Args:
            metric_names: List of metric names to filter by
            start_time: Start time for metrics
            end_time: End time for metrics
            limit: Maximum number of metrics to return
            
        Returns:
            List of metric dictionaries
        """
        try:
            # This would typically call the repository
            if not start_time:
                start_time = datetime.now() - timedelta(hours=24)
            if not end_time:
                end_time = datetime.now()
            
            # Generate mock metrics data
            metrics = []
            metric_types = metric_names or ['cpu_usage', 'memory_usage', 'disk_usage', 'network_io']
            
            current_time = start_time
            while current_time <= end_time:
                for metric_name in metric_types:
                    base_value = {
                        'cpu_usage': 35,
                        'memory_usage': 60,
                        'disk_usage': 45,
                        'network_io': 1000
                    }.get(metric_name, 50)
                    
                    # Add some variation
                    import random
                    value = base_value + random.uniform(-10, 10)
                    
                    metrics.append({
                        'id': f'metric_{len(metrics)}',
                        'metric_name': metric_name,
                        'metric_value': max(0, value),
                        'metric_unit': '%' if 'usage' in metric_name else 'MB/s',
                        'recorded_at': current_time,
                        'tags': {'component': 'system'}
                    })
                
                current_time += timedelta(minutes=5)
            
            return metrics[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return []
    
    @lru_cache(maxsize=128)
    def get_available_jobs(self) -> List[str]:
        """
        Get list of available job IDs for filtering.
        
        Returns:
            List of job IDs
        """
        try:
            # This would typically query the database
            return ['job-001', 'job-002', 'job-003', 'job-004', 'job-005']
        except Exception as e:
            self.logger.error(f"Error getting available jobs: {e}")
            return []
    
    @lru_cache(maxsize=128)
    def get_available_domains(self) -> List[str]:
        """
        Get list of available domains for filtering.
        
        Returns:
            List of domain names
        """
        try:
            # This would typically query the database
            return ['example.com', 'test.com', 'sample.org', 'demo.net', 'other.com']
        except Exception as e:
            self.logger.error(f"Error getting available domains: {e}")
            return []
    
    def clear_cache(self):
        """Clear all cached data."""
        try:
            # Clear Streamlit cache
            st.cache_data.clear()
            
            # Clear LRU caches
            self.get_available_jobs.cache_clear()
            self.get_available_domains.cache_clear()
            
            self.logger.info("Cache cleared successfully")
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about cache usage.
        
        Returns:
            Dictionary containing cache information
        """
        try:
            return {
                'available_jobs_cache': self.get_available_jobs.cache_info()._asdict(),
                'available_domains_cache': self.get_available_domains.cache_info()._asdict(),
                'cache_timeout': self._cache_timeout
            }
        except Exception as e:
            self.logger.error(f"Error getting cache info: {e}")
            return {}
    
    async def create_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Create a new scraping job.
        
        Args:
            job_data: Job configuration data
            
        Returns:
            True if job was created successfully
        """
        try:
            # This would typically call the repository to create a job
            self.logger.info(f"Creating job with URL: {job_data.get('url')}")
            
            # Simulate job creation
            await asyncio.sleep(0.1)  # Simulate async operation
            
            # Clear cache to refresh job lists
            self.clear_cache()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating job: {e}")
            return False
    
    async def update_job_status(self, job_id: str, status: str) -> bool:
        """
        Update job status.
        
        Args:
            job_id: Job identifier
            status: New status
            
        Returns:
            True if update was successful
        """
        try:
            # This would typically call the repository
            self.logger.info(f"Updating job {job_id} status to {status}")
            
            # Simulate update
            await asyncio.sleep(0.1)
            
            # Clear cache to refresh data
            self.clear_cache()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating job status: {e}")
            return False
    
    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if deletion was successful
        """
        try:
            # This would typically call the repository
            self.logger.info(f"Deleting job {job_id}")
            
            # Simulate deletion
            await asyncio.sleep(0.1)
            
            # Clear cache to refresh data
            self.clear_cache()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting job: {e}")
            return False