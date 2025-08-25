"""
Robots.txt handling utilities for ethical web scraping.

This module provides functionality to respect robots.txt files
and implement ethical scraping practices.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import aiohttp

from .logger import get_logger

logger = get_logger(__name__)


class RobotsHandler:
    """
    Handles robots.txt parsing and caching for ethical scraping.
    
    Provides methods to check if URLs can be scraped according to
    robots.txt rules and implements caching for performance.
    """
    
    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize robots handler.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict] = {}
        self._user_agents = [
            "*",  # Default user agent
            "python-requests",
            "Mozilla/5.0",
            "Googlebot"
        ]
    
    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if a URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string to check against
            
        Returns:
            bool: True if URL can be fetched, False otherwise
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Get robots.txt parser for this domain
            rp = await self._get_robots_parser(base_url)
            
            if rp is None:
                # If robots.txt is not available, allow scraping
                logger.debug(f"No robots.txt found for {base_url}, allowing access")
                return True
            
            # Check if the URL can be fetched
            can_fetch = rp.can_fetch(user_agent, url)
            
            logger.debug(f"Robots.txt check for {url}: {'allowed' if can_fetch else 'disallowed'}")
            return can_fetch
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {str(e)}")
            # Default to allowing access if check fails
            return True
    
    async def get_crawl_delay(self, url: str, user_agent: str = "*") -> Optional[float]:
        """
        Get the crawl delay specified in robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string
            
        Returns:
            Optional[float]: Crawl delay in seconds, None if not specified
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            rp = await self._get_robots_parser(base_url)
            
            if rp is None:
                return None
            
            delay = rp.crawl_delay(user_agent)
            
            if delay is not None:
                logger.debug(f"Crawl delay for {base_url}: {delay}s")
            
            return delay
            
        except Exception as e:
            logger.warning(f"Error getting crawl delay for {url}: {str(e)}")
            return None
    
    async def get_request_rate(self, url: str, user_agent: str = "*") -> Optional[tuple]:
        """
        Get the request rate specified in robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string
            
        Returns:
            Optional[tuple]: (requests, seconds) or None if not specified
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            rp = await self._get_robots_parser(base_url)
            
            if rp is None:
                return None
            
            rate = rp.request_rate(user_agent)
            
            if rate is not None:
                logger.debug(f"Request rate for {base_url}: {rate.requests}/{rate.seconds}s")
                return (rate.requests, rate.seconds)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting request rate for {url}: {str(e)}")
            return None
    
    async def _get_robots_parser(self, base_url: str) -> Optional[RobotFileParser]:
        """
        Get cached robots.txt parser or fetch and cache a new one.
        
        Args:
            base_url: Base URL of the domain
            
        Returns:
            Optional[RobotFileParser]: Parser instance or None if unavailable
        """
        current_time = time.time()
        
        # Check cache
        if base_url in self._cache:
            cache_entry = self._cache[base_url]
            if current_time - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['parser']
        
        # Fetch robots.txt
        robots_url = urljoin(base_url, '/robots.txt')
        
        try:
            robots_content = await self._fetch_robots_txt(robots_url)
            
            if robots_content is None:
                # Cache the fact that robots.txt is not available
                self._cache[base_url] = {
                    'parser': None,
                    'timestamp': current_time
                }
                return None
            
            # Parse robots.txt
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            # Use asyncio to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._parse_robots_content, rp, robots_content)
            
            # Cache the parser
            self._cache[base_url] = {
                'parser': rp,
                'timestamp': current_time
            }
            
            logger.debug(f"Cached robots.txt for {base_url}")
            return rp
            
        except Exception as e:
            logger.warning(f"Failed to fetch/parse robots.txt for {base_url}: {str(e)}")
            
            # Cache the failure to avoid repeated attempts
            self._cache[base_url] = {
                'parser': None,
                'timestamp': current_time
            }
            return None
    
    def _parse_robots_content(self, rp: RobotFileParser, content: str) -> None:
        """Parse robots.txt content synchronously."""
        # Split content into lines and feed to parser
        lines = content.split('\n')
        for line in lines:
            rp.read_line(line)
    
    async def _fetch_robots_txt(self, robots_url: str) -> Optional[str]:
        """
        Fetch robots.txt content from URL.
        
        Args:
            robots_url: URL of robots.txt file
            
        Returns:
            Optional[str]: Robots.txt content or None if unavailable
        """
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(robots_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.debug(f"Successfully fetched robots.txt from {robots_url}")
                        return content
                    elif response.status == 404:
                        logger.debug(f"No robots.txt found at {robots_url}")
                        return None
                    else:
                        logger.warning(f"Unexpected status {response.status} for {robots_url}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching robots.txt from {robots_url}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching robots.txt from {robots_url}: {str(e)}")
            return None
    
    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
        logger.info("Robots.txt cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for entry in self._cache.values():
            if current_time - entry['timestamp'] < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl": self.cache_ttl
        }
    
    def cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        for base_url, entry in self._cache.items():
            if current_time - entry['timestamp'] >= self.cache_ttl:
                expired_keys.append(base_url)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired robots.txt cache entries")


class EthicalScrapingEnforcer:
    """
    Enforces ethical scraping practices including robots.txt compliance.
    
    Provides a high-level interface for checking scraping permissions
    and implementing respectful crawling behavior.
    """
    
    def __init__(self, robots_handler: RobotsHandler = None):
        """
        Initialize ethical scraping enforcer.
        
        Args:
            robots_handler: Optional robots handler (creates default if None)
        """
        self.robots_handler = robots_handler or RobotsHandler()
        self._domain_delays: Dict[str, float] = {}
        self._last_request_times: Dict[str, float] = {}
    
    async def check_scraping_permission(
        self, 
        url: str, 
        user_agent: str = "*",
        respect_robots: bool = True
    ) -> Dict[str, any]:
        """
        Check if scraping is allowed and get recommended delays.
        
        Args:
            url: URL to check
            user_agent: User agent string
            respect_robots: Whether to check robots.txt
            
        Returns:
            Dict with permission info and recommended delays
        """
        result = {
            "allowed": True,
            "reason": "No restrictions found",
            "crawl_delay": None,
            "request_rate": None,
            "recommended_delay": 1.0  # Default 1 second delay
        }
        
        if not respect_robots:
            result["reason"] = "Robots.txt checking disabled"
            return result
        
        try:
            # Check robots.txt permission
            allowed = await self.robots_handler.can_fetch(url, user_agent)
            
            if not allowed:
                result.update({
                    "allowed": False,
                    "reason": "Disallowed by robots.txt"
                })
                return result
            
            # Get crawl delay
            crawl_delay = await self.robots_handler.get_crawl_delay(url, user_agent)
            if crawl_delay is not None:
                result["crawl_delay"] = crawl_delay
                result["recommended_delay"] = max(result["recommended_delay"], crawl_delay)
            
            # Get request rate
            request_rate = await self.robots_handler.get_request_rate(url, user_agent)
            if request_rate is not None:
                result["request_rate"] = request_rate
                # Convert request rate to delay
                requests, seconds = request_rate
                rate_delay = seconds / requests if requests > 0 else 1.0
                result["recommended_delay"] = max(result["recommended_delay"], rate_delay)
            
            result["reason"] = "Allowed by robots.txt"
            
        except Exception as e:
            logger.warning(f"Error checking scraping permission for {url}: {str(e)}")
            result["reason"] = f"Permission check failed: {str(e)}"
        
        return result
    
    async def wait_for_rate_limit(self, url: str, custom_delay: float = None) -> None:
        """
        Wait appropriate time before making request to respect rate limits.
        
        Args:
            url: URL being requested
            custom_delay: Custom delay to use (overrides calculated delay)
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        current_time = time.time()
        
        # Get last request time for this domain
        last_request_time = self._last_request_times.get(domain, 0)
        
        # Calculate required delay
        if custom_delay is not None:
            required_delay = custom_delay
        else:
            # Use domain-specific delay or default
            required_delay = self._domain_delays.get(domain, 1.0)
        
        # Calculate time since last request
        time_since_last = current_time - last_request_time
        
        # Wait if necessary
        if time_since_last < required_delay:
            wait_time = required_delay - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
            await asyncio.sleep(wait_time)
        
        # Update last request time
        self._last_request_times[domain] = time.time()
    
    def set_domain_delay(self, domain: str, delay: float) -> None:
        """
        Set custom delay for a specific domain.
        
        Args:
            domain: Domain name
            delay: Delay in seconds
        """
        self._domain_delays[domain] = delay
        logger.info(f"Set custom delay for {domain}: {delay}s")
    
    def get_domain_stats(self) -> Dict[str, Dict]:
        """Get statistics for all domains."""
        current_time = time.time()
        stats = {}
        
        for domain in set(list(self._domain_delays.keys()) + list(self._last_request_times.keys())):
            stats[domain] = {
                "custom_delay": self._domain_delays.get(domain),
                "last_request_time": self._last_request_times.get(domain),
                "time_since_last_request": (
                    current_time - self._last_request_times[domain]
                    if domain in self._last_request_times else None
                )
            }
        
        return stats


# Global instances
robots_handler = RobotsHandler()
ethical_enforcer = EthicalScrapingEnforcer(robots_handler)