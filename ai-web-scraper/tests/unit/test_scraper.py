"""
Unit tests for the scraping engine components.

Tests the WebScraper, SeleniumDriver, ContentExtractor, and configuration
management with mock dependencies and security validation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.scraper.web_scraper import WebScraper
from src.scraper.selenium_driver import SeleniumDriver
from src.scraper.content_extractor import ContentExtractor
from src.models.pydantic_models import ScrapingConfig, ScrapingResult, ScrapedData


class TestWebScraper:
    """Test cases for WebScraper class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock scraping configuration."""
        return ScrapingConfig(
            wait_time=5,
            max_retries=3,
            timeout=30,
            use_stealth=True,
            headless=True,
            delay_between_requests=1.0,
            respect_robots_txt=True
        )
    
    @pytest.fixture
    def web_scraper(self, mock_config):
        """Create a WebScraper instance with mock configuration."""
        return WebScraper(config=mock_config)
    
    
    @pytest.mark.asyncio
    async def test_scrape_url_success(self, web_scraper):
        """Test successful URL scraping."""
        test_url = "https://example.com"
        mock_html = "<html><head><title>Test</title></head><body><p>Test content</p></body></html>"
        
        # Mock the driver and extractor
        with patch.object(web_scraper, '_initialize_session') as mock_init, \
             patch.object(web_scraper, '_check_robots_txt', return_value=True) as mock_robots, \
             patch.object(web_scraper, '_scrape_single_page') as mock_scrape:
            
            # Setup mock scraped data
            mock_scraped_data = ScrapedData(
                job_id="test_job",
                url=test_url,
                content={"text": "Test content", "title": "Test"},
                confidence_score=0.9
            )
            mock_scrape.return_value = mock_scraped_data
            
            # Execute scraping
            result = await web_scraper.scrape_url(test_url)
            
            # Assertions
            assert isinstance(result, ScrapingResult)
            assert result.success is True
            assert len(result.data) == 1
            assert result.data[0].url == test_url
            assert result.pages_scraped == 1
            assert result.pages_failed == 0
            
            # Verify method calls
            mock_init.assert_called_once()
            mock_robots.assert_called_once_with(test_url)
            mock_scrape.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_url_with_retries(self, web_scraper):
        """Test URL scraping with retry logic."""
        test_url = "https://example.com"
        
        with patch.object(web_scraper, '_initialize_session'), \
             patch.object(web_scraper, '_check_robots_txt', return_value=True), \
             patch.object(web_scraper, '_scrape_single_page', side_effect=[None, None, ScrapedData(
                 job_id="test_job",
                 url=test_url,
                 content={"text": "Test content"},
                 confidence_score=0.8
             )]) as mock_scrape:
            
            result = await web_scraper.scrape_url(test_url)
            
            assert result.success is True
            assert mock_scrape.call_count == 1  # Only called once in scrape_url, retries handled in _scrape_single_page
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_urls(self, web_scraper):
        """Test scraping multiple URLs."""
        test_urls = ["https://example1.com", "https://example2.com"]
        
        with patch.object(web_scraper, '_initialize_session'), \
             patch.object(web_scraper, '_check_robots_txt', return_value=True), \
             patch.object(web_scraper, '_scrape_single_page') as mock_scrape:
            
            # Mock successful scraping for both URLs
            mock_scrape.side_effect = [
                ScrapedData(job_id="test_job", url=test_urls[0], content={"text": "Content 1"}, confidence_score=0.9),
                ScrapedData(job_id="test_job", url=test_urls[1], content={"text": "Content 2"}, confidence_score=0.8)
            ]
            
            result = await web_scraper.scrape_multiple(test_urls)
            
            assert result.success is True
            assert len(result.data) == 2
            assert result.pages_scraped == 2
            assert result.pages_failed == 0
            assert abs(result.average_confidence - 0.85) < 0.01  # Allow for floating point precision
    
    @pytest.mark.asyncio
    async def test_robots_txt_blocking(self, web_scraper):
        """Test that robots.txt blocking works correctly."""
        test_url = "https://example.com"
        
        with patch.object(web_scraper, '_initialize_session'), \
             patch.object(web_scraper, '_check_robots_txt', return_value=False):
            
            result = await web_scraper.scrape_url(test_url)
            
            assert result.success is False
            assert "robots.txt" in result.error_message
            assert result.pages_scraped == 0
            assert result.pages_failed == 1


class TestSeleniumDriver:
    """Test cases for SeleniumDriver class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock scraping configuration."""
        return ScrapingConfig(
            headless=True,
            use_stealth=True,
            timeout=30
        )
    
    @pytest.fixture
    def selenium_driver(self, mock_config):
        """Create a SeleniumDriver instance."""
        return SeleniumDriver(config=mock_config)
    
    @pytest.mark.asyncio
    async def test_initialize_chrome_driver(self, selenium_driver):
        """Test Chrome driver initialization."""
        with patch('src.scraper.selenium_driver.webdriver.Chrome') as mock_chrome, \
             patch.object(selenium_driver, '_create_chrome_driver') as mock_create:
            
            mock_driver = Mock()
            mock_create.return_value = mock_driver
            
            await selenium_driver.initialize()
            
            assert selenium_driver._is_initialized is True
            assert selenium_driver.driver is mock_driver
    
    @pytest.mark.asyncio
    async def test_navigate_to_url(self, selenium_driver):
        """Test URL navigation."""
        test_url = "https://example.com"
        
        # Mock driver
        mock_driver = Mock()
        mock_driver.get = Mock()
        mock_driver.current_url = test_url
        mock_driver.title = "Test Page"
        mock_driver.page_source = "<html><body>Test</body></html>"
        
        selenium_driver.driver = mock_driver
        selenium_driver._is_initialized = True
        selenium_driver.wait = Mock()
        
        with patch.object(selenium_driver, '_wait_for_page_ready'):
            metadata = await selenium_driver.navigate_to(test_url)
            
            assert metadata['url'] == test_url
            assert metadata['final_url'] == test_url
            assert metadata['title'] == "Test Page"
            assert 'load_time' in metadata
            mock_driver.get.assert_called_once_with(test_url)
    
    @pytest.mark.asyncio
    async def test_wait_for_element(self, selenium_driver):
        """Test waiting for elements."""
        mock_driver = Mock()
        mock_element = Mock()
        
        selenium_driver.driver = mock_driver
        selenium_driver._is_initialized = True
        selenium_driver.wait = Mock()
        selenium_driver.wait.until = Mock(return_value=mock_element)
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_element)
            
            element = await selenium_driver.wait_for_element('.test-selector')
            
            assert element is mock_element
    
    @pytest.mark.asyncio
    async def test_cleanup(self, selenium_driver):
        """Test driver cleanup."""
        mock_driver = Mock()
        selenium_driver.driver = mock_driver
        selenium_driver._is_initialized = True
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock()
            
            await selenium_driver.cleanup()
            
            assert selenium_driver.driver is None
            assert selenium_driver._is_initialized is False


class TestContentExtractor:
    """Test cases for ContentExtractor class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock scraping configuration."""
        return ScrapingConfig(
            extract_links=True,
            extract_images=True,
            custom_selectors={'price': '.price', 'title': 'h1'}
        )
    
    @pytest.fixture
    def content_extractor(self, mock_config):
        """Create a ContentExtractor instance."""
        return ContentExtractor(config=mock_config)
    
    def test_extract_from_html_basic(self, content_extractor):
        """Test basic HTML content extraction."""
        html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <h1>Main Title</h1>
                <p>This is a test paragraph.</p>
                <a href="https://example.com">Test Link</a>
                <img src="test.jpg" alt="Test Image">
            </body>
        </html>
        """
        
        result = content_extractor.extract_from_html(html, "https://test.com")
        
        # Check structure
        assert 'metadata' in result
        assert 'content' in result
        assert 'structure' in result
        assert 'links' in result
        assert 'images' in result
        assert 'custom' in result
        
        # Check metadata
        assert result['metadata']['title'] == "Test Page"
        assert result['metadata']['description'] == "Test description"
        
        # Check content
        assert "Main Title" in result['content']['text']
        assert "test paragraph" in result['content']['text']
        assert len(result['content']['headings']) == 1
        assert result['content']['headings'][0]['text'] == "Main Title"
        assert result['content']['headings'][0]['level'] == 1
    
    def test_extract_metadata(self, content_extractor):
        """Test metadata extraction from HTML."""
        html = """
        <html lang="en">
            <head>
                <title>Test Page Title</title>
                <meta name="description" content="Page description">
                <meta name="keywords" content="test, page, html">
                <meta name="author" content="Test Author">
                <meta property="og:title" content="OG Title">
                <meta property="og:description" content="OG Description">
                <meta name="twitter:card" content="summary">
                <link rel="canonical" href="https://example.com/canonical">
                <script type="application/ld+json">
                    {"@type": "WebPage", "name": "Test Page"}
                </script>
            </head>
            <body></body>
        </html>
        """
        
        result = content_extractor.extract_from_html(html, "https://test.com")
        metadata = result['metadata']
        
        assert metadata['title'] == "Test Page Title"
        assert metadata['description'] == "Page description"
        assert metadata['keywords'] == ["test", "page", "html"]
        assert metadata['author'] == "Test Author"
        assert metadata['language'] == "en"
        assert metadata['canonical_url'] == "https://example.com/canonical"
        assert metadata['og_data']['title'] == "OG Title"
        assert metadata['og_data']['description'] == "OG Description"
        assert metadata['twitter_data']['card'] == "summary"
        assert len(metadata['schema_data']) == 1
    
    def test_extract_custom_selectors(self, content_extractor):
        """Test custom selector extraction."""
        html = """
        <html>
            <body>
                <h1>Product Title</h1>
                <div class="price">$19.99</div>
                <div class="price">$24.99</div>
            </body>
        </html>
        """
        
        result = content_extractor.extract_from_html(html, "https://test.com")
        custom = result['custom']
        
        assert custom['title'] == "Product Title"
        assert custom['price'] == ["$19.99", "$24.99"]  # Multiple elements return list
    
    def test_extract_links_and_images(self, content_extractor):
        """Test link and image extraction."""
        html = """
        <html>
            <body>
                <a href="https://external.com" title="External Link">External</a>
                <a href="/internal" title="Internal Link">Internal</a>
                <a href="#anchor">Anchor</a>
                <img src="image1.jpg" alt="Image 1" width="100" height="200">
                <img src="/relative/image2.png" alt="Image 2">
            </body>
        </html>
        """
        
        result = content_extractor.extract_from_html(html, "https://test.com")
        
        # Check links (should exclude anchor links)
        links = result['links']
        assert len(links) == 2
        assert links[0]['url'] == "https://external.com"
        assert links[0]['is_external'] is True
        assert links[1]['url'] == "https://test.com/internal"
        assert links[1]['is_external'] is False
        
        # Check images
        images = result['images']
        assert len(images) == 2
        assert images[0]['url'] == "https://test.com/image1.jpg"
        assert images[0]['alt'] == "Image 1"
        assert images[0]['width'] == "100"
        assert images[0]['height'] == "200"
    
    def test_structure_analysis(self, content_extractor):
        """Test page structure analysis."""
        html = """
        <html>
            <body>
                <nav>Navigation</nav>
                <main>
                    <h1>Title</h1>
                    <p>Paragraph 1</p>
                    <p>Paragraph 2</p>
                    <ul><li>Item 1</li><li>Item 2</li></ul>
                    <table><tr><td>Cell</td></tr></table>
                </main>
                <aside>Sidebar</aside>
                <footer>Footer</footer>
                <form><input type="text"></form>
            </body>
        </html>
        """
        
        result = content_extractor.extract_from_html(html, "https://test.com")
        structure = result['structure']
        
        assert structure['has_navigation'] is True
        assert structure['has_sidebar'] is True
        assert structure['has_footer'] is True
        assert structure['form_count'] == 1
        assert structure['element_counts']['p'] == 2
        assert structure['element_counts']['h1'] == 1
    
    def test_clean_soup_removes_unwanted_elements(self, content_extractor):
        """Test that unwanted elements are removed during cleaning."""
        html = """
        <html>
            <head>
                <script>alert('test');</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <p>Good content</p>
                <div class="advertisement">Ad content</div>
                <div style="display: none">Hidden content</div>
                <!-- This is a comment -->
                <noscript>No script content</noscript>
            </body>
        </html>
        """
        
        result = content_extractor.extract_from_html(html, "https://test.com")
        text = result['content']['text']
        
        # Should contain good content
        assert "Good content" in text
        
        # Should not contain unwanted content
        assert "alert('test')" not in text
        assert "color: red" not in text
        assert "Ad content" not in text
        assert "Hidden content" not in text
        assert "This is a comment" not in text
        assert "No script content" not in text