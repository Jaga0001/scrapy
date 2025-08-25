"""
Job monitoring and progress tracking for the scraping system.

This module provides the JobMonitor class for tracking job status,
performance metrics, and system health monitoring.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, deque

import redis
from celery import Celery
from celery.events.state import State
from celery.events import EventReceiver

from .job_queue import celery_app, get_job_queue
from ..models.pydantic_models import JobStatus, ScrapingJob
from ..utils.logger import get_logger

logger = get_logger(__name__)


class JobMonitor:
    """
    Monitors job status, performance metrics, and system health.
    
    This class provides real-time monitoring capabilities for the scraping
    system, including job progress tracking, performance metrics collection,
    and system health monitoring.
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize the JobMonitor.
        
        Args:
            redis_url: Redis connection URL. If None, uses environment variable.
        """
        self.redis_url = redis_url or get_job_queue().redis_url
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        self.logger = get_logger(self.__class__.__name__)
        
        # Performance tracking
        self.performance_history = deque(maxlen=1000)  # Keep last 1000 metrics
        self.error_history = deque(maxlen=500)  # Keep last 500 errors
        
        # System metrics
        self.system_metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "uptime_start": datetime.utcnow()
        }
        
        # Real-time event state
        self.celery_state = State()
        
        # Sanitize Redis URL for logging
        safe_url = self._sanitize_url_for_logging(self.redis_url)
        self.logger.info("JobMonitor initialized", extra={"redis_url": safe_url})
    
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
    
    def get_job_progress(self, job_id: str) -> Dict[str, Any]:
        """
        Get detailed progress information for a specific job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Dict[str, Any]: Job progress information
        """
        try:
            job = get_job_queue().get_job_status(job_id)
            if not job:
                return {"error": "Job not found"}
            
            # Calculate progress percentage
            progress_percentage = 0.0
            if job.total_pages > 0:
                progress_percentage = (job.pages_completed / job.total_pages) * 100
            
            # Calculate estimated time remaining
            eta = None
            if job.status == JobStatus.RUNNING and job.started_at and job.total_pages > 0:
                elapsed_time = (datetime.utcnow() - job.started_at).total_seconds()
                if job.pages_completed > 0:
                    avg_time_per_page = elapsed_time / job.pages_completed
                    remaining_pages = job.total_pages - job.pages_completed
                    eta_seconds = remaining_pages * avg_time_per_page
                    eta = datetime.utcnow() + timedelta(seconds=eta_seconds)
            
            # Get Celery task info if available
            celery_task_info = None
            job_key = f"job:{job_id}"
            job_data = self.redis_client.hgetall(job_key)
            if job_data and "celery_task_id" in job_data:
                task_id = job_data["celery_task_id"]
                celery_task_info = self._get_celery_task_info(task_id)
            
            return {
                "job_id": job_id,
                "status": job.status.value,
                "progress_percentage": round(progress_percentage, 2),
                "pages_completed": job.pages_completed,
                "pages_failed": job.pages_failed,
                "total_pages": job.total_pages,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "estimated_completion": eta.isoformat() if eta else None,
                "error_message": job.error_message,
                "retry_count": job.retry_count,
                "celery_task_info": celery_task_info
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get job progress",
                extra={"job_id": job_id, "error": str(e)}
            )
            return {"error": str(e)}
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive system performance metrics.
        
        Returns:
            Dict[str, Any]: System metrics
        """
        try:
            # Get queue statistics
            queue_stats = get_job_queue().get_queue_stats()
            
            # Get Celery worker statistics
            inspect = celery_app.control.inspect()
            worker_stats = {
                "active_workers": 0,
                "total_active_tasks": 0,
                "total_scheduled_tasks": 0,
                "total_reserved_tasks": 0
            }
            
            try:
                stats = inspect.stats()
                active = inspect.active()
                scheduled = inspect.scheduled()
                reserved = inspect.reserved()
                
                if stats:
                    worker_stats["active_workers"] = len(stats)
                
                if active:
                    worker_stats["total_active_tasks"] = sum(len(tasks) for tasks in active.values())
                
                if scheduled:
                    worker_stats["total_scheduled_tasks"] = sum(len(tasks) for tasks in scheduled.values())
                
                if reserved:
                    worker_stats["total_reserved_tasks"] = sum(len(tasks) for tasks in reserved.values())
                    
            except Exception as e:
                self.logger.warning("Failed to get Celery worker stats", extra={"error": str(e)})
            
            # Calculate performance metrics
            current_time = datetime.utcnow()
            uptime = (current_time - self.system_metrics["uptime_start"]).total_seconds()
            
            # Get recent performance data
            recent_metrics = self._get_recent_performance_metrics()
            
            # Get error rate
            error_rate = self._calculate_error_rate()
            
            return {
                "timestamp": current_time.isoformat(),
                "uptime_seconds": uptime,
                "queue_stats": queue_stats,
                "worker_stats": worker_stats,
                "performance_metrics": {
                    "jobs_processed_total": self.system_metrics["jobs_processed"],
                    "jobs_failed_total": self.system_metrics["jobs_failed"],
                    "average_processing_time": self.system_metrics["average_processing_time"],
                    "recent_throughput": recent_metrics["throughput"],
                    "recent_avg_time": recent_metrics["avg_processing_time"],
                    "error_rate_percentage": error_rate
                },
                "health_status": self._get_health_status(),
                "redis_info": self._get_redis_info()
            }
            
        except Exception as e:
            self.logger.error("Failed to get system metrics", extra={"error": str(e)})
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_active_jobs_summary(self) -> Dict[str, Any]:
        """
        Get summary of all active jobs.
        
        Returns:
            Dict[str, Any]: Active jobs summary
        """
        try:
            active_jobs = get_job_queue().get_active_jobs()
            
            summary = {
                "total_active": len(active_jobs),
                "by_status": defaultdict(int),
                "by_priority": defaultdict(int),
                "jobs": []
            }
            
            for job in active_jobs:
                summary["by_status"][job.status.value] += 1
                summary["by_priority"][job.priority] += 1
                
                # Calculate progress
                progress = 0.0
                if job.total_pages > 0:
                    progress = (job.pages_completed / job.total_pages) * 100
                
                summary["jobs"].append({
                    "job_id": job.id,
                    "url": job.url,
                    "status": job.status.value,
                    "priority": job.priority,
                    "progress_percentage": round(progress, 2),
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None
                })
            
            # Convert defaultdicts to regular dicts
            summary["by_status"] = dict(summary["by_status"])
            summary["by_priority"] = dict(summary["by_priority"])
            
            return summary
            
        except Exception as e:
            self.logger.error("Failed to get active jobs summary", extra={"error": str(e)})
            return {"error": str(e)}
    
    def get_performance_history(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance metrics history.
        
        Args:
            hours: Number of hours of history to retrieve
            
        Returns:
            Dict[str, Any]: Performance history data
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Filter performance history by time
            recent_history = [
                metric for metric in self.performance_history
                if metric["timestamp"] >= cutoff_time
            ]
            
            # Group by hour for aggregation
            hourly_data = defaultdict(list)
            for metric in recent_history:
                hour_key = metric["timestamp"].replace(minute=0, second=0, microsecond=0)
                hourly_data[hour_key].append(metric)
            
            # Aggregate hourly data
            aggregated_data = []
            for hour, metrics in sorted(hourly_data.items()):
                if metrics:
                    avg_processing_time = sum(m["processing_time"] for m in metrics) / len(metrics)
                    total_jobs = len(metrics)
                    failed_jobs = sum(1 for m in metrics if not m["success"])
                    
                    aggregated_data.append({
                        "timestamp": hour.isoformat(),
                        "jobs_processed": total_jobs,
                        "jobs_failed": failed_jobs,
                        "success_rate": ((total_jobs - failed_jobs) / total_jobs) * 100 if total_jobs > 0 else 0,
                        "average_processing_time": avg_processing_time
                    })
            
            return {
                "hours_requested": hours,
                "data_points": len(aggregated_data),
                "history": aggregated_data
            }
            
        except Exception as e:
            self.logger.error("Failed to get performance history", extra={"error": str(e)})
            return {"error": str(e)}
    
    def record_job_completion(self, job_id: str, success: bool, processing_time: float):
        """
        Record job completion for performance tracking.
        
        Args:
            job_id: Unique job identifier
            success: Whether the job completed successfully
            processing_time: Time taken to process the job in seconds
        """
        try:
            # Update system metrics
            self.system_metrics["jobs_processed"] += 1
            if not success:
                self.system_metrics["jobs_failed"] += 1
            
            self.system_metrics["total_processing_time"] += processing_time
            self.system_metrics["average_processing_time"] = (
                self.system_metrics["total_processing_time"] / self.system_metrics["jobs_processed"]
            )
            
            # Add to performance history
            metric = {
                "timestamp": datetime.utcnow(),
                "job_id": job_id,
                "success": success,
                "processing_time": processing_time
            }
            self.performance_history.append(metric)
            
            # Store in Redis for persistence
            metric_key = f"metric:{job_id}:{int(time.time())}"
            self.redis_client.hset(
                metric_key,
                mapping={
                    "job_id": job_id,
                    "success": str(success),
                    "processing_time": str(processing_time),
                    "timestamp": metric["timestamp"].isoformat()
                }
            )
            self.redis_client.expire(metric_key, 86400 * 7)  # Keep for 7 days
            
            self.logger.debug(
                "Recorded job completion",
                extra={
                    "job_id": job_id,
                    "success": success,
                    "processing_time": processing_time
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to record job completion",
                extra={"job_id": job_id, "error": str(e)}
            )
    
    def record_error(self, job_id: str, error_type: str, error_message: str):
        """
        Record error for tracking and analysis.
        
        Args:
            job_id: Unique job identifier
            error_type: Type/category of error
            error_message: Detailed error message
        """
        try:
            error_record = {
                "timestamp": datetime.utcnow(),
                "job_id": job_id,
                "error_type": error_type,
                "error_message": error_message
            }
            
            self.error_history.append(error_record)
            
            # Store in Redis
            error_key = f"error:{job_id}:{int(time.time())}"
            self.redis_client.hset(
                error_key,
                mapping={
                    "job_id": job_id,
                    "error_type": error_type,
                    "error_message": error_message,
                    "timestamp": error_record["timestamp"].isoformat()
                }
            )
            self.redis_client.expire(error_key, 86400 * 7)  # Keep for 7 days
            
            self.logger.info(
                "Recorded error",
                extra={
                    "job_id": job_id,
                    "error_type": error_type,
                    "error_message": error_message
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to record error",
                extra={"job_id": job_id, "error": str(e)}
            )
    
    def start_real_time_monitoring(self):
        """
        Start real-time monitoring of Celery events.
        
        This method starts a background process that listens to Celery events
        and updates job status in real-time.
        """
        def monitor_events():
            try:
                with celery_app.connection() as connection:
                    recv = EventReceiver(connection, handlers={
                        'task-sent': self._on_task_sent,
                        'task-received': self._on_task_received,
                        'task-started': self._on_task_started,
                        'task-succeeded': self._on_task_succeeded,
                        'task-failed': self._on_task_failed,
                        'task-retried': self._on_task_retried,
                        'task-revoked': self._on_task_revoked,
                    })
                    recv.capture(limit=None, timeout=None, wakeup=True)
                    
            except Exception as e:
                self.logger.error("Real-time monitoring failed", extra={"error": str(e)})
        
        # Start monitoring in background thread
        import threading
        monitor_thread = threading.Thread(target=monitor_events, daemon=True)
        monitor_thread.start()
        
        self.logger.info("Started real-time monitoring")
    
    def _get_celery_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a Celery task."""
        try:
            inspect = celery_app.control.inspect()
            
            # Check active tasks
            active = inspect.active()
            if active:
                for worker, tasks in active.items():
                    for task in tasks:
                        if task.get("id") == task_id:
                            return {
                                "worker": worker,
                                "state": "ACTIVE",
                                "task_info": task
                            }
            
            # Check scheduled tasks
            scheduled = inspect.scheduled()
            if scheduled:
                for worker, tasks in scheduled.items():
                    for task in tasks:
                        if task.get("id") == task_id:
                            return {
                                "worker": worker,
                                "state": "SCHEDULED",
                                "task_info": task
                            }
            
            # Check reserved tasks
            reserved = inspect.reserved()
            if reserved:
                for worker, tasks in reserved.items():
                    for task in tasks:
                        if task.get("id") == task_id:
                            return {
                                "worker": worker,
                                "state": "RESERVED",
                                "task_info": task
                            }
            
            return None
            
        except Exception as e:
            self.logger.warning("Failed to get Celery task info", extra={"task_id": task_id, "error": str(e)})
            return None
    
    def _get_recent_performance_metrics(self, minutes: int = 60) -> Dict[str, float]:
        """Get performance metrics for recent time period."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_metrics = [
            metric for metric in self.performance_history
            if metric["timestamp"] >= cutoff_time
        ]
        
        if not recent_metrics:
            return {"throughput": 0.0, "avg_processing_time": 0.0}
        
        throughput = len(recent_metrics) / (minutes / 60.0)  # jobs per hour
        avg_time = sum(m["processing_time"] for m in recent_metrics) / len(recent_metrics)
        
        return {
            "throughput": throughput,
            "avg_processing_time": avg_time
        }
    
    def _calculate_error_rate(self, hours: int = 24) -> float:
        """Calculate error rate for specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_metrics = [
            metric for metric in self.performance_history
            if metric["timestamp"] >= cutoff_time
        ]
        
        if not recent_metrics:
            return 0.0
        
        failed_count = sum(1 for m in recent_metrics if not m["success"])
        return (failed_count / len(recent_metrics)) * 100
    
    def _get_health_status(self) -> str:
        """Determine overall system health status."""
        try:
            # Check Redis connection
            self.redis_client.ping()
            
            # Check error rate
            error_rate = self._calculate_error_rate(hours=1)
            
            # Check active workers
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            active_workers = len(stats) if stats else 0
            
            if active_workers == 0:
                return "DEGRADED"
            elif error_rate > 50:
                return "UNHEALTHY"
            elif error_rate > 20:
                return "DEGRADED"
            else:
                return "HEALTHY"
                
        except Exception:
            return "UNHEALTHY"
    
    def _get_redis_info(self) -> Dict[str, Any]:
        """Get Redis connection and memory information."""
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    # Celery event handlers
    def _on_task_sent(self, event):
        """Handle task sent event."""
        self.logger.debug("Task sent", extra={"task_id": event["uuid"], "task": event["name"]})
    
    def _on_task_received(self, event):
        """Handle task received event."""
        self.logger.debug("Task received", extra={"task_id": event["uuid"], "task": event["name"]})
    
    def _on_task_started(self, event):
        """Handle task started event."""
        self.logger.debug("Task started", extra={"task_id": event["uuid"], "task": event["name"]})
    
    def _on_task_succeeded(self, event):
        """Handle task succeeded event."""
        processing_time = event.get("runtime", 0.0)
        self.record_job_completion(event["uuid"], True, processing_time)
        self.logger.debug("Task succeeded", extra={"task_id": event["uuid"], "runtime": processing_time})
    
    def _on_task_failed(self, event):
        """Handle task failed event."""
        processing_time = event.get("runtime", 0.0)
        self.record_job_completion(event["uuid"], False, processing_time)
        self.record_error(event["uuid"], "TASK_FAILED", event.get("exception", "Unknown error"))
        self.logger.debug("Task failed", extra={"task_id": event["uuid"], "exception": event.get("exception")})
    
    def _on_task_retried(self, event):
        """Handle task retried event."""
        self.logger.debug("Task retried", extra={"task_id": event["uuid"], "reason": event.get("reason")})
    
    def _on_task_revoked(self, event):
        """Handle task revoked event."""
        self.logger.debug("Task revoked", extra={"task_id": event["uuid"]})


# Global monitor instance - created lazily to avoid Redis connection on import
job_monitor = None

def get_job_monitor() -> JobMonitor:
    """Get or create the global job monitor instance."""
    global job_monitor
    if job_monitor is None:
        job_monitor = JobMonitor()
    return job_monitor