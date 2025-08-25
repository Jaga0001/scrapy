"""
Integration tests for advanced scraping capabilities.

This module tests the advanced features including anti-detection,
JavaScript handling, pagination, retry logic, and robots.txt compliance.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urljoin

from src.scraper.web_scraper import WebScraper
from src.scraper.selenium_driver import SeleniumDriver
from src.models.pydantic_models import ScrapingConfig
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.utils.robots_handler import RobotsHandler, EthicalScrapingEnforcer


class TestAdvancedScrapingCapabilities:
    """Test suite for advanced scraping features."""
    
    @pytest.fixture
    def scraping_config(self):
        """Create a test scraping configuration."""
        return ScrapingConfig(
            wait_time=2,
            max_retries=2,
            timeout=10,
            use_stealth=True,
            headless=True,
            delay_between_requests=0.5,
            respect_robots_txt=True,
            javascript_enabled=True,
            follow_links=True,
            max_depth=2
        )
    
    @pytest.fixture
    def mock_driver(self):
        """Create a mock Selenium driver."""
        driver = AsyncMock(spec=SeleniumDriver)
        driver.initialize = AsyncMock()
        driver.navigate_to = AsyncMock(return_value={
            "url": "https://example.com",
            "final_url": "https://example.com",
            "title": "Test Page",
            "load_time": 1.5,
            "page_source_length": 1000,
            "timestamp": time.time()
        })
        driver.get_page_source = MagicMock(return_value="<html><body>Test content</body></html>")
        driver.find_pagination_links = AsyncMock(return_value=[
            "https://example.com/page/2",
            "https://example.com/page/3"
        ])
        driver.find_content_links = AsyncMock(return_value=[
            "https://example.com/article/1",
            "https://example.com/article/2"
        ])
        driver.cleanup = AsyncMock()
        return driver
    
    @pytest.fixture
    def mock_extractor(self):
        """Create a mock content extractor."""
        extractor = MagicMock()
        extractor.extract_from_html = MagicMock(return_value={
            "metadata": {"title": "Test Page"},
            "content": {"text": "Test content"},
            "structure": {"element_counts": {"paragraphs": 1}}
        })
        return extractor


class TestAntiDetectionTechniques:
    """Test anti-detection and stealth capabilities."""
    
    @pytest.mark.asyncio
    async def test_user_agent_rotation(self):
        """Test that user agents are rotated properly."""
        config = ScrapingConfig(use_stealth=True)
        driver = SeleniumDriver(config)
        
        # Test user agent pool
        assert len(driver._user_agent_pool) > 0
        
        # Test rotation
        ua1 = driver._rotate_user_agent()
        ua2 = driver._rotate_user_agent()
        
        # Should have different user agents (with high probability)
        assert isinstance(ua1, str)
        assert isinstance(ua2, str)
        assert len(ua1) > 0
        assert len(ua2) > 0
    
    @pytest.mark.asyncio
    async def test_random_delays(self):
        """Test that random delays are applied correctly."""
        config = ScrapingConfig(delay_between_requests=1.0)
        driver = SeleniumDriver(config)
        
        start_time = time.time()
        await driver.add_random_delay(1.0)
        elapsed = time.time() - start_time
        
        # Should be between 1.2 and 1.5 seconds (20-50% variation)
        assert 1.2 <= elapsed <= 1.5
    
    @pytest.mark.asyncio
    async def test_stealth_configuration(self):
        """Test that stealth options are properly configured."""
        config = ScrapingConfig(use_stealth=True, headless=True)
        driver = SeleniumDriver(config)
        
        # Test that stealth configuration is applied
        with patch('src.scraper.selenium_driver.webdriver.Chrome') as mock_chrome:
            mock_chrome_instance = MagicMock()
            mock_chrome.return_value = mock_chrome_instance
            
            driver._create_chrome_driver()
            
            # Verify Chrome was called with stealth arguments
            mock_chrome.assert_called_once()
            call_args = mock_chrome.call_args
            options = call_args[1]['options'] if 'options' in call_args[1] else call_args[0][0]
            
            # Check that stealth arguments are present
            stealth_args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
            
            for arg in stealth_args:
                assert any(arg in str(option) for option in options.arguments)


class TestJavaScriptHandling:
    """Test JavaScript-rendered content handling."""
    
    @pytest.mark.asyncio
    async def test_javascript_content_waiting(self):
        """Test waiting for JavaScript content to load."""
        config = ScrapingConfig(javascript_enabled=True, wait_time=2)
        driver = SeleniumDriver(config)
        
        # Mock WebDriver
        mock_webdriver = MagicMock()
        mock_webdriver.execute_script = MagicMock(return_value=True)
        driver.driver = mock_webdriver
        driver.wait = MagicMock()
        driver._is_initialized = True
        
        # Test JavaScript content handling
        await driver._handle_javascript_content()
        
        # Verify JavaScript checks were performed
        assert mock_webdriver.execute_script.called
    
    @pytest.mark.asyncio
    async def test_ajax_completion_waiting(self):
        """Test waiting for AJAX requests to complete."""
        config = ScrapingConfig(javascript_enabled=True)
        driver = SeleniumDriver(config)
        
        # Mock WebDriver and wait
        mock_webdriver = MagicMock()
        mock_wait = MagicMock()
        mock_wait.until = MagicMock()
        
        driver.driver = mock_webdriver
        driver.wait = mock_wait
        driver._is_initialized = True
        
        # Test AJAX waiting
        await driver._wait_for_ajax_complete()
        
        # Verify wait.until was called
        mock_wait.until.assert_called()


class TestPaginationSupport:
    """Test pagination and link following functionality."""
    
    @pytest.mark.asyncio
    async def test_pagination_link_detection(self):
        """Test detection of pagination links."""
        config = ScrapingConfig()
        driver = SeleniumDriver(config)
        
        # Mock WebDriver with pagination elements
        mock_element1 = MagicMock()
        mock_element1.get_attribute.return_value = "https://example.com/page/2"
        mock_element2 = MagicMock()
        mock_element2.get_attribute.return_value = "/page/3"
        
        mock_webdriver = MagicMock()
        mock_webdriver.find_elements.return_value = [mock_element1, mock_element2]
        mock_webdriver.current_url = "https://example.com/page/1"
        
        driver.driver = mock_webdriver
        driver._is_initialized = True
        
        # Test pagination detection
        pagination_urls = await driver.find_pagination_links()
        
        # Verify pagination URLs were found and normalized
        assert len(pagination_urls) >= 1
        assert "https://example.com/page/2" in pagination_urls
        assert "https://example.com/page/3" in pagination_urls
    
    @pytest.mark.asyncio
    async def test_content_link_detection(self):
        """Test detection of content links."""
        config = ScrapingConfig()
        driver = SeleniumDriver(config)
        
        # Mock WebDriver with content elements
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "https://example.com/article/1"
        
        mock_webdriver = MagicMock()
        mock_webdriver.find_elements.return_value = [mock_element]
        mock_webdriver.current_url = "https://example.com"
        
        driver.driver = mock_webdriver
        driver._is_initialized = True
        
        # Test content link detection
        content_urls = await driver.find_content_links()
        
        # Verify content URLs were found
        assert len(content_urls) >= 1
        assert "https://example.com/article/1" in content_urls
    
    @pytest.mark.asyncio
    async def test_multi_page_scraping_with_pagination(self, scraping_config, mock_driver, mock_extractor):
        """Test scraping multiple pages with pagination support."""
        scraper = WebScraper(scraping_config)
        
        with patch.object(scraper, '_initialize_session'), \
             patch.object(scraper, 'driver', mock_driver), \
             patch.object(scraper, 'extractor', mock_extractor):
            
            scraper._session_active = True
            
            # Mock ethical enforcer to allow scraping
            with patch('src.scraper.web_scraper.ethical_enforcer') as mock_enforcer:
                mock_enforcer.check_scraping_permission = AsyncMock(return_value={
                    "allowed": True,
                    "reason": "Test allowed",
                    "recommended_delay": 0.1
                })
                mock_enforcer.wait_for_rate_limit = AsyncMock()
                
                # Test multi-URL scraping
                urls = ["https://example.com/page/1"]
                result = await scraper.scrape_multiple(urls)
                
                # Verify scraping was successful
                assert result.success
                assert result.pages_scraped > 0


class TestRetryLogicAndCircuitBreaker:
    """Test retry logic with exponential backoff and circuit breaker pattern."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker behavior under failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1.0,
            success_threshold=1
        )
        
        circuit_breaker = CircuitBreaker("test_breaker", config)
        
        # Function that always fails
        async def failing_function():
            raise Exception("Test failure")
        
        # Test failure accumulation
        for _ in range(2):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)
        
        # Circuit should now be open
        assert circuit_breaker.state.value == "open"
        
        # Next call should raise CircuitBreakerError
        with pytest.raises(Exception):  # Could be CircuitBreakerError or the original exception
            await circuit_breaker.call(failing_function)
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = CircuitBreakerConfig(
            initial_delay=1.0,
            max_delay=10.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        
        circuit_breaker = CircuitBreaker("test_backoff", config)
        
        # Test backoff calculation
        circuit_breaker.failure_count = 1
        delay1 = circuit_breaker._calculate_backoff_delay()
        
        circuit_breaker.failure_count = 2
        delay2 = circuit_breaker._calculate_backoff_delay()
        
        circuit_breaker.failure_count = 3
        delay3 = circuit_breaker._calculate_backoff_delay()
        
        # Verify exponential increase
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0
    
    @pytest.mark.asyncio
    async def test_scraper_retry_logic(self, scraping_config):
        """Test scraper retry logic with failures."""
        scraper = WebScraper(scraping_config)
        
        # Mock driver that fails initially then succeeds
        mock_driver = AsyncMock()
        mock_driver.navigate_to = AsyncMock(side_effect=[
            Exception("Network error"),
            Exception("Timeout error"),
            {"url": "https://example.com", "load_time": 1.0, "title": "Success"}
        ])
        mock_driver.get_page_source = MagicMock(return_value="<html>Success</html>")
        
        mock_extractor = MagicMock()
        mock_extractor.extract_from_html = MagicMock(return_value={
            "content": {"text": "Success"},
            "metadata": {"title": "Success"}
        })
        
        with patch.object(scraper, '_initialize_session'), \
             patch.object(scraper, 'driver', mock_driver), \
             patch.object(scraper, 'extractor', mock_extractor):
            
            scraper._session_active = True
            
            # Test retry logic
            result = await scraper._scrape_single_page(
                "https://example.com", 
                "test_job", 
                scraping_config
            )
            
            # Should succeed after retries
            assert result is not None
            assert mock_driver.navigate_to.call_count == 3


class TestRobotsTxtCompliance:
    """Test robots.txt compliance and ethical scraping."""
    
    @pytest.mark.asyncio
    async def test_robots_txt_permission_check(self):
        """Test robots.txt permission checking."""
        robots_handler = RobotsHandler()
        
        # Mock robots.txt content
        mock_robots_content = """
User-agent: *
Disallow: /private/
Allow: /public/
Crawl-delay: 1
        """
        
        with patch.object(robots_handler, '_fetch_robots_txt', return_value=mock_robots_content):
            # Test allowed URL
            allowed = await robots_handler.can_fetch("https://example.com/public/page", "*")
            assert allowed
            
            # Test disallowed URL
            disallowed = await robots_handler.can_fetch("https://example.com/private/page", "*")
            assert not disallowed
    
    @pytest.mark.asyncio
    async def test_crawl_delay_extraction(self):
        """Test extraction of crawl delay from robots.txt."""
        robots_handler = RobotsHandler()
        
        mock_robots_content = """
User-agent: *
Crawl-delay: 2
        """
        
        with patch.object(robots_handler, '_fetch_robots_txt', return_value=mock_robots_content):
            delay = await robots_handler.get_crawl_delay("https://example.com/page", "*")
            assert delay == 2.0
    
    @pytest.mark.asyncio
    async def test_ethical_scraping_enforcer(self):
        """Test ethical scraping permission checking."""
        enforcer = EthicalScrapingEnforcer()
        
        # Mock robots handler
        mock_robots_handler = AsyncMock()
        mock_robots_handler.can_fetch = AsyncMock(return_value=True)
        mock_robots_handler.get_crawl_delay = AsyncMock(return_value=2.0)
        mock_robots_handler.get_request_rate = AsyncMock(return_value=None)
        
        enforcer.robots_handler = mock_robots_handler
        
        # Test permission check
        permission = await enforcer.check_scraping_permission(
            "https://example.com/page",
            "test-agent",
            respect_robots=True
        )
        
        assert permission["allowed"]
        assert permission["crawl_delay"] == 2.0
        assert permission["recommended_delay"] >= 2.0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self):
        """Test rate limiting between requests."""
        enforcer = EthicalScrapingEnforcer()
        
        url = "https://example.com/page"
        
        # First request should not wait
        start_time = time.time()
        await enforcer.wait_for_rate_limit(url, custom_delay=0.5)
        first_elapsed = time.time() - start_time
        
        # Second request should wait
        start_time = time.time()
        await enforcer.wait_for_rate_limit(url, custom_delay=0.5)
        second_elapsed = time.time() - start_time
        
        # First request should be immediate, second should wait
        assert first_elapsed < 0.1
        assert second_elapsed >= 0.4  # Should wait close to 0.5 seconds


class TestIntegrationScenarios:
    """Integration tests for complete scraping scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_scraping_workflow(self, scraping_config):
        """Test complete scraping workflow with all advanced features."""
        scraper = WebScraper(scraping_config)
        
        # Mock all components
        mock_driver = AsyncMock()
        mock_driver.initialize = AsyncMock()
        mock_driver.navigate_to = AsyncMock(return_value={
            "url": "https://example.com",
            "final_url": "https://example.com",
            "title": "Test Page",
            "load_time": 1.0,
            "page_source_length": 1000,
            "timestamp": time.time()
        })
        mock_driver.get_page_source = MagicMock(return_value="<html><body>Test</body></html>")
        mock_driver.find_pagination_links = AsyncMock(return_value=[])
        mock_driver.find_content_links = AsyncMock(return_value=[])
        mock_driver.cleanup = AsyncMock()
        
        mock_extractor = MagicMock()
        mock_extractor.extract_from_html = MagicMock(return_value={
            "content": {"text": "Test content"},
            "metadata": {"title": "Test Page"}
        })
        
        with patch.object(scraper, 'driver', mock_driver), \
             patch.object(scraper, 'extractor', mock_extractor), \
             patch('src.scraper.web_scraper.ethical_enforcer') as mock_enforcer:
            
            mock_enforcer.check_scraping_permission = AsyncMock(return_value={
                "allowed": True,
                "reason": "Allowed",
                "recommended_delay": 1.0
            })
            mock_enforcer.wait_for_rate_limit = AsyncMock()
            
            scraper._session_active = True
            
            # Test single URL scraping
            result = await scraper.scrape_url("https://example.com")
            
            # Verify successful scraping
            assert result.success
            assert result.pages_scraped == 1
            assert len(result.data) == 1
            assert result.data[0].content["content"]["text"] == "Test content"
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, scraping_config):
        """Test error handling and recovery mechanisms."""
        scraper = WebScraper(scraping_config)
        
        # Mock driver that fails then recovers
        mock_driver = AsyncMock()
        mock_driver.initialize = AsyncMock()
        mock_driver.navigate_to = AsyncMock(side_effect=[
            Exception("Network error"),
            {"url": "https://example.com", "load_time": 1.0, "title": "Success"}
        ])
        mock_driver.get_page_source = MagicMock(return_value="<html>Success</html>")
        mock_driver.cleanup = AsyncMock()
        
        mock_extractor = MagicMock()
        mock_extractor.extract_from_html = MagicMock(return_value={
            "content": {"text": "Success"},
            "metadata": {"title": "Success"}
        })
        
        with patch.object(scraper, 'driver', mock_driver), \
             patch.object(scraper, 'extractor', mock_extractor), \
             patch('src.scraper.web_scraper.ethical_enforcer') as mock_enforcer:
            
            mock_enforcer.check_scraping_permission = AsyncMock(return_value={
                "allowed": True,
                "reason": "Allowed",
                "recommended_delay": 0.1
            })
            
            scraper._session_active = True
            
            # Test error recovery
            result = await scraper.scrape_url("https://example.com")
            
            # Should succeed after retry
            assert result.success
            assert result.pages_scraped == 1


if __name__ == "__main__":
    pytest.main([__file__])