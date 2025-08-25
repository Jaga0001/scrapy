"""
Text Analysis module using Gemini AI for NLP and entity extraction.

This module provides natural language processing capabilities including
entity extraction, sentiment analysis, and content classification.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import google.generativeai as genai


logger = logging.getLogger(__name__)


class TextAnalyzer:
    """
    AI-powered text analyzer using Gemini for NLP tasks.
    
    Provides entity extraction, sentiment analysis, content classification,
    and other natural language processing capabilities.
    """
    
    def __init__(self, model: genai.GenerativeModel):
        """
        Initialize text analyzer with Gemini model.
        
        Args:
            model: Configured Gemini GenerativeModel instance
        """
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    async def analyze_text(
        self,
        text_content: str,
        source_url: str,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive text analysis using Gemini AI.
        
        Args:
            text_content: Text content to analyze
            source_url: Source URL for context
            analysis_type: Type of analysis (comprehensive, entities_only, classification_only)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            if analysis_type == "comprehensive":
                return await self._comprehensive_analysis(text_content, source_url)
            elif analysis_type == "entities_only":
                return await self._extract_entities_only(text_content)
            elif analysis_type == "classification_only":
                return await self._classify_content_only(text_content)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
                
        except Exception as e:
            self.logger.error(f"Text analysis failed: {e}")
            return self._create_error_result(str(e))   
 
    async def _comprehensive_analysis(
        self,
        text_content: str,
        source_url: str
    ) -> Dict[str, Any]:
        """Perform comprehensive text analysis including entities and classification."""
        
        # Prepare the analysis prompt
        prompt = f"""
        Analyze the following web content and provide a comprehensive analysis in JSON format.
        
        Source URL: {source_url}
        Content: {text_content[:4000]}  # Limit content to avoid token limits
        
        Please provide analysis in the following JSON structure:
        {{
            "entities": [
                {{
                    "type": "entity_type",
                    "value": "entity_value",
                    "confidence": 0.95,
                    "context": "surrounding_context"
                }}
            ],
            "classification": {{
                "primary_category": "category_name",
                "subcategories": ["sub1", "sub2"],
                "confidence": 0.90,
                "content_type": "article|product|news|blog|etc"
            }},
            "sentiment": {{
                "overall": "positive|negative|neutral",
                "score": 0.75,
                "aspects": [
                    {{"aspect": "service", "sentiment": "positive", "score": 0.8}}
                ]
            }},
            "key_topics": [
                {{"topic": "topic_name", "relevance": 0.85, "keywords": ["key1", "key2"]}}
            ],
            "summary": "Brief summary of the content",
            "language": "detected_language_code",
            "metadata": {{
                "word_count": 150,
                "reading_level": "intermediate",
                "content_quality": "high|medium|low"
            }}
        }}
        
        Focus on extracting:
        - Named entities (people, organizations, locations, dates, etc.)
        - Product information if present
        - Contact information
        - Key topics and themes
        - Sentiment and tone
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini")
            
            # Parse JSON response
            analysis_result = json.loads(response.text)
            
            # Add processing metadata
            analysis_result["metadata"]["processing_timestamp"] = datetime.utcnow().isoformat()
            analysis_result["metadata"]["source_url"] = source_url
            analysis_result["metadata"]["content_length"] = len(text_content)
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Gemini JSON response: {e}")
            return await self._fallback_analysis(text_content, source_url)
        except Exception as e:
            self.logger.error(f"Gemini analysis failed: {e}")
            return await self._fallback_analysis(text_content, source_url)
    
    async def _extract_entities_only(self, text_content: str) -> Dict[str, Any]:
        """Extract only entities from text content."""
        
        prompt = f"""
        Extract named entities from the following text and return them in JSON format:
        
        Text: {text_content[:3000]}
        
        Return JSON in this format:
        {{
            "entities": [
                {{
                    "type": "PERSON|ORGANIZATION|LOCATION|DATE|EMAIL|PHONE|URL|PRODUCT|MONEY",
                    "value": "entity_value",
                    "confidence": 0.95,
                    "start_pos": 10,
                    "end_pos": 25
                }}
            ]
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            result = json.loads(response.text)
            result["metadata"] = {
                "analysis_type": "entities_only",
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return self._create_error_result(str(e))
    
    async def _classify_content_only(self, text_content: str) -> Dict[str, Any]:
        """Classify content without entity extraction."""
        
        prompt = f"""
        Classify the following web content and return classification in JSON format:
        
        Content: {text_content[:2000]}
        
        Return JSON in this format:
        {{
            "classification": {{
                "primary_category": "news|blog|product|service|documentation|forum|social|ecommerce|corporate",
                "subcategories": ["technology", "business"],
                "confidence": 0.90,
                "content_type": "article|listing|profile|review|tutorial",
                "industry": "detected_industry",
                "target_audience": "general|professional|technical|consumer"
            }}
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            result = json.loads(response.text)
            result["metadata"] = {
                "analysis_type": "classification_only",
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Content classification failed: {e}")
            return self._create_error_result(str(e))
    
    async def _fallback_analysis(
        self,
        text_content: str,
        source_url: str
    ) -> Dict[str, Any]:
        """Fallback analysis using basic NLP techniques."""
        
        import re
        from collections import Counter
        
        # Basic entity extraction using regex
        entities = []
        
        # Email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content)
        entities.extend([
            {"type": "EMAIL", "value": email, "confidence": 0.9}
            for email in set(emails)
        ])
        
        # Phone numbers
        phones = re.findall(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', text_content)
        entities.extend([
            {"type": "PHONE", "value": phone, "confidence": 0.8}
            for phone in set(phones)
        ])
        
        # URLs
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text_content)
        entities.extend([
            {"type": "URL", "value": url, "confidence": 0.9}
            for url in set(urls)
        ])
        
        # Basic word frequency for topics
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text_content.lower())
        word_freq = Counter(words)
        common_words = word_freq.most_common(10)
        
        # Simple classification based on keywords
        classification = self._classify_by_keywords(text_content)
        
        return {
            "entities": entities,
            "classification": classification,
            "sentiment": {"overall": "neutral", "score": 0.5},
            "key_topics": [
                {"topic": word, "relevance": count/len(words), "keywords": [word]}
                for word, count in common_words[:5]
            ],
            "summary": text_content[:200] + "..." if len(text_content) > 200 else text_content,
            "language": "en",  # Default assumption
            "metadata": {
                "word_count": len(words),
                "processing_method": "fallback",
                "processing_timestamp": datetime.utcnow().isoformat(),
                "source_url": source_url
            }
        }
    
    def _classify_by_keywords(self, text_content: str) -> Dict[str, Any]:
        """Simple keyword-based classification."""
        
        text_lower = text_content.lower()
        
        # Define keyword patterns for different categories
        categories = {
            "ecommerce": ["buy", "price", "cart", "checkout", "product", "shop", "store"],
            "news": ["breaking", "report", "today", "yesterday", "news", "article"],
            "blog": ["posted", "author", "comment", "blog", "opinion", "thoughts"],
            "corporate": ["company", "business", "services", "about us", "contact"],
            "documentation": ["guide", "tutorial", "how to", "documentation", "manual"],
            "social": ["share", "like", "follow", "comment", "social", "profile"]
        }
        
        scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[category] = score / len(keywords)
        
        primary_category = max(scores, key=scores.get) if scores else "general"
        confidence = scores.get(primary_category, 0.1)
        
        return {
            "primary_category": primary_category,
            "subcategories": [cat for cat, score in scores.items() if score > 0.2],
            "confidence": min(confidence, 0.8),  # Cap confidence for fallback
            "content_type": "web_content"
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result structure."""
        
        return {
            "entities": [],
            "classification": {
                "primary_category": "error",
                "confidence": 0.0,
                "error": error_message
            },
            "sentiment": {"overall": "neutral", "score": 0.0},
            "key_topics": [],
            "summary": "Analysis failed",
            "language": "unknown",
            "metadata": {
                "error": error_message,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
        }
    
    async def extract_specific_entities(
        self,
        text_content: str,
        entity_types: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Extract specific types of entities from text.
        
        Args:
            text_content: Text to analyze
            entity_types: List of entity types to extract (PERSON, ORG, etc.)
            
        Returns:
            List of extracted entities
        """
        
        entity_types_str = ", ".join(entity_types)
        prompt = f"""
        Extract only the following entity types from the text: {entity_types_str}
        
        Text: {text_content[:3000]}
        
        Return JSON array of entities:
        [
            {{
                "type": "entity_type",
                "value": "entity_value",
                "confidence": 0.95
            }}
        ]
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            entities = json.loads(response.text)
            return entities if isinstance(entities, list) else []
            
        except Exception as e:
            self.logger.error(f"Specific entity extraction failed: {e}")
            return []