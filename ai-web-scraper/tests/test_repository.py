"""
Unit tests for the DataRepository class.

This module contains comprehensive tests for all repository operations
including CRUD operations, filtering, and performance monitoring.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.pipeline.repository import DataRepository
from src.models.pydantic_models import (
    JobStatus, ContentType, ScrapingJob, ScrapedData, ScrapingConfig
)
from src.models.database_models import (
    ScrapingJobORM, ScrapedDataORM, JobLogORM, SystemMetricORM
)


@pytest.fixture
def repository():
    """Create a DataRepository instance for testing."""
    return DataRepository()


@pytest.fixture
def sample_scraping_config():
    """Create a sample scraping configuration."""
    return ScrapingConfig(
        wait_time=5,
        max_retries=3,
        use_stealth=True,
        extract_images=False,
        follow_links=False,
        custom_selectors={"title": "h1", "content": ".content"}
    )


@pytest.fixture
def sample_scraping_job(sample_scraping_config):
    """Create a sample scraping job."""
    return ScrapingJob(
        id=str(uuid4()),
        url="https://example.com",
        config=sample_scraping_config,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow(),
        total_pages=10,
        pages_completed=0,
        pages_failed=0,
        user_id="test-user-123",
        tags=["test", "example"],
        priority=5
    )


@pytest.fixture
def sample_scraped_data():
    """Create a sample scraped data record."""
    return ScrapedData(
        id=str(uuid4()),
        job_id=str(uuid4()),
        url="https://example.com/page1",
        content={"title": "Test Page", "text": "Sample content"},
        raw_html="<html><body><h1>Test Page</h1><p>Sample content</p></body></html>",
        content_type=ContentType.HTML,
        content_metadata={"language": "en", "charset": "utf-8"},
        confidence_score=0.95,
        ai_processed=True,
        ai_metadata={"entities": ["Test"], "sentiment": "neutral"},
        data_quality_score=0.9,
        validation_errors=[],
        extracted_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
        content_length=1024,
        load_time=2.5
    )


class TestJobManagement:
    """Test cases for job management operations."""
    
    @pytest.mark.asyncio
    async def test_create_job_success(self, repository, sample_scraping_job):
        """Test successful job creation."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock successful job creation
            mock_job_orm = MagicMock()
            mock_job_orm.id = sample_scraping_job.id
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()
            
            result = await repository.create_job(sample_scraping_job)
            
            assert result == sample_scraping_job.id
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_job_duplicate_id(self, repository, sample_scraping_job):
        """Test job creation with duplicate ID."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock IntegrityError for duplicate ID
            mock_session_instance.commit.side_effect = IntegrityError("", "", "")
            
            with pytest.raises(ValueError, match="already exists"):
                await repository.create_job(sample_scraping_job)
    
    @pytest.mark.asyncio
    async def test_get_job_success(self, repository, sample_scraping_job):
        """Test successful job retrieval."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock job ORM
            mock_job_orm = MagicMock()
            mock_job_orm.id = sample_scraping_job.id
            mock_job_orm.url = sample_scraping_job.url
            mock_job_orm.status = sample_scraping_job.status.value
            mock_job_orm.config = sample_scraping_job.config.model_dump()
            mock_job_orm.created_at = sample_scraping_job.created_at
            mock_job_orm.started_at = sample_scraping_job.started_at
            mock_job_orm.completed_at = sample_scraping_job.completed_at
            mock_job_orm.total_pages = sample_scraping_job.total_pages
            mock_job_orm.pages_completed = sample_scraping_job.pages_completed
            mock_job_orm.pages_failed = sample_scraping_job.pages_failed
            mock_job_orm.error_message = sample_scraping_job.error_message
            mock_job_orm.retry_count = sample_scraping_job.retry_count
            mock_job_orm.user_id = sample_scraping_job.user_id
            mock_job_orm.tags = sample_scraping_job.tags
            mock_job_orm.priority = sample_scraping_job.priority
            
            # Mock query result
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_job_orm
            mock_session_instance.execute.return_value = mock_result
            
            result = await repository.get_job(sample_scraping_job.id)
            
            assert result is not None
            assert result.id == sample_scraping_job.id
            assert result.url == sample_scraping_job.url
            assert result.status == sample_scraping_job.status
    
    @pytest.mark.asyncio
    async def test_get_job_not_found(self, repository):
        """Test job retrieval when job doesn't exist."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock empty result
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session_instance.execute.return_value = mock_result
            
            result = await repository.get_job("non-existent-id")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_update_job_status_success(self, repository):
        """Test successful job status update."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock successful update
            mock_result = MagicMock()
            mock_result.rowcount = 1
            mock_session_instance.execute.return_value = mock_result
            mock_session_instance.commit = AsyncMock()
            
            result = await repository.update_job_status(
                "test-job-id", 
                JobStatus.RUNNING,
                pages_completed=5
            )
            
            assert result is True
            mock_session_instance.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_jobs_by_status(self, repository):
        """Test retrieving jobs by status."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock job ORMs
            mock_jobs = []
            for i in range(3):
                mock_job = MagicMock()
                mock_job.id = f"job-{i}"
                mock_job.url = f"https://example.com/{i}"
                mock_job.status = JobStatus.PENDING.value
                mock_job.config = {}
                mock_job.created_at = datetime.utcnow()
                mock_job.started_at = None
                mock_job.completed_at = None
                mock_job.total_pages = 10
                mock_job.pages_completed = 0
                mock_job.pages_failed = 0
                mock_job.error_message = None
                mock_job.retry_count = 0
                mock_job.user_id = "test-user"
                mock_job.tags = []
                mock_job.priority = 5
                mock_jobs.append(mock_job)
            
            # Mock query result
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_jobs
            mock_session_instance.execute.return_value = mock_result
            
            result = await repository.get_jobs_by_status(JobStatus.PENDING, limit=10)
            
            assert len(result) == 3
            assert all(job.status == JobStatus.PENDING for job in result)


class TestScrapedDataManagement:
    """Test cases for scraped data management operations."""
    
    @pytest.mark.asyncio
    async def test_save_scraped_data_success(self, repository, sample_scraped_data):
        """Test successful scraped data saving."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock successful data save
            mock_data_orm = MagicMock()
            mock_data_orm.id = sample_scraped_data.id
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()
            
            result = await repository.save_scraped_data(sample_scraped_data)
            
            assert result == sample_scraped_data.id
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_scraped_data_with_filters(self, repository):
        """Test retrieving scraped data with various filters."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 5
            
            # Mock data results
            mock_data = []
            for i in range(3):
                mock_item = MagicMock()
                mock_item.id = f"data-{i}"
                mock_item.job_id = "test-job"
                mock_item.url = f"https://example.com/{i}"
                mock_item.content = {"title": f"Page {i}"}
                mock_item.raw_html = f"<html>Page {i}</html>"
                mock_item.content_type = ContentType.HTML.value
                mock_item.content_metadata = {}
                mock_item.confidence_score = 0.9
                mock_item.ai_processed = True
                mock_item.ai_metadata = {}
                mock_item.data_quality_score = 0.8
                mock_item.validation_errors = []
                mock_item.extracted_at = datetime.utcnow()
                mock_item.processed_at = datetime.utcnow()
                mock_item.content_length = 1000
                mock_item.load_time = 1.5
                mock_data.append(mock_item)
            
            mock_data_result = MagicMock()
            mock_data_result.scalars.return_value.all.return_value = mock_data
            
            # Mock session execute to return different results for count and data queries
            mock_session_instance.execute.side_effect = [mock_count_result, mock_data_result]
            
            # Mock performance monitoring
            with patch.object(repository, '_monitor_query_performance') as mock_monitor:
                mock_monitor.return_value.__aenter__ = AsyncMock()
                mock_monitor.return_value.__aexit__ = AsyncMock()
                
                result_data, total_count = await repository.get_scraped_data(
                    job_id="test-job",
                    min_confidence=0.8,
                    ai_processed_only=True,
                    limit=10
                )
            
            assert len(result_data) == 3
            assert total_count == 5
            assert all(data.job_id == "test-job" for data in result_data)
    
    @pytest.mark.asyncio
    async def test_update_data_ai_processing(self, repository):
        """Test updating scraped data with AI processing results."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock successful update
            mock_result = MagicMock()
            mock_result.rowcount = 1
            mock_session_instance.execute.return_value = mock_result
            mock_session_instance.commit = AsyncMock()
            
            result = await repository.update_data_ai_processing(
                "test-data-id",
                confidence_score=0.95,
                ai_metadata={"entities": ["test"]},
                data_quality_score=0.9,
                validation_errors=[]
            )
            
            assert result is True
            mock_session_instance.commit.assert_called_once()


class TestLoggingAndMetrics:
    """Test cases for logging and metrics operations."""
    
    @pytest.mark.asyncio
    async def test_add_job_log(self, repository):
        """Test adding a job log entry."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock successful log creation
            mock_log_orm = MagicMock()
            mock_log_orm.id = "test-log-id"
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()
            
            # Mock uuid4 to return predictable ID
            with patch('src.pipeline.repository.uuid4') as mock_uuid:
                mock_uuid.return_value = MagicMock()
                mock_uuid.return_value.__str__ = MagicMock(return_value="test-log-id")
                
                result = await repository.add_job_log(
                    "test-job-id",
                    "INFO",
                    "Test log message",
                    {"context": "test"}
                )
                
                assert result == "test-log-id"
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_system_metric(self, repository):
        """Test recording a system metric."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock successful metric creation
            mock_metric_orm = MagicMock()
            mock_metric_orm.id = "test-metric-id"
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()
            
            # Mock uuid4 to return predictable ID
            with patch('src.pipeline.repository.uuid4') as mock_uuid:
                mock_uuid.return_value = MagicMock()
                mock_uuid.return_value.__str__ = MagicMock(return_value="test-metric-id")
                
                result = await repository.record_system_metric(
                    "cpu_usage",
                    75.5,
                    "percent",
                    {"host": "test-server"}
                )
                
                assert result == "test-metric-id"
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()


class TestPerformanceMonitoring:
    """Test cases for performance monitoring features."""
    
    @pytest.mark.asyncio
    async def test_get_database_performance_metrics(self, repository):
        """Test retrieving database performance metrics."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock connection pool
            mock_pool = MagicMock()
            mock_pool.size.return_value = 10
            mock_pool.checkedin.return_value = 8
            mock_pool.checkedout.return_value = 2
            mock_pool.overflow.return_value = 0
            mock_pool.invalid.return_value = 0
            
            mock_engine = MagicMock()
            mock_engine.pool = mock_pool
            
            # Mock get_bind to return the engine directly, not a coroutine
            def mock_get_bind():
                return mock_engine
            
            mock_session_instance.get_bind = mock_get_bind
            
            # Mock database queries
            mock_results = [
                # Database size query
                MagicMock(),
                # Table stats query  
                MagicMock(),
                # Index usage query
                MagicMock(),
                # Connections query
                MagicMock()
            ]
            
            # Configure mock results
            mock_results[0].fetchone.return_value = ("100 MB", 104857600)
            mock_results[1].return_value = []
            mock_results[2].return_value = []
            mock_results[3].fetchone.return_value = (10, 2, 8)
            
            mock_session_instance.execute.side_effect = mock_results
            
            result = await repository.get_database_performance_metrics()
            
            assert "connection_pool" in result
            assert "database_size" in result
            assert result["connection_pool"]["size"] == 10
            assert result["database_size"]["human_readable"] == "100 MB"
    
    @pytest.mark.asyncio
    async def test_analyze_query_performance(self, repository):
        """Test query performance analysis."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock EXPLAIN ANALYZE result
            mock_explain_result = [{
                "Plan": {
                    "Node Type": "Seq Scan",
                    "Total Cost": 100.0,
                    "Actual Rows": 1000
                },
                "Execution Time": 15.5,
                "Planning Time": 2.3
            }]
            
            mock_result = MagicMock()
            mock_result.fetchone.return_value = [mock_explain_result]
            mock_session_instance.execute.return_value = mock_result
            
            result = await repository.analyze_query_performance("SELECT * FROM scraped_data")
            
            assert result["execution_time_ms"] == 15.5
            assert result["planning_time_ms"] == 2.3
            assert result["total_cost"] == 100.0
            assert result["actual_rows"] == 1000
            assert result["node_type"] == "Seq Scan"
    
    @pytest.mark.asyncio
    async def test_optimize_database_performance(self, repository):
        """Test database optimization operations."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock optimization queries
            mock_results = [
                # Missing indexes query
                MagicMock(),
                # Unused indexes query
                MagicMock(),
                # Bloat query
                MagicMock()
            ]
            
            # Configure mock results
            mock_results[0].return_value = []
            mock_results[1].return_value = []
            mock_results[2].return_value = []
            
            mock_session_instance.execute.side_effect = [None] + mock_results
            mock_session_instance.commit = AsyncMock()
            
            result = await repository.optimize_database_performance()
            
            assert "analyze_completed" in result
            assert "index_recommendations" in result
            assert "unused_indexes" in result
            assert "table_bloat" in result
            assert "recommendations" in result
            assert result["analyze_completed"] is True


class TestAnalyticsAndReporting:
    """Test cases for analytics and reporting features."""
    
    @pytest.mark.asyncio
    async def test_get_job_statistics(self, repository):
        """Test retrieving job statistics."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock status counts query
            mock_status_result = MagicMock()
            mock_status_rows = [
                MagicMock(status="completed", count=10),
                MagicMock(status="failed", count=2),
                MagicMock(status="pending", count=5)
            ]
            mock_status_result.__iter__ = lambda x: iter(mock_status_rows)
            
            # Mock performance metrics query
            mock_perf_result = MagicMock()
            mock_perf_row = MagicMock()
            mock_perf_row.avg_pages = 25.5
            mock_perf_row.total_pages = 255
            mock_perf_row.avg_duration_seconds = 120.0
            mock_perf_result.first.return_value = mock_perf_row
            
            mock_session_instance.execute.side_effect = [mock_status_result, mock_perf_result]
            
            result = await repository.get_job_statistics()
            
            assert "status_counts" in result
            assert "performance_metrics" in result
            assert result["status_counts"]["completed"] == 10
            assert result["performance_metrics"]["average_pages_per_job"] == 25.5
    
    @pytest.mark.asyncio
    async def test_get_data_quality_metrics(self, repository):
        """Test retrieving data quality metrics."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock quality metrics query
            mock_quality_result = MagicMock()
            mock_quality_row = MagicMock()
            mock_quality_row.avg_confidence = 0.85
            mock_quality_row.avg_quality = 0.90
            mock_quality_row.total_records = 1000
            mock_quality_row.ai_processed_count = 800
            mock_quality_result.first.return_value = mock_quality_row
            
            # Mock error metrics query
            mock_error_result = MagicMock()
            mock_error_row = MagicMock()
            mock_error_row.avg_errors = 1.2
            mock_error_result.first.return_value = mock_error_row
            
            mock_session_instance.execute.side_effect = [mock_quality_result, mock_error_result]
            
            result = await repository.get_data_quality_metrics()
            
            assert result["average_confidence_score"] == 0.85
            assert result["average_quality_score"] == 0.90
            assert result["total_data_records"] == 1000
            assert result["ai_processed_percentage"] == 80.0
            assert result["average_validation_errors"] == 1.2


class TestErrorHandling:
    """Test cases for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, repository, sample_scraping_job):
        """Test handling of database errors."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock SQLAlchemy error
            mock_session_instance.commit.side_effect = SQLAlchemyError("Database connection failed")
            
            with pytest.raises(RuntimeError, match="Failed to create job"):
                await repository.create_job(sample_scraping_job)
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_error_handling(self, repository):
        """Test error handling in performance monitoring."""
        with patch('src.pipeline.repository.get_async_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock get_bind to return an engine that will cause an error when accessing pool
            mock_engine = MagicMock()
            mock_pool = MagicMock()
            mock_pool.size.side_effect = SQLAlchemyError("Connection lost")
            mock_engine.pool = mock_pool
            
            mock_session_instance.get_bind = MagicMock(return_value=mock_engine)
            
            with pytest.raises(RuntimeError, match="Failed to get database performance metrics"):
                await repository.get_database_performance_metrics()


if __name__ == "__main__":
    pytest.main([__file__])