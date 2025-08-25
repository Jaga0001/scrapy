"""
Unit tests for the job queue system.

This module contains comprehensive tests for the Celery-based task queue
system including job submission, monitoring, and worker operations.
"""

import asyncio
import pytest
import redis
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.pipeline.job_queue import JobQueue, celery_app, job_queue
from src.pipeline.worker import scrape_url_task, process_content_task, clean_data_task
from src.pipeline.monitor import JobMonitor, job_monitor
from src.models.pydantic_models import JobStatus, ScrapingConfig, ScrapingJob, ScrapedData


class TestJobQueue:
    """Test cases for JobQueue class."""
    
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
            mock_client.delete.return_value = True
            mock_redis_from_url.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def job_queue_instance(self, mock_redis):
        """Create JobQueue instance for testing."""
        return JobQueue("redis://localhost:6379/1")
    
    def test_job_queue_initialization(self, mock_redis):
        """Test JobQueue initialization."""
        queue = JobQueue("redis://localhost:6379/1")
        assert queue.redis_url == "redis://localhost:6379/1"
        mock_redis.ping.assert_called_once()
    
    def test_job_queue_redis_connection_failure(self):
        """Test JobQueue initialization with Redis connection failure."""
        with patch('redis.from_url') as mock_redis_from_url:
            mock_client = Mock()
            mock_client.ping.side_effect = redis.ConnectionError("Connection failed")
            mock_redis_from_url.return_value = mock_client
            
            with pytest.raises(redis.ConnectionError):
                JobQueue("redis://localhost:6379/1")
    
    @patch('src.pipeline.job_queue.scrape_url_task')
    def test_submit_scraping_job(self, mock_task, job_queue_instance, mock_redis):
        """Test submitting a scraping job."""
        # Mock Celery task
        mock_result = Mock()
        mock_result.id = "task-123"
        mock_task.apply_async.return_value = mock_result
        
        # Submit job
        config = ScrapingConfig(wait_time=10, max_retries=2)
        job = job_queue_instance.submit_scraping_job(
            url="https://example.com",
            config=config,
            priority=3
        )
        
        # Verify job creation
        assert job.url == "https://example.com"
        assert job.config.wait_time == 10
        assert job.priority == 3
        assert job.status == JobStatus.PENDING
        
        # Verify Redis operations
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
        
        # Verify Celery task submission
        mock_task.apply_async.assert_called_once()
    
    def test_submit_scraping_job_with_default_config(self, job_queue_instance, mock_redis):
        """Test submitting a job with default configuration."""
        with patch('src.pipeline.job_queue.scrape_url_task') as mock_task:
            mock_result = Mock()
            mock_result.id = "task-123"
            mock_task.apply_async.return_value = mock_result
            
            job = job_queue_instance.submit_scraping_job("https://example.com")
            
            assert job.config.wait_time == 5  # Default value
            assert job.priority == 5  # Default value
    
    def test_submit_scraping_job_with_eta(self, job_queue_instance, mock_redis):
        """Test submitting a job with estimated time of arrival."""
        with patch('src.pipeline.job_queue.scrape_url_task') as mock_task:
            mock_result = Mock()
            mock_result.id = "task-123"
            mock_task.apply_async.return_value = mock_result
            
            eta = datetime.utcnow() + timedelta(minutes=30)
            job = job_queue_instance.submit_scraping_job(
                "https://example.com",
                eta=eta
            )
            
            # Verify ETA was passed to Celery
            call_kwargs = mock_task.apply_async.call_args[1]
            assert "eta" in call_kwargs
    
    def test_get_job_status_existing_job(self, job_queue_instance, mock_redis):
        """Test getting status of an existing job."""
        # Mock Redis data
        job_data = {
            "id": "job-123",
            "url": "https://example.com",
            "config": ScrapingConfig().model_dump_json(),
            "status": JobStatus.RUNNING.value,
            "created_at": datetime.utcnow().isoformat(),
            "priority": "5",
            "retry_count": "0",
            "started_at": datetime.utcnow().isoformat(),
            "total_pages": "10",
            "pages_completed": "5"
        }
        mock_redis.hgetall.return_value = job_data
        
        job = job_queue_instance.get_job_status("job-123")
        
        assert job is not None
        assert job.id == "job-123"
        assert job.status == JobStatus.RUNNING
        assert job.total_pages == 10
        assert job.pages_completed == 5
    
    def test_get_job_status_nonexistent_job(self, job_queue_instance, mock_redis):
        """Test getting status of a non-existent job."""
        mock_redis.hgetall.return_value = {}
        
        job = job_queue_instance.get_job_status("nonexistent-job")
        
        assert job is None
    
    def test_update_job_status(self, job_queue_instance, mock_redis):
        """Test updating job status."""
        success = job_queue_instance.update_job_status(
            "job-123",
            JobStatus.COMPLETED,
            error_message=None,
            pages_completed=10
        )
        
        assert success is True
        mock_redis.hset.assert_called()
        
        # Verify update data includes status and completion time
        call_args = mock_redis.hset.call_args[1]
        update_data = call_args["mapping"]
        assert update_data["status"] == JobStatus.COMPLETED.value
        assert "completed_at" in update_data
        assert update_data["pages_completed"] == "10"
    
    def test_update_job_status_with_error(self, job_queue_instance, mock_redis):
        """Test updating job status with error message."""
        success = job_queue_instance.update_job_status(
            "job-123",
            JobStatus.FAILED,
            error_message="Network timeout"
        )
        
        assert success is True
        call_args = mock_redis.hset.call_args[1]
        update_data = call_args["mapping"]
        assert update_data["error_message"] == "Network timeout"
    
    @patch('src.pipeline.job_queue.celery_app')
    def test_cancel_job(self, mock_celery_app, job_queue_instance, mock_redis):
        """Test cancelling a job."""
        # Mock existing job data
        job_data = {
            "id": "job-123",
            "status": JobStatus.PENDING.value,
            "celery_task_id": "task-123"
        }
        mock_redis.hgetall.return_value = job_data
        
        success = job_queue_instance.cancel_job("job-123")
        
        assert success is True
        mock_celery_app.control.revoke.assert_called_once_with("task-123", terminate=True)
    
    def test_cancel_completed_job(self, job_queue_instance, mock_redis):
        """Test cancelling a job that's already completed."""
        job_data = {
            "id": "job-123",
            "status": JobStatus.COMPLETED.value
        }
        mock_redis.hgetall.return_value = job_data
        
        success = job_queue_instance.cancel_job("job-123")
        
        assert success is False
    
    def test_get_active_jobs(self, job_queue_instance, mock_redis):
        """Test getting list of active jobs."""
        # Mock Redis keys and data
        mock_redis.keys.return_value = ["job:123", "job:456", "job:789"]
        
        def mock_hgetall(key):
            if key == "job:123":
                return {
                    "id": "123",
                    "status": JobStatus.RUNNING.value,
                    "url": "https://example1.com",
                    "config": ScrapingConfig().model_dump_json(),
                    "created_at": datetime.utcnow().isoformat(),
                    "priority": "3",
                    "retry_count": "0"
                }
            elif key == "job:456":
                return {
                    "id": "456",
                    "status": JobStatus.PENDING.value,
                    "url": "https://example2.com",
                    "config": ScrapingConfig().model_dump_json(),
                    "created_at": datetime.utcnow().isoformat(),
                    "priority": "1",
                    "retry_count": "0"
                }
            elif key == "job:789":
                return {
                    "id": "789",
                    "status": JobStatus.COMPLETED.value,
                    "url": "https://example3.com",
                    "config": ScrapingConfig().model_dump_json(),
                    "created_at": datetime.utcnow().isoformat(),
                    "priority": "5",
                    "retry_count": "0"
                }
            return {}
        
        mock_redis.hgetall.side_effect = mock_hgetall
        
        active_jobs = job_queue_instance.get_active_jobs()
        
        # Should return only pending and running jobs, sorted by priority
        assert len(active_jobs) == 2
        assert active_jobs[0].priority == 1  # Higher priority first
        assert active_jobs[1].priority == 3
    
    def test_cleanup_old_jobs(self, job_queue_instance, mock_redis):
        """Test cleaning up old job records."""
        # Mock old job keys
        old_time = (datetime.utcnow() - timedelta(days=10)).isoformat()
        recent_time = datetime.utcnow().isoformat()
        
        mock_redis.keys.return_value = ["job:old", "job:recent"]
        
        def mock_hgetall(key):
            if key == "job:old":
                return {"created_at": old_time}
            elif key == "job:recent":
                return {"created_at": recent_time}
            return {}
        
        mock_redis.hgetall.side_effect = mock_hgetall
        
        cleaned_count = job_queue_instance.cleanup_old_jobs(max_age_days=7)
        
        assert cleaned_count == 1
        mock_redis.delete.assert_called_once_with("job:old")
    
    @patch('src.pipeline.job_queue.celery_app')
    def test_get_queue_stats(self, mock_celery_app, job_queue_instance, mock_redis):
        """Test getting queue statistics."""
        # Mock Celery inspect
        mock_inspect = Mock()
        mock_inspect.active.return_value = {"celery@worker": [{"id": "task1"}]}
        mock_inspect.scheduled.return_value = {"celery@worker": []}
        mock_inspect.reserved.return_value = {"celery@worker": []}
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        # Mock Redis job keys
        mock_redis.keys.return_value = ["job:1", "job:2", "job:3"]
        
        def mock_hgetall(key):
            if key == "job:1":
                return {"status": JobStatus.RUNNING.value}
            elif key == "job:2":
                return {"status": JobStatus.COMPLETED.value}
            elif key == "job:3":
                return {"status": JobStatus.PENDING.value}
            return {}
        
        mock_redis.hgetall.side_effect = mock_hgetall
        
        stats = job_queue_instance.get_queue_stats()
        
        assert stats["total_jobs"] == 3
        assert stats["status_counts"][JobStatus.RUNNING.value] == 1
        assert stats["status_counts"][JobStatus.COMPLETED.value] == 1
        assert stats["status_counts"][JobStatus.PENDING.value] == 1
        assert stats["active_tasks"] == 1


class TestJobMonitor:
    """Test cases for JobMonitor class."""
    
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
                "used_memory_human": "1.5M",
                "connected_clients": 5,
                "total_commands_processed": 1000
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
    
    @patch('src.pipeline.monitor.job_queue')
    def test_get_job_progress(self, mock_job_queue, monitor_instance, mock_redis):
        """Test getting job progress information."""
        # Mock job data
        mock_job = ScrapingJob(
            id="job-123",
            url="https://example.com",
            status=JobStatus.RUNNING,
            total_pages=10,
            pages_completed=7,
            started_at=datetime.utcnow() - timedelta(minutes=5)
        )
        mock_job_queue.get_job_status.return_value = mock_job
        
        # Mock Redis job data
        mock_redis.hgetall.return_value = {"celery_task_id": "task-123"}
        
        progress = monitor_instance.get_job_progress("job-123")
        
        assert progress["job_id"] == "job-123"
        assert progress["status"] == JobStatus.RUNNING.value
        assert progress["progress_percentage"] == 70.0
        assert progress["pages_completed"] == 7
        assert progress["total_pages"] == 10
        assert "estimated_completion" in progress
    
    @patch('src.pipeline.monitor.job_queue')
    def test_get_job_progress_nonexistent(self, mock_job_queue, monitor_instance):
        """Test getting progress for non-existent job."""
        mock_job_queue.get_job_status.return_value = None
        
        progress = monitor_instance.get_job_progress("nonexistent")
        
        assert "error" in progress
        assert progress["error"] == "Job not found"
    
    @patch('src.pipeline.monitor.celery_app')
    @patch('src.pipeline.monitor.job_queue')
    def test_get_system_metrics(self, mock_job_queue, mock_celery_app, monitor_instance, mock_redis):
        """Test getting system metrics."""
        # Mock queue stats
        mock_job_queue.get_queue_stats.return_value = {
            "total_jobs": 50,
            "status_counts": {
                "pending": 10,
                "running": 5,
                "completed": 30,
                "failed": 5
            }
        }
        
        # Mock Celery inspect
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {"worker1": {}, "worker2": {}}
        mock_inspect.active.return_value = {"worker1": [{"id": "task1"}]}
        mock_inspect.scheduled.return_value = {"worker1": []}
        mock_inspect.reserved.return_value = {"worker1": []}
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        metrics = monitor_instance.get_system_metrics()
        
        assert "timestamp" in metrics
        assert "uptime_seconds" in metrics
        assert metrics["queue_stats"]["total_jobs"] == 50
        assert metrics["worker_stats"]["active_workers"] == 2
        assert metrics["worker_stats"]["total_active_tasks"] == 1
        assert "health_status" in metrics
        assert "redis_info" in metrics
    
    def test_record_job_completion(self, monitor_instance, mock_redis):
        """Test recording job completion metrics."""
        monitor_instance.record_job_completion("job-123", True, 45.5)
        
        assert monitor_instance.system_metrics["jobs_processed"] == 1
        assert monitor_instance.system_metrics["jobs_failed"] == 0
        assert monitor_instance.system_metrics["total_processing_time"] == 45.5
        assert len(monitor_instance.performance_history) == 1
        
        # Verify Redis storage
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
    
    def test_record_job_failure(self, monitor_instance, mock_redis):
        """Test recording job failure metrics."""
        monitor_instance.record_job_completion("job-123", False, 30.0)
        
        assert monitor_instance.system_metrics["jobs_processed"] == 1
        assert monitor_instance.system_metrics["jobs_failed"] == 1
        assert len(monitor_instance.performance_history) == 1
    
    def test_record_error(self, monitor_instance, mock_redis):
        """Test recording error information."""
        monitor_instance.record_error("job-123", "NETWORK_ERROR", "Connection timeout")
        
        assert len(monitor_instance.error_history) == 1
        error = monitor_instance.error_history[0]
        assert error["job_id"] == "job-123"
        assert error["error_type"] == "NETWORK_ERROR"
        assert error["error_message"] == "Connection timeout"
        
        # Verify Redis storage
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
    
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
                pages_completed=5
            ),
            ScrapingJob(
                id="job-2",
                url="https://example2.com",
                status=JobStatus.PENDING,
                priority=3,
                total_pages=5,
                pages_completed=0
            )
        ]
        mock_job_queue.get_active_jobs.return_value = mock_jobs
        
        summary = monitor_instance.get_active_jobs_summary()
        
        assert summary["total_active"] == 2
        assert summary["by_status"]["running"] == 1
        assert summary["by_status"]["pending"] == 1
        assert summary["by_priority"][1] == 1
        assert summary["by_priority"][3] == 1
        assert len(summary["jobs"]) == 2
        assert summary["jobs"][0]["progress_percentage"] == 50.0
        assert summary["jobs"][1]["progress_percentage"] == 0.0
    
    def test_get_performance_history(self, monitor_instance):
        """Test getting performance history."""
        # Add some test metrics
        now = datetime.utcnow()
        for i in range(5):
            metric = {
                "timestamp": now - timedelta(hours=i),
                "job_id": f"job-{i}",
                "success": i % 2 == 0,
                "processing_time": 30.0 + i * 5
            }
            monitor_instance.performance_history.append(metric)
        
        history = monitor_instance.get_performance_history(hours=3)
        
        assert "history" in history
        assert history["hours_requested"] == 3
        # Should include metrics from last 3 hours
        assert len(history["history"]) > 0


class TestWorkerTasks:
    """Test cases for Celery worker tasks."""
    
    @pytest.fixture
    def mock_components(self):
        """Mock all external components."""
        with patch('src.pipeline.worker.web_scraper') as mock_scraper, \
             patch('src.pipeline.worker.content_processor') as mock_processor, \
             patch('src.pipeline.worker.data_cleaner') as mock_cleaner, \
             patch('src.pipeline.worker.data_repository') as mock_repository, \
             patch('src.pipeline.worker.job_queue') as mock_queue:
            
            yield {
                'scraper': mock_scraper,
                'processor': mock_processor,
                'cleaner': mock_cleaner,
                'repository': mock_repository,
                'queue': mock_queue
            }
    
    def test_scrape_url_task_success(self, mock_components):
        """Test successful URL scraping task."""
        # Mock scraping result
        mock_scraped_data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test Page", "text": "Sample content"}
        )
        
        mock_scraping_result = Mock()
        mock_scraping_result.success = True
        mock_scraping_result.data = [mock_scraped_data]
        mock_scraping_result.total_time = 15.5
        mock_scraping_result.error_message = None
        
        mock_components['scraper'].scrape_url.return_value = mock_scraping_result
        mock_components['cleaner'].clean_scraped_data.return_value = mock_scraped_data
        mock_components['repository'].save_scraped_data.return_value = True
        
        # Execute task
        config = ScrapingConfig().model_dump()
        result = scrape_url_task("job-123", "https://example.com", config)
        
        assert result["success"] is True
        assert result["job_id"] == "job-123"
        assert result["url"] == "https://example.com"
        assert result["data_count"] == 1
        assert result["saved_count"] == 1
        
        # Verify component calls
        mock_components['scraper'].scrape_url.assert_called_once()
        mock_components['cleaner'].clean_scraped_data.assert_called_once()
        mock_components['repository'].save_scraped_data.assert_called_once()
    
    def test_scrape_url_task_failure(self, mock_components):
        """Test URL scraping task failure."""
        # Mock scraping failure
        mock_scraping_result = Mock()
        mock_scraping_result.success = False
        mock_scraping_result.error_message = "Network timeout"
        
        mock_components['scraper'].scrape_url.return_value = mock_scraping_result
        
        # Execute task
        config = ScrapingConfig().model_dump()
        result = scrape_url_task("job-123", "https://example.com", config)
        
        assert result["success"] is False
        assert "error" in result
        assert "Network timeout" in result["error"]
    
    def test_process_content_task_success(self, mock_components):
        """Test successful content processing task."""
        # Mock processing result
        mock_result = Mock()
        mock_result.processed_content = {"extracted_data": "test"}
        mock_result.confidence_score = 0.85
        mock_result.metadata = {"ai_processed": True}
        
        mock_components['processor'].process_content.return_value = mock_result
        
        # Execute task
        result = process_content_task("<html>Test content</html>", "https://example.com", "html")
        
        assert result["success"] is True
        assert result["confidence_score"] == 0.85
        assert result["processed_content"]["extracted_data"] == "test"
        assert result["metadata"]["ai_processed"] is True
    
    def test_process_content_task_failure(self, mock_components):
        """Test content processing task failure."""
        # Mock processing failure
        mock_components['processor'].process_content.side_effect = Exception("AI service unavailable")
        
        # Execute task
        result = process_content_task("<html>Test content</html>", "https://example.com", "html")
        
        assert result["success"] is False
        assert "error" in result
        assert result["confidence_score"] == 0.0
    
    def test_clean_data_task_success(self, mock_components):
        """Test successful data cleaning task."""
        # Mock input data
        input_data = {
            "id": "data-123",
            "job_id": "job-123",
            "url": "https://example.com",
            "content": {"title": "Test"},
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Mock cleaned data
        cleaned_data = ScrapedData(**input_data)
        cleaned_data.data_quality_score = 0.9
        mock_components['cleaner'].clean_scraped_data.return_value = cleaned_data
        
        # Execute task
        result = clean_data_task(input_data)
        
        assert result["success"] is True
        assert result["quality_score"] == 0.9
        assert "cleaned_data" in result
    
    def test_clean_data_task_failure(self, mock_components):
        """Test data cleaning task failure."""
        # Mock cleaning failure
        mock_components['cleaner'].clean_scraped_data.side_effect = Exception("Validation error")
        
        input_data = {
            "id": "data-123",
            "job_id": "job-123",
            "url": "https://example.com",
            "content": {"title": "Test"},
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Execute task
        result = clean_data_task(input_data)
        
        assert result["success"] is False
        assert "error" in result
        assert result["original_data"] == input_data


@pytest.mark.integration
class TestTaskQueueIntegration:
    """Integration tests for the complete task queue system."""
    
    @pytest.fixture(scope="class")
    def redis_test_instance(self):
        """Set up Redis test instance."""
        # This would typically use a test Redis instance
        # For now, we'll mock it in the integration tests
        pass
    
    @pytest.mark.skip(reason="Requires Redis test instance")
    def test_end_to_end_job_processing(self):
        """Test complete job processing workflow."""
        # This test would:
        # 1. Submit a job to the queue
        # 2. Verify job status updates
        # 3. Monitor job progress
        # 4. Verify final results
        pass
    
    @pytest.mark.skip(reason="Requires Celery worker")
    def test_worker_task_execution(self):
        """Test actual worker task execution."""
        # This test would:
        # 1. Start a Celery worker
        # 2. Submit tasks
        # 3. Verify task execution
        # 4. Check results
        pass
    
    @pytest.mark.skip(reason="Requires Redis test instance")
    def test_job_monitoring_real_time(self):
        """Test real-time job monitoring."""
        # This test would:
        # 1. Start monitoring
        # 2. Submit jobs
        # 3. Verify real-time updates
        # 4. Check metrics collection
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])