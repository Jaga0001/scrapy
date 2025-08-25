"""
Unit tests for the job monitoring system.

This module contains tests for the JobMonitor class that handles
job progress tracking, performance metrics, and system health monitoring.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from collections import deque

from src.pipeline.monitor import JobMonitor, job_monitor
from src.models.pydantic_models import JobStatus, ScrapingJob


class TestJobMonitor:
    """Test cases for the JobMonitor class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing."""
        with patch('redis.from_url') as mock_redis_from_url:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_client.hset.return_value = True
            mock_client.expire.return_value = True
            mock_client.hgetall.return_value = {}
            mock_client.keys.return_value = []
            mock_client.info.return_value = {
                "used_memory_human": "2.1M",
                "connected_clients": 3,
                "total_commands_processed": 5000
            }
            mock_redis_from_url.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def monitor_instance(self, mock_redis):
        """Create JobMonitor instance for testing."""
        return JobMonitor("redis://localhost:6379/1")
    
    def test_monitor_initialization(self, mock_redis):
        """Test JobMonitor initialization."""
        monitor = JobMonitor("redis://localhost:6379/1")
        
        assert monitor.redis_url == "redis://localhost:6379/1"
        assert len(monitor.performance_history) == 0
        assert len(monitor.error_history) == 0
        assert monitor.system_metrics["jobs_processed"] == 0
        assert monitor.system_metrics["jobs_failed"] == 0
        assert isinstance(monitor.system_metrics["uptime_start"], datetime)
        
        # Verify Redis connection test
        mock_redis.ping.assert_called_once()
    
    @patch('src.pipeline.monitor.job_queue')
    def test_get_job_progress_running_job(self, mock_job_queue, monitor_instance, mock_redis):
        """Test getting progress for a running job."""
        # Mock job data
        start_time = datetime.utcnow() - timedelta(minutes=10)
        mock_job = ScrapingJob(
            id="job-123",
            url="https://example.com",
            status=JobStatus.RUNNING,
            total_pages=20,
            pages_completed=8,
            pages_failed=1,
            started_at=start_time,
            created_at=start_time - timedelta(minutes=5)
        )
        mock_job_queue.get_job_status.return_value = mock_job
        
        # Mock Redis job data with Celery task ID
        mock_redis.hgetall.return_value = {"celery_task_id": "task-456"}
        
        # Mock Celery task info
        with patch.object(monitor_instance, '_get_celery_task_info') as mock_celery_info:
            mock_celery_info.return_value = {
                "worker": "worker1",
                "state": "ACTIVE",
                "task_info": {"name": "scrape_url_task"}
            }
            
            progress = monitor_instance.get_job_progress("job-123")
        
        assert progress["job_id"] == "job-123"
        assert progress["status"] == JobStatus.RUNNING.value
        assert progress["progress_percentage"] == 40.0  # 8/20 * 100
        assert progress["pages_completed"] == 8
        assert progress["pages_failed"] == 1
        assert progress["total_pages"] == 20
        assert "estimated_completion" in progress
        assert progress["celery_task_info"]["worker"] == "worker1"
    
    @patch('src.pipeline.monitor.job_queue')
    def test_get_job_progress_completed_job(self, mock_job_queue, monitor_instance):
        """Test getting progress for a completed job."""
        mock_job = ScrapingJob(
            id="job-123",
            url="https://example.com",
            status=JobStatus.COMPLETED,
            total_pages=10,
            pages_completed=10,
            pages_failed=0,
            completed_at=datetime.utcnow()
        )
        mock_job_queue.get_job_status.return_value = mock_job
        
        progress = monitor_instance.get_job_progress("job-123")
        
        assert progress["status"] == JobStatus.COMPLETED.value
        assert progress["progress_percentage"] == 100.0
        assert progress["estimated_completion"] is None
        assert progress["completed_at"] is not None
    
    @patch('src.pipeline.monitor.job_queue')
    def test_get_job_progress_nonexistent_job(self, mock_job_queue, monitor_instance):
        """Test getting progress for non-existent job."""
        mock_job_queue.get_job_status.return_value = None
        
        progress = monitor_instance.get_job_progress("nonexistent")
        
        assert "error" in progress
        assert progress["error"] == "Job not found"
    
    @patch('src.pipeline.monitor.celery_app')
    @patch('src.pipeline.monitor.job_queue')
    def test_get_system_metrics(self, mock_job_queue, mock_celery_app, monitor_instance, mock_redis):
        """Test getting comprehensive system metrics."""
        # Mock queue stats
        mock_job_queue.get_queue_stats.return_value = {
            "total_jobs": 100,
            "status_counts": {
                "pending": 15,
                "running": 5,
                "completed": 75,
                "failed": 5
            },
            "active_tasks": 3,
            "scheduled_tasks": 2,
            "reserved_tasks": 1,
            "redis_connected": True
        }
        
        # Mock Celery inspect
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {"worker1": {}, "worker2": {}}
        mock_inspect.active.return_value = {"worker1": [{"id": "task1"}, {"id": "task2"}]}
        mock_inspect.scheduled.return_value = {"worker1": [{"id": "task3"}]}
        mock_inspect.reserved.return_value = {"worker1": []}
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        # Add some performance history
        monitor_instance.system_metrics["jobs_processed"] = 50
        monitor_instance.system_metrics["jobs_failed"] = 3
        monitor_instance.system_metrics["average_processing_time"] = 25.5
        
        metrics = monitor_instance.get_system_metrics()
        
        assert "timestamp" in metrics
        assert "uptime_seconds" in metrics
        assert metrics["queue_stats"]["total_jobs"] == 100
        assert metrics["worker_stats"]["active_workers"] == 2
        assert metrics["worker_stats"]["total_active_tasks"] == 2
        assert metrics["worker_stats"]["total_scheduled_tasks"] == 1
        assert metrics["performance_metrics"]["jobs_processed_total"] == 50
        assert metrics["performance_metrics"]["jobs_failed_total"] == 3
        assert metrics["performance_metrics"]["average_processing_time"] == 25.5
        assert "health_status" in metrics
        assert "redis_info" in metrics
    
    @patch('src.pipeline.monitor.job_queue')
    def test_get_active_jobs_summary(self, mock_job_queue, monitor_instance):
        """Test getting active jobs summary."""
        # Mock active jobs
        mock_jobs = [
            ScrapingJob(
                id="job-1",
                url="https://example1.com",
                status=JobStatus.RUNNING,
                priority=1,
                total_pages=10,
                pages_completed=7,
                created_at=datetime.utcnow() - timedelta(minutes=5)
            ),
            ScrapingJob(
                id="job-2",
                url="https://example2.com",
                status=JobStatus.PENDING,
                priority=3,
                total_pages=5,
                pages_completed=0,
                created_at=datetime.utcnow() - timedelta(minutes=2)
            ),
            ScrapingJob(
                id="job-3",
                url="https://example3.com",
                status=JobStatus.RUNNING,
                priority=2,
                total_pages=8,
                pages_completed=3,
                created_at=datetime.utcnow() - timedelta(minutes=8),
                started_at=datetime.utcnow() - timedelta(minutes=3)
            )
        ]
        mock_job_queue.get_active_jobs.return_value = mock_jobs
        
        summary = monitor_instance.get_active_jobs_summary()
        
        assert summary["total_active"] == 3
        assert summary["by_status"]["running"] == 2
        assert summary["by_status"]["pending"] == 1
        assert summary["by_priority"][1] == 1
        assert summary["by_priority"][2] == 1
        assert summary["by_priority"][3] == 1
        
        assert len(summary["jobs"]) == 3
        
        # Check progress calculations
        job_1 = next(job for job in summary["jobs"] if job["job_id"] == "job-1")
        assert job_1["progress_percentage"] == 70.0  # 7/10 * 100
        
        job_2 = next(job for job in summary["jobs"] if job["job_id"] == "job-2")
        assert job_2["progress_percentage"] == 0.0  # 0/5 * 100
        
        job_3 = next(job for job in summary["jobs"] if job["job_id"] == "job-3")
        assert job_3["progress_percentage"] == 37.5  # 3/8 * 100
    
    def test_record_job_completion_success(self, monitor_instance, mock_redis):
        """Test recording successful job completion."""
        monitor_instance.record_job_completion("job-123", True, 45.5)
        
        # Check system metrics updates
        assert monitor_instance.system_metrics["jobs_processed"] == 1
        assert monitor_instance.system_metrics["jobs_failed"] == 0
        assert monitor_instance.system_metrics["total_processing_time"] == 45.5
        assert monitor_instance.system_metrics["average_processing_time"] == 45.5
        
        # Check performance history
        assert len(monitor_instance.performance_history) == 1
        metric = monitor_instance.performance_history[0]
        assert metric["job_id"] == "job-123"
        assert metric["success"] is True
        assert metric["processing_time"] == 45.5
        
        # Verify Redis storage
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
    
    def test_record_job_completion_failure(self, monitor_instance, mock_redis):
        """Test recording failed job completion."""
        monitor_instance.record_job_completion("job-123", False, 30.0)
        
        assert monitor_instance.system_metrics["jobs_processed"] == 1
        assert monitor_instance.system_metrics["jobs_failed"] == 1
        assert monitor_instance.system_metrics["total_processing_time"] == 30.0
        
        metric = monitor_instance.performance_history[0]
        assert metric["success"] is False
    
    def test_record_multiple_job_completions(self, monitor_instance, mock_redis):
        """Test recording multiple job completions and average calculation."""
        monitor_instance.record_job_completion("job-1", True, 20.0)
        monitor_instance.record_job_completion("job-2", True, 40.0)
        monitor_instance.record_job_completion("job-3", False, 10.0)
        
        assert monitor_instance.system_metrics["jobs_processed"] == 3
        assert monitor_instance.system_metrics["jobs_failed"] == 1
        assert monitor_instance.system_metrics["total_processing_time"] == 70.0
        assert monitor_instance.system_metrics["average_processing_time"] == 70.0 / 3
    
    def test_record_error(self, monitor_instance, mock_redis):
        """Test recording error information."""
        monitor_instance.record_error("job-123", "NETWORK_ERROR", "Connection timeout after 30s")
        
        assert len(monitor_instance.error_history) == 1
        error = monitor_instance.error_history[0]
        assert error["job_id"] == "job-123"
        assert error["error_type"] == "NETWORK_ERROR"
        assert error["error_message"] == "Connection timeout after 30s"
        assert isinstance(error["timestamp"], datetime)
        
        # Verify Redis storage
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
    
    def test_get_performance_history(self, monitor_instance):
        """Test getting performance history with time filtering."""
        # Add test metrics spanning different time periods
        now = datetime.utcnow()
        test_metrics = [
            {
                "timestamp": now - timedelta(hours=0.5),  # 30 minutes ago
                "job_id": "job-1",
                "success": True,
                "processing_time": 25.0
            },
            {
                "timestamp": now - timedelta(hours=2),  # 2 hours ago
                "job_id": "job-2",
                "success": True,
                "processing_time": 35.0
            },
            {
                "timestamp": now - timedelta(hours=3),  # 3 hours ago
                "job_id": "job-3",
                "success": False,
                "processing_time": 15.0
            },
            {
                "timestamp": now - timedelta(hours=25),  # 25 hours ago (should be excluded)
                "job_id": "job-4",
                "success": True,
                "processing_time": 20.0
            }
        ]
        
        monitor_instance.performance_history.extend(test_metrics)
        
        # Get 24-hour history
        history = monitor_instance.get_performance_history(hours=24)
        
        assert history["hours_requested"] == 24
        assert len(history["history"]) > 0
        
        # Verify aggregation (should include first 3 metrics, exclude the 25-hour old one)
        total_jobs_in_history = sum(hour_data["jobs_processed"] for hour_data in history["history"])
        assert total_jobs_in_history == 3
    
    def test_get_performance_history_empty(self, monitor_instance):
        """Test getting performance history when no data exists."""
        history = monitor_instance.get_performance_history(hours=24)
        
        assert history["hours_requested"] == 24
        assert history["data_points"] == 0
        assert history["history"] == []
    
    def test_get_recent_performance_metrics(self, monitor_instance):
        """Test getting recent performance metrics."""
        # Add recent metrics
        now = datetime.utcnow()
        recent_metrics = [
            {
                "timestamp": now - timedelta(minutes=10),
                "job_id": "job-1",
                "success": True,
                "processing_time": 20.0
            },
            {
                "timestamp": now - timedelta(minutes=20),
                "job_id": "job-2",
                "success": True,
                "processing_time": 30.0
            },
            {
                "timestamp": now - timedelta(minutes=30),
                "job_id": "job-3",
                "success": False,
                "processing_time": 15.0
            }
        ]
        
        monitor_instance.performance_history.extend(recent_metrics)
        
        # Get recent metrics (last 60 minutes)
        metrics = monitor_instance._get_recent_performance_metrics(minutes=60)
        
        assert metrics["throughput"] == 3.0  # 3 jobs in 1 hour
        assert metrics["avg_processing_time"] == (20.0 + 30.0 + 15.0) / 3
    
    def test_calculate_error_rate(self, monitor_instance):
        """Test error rate calculation."""
        # Add metrics with mixed success/failure
        now = datetime.utcnow()
        metrics = [
            {"timestamp": now - timedelta(hours=1), "success": True, "processing_time": 20.0},
            {"timestamp": now - timedelta(hours=2), "success": False, "processing_time": 15.0},
            {"timestamp": now - timedelta(hours=3), "success": True, "processing_time": 25.0},
            {"timestamp": now - timedelta(hours=4), "success": False, "processing_time": 10.0},
            {"timestamp": now - timedelta(hours=5), "success": True, "processing_time": 30.0},
        ]
        
        monitor_instance.performance_history.extend(metrics)
        
        # Calculate error rate for last 24 hours
        error_rate = monitor_instance._calculate_error_rate(hours=24)
        
        # 2 failures out of 5 total = 40%
        assert error_rate == 40.0
    
    def test_get_health_status_healthy(self, monitor_instance, mock_redis):
        """Test health status when system is healthy."""
        # Mock healthy conditions
        mock_redis.ping.return_value = True
        
        with patch('src.pipeline.monitor.celery_app') as mock_celery:
            mock_inspect = Mock()
            mock_inspect.stats.return_value = {"worker1": {}}
            mock_celery.control.inspect.return_value = mock_inspect
            
            # Add low error rate
            monitor_instance.performance_history.extend([
                {"timestamp": datetime.utcnow(), "success": True, "processing_time": 20.0},
                {"timestamp": datetime.utcnow(), "success": True, "processing_time": 25.0}
            ])
            
            status = monitor_instance._get_health_status()
            assert status == "HEALTHY"
    
    def test_get_health_status_degraded(self, monitor_instance, mock_redis):
        """Test health status when system is degraded."""
        mock_redis.ping.return_value = True
        
        with patch('src.pipeline.monitor.celery_app') as mock_celery:
            mock_inspect = Mock()
            mock_inspect.stats.return_value = {"worker1": {}}
            mock_celery.control.inspect.return_value = mock_inspect
            
            # Add high error rate (30%)
            now = datetime.utcnow()
            monitor_instance.performance_history.extend([
                {"timestamp": now, "success": True, "processing_time": 20.0},
                {"timestamp": now, "success": False, "processing_time": 15.0},
                {"timestamp": now, "success": False, "processing_time": 10.0},
                {"timestamp": now, "success": True, "processing_time": 25.0},
                {"timestamp": now, "success": False, "processing_time": 12.0},
            ])
            
            status = monitor_instance._get_health_status()
            assert status == "DEGRADED"
    
    def test_get_health_status_unhealthy_no_workers(self, monitor_instance, mock_redis):
        """Test health status when no workers are active."""
        mock_redis.ping.return_value = True
        
        with patch('src.pipeline.monitor.celery_app') as mock_celery:
            mock_inspect = Mock()
            mock_inspect.stats.return_value = {}  # No workers
            mock_celery.control.inspect.return_value = mock_inspect
            
            status = monitor_instance._get_health_status()
            assert status == "DEGRADED"
    
    def test_get_health_status_unhealthy_redis_down(self, monitor_instance, mock_redis):
        """Test health status when Redis is down."""
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        status = monitor_instance._get_health_status()
        assert status == "UNHEALTHY"
    
    def test_get_redis_info_connected(self, monitor_instance, mock_redis):
        """Test getting Redis info when connected."""
        info = monitor_instance._get_redis_info()
        
        assert info["connected"] is True
        assert info["used_memory"] == "2.1M"
        assert info["connected_clients"] == 3
        assert info["total_commands_processed"] == 5000
    
    def test_get_redis_info_disconnected(self, monitor_instance, mock_redis):
        """Test getting Redis info when disconnected."""
        mock_redis.info.side_effect = Exception("Connection failed")
        
        info = monitor_instance._get_redis_info()
        
        assert info["connected"] is False
        assert "error" in info
    
    def test_get_celery_task_info_active_task(self, monitor_instance):
        """Test getting Celery task info for active task."""
        with patch('src.pipeline.monitor.celery_app') as mock_celery:
            mock_inspect = Mock()
            mock_inspect.active.return_value = {
                "worker1": [
                    {"id": "task-123", "name": "scrape_url_task", "args": [], "kwargs": {}}
                ]
            }
            mock_inspect.scheduled.return_value = {}
            mock_inspect.reserved.return_value = {}
            mock_celery.control.inspect.return_value = mock_inspect
            
            task_info = monitor_instance._get_celery_task_info("task-123")
            
            assert task_info is not None
            assert task_info["worker"] == "worker1"
            assert task_info["state"] == "ACTIVE"
            assert task_info["task_info"]["name"] == "scrape_url_task"
    
    def test_get_celery_task_info_not_found(self, monitor_instance):
        """Test getting Celery task info for non-existent task."""
        with patch('src.pipeline.monitor.celery_app') as mock_celery:
            mock_inspect = Mock()
            mock_inspect.active.return_value = {}
            mock_inspect.scheduled.return_value = {}
            mock_inspect.reserved.return_value = {}
            mock_celery.control.inspect.return_value = mock_inspect
            
            task_info = monitor_instance._get_celery_task_info("nonexistent-task")
            
            assert task_info is None


class TestJobMonitorEventHandlers:
    """Test cases for Celery event handlers."""
    
    @pytest.fixture
    def monitor_instance(self):
        """Create JobMonitor instance for testing event handlers."""
        with patch('redis.from_url'):
            return JobMonitor("redis://localhost:6379/1")
    
    def test_on_task_succeeded(self, monitor_instance):
        """Test task succeeded event handler."""
        event = {
            "uuid": "task-123",
            "name": "scrape_url_task",
            "runtime": 25.5
        }
        
        with patch.object(monitor_instance, 'record_job_completion') as mock_record:
            monitor_instance._on_task_succeeded(event)
            mock_record.assert_called_once_with("task-123", True, 25.5)
    
    def test_on_task_failed(self, monitor_instance):
        """Test task failed event handler."""
        event = {
            "uuid": "task-123",
            "name": "scrape_url_task",
            "runtime": 15.0,
            "exception": "Network timeout"
        }
        
        with patch.object(monitor_instance, 'record_job_completion') as mock_record_completion, \
             patch.object(monitor_instance, 'record_error') as mock_record_error:
            
            monitor_instance._on_task_failed(event)
            
            mock_record_completion.assert_called_once_with("task-123", False, 15.0)
            mock_record_error.assert_called_once_with("task-123", "TASK_FAILED", "Network timeout")
    
    def test_on_task_failed_no_exception(self, monitor_instance):
        """Test task failed event handler without exception info."""
        event = {
            "uuid": "task-123",
            "name": "scrape_url_task",
            "runtime": 10.0
        }
        
        with patch.object(monitor_instance, 'record_job_completion') as mock_record_completion, \
             patch.object(monitor_instance, 'record_error') as mock_record_error:
            
            monitor_instance._on_task_failed(event)
            
            mock_record_completion.assert_called_once_with("task-123", False, 10.0)
            mock_record_error.assert_called_once_with("task-123", "TASK_FAILED", "Unknown error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])