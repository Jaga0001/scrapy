"""
Pytest configuration and fixtures for AI Web Scraper tests.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4

from src.models.pydantic_models import (
    ScrapingConfig, ScrapingJob, ScrapedData, ScrapingResult,
    JobStatus, ContentType
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_scraping_config() -> ScrapingConfig:
    """Create a sample scraping configuration for testing."""
    return ScrapingConfig(
        name="Test Job",
        max_pages=5,
        wait_time=2,
        max_retries=2,
        timeout=30,
        use_stealth=True,
        headless=True,
        extract_images=True,
        extract_links=True,
        follow_links=False,
        max_depth=2,
        delay_between_requests=1.0,
        respect_robots_txt=True,
        custom_selectors={
            "title": "h1",
            "description": ".description",
            "price": ".price"
        },
        exclude_selectors=[".advertisement", ".cookie-banner"],
        javascript_enabled=True
    )


@pytest.fixture
def sample_scraping_job(sample_scraping_config) -> ScrapingJob:
    """Create a sample scraping job for testing."""
    return ScrapingJob(
        id=str(uuid4()),
        url="https://example.com",
        config=sample_scraping_config,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow(),
        total_pages=5,
        pages_completed=0,
        pages_failed=0,
        user_id="test_user",
        tags=["test", "example"],
        priority=5
    )


@pytest.fixture
def sample_scraped_data() -> ScrapedData:
    """Create sample scraped data for testing."""
    return ScrapedData(
        id=str(uuid4()),
        job_id=str(uuid4()),
        url="https://example.com/page1",
        content={
            "title": "Sample Page Title",
            "text": "This is sample content from a web page. It contains multiple sentences and paragraphs.",
            "headings": [
                {"level": 1, "text": "Main Heading", "id": "main", "class": ["title"]},
                {"level": 2, "text": "Sub Heading", "id": "sub", "class": ["subtitle"]}
            ],
            "paragraphs": [
                "First paragraph with some content.",
                "Second paragraph with more detailed information."
            ],
            "lists": [
                {
                    "type": "ul",
                    "items": ["Item 1", "Item 2", "Item 3"]
                }
            ],
            "tables": []
        },
        raw_html="<html><head><title>Sample Page Title</title></head><body><h1>Main Heading</h1><p>Sample content</p></body></html>",
        content_type=ContentType.HTML,
        content_metadata={
            "load_time": 1.5,
            "page_size": 1024,
            "response_code": 200
        },
        confidence_score=0.85,
        ai_processed=True,
        ai_metadata={
            "summary": "Sample page about testing",
            "topics": ["testing", "web scraping"],
            "quality_score": 0.8
        },
        data_quality_score=0.9,
        validation_errors=[],
        extracted_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
        content_length=150,
        load_time=1.5
    )


@pytest.fixture
def sample_scraping_result(sample_scraped_data) -> ScrapingResult:
    """Create a sample scraping result for testing."""
    return ScrapingResult(
        job_id=str(uuid4()),
        success=True,
        data=[sample_scraped_data],
        total_time=5.2,
        pages_scraped=1,
        pages_failed=0,
        average_confidence=0.85,
        data_quality_summary={
            "total_urls": 1,
            "successful_urls": 1,
            "failed_urls": 0,
            "success_rate": 1.0
        }
    )


@pytest.fixture
def sample_html_content() -> str:
    """Sample HTML content for testing content extraction."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Sample page for testing web scraping">
        <meta name="keywords" content="test, scraping, sample">
        <meta property="og:title" content="Sample Test Page">
        <meta property="og:description" content="This is a test page">
        <title>Sample Test Page</title>
    </head>
    <body>
        <header>
            <nav class="navigation">
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/about">About</a></li>
                </ul>
            </nav>
        </header>
        
        <main>
            <article>
                <h1 id="main-title">Main Article Title</h1>
                <p class="intro">This is the introduction paragraph with important information.</p>
                
                <h2>Section 1</h2>
                <p>First section content with <a href="/link1">internal link</a>.</p>
                
                <h2>Section 2</h2>
                <p>Second section with more detailed content.</p>
                
                <ul>
                    <li>List item 1</li>
                    <li>List item 2</li>
                    <li>List item 3</li>
                </ul>
                
                <table>
                    <thead>
                        <tr>
                            <th>Column 1</th>
                            <th>Column 2</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Data 1</td>
                            <td>Data 2</td>
                        </tr>
                    </tbody>
                </table>
            </article>
        </main>
        
        <aside class="sidebar">
            <h3>Related Links</h3>
            <ul>
                <li><a href="/related1">Related Article 1</a></li>
                <li><a href="/related2">Related Article 2</a></li>
            </ul>
        </aside>
        
        <footer>
            <p>&copy; 2024 Test Site</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def invalid_html_content() -> str:
    """Invalid HTML content for testing error handling."""
    return """
    <html>
    <head>
        <title>Broken Page
    </head>
    <body>
        <h1>Missing closing tags
        <p>Malformed content
        <div>
            <span>Unclosed elements
    </body>
    """


@pytest.fixture
def api_test_data() -> Dict[str, Any]:
    """Sample data for API testing."""
    return {
        "job_create": {
            "name": "Test API Job",
            "url": "https://httpbin.org/html",
            "max_pages": 3
        },
        "job_response": {
            "id": str(uuid4()),
            "name": "Test API Job",
            "url": "https://httpbin.org/html",
            "max_pages": 3,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "total_pages": 3,
            "pages_completed": 0,
            "config": {}
        },
        "scraped_data_response": [
            {
                "job_id": str(uuid4()),
                "job_name": "Test Job",
                "url": "https://httpbin.org/html",
                "title": "Sample Title",
                "content": "Sample content...",
                "scraped_at": datetime.utcnow().isoformat(),
                "scraped_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "confidence_score": 0.8,
                "ai_processed": True
            }
        ]
    }


@pytest.fixture
def export_test_data() -> Dict[str, Any]:
    """Sample data for export functionality testing."""
    return {
        "csv_fields": [
            "job_id", "job_name", "url", "title", "content", 
            "scraped_at", "confidence_score", "ai_processed"
        ],
        "json_structure": {
            "metadata": {"export_date": datetime.utcnow().isoformat()},
            "data": []
        },
        "sample_export_request": {
            "format": "csv",
            "job_ids": [str(uuid4())],
            "date_from": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "date_to": datetime.utcnow().isoformat(),
            "min_confidence": 0.5,
            "include_raw_html": False,
            "fields": ["title", "content", "url"]
        }
    }