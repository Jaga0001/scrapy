"""
Export Manager for handling data export operations.

This module provides functionality to export scraped data in various formats
including CSV, JSON, and XLSX with filtering and field selection capabilities.
"""

import asyncio
import csv
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
import zipfile

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.pydantic_models import ScrapedData, DataExportRequest
from src.models.database_models import ScrapedDataORM, DataExportORM
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExportManager:
    """
    Manager for handling data export operations.
    
    Supports exporting scraped data in multiple formats with filtering,
    field selection, and compression capabilities.
    """
    
    def __init__(self, db_session: AsyncSession, export_dir: str = None):
        """
        Initialize export manager.
        
        Args:
            db_session: Database session for data access
            export_dir: Directory for storing export files
        """
        self.db_session = db_session
        self.export_dir = export_dir or tempfile.gettempdir()
        self.logger = get_logger(__name__)
    
    async def create_export(
        self,
        export_request: DataExportRequest,
        user_id: str
    ) -> str:
        """
        Create a new data export job.
        
        Args:
            export_request: Export configuration and filters
            user_id: ID of the user requesting the export
            
        Returns:
            Export job ID
        """
        export_id = str(uuid4())
        
        try:
            # Create export record in database
            export_record = DataExportORM(
                id=export_id,
                format=export_request.format,
                status="pending",
                job_ids=export_request.job_ids or [],
                date_from=export_request.date_from,
                date_to=export_request.date_to,
                min_confidence=export_request.min_confidence,
                include_raw_html=export_request.include_raw_html,
                fields=export_request.fields or [],
                user_id=user_id,
                requested_at=datetime.utcnow()
            )
            
            self.db_session.add(export_record)
            await self.db_session.commit()
            
            # Start export processing in background
            asyncio.create_task(self._process_export(export_id, export_request))
            
            self.logger.info(f"Created export job {export_id} for user {user_id}")
            return export_id
            
        except Exception as e:
            self.logger.error(f"Failed to create export job: {e}")
            await self.db_session.rollback()
            raise
    
    async def _process_export(
        self,
        export_id: str,
        export_request: DataExportRequest
    ) -> None:
        """
        Process the export job in the background.
        
        Args:
            export_id: Export job ID
            export_request: Export configuration
        """
        try:
            # Update status to processing
            await self._update_export_status(export_id, "processing")
            
            # Query data based on filters
            data = await self._query_export_data(export_request)
            
            # Generate export file
            file_path = await self._generate_export_file(
                export_id, 
                data, 
                export_request
            )
            
            # Update export record with file information
            file_size = os.path.getsize(file_path)
            await self._update_export_completion(export_id, file_path, file_size)
            
            self.logger.info(f"Export {export_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Export {export_id} failed: {e}")
            await self._update_export_error(export_id, str(e))
    
    async def _query_export_data(
        self,
        export_request: DataExportRequest
    ) -> List[ScrapedData]:
        """
        Query scraped data based on export filters.
        
        Args:
            export_request: Export configuration with filters
            
        Returns:
            List of scraped data matching filters
        """
        try:
            from sqlalchemy import select, and_
            
            # Build query with filters
            query = select(ScrapedDataORM)
            conditions = []
            
            # Filter by job IDs
            if export_request.job_ids:
                conditions.append(ScrapedDataORM.job_id.in_(export_request.job_ids))
            
            # Filter by date range
            if export_request.date_from:
                conditions.append(ScrapedDataORM.extracted_at >= export_request.date_from)
            
            if export_request.date_to:
                conditions.append(ScrapedDataORM.extracted_at <= export_request.date_to)
            
            # Filter by confidence score
            if export_request.min_confidence > 0:
                conditions.append(ScrapedDataORM.confidence_score >= export_request.min_confidence)
            
            # Apply all conditions
            if conditions:
                query = query.where(and_(*conditions))
            
            # Execute query
            result = await self.db_session.execute(query)
            orm_data = result.scalars().all()
            
            # Convert to Pydantic models
            scraped_data = []
            for orm_item in orm_data:
                data_item = ScrapedData(
                    id=orm_item.id,
                    job_id=orm_item.job_id,
                    url=orm_item.url,
                    content=orm_item.content,
                    raw_html=orm_item.raw_html,
                    content_type=orm_item.content_type,
                    content_metadata=orm_item.content_metadata,
                    confidence_score=orm_item.confidence_score,
                    ai_processed=orm_item.ai_processed,
                    ai_metadata=orm_item.ai_metadata,
                    data_quality_score=orm_item.data_quality_score,
                    validation_errors=orm_item.validation_errors,
                    extracted_at=orm_item.extracted_at,
                    processed_at=orm_item.processed_at,
                    content_length=orm_item.content_length,
                    load_time=orm_item.load_time
                )
                scraped_data.append(data_item)
            
            self.logger.info(f"Queried {len(scraped_data)} records for export")
            return scraped_data
            
        except Exception as e:
            self.logger.error(f"Failed to query export data: {e}")
            raise
    
    async def _generate_export_file(
        self,
        export_id: str,
        data: List[ScrapedData],
        export_request: DataExportRequest
    ) -> str:
        """
        Generate export file in the requested format.
        
        Args:
            export_id: Export job ID
            data: Data to export
            export_request: Export configuration
            
        Returns:
            Path to generated file
        """
        try:
            # Prepare data for export
            export_data = self._prepare_export_data(data, export_request)
            
            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{export_id}_{timestamp}.{export_request.format}"
            file_path = os.path.join(self.export_dir, filename)
            
            # Generate file based on format
            if export_request.format == "csv":
                await self._generate_csv_file(file_path, export_data)
            elif export_request.format == "json":
                await self._generate_json_file(file_path, export_data)
            elif export_request.format == "xlsx":
                await self._generate_xlsx_file(file_path, export_data)
            else:
                raise ValueError(f"Unsupported export format: {export_request.format}")
            
            self.logger.info(f"Generated export file: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate export file: {e}")
            raise
    
    def _prepare_export_data(
        self,
        data: List[ScrapedData],
        export_request: DataExportRequest
    ) -> List[Dict[str, Any]]:
        """
        Prepare data for export by selecting fields and formatting.
        
        Args:
            data: Raw scraped data
            export_request: Export configuration
            
        Returns:
            Prepared data for export
        """
        export_data = []
        
        for item in data:
            # Convert to dictionary
            item_dict = item.model_dump()
            
            # Filter fields if specified
            if export_request.fields:
                filtered_dict = {}
                for field in export_request.fields:
                    if field in item_dict:
                        filtered_dict[field] = item_dict[field]
                    elif field in item_dict.get('content', {}):
                        # Allow accessing nested content fields
                        filtered_dict[field] = item_dict['content'][field]
                item_dict = filtered_dict
            
            # Handle raw HTML inclusion
            if not export_request.include_raw_html and 'raw_html' in item_dict:
                del item_dict['raw_html']
            
            # Flatten complex fields for CSV compatibility
            if export_request.format == "csv":
                item_dict = self._flatten_dict_for_csv(item_dict)
            
            export_data.append(item_dict)
        
        return export_data
    
    def _flatten_dict_for_csv(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested dictionaries for CSV export.
        
        Args:
            data: Dictionary to flatten
            
        Returns:
            Flattened dictionary
        """
        flattened = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # Flatten nested dictionaries
                for nested_key, nested_value in value.items():
                    flattened[f"{key}_{nested_key}"] = str(nested_value)
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                flattened[key] = ", ".join(str(v) for v in value)
            else:
                flattened[key] = value
        
        return flattened
    
    async def _generate_csv_file(
        self,
        file_path: str,
        data: List[Dict[str, Any]]
    ) -> None:
        """Generate CSV export file."""
        if not data:
            # Create empty CSV with headers
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['id', 'job_id', 'url', 'extracted_at'])
            return
        
        # Get all unique keys for headers
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())
        
        headers = sorted(all_keys)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for item in data:
                # Ensure all fields are present
                row = {key: item.get(key, '') for key in headers}
                writer.writerow(row)
    
    async def _generate_json_file(
        self,
        file_path: str,
        data: List[Dict[str, Any]]
    ) -> None:
        """Generate JSON export file."""
        export_structure = {
            "export_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_records": len(data),
                "format": "json"
            },
            "data": data
        }
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_structure, jsonfile, indent=2, default=str)
    
    async def _generate_xlsx_file(
        self,
        file_path: str,
        data: List[Dict[str, Any]]
    ) -> None:
        """Generate XLSX export file."""
        if not data:
            # Create empty DataFrame
            df = pd.DataFrame(columns=['id', 'job_id', 'url', 'extracted_at'])
        else:
            df = pd.DataFrame(data)
        
        # Create Excel writer with multiple sheets
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Scraped Data', index=False)
            
            # Summary sheet
            summary_data = {
                'Metric': ['Total Records', 'Export Generated At', 'Format'],
                'Value': [len(data), datetime.utcnow().isoformat(), 'xlsx']
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Export Summary', index=False)
    
    async def _update_export_status(self, export_id: str, status: str) -> None:
        """Update export status in database."""
        try:
            from sqlalchemy import update
            
            stmt = update(DataExportORM).where(
                DataExportORM.id == export_id
            ).values(status=status)
            
            await self.db_session.execute(stmt)
            await self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update export status: {e}")
            await self.db_session.rollback()
    
    async def _update_export_completion(
        self,
        export_id: str,
        file_path: str,
        file_size: int
    ) -> None:
        """Update export completion in database."""
        try:
            from sqlalchemy import update
            
            stmt = update(DataExportORM).where(
                DataExportORM.id == export_id
            ).values(
                status="completed",
                file_path=file_path,
                file_size=file_size,
                completed_at=datetime.utcnow()
            )
            
            await self.db_session.execute(stmt)
            await self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update export completion: {e}")
            await self.db_session.rollback()
    
    async def _update_export_error(self, export_id: str, error_message: str) -> None:
        """Update export error in database."""
        try:
            from sqlalchemy import update
            
            stmt = update(DataExportORM).where(
                DataExportORM.id == export_id
            ).values(
                status="failed",
                error_message=error_message,
                completed_at=datetime.utcnow()
            )
            
            await self.db_session.execute(stmt)
            await self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update export error: {e}")
            await self.db_session.rollback()
    
    async def get_export_status(self, export_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get export status and information.
        
        Args:
            export_id: Export job ID
            user_id: User ID for authorization
            
        Returns:
            Export status information or None if not found
        """
        try:
            from sqlalchemy import select
            
            query = select(DataExportORM).where(
                DataExportORM.id == export_id,
                DataExportORM.user_id == user_id
            )
            
            result = await self.db_session.execute(query)
            export_record = result.scalar_one_or_none()
            
            if not export_record:
                return None
            
            return {
                "export_id": export_record.id,
                "status": export_record.status,
                "format": export_record.format,
                "file_size": export_record.file_size,
                "created_at": export_record.requested_at,
                "completed_at": export_record.completed_at,
                "error_message": export_record.error_message
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get export status: {e}")
            return None
    
    async def delete_export(self, export_id: str, user_id: str) -> bool:
        """
        Delete an export job and its associated file.
        
        Args:
            export_id: Export job ID
            user_id: User ID for authorization
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            from sqlalchemy import select, delete
            
            # Get export record
            query = select(DataExportORM).where(
                DataExportORM.id == export_id,
                DataExportORM.user_id == user_id
            )
            
            result = await self.db_session.execute(query)
            export_record = result.scalar_one_or_none()
            
            if not export_record:
                return False
            
            # Delete file if it exists
            if export_record.file_path and os.path.exists(export_record.file_path):
                try:
                    os.remove(export_record.file_path)
                    self.logger.info(f"Deleted export file: {export_record.file_path}")
                except OSError as e:
                    self.logger.warning(f"Failed to delete export file: {e}")
            
            # Delete database record
            delete_stmt = delete(DataExportORM).where(
                DataExportORM.id == export_id,
                DataExportORM.user_id == user_id
            )
            
            await self.db_session.execute(delete_stmt)
            await self.db_session.commit()
            
            self.logger.info(f"Deleted export {export_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete export: {e}")
            await self.db_session.rollback()
            return False
    
    async def cleanup_old_exports(self, days_old: int = 7) -> int:
        """
        Clean up old export files and records.
        
        Args:
            days_old: Delete exports older than this many days
            
        Returns:
            Number of exports cleaned up
        """
        try:
            from sqlalchemy import select, delete
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old exports
            query = select(DataExportORM).where(
                DataExportORM.requested_at < cutoff_date
            )
            
            result = await self.db_session.execute(query)
            old_exports = result.scalars().all()
            
            cleaned_count = 0
            
            for export_record in old_exports:
                # Delete file if it exists
                if export_record.file_path and os.path.exists(export_record.file_path):
                    try:
                        os.remove(export_record.file_path)
                    except OSError as e:
                        self.logger.warning(f"Failed to delete old export file: {e}")
                
                cleaned_count += 1
            
            # Delete database records
            if old_exports:
                delete_stmt = delete(DataExportORM).where(
                    DataExportORM.requested_at < cutoff_date
                )
                
                await self.db_session.execute(delete_stmt)
                await self.db_session.commit()
            
            self.logger.info(f"Cleaned up {cleaned_count} old exports")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old exports: {e}")
            await self.db_session.rollback()
            return 0