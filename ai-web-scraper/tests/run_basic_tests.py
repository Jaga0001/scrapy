#!/usr/bin/env python3
"""
Basic test runner for task queue system without external dependencies.

This script runs basic functionality tests for the job queue, worker,
and monitor components to verify the implementation works correctly.
"""

import sys
import os
import traceback
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add src to path and set up proper module structure
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, src_path)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set up package structure
import src
import src.models
import src.pipeline
import src.utils

def test_job_queue_basic():
    """Test basic JobQueue functionality."""
    print("Testing JobQueue basic functionality...")
    
    try:
        from src.pipeline.job_queue import JobQueue
        from src.models.pydantic_models import ScrapingConfig, JobStatus
        
        # Mock Redis to avoid connection
        with patch('redis.from_url') as mock_redis_from_url:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.hset.return_value = True
            mock_client.expire.return_value = True
            mock_client.hgetall.return_value = {}
            mock_redis_from_url.return_value = mock_client
            
            # Test initialization
            queue = JobQueue("redis://localhost:6379/1")
            assert queue.redis_url == "redis://localhost:6379/1"
            
            # Test job creation (without actually submitting to Celery)
            config = ScrapingConfig(wait_time=10, max_retries=2)
            
            # Mock the Celery task to avoid actual submission
            with patch('src.pipeline.worker.scrape_url_task') as mock_task:
                mock_result = Mock()
                mock_result.id = "task-123"
                mock_task.apply_async.return_value = mock_result
                
                job = queue.submit_scraping_job(
                    url="https://example.com",
                    config=config,
                    priority=3
                )
                
                assert job.url == "https://example.com"
                assert job.config.wait_time == 10
                assert job.priority == 3
                assert job.status == JobStatus.PENDING
        
        print("✓ JobQueue basic functionality test passed")
        return True
        
    except Exception as e:
        print(f"✗ JobQueue basic functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_job_monitor_basic():
    """Test basic JobMonitor functionality."""
    print("Testing JobMonitor basic functionality...")
    
    try:
        from src.pipeline.monitor import JobMonitor
        from src.models.pydantic_models import ScrapingJob, JobStatus
        
        # Mock Redis
        with patch('redis.from_url') as mock_redis_from_url:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.hset.return_value = True
            mock_client.expire.return_value = True
            mock_client.info.return_value = {
                "used_memory_human": "1.5M",
                "connected_clients": 3,
                "total_commands_processed": 1000
            }
            mock_redis_from_url.return_value = mock_client
            
            # Test initialization
            monitor = JobMonitor("redis://localhost:6379/1")
            assert monitor.redis_url == "redis://localhost:6379/1"
            assert len(monitor.performance_history) == 0
            assert len(monitor.error_history) == 0
            
            # Test recording job completion
            monitor.record_job_completion("job-123", True, 45.5)
            assert monitor.system_metrics["jobs_processed"] == 1
            assert monitor.system_metrics["jobs_failed"] == 0
            assert len(monitor.performance_history) == 1
            
            # Test recording error
            monitor.record_error("job-123", "NETWORK_ERROR", "Connection timeout")
            assert len(monitor.error_history) == 1
            
            # Test getting system metrics
            with patch('src.pipeline.monitor.celery_app') as mock_celery, \
                 patch('src.pipeline.monitor.get_job_queue') as mock_queue:
                
                mock_queue.return_value.get_queue_stats.return_value = {
                    "total_jobs": 10,
                    "status_counts": {"pending": 2, "running": 1, "completed": 7}
                }
                
                mock_inspect = Mock()
                mock_inspect.stats.return_value = {"worker1": {}}
                mock_inspect.active.return_value = {"worker1": []}
                mock_inspect.scheduled.return_value = {"worker1": []}
                mock_inspect.reserved.return_value = {"worker1": []}
                mock_celery.control.inspect.return_value = mock_inspect
                
                metrics = monitor.get_system_metrics()
                assert "timestamp" in metrics
                assert "queue_stats" in metrics
                assert "worker_stats" in metrics
        
        print("✓ JobMonitor basic functionality test passed")
        return True
        
    except Exception as e:
        print(f"✗ JobMonitor basic functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_worker_tasks_basic():
    """Test basic worker task functionality."""
    print("Testing Worker tasks basic functionality...")
    
    try:
        from src.pipeline.worker import CallbackTask
        from src.models.pydantic_models import JobStatus
        
        # Test CallbackTask
        with patch('src.pipeline.worker.get_job_queue') as mock_queue:
            task = CallbackTask()
            
            # Test on_failure
            task.on_failure(
                exc=Exception("Test error"),
                task_id="task-123",
                args=[],
                kwargs={"job_id": "job-123"},
                einfo=Mock(traceback="test traceback")
            )
            
            mock_queue.return_value.update_job_status.assert_called_once_with(
                "job-123",
                JobStatus.FAILED,
                error_message="Test error"
            )
        
        print("✓ Worker tasks basic functionality test passed")
        return True
        
    except Exception as e:
        print(f"✗ Worker tasks basic functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_circuit_breaker_basic():
    """Test basic CircuitBreaker functionality."""
    print("Testing CircuitBreaker basic functionality...")
    
    try:
        from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
        
        # Test initialization
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
        breaker = CircuitBreaker("test_breaker", config)
        
        assert breaker.name == "test_breaker"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        
        # Test statistics
        stats = breaker.get_stats()
        assert stats["name"] == "test_breaker"
        assert stats["state"] == CircuitState.CLOSED.value
        assert stats["total_requests"] == 0
        
        print("✓ CircuitBreaker basic functionality test passed")
        return True
        
    except Exception as e:
        print(f"✗ CircuitBreaker basic functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_pydantic_models():
    """Test Pydantic models used by the task queue system."""
    print("Testing Pydantic models...")
    
    try:
        from src.models.pydantic_models import ScrapingJob, ScrapingConfig, JobStatus, ScrapedData
        
        # Test ScrapingConfig
        config = ScrapingConfig(wait_time=10, max_retries=3, use_stealth=True)
        assert config.wait_time == 10
        assert config.max_retries == 3
        assert config.use_stealth is True
        
        # Test ScrapingJob
        job = ScrapingJob(
            url="https://example.com",
            config=config,
            priority=5
        )
        assert job.url == "https://example.com"
        assert job.status == JobStatus.PENDING
        assert job.priority == 5
        
        # Test ScrapedData
        data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test Page"}
        )
        assert data.job_id == "job-123"
        assert data.content["title"] == "Test Page"
        assert data.confidence_score == 0.0  # Default value
        
        print("✓ Pydantic models test passed")
        return True
        
    except Exception as e:
        print(f"✗ Pydantic models test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all basic tests."""
    print("Running basic tests for task queue system...")
    print("=" * 50)
    
    tests = [
        test_pydantic_models,
        test_circuit_breaker_basic,
        test_job_queue_basic,
        test_job_monitor_basic,
        test_worker_tasks_basic,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())