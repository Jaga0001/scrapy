"""
AI Content Processing Pipeline using Gemini 2.5 API.

This module provides the main ContentProcessor class that orchestrates
AI-powered content analysis, extraction, and processing using Google's
Gemini 2.5 model.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from config.settings import get_settings
from src.models.pydantic_models import ScrapedData, ContentType


logger = logging.getLogger(__name__)


class ProcessedContent:
    """Container for AI-processed content results."""
    
    def __init__(
        self,
        structured_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        classification: Dict[str, Any],
        confidence_score: float,
        processing_metadata: Dict[str, Any]
    ):
        self.structured_data = structured_data
        self.entities = entities
        self.classification = classification
        self.confidence_score = confidence_score
        self.processing_metadata = processing_metadata
        self.processed_at = datetime.utcnow()


class ContentProcessor:
    """
    Main AI content processor using Gemini 2.5 API.
    
    Orchestrates the AI processing pipeline including text analysis,
    structure extraction, and confidence scoring.
    """
    
    def __init__(self):
        """Initialize the content processor with Gemini configuration."""
        self.settings = get_settings()
        self._model = None
        self._initialize_gemini()
    
    def _initialize_gemini(self) -> None:
        """Initialize Gemini API configuration."""
        if not self.settings.gemini_api_key:
            logger.warning("Gemini API key not configured - AI processing will be disabled")
            return
        
        try:
            genai.configure(api_key=self.settings.gemini_api_key)
            
            # Configure the model with safety settings
            generation_config = {
                "temperature": 0.1,  # Low temperature for consistent results
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            self._model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info("Gemini AI model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            self._model = None
    
    async def process_content(
        self,
        raw_content: str,
        content_type: ContentType,
        url: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ProcessedContent:
        """
        Process raw content using AI to extract structured data.
        
        Args:
            raw_content: Raw HTML or text content to process
            content_type: Type of content being processed
            url: Source URL for context
            additional_context: Additional context for processing
            
        Returns:
            ProcessedContent: AI-processed content with structured data
        """
        if not self._model:
            logger.warning("Gemini model not available - using fallback processing")
            return await self._fallback_processing(raw_content, content_type, url)
        
        try:
            # Import AI modules here to avoid circular imports
            from src.ai.text_analyzer import TextAnalyzer
            from src.ai.structure_extractor import StructureExtractor
            from src.ai.confidence_scorer import ConfidenceScorer
            
            # Initialize processors
            text_analyzer = TextAnalyzer(self._model)
            structure_extractor = StructureExtractor(self._model)
            confidence_scorer = ConfidenceScorer()
            
            # Process content in parallel where possible
            tasks = [
                text_analyzer.analyze_text(raw_content, url),
                structure_extractor.extract_structure(raw_content, content_type, url)
            ]
            
            analysis_results, structure_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions from parallel processing
            if isinstance(analysis_results, Exception):
                logger.error(f"Text analysis failed: {analysis_results}")
                analysis_results = {"entities": [], "classification": {"category": "unknown"}}
            
            if isinstance(structure_results, Exception):
                logger.error(f"Structure extraction failed: {structure_results}")
                structure_results = {"structured_data": {}, "metadata": {}}
            
            # Combine results
            structured_data = structure_results.get("structured_data", {})
            entities = analysis_results.get("entities", [])
            classification = analysis_results.get("classification", {"category": "unknown"})
            
            # Calculate confidence score
            confidence_score = await confidence_scorer.calculate_confidence(
                structured_data=structured_data,
                entities=entities,
                classification=classification,
                raw_content=raw_content
            )
            
            # Prepare processing metadata
            processing_metadata = {
                "model_used": "gemini-2.0-flash-exp",
                "processing_time": datetime.utcnow().isoformat(),
                "content_length": len(raw_content),
                "entities_found": len(entities),
                "structure_complexity": len(structured_data),
                "analysis_metadata": analysis_results.get("metadata", {}),
                "structure_metadata": structure_results.get("metadata", {}),
                "additional_context": additional_context or {}
            }
            
            return ProcessedContent(
                structured_data=structured_data,
                entities=entities,
                classification=classification,
                confidence_score=confidence_score,
                processing_metadata=processing_metadata
            )
            
        except Exception as e:
            logger.error(f"AI content processing failed: {e}")
            return await self._fallback_processing(raw_content, content_type, url)
    
    async def _fallback_processing(
        self,
        raw_content: str,
        content_type: ContentType,
        url: str
    ) -> ProcessedContent:
        """
        Fallback processing when AI is not available.
        
        Provides basic rule-based content extraction as a backup.
        """
        logger.info("Using fallback processing - AI not available")
        
        try:
            from bs4 import BeautifulSoup
            import re
            
            # Basic HTML parsing for fallback
            if content_type == ContentType.HTML:
                soup = BeautifulSoup(raw_content, 'html.parser')
                
                # Extract basic structured data
                structured_data = {
                    "title": soup.title.string if soup.title else "",
                    "headings": [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3'])],
                    "paragraphs": [p.get_text().strip() for p in soup.find_all('p')],
                    "links": [{"text": a.get_text().strip(), "href": a.get('href')} 
                             for a in soup.find_all('a', href=True)],
                    "images": [{"alt": img.get('alt', ''), "src": img.get('src')} 
                              for img in soup.find_all('img')]
                }
                
                # Basic entity extraction using regex
                text_content = soup.get_text()
                entities = []
                
                # Email addresses
                emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content)
                entities.extend([{"type": "email", "value": email} for email in emails])
                
                # Phone numbers (basic pattern)
                phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text_content)
                entities.extend([{"type": "phone", "value": phone} for phone in phones])
                
                # URLs
                urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text_content)
                entities.extend([{"type": "url", "value": url} for url in urls])
                
            else:
                # For non-HTML content, basic text processing
                structured_data = {
                    "content": raw_content[:1000],  # First 1000 chars
                    "length": len(raw_content),
                    "type": content_type.value
                }
                entities = []
            
            # Basic classification
            classification = {
                "category": "web_content",
                "confidence": 0.5,
                "subcategory": content_type.value
            }
            
            processing_metadata = {
                "model_used": "fallback_processor",
                "processing_time": datetime.utcnow().isoformat(),
                "content_length": len(raw_content),
                "entities_found": len(entities),
                "fallback_reason": "AI model not available"
            }
            
            return ProcessedContent(
                structured_data=structured_data,
                entities=entities,
                classification=classification,
                confidence_score=0.5,  # Lower confidence for fallback
                processing_metadata=processing_metadata
            )
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            # Return minimal result if even fallback fails
            return ProcessedContent(
                structured_data={"error": "Processing failed", "raw_length": len(raw_content)},
                entities=[],
                classification={"category": "error", "confidence": 0.0},
                confidence_score=0.0,
                processing_metadata={
                    "model_used": "error_handler",
                    "processing_time": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
            )
    
    async def batch_process_content(
        self,
        content_items: List[Tuple[str, ContentType, str]],
        max_concurrent: int = 5
    ) -> List[ProcessedContent]:
        """
        Process multiple content items in parallel batches.
        
        Args:
            content_items: List of (content, content_type, url) tuples
            max_concurrent: Maximum number of concurrent processing tasks
            
        Returns:
            List of ProcessedContent results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(content, content_type, url):
            async with semaphore:
                return await self.process_content(content, content_type, url)
        
        tasks = [
            process_with_semaphore(content, content_type, url)
            for content, content_type, url in content_items
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions in batch processing
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch processing failed for item {i}: {result}")
                # Create error result
                content, content_type, url = content_items[i]
                error_result = ProcessedContent(
                    structured_data={"error": str(result)},
                    entities=[],
                    classification={"category": "error", "confidence": 0.0},
                    confidence_score=0.0,
                    processing_metadata={"error": str(result), "item_index": i}
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def is_available(self) -> bool:
        """Check if AI processing is available."""
        return self._model is not None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on AI processing capabilities."""
        if not self._model:
            return {
                "status": "unavailable",
                "reason": "Gemini model not initialized",
                "api_key_configured": bool(self.settings.gemini_api_key)
            }
        
        try:
            # Test with a simple prompt
            test_prompt = "Analyze this text: 'Hello world'"
            response = await asyncio.to_thread(
                self._model.generate_content, test_prompt
            )
            
            return {
                "status": "healthy",
                "model": "gemini-2.0-flash-exp",
                "test_response_length": len(response.text) if response.text else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }