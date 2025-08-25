"""
Unit tests for AI Confidence Scorer module.

Tests the ConfidenceScorer class to ensure proper quality assessment
and confidence scoring functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.confidence_scorer import ConfidenceScorer


class TestConfidenceScorer:
    """Test cases for ConfidenceScorer class."""
    
    @pytest.fixture
    def confidence_scorer(self):
        """Create ConfidenceScorer instance."""
        return ConfidenceScorer()
    
    @pytest.fixture
    def sample_structured_data(self):
        """Sample structured data for testing."""
        return {
            "title": "Sample Article",
            "content": "This is sample content for testing purposes.",
            "author": "John Doe",
            "date": "2024-01-01",
            "tags": ["technology", "AI", "testing"],
            "links": [
                {"text": "Link 1", "url": "https://example.com/1"},
                {"text": "Link 2", "url": "https://example.com/2"}
            ],
            "metadata": {
                "word_count": 150,
                "reading_time": "2 minutes"
            }
        }
    
    @pytest.fixture
    def sample_entities(self):
        """Sample entities for testing."""
        return [
            {"type": "PERSON", "value": "John Doe", "confidence": 0.95},
            {"type": "DATE", "value": "2024-01-01", "confidence": 0.90},
            {"type": "EMAIL", "value": "john@example.com", "confidence": 0.85},
            {"type": "URL", "value": "https://example.com", "confidence": 0.92}
        ]
    
    @pytest.fixture
    def sample_classification(self):
        """Sample classification for testing."""
        return {
            "category": "article",
            "confidence": 0.88,
            "subcategory": "technology"
        }
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_high_quality(
        self, confidence_scorer, sample_structured_data, sample_entities, sample_classification
    ):
        """Test confidence calculation for high-quality data."""
        raw_content = "This is a comprehensive article about technology with detailed information and proper structure."
        
        confidence = await confidence_scorer.calculate_confidence(
            structured_data=sample_structured_data,
            entities=sample_entities,
            classification=sample_classification,
            raw_content=raw_content
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be high confidence for good data
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_low_quality(self, confidence_scorer):
        """Test confidence calculation for low-quality data."""
        poor_structured_data = {"title": ""}  # Mostly empty
        poor_entities = []  # No entities
        poor_classification = {"category": "unknown", "confidence": 0.1}
        raw_content = "Short text"
        
        confidence = await confidence_scorer.calculate_confidence(
            structured_data=poor_structured_data,
            entities=poor_entities,
            classification=poor_classification,
            raw_content=raw_content
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.5  # Should be low confidence for poor data
    
    def test_calculate_completeness_score_high(
        self, confidence_scorer, sample_structured_data, sample_entities
    ):
        """Test completeness score calculation for complete data."""
        raw_content = "This is a comprehensive article with lots of content and information."
        
        score = confidence_scorer._calculate_completeness_score(
            sample_structured_data, sample_entities, raw_content
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be good completeness
    
    def test_calculate_completeness_score_low(self, confidence_scorer):
        """Test completeness score calculation for incomplete data."""
        incomplete_data = {"title": "", "content": ""}  # Empty values
        no_entities = []
        short_content = "Short"
        
        score = confidence_scorer._calculate_completeness_score(
            incomplete_data, no_entities, short_content
        )
        
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low completeness
    
    def test_calculate_consistency_score_high(
        self, confidence_scorer, sample_structured_data, sample_entities, sample_classification
    ):
        """Test consistency score calculation for consistent data."""
        score = confidence_scorer._calculate_consistency_score(
            sample_structured_data, sample_entities, sample_classification
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.6  # Should be good consistency
    
    def test_calculate_consistency_score_low(self, confidence_scorer):
        """Test consistency score calculation for inconsistent data."""
        inconsistent_entities = [
            {"type": "PERSON", "value": "John", "confidence": 0.1},
            {"type": "PERSON", "value": "Jane", "confidence": 0.9},
            {"type": "DATE", "value": "invalid", "confidence": 0.2}
        ]
        low_classification = {"category": "unknown", "confidence": 0.1}
        
        score = confidence_scorer._calculate_consistency_score(
            {}, inconsistent_entities, low_classification
        )
        
        assert 0.0 <= score <= 1.0
    
    def test_calculate_entity_confidence_score_high(self, confidence_scorer, sample_entities):
        """Test entity confidence score calculation for high-confidence entities."""
        score = confidence_scorer._calculate_entity_confidence_score(sample_entities)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Should be high since all entities have good confidence
    
    def test_calculate_entity_confidence_score_empty(self, confidence_scorer):
        """Test entity confidence score calculation for no entities."""
        score = confidence_scorer._calculate_entity_confidence_score([])
        
        assert score == 0.0
    
    def test_calculate_structure_quality_score_good(
        self, confidence_scorer, sample_structured_data
    ):
        """Test structure quality score for well-structured data."""
        score = confidence_scorer._calculate_structure_quality_score(sample_structured_data)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be good quality
    
    def test_calculate_structure_quality_score_empty(self, confidence_scorer):
        """Test structure quality score for empty data."""
        score = confidence_scorer._calculate_structure_quality_score({})
        
        assert score == 0.0
    
    def test_calculate_content_richness_score_rich(
        self, confidence_scorer, sample_structured_data, sample_entities
    ):
        """Test content richness score for rich content."""
        rich_content = "This is a very comprehensive article with lots of detailed information, " * 10
        
        score = confidence_scorer._calculate_content_richness_score(
            sample_structured_data, sample_entities, rich_content
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.4  # Should be good richness
    
    def test_calculate_content_richness_score_poor(self, confidence_scorer):
        """Test content richness score for poor content."""
        poor_data = {"title": "Short"}
        no_entities = []
        short_content = "Short"
        
        score = confidence_scorer._calculate_content_richness_score(
            poor_data, no_entities, short_content
        )
        
        assert 0.0 <= score <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_validation_score_valid_data(self, confidence_scorer):
        """Test validation score for valid data."""
        valid_entities = [
            {"type": "EMAIL", "value": "valid@example.com"},
            {"type": "URL", "value": "https://example.com"},
            {"type": "PHONE", "value": "555-123-4567"}
        ]
        valid_data = {"date": "2024-01-01", "price": "$99.99"}
        
        score = await confidence_scorer._calculate_validation_score(
            valid_data, valid_entities, "sample content"
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # Should be high for valid data
    
    @pytest.mark.asyncio
    async def test_calculate_validation_score_invalid_data(self, confidence_scorer):
        """Test validation score for invalid data."""
        invalid_entities = [
            {"type": "EMAIL", "value": "invalid-email"},
            {"type": "URL", "value": "not-a-url"},
            {"type": "PHONE", "value": "abc"}
        ]
        
        score = await confidence_scorer._calculate_validation_score(
            {}, invalid_entities, "sample content"
        )
        
        assert 0.0 <= score <= 1.0
    
    def test_validate_email_valid(self, confidence_scorer):
        """Test email validation for valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for email in valid_emails:
            assert confidence_scorer._validate_email(email) is True
    
    def test_validate_email_invalid(self, confidence_scorer):
        """Test email validation for invalid emails."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user.example.com"
        ]
        
        for email in invalid_emails:
            assert confidence_scorer._validate_email(email) is False
    
    def test_validate_url_valid(self, confidence_scorer):
        """Test URL validation for valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "ftp://files.example.com"
        ]
        
        for url in valid_urls:
            assert confidence_scorer._validate_url(url) is True
    
    def test_validate_url_invalid(self, confidence_scorer):
        """Test URL validation for invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "example.com",  # Missing protocol
            "https://",  # Incomplete
            "file:///local/path"  # Not supported protocol
        ]
        
        for url in invalid_urls:
            assert confidence_scorer._validate_url(url) is False
    
    def test_validate_phone_valid(self, confidence_scorer):
        """Test phone validation for valid phone numbers."""
        valid_phones = [
            "555-123-4567",
            "(555) 123-4567",
            "+1-555-123-4567",
            "5551234567",
            "+44 20 7946 0958"
        ]
        
        for phone in valid_phones:
            assert confidence_scorer._validate_phone(phone) is True
    
    def test_validate_phone_invalid(self, confidence_scorer):
        """Test phone validation for invalid phone numbers."""
        invalid_phones = [
            "123",  # Too short
            "abc-def-ghij",  # Not numeric
            "123456789012345678",  # Too long
            ""  # Empty
        ]
        
        for phone in invalid_phones:
            assert confidence_scorer._validate_phone(phone) is False
    
    def test_check_data_type_consistency_good(self, confidence_scorer):
        """Test data type consistency check for consistent data."""
        consistent_data = {
            "items": [{"name": "item1"}, {"name": "item2"}],  # Consistent array
            "date": "2024-01-01",  # Looks like date
            "price": "$99.99",  # Looks like price
            "count": 5
        }
        
        score = confidence_scorer._check_data_type_consistency(consistent_data)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be good consistency
    
    def test_check_data_type_consistency_poor(self, confidence_scorer):
        """Test data type consistency check for inconsistent data."""
        inconsistent_data = {
            "items": [{"name": "item1"}, "string_item", 123],  # Inconsistent array
            "date": "not-a-date",  # Doesn't look like date
            "price": "not-a-price"  # Doesn't look like price
        }
        
        score = confidence_scorer._check_data_type_consistency(inconsistent_data)
        
        assert 0.0 <= score <= 1.0
    
    def test_calculate_data_depth(self, confidence_scorer):
        """Test data depth calculation."""
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "deep_value"
                    }
                }
            },
            "simple": "value"
        }
        
        depth = confidence_scorer._calculate_data_depth(nested_data)
        assert depth == 4  # Should find the deepest nesting
    
    def test_looks_like_date_valid(self, confidence_scorer):
        """Test date pattern recognition for valid dates."""
        valid_dates = [
            "2024-01-01",
            "01/15/2024",
            "January 15, 2024",
            "Jan 15 2024"
        ]
        
        for date in valid_dates:
            assert confidence_scorer._looks_like_date(date) is True
    
    def test_looks_like_date_invalid(self, confidence_scorer):
        """Test date pattern recognition for invalid dates."""
        invalid_dates = [
            "not-a-date",
            "random text",
            "123456",
            ""
        ]
        
        for date in invalid_dates:
            assert confidence_scorer._looks_like_date(date) is False
    
    def test_looks_like_price_valid(self, confidence_scorer):
        """Test price pattern recognition for valid prices."""
        valid_prices = [
            "$99.99",
            "99.99 USD",
            "£50.00",
            "€75.50",
            "123.45"
        ]
        
        for price in valid_prices:
            assert confidence_scorer._looks_like_price(price) is True
    
    def test_looks_like_price_invalid(self, confidence_scorer):
        """Test price pattern recognition for invalid prices."""
        invalid_prices = [
            "not-a-price",
            "free",
            "abc",
            ""
        ]
        
        for price in invalid_prices:
            assert confidence_scorer._looks_like_price(price) is False
    
    def test_get_detailed_score_breakdown(
        self, confidence_scorer, sample_structured_data, sample_entities, sample_classification
    ):
        """Test detailed score breakdown functionality."""
        raw_content = "Sample content for testing detailed breakdown."
        
        breakdown = confidence_scorer.get_detailed_score_breakdown(
            sample_structured_data, sample_entities, sample_classification, raw_content
        )
        
        expected_keys = [
            "completeness", "consistency", "entity_confidence",
            "structure_quality", "content_richness"
        ]
        
        for key in expected_keys:
            assert key in breakdown
            assert 0.0 <= breakdown[key] <= 1.0
    
    @pytest.mark.asyncio
    async def test_confidence_calculation_error_handling(self, confidence_scorer):
        """Test error handling in confidence calculation."""
        # Test with invalid data that might cause errors
        with patch.object(confidence_scorer, '_calculate_completeness_score', side_effect=Exception("Test error")):
            confidence = await confidence_scorer.calculate_confidence(
                structured_data={},
                entities=[],
                classification={},
                raw_content=""
            )
            
            assert confidence == 0.0  # Should return 0 on error
    
    def test_apply_additional_factors(self, confidence_scorer):
        """Test application of additional scoring factors."""
        original_weights = confidence_scorer.weights.copy()
        
        additional_factors = {
            "processing_time": 35,  # Slow processing
            "source_reliability": 0.9  # High reliability
        }
        
        confidence_scorer._apply_additional_factors(additional_factors)
        
        # Weights should be modified
        assert confidence_scorer.weights != original_weights