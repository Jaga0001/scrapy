"""
Data repository and storage layer for scraped data management.

This module provides the DataRepository class that handles all database operations
for scraped data, jobs, and related entities with async PostgreSQL support.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from sqlalchemy import and_, desc, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import literal_column

from config.database import get_async_db_session
from src.models.database_models import (
    DataExportORM, JobLogORM, ScrapedDataORM, ScrapingJobORM, SystemMetricORM
)
from src.models.pydantic_models import (
    DataExportRequest, JobStatus, ScrapedData, ScrapingJob
)

logger = logging.getLogger(__name__)


class DataRepository:
    """
    Repository class for managing scraped data and job information.
    
    Provides async CRUD operations, filtering, and performance-optimized queries
    for all database entities in the web scraping system.
    """
    
    def __init__(self):
        """Initialize the repository."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # ==================== Job Management Methods ====================
    
    async def create_job(self, job: ScrapingJob) -> str:
        """
        Create a new scraping job in the database.
        
        Args:
            job: ScrapingJob instance to create
            
        Returns:
            str: The created job ID
            
        Raises:
            ValueError: If job data is invalid
            RuntimeError: If database operation fails
        """
        try:
            async with get_async_db_session() as session:
                job_orm = ScrapingJobORM(
                    id=job.id,
                    url=job.url,
                    status=job.status.value,
                    config=job.config.model_dump(),
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    total_pages=job.total_pages,
                    pages_completed=job.pages_completed,
                    pages_failed=job.pages_failed,
                    error_message=job.error_message,
                    retry_count=job.retry_count,
                    user_id=job.user_id,
                    tags=job.tags,
                    priority=job.priority
                )
                
                session.add(job_orm)
                await session.commit()
                await session.refresh(job_orm)
                
                self.logger.info(f"Created job {job.id} for URL: {job.url}")
                return job_orm.id
                
        except IntegrityError as e:
            self.logger.error(f"Job creation failed - integrity error: {e}")
            raise ValueError(f"Job with ID {job.id} already exists")
        except SQLAlchemyError as e:
            self.logger.error(f"Job creation failed - database error: {e}")
            raise RuntimeError(f"Failed to create job: {e}")
    
    async def get_job(self, job_id: str) -> Optional[ScrapingJob]:
        """
        Retrieve a scraping job by ID.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            ScrapingJob instance or None if not found
        """
        try:
            async with get_async_db_session() as session:
                stmt = select(ScrapingJobORM).where(ScrapingJobORM.id == job_id)
                result = await session.execute(stmt)
                job_orm = result.scalar_one_or_none()
                
                if job_orm:
                    return self._orm_to_pydantic_job(job_orm)
                return None
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve job {job_id}: {e}")
            raise RuntimeError(f"Failed to retrieve job: {e}")
    
    async def update_job_status(
        self, 
        job_id: str, 
        status: JobStatus,
        error_message: Optional[str] = None,
        pages_completed: Optional[int] = None,
        pages_failed: Optional[int] = None
    ) -> bool:
        """
        Update job status and related fields.
        
        Args:
            job_id: Job identifier
            status: New job status
            error_message: Error message if status is FAILED
            pages_completed: Number of completed pages
            pages_failed: Number of failed pages
            
        Returns:
            bool: True if update was successful
        """
        try:
            async with get_async_db_session() as session:
                update_data = {"status": status.value}
                
                # Set timestamps based on status
                if status == JobStatus.RUNNING:
                    update_data["started_at"] = datetime.utcnow()
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    update_data["completed_at"] = datetime.utcnow()
                
                # Update optional fields
                if error_message is not None:
                    update_data["error_message"] = error_message
                if pages_completed is not None:
                    update_data["pages_completed"] = pages_completed
                if pages_failed is not None:
                    update_data["pages_failed"] = pages_failed
                
                stmt = (
                    update(ScrapingJobORM)
                    .where(ScrapingJobORM.id == job_id)
                    .values(**update_data)
                )
                
                result = await session.execute(stmt)
                await session.commit()
                
                success = result.rowcount > 0
                if success:
                    self.logger.info(f"Updated job {job_id} status to {status.value}")
                else:
                    self.logger.warning(f"Job {job_id} not found for status update")
                
                return success
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to update job {job_id} status: {e}")
            raise RuntimeError(f"Failed to update job status: {e}")
    
    async def get_jobs_by_status(
        self, 
        status: JobStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[ScrapingJob]:
        """
        Retrieve jobs by status with pagination.
        
        Args:
            status: Job status to filter by
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of ScrapingJob instances
        """
        try:
            async with get_async_db_session() as session:
                stmt = (
                    select(ScrapingJobORM)
                    .where(ScrapingJobORM.status == status.value)
                    .order_by(desc(ScrapingJobORM.created_at))
                    .limit(limit)
                    .offset(offset)
                )
                
                result = await session.execute(stmt)
                job_orms = result.scalars().all()
                
                return [self._orm_to_pydantic_job(job_orm) for job_orm in job_orms]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve jobs by status {status}: {e}")
            raise RuntimeError(f"Failed to retrieve jobs: {e}")
    
    async def get_jobs_by_user(
        self, 
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScrapingJob]:
        """
        Retrieve jobs for a specific user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of ScrapingJob instances
        """
        try:
            async with get_async_db_session() as session:
                stmt = (
                    select(ScrapingJobORM)
                    .where(ScrapingJobORM.user_id == user_id)
                    .order_by(desc(ScrapingJobORM.created_at))
                    .limit(limit)
                    .offset(offset)
                )
                
                result = await session.execute(stmt)
                job_orms = result.scalars().all()
                
                return [self._orm_to_pydantic_job(job_orm) for job_orm in job_orms]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve jobs for user {user_id}: {e}")
            raise RuntimeError(f"Failed to retrieve user jobs: {e}")
    
    # ==================== Scraped Data Management Methods ====================
    
    async def save_scraped_data(self, data: ScrapedData) -> str:
        """
        Save scraped data to the database.
        
        Args:
            data: ScrapedData instance to save
            
        Returns:
            str: The saved data record ID
            
        Raises:
            ValueError: If data is invalid
            RuntimeError: If database operation fails
        """
        try:
            async with get_async_db_session() as session:
                data_orm = ScrapedDataORM(
                    id=data.id,
                    job_id=data.job_id,
                    url=data.url,
                    content_type=data.content_type.value,
                    content=data.content,
                    raw_html=data.raw_html,
                    content_metadata=data.content_metadata,
                    confidence_score=data.confidence_score,
                    ai_processed=data.ai_processed,
                    ai_metadata=data.ai_metadata,
                    data_quality_score=data.data_quality_score,
                    validation_errors=data.validation_errors,
                    extracted_at=data.extracted_at,
                    processed_at=data.processed_at,
                    content_length=data.content_length,
                    load_time=data.load_time
                )
                
                session.add(data_orm)
                await session.commit()
                await session.refresh(data_orm)
                
                self.logger.debug(f"Saved scraped data {data.id} for job {data.job_id}")
                return data_orm.id
                
        except IntegrityError as e:
            self.logger.error(f"Data save failed - integrity error: {e}")
            raise ValueError(f"Data with ID {data.id} already exists or invalid job_id")
        except SQLAlchemyError as e:
            self.logger.error(f"Data save failed - database error: {e}")
            raise RuntimeError(f"Failed to save scraped data: {e}")
    
    async def get_scraped_data(
        self,
        job_id: Optional[str] = None,
        min_confidence: float = 0.0,
        min_quality: float = 0.0,
        ai_processed_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ScrapedData], int]:
        """
        Retrieve scraped data with filtering and pagination.
        
        Args:
            job_id: Filter by specific job ID
            min_confidence: Minimum confidence score
            min_quality: Minimum data quality score
            ai_processed_only: Only return AI-processed data
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            Tuple of (data_list, total_count)
        """
        try:
            async with self._monitor_query_performance("get_scraped_data"):
                async with get_async_db_session() as session:
                    # Build filter conditions
                    conditions = []
                    
                    if job_id:
                        conditions.append(ScrapedDataORM.job_id == job_id)
                    if min_confidence > 0:
                        conditions.append(ScrapedDataORM.confidence_score >= min_confidence)
                    if min_quality > 0:
                        conditions.append(ScrapedDataORM.data_quality_score >= min_quality)
                    if ai_processed_only:
                        conditions.append(ScrapedDataORM.ai_processed == True)
                    
                    # Count total records
                    count_stmt = select(func.count(ScrapedDataORM.id))
                    if conditions:
                        count_stmt = count_stmt.where(and_(*conditions))
                    
                    count_result = await session.execute(count_stmt)
                    total_count = count_result.scalar()
                    
                    # Get data records with optimized query
                    data_stmt = select(ScrapedDataORM)
                    if conditions:
                        data_stmt = data_stmt.where(and_(*conditions))
                    
                    data_stmt = (
                        data_stmt
                        .order_by(desc(ScrapedDataORM.extracted_at))
                        .limit(limit)
                        .offset(offset)
                    )
                    
                    data_result = await session.execute(data_stmt)
                    data_orms = data_result.scalars().all()
                    
                    scraped_data = [self._orm_to_pydantic_data(data_orm) for data_orm in data_orms]
                    
                    return scraped_data, total_count
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve scraped data: {e}")
            raise RuntimeError(f"Failed to retrieve scraped data: {e}")
    
    async def get_data_by_url_pattern(
        self, 
        url_pattern: str,
        limit: int = 100
    ) -> List[ScrapedData]:
        """
        Retrieve scraped data by URL pattern matching.
        
        Args:
            url_pattern: URL pattern to match (supports SQL LIKE syntax)
            limit: Maximum number of records to return
            
        Returns:
            List of ScrapedData instances
        """
        try:
            async with get_async_db_session() as session:
                stmt = (
                    select(ScrapedDataORM)
                    .where(ScrapedDataORM.url.like(url_pattern))
                    .order_by(desc(ScrapedDataORM.extracted_at))
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                data_orms = result.scalars().all()
                
                return [self._orm_to_pydantic_data(data_orm) for data_orm in data_orms]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve data by URL pattern: {e}")
            raise RuntimeError(f"Failed to retrieve data by URL pattern: {e}")
    
    async def update_data_ai_processing(
        self,
        data_id: str,
        confidence_score: float,
        ai_metadata: Dict[str, Any],
        data_quality_score: float,
        validation_errors: List[str]
    ) -> bool:
        """
        Update scraped data with AI processing results.
        
        Args:
            data_id: Data record identifier
            confidence_score: AI confidence score
            ai_metadata: AI processing metadata
            data_quality_score: Data quality score
            validation_errors: List of validation errors
            
        Returns:
            bool: True if update was successful
        """
        try:
            async with get_async_db_session() as session:
                stmt = (
                    update(ScrapedDataORM)
                    .where(ScrapedDataORM.id == data_id)
                    .values(
                        confidence_score=confidence_score,
                        ai_processed=True,
                        ai_metadata=ai_metadata,
                        data_quality_score=data_quality_score,
                        validation_errors=validation_errors,
                        processed_at=datetime.utcnow()
                    )
                )
                
                result = await session.execute(stmt)
                await session.commit()
                
                success = result.rowcount > 0
                if success:
                    self.logger.debug(f"Updated AI processing for data {data_id}")
                
                return success
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to update AI processing for data {data_id}: {e}")
            raise RuntimeError(f"Failed to update AI processing: {e}")
    
    # ==================== Logging Methods ====================
    
    async def add_job_log(
        self,
        job_id: str,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a log entry for a scraping job.
        
        Args:
            job_id: Job identifier
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            context: Additional context data
            
        Returns:
            str: Log entry ID
        """
        try:
            async with get_async_db_session() as session:
                log_orm = JobLogORM(
                    id=str(uuid4()),
                    job_id=job_id,
                    level=level.upper(),
                    message=message,
                    context=context or {},
                    created_at=datetime.utcnow()
                )
                
                session.add(log_orm)
                await session.commit()
                await session.refresh(log_orm)
                
                return log_orm.id
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to add job log: {e}")
            raise RuntimeError(f"Failed to add job log: {e}")
    
    async def get_job_logs(
        self,
        job_id: str,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs for a specific job.
        
        Args:
            job_id: Job identifier
            level: Filter by log level
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            
        Returns:
            List of log dictionaries
        """
        try:
            async with get_async_db_session() as session:
                stmt = select(JobLogORM).where(JobLogORM.job_id == job_id)
                
                if level:
                    stmt = stmt.where(JobLogORM.level == level.upper())
                
                stmt = (
                    stmt
                    .order_by(desc(JobLogORM.created_at))
                    .limit(limit)
                    .offset(offset)
                )
                
                result = await session.execute(stmt)
                log_orms = result.scalars().all()
                
                return [
                    {
                        "id": log.id,
                        "job_id": log.job_id,
                        "level": log.level,
                        "message": log.message,
                        "context": log.context,
                        "created_at": log.created_at
                    }
                    for log in log_orms
                ]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve job logs: {e}")
            raise RuntimeError(f"Failed to retrieve job logs: {e}")
    
    # ==================== System Metrics Methods ====================
    
    async def record_system_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a system performance metric.
        
        Args:
            metric_name: Name of the metric
            metric_value: Metric value
            metric_unit: Unit of measurement
            tags: Additional tags for the metric
            
        Returns:
            str: Metric record ID
        """
        try:
            async with get_async_db_session() as session:
                metric_orm = SystemMetricORM(
                    id=str(uuid4()),
                    metric_name=metric_name,
                    metric_value=metric_value,
                    metric_unit=metric_unit,
                    tags=tags or {},
                    recorded_at=datetime.utcnow()
                )
                
                session.add(metric_orm)
                await session.commit()
                await session.refresh(metric_orm)
                
                return metric_orm.id
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to record system metric: {e}")
            raise RuntimeError(f"Failed to record system metric: {e}")
    
    async def get_system_metrics(
        self,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve system metrics with filtering.
        
        Args:
            metric_name: Filter by metric name
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of metrics to return
            
        Returns:
            List of metric dictionaries
        """
        try:
            async with get_async_db_session() as session:
                stmt = select(SystemMetricORM)
                
                conditions = []
                if metric_name:
                    conditions.append(SystemMetricORM.metric_name == metric_name)
                if start_time:
                    conditions.append(SystemMetricORM.recorded_at >= start_time)
                if end_time:
                    conditions.append(SystemMetricORM.recorded_at <= end_time)
                
                if conditions:
                    stmt = stmt.where(and_(*conditions))
                
                stmt = (
                    stmt
                    .order_by(desc(SystemMetricORM.recorded_at))
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                metric_orms = result.scalars().all()
                
                return [
                    {
                        "id": metric.id,
                        "metric_name": metric.metric_name,
                        "metric_value": metric.metric_value,
                        "metric_unit": metric.metric_unit,
                        "tags": metric.tags,
                        "recorded_at": metric.recorded_at
                    }
                    for metric in metric_orms
                ]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve system metrics: {e}")
            raise RuntimeError(f"Failed to retrieve system metrics: {e}")
    
    # ==================== Analytics and Reporting Methods ====================
    
    async def get_job_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive job statistics.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary containing job statistics
        """
        try:
            async with get_async_db_session() as session:
                # Base query conditions
                conditions = []
                if start_date:
                    conditions.append(ScrapingJobORM.created_at >= start_date)
                if end_date:
                    conditions.append(ScrapingJobORM.created_at <= end_date)
                
                # Job counts by status
                status_stmt = (
                    select(
                        ScrapingJobORM.status,
                        func.count(ScrapingJobORM.id).label('count')
                    )
                    .group_by(ScrapingJobORM.status)
                )
                
                if conditions:
                    status_stmt = status_stmt.where(and_(*conditions))
                
                status_result = await session.execute(status_stmt)
                status_counts = {row.status: row.count for row in status_result}
                
                # Performance metrics
                perf_stmt = select(
                    func.avg(ScrapingJobORM.pages_completed).label('avg_pages'),
                    func.sum(ScrapingJobORM.pages_completed).label('total_pages'),
                    func.avg(
                        func.extract('epoch', ScrapingJobORM.completed_at - ScrapingJobORM.started_at)
                    ).label('avg_duration_seconds')
                ).where(ScrapingJobORM.status == 'completed')
                
                if conditions:
                    perf_stmt = perf_stmt.where(and_(*conditions))
                
                perf_result = await session.execute(perf_stmt)
                perf_row = perf_result.first()
                
                return {
                    "status_counts": status_counts,
                    "performance_metrics": {
                        "average_pages_per_job": float(perf_row.avg_pages or 0),
                        "total_pages_scraped": int(perf_row.total_pages or 0),
                        "average_job_duration_seconds": float(perf_row.avg_duration_seconds or 0)
                    },
                    "date_range": {
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None
                    }
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get job statistics: {e}")
            raise RuntimeError(f"Failed to get job statistics: {e}")
    
    async def get_data_quality_metrics(self) -> Dict[str, Any]:
        """
        Get data quality metrics across all scraped data.
        
        Returns:
            Dictionary containing data quality metrics
        """
        try:
            async with get_async_db_session() as session:
                # Quality score statistics
                quality_stmt = select(
                    func.avg(ScrapedDataORM.confidence_score).label('avg_confidence'),
                    func.avg(ScrapedDataORM.data_quality_score).label('avg_quality'),
                    func.count(ScrapedDataORM.id).label('total_records'),
                    func.count(ScrapedDataORM.id).filter(
                        ScrapedDataORM.ai_processed == True
                    ).label('ai_processed_count')
                )
                
                quality_result = await session.execute(quality_stmt)
                quality_row = quality_result.first()
                
                # Error statistics
                error_stmt = select(
                    func.avg(func.array_length(ScrapedDataORM.validation_errors, 1)).label('avg_errors')
                ).where(ScrapedDataORM.validation_errors != [])
                
                error_result = await session.execute(error_stmt)
                error_row = error_result.first()
                
                return {
                    "average_confidence_score": float(quality_row.avg_confidence or 0),
                    "average_quality_score": float(quality_row.avg_quality or 0),
                    "total_data_records": int(quality_row.total_records or 0),
                    "ai_processed_percentage": (
                        (quality_row.ai_processed_count / quality_row.total_records * 100)
                        if quality_row.total_records > 0 else 0
                    ),
                    "average_validation_errors": float(error_row.avg_errors or 0)
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get data quality metrics: {e}")
            raise RuntimeError(f"Failed to get data quality metrics: {e}")
    
    # ==================== Cleanup and Maintenance Methods ====================
    
    async def cleanup_old_data(
        self,
        retention_days: int = 30,
        dry_run: bool = True
    ) -> Dict[str, int]:
        """
        Clean up old data based on retention policy.
        
        Args:
            retention_days: Number of days to retain data
            dry_run: If True, only count records without deleting
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            async with get_async_db_session() as session:
                # Count old records
                old_jobs_stmt = select(func.count(ScrapingJobORM.id)).where(
                    ScrapingJobORM.created_at < cutoff_date
                )
                old_data_stmt = select(func.count(ScrapedDataORM.id)).where(
                    ScrapedDataORM.extracted_at < cutoff_date
                )
                old_logs_stmt = select(func.count(JobLogORM.id)).where(
                    JobLogORM.created_at < cutoff_date
                )
                
                old_jobs_count = (await session.execute(old_jobs_stmt)).scalar()
                old_data_count = (await session.execute(old_data_stmt)).scalar()
                old_logs_count = (await session.execute(old_logs_stmt)).scalar()
                
                cleanup_stats = {
                    "old_jobs_count": old_jobs_count,
                    "old_data_count": old_data_count,
                    "old_logs_count": old_logs_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "dry_run": dry_run
                }
                
                if not dry_run and (old_jobs_count > 0 or old_data_count > 0 or old_logs_count > 0):
                    # Delete old records (cascading will handle related data)
                    delete_jobs_stmt = ScrapingJobORM.__table__.delete().where(
                        ScrapingJobORM.created_at < cutoff_date
                    )
                    delete_logs_stmt = JobLogORM.__table__.delete().where(
                        JobLogORM.created_at < cutoff_date
                    )
                    
                    await session.execute(delete_jobs_stmt)
                    await session.execute(delete_logs_stmt)
                    await session.commit()
                    
                    self.logger.info(f"Cleaned up {old_jobs_count} jobs and {old_logs_count} logs")
                
                return cleanup_stats
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            raise RuntimeError(f"Failed to cleanup old data: {e}")
    
    # ==================== Performance Monitoring and Optimization ====================
    
    @asynccontextmanager
    async def _monitor_query_performance(self, operation_name: str):
        """
        Context manager to monitor query performance and log metrics.
        
        Args:
            operation_name: Name of the database operation being monitored
        """
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            
            # Log performance metrics
            self.logger.debug(f"Query '{operation_name}' took {execution_time:.3f}s")
            
            # Record metric in database for historical analysis
            try:
                await self.record_system_metric(
                    metric_name=f"db_query_time_{operation_name}",
                    metric_value=execution_time,
                    metric_unit="seconds",
                    tags={"operation": operation_name}
                )
            except Exception as e:
                # Don't fail the main operation if metric recording fails
                self.logger.warning(f"Failed to record performance metric: {e}")
    
    async def analyze_query_performance(self, query: str) -> Dict[str, Any]:
        """
        Analyze query performance using PostgreSQL EXPLAIN ANALYZE.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Dictionary containing query execution plan and performance metrics
        """
        try:
            async with get_async_db_session() as session:
                # Execute EXPLAIN ANALYZE
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                result = await session.execute(text(explain_query))
                explain_result = result.fetchone()[0]
                
                # Extract key performance metrics
                plan = explain_result[0]["Plan"]
                execution_time = explain_result[0]["Execution Time"]
                planning_time = explain_result[0]["Planning Time"]
                
                return {
                    "execution_time_ms": execution_time,
                    "planning_time_ms": planning_time,
                    "total_cost": plan.get("Total Cost", 0),
                    "actual_rows": plan.get("Actual Rows", 0),
                    "node_type": plan.get("Node Type", "Unknown"),
                    "full_plan": explain_result
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to analyze query performance: {e}")
            raise RuntimeError(f"Failed to analyze query performance: {e}")
    
    async def get_database_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive database performance metrics.
        
        Returns:
            Dictionary containing various database performance metrics
        """
        try:
            async with get_async_db_session() as session:
                metrics = {}
                
                # Connection pool metrics
                engine = session.get_bind()
                pool = engine.pool
                
                metrics["connection_pool"] = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
                
                # Database size metrics
                db_size_query = """
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as database_size,
                        pg_database_size(current_database()) as database_size_bytes
                """
                result = await session.execute(text(db_size_query))
                size_row = result.fetchone()
                
                metrics["database_size"] = {
                    "human_readable": size_row[0],
                    "bytes": size_row[1]
                }
                
                # Table statistics
                table_stats_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_tuples,
                        n_dead_tup as dead_tuples,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                """
                result = await session.execute(text(table_stats_query))
                table_stats = [dict(row._mapping) for row in result]
                
                metrics["table_statistics"] = table_stats
                
                # Index usage statistics
                index_usage_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_tup_read,
                        idx_tup_fetch,
                        idx_scan
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    ORDER BY idx_scan DESC
                """
                result = await session.execute(text(index_usage_query))
                index_stats = [dict(row._mapping) for row in result]
                
                metrics["index_usage"] = index_stats
                
                # Active connections
                connections_query = """
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """
                result = await session.execute(text(connections_query))
                conn_row = result.fetchone()
                
                metrics["connections"] = {
                    "total": conn_row[0],
                    "active": conn_row[1],
                    "idle": conn_row[2]
                }
                
                return metrics
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get database performance metrics: {e}")
            raise RuntimeError(f"Failed to get database performance metrics: {e}")
    
    async def optimize_database_performance(self) -> Dict[str, Any]:
        """
        Perform database optimization tasks and return results.
        
        Returns:
            Dictionary containing optimization results and recommendations
        """
        try:
            async with get_async_db_session() as session:
                optimization_results = {}
                
                # Analyze table statistics
                analyze_query = "ANALYZE"
                await session.execute(text(analyze_query))
                optimization_results["analyze_completed"] = True
                
                # Check for missing indexes
                missing_indexes_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        idx_tup_fetch,
                        CASE 
                            WHEN seq_scan > 0 AND idx_scan = 0 THEN 'Consider adding index'
                            WHEN seq_tup_read > idx_tup_fetch * 10 THEN 'High sequential scan ratio'
                            ELSE 'OK'
                        END as recommendation
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    AND (seq_scan > idx_scan OR idx_scan = 0)
                """
                result = await session.execute(text(missing_indexes_query))
                missing_indexes = [dict(row._mapping) for row in result]
                
                optimization_results["index_recommendations"] = missing_indexes
                
                # Check for unused indexes
                unused_indexes_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    AND idx_scan = 0
                """
                result = await session.execute(text(unused_indexes_query))
                unused_indexes = [dict(row._mapping) for row in result]
                
                optimization_results["unused_indexes"] = unused_indexes
                
                # Check table bloat
                bloat_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        n_dead_tup,
                        n_live_tup,
                        CASE 
                            WHEN n_live_tup > 0 THEN 
                                round((n_dead_tup::float / n_live_tup::float) * 100, 2)
                            ELSE 0
                        END as dead_tuple_percentage
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    AND n_dead_tup > 0
                    ORDER BY dead_tuple_percentage DESC
                """
                result = await session.execute(text(bloat_query))
                bloat_stats = [dict(row._mapping) for row in result]
                
                optimization_results["table_bloat"] = bloat_stats
                
                # Generate optimization recommendations
                recommendations = []
                
                for table in bloat_stats:
                    if table["dead_tuple_percentage"] > 20:
                        recommendations.append(
                            f"Consider VACUUM on table {table['tablename']} "
                            f"({table['dead_tuple_percentage']}% dead tuples)"
                        )
                
                if unused_indexes:
                    recommendations.append(
                        f"Consider dropping {len(unused_indexes)} unused indexes to save space"
                    )
                
                optimization_results["recommendations"] = recommendations
                
                await session.commit()
                
                return optimization_results
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to optimize database performance: {e}")
            raise RuntimeError(f"Failed to optimize database performance: {e}")
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get information about slow queries from pg_stat_statements if available.
        
        Args:
            limit: Maximum number of slow queries to return
            
        Returns:
            List of slow query information
        """
        try:
            async with get_async_db_session() as session:
                # Check if pg_stat_statements extension is available
                extension_check = """
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                    )
                """
                result = await session.execute(text(extension_check))
                has_pg_stat_statements = result.scalar()
                
                if not has_pg_stat_statements:
                    self.logger.warning("pg_stat_statements extension not available")
                    return []
                
                # Get slow queries
                slow_queries_query = f"""
                    SELECT 
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements
                    WHERE query NOT LIKE '%pg_stat_statements%'
                    ORDER BY mean_exec_time DESC
                    LIMIT {limit}
                """
                
                result = await session.execute(text(slow_queries_query))
                slow_queries = [dict(row._mapping) for row in result]
                
                return slow_queries
                
        except SQLAlchemyError as e:
            self.logger.warning(f"Failed to get slow queries: {e}")
            return []
    
    async def create_performance_indexes(self) -> Dict[str, bool]:
        """
        Create additional performance indexes based on common query patterns.
        
        Returns:
            Dictionary indicating which indexes were created successfully
        """
        try:
            async with get_async_db_session() as session:
                index_results = {}
                
                # Additional indexes for common query patterns
                indexes_to_create = [
                    {
                        "name": "idx_scraped_data_job_confidence",
                        "table": "scraped_data",
                        "columns": "(job_id, confidence_score DESC)",
                        "condition": None
                    },
                    {
                        "name": "idx_scraped_data_extracted_quality",
                        "table": "scraped_data", 
                        "columns": "(extracted_at DESC, data_quality_score DESC)",
                        "condition": None
                    },
                    {
                        "name": "idx_job_logs_job_created",
                        "table": "job_logs",
                        "columns": "(job_id, created_at DESC)",
                        "condition": None
                    },
                    {
                        "name": "idx_system_metrics_name_recorded",
                        "table": "system_metrics",
                        "columns": "(metric_name, recorded_at DESC)",
                        "condition": None
                    },
                    {
                        "name": "idx_scraped_data_ai_processed_partial",
                        "table": "scraped_data",
                        "columns": "(extracted_at DESC)",
                        "condition": "WHERE ai_processed = true"
                    }
                ]
                
                for index_info in indexes_to_create:
                    try:
                        # Check if index already exists
                        check_query = f"""
                            SELECT EXISTS(
                                SELECT 1 FROM pg_indexes 
                                WHERE indexname = '{index_info['name']}'
                            )
                        """
                        result = await session.execute(text(check_query))
                        index_exists = result.scalar()
                        
                        if not index_exists:
                            # Create the index
                            create_query = f"""
                                CREATE INDEX CONCURRENTLY {index_info['name']} 
                                ON {index_info['table']} {index_info['columns']}
                                {index_info['condition'] or ''}
                            """
                            await session.execute(text(create_query))
                            index_results[index_info['name']] = True
                            self.logger.info(f"Created index: {index_info['name']}")
                        else:
                            index_results[index_info['name']] = False
                            self.logger.debug(f"Index already exists: {index_info['name']}")
                            
                    except SQLAlchemyError as e:
                        index_results[index_info['name']] = False
                        self.logger.error(f"Failed to create index {index_info['name']}: {e}")
                
                await session.commit()
                return index_results
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create performance indexes: {e}")
            raise RuntimeError(f"Failed to create performance indexes: {e}")

    # ==================== Helper Methods ====================
    
    def _orm_to_pydantic_job(self, job_orm: ScrapingJobORM) -> ScrapingJob:
        """Convert SQLAlchemy ORM job to Pydantic model."""
        from src.models.pydantic_models import ScrapingConfig
        
        return ScrapingJob(
            id=job_orm.id,
            url=job_orm.url,
            config=ScrapingConfig(**job_orm.config),
            status=JobStatus(job_orm.status),
            created_at=job_orm.created_at,
            started_at=job_orm.started_at,
            completed_at=job_orm.completed_at,
            total_pages=job_orm.total_pages,
            pages_completed=job_orm.pages_completed,
            pages_failed=job_orm.pages_failed,
            error_message=job_orm.error_message,
            retry_count=job_orm.retry_count,
            user_id=job_orm.user_id,
            tags=job_orm.tags,
            priority=job_orm.priority
        )
    
    def _orm_to_pydantic_data(self, data_orm: ScrapedDataORM) -> ScrapedData:
        """Convert SQLAlchemy ORM data to Pydantic model."""
        from src.models.pydantic_models import ContentType
        
        return ScrapedData(
            id=data_orm.id,
            job_id=data_orm.job_id,
            url=data_orm.url,
            content=data_orm.content,
            raw_html=data_orm.raw_html,
            content_type=ContentType(data_orm.content_type),
            content_metadata=data_orm.content_metadata,
            confidence_score=data_orm.confidence_score,
            ai_processed=data_orm.ai_processed,
            ai_metadata=data_orm.ai_metadata,
            data_quality_score=data_orm.data_quality_score,
            validation_errors=data_orm.validation_errors,
            extracted_at=data_orm.extracted_at,
            processed_at=data_orm.processed_at,
            content_length=data_orm.content_length,
            load_time=data_orm.load_time
        )


# Global repository instance for dependency injection
data_repository = DataRepository()


async def get_data_repository() -> DataRepository:
    """
    Dependency injection function for FastAPI.
    
    Returns:
        DataRepository instance
    """
    return data_repository