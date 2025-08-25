"""
Integration tests for the DataRepository class with real database operations.

This module contains integration tests that use a real test database
to verify repository operations work correctly end-to-end.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.pipeline.repository import DataRepository
from src.models.pydantic_models import (
    JobStatus, ContentType, ScrapingJob, ScrapedData, ScrapingConfig
)
from tests.conftest import create_test_job_data, create_test_scraped_data


@pytest.mark.integration
class TestRepositoryIntegration:
    """Integration tests for DataRepository with real database."""
    
    @pytest.mark.asyncio
    async def test_complete_job_workflow(self, clean_database):
        """Test a complete job workflow from creation to completion."""
        repository = DataRepository()
        
        # Create a job
        job_data = create_test_job_data()
        job = ScrapingJob(**job_data)
        
        # Test job creation
        job_id = await repository.create_job(job)
        assert job_id == job.id
        
        # Test job retrieval
        retrieved_job = await repository.get_job(job_id)
        assert retrieved_job is not None
        assert retrieved_job.id == job.id
        assert retrieved_job.url == job.url
        assert retrieved_job.status == JobStatus.PENDING
        
        # Test job status update
        success = await repository.update_job_status(
            job_id, 
            JobStatus.RUNNING,
            pages_completed=3
        )
        assert success is True
        
        # Verify status update
        updated_job = await repository.get_job(job_id)
        assert updated_job.status == JobStatus.RUNNING
        assert updated_job.pages_completed == 3
        assert updated_job.started_at is not None
        
        # Complete the job
        await repository.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            pages_completed=5
        )
        
        # Verify completion
        completed_job = await repository.get_job(job_id)
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.pages_completed == 5
        assert completed_job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_scraped_data_workflow(self, clean_database):
        """Test scraped data operations workflow."""
        repository = DataRepository()
        
        # First create a job
        job_data = create_test_job_data()
        job = ScrapingJob(**job_data)
        job_id = await repository.create_job(job)
        
        # Create scraped data
        data_items = []
        for i in range(5):
            data_dict = create_test_scraped_data()
            data_dict["job_id"] = job_id
            data_dict["url"] = f"https://test-example.com/page{i}"
            data_dict["confidence_score"] = 0.8 + (i * 0.05)  # Varying confidence
            data_dict["ai_processed"] = i % 2 == 0  # Alternate AI processing
            
            data = ScrapedData(**data_dict)
            data_items.append(data)
            
            # Save the data
            saved_id = await repository.save_scraped_data(data)
            assert saved_id == data.id
        
        # Test data retrieval with filters
        all_data, total_count = await repository.get_scraped_data(job_id=job_id)
        assert len(all_data) == 5
        assert total_count == 5
        
        # Test filtering by confidence
        high_confidence_data, count = await repository.get_scraped_data(
            job_id=job_id,
            min_confidence=0.9
        )
        assert len(high_confidence_data) == 3  # Items with confidence >= 0.9
        
        # Test filtering by AI processing
        ai_processed_data, count = await repository.get_scraped_data(
            job_id=job_id,
            ai_processed_only=True
        )
        assert len(ai_processed_data) == 3  # Items where i % 2 == 0
        
        # Test pagination
        page1_data, total = await repository.get_scraped_data(
            job_id=job_id,
            limit=2,
            offset=0
        )
        assert len(page1_data) == 2
        assert total == 5
        
        page2_data, total = await repository.get_scraped_data(
            job_id=job_id,
            limit=2,
            offset=2
        )
        assert len(page2_data) == 2
        assert total == 5
        
        # Ensure different pages have different data
        page1_ids = {item.id for item in page1_data}
        page2_ids = {item.id for item in page2_data}
        assert page1_ids.isdisjoint(page2_ids)
    
    @pytest.mark.asyncio
    async def test_ai_processing_update(self, clean_database):
        """Test updating scraped data with AI processing results."""
        repository = DataRepository()
        
        # Create job and data
        job_data = create_test_job_data()
        job = ScrapingJob(**job_data)
        job_id = await repository.create_job(job)
        
        data_dict = create_test_scraped_data()
        data_dict["job_id"] = job_id
        data_dict["ai_processed"] = False
        data_dict["confidence_score"] = 0.0
        
        data = ScrapedData(**data_dict)
        data_id = await repository.save_scraped_data(data)
        
        # Update with AI processing results
        success = await repository.update_data_ai_processing(
            data_id,
            confidence_score=0.95,
            ai_metadata={"entities": ["Test Entity"], "sentiment": "positive"},
            data_quality_score=0.9,
            validation_errors=[]
        )
        assert success is True
        
        # Verify the update
        updated_data, _ = await repository.get_scraped_data(job_id=job_id)
        assert len(updated_data) == 1
        
        updated_item = updated_data[0]
        assert updated_item.ai_processed is True
        assert updated_item.confidence_score == 0.95
        assert updated_item.ai_metadata["entities"] == ["Test Entity"]
        assert updated_item.data_quality_score == 0.9
        assert updated_item.processed_at is not None
    
    @pytest.mark.asyncio
    async def test_logging_operations(self, clean_database):
        """Test job logging operations."""
        repository = DataRepository()
        
        # Create a job
        job_data = create_test_job_data()
        job = ScrapingJob(**job_data)
        job_id = await repository.create_job(job)
        
        # Add various log entries
        log_entries = [
            ("INFO", "Job started", {"step": "initialization"}),
            ("DEBUG", "Processing page 1", {"page": 1, "url": "https://example.com/1"}),
            ("WARNING", "Slow response detected", {"response_time": 5.2}),
            ("ERROR", "Failed to extract data", {"error": "timeout"}),
            ("INFO", "Job completed", {"pages_processed": 10})
        ]
        
        log_ids = []
        for level, message, context in log_entries:
            log_id = await repository.add_job_log(job_id, level, message, context)
            log_ids.append(log_id)
        
        # Retrieve all logs
        all_logs = await repository.get_job_logs(job_id)
        assert len(all_logs) == 5
        
        # Verify log content
        assert all(log["job_id"] == job_id for log in all_logs)
        assert any(log["level"] == "ERROR" for log in all_logs)
        assert any("timeout" in str(log["context"]) for log in all_logs)
        
        # Filter by log level
        error_logs = await repository.get_job_logs(job_id, level="ERROR")
        assert len(error_logs) == 1
        assert error_logs[0]["message"] == "Failed to extract data"
        
        info_logs = await repository.get_job_logs(job_id, level="INFO")
        assert len(info_logs) == 2
    
    @pytest.mark.asyncio
    async def test_system_metrics_operations(self, clean_database):
        """Test system metrics recording and retrieval."""
        repository = DataRepository()
        
        # Record various metrics
        metrics_data = [
            ("cpu_usage", 75.5, "percent", {"host": "server1"}),
            ("memory_usage", 8192, "MB", {"host": "server1"}),
            ("disk_usage", 85.2, "percent", {"host": "server1", "disk": "/"}),
            ("response_time", 250, "ms", {"endpoint": "/api/jobs"}),
            ("active_connections", 15, "count", {"service": "database"})
        ]
        
        metric_ids = []
        for name, value, unit, tags in metrics_data:
            metric_id = await repository.record_system_metric(name, value, unit, tags)
            metric_ids.append(metric_id)
        
        # Retrieve all metrics
        all_metrics = await repository.get_system_metrics()
        assert len(all_metrics) >= 5  # At least our test metrics
        
        # Filter by metric name
        cpu_metrics = await repository.get_system_metrics(metric_name="cpu_usage")
        assert len(cpu_metrics) == 1
        assert cpu_metrics[0]["metric_value"] == 75.5
        assert cpu_metrics[0]["metric_unit"] == "percent"
        
        # Filter by time range
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        recent_metrics = await repository.get_system_metrics(
            start_time=one_hour_ago,
            end_time=now
        )
        assert len(recent_metrics) >= 5
    
    @pytest.mark.asyncio
    async def test_job_statistics(self, clean_database):
        """Test job statistics generation."""
        repository = DataRepository()
        
        # Create multiple jobs with different statuses
        job_statuses = [
            JobStatus.COMPLETED, JobStatus.COMPLETED, JobStatus.COMPLETED,
            JobStatus.FAILED, JobStatus.FAILED,
            JobStatus.RUNNING,
            JobStatus.PENDING, JobStatus.PENDING
        ]
        
        for i, status in enumerate(job_statuses):
            job_data = create_test_job_data()
            job_data["id"] = str(uuid4())
            job_data["url"] = f"https://example.com/{i}"
            job_data["status"] = status
            
            if status == JobStatus.COMPLETED:
                job_data["pages_completed"] = 10 + i
                job_data["started_at"] = datetime.utcnow() - timedelta(minutes=30)
                job_data["completed_at"] = datetime.utcnow() - timedelta(minutes=10)
            elif status == JobStatus.RUNNING:
                job_data["started_at"] = datetime.utcnow() - timedelta(minutes=15)
                job_data["pages_completed"] = 5
            
            job = ScrapingJob(**job_data)
            await repository.create_job(job)
        
        # Get job statistics
        stats = await repository.get_job_statistics()
        
        assert "status_counts" in stats
        assert "performance_metrics" in stats
        
        # Verify status counts
        status_counts = stats["status_counts"]
        assert status_counts.get("completed", 0) == 3
        assert status_counts.get("failed", 0) == 2
        assert status_counts.get("running", 0) == 1
        assert status_counts.get("pending", 0) == 2
        
        # Verify performance metrics
        perf_metrics = stats["performance_metrics"]
        assert perf_metrics["total_pages_scraped"] > 0
        assert perf_metrics["average_pages_per_job"] > 0
    
    @pytest.mark.asyncio
    async def test_data_quality_metrics(self, clean_database):
        """Test data quality metrics calculation."""
        repository = DataRepository()
        
        # Create job
        job_data = create_test_job_data()
        job = ScrapingJob(**job_data)
        job_id = await repository.create_job(job)
        
        # Create data with varying quality metrics
        quality_data = [
            (0.9, 0.85, True, []),
            (0.8, 0.9, True, []),
            (0.7, 0.75, False, ["missing_title"]),
            (0.95, 0.95, True, []),
            (0.6, 0.7, False, ["invalid_date", "missing_content"])
        ]
        
        for confidence, quality, ai_processed, errors in quality_data:
            data_dict = create_test_scraped_data()
            data_dict["job_id"] = job_id
            data_dict["confidence_score"] = confidence
            data_dict["data_quality_score"] = quality
            data_dict["ai_processed"] = ai_processed
            data_dict["validation_errors"] = errors
            
            data = ScrapedData(**data_dict)
            await repository.save_scraped_data(data)
        
        # Get quality metrics
        quality_metrics = await repository.get_data_quality_metrics()
        
        assert "average_confidence_score" in quality_metrics
        assert "average_quality_score" in quality_metrics
        assert "total_data_records" in quality_metrics
        assert "ai_processed_percentage" in quality_metrics
        
        # Verify calculations
        assert quality_metrics["total_data_records"] == 5
        assert quality_metrics["ai_processed_percentage"] == 60.0  # 3 out of 5
        assert 0.7 <= quality_metrics["average_confidence_score"] <= 0.9
        assert 0.7 <= quality_metrics["average_quality_score"] <= 0.9
    
    @pytest.mark.asyncio
    async def test_cleanup_operations(self, clean_database):
        """Test data cleanup operations."""
        repository = DataRepository()
        
        # Create old jobs (older than retention period)
        old_date = datetime.utcnow() - timedelta(days=35)
        recent_date = datetime.utcnow() - timedelta(days=5)
        
        # Create old job
        old_job_data = create_test_job_data()
        old_job_data["created_at"] = old_date
        old_job = ScrapingJob(**old_job_data)
        old_job_id = await repository.create_job(old_job)
        
        # Create recent job
        recent_job_data = create_test_job_data()
        recent_job_data["id"] = str(uuid4())
        recent_job_data["created_at"] = recent_date
        recent_job = ScrapingJob(**recent_job_data)
        recent_job_id = await repository.create_job(recent_job)
        
        # Add logs for both jobs
        await repository.add_job_log(old_job_id, "INFO", "Old job log", {})
        await repository.add_job_log(recent_job_id, "INFO", "Recent job log", {})
        
        # Test dry run cleanup
        cleanup_stats = await repository.cleanup_old_data(
            retention_days=30,
            dry_run=True
        )
        
        assert cleanup_stats["dry_run"] is True
        assert cleanup_stats["old_jobs_count"] >= 1
        
        # Verify jobs still exist after dry run
        old_job_check = await repository.get_job(old_job_id)
        recent_job_check = await repository.get_job(recent_job_id)
        assert old_job_check is not None
        assert recent_job_check is not None
        
        # Test actual cleanup
        cleanup_stats = await repository.cleanup_old_data(
            retention_days=30,
            dry_run=False
        )
        
        assert cleanup_stats["dry_run"] is False
        
        # Verify old job is deleted, recent job remains
        old_job_check = await repository.get_job(old_job_id)
        recent_job_check = await repository.get_job(recent_job_id)
        assert old_job_check is None
        assert recent_job_check is not None


@pytest.mark.performance
class TestRepositoryPerformance:
    """Performance tests for repository operations."""
    
    @pytest.mark.asyncio
    async def test_bulk_data_operations(self, clean_database):
        """Test performance with bulk data operations."""
        repository = DataRepository()
        
        # Create a job
        job_data = create_test_job_data()
        job = ScrapingJob(**job_data)
        job_id = await repository.create_job(job)
        
        # Create many data records
        num_records = 100
        data_items = []
        
        for i in range(num_records):
            data_dict = create_test_scraped_data()
            data_dict["job_id"] = job_id
            data_dict["url"] = f"https://example.com/page{i}"
            data_items.append(ScrapedData(**data_dict))
        
        # Time the bulk insert
        import time
        start_time = time.time()
        
        for data in data_items:
            await repository.save_scraped_data(data)
        
        insert_time = time.time() - start_time
        
        # Verify all data was inserted
        all_data, total_count = await repository.get_scraped_data(job_id=job_id)
        assert total_count == num_records
        
        # Time the bulk retrieval
        start_time = time.time()
        
        retrieved_data, count = await repository.get_scraped_data(
            job_id=job_id,
            limit=num_records
        )
        
        retrieval_time = time.time() - start_time
        
        assert len(retrieved_data) == num_records
        
        # Performance assertions (adjust thresholds as needed)
        assert insert_time < 30.0  # Should insert 100 records in under 30 seconds
        assert retrieval_time < 5.0  # Should retrieve 100 records in under 5 seconds
        
        print(f"Bulk insert time: {insert_time:.2f}s")
        print(f"Bulk retrieval time: {retrieval_time:.2f}s")