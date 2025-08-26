"""
Scraping jobs API routes.

This module contains endpoints for creating, managing, and monitoring scraping jobs.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from src.api.schemas import (
    CreateJobRequest, UpdateJobRequest, BulkJobRequest,
    JobResponse, JobListResponse, JobStatsResponse,
    BatchOperationRequest, BatchOperationResponse
)
from src.models.pydantic_models import ScrapingJob, JobStatus, ScrapingConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
security = HTTPBearer()


# Dependency for authentication (placeholder)
async def get_current_user(token: str = Depends(security)):
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        dict: User information
        
    Raises:
        HTTPException: If token is invalid
    """
    # This would validate the JWT token and return user info
    # For now, return a placeholder user
    return {"user_id": "user123", "username": "testuser"}


# Placeholder for job service dependency
class JobService:
    """Placeholder job service for demonstration."""
    
    async def create_job(self, job_data: CreateJobRequest, user_id: str) -> ScrapingJob:
        """Create a new scraping job."""
        config = job_data.config or ScrapingConfig()
        
        job = ScrapingJob(
            id=str(uuid4()),
            url=job_data.url,
            config=config,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            tags=job_data.tags or [],
            priority=job_data.priority or 5,
            user_id=user_id
        )
        
        # Here you would save to database and queue the job
        logger.info(f"Created job {job.id} for URL: {job.url}")
        return job
    
    async def get_job(self, job_id: str, user_id: str) -> Optional[ScrapingJob]:
        """Get a job by ID."""
        # This would query the database
        # For now, return a placeholder job
        if job_id == "test-job-id":
            return ScrapingJob(
                id=job_id,
                url="https://example.com",
                status=JobStatus.RUNNING,
                created_at=datetime.utcnow(),
                user_id=user_id
            )
        return None
    
    async def update_job(self, job_id: str, updates: UpdateJobRequest, user_id: str) -> Optional[ScrapingJob]:
        """Update a job."""
        job = await self.get_job(job_id, user_id)
        if not job:
            return None
        
        # Apply updates
        if updates.status:
            job.status = updates.status
        if updates.priority:
            job.priority = updates.priority
        if updates.tags is not None:
            job.tags = updates.tags
        
        # Here you would save to database
        logger.info(f"Updated job {job_id}")
        return job
    
    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """Delete a job."""
        job = await self.get_job(job_id, user_id)
        if not job:
            return False
        
        # Here you would delete from database and cancel if running
        logger.info(f"Deleted job {job_id}")
        return True
    
    async def list_jobs(self, user_id: str, status: Optional[JobStatus] = None, 
                       page: int = 1, page_size: int = 50) -> tuple[List[ScrapingJob], int]:
        """List jobs for a user."""
        # This would query the database with filters
        # For now, return placeholder data
        jobs = [
            ScrapingJob(
                id=f"job-{i}",
                url=f"https://example{i}.com",
                status=JobStatus.COMPLETED if i % 2 == 0 else JobStatus.RUNNING,
                created_at=datetime.utcnow(),
                user_id=user_id
            )
            for i in range(1, 6)
        ]
        
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        total_count = len(jobs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        jobs = jobs[start_idx:end_idx]
        
        return jobs, total_count


# Create service instance
job_service = JobService()


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Scraping Job",
    description="Create a new web scraping job with specified configuration"
)
async def create_job(
    job_request: CreateJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new scraping job.
    
    Creates a new scraping job with the provided URL and configuration.
    The job will be queued for processing and can be monitored via other endpoints.
    """
    try:
        job = await job_service.create_job(job_request, current_user["user_id"])
        
        return JobResponse(
            job=job,
            message="Scraping job created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scraping job"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get Scraping Job",
    description="Retrieve details of a specific scraping job"
)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific scraping job by ID.
    
    Returns detailed information about the job including status,
    configuration, and progress metrics.
    """
    job = await job_service.get_job(job_id, current_user["user_id"])
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse(
        job=job,
        message="Job retrieved successfully"
    )


@router.put(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Update Scraping Job",
    description="Update properties of an existing scraping job"
)
async def update_job(
    job_id: str,
    job_update: UpdateJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a scraping job.
    
    Allows updating job status, priority, and tags.
    Some updates may not be allowed depending on current job status.
    """
    job = await job_service.update_job(job_id, job_update, current_user["user_id"])
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse(
        job=job,
        message="Job updated successfully"
    )


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Scraping Job",
    description="Delete a scraping job and all associated data"
)
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a scraping job.
    
    Permanently deletes the job and all associated scraped data.
    Running jobs will be cancelled before deletion.
    """
    success = await job_service.delete_job(job_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List Scraping Jobs",
    description="Retrieve a paginated list of scraping jobs with optional filtering"
)
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    List scraping jobs for the current user.
    
    Returns a paginated list of jobs with optional status filtering.
    Results are ordered by creation date (newest first).
    """
    jobs, total_count = await job_service.list_jobs(
        current_user["user_id"], 
        status_filter, 
        page, 
        page_size
    )
    
    has_next = (page * page_size) < total_count
    has_previous = page > 1
    
    return JobListResponse(
        jobs=jobs,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=has_next,
        has_previous=has_previous
    )


@router.post(
    "/jobs/bulk",
    response_model=JobListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Multiple Jobs",
    description="Create multiple scraping jobs with the same configuration"
)
async def create_bulk_jobs(
    bulk_request: BulkJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create multiple scraping jobs at once.
    
    Creates jobs for all provided URLs using the same configuration.
    Useful for batch scraping operations.
    """
    try:
        jobs = []
        
        for url in bulk_request.urls:
            job_request = CreateJobRequest(
                url=url,
                config=bulk_request.config,
                tags=bulk_request.tags,
                priority=bulk_request.priority
            )
            
            job = await job_service.create_job(job_request, current_user["user_id"])
            jobs.append(job)
        
        return JobListResponse(
            jobs=jobs,
            total_count=len(jobs),
            page=1,
            page_size=len(jobs),
            has_next=False,
            has_previous=False
        )
        
    except Exception as e:
        logger.error(f"Failed to create bulk jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bulk jobs"
        )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobResponse,
    summary="Cancel Scraping Job",
    description="Cancel a running or pending scraping job"
)
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a scraping job.
    
    Cancels a running or pending job. Completed jobs cannot be cancelled.
    """
    job_update = UpdateJobRequest(status=JobStatus.CANCELLED)
    job = await job_service.update_job(job_id, job_update, current_user["user_id"])
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed or failed job"
        )
    
    return JobResponse(
        job=job,
        message="Job cancelled successfully"
    )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=JobResponse,
    summary="Retry Failed Job",
    description="Retry a failed scraping job"
)
async def retry_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retry a failed scraping job.
    
    Requeues a failed job for processing. Only failed jobs can be retried.
    """
    job = await job_service.get_job(job_id, current_user["user_id"])
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed jobs can be retried"
        )
    
    job_update = UpdateJobRequest(status=JobStatus.PENDING)
    updated_job = await job_service.update_job(job_id, job_update, current_user["user_id"])
    
    return JobResponse(
        job=updated_job,
        message="Job queued for retry"
    )


@router.get(
    "/jobs/stats",
    response_model=JobStatsResponse,
    summary="Job Statistics",
    description="Get statistics about scraping jobs"
)
async def get_job_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get job statistics for the current user.
    
    Returns comprehensive statistics about job performance,
    success rates, and common errors.
    """
    # This would query the database for actual statistics
    # For now, return placeholder data
    return JobStatsResponse(
        total_jobs=150,
        jobs_by_status={
            JobStatus.COMPLETED: 120,
            JobStatus.RUNNING: 5,
            JobStatus.PENDING: 10,
            JobStatus.FAILED: 12,
            JobStatus.CANCELLED: 3
        },
        average_completion_time=45.5,
        success_rate=0.92,
        most_common_errors=[
            {"error": "Connection timeout", "count": 8},
            {"error": "Page not found", "count": 3},
            {"error": "Rate limited", "count": 1}
        ],
        performance_metrics={
            "average_pages_per_minute": 25.3,
            "average_data_quality": 0.87,
            "total_data_extracted_mb": 1250.5
        }
    )


@router.post(
    "/jobs/batch",
    response_model=BatchOperationResponse,
    summary="Batch Job Operations",
    description="Perform batch operations on multiple jobs"
)
async def batch_job_operation(
    batch_request: BatchOperationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Perform batch operations on multiple jobs.
    
    Supports operations like cancel, retry, delete on multiple jobs at once.
    """
    try:
        results = []
        successful_items = 0
        failed_items = 0
        
        for job_id in batch_request.job_ids:
            try:
                if batch_request.operation == "cancel":
                    job_update = UpdateJobRequest(status=JobStatus.CANCELLED)
                    job = await job_service.update_job(job_id, job_update, current_user["user_id"])
                    if job:
                        results.append({"job_id": job_id, "status": "success"})
                        successful_items += 1
                    else:
                        results.append({"job_id": job_id, "status": "not_found"})
                        failed_items += 1
                        
                elif batch_request.operation == "delete":
                    success = await job_service.delete_job(job_id, current_user["user_id"])
                    if success:
                        results.append({"job_id": job_id, "status": "success"})
                        successful_items += 1
                    else:
                        results.append({"job_id": job_id, "status": "not_found"})
                        failed_items += 1
                        
                else:
                    results.append({"job_id": job_id, "status": "unsupported_operation"})
                    failed_items += 1
                    
            except Exception as e:
                logger.error(f"Batch operation failed for job {job_id}: {e}")
                results.append({"job_id": job_id, "status": "error", "error": str(e)})
                failed_items += 1
        
        return BatchOperationResponse(
            operation_id=str(uuid4()),
            operation=batch_request.operation,
            total_items=len(batch_request.job_ids),
            successful_items=successful_items,
            failed_items=failed_items,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Batch operation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch operation failed"
        )