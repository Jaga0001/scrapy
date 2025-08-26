"""
Mock services and test doubles for comprehensive testing.

This module provides mock implementations of external services and
system components for isolated testing.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.models.pydantic_models import (
    ScrapingJob, ScrapedData, ScrapingConfig, JobStatus, ContentType
)


class MockWebDriver:
    """Mock Selenium WebDriver for testing."""
    
    def __init__(self, fail_rate: float = 0.0):
        self.fail_rate = fail_rate
        self.current_url = ""
        self.page_source = ""
        self.title = ""
        self._call_count = 0
        
    def get(self, url: str):
        """Mock navigation to URL."""
        self._call_count += 1
        
        if self._should_fail():
            raise Exception(f"Mock WebDriver failure for {url}")
        
        self.current_url = url
        self.page_source = self._generate_mock_html(url)
        self.title = f"Mock Page for {url}"
        
    def find_elements(self, by, value):
        """Mock element finding."""
        if "pagination" in value:
            return [
                MockWebElement(f"{self.current_url}/page/2"),
                MockWebElement(f"{self.current_url}/page/3")
            ]
        elif "link" in value:
            return [
                MockWebElement(f"{self.current_url}/article/1"),
                MockWebElement(f"{self.current_url}/article/2")
            ]
        return []
    
    def execute_script(self, script: str):
        """Mock JavaScript execution."""
        if "return document.readyState" in script:
            return "complete"
        elif "return jQuery.active" in script:
            return 0
        return True
    
    def quit(self):
        """Mock driver cleanup."""
        pass
    
    def _should_fail(self) -> bool:
        """Determine if this call should fail based on fail_rate."""
        import random
        return random.random() < self.fail_rate
    
    def _generate_mock_html(self, url: str) -> str:
        """Generate mock HTML content."""
        return f"""
        <html>
            <head>
                <title>Mock Page for {url}</title>
            </head>
            <body>
                <h1>Test Page</h1>
                <div class="content">
                    <p>This is mock content for {url}</p>
                    <div class="price">$99.99</div>
                    <div class="rating">4.5 stars</div>
                </div>
                <nav class="pagination">
                    <a href="{url}/page/2">Next</a>
                </nav>
            </body>
        </html>
        """


class MockWebElement:
    """Mock Selenium WebElement."""
    
    def __init__(self, href: str):
        self.href = href
    
    def get_attribute(self, name: str) -> str:
        if name == "href":
            return self.href
        return ""


class MockGeminiAPI:
    """Mock Gemini AI API for testing."""
    
    def __init__(self, response_delay: float = 0.1, fail_rate: float = 0.0):
        self.response_delay = response_delay
        self.fail_rate = fail_rate
        self._call_count = 0
    
    async def process_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """Mock AI content processing."""
        self._call_count += 1
        
        if self._should_fail():
            raise Exception("Mock Gemini API failure")
        
        await asyncio.sleep(self.response_delay)
        
        return {
            "processed_content": {
                "title": self._extract_title(content),
                "text": self._extract_text(content),
                "entities": self._extract_entities(content),
                "categories": ["technology", "web"]
            },
            "confidence_score": 0.92,
            "metadata": {
                "processing_time": self.response_delay,
                "model_version": "gemini-2.5-mock",
                "tokens_processed": len(content.split()),
                "api_call_count": self._call_count
            }
        }
    
    def _should_fail(self) -> bool:
        """Determine if this call should fail."""
        import random
        return random.random() < self.fail_rate
    
    def _extract_title(self, content: str) -> str:
        """Extract mock title from content."""
        if "<title>" in content:
            start = content.find("<title>") + 7
            end = content.find("</title>")
            return content[start:end] if end > start else "Mock Title"
        return "Mock Title"
    
    def _extract_text(self, content: str) -> str:
        """Extract mock text from content."""
        if "<p>" in content:
            start = content.find("<p>") + 3
            end = content.find("</p>")
            return content[start:end] if end > start else "Mock text content"
        return "Mock text content"
    
    def _extract_entities(self, content: str) -> List[Dict[str, Any]]:
        """Extract mock entities from content."""
        entities = []
        
        if "$" in content:
            entities.append({
                "type": "PRICE",
                "value": "$99.99",
                "confidence": 0.95
            })
        
        if "star" in content.lower():
            entities.append({
                "type": "RATING",
                "value": "4.5",
                "confidence": 0.90
            })
        
        return entities


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.scraped_data: Dict[str, Dict] = {}
        self.system_metrics: List[Dict] = []
        self._connection_count = 0
    
    async def connect(self):
        """Mock database connection."""
        self._connection_count += 1
        await asyncio.sleep(0.01)  # Simulate connection time
    
    async def disconnect(self):
        """Mock database disconnection."""
        self._connection_count = max(0, self._connection_count - 1)
        await asyncio.sleep(0.01)
    
    async def save_job(self, job_data: Dict) -> str:
        """Mock job saving."""
        job_id = job_data.get('id', str(uuid4()))
        self.jobs[job_id] = {
            **job_data,
            'saved_at': datetime.utcnow()
        }
        return job_id
    
    async def get_job(self, job_id: str) -> Optional[Dict]:
        """Mock job retrieval."""
        return self.jobs.get(job_id)
    
    async def update_job_status(self, job_id: str, status: JobStatus) -> bool:
        """Mock job status update."""
        if job_id in self.jobs:
            self.jobs[job_id]['status'] = status
            self.jobs[job_id]['updated_at'] = datetime.utcnow()
            return True
        return False
    
    async def save_scraped_data(self, data: Dict) -> str:
        """Mock scraped data saving."""
        data_id = data.get('id', str(uuid4()))
        self.scraped_data[data_id] = {
            **data,
            'saved_at': datetime.utcnow()
        }
        return data_id
    
    async def get_scraped_data(
        self,
        job_ids: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> List[Dict]:
        """Mock scraped data retrieval."""
        results = []
        
        for data_id, data in self.scraped_data.items():
            # Apply filters
            if job_ids and data.get('job_id') not in job_ids:
                continue
            
            if data.get('confidence_score', 0) < min_confidence:
                continue
            
            results.append(data)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def save_system_metric(self, metric_data: Dict):
        """Mock system metric saving."""
        metric_data['recorded_at'] = datetime.utcnow()
        self.system_metrics.append(metric_data)
    
    async def get_system_metrics(
        self,
        metric_names: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Mock system metrics retrieval."""
        results = []
        
        for metric in self.system_metrics:
            if metric.get('metric_name') in metric_names:
                recorded_at = metric.get('recorded_at')
                if start_time <= recorded_at <= end_time:
                    results.append(metric)
        
        return results
    
    def clear_all_data(self):
        """Clear all mock data."""
        self.jobs.clear()
        self.scraped_data.clear()
        self.system_metrics.clear()


class MockRedis:
    """Mock Redis for testing."""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.queues: Dict[str, List] = {}
        self._connection_count = 0
    
    async def connect(self):
        """Mock Redis connection."""
        self._connection_count += 1
        await asyncio.sleep(0.005)  # Simulate connection time
    
    async def disconnect(self):
        """Mock Redis disconnection."""
        self._connection_count = max(0, self._connection_count - 1)
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        """Mock Redis SET operation."""
        self.data[key] = {
            'value': value,
            'expires_at': datetime.utcnow() + timedelta(seconds=ex) if ex else None,
            'set_at': datetime.utcnow()
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Mock Redis GET operation."""
        if key not in self.data:
            return None
        
        entry = self.data[key]
        
        # Check expiration
        if entry['expires_at'] and datetime.utcnow() > entry['expires_at']:
            del self.data[key]
            return None
        
        return entry['value']
    
    async def lpush(self, queue_name: str, *values):
        """Mock Redis LPUSH operation."""
        if queue_name not in self.queues:
            self.queues[queue_name] = []
        
        for value in reversed(values):
            self.queues[queue_name].insert(0, value)
    
    async def rpop(self, queue_name: str) -> Optional[Any]:
        """Mock Redis RPOP operation."""
        if queue_name not in self.queues or not self.queues[queue_name]:
            return None
        
        return self.queues[queue_name].pop()
    
    async def llen(self, queue_name: str) -> int:
        """Mock Redis LLEN operation."""
        return len(self.queues.get(queue_name, []))
    
    def clear_all_data(self):
        """Clear all mock data."""
        self.data.clear()
        self.queues.clear()


class MockFileSystem:
    """Mock file system for testing."""
    
    def __init__(self):
        self.files: Dict[str, bytes] = {}
        self.directories: set = set()
    
    async def write_file(self, path: str, content: bytes):
        """Mock file writing."""
        # Create directory if needed
        directory = '/'.join(path.split('/')[:-1])
        if directory:
            self.directories.add(directory)
        
        self.files[path] = content
    
    async def read_file(self, path: str) -> Optional[bytes]:
        """Mock file reading."""
        return self.files.get(path)
    
    async def delete_file(self, path: str) -> bool:
        """Mock file deletion."""
        if path in self.files:
            del self.files[path]
            return True
        return False
    
    async def list_files(self, directory: str) -> List[str]:
        """Mock directory listing."""
        files = []
        for path in self.files.keys():
            if path.startswith(directory + '/'):
                relative_path = path[len(directory) + 1:]
                if '/' not in relative_path:  # Only direct children
                    files.append(relative_path)
        return files
    
    def clear_all_files(self):
        """Clear all mock files."""
        self.files.clear()
        self.directories.clear()


class MockEmailService:
    """Mock email service for testing."""
    
    def __init__(self):
        self.sent_emails: List[Dict] = []
        self.fail_rate = 0.0
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """Mock email sending."""
        if self._should_fail():
            raise Exception("Mock email service failure")
        
        email = {
            'to': to,
            'subject': subject,
            'body': body,
            'html_body': html_body,
            'sent_at': datetime.utcnow()
        }
        
        self.sent_emails.append(email)
        return True
    
    def _should_fail(self) -> bool:
        """Determine if this call should fail."""
        import random
        return random.random() < self.fail_rate
    
    def get_sent_emails(self) -> List[Dict]:
        """Get all sent emails."""
        return self.sent_emails.copy()
    
    def clear_sent_emails(self):
        """Clear sent emails history."""
        self.sent_emails.clear()


class MockSystemMonitor:
    """Mock system monitoring for testing."""
    
    def __init__(self):
        self.cpu_usage = 45.0
        self.memory_usage = 68.5
        self.disk_usage = 32.1
        self.network_io = {'bytes_sent': 1024000, 'bytes_recv': 2048000}
    
    def get_cpu_usage(self) -> float:
        """Mock CPU usage."""
        # Simulate varying CPU usage
        import random
        self.cpu_usage += random.uniform(-5, 5)
        self.cpu_usage = max(0, min(100, self.cpu_usage))
        return self.cpu_usage
    
    def get_memory_usage(self) -> float:
        """Mock memory usage."""
        import random
        self.memory_usage += random.uniform(-2, 2)
        self.memory_usage = max(0, min(100, self.memory_usage))
        return self.memory_usage
    
    def get_disk_usage(self) -> float:
        """Mock disk usage."""
        return self.disk_usage
    
    def get_network_io(self) -> Dict[str, int]:
        """Mock network I/O statistics."""
        import random
        self.network_io['bytes_sent'] += random.randint(1000, 10000)
        self.network_io['bytes_recv'] += random.randint(2000, 20000)
        return self.network_io.copy()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Mock system information."""
        return {
            'cpu_count': 8,
            'memory_total': 16 * 1024 * 1024 * 1024,  # 16GB
            'disk_total': 500 * 1024 * 1024 * 1024,   # 500GB
            'platform': 'mock-system',
            'python_version': '3.12.0'
        }


class MockServiceFactory:
    """Factory for creating mock services with consistent configuration."""
    
    @staticmethod
    def create_mock_scraper(fail_rate: float = 0.0) -> AsyncMock:
        """Create mock web scraper."""
        scraper = AsyncMock()
        
        async def mock_scrape_url(url: str):
            if MockServiceFactory._should_fail(fail_rate):
                raise Exception(f"Mock scraper failure for {url}")
            
            await asyncio.sleep(0.01)  # Simulate processing time
            
            return MagicMock(
                success=True,
                data=[{
                    'url': url,
                    'content': {
                        'title': f'Mock Title for {url}',
                        'text': f'Mock content for {url}',
                        'metadata': {'scraped_at': datetime.utcnow().isoformat()}
                    },
                    'confidence_score': 0.9
                }],
                pages_scraped=1,
                pages_failed=0,
                total_time=0.01
            )
        
        scraper.scrape_url.side_effect = mock_scrape_url
        return scraper
    
    @staticmethod
    def create_mock_ai_processor(fail_rate: float = 0.0) -> AsyncMock:
        """Create mock AI processor."""
        processor = AsyncMock()
        
        async def mock_process_content(content: str, content_type: ContentType):
            if MockServiceFactory._should_fail(fail_rate):
                raise Exception("Mock AI processor failure")
            
            await asyncio.sleep(0.05)  # Simulate AI processing time
            
            return {
                'processed_content': content,
                'entities': [
                    {'type': 'TITLE', 'value': 'Mock Title', 'confidence': 0.95}
                ],
                'confidence_score': 0.92,
                'metadata': {
                    'processing_time': 0.05,
                    'model_version': 'mock-ai-1.0'
                }
            }
        
        processor.process_content.side_effect = mock_process_content
        return processor
    
    @staticmethod
    def create_mock_repository(fail_rate: float = 0.0) -> AsyncMock:
        """Create mock data repository."""
        repository = AsyncMock()
        mock_db = MockDatabase()
        
        async def mock_save_scraped_data(data: Dict):
            if MockServiceFactory._should_fail(fail_rate):
                raise Exception("Mock repository failure")
            
            return await mock_db.save_scraped_data(data)
        
        async def mock_get_scraped_data(**kwargs):
            return await mock_db.get_scraped_data(**kwargs)
        
        repository.save_scraped_data.side_effect = mock_save_scraped_data
        repository.get_scraped_data.side_effect = mock_get_scraped_data
        repository._mock_db = mock_db  # Expose for test access
        
        return repository
    
    @staticmethod
    def _should_fail(fail_rate: float) -> bool:
        """Determine if operation should fail."""
        import random
        return random.random() < fail_rate


# Test data generators
class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_scraping_jobs(count: int) -> List[ScrapingJob]:
        """Generate test scraping jobs."""
        jobs = []
        
        for i in range(count):
            job = ScrapingJob(
                id=f'test-job-{i}',
                url=f'https://test-site.com/page{i}',
                config=ScrapingConfig(
                    wait_time=5,
                    max_retries=3,
                    use_stealth=True
                ),
                status=JobStatus.PENDING,
                created_at=datetime.utcnow() - timedelta(hours=i),
                priority=5,
                tags=[f'test-tag-{i % 3}']
            )
            jobs.append(job)
        
        return jobs
    
    @staticmethod
    def generate_scraped_data(count: int, job_id: str = "test-job") -> List[ScrapedData]:
        """Generate test scraped data."""
        data_list = []
        
        for i in range(count):
            data = ScrapedData(
                id=f'test-data-{i}',
                job_id=job_id,
                url=f'https://test-site.com/page{i}',
                content={
                    'title': f'Test Page {i}',
                    'text': f'Test content for page {i}',
                    'metadata': {'page_number': i}
                },
                content_type=ContentType.HTML,
                confidence_score=0.9 - (i * 0.01),
                ai_processed=True,
                extracted_at=datetime.utcnow() - timedelta(minutes=i),
                content_length=1000 + (i * 100)
            )
            data_list.append(data)
        
        return data_list
    
    @staticmethod
    def generate_system_metrics(count: int) -> List[Dict[str, Any]]:
        """Generate test system metrics."""
        metrics = []
        
        for i in range(count):
            metric = {
                'metric_name': 'cpu_usage',
                'metric_value': 45.0 + (i % 20),
                'recorded_at': datetime.utcnow() - timedelta(minutes=i),
                'source': 'test-system'
            }
            metrics.append(metric)
        
        return metrics