"""
Selenium WebDriver wrapper with stealth capabilities and advanced features.

This module provides a robust WebDriver wrapper that includes anti-detection
techniques, error handling, and performance optimizations.
"""

import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..models.pydantic_models import ScrapingConfig
from ..utils.logger import get_logger
from .config import config_manager

logger = get_logger(__name__)


class SeleniumDriver:
    """
    Advanced Selenium WebDriver wrapper with stealth capabilities.
    
    Provides anti-detection techniques, robust error handling,
    and performance optimizations for web scraping.
    """
    
    def __init__(self, config: ScrapingConfig):
        """
        Initialize the Selenium driver wrapper.
        
        Args:
            config: Scraping configuration
        """
        self.config = config
        self.driver: Optional[webdriver.Chrome | webdriver.Firefox] = None
        self.wait: Optional[WebDriverWait] = None
        self._is_initialized = False
        self._page_load_start_time = 0.0
        self._current_user_agent = None
        self._user_agent_pool = self._get_user_agent_pool()
        self._viewport_sizes = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720)
        ]
        
    async def initialize(self) -> None:
        """Initialize the WebDriver with stealth configuration."""
        try:
            logger.info("Initializing Selenium WebDriver", extra={
                "headless": self.config.headless,
                "stealth": self.config.use_stealth,
                "timeout": self.config.timeout
            })
            
            # Run driver initialization in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._create_driver)
            
            # Initialize WebDriverWait
            self.wait = WebDriverWait(self.driver, self.config.timeout)
            self._is_initialized = True
            
            logger.info("Selenium WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            await self.cleanup()
            raise
    
    def _create_driver(self) -> None:
        """Create and configure the WebDriver instance."""
        # Try Chrome first, then Firefox as fallback
        try:
            self.driver = self._create_chrome_driver()
        except Exception as chrome_error:
            logger.warning(f"Chrome driver failed, trying Firefox: {chrome_error}")
            try:
                self.driver = self._create_firefox_driver()
            except Exception as firefox_error:
                logger.error(f"Both Chrome and Firefox drivers failed")
                raise WebDriverException(
                    f"Failed to create WebDriver. Chrome: {chrome_error}, Firefox: {firefox_error}"
                )
    
    def _get_user_agent_pool(self) -> List[str]:
        """Get a pool of generic user agents for rotation to prevent fingerprinting."""
        # Use security config to get user agents
        from ..utils.security_config import SecurityConfig
        return SecurityConfig.get_secure_user_agents()
    
    def _rotate_user_agent(self) -> str:
        """Rotate to a new user agent from the pool."""
        if self.config.user_agent:
            return self.config.user_agent
        
        # Select a random user agent different from current one
        available_agents = [ua for ua in self._user_agent_pool if ua != self._current_user_agent]
        if not available_agents:
            available_agents = self._user_agent_pool
        
        self._current_user_agent = random.choice(available_agents)
        return self._current_user_agent
    
    def _create_chrome_driver(self) -> webdriver.Chrome:
        """Create Chrome WebDriver with advanced stealth configuration."""
        options = ChromeOptions()
        
        # Basic options
        if self.config.headless:
            options.add_argument("--headless=new")
        
        # Advanced stealth options
        if self.config.use_stealth:
            # Core stealth arguments
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Additional anti-detection measures
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--disable-ipc-flooding-protection")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-client-side-phishing-detection")
            options.add_argument("--disable-sync")
            options.add_argument("--disable-default-apps")
            options.add_argument("--hide-scrollbars")
            options.add_argument("--mute-audio")
            
            # Memory and performance optimizations
            options.add_argument("--memory-pressure-off")
            options.add_argument("--max_old_space_size=4096")
            
            # Disable unnecessary features
            if not self.config.load_images:
                options.add_argument("--disable-images")
                prefs = {"profile.managed_default_content_settings.images": 2}
                options.add_experimental_option("prefs", prefs)
            
            if not self.config.javascript_enabled:
                options.add_argument("--disable-javascript")
        
        # Performance options
        options.add_argument("--no-first-run")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        # User agent rotation
        user_agent = self._rotate_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        
        # Random viewport size
        viewport = random.choice(self._viewport_sizes)
        options.add_argument(f"--window-size={viewport[0]},{viewport[1]}")
        
        # Proxy configuration
        if self.config.proxy_url:
            options.add_argument(f"--proxy-server={self.config.proxy_url}")
        
        # Create service
        service = None
        if config_manager.settings.chrome_binary_path:
            service = ChromeService(executable_path=config_manager.settings.chrome_binary_path)
        
        # Create driver
        driver = webdriver.Chrome(options=options, service=service)
        
        # Advanced stealth measures post-initialization
        if self.config.use_stealth:
            self._apply_advanced_stealth(driver, user_agent)
        
        return driver
    
    def _apply_advanced_stealth(self, driver: webdriver.Chrome, user_agent: str) -> None:
        """Apply advanced stealth techniques after driver initialization."""
        try:
            # Remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Override user agent via CDP
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent
            })
            
            # Randomize navigator properties
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            # Add realistic timing to mouse movements
            driver.execute_script("""
                const originalAddEventListener = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                    if (type === 'mousedown' || type === 'mouseup' || type === 'click') {
                        const delay = Math.random() * 100 + 50;
                        setTimeout(() => originalAddEventListener.call(this, type, listener, options), delay);
                    } else {
                        originalAddEventListener.call(this, type, listener, options);
                    }
                };
            """)
            
        except Exception as e:
            logger.warning(f"Failed to apply some stealth measures: {str(e)}")
    
    async def simulate_human_behavior(self) -> None:
        """Simulate human-like behavior patterns."""
        if not self.config.use_stealth:
            return
        
        try:
            # Random mouse movements
            actions = ActionChains(self.driver)
            
            # Get viewport size
            viewport_width = self.driver.execute_script("return window.innerWidth")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            
            # Random mouse movement
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, viewport_width)
                y = random.randint(0, viewport_height)
                actions.move_by_offset(x - viewport_width//2, y - viewport_height//2)
                actions.pause(random.uniform(0.1, 0.5))
            
            actions.perform()
            
            # Random scroll
            if random.choice([True, False]):
                scroll_amount = random.randint(100, 500)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            logger.debug(f"Human behavior simulation failed: {str(e)}")
    
    async def add_random_delay(self, base_delay: float = None) -> None:
        """Add randomized delay to mimic human behavior."""
        if base_delay is None:
            base_delay = self.config.delay_between_requests
        
        # Add 20-50% random variation to the delay
        variation = random.uniform(0.2, 0.5)
        actual_delay = base_delay * (1 + variation)
        
        await asyncio.sleep(actual_delay)
    
    def _create_firefox_driver(self) -> webdriver.Firefox:
        """Create Firefox WebDriver with stealth configuration."""
        options = FirefoxOptions()
        
        # Basic options
        if self.config.headless:
            options.add_argument("--headless")
        
        # Stealth options
        if self.config.use_stealth:
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference('useAutomationExtension', False)
            options.set_preference("general.useragent.override", config_manager.get_user_agent(self.config))
        
        # Performance options
        if not self.config.load_images:
            options.set_preference("permissions.default.image", 2)
        
        if not self.config.javascript_enabled:
            options.set_preference("javascript.enabled", False)
        
        # Proxy configuration
        if self.config.proxy_url:
            proxy_parts = self.config.proxy_url.replace("http://", "").replace("https://", "").split(":")
            if len(proxy_parts) == 2:
                options.set_preference("network.proxy.type", 1)
                options.set_preference("network.proxy.http", proxy_parts[0])
                options.set_preference("network.proxy.http_port", int(proxy_parts[1]))
        
        # Create service
        service = None
        if config_manager.settings.firefox_binary_path:
            service = FirefoxService(executable_path=config_manager.settings.firefox_binary_path)
        
        return webdriver.Firefox(options=options, service=service)
    
    async def navigate_to(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL with error handling and performance tracking.
        
        Args:
            url: Target URL
            
        Returns:
            Dict containing navigation metadata
        """
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized. Call initialize() first.")
        
        self._page_load_start_time = time.time()
        
        try:
            logger.info(f"Navigating to URL: {url}")
            
            # Add random delay before navigation
            await self.add_random_delay(0.5)
            
            # Navigate in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.get, url)
            
            # Wait for page to be ready
            await self._wait_for_page_ready()
            
            # Simulate human behavior
            await self.simulate_human_behavior()
            
            # Handle JavaScript-rendered content
            await self._handle_javascript_content()
            
            load_time = time.time() - self._page_load_start_time
            
            metadata = {
                "url": url,
                "final_url": self.driver.current_url,
                "title": self.driver.title,
                "load_time": load_time,
                "page_source_length": len(self.driver.page_source),
                "timestamp": time.time(),
                "user_agent": self._current_user_agent,
                "javascript_enabled": self.config.javascript_enabled
            }
            
            logger.info(f"Successfully navigated to {url}", extra=metadata)
            return metadata
            
        except Exception as e:
            load_time = time.time() - self._page_load_start_time
            logger.error(f"Failed to navigate to {url}: {str(e)}", extra={
                "url": url,
                "load_time": load_time,
                "error": str(e)
            })
            raise
    
    async def _handle_javascript_content(self) -> None:
        """Handle JavaScript-rendered content with intelligent waiting."""
        if not self.config.javascript_enabled:
            return
        
        try:
            # Wait for common JavaScript frameworks to load
            js_checks = [
                "return document.readyState === 'complete'",
                "return typeof jQuery === 'undefined' || jQuery.active === 0",
                "return typeof angular === 'undefined' || angular.element(document).injector().get('$http').pendingRequests.length === 0",
                "return typeof React === 'undefined' || document.querySelector('[data-reactroot]') !== null"
            ]
            
            for check in js_checks:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        self.wait.until,
                        lambda driver: driver.execute_script(check)
                    )
                except TimeoutException:
                    continue
            
            # Wait for any AJAX requests to complete
            await self._wait_for_ajax_complete()
            
            # Additional wait for dynamic content
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
        except Exception as e:
            logger.debug(f"JavaScript content handling failed: {str(e)}")
    
    async def _wait_for_ajax_complete(self) -> None:
        """Wait for AJAX requests to complete."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.wait.until,
                lambda driver: driver.execute_script(
                    "return (typeof XMLHttpRequest !== 'undefined' ? "
                    "XMLHttpRequest.prototype.readyState === 4 : true) && "
                    "(typeof fetch !== 'undefined' ? "
                    "!window.fetch.toString().includes('[native code]') || "
                    "document.readyState === 'complete' : true)"
                )
            )
        except (TimeoutException, WebDriverException):
            pass
    
    async def find_pagination_links(self) -> List[str]:
        """
        Find pagination links on the current page.
        
        Returns:
            List of pagination URLs
        """
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        pagination_urls = []
        current_url = self.driver.current_url
        
        try:
            # Common pagination selectors
            pagination_selectors = [
                "a[href*='page']",
                "a[href*='p=']",
                "a[href*='offset']",
                ".pagination a",
                ".pager a",
                ".page-numbers a",
                "a[rel='next']",
                "a.next",
                ".next-page a"
            ]
            
            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and href != current_url:
                            # Convert relative URLs to absolute
                            if href.startswith('/'):
                                parsed_url = urlparse(current_url)
                                href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                            elif not href.startswith(('http://', 'https://')):
                                href = urljoin(current_url, href)
                            
                            if href not in pagination_urls:
                                pagination_urls.append(href)
                                
                except Exception as e:
                    logger.debug(f"Error finding pagination with selector {selector}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(pagination_urls)} pagination links")
            return pagination_urls
            
        except Exception as e:
            logger.error(f"Failed to find pagination links: {str(e)}")
            return []
    
    async def find_content_links(self, link_patterns: List[str] = None) -> List[str]:
        """
        Find content links based on patterns.
        
        Args:
            link_patterns: List of CSS selectors or URL patterns to match
            
        Returns:
            List of content URLs
        """
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        content_urls = []
        current_url = self.driver.current_url
        
        try:
            # Default link patterns if none provided
            if not link_patterns:
                link_patterns = [
                    "a[href*='/article/']",
                    "a[href*='/post/']",
                    "a[href*='/blog/']",
                    "a[href*='/news/']",
                    "a[href*='/product/']",
                    ".content-link a",
                    ".article-link a",
                    ".post-link a"
                ]
            
            for pattern in link_patterns:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and href != current_url:
                            # Convert relative URLs to absolute
                            if href.startswith('/'):
                                parsed_url = urlparse(current_url)
                                href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                            elif not href.startswith(('http://', 'https://')):
                                href = urljoin(current_url, href)
                            
                            if href not in content_urls:
                                content_urls.append(href)
                                
                except Exception as e:
                    logger.debug(f"Error finding links with pattern {pattern}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(content_urls)} content links")
            return content_urls
            
        except Exception as e:
            logger.error(f"Failed to find content links: {str(e)}")
            return []
    
    async def _wait_for_page_ready(self) -> None:
        """Wait for the page to be fully loaded."""
        try:
            # Wait for document ready state
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.wait.until,
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Additional wait time as configured
            if self.config.wait_time > 0:
                await asyncio.sleep(self.config.wait_time)
                
        except TimeoutException:
            logger.warning(f"Page ready timeout after {self.config.timeout} seconds")
    
    async def wait_for_element(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Wait for an element to be present and visible.
        
        Args:
            selector: Element selector
            by: Selenium By strategy
            timeout: Custom timeout (uses config timeout if None)
            
        Returns:
            WebElement if found
        """
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        wait_timeout = timeout or self.config.timeout
        custom_wait = WebDriverWait(self.driver, wait_timeout)
        
        try:
            loop = asyncio.get_event_loop()
            element = await loop.run_in_executor(
                None,
                custom_wait.until,
                EC.presence_of_element_located((by, selector))
            )
            
            logger.debug(f"Element found: {selector}")
            return element
            
        except TimeoutException:
            logger.warning(f"Element not found within {wait_timeout}s: {selector}")
            raise
    
    async def wait_for_elements(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> List[Any]:
        """
        Wait for multiple elements to be present.
        
        Args:
            selector: Element selector
            by: Selenium By strategy
            timeout: Custom timeout
            
        Returns:
            List of WebElements
        """
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        wait_timeout = timeout or self.config.timeout
        custom_wait = WebDriverWait(self.driver, wait_timeout)
        
        try:
            loop = asyncio.get_event_loop()
            elements = await loop.run_in_executor(
                None,
                custom_wait.until,
                EC.presence_of_all_elements_located((by, selector))
            )
            
            logger.debug(f"Found {len(elements)} elements: {selector}")
            return elements
            
        except TimeoutException:
            logger.warning(f"Elements not found within {wait_timeout}s: {selector}")
            return []
    
    async def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the browser.
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script
            
        Returns:
            Script execution result
        """
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.driver.execute_script,
                script,
                *args
            )
            
            logger.debug(f"Executed script successfully")
            return result
            
        except Exception as e:
            logger.error(f"Script execution failed: {str(e)}")
            raise
    
    async def take_screenshot(self, filename: Optional[str] = None) -> bytes:
        """
        Take a screenshot of the current page.
        
        Args:
            filename: Optional filename to save screenshot
            
        Returns:
            Screenshot as bytes
        """
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            
            if filename:
                await loop.run_in_executor(None, self.driver.save_screenshot, filename)
                logger.info(f"Screenshot saved to {filename}")
            
            screenshot_bytes = await loop.run_in_executor(
                None,
                self.driver.get_screenshot_as_png
            )
            
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            raise
    
    def get_page_source(self) -> str:
        """Get the current page source."""
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        return self.driver.page_source
    
    def get_current_url(self) -> str:
        """Get the current URL."""
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        return self.driver.current_url
    
    def get_title(self) -> str:
        """Get the current page title."""
        if not self._is_initialized:
            raise RuntimeError("Driver not initialized")
        
        return self.driver.title
    
    async def cleanup(self) -> None:
        """Clean up the WebDriver resources."""
        if self.driver:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.quit)
                logger.info("WebDriver cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during WebDriver cleanup: {str(e)}")
            finally:
                self.driver = None
                self.wait = None
                self._is_initialized = False
    
    @asynccontextmanager
    async def session(self):
        """Context manager for WebDriver session."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass