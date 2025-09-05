"""
Simplified web scraper that actually works.

This module provides a working web scraper implementation that focuses on
reliability and functionality over advanced features.
"""

import asyncio
import logging
import time
import random
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
from datetime import datetime

from ..models.pydantic_models import ScrapingConfig, ScrapedData, ContentType
from ..utils.security_config import SecurityConfig

logger = logging.getLogger(__name__)


class SimpleWebScraper:
    """
    Simple, reliable web scraper using requests and BeautifulSoup.
    
    Focuses on functionality and reliability over advanced features.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize the simple web scraper."""
        self.config = config or ScrapingConfig()
        self.session = requests.Session()
        
        # Configure Gemini AI if available
        self.gemini_model = None
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini AI: {e}")
        
        # Setup session with secure headers
        self._setup_session()
    
    def _setup_session(self):
        """Setup the requests session with secure headers."""
        # Get secure user agents
        user_agents = SecurityConfig.get_secure_user_agents()
        user_agent = random.choice(user_agents)
        
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Set timeout
        self.session.timeout = self.config.timeout
    
    async def scrape_url(self, url: str, job_id: str = None) -> Optional[ScrapedData]:
        """
        Scrape a single URL and return structured data.
        
        Args:
            url: URL to scrape
            job_id: Optional job identifier
            
        Returns:
            ScrapedData if successful, None if failed
        """
        if not job_id:
            job_id = f"simple_{int(time.time())}"
        
        logger.info(f"Starting enhanced scrape of {url}")
        
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format: {url}")
            
            # Add delay for politeness
            if self.config.delay_between_requests > 0:
                delay = self.config.delay_between_requests
                # Add some randomization to avoid detection
                delay += random.uniform(0, delay * 0.3)
                await asyncio.sleep(delay)
            
            # Make the request with retries
            start_time = time.time()
            response = await self._make_request(url)
            load_time = time.time() - start_time
            
            if not response:
                logger.error(f"Failed to fetch {url} after all retries")
                return None
            
            # Validate response
            if response.status_code != 200:
                logger.warning(f"Non-200 status code {response.status_code} for {url}")
            
            if len(response.content) < 100:
                logger.warning(f"Response content too small ({len(response.content)} bytes) for {url}")
            
            # Parse the content with error handling
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                logger.error(f"Failed to parse HTML for {url}: {e}")
                return None
            
            # Extract content with enhanced error handling
            extracted_content = self._extract_content(soup, url)
            
            # Validate extracted content
            if not extracted_content.get('text') or len(extracted_content['text'].strip()) < 50:
                logger.warning(f"Insufficient content extracted from {url}")
                # Don't return None, but mark with low confidence
                extracted_content['text'] = extracted_content.get('title', 'No content available')
            
            # Process with AI if available
            ai_metadata = {}
            confidence_score = 0.5
            
            if self.gemini_model and extracted_content.get('text'):
                try:
                    ai_result = await self._analyze_with_ai(
                        extracted_content['text'], 
                        extracted_content.get('title', '')
                    )
                    ai_metadata = ai_result
                    confidence_score = ai_result.get('confidence', 0.5)
                except Exception as e:
                    logger.warning(f"AI analysis failed for {url}: {e}")
                    ai_metadata = {"error": str(e), "processing_status": "failed"}
            
            # Calculate quality score based on content
            quality_score = self._calculate_quality_score(extracted_content, response)
            
            # Create scraped data object
            scraped_data = ScrapedData(
                job_id=job_id,
                url=url,
                content=extracted_content,
                raw_html=response.text[:5000] if len(response.text) > 5000 else response.text,
                content_type=ContentType.HTML,
                confidence_score=confidence_score,
                ai_processed=bool(self.gemini_model and ai_metadata.get('processing_status') != 'failed'),
                ai_metadata=ai_metadata,
                data_quality_score=quality_score,
                content_length=len(extracted_content.get('text', '')),
                load_time=load_time,
                extracted_at=datetime.utcnow()
            )
            
            logger.info(f"Successfully scraped {url} (quality: {quality_score:.2f}, confidence: {confidence_score:.2f})")
            return scraped_data
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None
    
    async def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with retries."""
        for attempt in range(self.config.max_retries + 1):
            try:
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.session.get(url, timeout=self.config.timeout)
                )
                
                response.raise_for_status()
                return response
                
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed for {url}: {str(e)}")
                
                if attempt < self.config.max_retries:
                    # Exponential backoff
                    delay = min(2 ** attempt, 30)
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for {url}")
                    return None
        
        return None
    
    def _extract_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract content from BeautifulSoup object with enhanced error handling."""
        content = {
            'title': '',
            'text': '',
            'headings': [],
            'links': [],
            'images': [],
            'metadata': {}
        }
        
        try:
            # Extract title with fallbacks
            title_tag = soup.find('title')
            if title_tag:
                content['title'] = title_tag.get_text().strip()
            
            # Try Open Graph title as fallback
            if not content['title']:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    content['title'] = og_title['content'].strip()
            
            # Try h1 as final fallback
            if not content['title']:
                h1_tag = soup.find('h1')
                if h1_tag:
                    content['title'] = h1_tag.get_text().strip()
            
            # Extract metadata
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description and meta_description.get('content'):
                content['metadata']['description'] = meta_description['content'].strip()
            
            # Extract keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                content['metadata']['keywords'] = [k.strip() for k in meta_keywords['content'].split(',')]
            
            # Remove unwanted elements more thoroughly
            unwanted_selectors = [
                'script', 'style', 'nav', 'header', 'footer', 'aside',
                '.advertisement', '.ad', '.ads', '.cookie-banner', '.popup',
                '.social-share', '.share-buttons', '.newsletter-signup'
            ]
            
            for selector in unwanted_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Extract main text content with multiple strategies
            main_content = self._find_main_content(soup)
            
            # Extract paragraphs with better filtering
            text_parts = []
            paragraphs = main_content.find_all('p')
            
            for p in paragraphs:
                text = p.get_text().strip()
                # Better filtering for meaningful content
                if (text and 
                    len(text) > 20 and 
                    not text.lower().startswith(('click', 'subscribe', 'follow', 'share')) and
                    len([c for c in text if c.isalpha()]) > len(text) * 0.5):  # At least 50% letters
                    text_parts.append(text)
            
            # If no paragraphs found, try divs and other elements
            if not text_parts:
                for element in main_content.find_all(['div', 'span', 'section']):
                    text = element.get_text().strip()
                    if text and len(text) > 50 and len(text) < 1000:  # Reasonable length
                        text_parts.append(text)
                        if len(text_parts) >= 5:  # Limit to avoid too much noise
                            break
            
            content['text'] = ' '.join(text_parts)
            
            # Extract headings with hierarchy
            heading_hierarchy = []
            for i in range(1, 7):
                headings = main_content.find_all(f'h{i}')
                for heading in headings:
                    text = heading.get_text().strip()
                    if text and len(text) > 2:  # Filter very short headings
                        heading_hierarchy.append({
                            'level': i,
                            'text': text,
                            'id': heading.get('id', ''),
                            'class': ' '.join(heading.get('class', []))
                        })
            
            content['headings'] = heading_hierarchy
            
            # Extract links if configured
            if self.config.extract_links:
                unique_links = set()
                for link in main_content.find_all('a', href=True):
                    href = link['href'].strip()
                    if (href and 
                        not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) and
                        href not in unique_links):
                        
                        try:
                            absolute_url = urljoin(url, href)
                            link_text = link.get_text().strip()
                            
                            if link_text and len(link_text) > 2:  # Filter empty or very short link text
                                content['links'].append({
                                    'url': absolute_url,
                                    'text': link_text,
                                    'title': link.get('title', '')
                                })
                                unique_links.add(href)
                                
                                if len(content['links']) >= 20:  # Limit number of links
                                    break
                        except Exception as e:
                            logger.debug(f"Error processing link {href}: {e}")
                            continue
            
            # Extract images if configured
            if self.config.extract_images:
                unique_images = set()
                for img in main_content.find_all('img'):
                    src = img.get('src', '').strip()
                    if not src:
                        # Try data-src for lazy-loaded images
                        src = img.get('data-src', '').strip()
                    
                    if src and src not in unique_images:
                        try:
                            absolute_url = urljoin(url, src)
                            content['images'].append({
                                'url': absolute_url,
                                'alt': img.get('alt', ''),
                                'title': img.get('title', ''),
                                'width': img.get('width', ''),
                                'height': img.get('height', '')
                            })
                            unique_images.add(src)
                            
                            if len(content['images']) >= 10:  # Limit number of images
                                break
                        except Exception as e:
                            logger.debug(f"Error processing image {src}: {e}")
                            continue
            
        except Exception as e:
            logger.error(f"Content extraction error for {url}: {str(e)}")
            # Return minimal content on error
            content = {
                'title': 'Extraction Error',
                'text': f'Failed to extract content: {str(e)}',
                'headings': [],
                'links': [],
                'images': [],
                'metadata': {'error': str(e)}
            }
        
        return content
    
    def _find_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Find the main content area using multiple strategies."""
        # Strategy 1: Semantic HTML5 elements
        main_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '.content',
            '.post-content',
            '.entry-content',
            '.article-content',
            '#main',
            '#content',
            '#post'
        ]
        
        for selector in main_selectors:
            try:
                main_area = soup.select_one(selector)
                if main_area and len(main_area.get_text().strip()) > 100:
                    return main_area
            except Exception:
                continue
        
        # Strategy 2: Find the div with most text content
        divs = soup.find_all('div')
        best_div = None
        max_text_length = 0
        
        for div in divs:
            try:
                text_length = len(div.get_text().strip())
                if text_length > max_text_length and text_length > 200:
                    max_text_length = text_length
                    best_div = div
            except Exception:
                continue
        
        if best_div:
            return best_div
        
        # Fallback: use body or entire soup
        body = soup.find('body')
        return body if body else soup
    
    async def _analyze_with_ai(self, text: str, title: str) -> Dict[str, Any]:
        """Analyze content with Gemini AI."""
        try:
            prompt = f"""
            Analyze this web content and provide a JSON response with the following structure:
            {{
                "summary": "Brief summary (max 200 characters)",
                "topics": ["topic1", "topic2", "topic3"],
                "confidence": 0.8,
                "key_info": ["key point 1", "key point 2"],
                "content_category": "news|blog|product|documentation|other",
                "language": "detected language code",
                "quality_score": 0.7
            }}
            
            Title: {title}
            Content: {text[:2000]}
            
            Respond only with valid JSON.
            """
            
            # Run AI analysis in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_model.generate_content(prompt)
            )
            
            if response and response.text:
                try:
                    import json
                    ai_result = json.loads(response.text.strip())
                    
                    # Validate and standardize
                    return {
                        "summary": str(ai_result.get("summary", ""))[:200],
                        "confidence": min(max(float(ai_result.get("confidence", 0.5)), 0.0), 1.0),
                        "topics": ai_result.get("topics", [])[:5],
                        "quality_score": min(max(float(ai_result.get("quality_score", 0.5)), 0.0), 1.0),
                        "key_info": ai_result.get("key_info", [])[:10],
                        "content_category": ai_result.get("content_category", "other"),
                        "language": ai_result.get("language", "unknown"),
                        "ai_model": "gemini-2.0-flash-exp",
                        "processing_status": "success"
                    }
                    
                except (json.JSONDecodeError, ValueError, KeyError):
                    # Fallback to text parsing
                    return {
                        "summary": response.text[:200],
                        "confidence": 0.6,
                        "topics": [],
                        "quality_score": 0.6,
                        "key_info": [],
                        "content_category": "other",
                        "language": "unknown",
                        "ai_model": "gemini-2.0-flash-exp",
                        "processing_status": "partial_success"
                    }
            
        except Exception as e:
            logger.warning(f"AI analysis failed: {str(e)}")
        
        # Return default result on failure
        return {
            "summary": "AI analysis failed",
            "confidence": 0.3,
            "topics": [],
            "quality_score": 0.3,
            "key_info": [],
            "content_category": "other",
            "language": "unknown",
            "ai_model": "gemini-2.0-flash-exp",
            "processing_status": "error"
        }
    
    async def scrape_multiple(self, urls: List[str], job_id: str = None) -> List[ScrapedData]:
        """
        Scrape multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            job_id: Optional job identifier
            
        Returns:
            List of successfully scraped data
        """
        if not job_id:
            job_id = f"multi_{int(time.time())}"
        
        logger.info(f"Starting multi-URL scrape of {len(urls)} URLs")
        
        results = []
        
        for i, url in enumerate(urls):
            logger.info(f"Scraping URL {i+1}/{len(urls)}: {url}")
            
            try:
                data = await self.scrape_url(url, job_id)
                if data:
                    results.append(data)
                
                # Add delay between requests
                if i < len(urls) - 1:  # Don't delay after last URL
                    delay = self.config.delay_between_requests
                    # Add some randomization
                    delay += random.uniform(0, delay * 0.5)
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {str(e)}")
                continue
        
        logger.info(f"Multi-URL scrape completed: {len(results)}/{len(urls)} successful")
        return results
    
    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    def _calculate_quality_score(self, content: Dict[str, Any], response: requests.Response) -> float:
        """Calculate content quality score based on various factors."""
        score = 0.0
        
        try:
            # Title presence and quality (0-0.2)
            title = content.get('title', '')
            if title and len(title.strip()) > 5:
                score += 0.15
                if len(title) > 20 and len(title) < 100:  # Good title length
                    score += 0.05
            
            # Text content quality (0-0.4)
            text = content.get('text', '')
            if text:
                text_length = len(text.strip())
                if text_length > 100:
                    score += 0.2
                if text_length > 500:
                    score += 0.1
                if text_length > 1000:
                    score += 0.1
            
            # Structure quality (0-0.2)
            headings = content.get('headings', [])
            if headings:
                score += 0.1
                if len(headings) > 2:
                    score += 0.1
            
            # Links and images (0-0.1)
            if content.get('links'):
                score += 0.05
            if content.get('images'):
                score += 0.05
            
            # Response quality (0-0.1)
            if response.status_code == 200:
                score += 0.05
            if len(response.content) > 5000:
                score += 0.05
            
        except Exception as e:
            logger.warning(f"Error calculating quality score: {e}")
            score = 0.3  # Default fallback score
        
        return min(score, 1.0)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()