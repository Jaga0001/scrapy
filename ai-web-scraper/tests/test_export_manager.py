"""
Unit tests for the ExportManager class.

This module contains comprehensive tests for data export functionality
including CSV, JSON, and XLSX exports with filtering and streaming capabilities.
"""

import asyncio
import csv
import gzip
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.pydantic_models import (
    ContentType, DataExportRequest, ScrapedData, ScrapingConfig
)
from src.models.database_models import DataExportORM, ScrapedDataORM
from src.pipeline.export_manager import ExportManager


class TestExportManager:
    """Test suite for ExportManager class."""
    
    @pytest_asyncio.fixture
    async def export_manager(self, test_session):
        """Create ExportManager instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ExportManager(test_session, temp_dir)
            yield manager
    
    @pytest.fixture
    def sample_export_request(self):
        """Create sample export request for testing."""
        return DataExportRequest(
            format="csv",
            job_ids=["job-1", "job-2"],
            date_from=datetime.utcnow() - timedelta(days=7),
            date_to=datetime.utcnow(),
            min_confidence=0.5,
            include_raw_html=False,
            fields=["id", "url", "content", "confidence_score"]
        )
    
    @pytest.fixture
    def sample_scraped_data(self):
        """Create sample scraped data for testing."""
        return [
            ScrapedData(
                id=str(uuid4()),
                job_id="job-1",
                url="https://example.com/page1",
                content={"title": "Test Page 1", "text": "Content 1"},
                raw_html="<html><body>Test 1</body></html>",
                content_type=ContentType.HTML,
                content_metadata={"language": "en"},
                confidence_score=0.9,
                ai_processed=True,
                ai_metadata={"entities": ["Test"]},
                data_quality_score=0.85,
                validation_errors=[],
                extracted_at=datetime.utcnow(),
                processed_at=datetime.utcnow(),
                content_length=100,
                load_time=1.5
            ),
            ScrapedData(
                id=str(uuid4()),
                job_id="job-2",
                url="https://example.com/page2",
                content={"title": "Test Page 2", "text": "Content 2"},
                raw_html="<html><body>Test 2</body></html>",
                content_type=ContentType.HTML,
                content_metadata={"language": "en"},
                confidence_score=0.7,
                ai_processed=True,
                ai_metadata={"entities": ["Test"]},
                data_quality_score=0.75,
                validation_errors=[],
                extracted_at=datetime.utcnow(),
                processed_at=datetime.utcnow(),
                content_length=120,
                load_time=2.0
            )
        ]
    
    # ==================== Basic Export Tests ====================
    
    @pytest.mark.asyncio
    async def test_create_export_success(self, export_manager, sample_export_request):
        """Test successful export creation."""
        user_id = "test-user-123"
        
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        assert export_id is not None
        assert len(export_id) == 36  # UUID length
        
        # Verify export record was created in database
        export_status = await export_manager.get_export_status(export_id, user_id)
        assert export_status is not None
        assert export_status["status"] == "pending"
        assert export_status["format"] == "csv"
    
    @pytest.mark.asyncio
    async def test_create_export_with_invalid_format(self, export_manager):
        """Test export creation with invalid format."""
        invalid_request = DataExportRequest(format="invalid")
        user_id = "test-user-123"
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            await export_manager.create_export(invalid_request, user_id)
    
    @pytest.mark.asyncio
    async def test_get_export_status_not_found(self, export_manager):
        """Test getting status for non-existent export."""
        result = await export_manager.get_export_status("non-existent", "user-123")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_export_status_wrong_user(self, export_manager, sample_export_request):
        """Test getting status with wrong user ID."""
        user_id = "test-user-123"
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        result = await export_manager.get_export_status(export_id, "wrong-user")
        assert result is None
    
    # ==================== Data Preparation Tests ====================
    
    def test_prepare_export_data_field_filtering(self, export_manager, sample_scraped_data):
        """Test data preparation with field filtering."""
        export_request = DataExportRequest(
            format="csv",
            fields=["id", "url", "confidence_score"]
        )
        
        result = export_manager._prepare_export_data(sample_scraped_data, export_request)
        
        assert len(result) == 2
        for item in result:
            assert set(item.keys()) == {"id", "url", "confidence_score"}
            assert "content" not in item
            assert "raw_html" not in item
    
    def test_prepare_export_data_raw_html_exclusion(self, export_manager, sample_scraped_data):
        """Test data preparation excludes raw HTML by default."""
        export_request = DataExportRequest(format="csv", include_raw_html=False)
        
        result = export_manager._prepare_export_data(sample_scraped_data, export_request)
        
        for item in result:
            assert "raw_html" not in item
    
    def test_prepare_export_data_raw_html_inclusion(self, export_manager, sample_scraped_data):
        """Test data preparation includes raw HTML when requested."""
        export_request = DataExportRequest(format="csv", include_raw_html=True)
        
        result = export_manager._prepare_export_data(sample_scraped_data, export_request)
        
        for item in result:
            assert "raw_html" in item
            assert item["raw_html"] is not None
    
    def test_flatten_dict_for_csv(self, export_manager):
        """Test dictionary flattening for CSV compatibility."""
        test_data = {
            "id": "123",
            "content": {"title": "Test", "text": "Content"},
            "metadata": {"lang": "en", "score": 0.9},
            "tags": ["tag1", "tag2"]
        }
        
        result = export_manager._flatten_dict_for_csv(test_data)
        
        assert result["id"] == "123"
        assert result["content_title"] == "Test"
        assert result["content_text"] == "Content"
        assert result["metadata_lang"] == "en"
        assert result["metadata_score"] == "0.9"
        assert result["tags"] == "tag1, tag2"
    
    # ==================== CSV Export Tests ====================
    
    @pytest.mark.asyncio
    async def test_generate_csv_file_success(self, export_manager, sample_scraped_data):
        """Test successful CSV file generation."""
        export_request = DataExportRequest(format="csv")
        export_data = export_manager._prepare_export_data(sample_scraped_data, export_request)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_path = temp_file.name
        
        try:
            await export_manager._generate_csv_file(temp_path, export_data)
            
            # Verify file was created and has content
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            
            # Verify CSV structure
            with open(temp_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                assert len(rows) == 2
                assert "id" in reader.fieldnames
                assert "url" in reader.fieldnames
                assert "confidence_score" in reader.fieldnames
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_generate_csv_file_empty_data(self, export_manager):
        """Test CSV file generation with empty data."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_path = temp_file.name
        
        try:
            await export_manager._generate_csv_file(temp_path, [])
            
            # Verify file was created with headers only
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                assert len(rows) == 1  # Header row only
                assert rows[0] == ['id', 'job_id', 'url', 'extracted_at']
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    # ==================== JSON Export Tests ====================
    
    @pytest.mark.asyncio
    async def test_generate_json_file_success(self, export_manager, sample_scraped_data):
        """Test successful JSON file generation."""
        export_request = DataExportRequest(format="json")
        export_data = export_manager._prepare_export_data(sample_scraped_data, export_request)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            await export_manager._generate_json_file(temp_path, export_data)
            
            # Verify file was created and has content
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            
            # Verify JSON structure
            with open(temp_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                assert "export_metadata" in data
                assert "data" in data
                assert data["export_metadata"]["format"] == "json"
                assert data["export_metadata"]["total_records"] == 2
                assert len(data["data"]) == 2
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_generate_json_file_empty_data(self, export_manager):
        """Test JSON file generation with empty data."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            await export_manager._generate_json_file(temp_path, [])
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                assert data["export_metadata"]["total_records"] == 0
                assert len(data["data"]) == 0
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    # ==================== XLSX Export Tests ====================
    
    @pytest.mark.asyncio
    async def test_generate_xlsx_file_success(self, export_manager, sample_scraped_data):
        """Test successful XLSX file generation."""
        export_request = DataExportRequest(format="xlsx")
        export_data = export_manager._prepare_export_data(sample_scraped_data, export_request)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            temp_path = temp_file.name
        
        try:
            await export_manager._generate_xlsx_file(temp_path, export_data)
            
            # Verify file was created and has content
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            
            # Verify XLSX structure
            df = pd.read_excel(temp_path, sheet_name='Scraped Data')
            assert len(df) == 2
            assert 'id' in df.columns
            assert 'url' in df.columns
            
            # Check summary sheet
            summary_df = pd.read_excel(temp_path, sheet_name='Export Summary')
            assert len(summary_df) == 3  # Total Records, Export Generated At, Format
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    # ==================== Streaming Export Tests ====================
    
    @pytest.mark.asyncio
    async def test_create_streaming_export_success(self, export_manager, sample_export_request):
        """Test successful streaming export creation."""
        user_id = "test-user-123"
        
        export_id = await export_manager.create_streaming_export(
            sample_export_request, user_id, compress=True, chunk_size=100
        )
        
        assert export_id is not None
        assert len(export_id) == 36  # UUID length
        
        # Verify export record was created
        export_status = await export_manager.get_export_status(export_id, user_id)
        assert export_status is not None
        assert export_status["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_stream_export_data_empty_result(self, export_manager, sample_export_request):
        """Test streaming export data with no matching records."""
        chunks = []
        async for chunk in export_manager.stream_export_data(sample_export_request, chunk_size=100):
            chunks.append(chunk)
        
        # Should have no chunks since no data exists in test database
        assert len(chunks) == 0
    
    @pytest.mark.asyncio
    async def test_generate_streaming_csv_empty(self, export_manager, sample_export_request):
        """Test streaming CSV generation with empty data."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            temp_path = temp_file.name
        
        try:
            total_records = await export_manager._generate_streaming_csv(
                temp_path, sample_export_request, compress=False, chunk_size=100
            )
            
            assert total_records == 0
            assert os.path.exists(temp_path)
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_generate_streaming_json_empty(self, export_manager, sample_export_request):
        """Test streaming JSON generation with empty data."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            total_records = await export_manager._generate_streaming_json(
                temp_path, sample_export_request, compress=False, chunk_size=100
            )
            
            assert total_records == 0
            assert os.path.exists(temp_path)
            
            # Verify JSON structure
            with open(temp_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                assert data["export_metadata"]["total_records"] == 0
                assert len(data["data"]) == 0
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_generate_streaming_csv_compressed(self, export_manager, sample_export_request):
        """Test streaming CSV generation with compression."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv.gz') as temp_file:
            temp_path = temp_file.name
        
        try:
            total_records = await export_manager._generate_streaming_csv(
                temp_path, sample_export_request, compress=True, chunk_size=100
            )
            
            assert total_records == 0  # No data in test database
            assert os.path.exists(temp_path)
            
            # Verify file is compressed
            with gzip.open(temp_path, 'rt', encoding='utf-8') as gzfile:
                content = gzfile.read()
                assert len(content) > 0  # Should have at least headers
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    # ==================== Export Management Tests ====================
    
    @pytest.mark.asyncio
    async def test_delete_export_success(self, export_manager, sample_export_request):
        """Test successful export deletion."""
        user_id = "test-user-123"
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        # Delete the export
        result = await export_manager.delete_export(export_id, user_id)
        assert result is True
        
        # Verify export is gone
        export_status = await export_manager.get_export_status(export_id, user_id)
        assert export_status is None
    
    @pytest.mark.asyncio
    async def test_delete_export_not_found(self, export_manager):
        """Test deleting non-existent export."""
        result = await export_manager.delete_export("non-existent", "user-123")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_export_wrong_user(self, export_manager, sample_export_request):
        """Test deleting export with wrong user ID."""
        user_id = "test-user-123"
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        result = await export_manager.delete_export(export_id, "wrong-user")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_exports(self, export_manager, sample_export_request):
        """Test cleanup of old export records."""
        user_id = "test-user-123"
        
        # Create an export
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        # Manually update the created timestamp to make it old
        from sqlalchemy import update
        stmt = update(DataExportORM).where(
            DataExportORM.id == export_id
        ).values(requested_at=datetime.utcnow() - timedelta(days=10))
        
        await export_manager.db_session.execute(stmt)
        await export_manager.db_session.commit()
        
        # Run cleanup
        cleaned_count = await export_manager.cleanup_old_exports(days_old=7)
        assert cleaned_count == 1
        
        # Verify export is gone
        export_status = await export_manager.get_export_status(export_id, user_id)
        assert export_status is None
    
    @pytest.mark.asyncio
    async def test_get_export_download_info_success(self, export_manager, sample_export_request):
        """Test getting download info for completed export."""
        user_id = "test-user-123"
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        # Manually update export to completed status with file path
        from sqlalchemy import update
        test_file_path = "/tmp/test_export.csv"
        
        stmt = update(DataExportORM).where(
            DataExportORM.id == export_id
        ).values(
            status="completed",
            file_path=test_file_path,
            file_size=1024,
            completed_at=datetime.utcnow()
        )
        
        await export_manager.db_session.execute(stmt)
        await export_manager.db_session.commit()
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            download_info = await export_manager.get_export_download_info(export_id, user_id)
        
        assert download_info is not None
        assert download_info["export_id"] == export_id
        assert download_info["file_path"] == test_file_path
        assert download_info["file_size"] == 1024
        assert download_info["format"] == "csv"
    
    @pytest.mark.asyncio
    async def test_get_export_download_info_not_completed(self, export_manager, sample_export_request):
        """Test getting download info for non-completed export."""
        user_id = "test-user-123"
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        # Export should still be pending
        download_info = await export_manager.get_export_download_info(export_id, user_id)
        assert download_info is None
    
    @pytest.mark.asyncio
    async def test_get_export_download_info_file_missing(self, export_manager, sample_export_request):
        """Test getting download info when file is missing."""
        user_id = "test-user-123"
        export_id = await export_manager.create_export(sample_export_request, user_id)
        
        # Update to completed but file doesn't exist
        from sqlalchemy import update
        stmt = update(DataExportORM).where(
            DataExportORM.id == export_id
        ).values(
            status="completed",
            file_path="/non/existent/file.csv",
            file_size=1024,
            completed_at=datetime.utcnow()
        )
        
        await export_manager.db_session.execute(stmt)
        await export_manager.db_session.commit()
        
        download_info = await export_manager.get_export_download_info(export_id, user_id)
        assert download_info is None
    
    # ==================== Error Handling Tests ====================
    
    @pytest.mark.asyncio
    async def test_create_export_database_error(self, export_manager, sample_export_request):
        """Test export creation with database error."""
        user_id = "test-user-123"
        
        # Mock database session to raise an error
        export_manager.db_session.add = MagicMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception, match="Database error"):
            await export_manager.create_export(sample_export_request, user_id)
    
    @pytest.mark.asyncio
    async def test_query_export_data_database_error(self, export_manager, sample_export_request):
        """Test data querying with database error."""
        # Mock database session to raise an error
        export_manager.db_session.execute = AsyncMock(side_effect=Exception("Query error"))
        
        with pytest.raises(Exception, match="Query error"):
            await export_manager._query_export_data(sample_export_request)
    
    @pytest.mark.asyncio
    async def test_generate_export_file_invalid_format(self, export_manager, sample_scraped_data):
        """Test export file generation with invalid format."""
        export_request = DataExportRequest(format="invalid")
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            await export_manager._generate_export_file("test", sample_scraped_data, export_request)


# ==================== Integration Tests ====================

class TestExportManagerIntegration:
    """Integration tests for ExportManager with real database operations."""
    
    @pytest_asyncio.fixture
    async def export_manager_with_data(self, test_session):
        """Create ExportManager with sample data in database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ExportManager(test_session, temp_dir)
            
            # Add sample data to database
            sample_data = [
                ScrapedDataORM(
                    id=str(uuid4()),
                    job_id="job-1",
                    url="https://example.com/page1",
                    content_type="html",
                    content={"title": "Test Page 1", "text": "Content 1"},
                    raw_html="<html><body>Test 1</body></html>",
                    content_metadata={"language": "en"},
                    confidence_score=0.9,
                    ai_processed=True,
                    ai_metadata={"entities": ["Test"]},
                    data_quality_score=0.85,
                    validation_errors=[],
                    extracted_at=datetime.utcnow(),
                    processed_at=datetime.utcnow(),
                    content_length=100,
                    load_time=1.5
                ),
                ScrapedDataORM(
                    id=str(uuid4()),
                    job_id="job-2",
                    url="https://example.com/page2",
                    content_type="html",
                    content={"title": "Test Page 2", "text": "Content 2"},
                    raw_html="<html><body>Test 2</body></html>",
                    content_metadata={"language": "en"},
                    confidence_score=0.7,
                    ai_processed=True,
                    ai_metadata={"entities": ["Test"]},
                    data_quality_score=0.75,
                    validation_errors=[],
                    extracted_at=datetime.utcnow(),
                    processed_at=datetime.utcnow(),
                    content_length=120,
                    load_time=2.0
                )
            ]
            
            for data in sample_data:
                test_session.add(data)
            await test_session.commit()
            
            yield manager
    
    @pytest.mark.asyncio
    async def test_full_export_workflow_csv(self, export_manager_with_data):
        """Test complete CSV export workflow with real data."""
        export_request = DataExportRequest(
            format="csv",
            min_confidence=0.5,
            include_raw_html=False
        )
        user_id = "test-user-123"
        
        # Create export
        export_id = await export_manager_with_data.create_export(export_request, user_id)
        
        # Wait a bit for background processing
        await asyncio.sleep(0.1)
        
        # Check status
        status = await export_manager_with_data.get_export_status(export_id, user_id)
        assert status is not None
        assert status["format"] == "csv"
    
    @pytest.mark.asyncio
    async def test_streaming_export_with_real_data(self, export_manager_with_data):
        """Test streaming export with real database data."""
        export_request = DataExportRequest(
            format="csv",
            min_confidence=0.0
        )
        
        chunks = []
        async for chunk in export_manager_with_data.stream_export_data(export_request, chunk_size=1):
            chunks.append(chunk)
        
        # Should have 2 chunks (one record each)
        assert len(chunks) == 2
        assert len(chunks[0]) == 1
        assert len(chunks[1]) == 1
        
        # Verify data content
        all_data = chunks[0] + chunks[1]
        urls = [data.url for data in all_data]
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
    
    @pytest.mark.asyncio
    async def test_export_filtering_by_confidence(self, export_manager_with_data):
        """Test export filtering by confidence score."""
        export_request = DataExportRequest(
            format="json",
            min_confidence=0.8  # Should only get the first record (0.9)
        )
        
        chunks = []
        async for chunk in export_manager_with_data.stream_export_data(export_request):
            chunks.append(chunk)
        
        # Should have 1 chunk with 1 record
        assert len(chunks) == 1
        assert len(chunks[0]) == 1
        assert chunks[0][0].confidence_score == 0.9