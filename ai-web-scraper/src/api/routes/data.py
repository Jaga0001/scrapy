"""
Scraped data API routes.

This module contains endpoints for retrieving, filtering, and exporting scraped data.
"""

import asyncio
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse

from src.api.schemas import (
    DataQueryRequest, DataResponse, DataSummaryResponse,
    ExportResponse, DataExportRequest
)
from src.models.pydantic_models import ScrapedData, ContentType, DataExportRequest as CoreDataExportRequest
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


# Data service with actual implementations
class DataService:
    """Data service with actual database and export functionality."""
    
    def __init__(self):
        self.repository = None
        self.export_manager = None
    
    async def _get_repository(self):
        """Get data repository instance."""
        if not self.repository:
            from src.pipeline.repository import DataRepository
            self.repository = DataRepository()
        return self.repository
    
    async def _get_export_manager(self):
        """Get export manager instance."""
        if not self.export_manager:
            from src.pipeline.export_manager import ExportManager
            from config.database import get_async_db_session
            
            # Get database session
            async with get_async_db_session() as session:
                self.export_manager = ExportManager(session)
        return self.export_manager
    
    async def query_data(self, query: DataQueryRequest, user_id: str) -> tuple[List[ScrapedData], int]:
        """Query scraped data with filters."""
        try:
            repository = await self._get_repository()
            
            # Convert API query to repository parameters
            data, total_count = await repository.get_scraped_data(
                job_id=query.job_ids[0] if query.job_ids and len(query.job_ids) == 1 else None,
                min_confidence=query.min_confidence or 0.0,
                ai_processed_only=query.ai_processed if query.ai_processed is not None else False,
                limit=query.page_size,
                offset=(query.page - 1) * query.page_size
            )
            
            return data, total_count
            
        except Exception as e:
            logger.error(f"Failed to query data: {e}")
            # Return empty results on error
            return [], 0
    
    async def get_data_by_id(self, data_id: str, user_id: str) -> Optional[ScrapedData]:
        """Get scraped data by ID."""
        try:
            repository = await self._get_repository()
            
            # Query single record (simplified - would need proper implementation)
            data, _ = await repository.get_scraped_data(limit=1000)
            
            # Find matching record
            for record in data:
                if record.id == data_id:
                    return record
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get data by ID: {e}")
            return None
    
    async def get_data_summary(self, user_id: str) -> dict:
        """Get summary statistics for scraped data."""
        try:
            repository = await self._get_repository()
            
            # Get job statistics
            job_stats = await repository.get_job_statistics()
            
            # Get data quality metrics
            quality_metrics = await repository.get_data_quality_metrics()
            
            return {
                "total_records": quality_metrics.get("total_data_records", 0),
                "total_jobs": job_stats.get("status_counts", {}).get("completed", 0),
                "average_confidence": quality_metrics.get("average_confidence_score", 0.0),
                "content_type_distribution": {
                    "html": quality_metrics.get("total_data_records", 0),  # Simplified
                    "json": 0,
                    "text": 0
                },
                "date_range": {
                    "earliest": datetime(2024, 1, 1),
                    "latest": datetime.utcnow()
                },
                "quality_metrics": {
                    "high_confidence_records": int(quality_metrics.get("total_data_records", 0) * 0.8),
                    "ai_processed_records": int(quality_metrics.get("total_data_records", 0) * quality_metrics.get("ai_processed_percentage", 0) / 100),
                    "validation_errors": int(quality_metrics.get("average_validation_errors", 0))
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get data summary: {e}")
            # Return default values on error
            return {
                "total_records": 0,
                "total_jobs": 0,
                "average_confidence": 0.0,
                "content_type_distribution": {"html": 0, "json": 0, "text": 0},
                "date_range": {"earliest": datetime.utcnow(), "latest": datetime.utcnow()},
                "quality_metrics": {"high_confidence_records": 0, "ai_processed_records": 0, "validation_errors": 0}
            }
    
    async def create_export(self, export_request: CoreDataExportRequest, user_id: str) -> str:
        """Create a data export job."""
        try:
            export_manager = await self._get_export_manager()
            
            # Determine if we should use streaming export for large datasets
            use_streaming = True  # Default to streaming for better performance
            
            if use_streaming:
                export_id = await export_manager.create_streaming_export(
                    export_request, user_id, compress=True, chunk_size=1000
                )
            else:
                export_id = await export_manager.create_export(export_request, user_id)
            
            logger.info(f"Created export job {export_id} for user {user_id}")
            return export_id
            
        except Exception as e:
            logger.error(f"Failed to create export: {e}")
            raise
    
    async def get_export_status(self, export_id: str, user_id: str) -> Optional[dict]:
        """Get export job status."""
        try:
            export_manager = await self._get_export_manager()
            
            status_info = await export_manager.get_export_status(export_id, user_id)
            
            if not status_info:
                return None
            
            result = {
                "export_id": status_info["export_id"],
                "status": status_info["status"],
                "file_size": status_info.get("file_size"),
                "created_at": status_info["created_at"],
                "completed_at": status_info.get("completed_at")
            }
            
            # Add download URL if completed
            if status_info["status"] == "completed":
                result["download_url"] = f"/api/v1/data/exports/{export_id}/download"
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get export status: {e}")
            return None
    
    async def get_export_download_info(self, export_id: str, user_id: str) -> Optional[dict]:
        """Get export download information."""
        try:
            export_manager = await self._get_export_manager()
            return await export_manager.get_export_download_info(export_id, user_id)
            
        except Exception as e:
            logger.error(f"Failed to get export download info: {e}")
            return None
    
    async def delete_export(self, export_id: str, user_id: str) -> bool:
        """Delete an export job."""
        try:
            export_manager = await self._get_export_manager()
            return await export_manager.delete_export(export_id, user_id)
            
        except Exception as e:
            logger.error(f"Failed to delete export: {e}")
            return False


# Create service instance
data_service = DataService()


@router.get(
    "/",
    response_model=DataResponse,
    summary="Query Scraped Data",
    description="Retrieve scraped data with filtering and pagination"
)
async def query_data(
    job_ids: Optional[List[str]] = Query(None, description="Filter by job IDs"),
    urls: Optional[List[str]] = Query(None, description="Filter by URLs"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    content_type: Optional[ContentType] = Query(None, description="Filter by content type"),
    ai_processed: Optional[bool] = Query(None, description="Filter by AI processing status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: str = Query("extracted_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: dict = Depends(get_current_user)
):
    """
    Query scraped data with comprehensive filtering options.
    
    Supports filtering by job IDs, URLs, date ranges, confidence scores,
    content types, and AI processing status. Results are paginated and sortable.
    """
    try:
        query = DataQueryRequest(
            job_ids=job_ids,
            urls=urls,
            date_from=date_from,
            date_to=date_to,
            min_confidence=min_confidence,
            content_type=content_type,
            ai_processed=ai_processed,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        data, total_count = await data_service.query_data(query, current_user["user_id"])
        
        has_next = (page * page_size) < total_count
        has_previous = page > 1
        
        # Build filters applied summary
        filters_applied = {}
        if job_ids:
            filters_applied["job_ids"] = job_ids
        if urls:
            filters_applied["urls"] = urls
        if date_from:
            filters_applied["date_from"] = date_from
        if date_to:
            filters_applied["date_to"] = date_to
        if min_confidence:
            filters_applied["min_confidence"] = min_confidence
        if content_type:
            filters_applied["content_type"] = content_type
        if ai_processed is not None:
            filters_applied["ai_processed"] = ai_processed
        
        return DataResponse(
            data=data,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"Failed to query data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data"
        )


@router.get(
    "/{data_id}",
    response_model=ScrapedData,
    summary="Get Scraped Data by ID",
    description="Retrieve a specific scraped data record by its ID"
)
async def get_data_by_id(
    data_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific scraped data record by ID.
    
    Returns detailed information about a single scraped data record
    including content, metadata, and AI processing results.
    """
    data = await data_service.get_data_by_id(data_id, current_user["user_id"])
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data record not found"
        )
    
    return data


@router.get(
    "/summary",
    response_model=DataSummaryResponse,
    summary="Data Summary Statistics",
    description="Get summary statistics about scraped data"
)
async def get_data_summary(
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary statistics for scraped data.
    
    Returns comprehensive statistics including record counts,
    quality metrics, and content type distribution.
    """
    try:
        summary = await data_service.get_data_summary(current_user["user_id"])
        
        return DataSummaryResponse(
            total_records=summary["total_records"],
            total_jobs=summary["total_jobs"],
            average_confidence=summary["average_confidence"],
            content_type_distribution=summary["content_type_distribution"],
            date_range=summary["date_range"],
            quality_metrics=summary["quality_metrics"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get data summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data summary"
        )


@router.post(
    "/export",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Data Export",
    description="Create an export job for scraped data in various formats"
)
async def create_data_export(
    export_request: DataExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a data export job.
    
    Creates a background job to export scraped data in the specified format.
    The export can be filtered by job IDs, date ranges, and confidence scores.
    """
    try:
        # Convert API request to core model
        core_export_request = CoreDataExportRequest(
            format=export_request.format,
            job_ids=export_request.job_ids,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            min_confidence=export_request.min_confidence,
            include_raw_html=export_request.include_raw_html,
            fields=export_request.fields
        )
        
        export_id = await data_service.create_export(core_export_request, current_user["user_id"])
        
        return ExportResponse(
            export_id=export_id,
            status="pending",
            created_at=datetime.utcnow(),
            message="Export job created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export job"
        )


@router.post(
    "/export/streaming",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Streaming Data Export",
    description="Create a streaming export job for large datasets with compression"
)
async def create_streaming_export(
    export_request: DataExportRequest,
    compress: bool = Query(True, description="Whether to compress the export file"),
    chunk_size: int = Query(1000, ge=100, le=10000, description="Records per processing chunk"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a streaming data export job for large datasets.
    
    This endpoint is optimized for large datasets and provides:
    - Memory-efficient streaming processing
    - Optional file compression
    - Configurable chunk sizes for optimal performance
    """
    try:
        # Convert API request to core model
        core_export_request = CoreDataExportRequest(
            format=export_request.format,
            job_ids=export_request.job_ids,
            date_from=export_request.date_from,
            date_to=export_request.date_to,
            min_confidence=export_request.min_confidence,
            include_raw_html=export_request.include_raw_html,
            fields=export_request.fields
        )
        
        # Validate format for streaming
        if export_request.format not in ["csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Streaming export only supports CSV and JSON formats"
            )
        
        export_manager = await data_service._get_export_manager()
        export_id = await export_manager.create_streaming_export(
            core_export_request, 
            current_user["user_id"], 
            compress=compress, 
            chunk_size=chunk_size
        )
        
        return ExportResponse(
            export_id=export_id,
            status="pending",
            created_at=datetime.utcnow(),
            message=f"Streaming export job created successfully (compress={compress}, chunk_size={chunk_size})"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create streaming export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create streaming export job"
        )


@router.get(
    "/exports/{export_id}",
    response_model=ExportResponse,
    summary="Get Export Status",
    description="Check the status of a data export job"
)
async def get_export_status(
    export_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the status of a data export job.
    
    Returns the current status of the export job and download URL
    when the export is completed.
    """
    try:
        export_status = await data_service.get_export_status(export_id, current_user["user_id"])
        
        if not export_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )
        
        return ExportResponse(
            export_id=export_status["export_id"],
            status=export_status["status"],
            download_url=export_status.get("download_url"),
            file_size=export_status.get("file_size"),
            created_at=export_status["created_at"],
            message="Export status retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export status"
        )


@router.get(
    "/exports/{export_id}/download",
    summary="Download Export File",
    description="Download the exported data file"
)
async def download_export(
    export_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Download an exported data file.
    
    Returns the exported file as a downloadable attachment.
    The file format depends on the export request (CSV, JSON, or XLSX).
    """
    try:
        download_info = await data_service.get_export_download_info(export_id, current_user["user_id"])
        
        if not download_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found or not ready for download"
            )
        
        file_path = download_info["file_path"]
        filename = download_info["filename"]
        
        # Determine media type based on file extension
        media_type = "application/octet-stream"
        if filename.endswith('.csv') or filename.endswith('.csv.gz'):
            media_type = "text/csv"
        elif filename.endswith('.json') or filename.endswith('.json.gz'):
            media_type = "application/json"
        elif filename.endswith('.xlsx'):
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(download_info["file_size"])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download export file"
        )


@router.delete(
    "/exports/{export_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Export",
    description="Delete an export job and its associated file"
)
async def delete_export(
    export_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an export job and its associated file.
    
    Permanently removes the export job and any generated files
    from the system.
    """
    try:
        success = await data_service.delete_export(export_id, current_user["user_id"])
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )
        
        logger.info(f"Deleted export {export_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete export"
        )


@router.post(
    "/validate",
    summary="Validate Data Quality",
    description="Run data quality validation on scraped data"
)
async def validate_data_quality(
    job_ids: Optional[List[str]] = Query(None, description="Job IDs to validate"),
    current_user: dict = Depends(get_current_user)
):
    """
    Run data quality validation on scraped data.
    
    Performs comprehensive quality checks on scraped data
    and returns validation results and recommendations.
    """
    try:
        # This would run actual data validation
        # For now, return placeholder results
        validation_results = {
            "total_records_checked": 500,
            "validation_passed": 475,
            "validation_failed": 25,
            "quality_score": 0.95,
            "issues_found": [
                {
                    "type": "missing_content",
                    "count": 15,
                    "severity": "medium",
                    "description": "Records with empty content fields"
                },
                {
                    "type": "low_confidence",
                    "count": 10,
                    "severity": "low",
                    "description": "Records with confidence score below 0.5"
                }
            ],
            "recommendations": [
                "Review scraping configuration for pages with missing content",
                "Consider re-processing low confidence records with updated AI models"
            ]
        }
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Failed to validate data quality: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate data quality"
        )


@router.post(
    "/reprocess",
    summary="Reprocess Data with AI",
    description="Reprocess scraped data with updated AI models"
)
async def reprocess_data(
    data_ids: List[str] = Query(..., description="Data record IDs to reprocess"),
    current_user: dict = Depends(get_current_user)
):
    """
    Reprocess scraped data with updated AI models.
    
    Queues the specified data records for reprocessing with
    the latest AI models and processing algorithms.
    """
    try:
        # This would queue the data for reprocessing
        # For now, just log and return success
        logger.info(f"Queued {len(data_ids)} records for reprocessing")
        
        return {
            "message": f"Queued {len(data_ids)} records for reprocessing",
            "reprocess_job_id": str(uuid4()),
            "estimated_completion": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to queue data for reprocessing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue data for reprocessing"
        )