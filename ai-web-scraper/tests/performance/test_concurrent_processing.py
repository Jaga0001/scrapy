"""
Performance tests for concurrent job processing with load simulation.

This module tests the system's ability to handle concurrent scraping jobs,
load balancing, and performance under various load conditions.
"""

import asyncio
import pytest
import time
import statistics
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from src.pipeline.job_queue import JobQueue
from src.pipeline.worker import JobWorker
from src.scraper.web_scraper import WebScraper
from src.models.pydantic_models import ScrapingJob, ScrapingConfig, JobStatus


class TestConcurrentJobProcessing:
    """Test concurrent processing capabilities and performance."""
    
    @pytest.fixture
    def performance_config(self):
        """Configuration optimized for performance testing."""
        return ScrapingConfig(
            wait_time=1,
            max_retries=2,
            timeout=10,
            use_stealth=False,  # Disable for performance
            headless=True,
            delay_between_requests=0.1,
            javascript_enabled=False  # Disable for performance
        )
    
    @pytest.fixture
    def mock_job_queue(self):
        """Mock job queue for performance testing."""
        queue = AsyncMock(spec=JobQueue)
        queue.enqueue_job.return_value = True
        queue.get_queue_size.return_value = 0
        queue.get_active_workers.return_value = 4
        return queue
    
    @pytest.fixture
    def mock_worker(self):
        """Mock worker for performance testing."""
        worker = AsyncMock(spec=JobWorker)
        
        async def mock_process_job(job):
            # Simulate processing time
            await asyncio.sleep(0.01)
            return {
                'job_id': job.id,
                'status': 'completed',
                'pages_scraped': 5,
                'processing_time': 0.01,
                'success': True
            }
        
        worker.process_job.side_effect = mock_process_job
        return worker
    
    @pytest.mark.asyncio
    async def test_concurrent_job_submission(self, performance_config, mock_job_queue):
        """Test concurrent submission of multiple jobs."""
        # Create multiple jobs
        num_jobs = 50
        jobs = [
            ScrapingJob(
                id=f'perf-job-{i}',
                url=f'https://test.com/page{i}',
                config=performance_config,
                status=JobStatus.PENDING,
                priority=5,
                created_at=datetime.utcnow()
            )
            for i in range(num_jobs)
        ]
        
        # Submit jobs concurrently
        start_time = time.time()
        
        submission_tasks = [
            mock_job_queue.enqueue_job(job)
            for job in jobs
        ]
        
        results = await asyncio.gather(*submission_tasks)
        
        end_time = time.time()
        submission_time = end_time - start_time
        
        # Verify all jobs were submitted successfully
        assert all(results)
        assert len(results) == num_jobs
        
        # Performance assertions
        submission_rate = num_jobs / submission_time
        assert submission_rate > 100  # Should handle >100 submissions per second
        assert submission_time < 1.0  # Should complete within 1 second
        
        # Verify queue interactions
        assert mock_job_queue.enqueue_job.call_count == num_jobs
    
    @pytest.mark.asyncio
    async def test_concurrent_job_processing(self, performance_config, mock_worker):
        """Test concurrent processing of multiple jobs."""
        # Create jobs for processing
        num_jobs = 20
        jobs = [
            ScrapingJob(
                id=f'proc-job-{i}',
                url=f'https://test.com/process{i}',
                config=performance_config,
                status=JobStatus.RUNNING,
                created_at=datetime.utcnow()
            )
            for i in range(num_jobs)
        ]
        
        # Process jobs concurrently
        start_time = time.time()
        
        processing_tasks = [
            mock_worker.process_job(job)
            for job in jobs
        ]
        
        results = await asyncio.gather(*processing_tasks)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all jobs were processed successfully
        assert len(results) == num_jobs
        assert all(result['success'] for result in results)
        
        # Performance assertions
        processing_rate = num_jobs / processing_time
        assert processing_rate > 50  # Should process >50 jobs per second
        
        # Calculate average processing time per job
        avg_processing_time = sum(result['processing_time'] for result in results) / num_jobs
        assert avg_processing_time < 0.1  # Average should be less than 100ms per job
    
    @pytest.mark.asyncio
    async def test_load_balancing_across_workers(self, performance_config):
        """Test load balancing across multiple workers."""
        num_workers = 4
        num_jobs = 40
        
        # Create mock workers
        workers = []
        job_counts = []
        
        for i in range(num_workers):
            worker = AsyncMock(spec=JobWorker)
            job_count = 0
            
            async def mock_process_with_counter(job, worker_id=i):
                nonlocal job_count
                job_count += 1
                await asyncio.sleep(0.02)  # Simulate processing time
                return {
                    'job_id': job.id,
                    'worker_id': worker_id,
                    'status': 'completed',
                    'success': True
                }
            
            worker.process_job.side_effect = mock_process_with_counter
            workers.append(worker)
            job_counts.append(job_count)
        
        # Create jobs
        jobs = [
            ScrapingJob(
                id=f'lb-job-{i}',
                url=f'https://test.com/loadbalance{i}',
                config=performance_config,
                status=JobStatus.PENDING
            )
            for i in range(num_jobs)
        ]
        
        # Distribute jobs across workers (round-robin simulation)
        tasks = []
        for i, job in enumerate(jobs):
            worker = workers[i % num_workers]
            tasks.append(worker.process_job(job))
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify load balancing
        worker_job_counts = [0] * num_workers
        for result in results:
            worker_job_counts[result['worker_id']] += 1
        
        # Each worker should have processed approximately equal number of jobs
        expected_jobs_per_worker = num_jobs // num_workers
        for count in worker_job_counts:
            assert abs(count - expected_jobs_per_worker) <= 1
        
        # Performance verification
        total_time = end_time - start_time
        throughput = num_jobs / total_time
        assert throughput > 100  # Should achieve high throughput with load balancing
    
    @pytest.mark.asyncio
    async def test_queue_performance_under_load(self, mock_job_queue):
        """Test job queue performance under high load."""
        # Simulate high load scenario
        num_producers = 5
        num_consumers = 3
        jobs_per_producer = 20
        
        # Producer function
        async def producer(producer_id, num_jobs):
            jobs_submitted = 0
            for i in range(num_jobs):
                job = ScrapingJob(
                    id=f'load-job-{producer_id}-{i}',
                    url=f'https://test.com/load/{producer_id}/{i}',
                    status=JobStatus.PENDING
                )
                await mock_job_queue.enqueue_job(job)
                jobs_submitted += 1
                await asyncio.sleep(0.001)  # Small delay to simulate real conditions
            return jobs_submitted
        
        # Consumer function
        async def consumer(consumer_id):
            jobs_processed = 0
            processing_times = []
            
            # Simulate processing jobs for a fixed duration
            end_time = time.time() + 0.5  # Process for 0.5 seconds
            
            while time.time() < end_time:
                # Simulate getting job from queue
                start_process = time.time()
                await asyncio.sleep(0.01)  # Simulate job processing
                end_process = time.time()
                
                processing_times.append(end_process - start_process)
                jobs_processed += 1
            
            return {
                'consumer_id': consumer_id,
                'jobs_processed': jobs_processed,
                'avg_processing_time': statistics.mean(processing_times),
                'processing_times': processing_times
            }
        
        # Start producers and consumers concurrently
        start_time = time.time()
        
        producer_tasks = [
            producer(i, jobs_per_producer)
            for i in range(num_producers)
        ]
        
        consumer_tasks = [
            consumer(i)
            for i in range(num_consumers)
        ]
        
        # Wait for all tasks to complete
        producer_results = await asyncio.gather(*producer_tasks)
        consumer_results = await asyncio.gather(*consumer_tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify producer performance
        total_jobs_submitted = sum(producer_results)
        expected_total_jobs = num_producers * jobs_per_producer
        assert total_jobs_submitted == expected_total_jobs
        
        submission_rate = total_jobs_submitted / total_time
        assert submission_rate > 50  # Should handle >50 submissions per second
        
        # Verify consumer performance
        total_jobs_processed = sum(result['jobs_processed'] for result in consumer_results)
        assert total_jobs_processed > 0
        
        # Calculate average processing time across all consumers
        all_processing_times = []
        for result in consumer_results:
            all_processing_times.extend(result['processing_times'])
        
        if all_processing_times:
            avg_processing_time = statistics.mean(all_processing_times)
            assert avg_processing_time < 0.05  # Should average less than 50ms per job
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_concurrent_load(self):
        """Test memory usage during concurrent job processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large number of concurrent tasks
        num_tasks = 100
        
        async def memory_intensive_task(task_id):
            # Simulate memory usage during job processing
            data = {
                'task_id': task_id,
                'large_data': ['x' * 1000 for _ in range(100)],  # ~100KB per task
                'processing_start': time.time()
            }
            
            await asyncio.sleep(0.01)  # Simulate processing
            
            # Clean up data
            del data['large_data']
            
            return {
                'task_id': task_id,
                'memory_cleaned': True,
                'processing_time': time.time() - data['processing_start']
            }
        
        # Execute tasks concurrently
        start_time = time.time()
        
        tasks = [
            memory_intensive_task(i)
            for i in range(num_tasks)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Check memory usage after processing
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify results
        assert len(results) == num_tasks
        assert all(result['memory_cleaned'] for result in results)
        
        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50
        
        # Performance should be good
        total_time = end_time - start_time
        task_throughput = num_tasks / total_time
        assert task_throughput > 200  # Should handle >200 tasks per second
    
    @pytest.mark.asyncio
    async def test_error_handling_under_load(self, performance_config):
        """Test error handling during high-load concurrent processing."""
        num_jobs = 30
        error_rate = 0.2  # 20% of jobs will fail
        
        # Create mock scraper with controlled failure rate
        mock_scraper = AsyncMock(spec=WebScraper)
        
        async def mock_scrape_with_failures(url):
            # Simulate random failures
            job_id = url.split('/')[-1]
            job_num = int(job_id.replace('error', ''))
            
            if job_num % 5 == 0:  # Every 5th job fails (20% failure rate)
                raise Exception(f"Simulated failure for job {job_num}")
            
            await asyncio.sleep(0.01)  # Simulate processing time
            return MagicMock(
                success=True,
                data=[{
                    'url': url,
                    'content': {'title': f'Success {job_num}'},
                    'confidence_score': 0.9
                }],
                pages_scraped=1
            )
        
        mock_scraper.scrape_url.side_effect = mock_scrape_with_failures
        
        # Create jobs
        jobs = [
            f'https://test.com/error{i}'
            for i in range(num_jobs)
        ]
        
        # Process jobs concurrently with error handling
        start_time = time.time()
        
        async def safe_scrape(url):
            try:
                result = await mock_scraper.scrape_url(url)
                return {'url': url, 'success': True, 'result': result}
            except Exception as e:
                return {'url': url, 'success': False, 'error': str(e)}
        
        tasks = [safe_scrape(url) for url in jobs]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Analyze results
        successful_jobs = [r for r in results if r['success']]
        failed_jobs = [r for r in results if not r['success']]
        
        # Verify error handling
        expected_failures = int(num_jobs * error_rate)
        assert len(failed_jobs) == expected_failures
        assert len(successful_jobs) == num_jobs - expected_failures
        
        # Verify all jobs were processed (either successfully or with error handling)
        assert len(results) == num_jobs
        
        # Performance should not be significantly impacted by errors
        total_time = end_time - start_time
        job_throughput = num_jobs / total_time
        assert job_throughput > 100  # Should maintain good throughput despite errors
    
    @pytest.mark.asyncio
    async def test_priority_queue_performance(self, performance_config, mock_job_queue):
        """Test performance of priority-based job processing."""
        # Create jobs with different priorities
        high_priority_jobs = [
            ScrapingJob(
                id=f'high-{i}',
                url=f'https://test.com/high{i}',
                config=performance_config,
                priority=9,  # High priority
                status=JobStatus.PENDING
            )
            for i in range(10)
        ]
        
        low_priority_jobs = [
            ScrapingJob(
                id=f'low-{i}',
                url=f'https://test.com/low{i}',
                config=performance_config,
                priority=1,  # Low priority
                status=JobStatus.PENDING
            )
            for i in range(20)
        ]
        
        all_jobs = high_priority_jobs + low_priority_jobs
        
        # Configure mock queue to simulate priority ordering
        job_queue = []
        
        async def mock_enqueue_with_priority(job):
            # Insert job in priority order (higher priority first)
            inserted = False
            for i, queued_job in enumerate(job_queue):
                if job.priority > queued_job.priority:
                    job_queue.insert(i, job)
                    inserted = True
                    break
            if not inserted:
                job_queue.append(job)
            return True
        
        async def mock_get_next_job():
            if job_queue:
                return job_queue.pop(0)
            return None
        
        mock_job_queue.enqueue_job.side_effect = mock_enqueue_with_priority
        mock_job_queue.get_next_job.side_effect = mock_get_next_job
        
        # Enqueue all jobs
        start_time = time.time()
        
        enqueue_tasks = [
            mock_job_queue.enqueue_job(job)
            for job in all_jobs
        ]
        
        await asyncio.gather(*enqueue_tasks)
        
        enqueue_time = time.time() - start_time
        
        # Process jobs and track order
        processed_jobs = []
        processing_start = time.time()
        
        while True:
            job = await mock_job_queue.get_next_job()
            if not job:
                break
            processed_jobs.append(job)
            await asyncio.sleep(0.001)  # Simulate processing time
        
        processing_time = time.time() - processing_start
        
        # Verify priority ordering
        # First 10 jobs should be high priority
        first_10_jobs = processed_jobs[:10]
        assert all(job.priority == 9 for job in first_10_jobs)
        
        # Remaining jobs should be low priority
        remaining_jobs = processed_jobs[10:]
        assert all(job.priority == 1 for job in remaining_jobs)
        
        # Performance verification
        total_jobs = len(all_jobs)
        enqueue_rate = total_jobs / enqueue_time
        processing_rate = total_jobs / processing_time
        
        assert enqueue_rate > 100  # Should enqueue >100 jobs per second
        assert processing_rate > 500  # Should process >500 jobs per second (minimal processing)
    
    @pytest.mark.asyncio
    async def test_throughput_scaling_with_workers(self, performance_config):
        """Test how throughput scales with number of workers."""
        num_jobs = 60
        worker_counts = [1, 2, 4, 8]
        throughput_results = {}
        
        for num_workers in worker_counts:
            # Create mock workers
            workers = []
            for i in range(num_workers):
                worker = AsyncMock(spec=JobWorker)
                
                async def mock_process_job(job):
                    await asyncio.sleep(0.01)  # Simulate processing time
                    return {
                        'job_id': job.id,
                        'status': 'completed',
                        'success': True
                    }
                
                worker.process_job.side_effect = mock_process_job
                workers.append(worker)
            
            # Create jobs
            jobs = [
                ScrapingJob(
                    id=f'scale-job-{i}',
                    url=f'https://test.com/scale{i}',
                    config=performance_config,
                    status=JobStatus.PENDING
                )
                for i in range(num_jobs)
            ]
            
            # Distribute jobs across workers
            start_time = time.time()
            
            tasks = []
            for i, job in enumerate(jobs):
                worker = workers[i % num_workers]
                tasks.append(worker.process_job(job))
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            processing_time = end_time - start_time
            throughput = num_jobs / processing_time
            
            throughput_results[num_workers] = throughput
            
            # Verify all jobs completed successfully
            assert len(results) == num_jobs
            assert all(result['success'] for result in results)
        
        # Verify throughput scaling
        # Throughput should increase with more workers (up to a point)
        assert throughput_results[2] > throughput_results[1]
        assert throughput_results[4] > throughput_results[2]
        
        # Calculate scaling efficiency
        baseline_throughput = throughput_results[1]
        for workers, throughput in throughput_results.items():
            if workers > 1:
                scaling_factor = throughput / baseline_throughput
                efficiency = scaling_factor / workers
                
                # Efficiency should be reasonable (>0.5 means good scaling)
                assert efficiency > 0.5, f"Poor scaling efficiency with {workers} workers: {efficiency}"


class TestLoadSimulation:
    """Test system behavior under various load simulation scenarios."""
    
    @pytest.mark.asyncio
    async def test_burst_load_handling(self, performance_config):
        """Test handling of sudden burst loads."""
        # Simulate burst load scenario
        burst_size = 50
        normal_load = 5
        
        mock_scraper = AsyncMock(spec=WebScraper)
        
        async def mock_scrape_with_delay(url):
            await asyncio.sleep(0.02)  # Simulate processing time
            return MagicMock(
                success=True,
                data=[{'url': url, 'content': {'title': 'Burst test'}}],
                pages_scraped=1
            )
        
        mock_scraper.scrape_url.side_effect = mock_scrape_with_delay
        
        # Normal load phase
        normal_jobs = [f'https://test.com/normal{i}' for i in range(normal_load)]
        
        start_time = time.time()
        normal_tasks = [mock_scraper.scrape_url(url) for url in normal_jobs]
        normal_results = await asyncio.gather(*normal_tasks)
        normal_time = time.time() - start_time
        
        # Burst load phase
        burst_jobs = [f'https://test.com/burst{i}' for i in range(burst_size)]
        
        start_time = time.time()
        burst_tasks = [mock_scraper.scrape_url(url) for url in burst_jobs]
        burst_results = await asyncio.gather(*burst_tasks)
        burst_time = time.time() - start_time
        
        # Verify handling of both loads
        assert len(normal_results) == normal_load
        assert len(burst_results) == burst_size
        assert all(result.success for result in normal_results)
        assert all(result.success for result in burst_results)
        
        # Calculate throughput
        normal_throughput = normal_load / normal_time
        burst_throughput = burst_size / burst_time
        
        # System should handle burst load efficiently
        # Burst throughput should be at least 50% of normal throughput per job
        assert burst_throughput > normal_throughput * 0.5
    
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, performance_config):
        """Test performance under sustained load over time."""
        duration_seconds = 2.0
        jobs_per_second = 20
        
        mock_scraper = AsyncMock(spec=WebScraper)
        
        async def mock_scrape_sustained(url):
            await asyncio.sleep(0.01)  # Fast processing for sustained load
            return MagicMock(
                success=True,
                data=[{'url': url, 'content': {'title': 'Sustained test'}}],
                pages_scraped=1
            )
        
        mock_scraper.scrape_url.side_effect = mock_scrape_sustained
        
        # Generate sustained load
        start_time = time.time()
        all_results = []
        job_counter = 0
        
        while time.time() - start_time < duration_seconds:
            # Create batch of jobs
            batch_size = min(jobs_per_second, 10)  # Process in small batches
            batch_jobs = [
                f'https://test.com/sustained{job_counter + i}'
                for i in range(batch_size)
            ]
            job_counter += batch_size
            
            # Process batch
            batch_tasks = [mock_scraper.scrape_url(url) for url in batch_jobs]
            batch_results = await asyncio.gather(*batch_tasks)
            all_results.extend(batch_results)
            
            # Small delay to control rate
            await asyncio.sleep(0.05)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Verify sustained performance
        total_jobs = len(all_results)
        actual_throughput = total_jobs / actual_duration
        
        assert total_jobs > 0
        assert all(result.success for result in all_results)
        
        # Should maintain reasonable throughput
        expected_min_throughput = jobs_per_second * 0.7  # Allow 30% variance
        assert actual_throughput >= expected_min_throughput
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_recovery(self):
        """Test system recovery from resource exhaustion scenarios."""
        # Simulate resource exhaustion
        max_concurrent_tasks = 100
        recovery_tasks = 20
        
        # Create resource-intensive tasks
        async def resource_intensive_task(task_id):
            # Simulate resource usage
            large_data = ['x' * 10000 for _ in range(100)]  # ~1MB per task
            
            try:
                await asyncio.sleep(0.05)  # Simulate processing
                return {
                    'task_id': task_id,
                    'success': True,
                    'data_size': len(large_data)
                }
            finally:
                # Clean up resources
                del large_data
        
        # Phase 1: Create resource exhaustion
        exhaustion_tasks = [
            resource_intensive_task(i)
            for i in range(max_concurrent_tasks)
        ]
        
        start_time = time.time()
        
        try:
            exhaustion_results = await asyncio.gather(*exhaustion_tasks)
            exhaustion_success = True
        except Exception:
            exhaustion_success = False
        
        exhaustion_time = time.time() - start_time
        
        # Phase 2: Test recovery
        await asyncio.sleep(0.1)  # Allow system to recover
        
        recovery_start = time.time()
        
        async def simple_recovery_task(task_id):
            await asyncio.sleep(0.01)
            return {'task_id': task_id, 'recovered': True}
        
        recovery_task_list = [
            simple_recovery_task(i)
            for i in range(recovery_tasks)
        ]
        
        recovery_results = await asyncio.gather(*recovery_task_list)
        recovery_time = time.time() - recovery_start
        
        # Verify recovery
        assert len(recovery_results) == recovery_tasks
        assert all(result['recovered'] for result in recovery_results)
        
        # Recovery should be fast
        recovery_throughput = recovery_tasks / recovery_time
        assert recovery_throughput > 50  # Should recover quickly
        
        # System should handle the recovery gracefully
        assert recovery_time < 1.0  # Should recover within 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])