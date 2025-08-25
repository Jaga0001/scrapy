"""
Main web scraper class that orchestrates the scraping process.

This module provides the primary WebScraper class that coordinates
Selenium WebDriver operations, content extraction, and error handling.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

from ..models.pydantic_models import ScrapingConfig, ScrapingResult, ScrapedData, JobStatus, ContentType
from ..utils.logger import get_logger
from .selenium_driver import SeleniumDriver
from .content_extractor import ContentExtractor
from .config import config_manager

logger = get_logger(__name__)


class WebScraper:
    """
    Main web scraper class with async support and comprehensive error handling.
    
    Orchestrates the entire scraping process from URL navigation to content
    extraction, with support for dynamic content, rate limiting, and retries.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Initialize the web scraper.
        
        Args:
            config: Scraping configuration (uses default if None)
        """
        self.config = config or config_manager.get_default_config()
        self.driver: Optional[SeleniumDriver] = None
        self.extractor: Optional[ContentExtractor] = None
        self._session_active = False
        self._scraped_urls: set = set()
        self._robots_cache: Dict[str, RobotFileParser] = {}
        
        # Validate configuration
        is_valid, errors = config_manager.validate_config(self.config)
        if not is_valid:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    async def scrape_url(self, url: str, custom_config: Optional[Dict] = None) -> ScrapingResult:
        """
        Scrape a single URL and return structured data.
        
        Args:
            url: Target URL to scrape
            custom_config: Optional custom configuration overrides
            
        Returns:
            ScrapingResult: Complete scraping result with data and metadata
        """
        start_time = time.time()
        job_id = f"single_{int(start_time)}"
        
        # Apply custom configuration if provided
        effective_config = self.config
        if custom_config:
            config_data = self.config.model_dump()
            config_data.update(custom_config)
            effective_config = config_manager.create_config(url, config_data)
        
        logger.info(f"Starting single URL scrape: {url}", extra={
            "job_id": job_id,
            "url": url,
            "config": effective_config.model_dump()
        })
        
        try:
            # Check robots.txt if required
            if effective_config.respect_robots_txt and not await self._check_robots_txt(url):
                raise ValueError(f"Scraping not allowed by robots.txt: {url}")
            
            # Initialize components if needed
            if not self._session_active:
                await self._initialize_session(effective_config)
            
            # Perform the scraping
            scraped_data = await self._scrape_single_page(url, job_id, effective_config)
            
            total_time = time.time() - start_time
            
            result = ScrapingResult(
                job_id=job_id,
                success=True,
                data=[scraped_data] if scraped_data else [],
                total_time=total_time,
                pages_scraped=1 if scraped_data else 0,
                pages_failed=0 if scraped_data else 1,
                average_confidence=scraped_data.confidence_score if scraped_data else 0.0
            )
            
            logger.info(f"Single URL scrape completed successfully", extra={
                "job_id": job_id,
                "url": url,
                "total_time": total_time,
                "data_extracted": bool(scraped_data)
            })
            
            return result
            
        except Exception as e:
            total_time = time.time() - start_time
            error_message = str(e)
            
            logger.error(f"Single URL scrape failed: {error_message}", extra={
                "job_id": job_id,
                "url": url,
                "total_time": total_time,
                "error": error_message
            })
            
            return ScrapingResult(
                job_id=job_id,
                success=False,
                error_message=error_message,
                total_time=total_time,
                pages_scraped=0,
                pages_failed=1
            )
    
    async def scrape_multiple(self, urls: List[str], job_id: Optional[str] = None) -> ScrapingResult:
        """
        Scrape multiple URLs with rate limiting and error handling.
        
        Args:
            urls: List of URLs to scrape
            job_id: Optional job identifier
            
        Returns:
            ScrapingResult: Aggregated results from all URLs
        """
        start_time = time.time()
        job_id = job_id or f"multi_{int(start_time)}"
        
        logger.info(f"Starting multi-URL scrape", extra={
            "job_id": job_id,
            "url_count": len(urls),
            "config": self.config.model_dump()
        })
        
        scraped_data = []
        failed_urls = []
        
        try:
            # Initialize session
            await self._initialize_session(self.config)
            
            # Process URLs with rate limiting
            for i, url in enumerate(urls):
                try:
                    # Check robots.txt if required
                    if self.config.respect_robots_txt and not await self._check_robots_txt(url):
                        logger.warning(f"Skipping URL due to robots.txt: {url}")
                        failed_urls.append(url)
                        continue
                    
                    # Scrape the URL
                    data = await self._scrape_single_page(url, job_id, self.config)
                    if data:
                        scraped_data.append(data)
                    else:
                        failed_urls.append(url)
                    
                    # Rate limiting delay
                    if i < len(urls) - 1 and self.config.delay_between_requests > 0:
                        await asyncio.sleep(self.config.delay_between_requests)
                        
                except Exception as e:
                    logger.error(f"Failed to scrape URL {url}: {str(e)}")
                    failed_urls.append(url)
                    continue
            
            total_time = time.time() - start_time
            
            # Calculate average confidence
            avg_confidence = 0.0
            if scraped_data:
                avg_confidence = sum(data.confidence_score for data in scraped_data) / len(scraped_data)
            
            result = ScrapingResult(
                job_id=job_id,
                success=len(scraped_data) > 0,
                data=scraped_data,
                total_time=total_time,
                pages_scraped=len(scraped_data),
                pages_failed=len(failed_urls),
                average_confidence=avg_confidence,
                data_quality_summary={
                    "total_urls": len(urls),
                    "successful_urls": len(scraped_data),
                    "failed_urls": len(failed_urls),
                    "success_rate": len(scraped_data) / len(urls) if urls else 0
                }
            )
            
            logger.info(f"Multi-URL scrape completed", extra={
                "job_id": job_id,
                "total_urls": len(urls),
                "successful": len(scraped_data),
                "failed": len(failed_urls),
                "total_time": total_time
            })
            
            return result
            
        except Exception as e:
            total_time = time.time() - start_time
            error_message = str(e)
            
            logger.error(f"Multi-URL scrape failed: {error_message}", extra={
                "job_id": job_id,
                "total_time": total_time,
                "error": error_message
            })
            
            return ScrapingResult(
                job_id=job_id,
                success=False,
                error_message=error_message,
                data=scraped_data,
                total_time=total_time,
                pages_scraped=len(scraped_data),
                pages_failed=len(urls) - len(scraped_data)
            )
    
    async def _scrape_single_page(
        self, 
        url: str, 
        job_id: str, 
        config: ScrapingConfig
    ) -> Optional[ScrapedData]:
        """
        Scrape a single page with retries and error handling.
        
        Args:
            url: URL to scrape
            job_id: Job identifier
            config: Scraping configuration
            
        Returns:
            ScrapedData if successful, None if failed
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= config.max_retries:
            try:
                logger.debug(f"Scraping attempt {retry_count + 1} for {url}")
                
                # Navigate to the URL
                navigation_metadata = await self.driver.navigate_to(url)
                
                # Wait for dynamic content if configured
                if config.wait_time > 0:
                    await asyncio.sleep(config.wait_time)
                
                # Get page source
                html_content = self.driver.get_page_source()
                
                if not html_content or len(html_content.strip()) < 100:
                    raise ValueError("Page content is empty or too short")
                
                # Extract content
                extracted_content = self.extractor.extract_from_html(html_content, url)
                
                # Create scraped data object
                scraped_data = ScrapedData(
                    job_id=job_id,
                    url=url,
                    content=extracted_content,
                    raw_html=html_content if config.custom_selectors.get('include_raw_html') else None,
                    content_type=ContentType.HTML,
                    content_metadata={
                        **navigation_metadata,
                        "retry_count": retry_count,
                        "config_used": config.model_dump()
                    },
                    confidence_score=self._calculate_confidence_score(extracted_content),
                    content_length=len(html_content),
                    load_time=navigation_metadata.get('load_time', 0.0)
                )
                
                # Mark URL as scraped
                self._scraped_urls.add(url)
                
                logger.debug(f"Successfully scraped {url} on attempt {retry_count + 1}")
                return scraped_data
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                logger.warning(f"Scraping attempt {retry_count} failed for {url}: {str(e)}")
                
                if retry_count <= config.max_retries:
                    # Exponential backoff
                    delay = min(2 ** retry_count, 30)
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for {url}: {str(last_error)}")
        
        return None
    
    async def _initialize_session(self, config: ScrapingConfig) -> None:
        """Initialize the scraping session with driver and extractor."""
        if self._session_active:
            return
        
        try:
            logger.info("Initializing scraping session")
            
            # Initialize Selenium driver
            self.driver = SeleniumDriver(config)
            await self.driver.initialize()
            
            # Initialize content extractor
            self.extractor = ContentExtractor(config)
            
            self._session_active = True
            logger.info("Scraping session initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize scraping session: {str(e)}")
            await self.cleanup()
            raise
    
    async def _check_robots_txt(self, url: str) -> bool:
        """
        Check if scraping is allowed by robots.txt.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if scraping is allowed
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check cache first
            if base_url in self._robots_cache:
                rp = self._robots_cache[base_url]
            else:
                # Fetch and parse robots.txt
                robots_url = urljoin(base_url, '/robots.txt')
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                # Use asyncio to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, rp.read)
                
                self._robots_cache[base_url] = rp
            
            # Check if scraping is allowed
            user_agent = config_manager.get_user_agent(self.config)
            return rp.can_fetch(user_agent, url)
            
        except Exception as e:
            logger.warning(f"Could not check robots.txt for {url}: {str(e)}")
            # Default to allowing scraping if robots.txt check fails
            return True
    
    def _calculate_confidence_score(self, extracted_content: Dict[str, Any]) -> float:
        """
        Calculate a confidence score for the extracted content.
        
        Args:
            extracted_content: Extracted content dictionary
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check for presence of different content types
        if extracted_content.get('metadata', {}).get('title'):
            score += 0.2
        
        if extracted_content.get('content', {}).get('text'):
            text_length = len(extracted_content['content']['text'])
            if text_length > 100:
                score += 0.3
            elif text_length > 50:
                score += 0.15
        
        if extracted_content.get('content', {}).get('headings'):
            score += 0.2
        
        if extracted_content.get('structure', {}).get('element_counts', {}).get('paragraphs', 0) > 0:
            score += 0.15
        
        if extracted_content.get('custom'):
            custom_data = extracted_content['custom']
            non_null_custom = sum(1 for v in custom_data.values() if v is not None)
            if non_null_custom > 0:
                score += 0.15
        
        return min(score, 1.0)
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        try:
            if self.driver:
                await self.driver.cleanup()
                self.driver = None
            
            self.extractor = None
            self._session_active = False
            self._scraped_urls.clear()
            
            logger.info("WebScraper cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during WebScraper cleanup: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        if self._session_active:
            try:
                asyncio.create_task(self.cleanup())
            except:
                pass