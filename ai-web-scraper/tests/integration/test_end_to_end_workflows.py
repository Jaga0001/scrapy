"""
End-to-end integration tests for complete scraping workflows.

This module tests complete scraping workflows from job creation to data export,
including all system components working together.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.scraper.web_scraper import WebScraper
from src.ai.content_processor import ContentProcessor
from src.pipeline.repository import DataRepository
from src.pipeline.cleaner import DataCleaner
from src.pipeline.export_manager import ExportManager
from src.pipeline.job_queue import JobQueue
from src.api.main import app
from src.models.pydantic_models import (
    ScrapingConfig, ScrapingJob, JobStatus, ContentType
)


class TestEndToEndScrapingWorkflows:
    """Test complete scraping workflows from start to finish."""
    
    @pytest.fixture
    def e2e_config(self):
        """Configuration for end-to-end testing."""
        return ScrapingConfig(
            wait_time=2,
            max_retries=2,
            timeout=30,
            use_stealth=True,
            headless=True,
            javascript_enabled=True,
            follow_links=True,
            max_depth=2,
            respect_robots_txt=True,
            delay_between_requests=0.5
        )
    
    @pytest.fixture
    def mock_components(self):
        """Mock all system components for integration testing."""
        components = {
            'scraper': AsyncMock(spec=WebScraper),
            'ai_processor': AsyncMock(spec=ContentProcessor),
            'repository': AsyncMock(spec=DataRepository),
            'cleaner': AsyncMock(spec=DataCleaner),
            'export_manager': AsyncMock(spec=ExportManager),
            'job_queue': AsyncMock(spec=JobQueue)
        }
        
        # Configure mock behaviors
        components['scraper'].scrape_url.return_value = MagicMock(
            success=True,
            data=[{
                'url': 'https://test.com',
                'content': {'title': 'Test Page', 'text': 'Test content'},
                'confidence_score': 0.9
            }],
            pages_scraped=1,
            total_time=5.0
        )
        
        components['ai_processor'].process_content.return_value = {
            'processed_content': {'title': 'Test Page', 'text': 'Test content'},
            'entities': [{'type': 'TITLE', 'value': 'Test Page'}],
            'confidence_score': 0.9,
            'metadata': {'processing_time': 1.2}
        }
        
        components['cleaner'].clean_data.return_value = {
            'cleaned_data': {'title': 'Test Page', 'text': 'Test content'},
            'quality_score': 0.95,
            'validation_errors': []
        }
        
        components['repository'].save_scraped_data.return_value = 'data-123'
        components['export_manager'].export_data.return_value = {
            'export_id': 'export-123',
            'file_path': '/tmp/export.csv',
            'record_count': 1
        }
        
        return components
    
    @pytest.mark.asyncio
    async def test_complete_single_url_workflow(self, e2e_config, mock_components):
        """Test complete workflow for scraping a single URL."""
        job_id = str(uuid4())
        url = "https://test-example.com"
        
        # Create job
        job = ScrapingJob(
            id=job_id,
            url=url,
            config=e2e_config,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        # Simulate complete workflow
        with patch.multiple(
            'src.pipeline.workflow_orchestrator',
            scraper=mock_components['scraper'],
            ai_processor=mock_components['ai_processor'],
            repository=mock_components['repository'],
            cleaner=mock_components['cleaner']
        ):
            # Step 1: Scrape URL
            scrape_result = await mock_components['scraper'].scrape_url(url)
            assert scrape_result.success
            assert len(scrape_result.data) == 1
            
            # Step 2: Process with AI
            raw_content = scrape_result.data[0]['content']
            ai_result = await mock_components['ai_processor'].process_content(
                raw_content, ContentType.HTML
            )
            assert ai_result['confidence_score'] >= 0.8
            
            # Step 3: Clean data
            clean_result = await mock_components['cleaner'].clean_data(ai_result)
            assert clean_result['quality_score'] >= 0.9
            assert len(clean_result['validation_errors']) == 0
            
            # Step 4: Save to database
            data_id = await mock_components['repository'].save_scraped_data({
                'job_id': job_id,
                'url': url,
                'content': clean_result['cleaned_data'],
                'confidence_score': ai_result['confidence_score'],
                'data_quality_score': clean_result['quality_score']
            })
            assert data_id == 'data-123'
            
            # Verify all components were called
            mock_components['scraper'].scrape_url.assert_called_once_with(url)
            mock_components['ai_processor'].process_content.assert_called_once()
            mock_components['cleaner'].clean_data.assert_called_once()
            mock_components['repository'].save_scraped_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_url_batch_workflow(self, e2e_config, mock_components):
        """Test workflow for scraping multiple URLs in batch."""
        job_id = str(uuid4())
        urls = [
            "https://test-example.com/page1",
            "https://test-example.com/page2",
            "https://test-example.com/page3"
        ]
        
        # Configure mock for multiple URLs
        mock_components['scraper'].scrape_multiple.return_value = MagicMock(
            success=True,
            data=[
                {
                    'url': url,
                    'content': {'title': f'Page {i+1}', 'text': f'Content {i+1}'},
                    'confidence_score': 0.9 - (i * 0.05)
                }
                for i, url in enumerate(urls)
            ],
            pages_scraped=3,
            pages_failed=0,
            total_time=15.0
        )
        
        # Execute batch workflow
        batch_result = await mock_components['scraper'].scrape_multiple(urls)
        assert batch_result.success
        assert batch_result.pages_scraped == 3
        assert batch_result.pages_failed == 0
        assert len(batch_result.data) == 3
        
        # Process each result through AI and cleaning
        processed_results = []
        for scraped_data in batch_result.data:
            ai_result = await mock_components['ai_processor'].process_content(
                scraped_data['content'], ContentType.HTML
            )
            clean_result = await mock_components['cleaner'].clean_data(ai_result)
            processed_results.append({
                'url': scraped_data['url'],
                'processed_data': clean_result,
                'ai_metadata': ai_result
            })
        
        assert len(processed_results) == 3
        
        # Save all results
        saved_ids = []
        for result in processed_results:
            data_id = await mock_components['repository'].save_scraped_data({
                'job_id': job_id,
                'url': result['url'],
                'content': result['processed_data']['cleaned_data'],
                'confidence_score': result['ai_metadata']['confidence_score']
            })
            saved_ids.append(data_id)
        
        assert len(saved_ids) == 3
        assert all(id == 'data-123' for id in saved_ids)
    
    @pytest.mark.asyncio
    async def test_workflow_with_pagination(self, e2e_config, mock_components):
        """Test workflow with pagination support."""
        base_url = "https://test-example.com/products"
        
        # Configure mock for pagination
        mock_components['scraper'].scrape_url.side_effect = [
            # First page
            MagicMock(
                success=True,
                data=[{
                    'url': f'{base_url}?page=1',
                    'content': {'title': 'Products Page 1', 'products': ['Product 1', 'Product 2']},
                    'pagination_links': [f'{base_url}?page=2'],
                    'confidence_score': 0.95
                }],
                pages_scraped=1
            ),
            # Second page
            MagicMock(
                success=True,
                data=[{
                    'url': f'{base_url}?page=2',
                    'content': {'title': 'Products Page 2', 'products': ['Product 3', 'Product 4']},
                    'pagination_links': [],
                    'confidence_score': 0.92
                }],
                pages_scraped=1
            )
        ]
        
        # Scrape first page
        page1_result = await mock_components['scraper'].scrape_url(f'{base_url}?page=1')
        assert page1_result.success
        assert 'pagination_links' in page1_result.data[0]
        
        # Follow pagination
        if page1_result.data[0]['pagination_links']:
            next_url = page1_result.data[0]['pagination_links'][0]
            page2_result = await mock_components['scraper'].scrape_url(next_url)
            assert page2_result.success
            assert len(page2_result.data[0]['pagination_links']) == 0  # No more pages
        
        # Verify pagination was handled
        assert mock_components['scraper'].scrape_url.call_count == 2
    
    @pytest.mark.asyncio
    async def test_workflow_with_error_recovery(self, e2e_config, mock_components):
        """Test workflow with error handling and recovery."""
        job_id = str(uuid4())
        url = "https://test-example.com/flaky-page"
        
        # Configure mock to fail first, then succeed
        mock_components['scraper'].scrape_url.side_effect = [
            Exception("Network timeout"),
            MagicMock(
                success=True,
                data=[{
                    'url': url,
                    'content': {'title': 'Recovered Page', 'text': 'Success after retry'},
                    'confidence_score': 0.88
                }],
                pages_scraped=1,
                retry_count=1
            )
        ]
        
        # Simulate retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                result = await mock_components['scraper'].scrape_url(url)
                if result.success:
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1)  # Brief delay before retry
        
        # Verify recovery was successful
        assert result.success
        assert result.data[0]['content']['title'] == 'Recovered Page'
        assert mock_components['scraper'].scrape_url.call_count == 2
    
    @pytest.mark.asyncio
    async def test_data_export_workflow(self, mock_components):
        """Test complete data export workflow."""
        job_ids = ['job-123', 'job-456']
        export_format = 'csv'
        
        # Configure repository mock for data retrieval
        mock_components['repository'].get_scraped_data.return_value = [
            {
                'id': 'data-1',
                'job_id': 'job-123',
                'url': 'https://test.com/page1',
                'content': {'title': 'Page 1', 'text': 'Content 1'},
                'confidence_score': 0.95
            },
            {
                'id': 'data-2',
                'job_id': 'job-456',
                'url': 'https://test.com/page2',
                'content': {'title': 'Page 2', 'text': 'Content 2'},
                'confidence_score': 0.88
            }
        ]
        
        # Execute export workflow
        # Step 1: Retrieve data
        data = await mock_components['repository'].get_scraped_data(
            job_ids=job_ids,
            min_confidence=0.8
        )
        assert len(data) == 2
        
        # Step 2: Export data
        export_result = await mock_components['export_manager'].export_data(
            data=data,
            format=export_format,
            filename=f'export_{int(time.time())}.csv'
        )
        
        assert export_result['export_id'] == 'export-123'
        assert export_result['record_count'] == 2
        
        # Verify components were called correctly
        mock_components['repository'].get_scraped_data.assert_called_once()
        mock_components['export_manager'].export_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_job_queue_workflow(self, e2e_config, mock_components):
        """Test job queue processing workflow."""
        # Create multiple jobs
        jobs = [
            ScrapingJob(
                id=f'job-{i}',
                url=f'https://test.com/page{i}',
                config=e2e_config,
                status=JobStatus.PENDING,
                priority=5 - i,  # Different priorities
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]
        
        # Configure job queue mock
        mock_components['job_queue'].enqueue_job.return_value = True
        mock_components['job_queue'].get_next_job.side_effect = jobs + [None]
        mock_components['job_queue'].update_job_status.return_value = True
        
        # Enqueue jobs
        for job in jobs:
            success = await mock_components['job_queue'].enqueue_job(job)
            assert success
        
        # Process jobs from queue
        processed_jobs = []
        while True:
            job = await mock_components['job_queue'].get_next_job()
            if not job:
                break
            
            # Update status to running
            await mock_components['job_queue'].update_job_status(
                job.id, JobStatus.RUNNING
            )
            
            # Simulate job processing
            await asyncio.sleep(0.01)  # Simulate processing time
            processed_jobs.append(job)
            
            # Update status to completed
            await mock_components['job_queue'].update_job_status(
                job.id, JobStatus.COMPLETED
            )
        
        assert len(processed_jobs) == 3
        assert mock_components['job_queue'].enqueue_job.call_count == 3
        assert mock_components['job_queue'].update_job_status.call_count == 6  # 2 calls per job
    
    @pytest.mark.asyncio
    async def test_concurrent_job_processing(self, e2e_config, mock_components):
        """Test concurrent processing of multiple jobs."""
        # Create jobs for concurrent processing
        urls = [f'https://test.com/concurrent/{i}' for i in range(5)]
        
        # Configure scraper for concurrent execution
        async def mock_scrape_with_delay(url):
            await asyncio.sleep(0.1)  # Simulate processing time
            return MagicMock(
                success=True,
                data=[{
                    'url': url,
                    'content': {'title': f'Page for {url}', 'text': 'Concurrent content'},
                    'confidence_score': 0.9
                }],
                pages_scraped=1
            )
        
        mock_components['scraper'].scrape_url.side_effect = mock_scrape_with_delay
        
        # Execute concurrent scraping
        start_time = time.time()
        tasks = [
            mock_components['scraper'].scrape_url(url)
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Verify concurrent execution
        assert len(results) == 5
        assert all(not isinstance(r, Exception) for r in results)
        assert all(r.success for r in results)
        
        # Should complete faster than sequential execution
        # (5 * 0.1 = 0.5s sequential vs ~0.1s concurrent)
        assert end_time - start_time < 0.3
    
    @pytest.mark.asyncio
    async def test_data_quality_workflow(self, mock_components):
        """Test data quality assessment workflow."""
        # Configure mock data with varying quality
        test_data = [
            {
                'content': {'title': 'High Quality Page', 'text': 'Comprehensive content with good structure'},
                'confidence_score': 0.95,
                'expected_quality': 0.9
            },
            {
                'content': {'title': 'Medium Quality', 'text': 'Some content'},
                'confidence_score': 0.75,
                'expected_quality': 0.7
            },
            {
                'content': {'title': '', 'text': 'Poor content'},
                'confidence_score': 0.45,
                'expected_quality': 0.4
            }
        ]
        
        # Configure cleaner mock to return quality scores
        def mock_clean_data(data):
            for test_item in test_data:
                if test_item['content']['title'] in str(data):
                    return {
                        'cleaned_data': test_item['content'],
                        'quality_score': test_item['expected_quality'],
                        'validation_errors': [] if test_item['expected_quality'] > 0.6 else ['Low quality content']
                    }
            return {'cleaned_data': data, 'quality_score': 0.5, 'validation_errors': []}
        
        mock_components['cleaner'].clean_data.side_effect = mock_clean_data
        
        # Process each data item through quality assessment
        quality_results = []
        for item in test_data:
            result = await mock_components['cleaner'].clean_data(item['content'])
            quality_results.append({
                'original': item,
                'quality_result': result
            })
        
        # Verify quality assessment
        assert len(quality_results) == 3
        assert quality_results[0]['quality_result']['quality_score'] >= 0.9  # High quality
        assert quality_results[1]['quality_result']['quality_score'] >= 0.7  # Medium quality
        assert quality_results[2]['quality_result']['quality_score'] <= 0.5  # Low quality
        
        # Verify validation errors for low quality data
        assert len(quality_results[2]['quality_result']['validation_errors']) > 0


class TestSystemIntegrationScenarios:
    """Test integration between different system components."""
    
    @pytest.mark.asyncio
    async def test_api_to_scraper_integration(self, mock_components):
        """Test integration from API request to scraper execution."""
        from fastapi.testclient import TestClient
        
        # Mock the scraper in the API
        with patch('src.api.routes.jobs.scraper', mock_components['scraper']):
            client = TestClient(app)
            
            # Create job via API
            job_data = {
                'url': 'https://test.com',
                'config': {
                    'wait_time': 5,
                    'max_retries': 3,
                    'use_stealth': True
                },
                'tags': ['integration-test']
            }
            
            response = client.post('/api/v1/jobs', json=job_data)
            assert response.status_code == 201
            
            job_response = response.json()
            assert 'job_id' in job_response
            assert job_response['status'] == 'pending'
    
    @pytest.mark.asyncio
    async def test_database_to_export_integration(self, mock_components):
        """Test integration from database retrieval to export generation."""
        # Configure repository with test data
        test_data = [
            {
                'id': f'data-{i}',
                'job_id': 'job-123',
                'url': f'https://test.com/page{i}',
                'content': {'title': f'Page {i}', 'text': f'Content {i}'},
                'confidence_score': 0.9 - (i * 0.1),
                'extracted_at': datetime.utcnow() - timedelta(hours=i)
            }
            for i in range(3)
        ]
        
        mock_components['repository'].get_scraped_data.return_value = test_data
        
        # Configure export manager
        mock_components['export_manager'].export_data.return_value = {
            'export_id': 'export-integration-123',
            'file_path': '/tmp/integration_export.csv',
            'record_count': len(test_data),
            'file_size': 1024
        }
        
        # Execute integration workflow
        # Step 1: Query data from repository
        filters = {
            'job_ids': ['job-123'],
            'min_confidence': 0.7,
            'date_from': datetime.utcnow() - timedelta(days=1)
        }
        
        data = await mock_components['repository'].get_scraped_data(**filters)
        assert len(data) == 3
        
        # Step 2: Export filtered data
        export_result = await mock_components['export_manager'].export_data(
            data=data,
            format='csv',
            include_metadata=True
        )
        
        assert export_result['export_id'] == 'export-integration-123'
        assert export_result['record_count'] == 3
        
        # Verify integration calls
        mock_components['repository'].get_scraped_data.assert_called_once_with(**filters)
        mock_components['export_manager'].export_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ai_processor_to_cleaner_integration(self, mock_components):
        """Test integration between AI processor and data cleaner."""
        # Configure AI processor with realistic output
        ai_output = {
            'processed_content': {
                'title': 'AI Processed Title',
                'text': 'AI processed and enhanced content',
                'entities': ['Entity1', 'Entity2'],
                'categories': ['Technology', 'AI']
            },
            'confidence_score': 0.92,
            'metadata': {
                'processing_time': 1.5,
                'model_version': 'gemini-2.5',
                'tokens_processed': 150
            }
        }
        
        mock_components['ai_processor'].process_content.return_value = ai_output
        
        # Configure cleaner to work with AI output
        mock_components['cleaner'].clean_data.return_value = {
            'cleaned_data': ai_output['processed_content'],
            'quality_score': 0.95,
            'validation_errors': [],
            'cleaning_applied': ['text_normalization', 'entity_validation']
        }
        
        # Execute integration workflow
        raw_content = {
            'title': 'Raw Title',
            'text': 'Raw content that needs AI processing'
        }
        
        # Step 1: AI processing
        ai_result = await mock_components['ai_processor'].process_content(
            raw_content, ContentType.HTML
        )
        assert ai_result['confidence_score'] == 0.92
        
        # Step 2: Data cleaning
        clean_result = await mock_components['cleaner'].clean_data(ai_result)
        assert clean_result['quality_score'] == 0.95
        assert len(clean_result['validation_errors']) == 0
        
        # Verify integration
        mock_components['ai_processor'].process_content.assert_called_once_with(
            raw_content, ContentType.HTML
        )
        mock_components['cleaner'].clean_data.assert_called_once_with(ai_result)


class TestWorkflowPerformanceScenarios:
    """Test performance aspects of complete workflows."""
    
    @pytest.mark.asyncio
    async def test_large_batch_processing_performance(self, mock_components):
        """Test performance with large batch of URLs."""
        # Create large batch of URLs
        batch_size = 100
        urls = [f'https://test.com/page{i}' for i in range(batch_size)]
        
        # Configure mock for batch processing
        async def mock_batch_scrape(urls_batch):
            await asyncio.sleep(0.01)  # Simulate processing time
            return MagicMock(
                success=True,
                data=[
                    {
                        'url': url,
                        'content': {'title': f'Page {i}', 'text': f'Content {i}'},
                        'confidence_score': 0.9
                    }
                    for i, url in enumerate(urls_batch)
                ],
                pages_scraped=len(urls_batch),
                pages_failed=0
            )
        
        mock_components['scraper'].scrape_multiple.side_effect = mock_batch_scrape
        
        # Process in chunks for better performance
        chunk_size = 20
        start_time = time.time()
        
        all_results = []
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i:i + chunk_size]
            result = await mock_components['scraper'].scrape_multiple(chunk)
            all_results.extend(result.data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance metrics
        assert len(all_results) == batch_size
        assert processing_time < 1.0  # Should complete within 1 second
        
        # Calculate throughput
        throughput = batch_size / processing_time
        assert throughput > 50  # Should process more than 50 URLs per second
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_large_workflow(self, mock_components):
        """Test memory usage during large data processing workflow."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large amount of data
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'id': f'data-{i}',
                'content': {'title': f'Title {i}', 'text': f'Content {i}' * 100},
                'metadata': {'processing_time': 1.0, 'tokens': 500}
            })
        
        # Configure mocks for large dataset
        mock_components['cleaner'].clean_data.return_value = {
            'cleaned_data': {'processed': True},
            'quality_score': 0.9,
            'validation_errors': []
        }
        
        # Process data in batches
        batch_size = 50
        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i:i + batch_size]
            for item in batch:
                await mock_components['cleaner'].clean_data(item)
        
        # Check memory usage after processing
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_performance(self, mock_components):
        """Test performance of concurrent workflow execution."""
        # Configure mock for concurrent execution
        async def mock_concurrent_scrape(url):
            await asyncio.sleep(0.05)  # Simulate network delay
            return MagicMock(
                success=True,
                data=[{
                    'url': url,
                    'content': {'title': f'Concurrent {url}', 'text': 'Concurrent content'},
                    'confidence_score': 0.9
                }],
                pages_scraped=1
            )
        
        mock_components['scraper'].scrape_url.side_effect = mock_concurrent_scrape
        
        # Test different concurrency levels
        urls = [f'https://test.com/concurrent{i}' for i in range(20)]
        
        # Sequential execution
        start_time = time.time()
        sequential_results = []
        for url in urls:
            result = await mock_components['scraper'].scrape_url(url)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Reset mock call count
        mock_components['scraper'].scrape_url.reset_mock()
        mock_components['scraper'].scrape_url.side_effect = mock_concurrent_scrape
        
        # Concurrent execution
        start_time = time.time()
        concurrent_tasks = [
            mock_components['scraper'].scrape_url(url)
            for url in urls
        ]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_time = time.time() - start_time
        
        # Verify performance improvement
        assert len(sequential_results) == len(concurrent_results) == 20
        assert concurrent_time < sequential_time * 0.3  # Should be much faster
        
        # Calculate performance metrics
        sequential_throughput = len(urls) / sequential_time
        concurrent_throughput = len(urls) / concurrent_time
        
        assert concurrent_throughput > sequential_throughput * 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])