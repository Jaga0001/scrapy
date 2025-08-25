"""
Celery worker tasks for background processing of scraping jobs.

This module contains the Celery tasks that handle the actual scraping,
content processing, and data cleaning operations in the background.
"""

import asyncio
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery import Task
from celery.exceptions import Retry, WorkerLostError
from celery.signals import task_prerun, task_postrun, task_failure

from .job_queue import celery_app, get_job_queue
from ..models.pydantic_models import JobStatus, ScrapingConfig, ScrapedData, ScrapingResult
from ..scraper.web_scraper import WebScraper
from ..ai.content_processor import ContentProcessor
from ..pipeline.cleaner import DataCleaner
from ..pipeline.repository import DataRepository
from ..utils.logger import get_logger
from ..utils.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)

# Initialize components
web_scraper = WebScraper()
content_processor = ContentProcessor()
data_cleaner = DataCleaner()
data_repository = DataRepository()

# Circuit breakers for external services
from ..utils.circuit_breaker import CircuitBreakerConfig

scraper_circuit_breaker = CircuitBreaker(
    name="web_scraper",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=300.0,  # 5 minutes
        timeout=60.0
    )
)

ai_circuit_breaker = CircuitBreaker(
    name="ai_processor", 
    config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=600.0,  # 10 minutes
        timeout=120.0
    )
)


class CallbackTask(Task):
    """Base task class with enhanced error handling and logging."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        job_id = kwargs.get('job_id')
        if job_id:
            get_job_queue().update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(exc)
            )
        
        logger.error(
            "Task failed",
            extra={
                "task_id": task_id,
                "job_id": job_id,
                "error": str(exc),
                "traceback": einfo.traceback
            }
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        job_id = kwargs.get('job_id')
        if job_id:
            # Increment retry count
            job = get_job_queue().get_job_status(job_id)
            if job:
                get_job_queue().update_job_status(
                    job_id,
                    JobStatus.PENDING,
                    retry_count=job.retry_count + 1
                )
        
        logger.warning(
            "Task retrying",
            extra={
                "task_id": task_id,
                "job_id": job_id,
                "error": str(exc),
                "retry_count": self.request.retries
            }
        )


@celery_app.task(bind=True, base=CallbackTask, name="src.pipeline.worker.scrape_url_task")
def scrape_url_task(self, job_id: str, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scrape a single URL and process the content.
    
    Args:
        job_id: Unique job identifier
        url: Target URL to scrape
        config: Scraping configuration dictionary
        
    Returns:
        Dict[str, Any]: Scraping result
    """
    logger.info(
        "Starting scraping task",
        extra={"task_id": self.request.id, "job_id": job_id, "url": url}
    )
    
    try:
        # Update job status to running
        get_job_queue().update_job_status(job_id, JobStatus.RUNNING)
        
        # Parse configuration
        scraping_config = ScrapingConfig(**config)
        
        # Perform scraping with circuit breaker
        try:
            scraping_result = asyncio.run(scraper_circuit_breaker.call(
                web_scraper.scrape_url, url, scraping_config
            ))
        except Exception as e:
            if scraper_circuit_breaker.state.value == "open":
                logger.error(
                    "Scraper circuit breaker is open",
                    extra={"job_id": job_id, "url": url}
                )
                raise Exception("Scraping service temporarily unavailable")
            raise e
        
        if not scraping_result.success:
            raise Exception(f"Scraping failed: {scraping_result.error_message}")
        
        # Process scraped data
        processed_data = []
        for raw_data in scraping_result.data:
            try:
                # Process with AI if enabled
                if scraping_config.javascript_enabled:  # Use as proxy for AI processing
                    processed_content = process_content_with_ai(raw_data.content, raw_data.url)
                    raw_data.ai_processed = True
                    raw_data.ai_metadata = processed_content.get("metadata", {})
                    raw_data.confidence_score = processed_content.get("confidence_score", 0.0)
                
                # Clean and validate data
                cleaned_data = data_cleaner.clean_scraped_data(raw_data)
                processed_data.append(cleaned_data)
                
            except Exception as e:
                logger.warning(
                    "Failed to process scraped data",
                    extra={"job_id": job_id, "url": raw_data.url, "error": str(e)}
                )
                # Keep original data if processing fails
                processed_data.append(raw_data)
        
        # Save to database
        saved_count = 0
        for data in processed_data:
            try:
                data_repository.save_scraped_data(data)
                saved_count += 1
            except Exception as e:
                logger.error(
                    "Failed to save scraped data",
                    extra={"job_id": job_id, "data_id": data.id, "error": str(e)}
                )
        
        # Update job status
        get_job_queue().update_job_status(
            job_id,
            JobStatus.COMPLETED,
            total_pages=1,
            pages_completed=1 if scraping_result.success else 0,
            pages_failed=0 if scraping_result.success else 1
        )
        
        result = {
            "success": True,
            "job_id": job_id,
            "url": url,
            "data_count": len(processed_data),
            "saved_count": saved_count,
            "processing_time": scraping_result.total_time
        }
        
        logger.info(
            "Completed scraping task",
            extra={
                "task_id": self.request.id,
                "job_id": job_id,
                "url": url,
                "data_count": len(processed_data),
                "processing_time": scraping_result.total_time
            }
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Scraping task failed: {str(e)}"
        logger.error(
            "Scraping task failed",
            extra={
                "task_id": self.request.id,
                "job_id": job_id,
                "url": url,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
        
        # Update job status to failed
        get_job_queue().update_job_status(job_id, JobStatus.FAILED, error_message=error_msg)
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying scraping task",
                extra={
                    "task_id": self.request.id,
                    "job_id": job_id,
                    "retry_count": self.request.retries + 1
                }
            )
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)
        
        return {
            "success": False,
            "job_id": job_id,
            "url": url,
            "error": error_msg
        }


@celery_app.task(bind=True, base=CallbackTask, name="src.pipeline.worker.process_content_task")
def process_content_task(self, content: str, url: str, content_type: str = "html") -> Dict[str, Any]:
    """
    Process content using AI for intelligent extraction.
    
    Args:
        content: Raw content to process
        url: Source URL
        content_type: Type of content (html, text, etc.)
        
    Returns:
        Dict[str, Any]: Processing result
    """
    logger.info(
        "Starting content processing task",
        extra={"task_id": self.request.id, "url": url, "content_type": content_type}
    )
    
    try:
        # Process with AI using circuit breaker
        try:
            result = asyncio.run(ai_circuit_breaker.call(
                content_processor.process_content, content, content_type
            ))
        except Exception as e:
            if ai_circuit_breaker.state.value == "open":
                logger.error(
                    "AI circuit breaker is open",
                    extra={"url": url, "content_type": content_type}
                )
                # Return basic processing result
                return {
                    "success": True,
                    "processed_content": {"raw_content": content},
                    "confidence_score": 0.5,
                    "metadata": {"ai_processed": False, "fallback_used": True}
                }
            raise e
        
        logger.info(
            "Completed content processing task",
            extra={
                "task_id": self.request.id,
                "url": url,
                "confidence_score": result.confidence_score
            }
        )
        
        return {
            "success": True,
            "processed_content": result.processed_content,
            "confidence_score": result.confidence_score,
            "metadata": result.metadata
        }
        
    except Exception as e:
        logger.error(
            "Content processing task failed",
            extra={
                "task_id": self.request.id,
                "url": url,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
        
        # Return fallback result
        return {
            "success": False,
            "processed_content": {"raw_content": content},
            "confidence_score": 0.0,
            "metadata": {"error": str(e)},
            "error": str(e)
        }


@celery_app.task(bind=True, base=CallbackTask, name="src.pipeline.worker.clean_data_task")
def clean_data_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean and validate scraped data.
    
    Args:
        data: Raw scraped data dictionary
        
    Returns:
        Dict[str, Any]: Cleaned data
    """
    logger.info(
        "Starting data cleaning task",
        extra={"task_id": self.request.id, "data_id": data.get("id")}
    )
    
    try:
        # Convert dict to ScrapedData model
        scraped_data = ScrapedData(**data)
        
        # Clean the data
        cleaned_data = data_cleaner.clean_scraped_data(scraped_data)
        
        logger.info(
            "Completed data cleaning task",
            extra={
                "task_id": self.request.id,
                "data_id": cleaned_data.id,
                "quality_score": cleaned_data.data_quality_score
            }
        )
        
        return {
            "success": True,
            "cleaned_data": cleaned_data.model_dump(),
            "quality_score": cleaned_data.data_quality_score
        }
        
    except Exception as e:
        logger.error(
            "Data cleaning task failed",
            extra={
                "task_id": self.request.id,
                "data_id": data.get("id"),
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
        
        return {
            "success": False,
            "error": str(e),
            "original_data": data
        }


@celery_app.task(bind=True, name="src.pipeline.worker.batch_scrape_task")
def batch_scrape_task(self, job_id: str, urls: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process multiple URLs in a batch.
    
    Args:
        job_id: Unique job identifier
        urls: List of URLs to scrape
        config: Scraping configuration dictionary
        
    Returns:
        Dict[str, Any]: Batch processing result
    """
    logger.info(
        "Starting batch scraping task",
        extra={"task_id": self.request.id, "job_id": job_id, "url_count": len(urls)}
    )
    
    try:
        # Update job status
        get_job_queue().update_job_status(
            job_id,
            JobStatus.RUNNING,
            total_pages=len(urls)
        )
        
        results = []
        completed_count = 0
        failed_count = 0
        
        for i, url in enumerate(urls):
            try:
                # Submit individual scraping task
                result = scrape_url_task.apply(kwargs={
                    "job_id": f"{job_id}_{i}",
                    "url": url,
                    "config": config
                })
                
                if result.get("success"):
                    completed_count += 1
                else:
                    failed_count += 1
                
                results.append(result)
                
                # Update progress
                get_job_queue().update_job_status(
                    job_id,
                    JobStatus.RUNNING,
                    pages_completed=completed_count,
                    pages_failed=failed_count
                )
                
            except Exception as e:
                failed_count += 1
                logger.error(
                    "Failed to process URL in batch",
                    extra={"job_id": job_id, "url": url, "error": str(e)}
                )
                results.append({
                    "success": False,
                    "url": url,
                    "error": str(e)
                })
        
        # Update final job status
        final_status = JobStatus.COMPLETED if failed_count == 0 else JobStatus.FAILED
        get_job_queue().update_job_status(
            job_id,
            final_status,
            pages_completed=completed_count,
            pages_failed=failed_count
        )
        
        logger.info(
            "Completed batch scraping task",
            extra={
                "task_id": self.request.id,
                "job_id": job_id,
                "completed_count": completed_count,
                "failed_count": failed_count
            }
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "total_urls": len(urls),
            "completed_count": completed_count,
            "failed_count": failed_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(
            "Batch scraping task failed",
            extra={
                "task_id": self.request.id,
                "job_id": job_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
        
        get_job_queue().update_job_status(job_id, JobStatus.FAILED, error_message=str(e))
        
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e)
        }


def process_content_with_ai(content: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Helper function to process content with AI.
    
    Args:
        content: Content dictionary to process
        url: Source URL
        
    Returns:
        Dict[str, Any]: AI processing result
    """
    try:
        # Submit AI processing task
        result = process_content_task.apply(kwargs={
            "content": str(content),
            "url": url,
            "content_type": "html"
        })
        
        return result if result.get("success") else {
            "confidence_score": 0.0,
            "metadata": {"ai_processing_failed": True}
        }
        
    except Exception as e:
        logger.warning(
            "AI processing failed",
            extra={"url": url, "error": str(e)}
        )
        return {
            "confidence_score": 0.0,
            "metadata": {"ai_processing_failed": True, "error": str(e)}
        }


# Task signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run setup."""
    logger.info(
        "Task starting",
        extra={
            "task_id": task_id,
            "task_name": sender,
            "job_id": kwargs.get("job_id") if kwargs else None
        }
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task post-run cleanup."""
    logger.info(
        "Task completed",
        extra={
            "task_id": task_id,
            "task_name": sender,
            "state": state,
            "job_id": kwargs.get("job_id") if kwargs else None
        }
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure."""
    logger.error(
        "Task failed",
        extra={
            "task_id": task_id,
            "task_name": sender,
            "exception": str(exception),
            "traceback": str(traceback)
        }
    )