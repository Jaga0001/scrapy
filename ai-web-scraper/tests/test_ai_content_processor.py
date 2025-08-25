"""
Unit tests for AI Content Processor module.

Tests the ContentProcessor class with mock Gemini responses to ensure
proper AI processing pipeline functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.ai.content_processor import ContentProcessor, ProcessedContent
from src.models.pydantic_models import ContentType


class TestContentProcessor:
    """Test cases for ContentProcessor class."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with Gemini API key."""
        settings = MagicMock()
        settings.gemini_api_key = "test_api_key"
        return settings
    
    @pytest.fixture
    def mock_gemini_model(self):
        """Mock Gemini model for testing."""
        model = MagicMock()
        return model
    
    @pytest.fixture
    def content_processor(self, mock_settings):
        """Create ContentProcessor instance with mocked dependencies."""
        with patch('src.ai.content_processor.get_settings', return_value=mock_settings):
            with patch('src.ai.content_processor.genai') as mock_genai:
                mock_model = MagicMock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                processor = ContentProcessor()
                processor._model = mock_model
                return processor
    
    @pytest.mark.asyncio
    async def test_process_content_success(self, content_processor):
        """Test successful content processing."""
        # Mock the AI module imports and responses
        with patch('src.ai.content_processor.TextAnalyzer') as mock_text_analyzer:
            with patch('src.ai.content_processor.StructureExtractor') as mock_structure_extractor:
                with patch('src.ai.content_processor.ConfidenceScorer') as mock_confidence_scorer:
                    
                    # Setup mocks
                    mock_text_instance = AsyncMock()
                    mock_text_instance.analyze_text.return_value = {
                        "entities": [{"type": "PERSON", "value": "John Doe", "confidence": 0.9}],
                        "classification": {"category": "article", "confidence": 0.8},
                        "metadata": {"processing_time": "2024-01-01T00:00:00"}
                    }
                    mock_text_analyzer.return_value = mock_text_instance
                    
                    mock_structure_instance = AsyncMock()
                    mock_structure_instance.extract_structure.return_value = {
                        "structured_data": {"title": "Test Article", "content": "Test content"},
                        "metadata": {"extraction_method": "ai"}
                    }
                    mock_structure_extractor.return_value = mock_structure_instance
                    
                    mock_confidence_instance = AsyncMock()
                    mock_confidence_instance.calculate_confidence.return_value = 0.85
                    mock_confidence_scorer.return_value = mock_confidence_instance
                    
                    # Test processing
                    result = await content_processor.process_content(
                        raw_content="<html><body><h1>Test Article</h1><p>Test content</p></body></html>",
                        content_type=ContentType.HTML,
                        url="https://example.com"
                    )
                    
                    # Assertions
                    assert isinstance(result, ProcessedContent)
                    assert result.structured_data["title"] == "Test Article"
                    assert len(result.entities) == 1
                    assert result.entities[0]["type"] == "PERSON"
                    assert result.confidence_score == 0.85
                    assert result.classification["category"] == "article"
    
    @pytest.mark.asyncio
    async def test_process_content_fallback_no_model(self):
        """Test fallback processing when Gemini model is not available."""
        with patch('src.ai.content_processor.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.gemini_api_key = None
            mock_get_settings.return_value = mock_settings
            
            processor = ContentProcessor()
            
            result = await processor.process_content(
                raw_content="<html><body><h1>Test</h1><p>Content</p></body></html>",
                content_type=ContentType.HTML,
                url="https://example.com"
            )
            
            assert isinstance(result, ProcessedContent)
            assert result.confidence_score == 0.5  # Fallback confidence
            assert "fallback_processor" in result.processing_metadata["model_used"]
    
    @pytest.mark.asyncio
    async def test_process_content_ai_failure_fallback(self, content_processor):
        """Test fallback when AI processing fails."""
        with patch('src.ai.content_processor.TextAnalyzer') as mock_text_analyzer:
            # Make TextAnalyzer raise an exception
            mock_text_analyzer.side_effect = Exception("AI processing failed")
            
            result = await content_processor.process_content(
                raw_content="<html><body><h1>Test</h1></body></html>",
                content_type=ContentType.HTML,
                url="https://example.com"
            )
            
            assert isinstance(result, ProcessedContent)
            assert "fallback_processor" in result.processing_metadata["model_used"]
    
    @pytest.mark.asyncio
    async def test_batch_process_content(self, content_processor):
        """Test batch processing of multiple content items."""
        with patch.object(content_processor, 'process_content') as mock_process:
            # Setup mock to return different results for each item
            mock_results = [
                ProcessedContent({}, [], {}, 0.8, {}),
                ProcessedContent({}, [], {}, 0.9, {}),
                ProcessedContent({}, [], {}, 0.7, {})
            ]
            mock_process.side_effect = mock_results
            
            content_items = [
                ("content1", ContentType.HTML, "url1"),
                ("content2", ContentType.HTML, "url2"),
                ("content3", ContentType.HTML, "url3")
            ]
            
            results = await content_processor.batch_process_content(content_items)
            
            assert len(results) == 3
            assert all(isinstance(result, ProcessedContent) for result in results)
            assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_process_with_exceptions(self, content_processor):
        """Test batch processing handles exceptions gracefully."""
        with patch.object(content_processor, 'process_content') as mock_process:
            # First call succeeds, second fails, third succeeds
            mock_process.side_effect = [
                ProcessedContent({}, [], {}, 0.8, {}),
                Exception("Processing failed"),
                ProcessedContent({}, [], {}, 0.7, {})
            ]
            
            content_items = [
                ("content1", ContentType.HTML, "url1"),
                ("content2", ContentType.HTML, "url2"),
                ("content3", ContentType.HTML, "url3")
            ]
            
            results = await content_processor.batch_process_content(content_items)
            
            assert len(results) == 3
            assert results[0].confidence_score == 0.8
            assert results[1].confidence_score == 0.0  # Error result
            assert results[2].confidence_score == 0.7
    
    def test_is_available_with_model(self, content_processor):
        """Test is_available returns True when model is initialized."""
        assert content_processor.is_available() is True
    
    def test_is_available_without_model(self):
        """Test is_available returns False when model is not initialized."""
        with patch('src.ai.content_processor.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.gemini_api_key = None
            mock_get_settings.return_value = mock_settings
            
            processor = ContentProcessor()
            assert processor.is_available() is False
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, content_processor):
        """Test health check when AI is working properly."""
        # Mock successful Gemini response
        mock_response = MagicMock()
        mock_response.text = "Test response"
        
        with patch('asyncio.to_thread', return_value=mock_response):
            health_status = await content_processor.health_check()
            
            assert health_status["status"] == "healthy"
            assert health_status["model"] == "gemini-2.0-flash-exp"
            assert "timestamp" in health_status
    
    @pytest.mark.asyncio
    async def test_health_check_unavailable(self):
        """Test health check when AI is not available."""
        with patch('src.ai.content_processor.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.gemini_api_key = None
            mock_get_settings.return_value = mock_settings
            
            processor = ContentProcessor()
            health_status = await processor.health_check()
            
            assert health_status["status"] == "unavailable"
            assert health_status["reason"] == "Gemini model not initialized"
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, content_processor):
        """Test health check when AI throws an error."""
        with patch('asyncio.to_thread', side_effect=Exception("API Error")):
            health_status = await content_processor.health_check()
            
            assert health_status["status"] == "error"
            assert "API Error" in health_status["error"]


class TestProcessedContent:
    """Test cases for ProcessedContent class."""
    
    def test_processed_content_creation(self):
        """Test ProcessedContent object creation."""
        structured_data = {"title": "Test"}
        entities = [{"type": "PERSON", "value": "John"}]
        classification = {"category": "article"}
        confidence_score = 0.85
        metadata = {"model": "gemini"}
        
        content = ProcessedContent(
            structured_data=structured_data,
            entities=entities,
            classification=classification,
            confidence_score=confidence_score,
            processing_metadata=metadata
        )
        
        assert content.structured_data == structured_data
        assert content.entities == entities
        assert content.classification == classification
        assert content.confidence_score == confidence_score
        assert content.processing_metadata == metadata
        assert isinstance(content.processed_at, datetime)
    
    def test_processed_content_attributes(self):
        """Test ProcessedContent has all required attributes."""
        content = ProcessedContent({}, [], {}, 0.5, {})
        
        assert hasattr(content, 'structured_data')
        assert hasattr(content, 'entities')
        assert hasattr(content, 'classification')
        assert hasattr(content, 'confidence_score')
        assert hasattr(content, 'processing_metadata')
        assert hasattr(content, 'processed_at')