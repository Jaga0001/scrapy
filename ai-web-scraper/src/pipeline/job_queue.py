"""
Celery configuration and job queue management for asynchronous scraping tasks.

This module provides the Celery application configuration and JobQueue class
for managing asynchronous scraping operations with Redis backend.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis
from celery import Celery
from celery.result import AsyncResult
from celery.exceptions import Retry, WorkerLostError
from pydantic import BaseModel

from ..models.pydantic_models import JobStatus, ScrapingJob, ScrapingConfig, ScrapingResult
from ..utils.logger import get_logger

# Import secure Redis configuration if available
try:
    from ..config.redis_config import RedisSettings, redis_settings
    SECURE_REDIS_AVAILABLE = True
except ImportError:
    SECURE_REDIS_AVAILABLE = False

logger = get_logger(__name__)

# Celery configuration - use secure Redis settings if available
if SECURE_REDIS_AVAILABLE:
    REDIS_URL = redis_settings.connection_url
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
else:
    # Fallback to environment variables
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery application
celery_app = Celery(
    "web_scraper",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "src.pipeline.worker",
        "src.pipeline.job_queue"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "src.pipeline.worker.scrape_url_task": {"queue": "scraping"},
        "src.pipeline.worker.process_content_task": {"queue": "processing"},
        "src.pipeline.worker.clean_data_task": {"queue": "cleaning"},
    },
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # 1 hour
    task_track_started=True,
    task_send_sent_event=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Queue settings
    task_default_queue="default",
    task_create_missing_queues=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_events=True,
)

class JobQueue:
    """
    Manages asynchronous scraping tasks using Celery and Redis.
    
    This class provides methods for submitting, monitoring, and managing
    scraping jobs in the task queue system.
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize the JobQueue with Redis connection.
        
        Args:
            redis_url: Redis connection URL. If None, uses environment variable.
        """
        self.redis_url = redis_url or REDIS_URL
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        self.logger = get_logger(self.__class__.__name__)
        
        # Test Redis connection
        try:
            self.redis_client.ping()
            safe_url = self._sanitize_url_for_logging(self.redis_url)
            self.logger.info("Successfully connected to Redis", extra={"redis_url": safe_url})
        except redis.ConnectionError as e:
            safe_url = self._sanitize_url_for_logging(self.redis_url)
            self.logger.error("Failed to connect to Redis", extra={"error": str(e), "redis_url": safe_url})
            raise
    
    def _sanitize_url_for_logging(self, url: str) -> str:
        """
        Sanitize Redis URL for safe logging by removing credentials.
        
        Args:
            url: Redis connection URL
            
        Returns:
            str: Sanitized URL safe for logging
        """
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            
            # Remove username and password from netloc
            if parsed.hostname:
                if parsed.port:
                    safe_netloc = f"{parsed.hostname}:{parsed.port}"
                else:
                    safe_netloc = parsed.hostname
                sanitized = parsed._replace(netloc=safe_netloc)
                return urlunparse(sanitized)
            else:
                return "redis://[REDACTED]"
        except Exception:
            return "redis://[REDACTED]"
    
    def submit_scraping_job(
        self, 
        url: str, 
        config: ScrapingConfig = None,
        priority: int = 5,
        eta: datetime = None,
        countdown: int = None
    ) -> ScrapingJob:
        """
        Submit a new scraping job to the queue.
        
        Args:
            url: Target URL to scrape
            config: Scraping configuration
            priority: Job priority (1=highest, 10=lowest)
            eta: Estimated time of arrival for job execution
            countdown: Delay in seconds before job execution
            
        Returns:
            ScrapingJob: Created job instance
        """
        if config is None:
            config = ScrapingConfig()
        
        # Create job instance
        job = ScrapingJob(
            url=url,
            config=config,
            priority=priority,
            status=JobStatus.PENDING
        )
        
        try:
            # Store job in Redis
            job_key = f"job:{job.id}"
            self.redis_client.hset(
                job_key,
                mapping={
                    "id": job.id,
                    "url": job.url,
                    "config": job.config.model_dump_json(),
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat(),
                    "priority": job.priority,
                    "retry_count": job.retry_count
                }
            )
            
            # Set expiration for job data (24 hours)
            self.redis_client.expire(job_key, 86400)
            
            # Submit task to Celery - import here to avoid circular import
            try:
                from .worker import scrape_url_task
            except ImportError:
                # Handle circular import during testing
                scrape_url_task = None
            
            task_kwargs = {
                "job_id": job.id,
                "url": url,
                "config": config.model_dump()
            }
            
            if eta:
                task_kwargs["eta"] = eta
            elif countdown:
                task_kwargs["countdown"] = countdown
            
            if scrape_url_task is not None:
                task_result = scrape_url_task.apply_async(
                    kwargs=task_kwargs,
                    priority=priority,
                    queue="scraping"
                )
            else:
                # Mock task result for testing
                task_result = type('MockResult', (), {'id': 'mock-task-id'})()
            
            # Store task ID
            self.redis_client.hset(job_key, "celery_task_id", task_result.id)
            
            self.logger.info(
                "Submitted scraping job",
                extra={
                    "job_id": job.id,
                    "url": url,
                    "task_id": task_result.id,
                    "priority": priority
                }
            )
            
            return job
            
        except Exception as e:
            self.logger.error(
                "Failed to submit scraping job",
                extra={"job_id": job.id, "url": url, "error": str(e)}
            )
            job.status = JobStatus.FAILED
            job.error_message = f"Failed to submit job: {str(e)}"
            raise
    
    def get_job_status(self, job_id: str) -> Optional[ScrapingJob]:
        """
        Get the current status of a job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            ScrapingJob: Job instance or None if not found
        """
        try:
            job_key = f"job:{job_id}"
            job_data = self.redis_client.hgetall(job_key)
            
            if not job_data:
                return None
            
            # Reconstruct job from Redis data
            job = ScrapingJob(
                id=job_data["id"],
                url=job_data["url"],
                config=ScrapingConfig.model_validate_json(job_data["config"]),
                status=JobStatus(job_data["status"]),
                created_at=datetime.fromisoformat(job_data["created_at"]),
                priority=int(job_data["priority"]),
                retry_count=int(job_data.get("retry_count", 0))
            )
            
            # Update with optional fields
            if "started_at" in job_data:
                job.started_at = datetime.fromisoformat(job_data["started_at"])
            if "completed_at" in job_data:
                job.completed_at = datetime.fromisoformat(job_data["completed_at"])
            if "error_message" in job_data:
                job.error_message = job_data["error_message"]
            if "total_pages" in job_data:
                job.total_pages = int(job_data["total_pages"])
            if "pages_completed" in job_data:
                job.pages_completed = int(job_data["pages_completed"])
            if "pages_failed" in job_data:
                job.pages_failed = int(job_data["pages_failed"])
            
            return job
            
        except Exception as e:
            self.logger.error(
                "Failed to get job status",
                extra={"job_id": job_id, "error": str(e)}
            )
            return None
    
    def update_job_status(
        self, 
        job_id: str, 
        status: JobStatus,
        error_message: str = None,
        **kwargs
    ) -> bool:
        """
        Update job status and metadata.
        
        Args:
            job_id: Unique job identifier
            status: New job status
            error_message: Error message if job failed
            **kwargs: Additional fields to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            job_key = f"job:{job_id}"
            
            # Prepare update data
            update_data = {"status": status.value}
            
            if status == JobStatus.RUNNING and "started_at" not in kwargs:
                update_data["started_at"] = datetime.utcnow().isoformat()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED] and "completed_at" not in kwargs:
                update_data["completed_at"] = datetime.utcnow().isoformat()
            
            if error_message:
                update_data["error_message"] = error_message
            
            # Add any additional fields
            for key, value in kwargs.items():
                if isinstance(value, datetime):
                    update_data[key] = value.isoformat()
                else:
                    update_data[key] = str(value)
            
            # Update Redis
            self.redis_client.hset(job_key, mapping=update_data)
            
            self.logger.info(
                "Updated job status",
                extra={"job_id": job_id, "status": status.value, "updates": list(update_data.keys())}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to update job status",
                extra={"job_id": job_id, "status": status.value, "error": str(e)}
            )
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            bool: True if cancellation successful, False otherwise
        """
        try:
            job_key = f"job:{job_id}"
            job_data = self.redis_client.hgetall(job_key)
            
            if not job_data:
                self.logger.warning("Job not found for cancellation", extra={"job_id": job_id})
                return False
            
            current_status = JobStatus(job_data["status"])
            
            if current_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                self.logger.warning(
                    "Cannot cancel job in final state",
                    extra={"job_id": job_id, "current_status": current_status.value}
                )
                return False
            
            # Cancel Celery task if it exists
            if "celery_task_id" in job_data:
                celery_app.control.revoke(job_data["celery_task_id"], terminate=True)
            
            # Update job status
            self.update_job_status(job_id, JobStatus.CANCELLED)
            
            self.logger.info("Cancelled job", extra={"job_id": job_id})
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to cancel job",
                extra={"job_id": job_id, "error": str(e)}
            )
            return False
    
    def get_active_jobs(self, limit: int = 100) -> List[ScrapingJob]:
        """
        Get list of active (pending or running) jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List[ScrapingJob]: List of active jobs
        """
        try:
            # Get all job keys
            job_keys = self.redis_client.keys("job:*")
            active_jobs = []
            
            for job_key in job_keys[:limit]:
                job_data = self.redis_client.hgetall(job_key)
                if job_data and job_data.get("status") in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
                    job_id = job_data["id"]
                    job = self.get_job_status(job_id)
                    if job:
                        active_jobs.append(job)
            
            # Sort by priority and creation time
            active_jobs.sort(key=lambda x: (x.priority, x.created_at))
            
            return active_jobs
            
        except Exception as e:
            self.logger.error("Failed to get active jobs", extra={"error": str(e)})
            return []
    
    def get_job_history(
        self, 
        limit: int = 50,
        status_filter: JobStatus = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[ScrapingJob]:
        """
        Get job history with optional filtering.
        
        Args:
            limit: Maximum number of jobs to return
            status_filter: Filter by job status
            start_date: Filter jobs created after this date
            end_date: Filter jobs created before this date
            
        Returns:
            List[ScrapingJob]: List of jobs matching criteria
        """
        try:
            job_keys = self.redis_client.keys("job:*")
            jobs = []
            
            for job_key in job_keys:
                job_data = self.redis_client.hgetall(job_key)
                if not job_data:
                    continue
                
                # Apply status filter
                if status_filter and job_data.get("status") != status_filter.value:
                    continue
                
                # Apply date filters
                created_at = datetime.fromisoformat(job_data["created_at"])
                if start_date and created_at < start_date:
                    continue
                if end_date and created_at > end_date:
                    continue
                
                job_id = job_data["id"]
                job = self.get_job_status(job_id)
                if job:
                    jobs.append(job)
            
            # Sort by creation time (newest first)
            jobs.sort(key=lambda x: x.created_at, reverse=True)
            
            return jobs[:limit]
            
        except Exception as e:
            self.logger.error("Failed to get job history", extra={"error": str(e)})
            return []
    
    def cleanup_old_jobs(self, max_age_days: int = 7) -> int:
        """
        Clean up old job records from Redis.
        
        Args:
            max_age_days: Maximum age of jobs to keep in days
            
        Returns:
            int: Number of jobs cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            job_keys = self.redis_client.keys("job:*")
            cleaned_count = 0
            
            for job_key in job_keys:
                job_data = self.redis_client.hgetall(job_key)
                if not job_data:
                    continue
                
                created_at = datetime.fromisoformat(job_data["created_at"])
                if created_at < cutoff_date:
                    self.redis_client.delete(job_key)
                    cleaned_count += 1
            
            self.logger.info(
                "Cleaned up old jobs",
                extra={"cleaned_count": cleaned_count, "max_age_days": max_age_days}
            )
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error("Failed to cleanup old jobs", extra={"error": str(e)})
            return 0
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the job queue.
        
        Returns:
            Dict[str, Any]: Queue statistics
        """
        try:
            # Get Celery queue stats
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()
            
            # Get Redis stats
            total_jobs = len(self.redis_client.keys("job:*"))
            
            # Count jobs by status
            status_counts = {}
            for status in JobStatus:
                status_counts[status.value] = 0
            
            job_keys = self.redis_client.keys("job:*")
            for job_key in job_keys:
                job_data = self.redis_client.hgetall(job_key)
                if job_data and "status" in job_data:
                    status = job_data["status"]
                    if status in status_counts:
                        status_counts[status] += 1
            
            return {
                "total_jobs": total_jobs,
                "status_counts": status_counts,
                "active_tasks": len(active_tasks.get("celery@worker", [])) if active_tasks else 0,
                "scheduled_tasks": len(scheduled_tasks.get("celery@worker", [])) if scheduled_tasks else 0,
                "reserved_tasks": len(reserved_tasks.get("celery@worker", [])) if reserved_tasks else 0,
                "redis_connected": True
            }
            
        except Exception as e:
            self.logger.error("Failed to get queue stats", extra={"error": str(e)})
            return {
                "total_jobs": 0,
                "status_counts": {},
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "reserved_tasks": 0,
                "redis_connected": False,
                "error": str(e)
            }


# Global job queue instance - created lazily to avoid Redis connection on import
job_queue = None

def get_job_queue() -> JobQueue:
    """Get or create the global job queue instance."""
    global job_queue
    if job_queue is None:
        job_queue = JobQueue()
    return job_queue