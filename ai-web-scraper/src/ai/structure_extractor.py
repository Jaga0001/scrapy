"""
Structure Extractor module for identifying and extracting data structures.

This module uses Gemini AI to identify structured data patterns in web content
and extract them into organized, queryable formats.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import google.generativeai as genai
from bs4 import BeautifulSoup

from src.models.pydantic_models import ContentType


logger = logging.getLogger(__name__)


class StructureExtractor:
    """
    AI-powered structure extractor using Gemini for data structure identification.
    
    Identifies and extracts structured data patterns from web content including
    tables, lists, forms, product information, and other structured elements.
    """
    
    def __init__(self, model: genai.GenerativeModel):
        """
        Initialize structure extractor with Gemini model.
        
        Args:
            model: Configured Gemini GenerativeModel instance
        """
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    async def extract_structure(
        self,
        content: str,
        content_type: ContentType,
        source_url: str,
        extraction_focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from content using AI analysis.
        
        Args:
            content: Raw content to analyze
            content_type: Type of content (HTML, JSON, etc.)
            source_url: Source URL for context
            extraction_focus: Specific focus for extraction (products, contacts, etc.)
            
        Returns:
            Dictionary containing structured data and metadata
        """
        try:
            if content_type == ContentType.HTML:
                return await self._extract_html_structure(content, source_url, extraction_focus)
            elif content_type == ContentType.JSON:
                return await self._extract_json_structure(content, source_url)
            elif content_type == ContentType.TEXT:
                return await self._extract_text_structure(content, source_url, extraction_focus)
            else:
                return await self._extract_generic_structure(content, source_url)
                
        except Exception as e:
            self.logger.error(f"Structure extraction failed: {e}")
            return self._create_error_result(str(e)) 
   
    async def _extract_html_structure(
        self,
        html_content: str,
        source_url: str,
        extraction_focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structured data from HTML content."""
        
        # First, parse HTML to get clean text and structure
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text_content = soup.get_text()
        
        # Prepare extraction prompt based on focus
        if extraction_focus:
            focus_instruction = f"Focus specifically on extracting: {extraction_focus}"
        else:
            focus_instruction = "Extract all structured data patterns you can identify"
        
        prompt = f"""
        Analyze this HTML content and extract structured data. {focus_instruction}
        
        Source URL: {source_url}
        HTML Content: {html_content[:5000]}  # Limit to avoid token limits
        
        Return structured data in JSON format:
        {{
            "structured_data": {{
                "products": [
                    {{
                        "name": "product_name",
                        "price": "price_value",
                        "description": "description",
                        "availability": "in_stock|out_of_stock",
                        "rating": 4.5,
                        "reviews_count": 123
                    }}
                ],
                "contacts": [
                    {{
                        "type": "email|phone|address",
                        "value": "contact_value",
                        "label": "contact_label"
                    }}
                ],
                "articles": [
                    {{
                        "title": "article_title",
                        "author": "author_name",
                        "date": "publication_date",
                        "content": "article_content",
                        "tags": ["tag1", "tag2"]
                    }}
                ],
                "navigation": [
                    {{
                        "text": "link_text",
                        "url": "link_url",
                        "level": 1
                    }}
                ],
                "forms": [
                    {{
                        "action": "form_action",
                        "method": "GET|POST",
                        "fields": [
                            {{
                                "name": "field_name",
                                "type": "text|email|password",
                                "required": true,
                                "label": "field_label"
                            }}
                        ]
                    }}
                ],
                "tables": [
                    {{
                        "headers": ["col1", "col2"],
                        "rows": [
                            ["value1", "value2"],
                            ["value3", "value4"]
                        ],
                        "caption": "table_caption"
                    }}
                ],
                "media": [
                    {{
                        "type": "image|video|audio",
                        "src": "media_url",
                        "alt": "alt_text",
                        "caption": "media_caption"
                    }}
                ]
            }},
            "metadata": {{
                "page_title": "extracted_title",
                "meta_description": "meta_description",
                "keywords": ["keyword1", "keyword2"],
                "language": "detected_language",
                "structure_complexity": "simple|moderate|complex",
                "data_richness": "low|medium|high"
            }}
        }}
        
        Only include sections that contain actual data. Empty sections should be omitted.
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini")
            
            result = json.loads(response.text)
            
            # Add processing metadata
            result["metadata"]["processing_timestamp"] = datetime.utcnow().isoformat()
            result["metadata"]["source_url"] = source_url
            result["metadata"]["content_length"] = len(html_content)
            result["metadata"]["extraction_method"] = "gemini_ai"
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Gemini JSON response: {e}")
            return await self._fallback_html_extraction(html_content, source_url)
        except Exception as e:
            self.logger.error(f"Gemini HTML extraction failed: {e}")
            return await self._fallback_html_extraction(html_content, source_url)
    
    async def _extract_json_structure(
        self,
        json_content: str,
        source_url: str
    ) -> Dict[str, Any]:
        """Extract and analyze JSON structure."""
        
        try:
            # Parse JSON to validate and analyze structure
            parsed_json = json.loads(json_content)
            
            prompt = f"""
            Analyze this JSON data and extract meaningful structured information:
            
            JSON Data: {json.dumps(parsed_json, indent=2)[:4000]}
            
            Return analysis in JSON format:
            {{
                "structured_data": {{
                    "schema_analysis": {{
                        "top_level_keys": ["key1", "key2"],
                        "data_types": {{"key1": "array", "key2": "object"}},
                        "nested_levels": 3,
                        "array_lengths": {{"items": 10}}
                    }},
                    "extracted_entities": [
                        {{
                            "path": "data.items[0].name",
                            "type": "product_name",
                            "value": "extracted_value"
                        }}
                    ],
                    "patterns": [
                        {{
                            "pattern_type": "product_listing|user_data|api_response",
                            "confidence": 0.9,
                            "description": "pattern_description"
                        }}
                    ]
                }},
                "metadata": {{
                    "json_valid": true,
                    "structure_type": "api_response|config|data_export",
                    "complexity": "simple|moderate|complex"
                }}
            }}
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            result = json.loads(response.text)
            result["metadata"]["processing_timestamp"] = datetime.utcnow().isoformat()
            result["metadata"]["source_url"] = source_url
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON content: {e}")
            return self._create_error_result(f"Invalid JSON: {e}")
        except Exception as e:
            self.logger.error(f"JSON structure extraction failed: {e}")
            return self._create_error_result(str(e))
    
    async def _extract_text_structure(
        self,
        text_content: str,
        source_url: str,
        extraction_focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structure from plain text content."""
        
        focus_instruction = f"Focus on: {extraction_focus}" if extraction_focus else "Extract all structured patterns"
        
        prompt = f"""
        Analyze this text content and identify structured patterns. {focus_instruction}
        
        Text: {text_content[:4000]}
        
        Return structured data in JSON format:
        {{
            "structured_data": {{
                "sections": [
                    {{
                        "title": "section_title",
                        "content": "section_content",
                        "type": "header|paragraph|list|quote"
                    }}
                ],
                "lists": [
                    {{
                        "type": "ordered|unordered|definition",
                        "items": ["item1", "item2"]
                    }}
                ],
                "key_value_pairs": [
                    {{
                        "key": "attribute_name",
                        "value": "attribute_value"
                    }}
                ],
                "addresses": [
                    {{
                        "full_address": "complete_address",
                        "street": "street_address",
                        "city": "city_name",
                        "state": "state_name",
                        "zip": "zip_code"
                    }}
                ],
                "dates_times": [
                    {{
                        "raw_text": "original_date_text",
                        "parsed_date": "2024-01-01",
                        "type": "event|deadline|publication"
                    }}
                ]
            }},
            "metadata": {{
                "text_structure": "structured|semi_structured|unstructured",
                "information_density": "high|medium|low"
            }}
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            result = json.loads(response.text)
            result["metadata"]["processing_timestamp"] = datetime.utcnow().isoformat()
            result["metadata"]["source_url"] = source_url
            
            return result
            
        except Exception as e:
            self.logger.error(f"Text structure extraction failed: {e}")
            return await self._fallback_text_extraction(text_content, source_url)
    
    async def _extract_generic_structure(
        self,
        content: str,
        source_url: str
    ) -> Dict[str, Any]:
        """Generic structure extraction for unknown content types."""
        
        prompt = f"""
        Analyze this content and extract any structured information:
        
        Content: {content[:3000]}
        
        Return any structured patterns you can identify in JSON format:
        {{
            "structured_data": {{
                "identified_patterns": [
                    {{
                        "pattern_type": "pattern_name",
                        "data": {{}},
                        "confidence": 0.8
                    }}
                ]
            }},
            "metadata": {{
                "content_type_guess": "guessed_type",
                "structure_found": true
            }}
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            result = json.loads(response.text)
            result["metadata"]["processing_timestamp"] = datetime.utcnow().isoformat()
            result["metadata"]["source_url"] = source_url
            
            return result
            
        except Exception as e:
            self.logger.error(f"Generic structure extraction failed: {e}")
            return self._create_error_result(str(e))
    
    async def _fallback_html_extraction(
        self,
        html_content: str,
        source_url: str
    ) -> Dict[str, Any]:
        """Fallback HTML extraction using BeautifulSoup."""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic structured data
            structured_data = {
                "products": [],  # Would need more sophisticated logic
                "contacts": [],
                "articles": [],
                "navigation": [],
                "forms": [],
                "tables": [],
                "media": []
            }
            
            # Extract navigation links
            for link in soup.find_all('a', href=True):
                if link.get_text().strip():
                    structured_data["navigation"].append({
                        "text": link.get_text().strip(),
                        "url": link['href'],
                        "level": 1
                    })
            
            # Extract forms
            for form in soup.find_all('form'):
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', 'GET').upper(),
                    "fields": []
                }
                
                for input_field in form.find_all(['input', 'textarea', 'select']):
                    field_data = {
                        "name": input_field.get('name', ''),
                        "type": input_field.get('type', 'text'),
                        "required": input_field.has_attr('required'),
                        "label": ""
                    }
                    form_data["fields"].append(field_data)
                
                structured_data["forms"].append(form_data)
            
            # Extract tables
            for table in soup.find_all('table'):
                table_data = {"headers": [], "rows": [], "caption": ""}
                
                # Get caption
                caption = table.find('caption')
                if caption:
                    table_data["caption"] = caption.get_text().strip()
                
                # Get headers
                header_row = table.find('tr')
                if header_row:
                    headers = header_row.find_all(['th', 'td'])
                    table_data["headers"] = [h.get_text().strip() for h in headers]
                
                # Get data rows
                for row in table.find_all('tr')[1:]:  # Skip header row
                    cells = row.find_all(['td', 'th'])
                    row_data = [cell.get_text().strip() for cell in cells]
                    if row_data:
                        table_data["rows"].append(row_data)
                
                structured_data["tables"].append(table_data)
            
            # Extract media
            for img in soup.find_all('img'):
                structured_data["media"].append({
                    "type": "image",
                    "src": img.get('src', ''),
                    "alt": img.get('alt', ''),
                    "caption": ""
                })
            
            metadata = {
                "page_title": soup.title.string if soup.title else "",
                "meta_description": "",
                "keywords": [],
                "language": soup.get('lang', 'unknown'),
                "structure_complexity": "moderate",
                "data_richness": "medium",
                "processing_timestamp": datetime.utcnow().isoformat(),
                "source_url": source_url,
                "extraction_method": "fallback_beautifulsoup"
            }
            
            # Get meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                metadata["meta_description"] = meta_desc.get('content', '')
            
            return {
                "structured_data": structured_data,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Fallback HTML extraction failed: {e}")
            return self._create_error_result(str(e))
    
    async def _fallback_text_extraction(
        self,
        text_content: str,
        source_url: str
    ) -> Dict[str, Any]:
        """Fallback text structure extraction using regex patterns."""
        
        import re
        
        structured_data = {
            "sections": [],
            "lists": [],
            "key_value_pairs": [],
            "addresses": [],
            "dates_times": []
        }
        
        # Extract sections (lines that look like headers)
        lines = text_content.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.isupper() or line.endswith(':') or len(line.split()) <= 5):
                structured_data["sections"].append({
                    "title": line,
                    "content": "",
                    "type": "header"
                })
        
        # Extract key-value pairs (pattern: "Key: Value")
        kv_pattern = r'([A-Za-z\s]+):\s*([^\n]+)'
        matches = re.findall(kv_pattern, text_content)
        for key, value in matches:
            structured_data["key_value_pairs"].append({
                "key": key.strip(),
                "value": value.strip()
            })
        
        # Extract dates
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            dates = re.findall(pattern, text_content, re.IGNORECASE)
            for date in dates:
                structured_data["dates_times"].append({
                    "raw_text": date,
                    "parsed_date": "",  # Would need proper date parsing
                    "type": "unknown"
                })
        
        metadata = {
            "text_structure": "semi_structured",
            "information_density": "medium",
            "processing_timestamp": datetime.utcnow().isoformat(),
            "source_url": source_url,
            "extraction_method": "fallback_regex"
        }
        
        return {
            "structured_data": structured_data,
            "metadata": metadata
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result structure."""
        
        return {
            "structured_data": {},
            "metadata": {
                "error": error_message,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "extraction_method": "error"
            }
        }
    
    async def extract_specific_structure(
        self,
        content: str,
        structure_type: str,
        content_type: ContentType
    ) -> Dict[str, Any]:
        """
        Extract specific type of structure (e.g., products, contacts, articles).
        
        Args:
            content: Content to analyze
            structure_type: Specific structure to extract
            content_type: Type of content
            
        Returns:
            Extracted structure data
        """
        
        return await self.extract_structure(
            content=content,
            content_type=content_type,
            source_url="",
            extraction_focus=structure_type
        )