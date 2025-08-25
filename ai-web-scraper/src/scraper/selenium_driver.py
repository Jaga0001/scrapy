"""
Selenium WebDriver wrapper with stealth capabilities and advanced features.

This module provides a robust WebDriver wrapper that includes anti-detection
techniques, error handling, and performance optimizations.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
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
    
    def _create_chrome_driver(self) -> webdriver.Chrome:
        """Create Chrome WebDriver with stealth configuration."""
        options = ChromeOptions()
        
        # Basic options
        if self.config.headless:
            options.add_argument("--headless=new")
        
        # Stealth options
        if self.config.use_stealth:
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images") if not self.config.load_images else None
            options.add_argument("--disable-javascript") if not self.config.javascript_enabled else None
        
        # Performance options
        options.add_argument("--no-first-run")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-popup-blocking")
        
        # User agent
        user_agent = config_manager.get_user_agent(self.config)
        options.add_argument(f"--user-agent={user_agent}")
        
        # Proxy configuration
        if self.config.proxy_url:
            options.add_argument(f"--proxy-server={self.config.proxy_url}")
        
        # Window size for consistency
        options.add_argument("--window-size=1920,1080")
        
        # Create service
        service = None
        if config_manager.settings.chrome_binary_path:
            service = ChromeService(executable_path=config_manager.settings.chrome_binary_path)
        
        # Create driver
        driver = webdriver.Chrome(options=options, service=service)
        
        # Additional stealth measures
        if self.config.use_stealth:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent
            })
        
        return driver
    
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
            
            # Navigate in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.get, url)
            
            # Wait for page to be ready
            await self._wait_for_page_ready()
            
            load_time = time.time() - self._page_load_start_time
            
            metadata = {
                "url": url,
                "final_url": self.driver.current_url,
                "title": self.driver.title,
                "load_time": load_time,
                "page_source_length": len(self.driver.page_source),
                "timestamp": time.time()
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