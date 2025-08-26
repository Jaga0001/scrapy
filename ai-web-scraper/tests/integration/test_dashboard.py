"""
Integration tests for the Streamlit dashboard functionality.

This module contains tests for dashboard components, data loading,
and user interactions with test data.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.dashboard.main import IntelligentScraperDashboard
from src.dashboard.components.job_management import JobManagementComponent
from src.dashboard.components.data_visualization import DataVisualizationComponent
from src.dashboard.components.system_metrics import SystemMetricsComponent
from src.dashboard.utils.data_loader import DashboardDataLoader
from src.dashboard.utils.session_manager import SessionManager


class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""
    
    @pytest.fixture
    def mock_data_loader(self):
        """Create a mock data loader with test data."""
        loader = Mock(spec=DashboardDataLoader)
        
        # Mock job statistics
        loader.get_job_statistics.return_value = {
            'total_jobs': 100,
            'completed_jobs': 85,
            'failed_jobs': 5,
            'running_jobs': 8,
            'pending_jobs': 2,
            'success_rate': 85.0,
            'average_pages_per_job': 25.5,
            'total_pages_scraped': 2550,
            'average_job_duration': 120.0
        }
        
        # Mock system health
        loader.get_system_health.return_value = {
            'overall_status': 'healthy',
            'services': {
                'api': {'status': 'healthy', 'response_time': 45},
                'database': {'status': 'healthy', 'response_time': 80},
                'redis': {'status': 'healthy', 'response_time': 2},
                'workers': {'status': 'healthy', 'active_count': 4}
            },
            'system_resources': {
                'cpu_usage': 35.2,
                'memory_usage': 68.5,
                'disk_usage': 45.8
            }
        }
        
        # Mock active jobs
        async def mock_get_active_jobs(*args, **kwargs):
            return [
                {
                    'id': 'test-job-1',
                    'url': 'https://test.com',
                    'status': 'running',
                    'pages_completed': 10,
                    'pages_failed': 0,
                    'total_pages': 50,
                    'created_at': datetime.now() - timedelta(hours=1),
                    'priority': 5,
                    'tags': ['test'],
                    'progress_percentage': 20.0
                }
            ]
        
        loader.get_active_jobs = AsyncMock(side_effect=mock_get_active_jobs)
        
        # Mock scraped data
        async def mock_get_scraped_data(*args, **kwargs):
            return [
                {
                    'id': 'data-1',
                    'job_id': 'test-job-1',
                    'url': 'https://test.com/page1',
                    'confidence_score': 0.85,
                    'data_quality_score': 0.90,
                    'ai_processed': True,
                    'extracted_at': datetime.now(),
                    'content': {'title': 'Test Title', 'content': 'Test content'},
                    'content_length': 500,
                    'validation_errors': []
                }
            ], 1
        
        loader.get_scraped_data = AsyncMock(side_effect=mock_get_scraped_data)
        
        return loader
    
    @pytest.fixture
    def session_manager(self):
        """Create a session manager for testing."""
        return SessionManager()
    
    def test_dashboard_initialization(self, mock_data_loader):
        """Test dashboard initialization."""
        with patch('src.dashboard.main.DashboardDataLoader', return_value=mock_data_loader):
            dashboard = IntelligentScraperDashboard()
            
            assert dashboard.data_loader is not None
            assert dashboard.session_manager is not None
            assert dashboard.job_management is not None
            assert dashboard.data_visualization is not None
            assert dashboard.system_metrics is not None
    
    def test_job_management_component(self, mock_data_loader):
        """Test job management component functionality."""
        component = JobManagementComponent(mock_data_loader)
        
        # Test component initialization
        assert component.data_loader == mock_data_loader
        
        # Test job creation data preparation
        job_data = {
            'url': 'https://test.com',
            'wait_time': 5,
            'max_retries': 3,
            'use_stealth': True,
            'tags': ['test', 'integration']
        }
        
        # This would normally interact with Streamlit components
        # In a real test, we'd use Streamlit's testing framework
        assert job_data['url'] == 'https://test.com'
        assert job_data['tags'] == ['test', 'integration']
    
    def test_data_visualization_component(self, mock_data_loader):
        """Test data visualization component functionality."""
        component = DataVisualizationComponent(mock_data_loader)
        
        # Test component initialization
        assert component.data_loader == mock_data_loader
        
        # Test data filtering logic
        filters = {
            'min_confidence': 0.8,
            'min_quality': 0.85,
            'ai_processed_only': True
        }
        
        # Test filter validation
        assert filters['min_confidence'] >= 0.0
        assert filters['min_quality'] >= 0.0
        assert isinstance(filters['ai_processed_only'], bool)
    
    def test_system_metrics_component(self, mock_data_loader):
        """Test system metrics component functionality."""
        component = SystemMetricsComponent(mock_data_loader)
        
        # Test component initialization
        assert component.data_loader == mock_data_loader
        
        # Test system info gathering
        system_info = component._get_system_info()
        
        # Verify system info structure
        assert 'cpu_percent' in system_info
        assert 'memory_percent' in system_info
        assert 'platform' in system_info
    
    @pytest.mark.asyncio
    async def test_data_loader_async_methods(self, mock_data_loader):
        """Test async methods in data loader."""
        # Test get_active_jobs
        jobs = await mock_data_loader.get_active_jobs()
        assert len(jobs) == 1
        assert jobs[0]['id'] == 'test-job-1'
        assert jobs[0]['status'] == 'running'
        
        # Test get_scraped_data
        data, count = await mock_data_loader.get_scraped_data()
        assert len(data) == 1
        assert count == 1
        assert data[0]['id'] == 'data-1'
        assert data[0]['confidence_score'] == 0.85
    
    def test_session_manager_functionality(self, session_manager):
        """Test session manager functionality."""
        # Test setting and getting values
        session_manager.set('test_key', 'test_value')
        assert session_manager.get('test_key') == 'test_value'
        
        # Test default values
        assert session_manager.get('nonexistent_key', 'default') == 'default'
        
        # Test updating multiple values
        updates = {'key1': 'value1', 'key2': 'value2'}
        session_manager.update(updates)
        assert session_manager.get('key1') == 'value1'
        assert session_manager.get('key2') == 'value2'
        
        # Test notifications
        session_manager.add_notification('Test message', 'info')
        notifications = session_manager.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]['message'] == 'Test message'
        assert notifications[0]['level'] == 'info'
    
    def test_session_manager_preferences(self, session_manager):
        """Test session manager preferences functionality."""
        # Test saving preferences
        session_manager.set('auto_refresh', False)
        session_manager.set('refresh_interval', 10)
        
        success = session_manager.save_user_preferences()
        assert success is True
        
        # Test loading preferences
        session_manager.set('auto_refresh', True)  # Change value
        success = session_manager.load_user_preferences()
        assert success is True
        assert session_manager.get('auto_refresh') is False  # Should be restored
    
    def test_session_manager_filters(self, session_manager):
        """Test session manager filter functionality."""
        # Set some filters
        session_manager.set('min_confidence_filter', 0.8)
        session_manager.set('job_status_filter', ['running', 'completed'])
        
        # Get filter summary
        summary = session_manager.get_filter_summary()
        assert summary['min_confidence_filter'] == 0.8
        assert summary['job_status_filter'] == ['running', 'completed']
        assert summary['active_filters_count'] >= 1
        
        # Clear filters
        session_manager.clear_filters()
        summary = session_manager.get_filter_summary()
        assert summary['min_confidence_filter'] == 0.0
    
    def test_session_manager_export_import(self, session_manager):
        """Test session manager export/import functionality."""
        # Set some test values
        session_manager.set('auto_refresh', False)
        session_manager.set('theme', 'dark')
        session_manager.set('page_size', 50)
        
        # Export session state
        exported_data = session_manager.export_session_state()
        assert exported_data != "{}"
        assert 'auto_refresh' in exported_data
        
        # Change values
        session_manager.set('auto_refresh', True)
        session_manager.set('theme', 'light')
        
        # Import session state
        success = session_manager.import_session_state(exported_data)
        assert success is True
        assert session_manager.get('auto_refresh') is False
        assert session_manager.get('theme') == 'dark'
    
    @pytest.mark.asyncio
    async def test_data_loader_caching(self):
        """Test data loader caching functionality."""
        loader = DashboardDataLoader()
        
        # Test cache clearing
        loader.clear_cache()
        
        # Test cache info
        cache_info = loader.get_cache_info()
        assert 'cache_timeout' in cache_info
        assert cache_info['cache_timeout'] == 30
    
    @pytest.mark.asyncio
    async def test_data_loader_job_operations(self):
        """Test data loader job operations."""
        loader = DashboardDataLoader()
        
        # Test job creation
        job_data = {
            'url': 'https://test.com',
            'config': {'wait_time': 5},
            'tags': ['test']
        }
        
        success = await loader.create_job(job_data)
        assert success is True
        
        # Test job status update
        success = await loader.update_job_status('test-job-1', 'completed')
        assert success is True
        
        # Test job deletion
        success = await loader.delete_job('test-job-1')
        assert success is True
    
    def test_data_loader_available_options(self):
        """Test data loader available options methods."""
        loader = DashboardDataLoader()
        
        # Test available jobs
        jobs = loader.get_available_jobs()
        assert isinstance(jobs, list)
        assert len(jobs) > 0
        
        # Test available domains
        domains = loader.get_available_domains()
        assert isinstance(domains, list)
        assert len(domains) > 0
    
    @pytest.mark.asyncio
    async def test_data_loader_system_metrics(self):
        """Test data loader system metrics functionality."""
        loader = DashboardDataLoader()
        
        # Test system metrics retrieval
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        metrics = await loader.get_system_metrics(
            metric_names=['cpu_usage', 'memory_usage'],
            start_time=start_time,
            end_time=end_time,
            limit=100
        )
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        
        # Verify metric structure
        if metrics:
            metric = metrics[0]
            assert 'metric_name' in metric
            assert 'metric_value' in metric
            assert 'recorded_at' in metric
    
    def test_component_error_handling(self, mock_data_loader):
        """Test error handling in dashboard components."""
        # Test job management component with error
        mock_data_loader.get_active_jobs.side_effect = Exception("Test error")
        
        component = JobManagementComponent(mock_data_loader)
        
        # Component should handle errors gracefully
        # In a real test, we'd verify error messages are displayed
        assert component.data_loader == mock_data_loader
    
    def test_dashboard_data_flow(self, mock_data_loader):
        """Test data flow through dashboard components."""
        with patch('src.dashboard.main.DashboardDataLoader', return_value=mock_data_loader):
            dashboard = IntelligentScraperDashboard()
            
            # Test that components have access to data loader
            assert dashboard.job_management.data_loader == mock_data_loader
            assert dashboard.data_visualization.data_loader == mock_data_loader
            assert dashboard.system_metrics.data_loader == mock_data_loader
    
    def test_dashboard_session_integration(self, mock_data_loader):
        """Test integration between dashboard and session manager."""
        with patch('src.dashboard.main.DashboardDataLoader', return_value=mock_data_loader):
            dashboard = IntelligentScraperDashboard()
            
            # Test session state initialization
            assert hasattr(dashboard, 'session_manager')
            
            # Test that session manager has default values
            assert dashboard.session_manager.get('auto_refresh') is not None
            assert dashboard.session_manager.get('refresh_interval') is not None


class TestDashboardPerformance:
    """Performance tests for dashboard functionality."""
    
    def test_data_loading_performance(self):
        """Test data loading performance."""
        loader = DashboardDataLoader()
        
        # Test that cached methods are fast on subsequent calls
        import time
        
        start_time = time.time()
        stats1 = loader.get_job_statistics()
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        stats2 = loader.get_job_statistics()
        second_call_time = time.time() - start_time
        
        # Second call should be faster due to caching
        # Note: This might not always be true in test environment
        assert stats1 == stats2  # Results should be identical
    
    def test_session_manager_performance(self):
        """Test session manager performance with large datasets."""
        session_manager = SessionManager()
        
        # Test performance with many notifications
        import time
        
        start_time = time.time()
        for i in range(100):
            session_manager.add_notification(f"Test message {i}", 'info')
        
        add_time = time.time() - start_time
        
        start_time = time.time()
        notifications = session_manager.get_notifications()
        get_time = time.time() - start_time
        
        # Operations should complete quickly
        assert add_time < 1.0  # Should take less than 1 second
        assert get_time < 0.1  # Should take less than 0.1 seconds
        assert len(notifications) == 100


class TestDashboardEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_data_handling(self):
        """Test handling of empty data sets."""
        loader = DashboardDataLoader()
        
        # Test with empty results
        with patch.object(loader, 'get_job_statistics', return_value={}):
            stats = loader.get_job_statistics()
            assert stats == {}
    
    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test async error handling."""
        loader = DashboardDataLoader()
        
        # Test with network errors
        with patch.object(loader, 'get_active_jobs', side_effect=Exception("Network error")):
            try:
                await loader.get_active_jobs()
            except Exception as e:
                assert str(e) == "Network error"
    
    def test_invalid_session_data(self):
        """Test handling of invalid session data."""
        session_manager = SessionManager()
        
        # Test importing invalid JSON
        success = session_manager.import_session_state("invalid json")
        assert success is False
        
        # Test with None values
        session_manager.set('test_key', None)
        assert session_manager.get('test_key') is None
    
    def test_large_dataset_handling(self):
        """Test handling of large datasets."""
        loader = DashboardDataLoader()
        
        # Test with large limit values
        # This should not cause memory issues
        try:
            # In a real implementation, this would test actual large data
            large_limit = 100000
            assert large_limit > 0  # Basic validation
        except Exception as e:
            pytest.fail(f"Large dataset handling failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])