#!/usr/bin/env python3
"""
Task Queue System Example

This example demonstrates how to use the Celery-based task queue system
for asynchronous web scraping operations.

Prerequisites:
- Redis server running on localhost:6379
- Celery worker running: celery -A src.pipeline.worker worker --loglevel=info
"""

import asyncio
import time
from datetime import datetime

from src.pipeline.job_queue import get_job_queue
from src.pipeline.monitor import get_job_monitor
from src.models.pydantic_models import ScrapingConfig, JobStatus


def demonstrate_job_submission():
    """Demonstrate submitting scraping jobs to the queue."""
    print("=== Job Submission Example ===")
    
    # Get job queue instance
    job_queue = get_job_queue()
    
    # Create scraping configuration
    config = ScrapingConfig(
        wait_time=5,
        max_retries=2,
        use_stealth=True,
        headless=True,
        extract_links=True,
        delay_between_requests=1.0
    )
    
    # Submit a single job
    print("Submitting single scraping job...")
    job = job_queue.submit_scraping_job(
        url="https://httpbin.org/html",
        config=config,
        priority=3
    )
    
    print(f"Job submitted: {job.id}")
    print(f"URL: {job.url}")
    print(f"Status: {job.status}")
    print(f"Priority: {job.priority}")
    print(f"Created at: {job.created_at}")
    
    return job.id


def demonstrate_job_monitoring(job_id: str):
    """Demonstrate job monitoring and progress tracking."""
    print("\n=== Job Monitoring Example ===")
    
    # Get monitor instance
    monitor = get_job_monitor()
    job_queue = get_job_queue()
    
    # Monitor job progress
    print(f"Monitoring job: {job_id}")
    
    for i in range(10):  # Monitor for up to 10 iterations
        # Get job status
        job = job_queue.get_job_status(job_id)
        if job:
            print(f"Status: {job.status.value}")
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                print(f"Job finished with status: {job.status.value}")
                if job.error_message:
                    print(f"Error: {job.error_message}")
                break
        
        # Get detailed progress
        progress = monitor.get_job_progress(job_id)
        if "error" not in progress:
            print(f"Progress: {progress['progress_percentage']:.1f}%")
            print(f"Pages completed: {progress['pages_completed']}")
            print(f"Pages failed: {progress['pages_failed']}")
        
        time.sleep(2)  # Wait 2 seconds before next check
    
    print("Monitoring complete.")


def demonstrate_system_metrics():
    """Demonstrate system metrics and health monitoring."""
    print("\n=== System Metrics Example ===")
    
    monitor = get_job_monitor()
    job_queue = get_job_queue()
    
    # Get queue statistics
    print("Queue Statistics:")
    queue_stats = job_queue.get_queue_stats()
    print(f"  Total jobs: {queue_stats['total_jobs']}")
    print(f"  Active tasks: {queue_stats['active_tasks']}")
    print(f"  Redis connected: {queue_stats['redis_connected']}")
    
    # Get system metrics
    print("\nSystem Metrics:")
    metrics = monitor.get_system_metrics()
    print(f"  Health status: {metrics['health_status']}")
    print(f"  Uptime: {metrics['uptime_seconds']:.1f} seconds")
    print(f"  Active workers: {metrics['worker_stats']['active_workers']}")
    
    # Get active jobs summary
    print("\nActive Jobs:")
    active_summary = monitor.get_active_jobs_summary()
    print(f"  Total active: {active_summary['total_active']}")
    print(f"  By status: {active_summary['by_status']}")
    print(f"  By priority: {active_summary['by_priority']}")


def demonstrate_batch_operations():
    """Demonstrate batch job operations."""
    print("\n=== Batch Operations Example ===")
    
    job_queue = get_job_queue()
    
    # Submit multiple jobs
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/xml"
    ]
    
    config = ScrapingConfig(
        wait_time=3,
        max_retries=1,
        use_stealth=False,
        headless=True
    )
    
    job_ids = []
    print(f"Submitting {len(urls)} jobs...")
    
    for i, url in enumerate(urls):
        job = job_queue.submit_scraping_job(
            url=url,
            config=config,
            priority=i + 1  # Different priorities
        )
        job_ids.append(job.id)
        print(f"  Job {i+1}: {job.id} -> {url}")
    
    # Get active jobs
    print("\nActive jobs after submission:")
    active_jobs = job_queue.get_active_jobs()
    for job in active_jobs[:5]:  # Show first 5
        print(f"  {job.id}: {job.url} (Priority: {job.priority}, Status: {job.status.value})")
    
    return job_ids


def demonstrate_error_handling():
    """Demonstrate error handling and recovery."""
    print("\n=== Error Handling Example ===")
    
    job_queue = get_job_queue()
    monitor = get_job_monitor()
    
    # Submit a job that will likely fail (invalid URL)
    config = ScrapingConfig(max_retries=1, timeout=5)
    
    print("Submitting job with invalid URL...")
    job = job_queue.submit_scraping_job(
        url="https://invalid-domain-that-does-not-exist.com",
        config=config,
        priority=1
    )
    
    print(f"Job ID: {job.id}")
    
    # Monitor for failure
    for i in range(15):  # Monitor for up to 30 seconds
        job_status = job_queue.get_job_status(job.id)
        if job_status:
            print(f"Status: {job_status.status.value}")
            
            if job_status.status == JobStatus.FAILED:
                print(f"Job failed as expected: {job_status.error_message}")
                break
            elif job_status.status == JobStatus.COMPLETED:
                print("Job unexpectedly completed")
                break
        
        time.sleep(2)
    
    # Record error for demonstration
    monitor.record_error(job.id, "DEMO_ERROR", "This is a demonstration error")
    print("Recorded demonstration error")


def demonstrate_job_cancellation():
    """Demonstrate job cancellation."""
    print("\n=== Job Cancellation Example ===")
    
    job_queue = get_job_queue()
    
    # Submit a job
    config = ScrapingConfig(wait_time=10)  # Long wait time
    job = job_queue.submit_scraping_job(
        url="https://httpbin.org/delay/10",  # Slow endpoint
        config=config,
        priority=5
    )
    
    print(f"Submitted job: {job.id}")
    
    # Wait a moment then cancel
    time.sleep(1)
    
    print("Cancelling job...")
    success = job_queue.cancel_job(job.id)
    
    if success:
        print("Job cancelled successfully")
        
        # Check status
        cancelled_job = job_queue.get_job_status(job.id)
        if cancelled_job:
            print(f"Job status: {cancelled_job.status.value}")
    else:
        print("Failed to cancel job")


def main():
    """Run all demonstration examples."""
    print("Task Queue System Demonstration")
    print("=" * 50)
    
    try:
        # Basic job submission and monitoring
        job_id = demonstrate_job_submission()
        demonstrate_job_monitoring(job_id)
        
        # System metrics
        demonstrate_system_metrics()
        
        # Batch operations
        batch_job_ids = demonstrate_batch_operations()
        
        # Error handling
        demonstrate_error_handling()
        
        # Job cancellation
        demonstrate_job_cancellation()
        
        print("\n" + "=" * 50)
        print("Demonstration complete!")
        print("\nTo see the jobs being processed, start a Celery worker:")
        print("celery -A src.pipeline.worker worker --loglevel=info")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        print("\nMake sure Redis is running on localhost:6379")
        print("You can start Redis with: redis-server")


if __name__ == "__main__":
    main()