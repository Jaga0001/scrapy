"""
Content extraction module using BeautifulSoup4 for HTML parsing.

This module provides the ContentExtractor class that handles parsing HTML content,
extracting structured data, and applying custom selectors for targeted extraction.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment
from bs4.element import Tag

from ..models.pydantic_models import ScrapingConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ContentExtractor:
    """
    Advanced HTML content extractor using BeautifulSoup4.
    
    Provides comprehensive content extraction including text, metadata,
    structure analysis, and custom selector-based extraction.
    """
    
    def __init__(self, config: ScrapingConfig):
        """
        Initialize the content extractor.
        
        Args:
            config: Scraping configuration
        """
        self.config = config
        self._text_content_cache: Dict[str, str] = {}
        
    def extract_from_html(self, html_content: str, base_url: str) -> Dict[str, Any]:
        """
        Extract structured content from HTML.
        
        Args:
            html_content: Raw HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            Dict containing extracted content and metadata
        """
        try:
            logger.debug(f"Starting content extraction for {base_url}")
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            self._clean_soup(soup)
            
            # Extract different types of content
            extracted_content = {
                'metadata': self._extract_metadata(soup, base_url),
                'content': self._extract_main_content(soup),
                'structure': self._analyze_structure(soup),
                'links': self._extract_links(soup, base_url) if self.config.extract_links else [],
                'images': self._extract_images(soup, base_url) if self.config.extract_images else [],
                'custom': self._extract_custom_selectors(soup)
            }
            
            logger.debug(f"Content extraction completed for {base_url}")
            return extracted_content
            
        except Exception as e:
            logger.error(f"Content extraction failed for {base_url}: {str(e)}")
            return self._create_empty_content(base_url, str(e))
    
    def _clean_soup(self, soup: BeautifulSoup) -> None:
        """
        Remove unwanted elements from the soup.
        
        Args:
            soup: BeautifulSoup object to clean
        """
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove script and style elements (but preserve JSON-LD scripts)
        for element in soup(['style', 'noscript']):
            element.decompose()
        
        # Remove script elements except JSON-LD
        for script in soup.find_all('script'):
            if script.get('type') != 'application/ld+json':
                script.decompose()
        
        # Remove elements matching exclude selectors
        for selector in self.config.exclude_selectors:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except Exception as e:
                logger.warning(f"Invalid exclude selector '{selector}': {str(e)}")
        
        # Remove common unwanted elements
        unwanted_selectors = [
            '.advertisement', '.ad', '.ads',
            '.cookie-banner', '.cookie-notice',
            '.popup', '.modal',
            '.social-share', '.share-buttons',
            '.newsletter-signup',
            '[style*="display: none"]',
            '[style*="visibility: hidden"]'
        ]
        
        for selector in unwanted_selectors:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except:
                continue
    
    def _extract_metadata(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Extract page metadata including title, description, and meta tags.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for context
            
        Returns:
            Dict containing metadata
        """
        metadata = {
            'title': None,
            'description': None,
            'keywords': None,
            'author': None,
            'language': None,
            'canonical_url': None,
            'og_data': {},
            'twitter_data': {},
            'schema_data': []
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if not content:
                continue
            
            # Standard meta tags
            if name == 'description':
                metadata['description'] = content
            elif name == 'keywords':
                metadata['keywords'] = [k.strip() for k in content.split(',')]
            elif name == 'author':
                metadata['author'] = content
            elif name == 'language':
                metadata['language'] = content
            
            # Open Graph data
            elif property_attr.startswith('og:'):
                og_key = property_attr[3:]  # Remove 'og:' prefix
                metadata['og_data'][og_key] = content
            
            # Twitter Card data
            elif name.startswith('twitter:'):
                twitter_key = name[8:]  # Remove 'twitter:' prefix
                metadata['twitter_data'][twitter_key] = content
        
        # Extract canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            metadata['canonical_url'] = urljoin(base_url, canonical['href'])
        
        # Extract JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                script_content = script.string or script.get_text()
                if script_content:
                    # Clean up the content - remove extra whitespace and newlines
                    script_content = script_content.strip()
                    schema_data = json.loads(script_content)
                    metadata['schema_data'].append(schema_data)
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug(f"Failed to parse JSON-LD: {str(e)}")
                continue
        
        # Extract language from html tag
        if not metadata['language']:
            html_tag = soup.find('html')
            if html_tag:
                metadata['language'] = html_tag.get('lang') or html_tag.get('xml:lang')
        
        return metadata
    
    def _extract_main_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract the main content from the page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dict containing main content
        """
        content = {
            'text': '',
            'headings': [],
            'paragraphs': [],
            'lists': [],
            'tables': []
        }
        
        # Try to find main content area
        main_content = self._find_main_content_area(soup)
        
        # Extract text content
        content['text'] = self._extract_clean_text(main_content)
        
        # Extract headings (h1-h6)
        for i in range(1, 7):
            headings = main_content.find_all(f'h{i}')
            for heading in headings:
                content['headings'].append({
                    'level': i,
                    'text': heading.get_text().strip(),
                    'id': heading.get('id'),
                    'class': heading.get('class')
                })
        
        # Extract paragraphs
        paragraphs = main_content.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if text and len(text) > 10:  # Filter out very short paragraphs
                content['paragraphs'].append(text)
        
        # Extract lists
        lists = main_content.find_all(['ul', 'ol'])
        for list_elem in lists:
            list_items = [li.get_text().strip() for li in list_elem.find_all('li')]
            if list_items:
                content['lists'].append({
                    'type': list_elem.name,
                    'items': list_items
                })
        
        # Extract tables
        tables = main_content.find_all('table')
        for table in tables:
            table_data = self._extract_table_data(table)
            if table_data:
                content['tables'].append(table_data)
        
        return content
    
    def _find_main_content_area(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Identify and return the main content area of the page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            BeautifulSoup object containing main content
        """
        # Try semantic HTML5 elements first
        main_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '.content',
            '.post-content',
            '.entry-content',
            '#main',
            '#content'
        ]
        
        for selector in main_selectors:
            try:
                main_area = soup.select_one(selector)
                if main_area:
                    logger.debug(f"Found main content area using selector: {selector}")
                    return main_area
            except:
                continue
        
        # Fallback: use body or entire soup
        body = soup.find('body')
        return body if body else soup
    
    def _extract_clean_text(self, element: BeautifulSoup) -> str:
        """
        Extract clean text content from an element.
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            Clean text string
        """
        if not element:
            return ''
        
        # Get text and clean it
        text = element.get_text(separator=' ', strip=True)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common unwanted patterns
        text = re.sub(r'\n\s*\n', '\n', text)  # Multiple newlines
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Leading/trailing whitespace
        
        return text.strip()
    
    def _extract_table_data(self, table: Tag) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from a table.
        
        Args:
            table: BeautifulSoup table element
            
        Returns:
            Dict containing table data or None if empty
        """
        try:
            rows = table.find_all('tr')
            if not rows:
                return None
            
            table_data = {
                'headers': [],
                'rows': [],
                'caption': None
            }
            
            # Extract caption if present
            caption = table.find('caption')
            if caption:
                table_data['caption'] = caption.get_text().strip()
            
            # Extract headers
            header_row = table.find('tr')
            if header_row:
                headers = header_row.find_all(['th', 'td'])
                table_data['headers'] = [h.get_text().strip() for h in headers]
            
            # Extract data rows
            for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_data = [cell.get_text().strip() for cell in cells]
                    table_data['rows'].append(row_data)
            
            return table_data if table_data['rows'] else None
            
        except Exception as e:
            logger.warning(f"Failed to extract table data: {str(e)}")
            return None
    
    def _analyze_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Analyze the structural elements of the page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dict containing structure analysis
        """
        structure = {
            'element_counts': {},
            'has_navigation': False,
            'has_sidebar': False,
            'has_footer': False,
            'form_count': 0,
            'media_count': 0
        }
        
        # Count different element types
        elements_to_count = [
            'div', 'span', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'input', 'button'
        ]
        
        for element in elements_to_count:
            count = len(soup.find_all(element))
            if count > 0:
                structure['element_counts'][element] = count
        
        # Check for common page sections
        nav_selectors = ['nav', '.navigation', '.nav', '.menu', '#navigation']
        for selector in nav_selectors:
            if soup.select_one(selector):
                structure['has_navigation'] = True
                break
        
        sidebar_selectors = ['.sidebar', '.side-bar', '#sidebar', 'aside']
        for selector in sidebar_selectors:
            if soup.select_one(selector):
                structure['has_sidebar'] = True
                break
        
        footer_selectors = ['footer', '.footer', '#footer']
        for selector in footer_selectors:
            if soup.select_one(selector):
                structure['has_footer'] = True
                break
        
        # Count forms and media
        structure['form_count'] = len(soup.find_all('form'))
        structure['media_count'] = len(soup.find_all(['img', 'video', 'audio', 'iframe']))
        
        return structure
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract all links from the page.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of link dictionaries
        """
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            
            link_data = {
                'url': absolute_url,
                'text': link.get_text().strip(),
                'title': link.get('title'),
                'rel': link.get('rel'),
                'target': link.get('target'),
                'is_external': self._is_external_link(absolute_url, base_url)
            }
            
            links.append(link_data)
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract image information from the page.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of image dictionaries
        """
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, src.strip())
            
            image_data = {
                'url': absolute_url,
                'alt': img.get('alt', ''),
                'title': img.get('title'),
                'width': img.get('width'),
                'height': img.get('height'),
                'class': img.get('class'),
                'loading': img.get('loading')
            }
            
            images.append(image_data)
        
        return images
    
    def _extract_custom_selectors(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract content using custom CSS selectors.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dict containing custom extracted content
        """
        custom_content = {}
        
        for name, selector in self.config.custom_selectors.items():
            try:
                elements = soup.select(selector)
                
                if not elements:
                    custom_content[name] = None
                elif len(elements) == 1:
                    # Single element - return text content
                    custom_content[name] = elements[0].get_text().strip()
                else:
                    # Multiple elements - return list of text content
                    custom_content[name] = [elem.get_text().strip() for elem in elements]
                    
            except Exception as e:
                logger.warning(f"Failed to apply custom selector '{name}': {selector} - {str(e)}")
                custom_content[name] = None
        
        return custom_content
    
    def _is_external_link(self, url: str, base_url: str) -> bool:
        """
        Check if a URL is external to the base domain.
        
        Args:
            url: URL to check
            base_url: Base URL for comparison
            
        Returns:
            True if the URL is external
        """
        try:
            url_domain = urlparse(url).netloc.lower()
            base_domain = urlparse(base_url).netloc.lower()
            return url_domain != base_domain
        except:
            return True
    
    def _create_empty_content(self, url: str, error_message: str) -> Dict[str, Any]:
        """
        Create an empty content structure for failed extractions.
        
        Args:
            url: URL that failed
            error_message: Error message
            
        Returns:
            Empty content structure
        """
        return {
            'metadata': {
                'title': None,
                'description': None,
                'error': error_message
            },
            'content': {
                'text': '',
                'headings': [],
                'paragraphs': [],
                'lists': [],
                'tables': []
            },
            'structure': {
                'element_counts': {},
                'has_navigation': False,
                'has_sidebar': False,
                'has_footer': False,
                'form_count': 0,
                'media_count': 0
            },
            'links': [],
            'images': [],
            'custom': {}
        }