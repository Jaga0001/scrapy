"""
Pytest configuration and fixtures for repository tests.

This module provides test configuration and shared fixtures for testing
the data repository with a test database.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from config.settings import Settings
from src.models.database_models import Base


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestSettings(Settings):
    """Test-specific settings that override the main settings."""
    
    app_name: str = "AI Web Scraper Test"
    debug: bool = True
    log_level: str = "DEBUG"
    
    # Test database settings
    database_url: str = TEST_DATABASE_URL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "test_webscraper"
    db_user: str = "test"
    db_password: str = "test"
    db_pool_size: int = 1
    db_max_overflow: int = 0
    db_echo: bool = False
    
    # Test Redis settings
    redis_url: str = "redis://localhost:6379/15"  # Use different DB for tests
    
    # Test API settings
    api_host: str = "127.0.0.1"
    api_port: int = 8001
    secret_key: str = "TEST_ONLY_SECRET_KEY_DO_NOT_USE_IN_PRODUCTION_a1b2c3d4e5f6g7h8i9j0"
    environment: str = "test"
    
    # Test scraping settings
    max_concurrent_jobs: int = 2
    default_timeout: int = 10
    max_retries: int = 1
    
    # Test dashboard settings
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8502
    
    # Test AI settings
    gemini_api_key: str = "test-api-key"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_settings():
    """Provide test settings."""
    return TestSettings()


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch, test_settings):
    """Mock the settings for all tests."""
    # Mock the get_settings function to return test settings
    import config.settings
    monkeypatch.setattr(config.settings, "get_settings", lambda: test_settings)
    
    # Also mock the global _settings variable
    monkeypatch.setattr(config.settings, "_settings", test_settings)


@pytest_asyncio.fixture
async def clean_database(test_session):
    """Ensure a clean database state for each test."""
    # Clean up any existing data
    await test_session.execute("DELETE FROM job_logs")
    await test_session.execute("DELETE FROM scraped_data")
    await test_session.execute("DELETE FROM scraping_jobs")
    await test_session.execute("DELETE FROM system_metrics")
    await test_session.execute("DELETE FROM data_exports")
    await test_session.execute("DELETE FROM user_sessions")
    await test_session.commit()
    
    yield test_session
    
    # Clean up after test
    await test_session.rollback()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add asyncio marker to async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # Add integration marker to integration tests
        if "integration" in item.name or "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to performance tests
        if "performance" in item.name or "benchmark" in item.name:
            item.add_marker(pytest.mark.performance)


# Test data helpers
def create_test_job_data():
    """Create test job data for use in tests."""
    from datetime import datetime
    from uuid import uuid4
    from src.models.pydantic_models import JobStatus, ScrapingConfig
    
    return {
        "id": str(uuid4()),
        "url": "https://test-example.com",
        "config": ScrapingConfig(
            wait_time=3,
            max_retries=2,
            use_stealth=True,
            extract_images=False,
            follow_links=False,
            custom_selectors={"title": "h1"}
        ),
        "status": JobStatus.PENDING,
        "created_at": datetime.utcnow(),
        "total_pages": 5,
        "pages_completed": 0,
        "pages_failed": 0,
        "user_id": "test-user-123",
        "tags": ["test"],
        "priority": 5
    }


def create_test_scraped_data():
    """Create test scraped data for use in tests."""
    from datetime import datetime
    from uuid import uuid4
    from src.models.pydantic_models import ContentType
    
    return {
        "id": str(uuid4()),
        "job_id": str(uuid4()),
        "url": "https://test-example.com/page1",
        "content": {"title": "Test Page", "text": "Test content"},
        "raw_html": "<html><body><h1>Test Page</h1><p>Test content</p></body></html>",
        "content_type": ContentType.HTML,
        "content_metadata": {"language": "en"},
        "confidence_score": 0.9,
        "ai_processed": True,
        "ai_metadata": {"entities": ["Test"]},
        "data_quality_score": 0.85,
        "validation_errors": [],
        "extracted_at": datetime.utcnow(),
        "processed_at": datetime.utcnow(),
        "content_length": 500,
        "load_time": 1.5
    }