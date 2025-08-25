"""
Unit tests for SQLAlchemy database models.

This module contains tests for the SQLAlchemy ORM models, including
relationships, constraints, and database operations.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.models.database_models import (
    Base,
    ScrapingJobORM,
    ScrapedDataORM,
    JobLogORM,
    SystemMetricORM,
    DataExportORM,
    UserSessionORM
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestScrapingJobORM:
    """Test cases for ScrapingJobORM model."""
    
    def test_create_scraping_job(self, session):
        """Test creating a scraping job."""
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com",
            status="pending",
            config={"wait_time": 5, "max_retries": 3},
            total_pages=10,
            pages_completed=0,
            pages_failed=0,
            retry_count=0,
            user_id="user123",
            tags=["test", "example"],
            priority=5
        )
        
        session.add(job)
        session.commit()
        
        # Verify the job was created
        retrieved_job = session.query(ScrapingJobORM).filter_by(id=job.id).first()
        assert retrieved_job is not None
        assert retrieved_job.url == "https://example.com"
        assert retrieved_job.status == "pending"
        assert retrieved_job.config == {"wait_time": 5, "max_retries": 3}
        assert retrieved_job.total_pages == 10
        assert retrieved_job.pages_completed == 0
        assert retrieved_job.pages_failed == 0
        assert retrieved_job.retry_count == 0
        assert retrieved_job.user_id == "user123"
        assert retrieved_job.tags == ["test", "example"]
        assert retrieved_job.priority == 5
        assert isinstance(retrieved_job.created_at, datetime)
    
    def test_scraping_job_defaults(self, session):
        """Test default values for scraping job."""
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        
        session.add(job)
        session.commit()
        
        retrieved_job = session.query(ScrapingJobORM).filter_by(id=job.id).first()
        assert retrieved_job.status == "pending"
        assert retrieved_job.config == {}
        assert retrieved_job.total_pages == 0
        assert retrieved_job.pages_completed == 0
        assert retrieved_job.pages_failed == 0
        assert retrieved_job.retry_count == 0
        assert retrieved_job.tags == []
        assert retrieved_job.priority == 5
    
    def test_scraping_job_relationships(self, session):
        """Test relationships with other models."""
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Add scraped data
        data = ScrapedDataORM(
            id=str(uuid4()),
            job_id=job.id,
            url="https://example.com",
            content={"title": "Test Page"},
            confidence_score=0.95
        )
        session.add(data)
        
        # Add job log
        log = JobLogORM(
            id=str(uuid4()),
            job_id=job.id,
            level="INFO",
            message="Job started",
            context={}
        )
        session.add(log)
        session.commit()
        
        # Test relationships
        retrieved_job = session.query(ScrapingJobORM).filter_by(id=job.id).first()
        assert len(retrieved_job.scraped_data) == 1
        assert len(retrieved_job.job_logs) == 1
        assert retrieved_job.scraped_data[0].content == {"title": "Test Page"}
        assert retrieved_job.job_logs[0].message == "Job started"
    
    def test_scraping_job_repr(self, session):
        """Test string representation of scraping job."""
        job = ScrapingJobORM(
            id="test-id",
            url="https://example.com",
            status="running"
        )
        
        expected_repr = "<ScrapingJob(id=test-id, url=https://example.com, status=running)>"
        assert repr(job) == expected_repr


class TestScrapedDataORM:
    """Test cases for ScrapedDataORM model."""
    
    def test_create_scraped_data(self, session):
        """Test creating scraped data."""
        # First create a job
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Create scraped data
        data = ScrapedDataORM(
            id=str(uuid4()),
            job_id=job.id,
            url="https://example.com/page1",
            content_type="html",
            content={"title": "Test Page", "text": "Content"},
            raw_html="<html><body>Test</body></html>",
            content_metadata={"source": "scraper"},
            confidence_score=0.95,
            ai_processed=True,
            ai_metadata={"model": "gemini-2.5"},
            data_quality_score=0.88,
            validation_errors=["missing field"],
            content_length=1024,
            load_time=2.5
        )
        
        session.add(data)
        session.commit()
        
        # Verify the data was created
        retrieved_data = session.query(ScrapedDataORM).filter_by(id=data.id).first()
        assert retrieved_data is not None
        assert retrieved_data.job_id == job.id
        assert retrieved_data.url == "https://example.com/page1"
        assert retrieved_data.content_type == "html"
        assert retrieved_data.content == {"title": "Test Page", "text": "Content"}
        assert retrieved_data.raw_html == "<html><body>Test</body></html>"
        assert retrieved_data.content_metadata == {"source": "scraper"}
        assert retrieved_data.confidence_score == 0.95
        assert retrieved_data.ai_processed is True
        assert retrieved_data.ai_metadata == {"model": "gemini-2.5"}
        assert retrieved_data.data_quality_score == 0.88
        assert retrieved_data.validation_errors == ["missing field"]
        assert retrieved_data.content_length == 1024
        assert retrieved_data.load_time == 2.5
        assert isinstance(retrieved_data.extracted_at, datetime)
    
    def test_scraped_data_defaults(self, session):
        """Test default values for scraped data."""
        # First create a job
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Create minimal scraped data
        data = ScrapedDataORM(
            id=str(uuid4()),
            job_id=job.id,
            url="https://example.com",
            content={"title": "Test"}
        )
        
        session.add(data)
        session.commit()
        
        retrieved_data = session.query(ScrapedDataORM).filter_by(id=data.id).first()
        assert retrieved_data.content_type == "html"
        assert retrieved_data.content_metadata == {}
        assert retrieved_data.confidence_score == 0.0
        assert retrieved_data.ai_processed is False
        assert retrieved_data.ai_metadata == {}
        assert retrieved_data.data_quality_score == 0.0
        assert retrieved_data.validation_errors == []
        assert retrieved_data.content_length == 0
        assert retrieved_data.load_time == 0.0
    
    def test_scraped_data_foreign_key_constraint(self, session):
        """Test foreign key constraint for job_id."""
        # Try to create scraped data with non-existent job_id
        data = ScrapedDataORM(
            id=str(uuid4()),
            job_id="non-existent-job",
            url="https://example.com",
            content={"title": "Test"}
        )
        
        session.add(data)
        
        # This should raise an integrity error due to foreign key constraint
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_scraped_data_relationship(self, session):
        """Test relationship with job."""
        # Create a job
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Create scraped data
        data = ScrapedDataORM(
            id=str(uuid4()),
            job_id=job.id,
            url="https://example.com",
            content={"title": "Test"}
        )
        session.add(data)
        session.commit()
        
        # Test relationship
        retrieved_data = session.query(ScrapedDataORM).filter_by(id=data.id).first()
        assert retrieved_data.job is not None
        assert retrieved_data.job.id == job.id
        assert retrieved_data.job.url == "https://example.com"
    
    def test_scraped_data_repr(self, session):
        """Test string representation of scraped data."""
        data = ScrapedDataORM(
            id="test-data-id",
            job_id="test-job-id",
            url="https://example.com",
            content={"title": "Test"}
        )
        
        expected_repr = "<ScrapedData(id=test-data-id, job_id=test-job-id, url=https://example.com)>"
        assert repr(data) == expected_repr


class TestJobLogORM:
    """Test cases for JobLogORM model."""
    
    def test_create_job_log(self, session):
        """Test creating a job log."""
        # First create a job
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Create job log
        log = JobLogORM(
            id=str(uuid4()),
            job_id=job.id,
            level="ERROR",
            message="Connection timeout occurred",
            context={"url": "https://example.com", "timeout": 30}
        )
        
        session.add(log)
        session.commit()
        
        # Verify the log was created
        retrieved_log = session.query(JobLogORM).filter_by(id=log.id).first()
        assert retrieved_log is not None
        assert retrieved_log.job_id == job.id
        assert retrieved_log.level == "ERROR"
        assert retrieved_log.message == "Connection timeout occurred"
        assert retrieved_log.context == {"url": "https://example.com", "timeout": 30}
        assert isinstance(retrieved_log.created_at, datetime)
    
    def test_job_log_defaults(self, session):
        """Test default values for job log."""
        # First create a job
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Create minimal job log
        log = JobLogORM(
            id=str(uuid4()),
            job_id=job.id,
            level="INFO",
            message="Test message"
        )
        
        session.add(log)
        session.commit()
        
        retrieved_log = session.query(JobLogORM).filter_by(id=log.id).first()
        assert retrieved_log.context == {}
    
    def test_job_log_relationship(self, session):
        """Test relationship with job."""
        # Create a job
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Create job log
        log = JobLogORM(
            id=str(uuid4()),
            job_id=job.id,
            level="INFO",
            message="Test message"
        )
        session.add(log)
        session.commit()
        
        # Test relationship
        retrieved_log = session.query(JobLogORM).filter_by(id=log.id).first()
        assert retrieved_log.job is not None
        assert retrieved_log.job.id == job.id
    
    def test_job_log_repr(self, session):
        """Test string representation of job log."""
        log = JobLogORM(
            id="test-log-id",
            job_id="test-job-id",
            level="INFO",
            message="Test message"
        )
        
        expected_repr = "<JobLog(id=test-log-id, job_id=test-job-id, level=INFO)>"
        assert repr(log) == expected_repr


class TestSystemMetricORM:
    """Test cases for SystemMetricORM model."""
    
    def test_create_system_metric(self, session):
        """Test creating a system metric."""
        metric = SystemMetricORM(
            id=str(uuid4()),
            metric_name="cpu_usage",
            metric_value=75.5,
            metric_unit="percent",
            tags={"host": "server1", "environment": "production"}
        )
        
        session.add(metric)
        session.commit()
        
        # Verify the metric was created
        retrieved_metric = session.query(SystemMetricORM).filter_by(id=metric.id).first()
        assert retrieved_metric is not None
        assert retrieved_metric.metric_name == "cpu_usage"
        assert retrieved_metric.metric_value == 75.5
        assert retrieved_metric.metric_unit == "percent"
        assert retrieved_metric.tags == {"host": "server1", "environment": "production"}
        assert isinstance(retrieved_metric.recorded_at, datetime)
    
    def test_system_metric_defaults(self, session):
        """Test default values for system metric."""
        metric = SystemMetricORM(
            id=str(uuid4()),
            metric_name="memory_usage",
            metric_value=1024.0
        )
        
        session.add(metric)
        session.commit()
        
        retrieved_metric = session.query(SystemMetricORM).filter_by(id=metric.id).first()
        assert retrieved_metric.metric_unit is None
        assert retrieved_metric.tags == {}
    
    def test_system_metric_repr(self, session):
        """Test string representation of system metric."""
        now = datetime.utcnow()
        metric = SystemMetricORM(
            metric_name="cpu_usage",
            metric_value=75.5,
            recorded_at=now
        )
        
        expected_repr = f"<SystemMetric(name=cpu_usage, value=75.5, recorded_at={now})>"
        assert repr(metric) == expected_repr


class TestDataExportORM:
    """Test cases for DataExportORM model."""
    
    def test_create_data_export(self, session):
        """Test creating a data export."""
        export = DataExportORM(
            id=str(uuid4()),
            format="csv",
            status="completed",
            job_ids=["job1", "job2"],
            date_from=datetime.utcnow() - timedelta(days=7),
            date_to=datetime.utcnow(),
            min_confidence=0.8,
            include_raw_html=True,
            fields=["title", "content"],
            file_path="/exports/data.csv",
            file_size=1024000,
            completed_at=datetime.utcnow(),
            user_id="user123"
        )
        
        session.add(export)
        session.commit()
        
        # Verify the export was created
        retrieved_export = session.query(DataExportORM).filter_by(id=export.id).first()
        assert retrieved_export is not None
        assert retrieved_export.format == "csv"
        assert retrieved_export.status == "completed"
        assert retrieved_export.job_ids == ["job1", "job2"]
        assert retrieved_export.min_confidence == 0.8
        assert retrieved_export.include_raw_html is True
        assert retrieved_export.fields == ["title", "content"]
        assert retrieved_export.file_path == "/exports/data.csv"
        assert retrieved_export.file_size == 1024000
        assert retrieved_export.user_id == "user123"
        assert isinstance(retrieved_export.requested_at, datetime)
    
    def test_data_export_defaults(self, session):
        """Test default values for data export."""
        export = DataExportORM(
            id=str(uuid4()),
            format="json"
        )
        
        session.add(export)
        session.commit()
        
        retrieved_export = session.query(DataExportORM).filter_by(id=export.id).first()
        assert retrieved_export.status == "pending"
        assert retrieved_export.job_ids == []
        assert retrieved_export.min_confidence == 0.0
        assert retrieved_export.include_raw_html is False
        assert retrieved_export.fields == []
    
    def test_data_export_repr(self, session):
        """Test string representation of data export."""
        export = DataExportORM(
            id="test-export-id",
            format="csv",
            status="pending"
        )
        
        expected_repr = "<DataExport(id=test-export-id, format=csv, status=pending)>"
        assert repr(export) == expected_repr


class TestUserSessionORM:
    """Test cases for UserSessionORM model."""
    
    def test_create_user_session(self, session):
        """Test creating a user session."""
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        user_session = UserSessionORM(
            id=str(uuid4()),
            user_id="user123",
            session_token="abc123def456",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            expires_at=expires_at,
            is_active=True
        )
        
        session.add(user_session)
        session.commit()
        
        # Verify the session was created
        retrieved_session = session.query(UserSessionORM).filter_by(id=user_session.id).first()
        assert retrieved_session is not None
        assert retrieved_session.user_id == "user123"
        assert retrieved_session.session_token == "abc123def456"
        assert retrieved_session.ip_address == "192.168.1.100"
        assert retrieved_session.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        assert retrieved_session.expires_at == expires_at
        assert retrieved_session.is_active is True
        assert isinstance(retrieved_session.created_at, datetime)
        assert isinstance(retrieved_session.last_accessed, datetime)
    
    def test_user_session_defaults(self, session):
        """Test default values for user session."""
        user_session = UserSessionORM(
            id=str(uuid4()),
            user_id="user123",
            session_token="abc123def456",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        session.add(user_session)
        session.commit()
        
        retrieved_session = session.query(UserSessionORM).filter_by(id=user_session.id).first()
        assert retrieved_session.ip_address is None
        assert retrieved_session.user_agent is None
        assert retrieved_session.is_active is True
    
    def test_user_session_unique_token(self, session):
        """Test unique constraint on session token."""
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Create first session
        session1 = UserSessionORM(
            id=str(uuid4()),
            user_id="user123",
            session_token="duplicate_token",
            expires_at=expires_at
        )
        session.add(session1)
        session.commit()
        
        # Try to create second session with same token
        session2 = UserSessionORM(
            id=str(uuid4()),
            user_id="user456",
            session_token="duplicate_token",
            expires_at=expires_at
        )
        session.add(session2)
        
        # This should raise an integrity error due to unique constraint
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_user_session_repr(self, session):
        """Test string representation of user session."""
        user_session = UserSessionORM(
            id="test-session-id",
            user_id="user123",
            session_token="abc123",
            expires_at=datetime.utcnow(),
            is_active=True
        )
        
        expected_repr = "<UserSession(id=test-session-id, user_id=user123, active=True)>"
        assert repr(user_session) == expected_repr


class TestCascadeDeletes:
    """Test cascade delete behavior."""
    
    def test_job_deletion_cascades_to_data_and_logs(self, session):
        """Test that deleting a job cascades to scraped data and logs."""
        # Create a job
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Add scraped data
        data = ScrapedDataORM(
            id=str(uuid4()),
            job_id=job.id,
            url="https://example.com",
            content={"title": "Test"}
        )
        session.add(data)
        
        # Add job log
        log = JobLogORM(
            id=str(uuid4()),
            job_id=job.id,
            level="INFO",
            message="Test message"
        )
        session.add(log)
        session.commit()
        
        # Verify data and log exist
        assert session.query(ScrapedDataORM).filter_by(job_id=job.id).count() == 1
        assert session.query(JobLogORM).filter_by(job_id=job.id).count() == 1
        
        # Delete the job
        session.delete(job)
        session.commit()
        
        # Verify cascaded deletion
        assert session.query(ScrapedDataORM).filter_by(job_id=job.id).count() == 0
        assert session.query(JobLogORM).filter_by(job_id=job.id).count() == 0


class TestIndexes:
    """Test database indexes are working correctly."""
    
    def test_job_indexes(self, session):
        """Test that job indexes are created and functional."""
        # Create multiple jobs with different statuses and priorities
        jobs = [
            ScrapingJobORM(
                id=str(uuid4()),
                url="https://example1.com",
                status="pending",
                priority=1,
                user_id="user1"
            ),
            ScrapingJobORM(
                id=str(uuid4()),
                url="https://example2.com",
                status="running",
                priority=5,
                user_id="user1"
            ),
            ScrapingJobORM(
                id=str(uuid4()),
                url="https://example3.com",
                status="completed",
                priority=10,
                user_id="user2"
            )
        ]
        
        for job in jobs:
            session.add(job)
        session.commit()
        
        # Test queries that should use indexes
        pending_jobs = session.query(ScrapingJobORM).filter_by(status="pending").all()
        assert len(pending_jobs) == 1
        
        user1_jobs = session.query(ScrapingJobORM).filter_by(user_id="user1").all()
        assert len(user1_jobs) == 2
        
        high_priority_jobs = session.query(ScrapingJobORM).filter(ScrapingJobORM.priority <= 5).all()
        assert len(high_priority_jobs) == 2
    
    def test_data_indexes(self, session):
        """Test that scraped data indexes are functional."""
        # Create a job first
        job = ScrapingJobORM(
            id=str(uuid4()),
            url="https://example.com"
        )
        session.add(job)
        session.commit()
        
        # Create multiple data records
        data_records = [
            ScrapedDataORM(
                id=str(uuid4()),
                job_id=job.id,
                url="https://example.com/page1",
                content={"title": "Page 1"},
                confidence_score=0.9,
                ai_processed=True
            ),
            ScrapedDataORM(
                id=str(uuid4()),
                job_id=job.id,
                url="https://example.com/page2",
                content={"title": "Page 2"},
                confidence_score=0.7,
                ai_processed=False
            )
        ]
        
        for data in data_records:
            session.add(data)
        session.commit()
        
        # Test queries that should use indexes
        high_confidence_data = session.query(ScrapedDataORM).filter(
            ScrapedDataORM.confidence_score >= 0.8
        ).all()
        assert len(high_confidence_data) == 1
        
        ai_processed_data = session.query(ScrapedDataORM).filter_by(ai_processed=True).all()
        assert len(ai_processed_data) == 1
        
        job_data = session.query(ScrapedDataORM).filter_by(job_id=job.id).all()
        assert len(job_data) == 2