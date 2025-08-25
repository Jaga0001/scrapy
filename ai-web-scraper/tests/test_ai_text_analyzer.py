"""
Unit tests for AI Text Analyzer module.

Tests the TextAnalyzer class with mock Gemini responses to ensure
proper text analysis and entity extraction functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.text_analyzer import TextAnalyzer


class TestTextAnalyzer:
    """Test cases for TextAnalyzer class."""
    
    @pytest.fixture
    def mock_gemini_model(self):
        """Mock Gemini model for testing."""
        model = MagicMock()
        return model
    
    @pytest.fixture
    def text_analyzer(self, mock_gemini_model):
        """Create TextAnalyzer instance with mocked model."""
        return TextAnalyzer(mock_gemini_model)
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_success(self, text_analyzer):
        """Test successful comprehensive text analysis."""
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "entities": [
                {
                    "type": "PERSON",
                    "value": "John Doe",
                    "confidence": 0.95,
                    "context": "CEO John Doe announced"
                }
            ],
            "classification": {
                "primary_category": "news",
                "subcategories": ["business", "technology"],
                "confidence": 0.90,
                "content_type": "article"
            },
            "sentiment": {
                "overall": "positive",
                "score": 0.75,
                "aspects": [
                    {"aspect": "company", "sentiment": "positive", "score": 0.8}
                ]
            },
            "key_topics": [
                {"topic": "technology", "relevance": 0.85, "keywords": ["AI", "innovation"]}
            ],
            "summary": "Article about technology innovation",
            "language": "en",
            "metadata": {
                "word_count": 150,
                "reading_level": "intermediate",
                "content_quality": "high"
            }
        })
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await text_analyzer.analyze_text(
                text_content="CEO John Doe announced new AI innovation...",
                source_url="https://example.com/news"
            )
            
            assert "entities" in result
            assert len(result["entities"]) == 1
            assert result["entities"][0]["type"] == "PERSON"
            assert result["entities"][0]["value"] == "John Doe"
            
            assert "classification" in result
            assert result["classification"]["primary_category"] == "news"
            assert result["classification"]["confidence"] == 0.90
            
            assert "sentiment" in result
            assert result["sentiment"]["overall"] == "positive"
            
            assert "metadata" in result
            assert "processing_timestamp" in result["metadata"]
            assert result["metadata"]["source_url"] == "https://example.com/news"
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_json_parse_error(self, text_analyzer):
        """Test handling of JSON parse errors in comprehensive analysis."""
        # Mock Gemini response with invalid JSON
        mock_response = MagicMock()
        mock_response.text = "Invalid JSON response"
        
        with patch('asyncio.to_thread', return_value=mock_response):
            with patch.object(text_analyzer, '_fallback_analysis') as mock_fallback:
                mock_fallback.return_value = {"entities": [], "classification": {}}
                
                result = await text_analyzer.analyze_text(
                    text_content="Test content",
                    source_url="https://example.com"
                )
                
                mock_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_entities_only(self, text_analyzer):
        """Test entity-only extraction."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "entities": [
                {
                    "type": "EMAIL",
                    "value": "john@example.com",
                    "confidence": 0.95,
                    "start_pos": 10,
                    "end_pos": 25
                },
                {
                    "type": "PHONE",
                    "value": "555-123-4567",
                    "confidence": 0.90,
                    "start_pos": 30,
                    "end_pos": 42
                }
            ]
        })
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await text_analyzer.analyze_text(
                text_content="Contact John at john@example.com or 555-123-4567",
                source_url="https://example.com",
                analysis_type="entities_only"
            )
            
            assert "entities" in result
            assert len(result["entities"]) == 2
            assert result["entities"][0]["type"] == "EMAIL"
            assert result["entities"][1]["type"] == "PHONE"
            assert result["metadata"]["analysis_type"] == "entities_only"
    
    @pytest.mark.asyncio
    async def test_classify_content_only(self, text_analyzer):
        """Test content classification only."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "classification": {
                "primary_category": "ecommerce",
                "subcategories": ["electronics", "consumer"],
                "confidence": 0.88,
                "content_type": "product",
                "industry": "technology",
                "target_audience": "consumer"
            }
        })
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await text_analyzer.analyze_text(
                text_content="Buy the latest smartphone with advanced features...",
                source_url="https://shop.example.com",
                analysis_type="classification_only"
            )
            
            assert "classification" in result
            assert result["classification"]["primary_category"] == "ecommerce"
            assert result["classification"]["content_type"] == "product"
            assert result["metadata"]["analysis_type"] == "classification_only"
    
    @pytest.mark.asyncio
    async def test_fallback_analysis(self, text_analyzer):
        """Test fallback analysis using basic NLP techniques."""
        text_content = """
        Contact Information:
        Email: support@example.com
        Phone: (555) 123-4567
        Website: https://example.com
        
        This is a technology company specializing in AI solutions.
        """
        
        result = await text_analyzer._fallback_analysis(text_content, "https://example.com")
        
        assert "entities" in result
        assert "classification" in result
        assert "metadata" in result
        
        # Check that email was extracted
        email_entities = [e for e in result["entities"] if e["type"] == "EMAIL"]
        assert len(email_entities) > 0
        assert "support@example.com" in [e["value"] for e in email_entities]
        
        # Check that URL was extracted
        url_entities = [e for e in result["entities"] if e["type"] == "URL"]
        assert len(url_entities) > 0
        
        # Check classification
        assert result["classification"]["primary_category"] in [
            "corporate", "technology", "general"
        ]
        
        assert result["metadata"]["processing_method"] == "fallback"
    
    @pytest.mark.asyncio
    async def test_extract_specific_entities(self, text_analyzer):
        """Test extraction of specific entity types."""
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {"type": "PERSON", "value": "Alice Smith", "confidence": 0.9},
            {"type": "PERSON", "value": "Bob Johnson", "confidence": 0.85}
        ])
        
        with patch('asyncio.to_thread', return_value=mock_response):
            entities = await text_analyzer.extract_specific_entities(
                text_content="Alice Smith and Bob Johnson are colleagues",
                entity_types=["PERSON"]
            )
            
            assert len(entities) == 2
            assert all(entity["type"] == "PERSON" for entity in entities)
            assert "Alice Smith" in [e["value"] for e in entities]
            assert "Bob Johnson" in [e["value"] for e in entities]
    
    @pytest.mark.asyncio
    async def test_extract_specific_entities_error(self, text_analyzer):
        """Test handling of errors in specific entity extraction."""
        with patch('asyncio.to_thread', side_effect=Exception("API Error")):
            entities = await text_analyzer.extract_specific_entities(
                text_content="Test content",
                entity_types=["PERSON"]
            )
            
            assert entities == []
    
    def test_classify_by_keywords(self, text_analyzer):
        """Test keyword-based classification."""
        # Test ecommerce content
        ecommerce_text = "Buy now! Add to cart. Checkout with PayPal. Great prices on products."
        result = text_analyzer._classify_by_keywords(ecommerce_text)
        assert result["primary_category"] == "ecommerce"
        
        # Test news content
        news_text = "Breaking news today: Major report reveals new findings in yesterday's article."
        result = text_analyzer._classify_by_keywords(news_text)
        assert result["primary_category"] == "news"
        
        # Test corporate content
        corporate_text = "Our company provides business services. Contact us about our solutions."
        result = text_analyzer._classify_by_keywords(corporate_text)
        assert result["primary_category"] == "corporate"
    
    def test_create_error_result(self, text_analyzer):
        """Test error result creation."""
        error_message = "Test error message"
        result = text_analyzer._create_error_result(error_message)
        
        assert result["entities"] == []
        assert result["classification"]["primary_category"] == "error"
        assert result["classification"]["confidence"] == 0.0
        assert result["classification"]["error"] == error_message
        assert result["sentiment"]["overall"] == "neutral"
        assert result["metadata"]["error"] == error_message
    
    @pytest.mark.asyncio
    async def test_invalid_analysis_type(self, text_analyzer):
        """Test handling of invalid analysis type."""
        with pytest.raises(ValueError, match="Unknown analysis type"):
            await text_analyzer.analyze_text(
                text_content="Test content",
                source_url="https://example.com",
                analysis_type="invalid_type"
            )
    
    @pytest.mark.asyncio
    async def test_gemini_api_error_handling(self, text_analyzer):
        """Test handling of Gemini API errors."""
        with patch('asyncio.to_thread', side_effect=Exception("Gemini API Error")):
            result = await text_analyzer.analyze_text(
                text_content="Test content",
                source_url="https://example.com"
            )
            
            # Should return error result
            assert result["classification"]["primary_category"] == "error"
            assert "Gemini API Error" in result["metadata"]["error"]
    
    @pytest.mark.asyncio
    async def test_empty_gemini_response(self, text_analyzer):
        """Test handling of empty Gemini response."""
        mock_response = MagicMock()
        mock_response.text = None
        
        with patch('asyncio.to_thread', return_value=mock_response):
            with patch.object(text_analyzer, '_fallback_analysis') as mock_fallback:
                mock_fallback.return_value = {"entities": [], "classification": {}}
                
                result = await text_analyzer.analyze_text(
                    text_content="Test content",
                    source_url="https://example.com"
                )
                
                mock_fallback.assert_called_once()