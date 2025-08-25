"""
Unit tests for Celery worker tasks.

This module contains tests for the background worker tasks that handle
scraping, content processing, and data cleaning operations.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from celery.exceptions import Retry

from src.pipeline.worker import (
    scrape_url_task, 
    process_content_task, 
    clean_data_task,
    batch_scrape_task,
    process_content_with_ai,
    CallbackTask
)
from src.models.pydantic_models import JobStatus, ScrapingConfig, ScrapedData, ScrapingResult
from src.utils.circuit_breaker import CircuitBreaker


class TestCallbackTask:
    """Test cases for the CallbackTask base class."""
    
    def test_on_failure_updates_job_status(self):
        """Test that task failure updates job status."""
        with patch('src.pipeline.worker.job_queue') as mock_queue:
            task = CallbackTask()
            task.on_failure(
                exc=Exception("Test error"),
                task_id="task-123",
                args=[],
                kwargs={"job_id": "job-123"},
                einfo=Mock(traceback="test traceback")
            )
            
            mock_queue.update_job_status.assert_called_once_with(
                "job-123",
                JobStatus.FAILED,
                error_message="Test error"
            )
    
    def test_on_retry_increments_count(self):
        """Test that task retry increments retry count."""
        with patch('src.pipeline.worker.job_queue') as mock_queue:
            mock_job = Mock()
            mock_job.retry_count = 1
            mock_queue.get_job_status.return_value = mock_job
            
            task = CallbackTask()
            task.request = Mock(retries=1)
            task.on_retry(
                exc=Exception("Retry error"),
                task_id="task-123",
                args=[],
                kwargs={"job_id": "job-123"},
                einfo=Mock()
            )
            
            mock_queue.update_job_status.assert_called_once_with(
                "job-123",
                JobStatus.PENDING,
                retry_count=2
            )


class TestScrapeUrlTask:
    """Test cases for the scrape_url_task."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('src.pipeline.worker.job_queue') as mock_queue, \
             patch('src.pipeline.worker.web_scraper') as mock_scraper, \
             patch('src.pipeline.worker.data_cleaner') as mock_cleaner, \
             patch('src.pipeline.worker.data_repository') as mock_repository:
            
            yield {
                'queue': mock_queue,
                'scraper': mock_scraper,
                'cleaner': mock_cleaner,
                'repository': mock_repository
            }
    
    def test_successful_scraping(self, mock_dependencies):
        """Test successful URL scraping."""
        # Mock scraped data
        mock_scraped_data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test Page", "body": "Content"}
        )
        
        # Mock scraping result
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = [mock_scraped_data]
        mock_result.total_time = 10.5
        mock_result.error_message = None
        
        mock_dependencies['scraper'].scrape_url.return_value = mock_result
        mock_dependencies['cleaner'].clean_scraped_data.return_value = mock_scraped_data
        mock_dependencies['repository'].save_scraped_data.return_value = True
        
        # Create mock task instance
        task_instance = Mock()
        task_instance.request = Mock(id="task-123", retries=0)
        
        # Execute task
        config = ScrapingConfig().model_dump()
        result = scrape_url_task.__wrapped__(task_instance, "job-123", "https://example.com", config)
        
        # Verify result
        assert result["success"] is True
        assert result["job_id"] == "job-123"
        assert result["url"] == "https://example.com"
        assert result["data_count"] == 1
        assert result["saved_count"] == 1
        assert result["processing_time"] == 10.5
        
        # Verify job status updates
        mock_dependencies['queue'].update_job_status.assert_any_call("job-123", JobStatus.RUNNING)
        mock_dependencies['queue'].update_job_status.assert_any_call(
            "job-123",
            JobStatus.COMPLETED,
            total_pages=1,
            pages_completed=1,
            pages_failed=0
        )
    
    def test_scraping_failure(self, mock_dependencies):
        """Test scraping failure handling."""
        # Mock scraping failure
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Network timeout"
        
        mock_dependencies['scraper'].scrape_url.return_value = mock_result
        
        # Create mock task instance
        task_instance = Mock()
        task_instance.request = Mock(id="task-123", retries=0)
        task_instance.max_retries = 3
        task_instance.retry = Mock(side_effect=Retry("Retrying"))
        
        # Execute task - should raise Retry exception
        config = ScrapingConfig().model_dump()
        with pytest.raises(Retry):
            scrape_url_task.__wrapped__(task_instance, "job-123", "https://example.com", config)
        
        # Verify job status updated to failed
        mock_dependencies['queue'].update_job_status.assert_any_call(
            "job-123", 
            JobStatus.FAILED, 
            error_message="Scraping task failed: Scraping failed: Network timeout"
        )
    
    def test_circuit_breaker_open(self, mock_dependencies):
        """Test behavior when circuit breaker is open."""
        # Mock circuit breaker open state
        with patch('src.pipeline.worker.scraper_circuit_breaker') as mock_cb:
            mock_cb.is_open = True
            mock_cb.side_effect = Exception("Circuit breaker open")
            
            task_instance = Mock()
            task_instance.request = Mock(id="task-123", retries=0)
            task_instance.max_retries = 3
            task_instance.retry = Mock(side_effect=Retry("Retrying"))
            
            config = ScrapingConfig().model_dump()
            with pytest.raises(Retry):
                scrape_url_task.__wrapped__(task_instance, "job-123", "https://example.com", config)
    
    def test_data_processing_failure(self, mock_dependencies):
        """Test handling of data processing failures."""
        # Mock successful scraping but failed processing
        mock_scraped_data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test"}
        )
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = [mock_scraped_data]
        mock_result.total_time = 5.0
        
        mock_dependencies['scraper'].scrape_url.return_value = mock_result
        mock_dependencies['cleaner'].clean_scraped_data.side_effect = Exception("Cleaning failed")
        mock_dependencies['repository'].save_scraped_data.return_value = True
        
        task_instance = Mock()
        task_instance.request = Mock(id="task-123", retries=0)
        
        config = ScrapingConfig().model_dump()
        result = scrape_url_task.__wrapped__(task_instance, "job-123", "https://example.com", config)
        
        # Should still succeed but use original data
        assert result["success"] is True
        assert result["data_count"] == 1
    
    def test_database_save_failure(self, mock_dependencies):
        """Test handling of database save failures."""
        mock_scraped_data = ScrapedData(
            job_id="job-123",
            url="https://example.com",
            content={"title": "Test"}
        )
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = [mock_scraped_data]
        mock_result.total_time = 5.0
        
        mock_dependencies['scraper'].scrape_url.return_value = mock_result
        mock_dependencies['cleaner'].clean_scraped_data.return_value = mock_scraped_data
        mock_dependencies['repository'].save_scraped_data.side_effect = Exception("DB error")
        
        task_instance = Mock()
        task_instance.request = Mock(id="task-123", retries=0)
        
        config = ScrapingConfig().model_dump()
        result = scrape_url_task.__wrapped__(task_instance, "job-123", "https://example.com", config)
        
        # Should succeed but with 0 saved count
        assert result["success"] is True
        assert result["saved_count"] == 0


class TestProcessContentTask:
    """Test cases for the process_content_task."""
    
    @pytest.fixture
    def mock_processor(self):
        """Mock content processor."""
        with patch('src.pipeline.worker.content_processor') as mock:
            yield mock
    
    def test_successful_processing(self, mock_processor):
        """Test successful content processing."""
        # Mock processing result
        mock_result = Mock()
        mock_result.processed_content = {"extracted": "data"}
        mock_result.confidence_score = 0.85
        mock_result.metadata = {"ai_processed": True}
        
        mock_processor.process_content.return_value = mock_result
        
        # Create mock task instance
        task_instance = Mock()
        task_instance.request = Mock(id="task-123")
        
        # Execute task
        result = process_content_task.__wrapped__(
            task_instance, 
            "<html>Test content</html>", 
            "https://example.com", 
            "html"
        )
        
        assert result["success"] is True
        assert result["confidence_score"] == 0.85
        assert result["processed_content"]["extracted"] == "data"
        assert result["metadata"]["ai_processed"] is True
    
    def test_processing_failure(self, mock_processor):
        """Test content processing failure."""
        mock_processor.process_content.side_effect = Exception("AI service error")
        
        task_instance = Mock()
        task_instance.request = Mock(id="task-123")
        
        result = process_content_task.__wrapped__(
            task_instance,
            "<html>Test content</html>",
            "https://example.com",
            "html"
        )
        
        assert result["success"] is False
        assert result["confidence_score"] == 0.0
        assert "error" in result
    
    def test_circuit_breaker_fallback(self, mock_processor):
        """Test circuit breaker fallback behavior."""
        with patch('src.pipeline.worker.ai_circuit_breaker') as mock_cb:
            mock_cb.is_open = True
            mock_cb.side_effect = Exception("Circuit breaker open")
            
            task_instance = Mock()
            task_instance.request = Mock(id="task-123")
            
            result = process_content_task.__wrapped__(
                task_instance,
                "<html>Test content</html>",
                "https://example.com",
                "html"
            )
            
            # Should return fallback result
            assert result["success"] is True
            assert result["confidence_score"] == 0.5
            assert result["metadata"]["fallback_used"] is True


class TestCleanDataTask:
    """Test cases for the clean_data_task."""
    
    @pytest.fixture
    def mock_cleaner(self):
        """Mock data cleaner."""
        with patch('src.pipeline.worker.data_cleaner') as mock:
            yield mock
    
    def test_successful_cleaning(self, mock_cleaner):
        """Test successful data cleaning."""
        # Input data
        input_data = {
            "id": "data-123",
            "job_id": "job-123",
            "url": "https://example.com",
            "content": {"title": "Test"},
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Mock cleaned result
        cleaned_data = ScrapedData(**input_data)
        cleaned_data.data_quality_score = 0.9
        mock_cleaner.clean_scraped_data.return_value = cleaned_data
        
        task_instance = Mock()
        task_instance.request = Mock(id="task-123")
        
        result = clean_data_task.__wrapped__(task_instance, input_data)
        
        assert result["success"] is True
        assert result["quality_score"] == 0.9
        assert "cleaned_data" in result
    
    def test_cleaning_failure(self, mock_cleaner):
        """Test data cleaning failure."""
        mock_cleaner.clean_scraped_data.side_effect = Exception("Validation error")
        
        input_data = {
            "id": "data-123",
            "job_id": "job-123",
            "url": "https://example.com",
            "content": {"title": "Test"},
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        task_instance = Mock()
        task_instance.request = Mock(id="task-123")
        
        result = clean_data_task.__wrapped__(task_instance, input_data)
        
        assert result["success"] is False
        assert "error" in result
        assert result["original_data"] == input_data


class TestBatchScrapeTask:
    """Test cases for the batch_scrape_task."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock dependencies for batch scraping."""
        with patch('src.pipeline.worker.job_queue') as mock_queue, \
             patch('src.pipeline.worker.scrape_url_task') as mock_task:
            yield {
                'queue': mock_queue,
                'task': mock_task
            }
    
    def test_successful_batch_processing(self, mock_dependencies):
        """Test successful batch URL processing."""
        # Mock individual task results
        mock_dependencies['task'].apply.return_value = {
            "success": True,
            "job_id": "job-123_0",
            "url": "https://example1.com"
        }
        
        task_instance = Mock()
        task_instance.request = Mock(id="batch-task-123")
        
        urls = ["https://example1.com", "https://example2.com"]
        config = ScrapingConfig().model_dump()
        
        result = batch_scrape_task.__wrapped__(task_instance, "batch-job-123", urls, config)
        
        assert result["success"] is True
        assert result["total_urls"] == 2
        assert result["completed_count"] == 2
        assert result["failed_count"] == 0
        
        # Verify job status updates
        mock_dependencies['queue'].update_job_status.assert_any_call(
            "batch-job-123",
            JobStatus.RUNNING,
            total_pages=2
        )
    
    def test_partial_batch_failure(self, mock_dependencies):
        """Test batch processing with some failures."""
        # Mock mixed results
        def mock_apply(kwargs):
            if "example1.com" in kwargs["url"]:
                return {"success": True, "url": kwargs["url"]}
            else:
                return {"success": False, "url": kwargs["url"], "error": "Failed"}
        
        mock_dependencies['task'].apply.side_effect = mock_apply
        
        task_instance = Mock()
        task_instance.request = Mock(id="batch-task-123")
        
        urls = ["https://example1.com", "https://example2.com"]
        config = ScrapingConfig().model_dump()
        
        result = batch_scrape_task.__wrapped__(task_instance, "batch-job-123", urls, config)
        
        assert result["success"] is True
        assert result["completed_count"] == 1
        assert result["failed_count"] == 1
        
        # Final status should be FAILED due to failures
        mock_dependencies['queue'].update_job_status.assert_any_call(
            "batch-job-123",
            JobStatus.FAILED,
            pages_completed=1,
            pages_failed=1
        )


class TestProcessContentWithAI:
    """Test cases for the process_content_with_ai helper function."""
    
    def test_successful_ai_processing(self):
        """Test successful AI content processing."""
        with patch('src.pipeline.worker.process_content_task') as mock_task:
            mock_task.apply.return_value = {
                "success": True,
                "confidence_score": 0.8,
                "metadata": {"ai_processed": True}
            }
            
            result = process_content_with_ai(
                {"title": "Test", "body": "Content"},
                "https://example.com"
            )
            
            assert result["confidence_score"] == 0.8
            assert result["metadata"]["ai_processed"] is True
    
    def test_ai_processing_failure(self):
        """Test AI processing failure fallback."""
        with patch('src.pipeline.worker.process_content_task') as mock_task:
            mock_task.apply.return_value = {
                "success": False,
                "error": "AI service unavailable"
            }
            
            result = process_content_with_ai(
                {"title": "Test"},
                "https://example.com"
            )
            
            assert result["confidence_score"] == 0.0
            assert result["metadata"]["ai_processing_failed"] is True
    
    def test_ai_processing_exception(self):
        """Test AI processing with exception."""
        with patch('src.pipeline.worker.process_content_task') as mock_task:
            mock_task.apply.side_effect = Exception("Task failed")
            
            result = process_content_with_ai(
                {"title": "Test"},
                "https://example.com"
            )
            
            assert result["confidence_score"] == 0.0
            assert result["metadata"]["ai_processing_failed"] is True
            assert "error" in result["metadata"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])