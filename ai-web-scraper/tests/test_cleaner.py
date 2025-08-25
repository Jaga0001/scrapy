"""
Unit tests for the data cleaning and validation system.

This module contains comprehensive tests for the DataCleaner class,
including tests for cleaning rules, duplicate detection, data validation,
and quality assessment functionality.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from src.pipeline.cleaner import DataCleaner, DataQualityMetrics, CleaningRule
from src.models.pydantic_models import ScrapedData, ContentType


class TestDataCleaner:
    """Test suite for DataCleaner class."""
    
    @pytest.fixture
    def cleaner(self):
        """Create a DataCleaner instance for testing."""
        return DataCleaner()
    
    @pytest.fixture
    def sample_scraped_data(self) -> List[ScrapedData]:
        """Create sample scraped data for testing."""
        return [
            ScrapedData(
                id="test-1",
                job_id="job-1",
                url="https://example.com/page1",
                content={
                    "title": "Test Article 1",
                    "email": "  TEST@EXAMPLE.COM  ",
                    "phone": "(555) 123-4567",
                    "price": "$19.99",
                    "description": "This is a   test   description with   extra spaces"
                },
                content_type=ContentType.HTML,
                confidence_score=0.8
            ),
            ScrapedData(
                id="test-2",
                job_id="job-1",
                url="https://example.com/page2",
                content={
                    "title": "Test Article 2",
                    "email": "invalid-email",
                    "phone": "555.123.4567",
                    "price": "29.95",
                    "description": "Another test description"
                },
                content_type=ContentType.HTML,
                confidence_score=0.7
            ),
            ScrapedData(
                id="test-3",
                job_id="job-1",
                url="https://example.com/page3",
                content={
                    "title": "Test Article 1",  # Duplicate content
                    "email": "  TEST@EXAMPLE.COM  ",
                    "phone": "(555) 123-4567",
                    "price": "$19.99",
                    "description": "This is a   test   description with   extra spaces"
                },
                content_type=ContentType.HTML,
                confidence_score=0.8
            )
        ]
    
    @pytest.fixture
    def dirty_data_samples(self) -> List[Dict[str, Any]]:
        """Create samples of dirty data for testing cleaning rules."""
        return [
            {
                "email": "  JOHN.DOE@EXAMPLE.COM  ",
                "phone": "(555) 123-4567",
                "url": "example.com/page",
                "text": "This   has    extra     spaces",
                "price": "$1,234.56"
            },
            {
                "email": "invalid.email.format",
                "phone": "555-123-4567",
                "url": "https://valid-url.com",
                "text": "",
                "price": "Free"
            },
            {
                "email": "valid@email.com",
                "phone": "15551234567",
                "url": "//protocol-relative.com",
                "text": "Normal text content",
                "price": "€25.00"
            }
        ]
    
    def test_initialization(self, cleaner):
        """Test DataCleaner initialization."""
        assert isinstance(cleaner, DataCleaner)
        assert len(cleaner.cleaning_rules) > 0
        assert cleaner.similarity_threshold == 0.85
        assert isinstance(cleaner.content_hashes, set)
    
    def test_add_cleaning_rule(self, cleaner):
        """Test adding custom cleaning rules."""
        initial_count = len(cleaner.cleaning_rules)
        
        custom_rule = CleaningRule(
            field_name="custom_field",
            rule_type="custom_rule",
            parameters={"test": True},
            confidence_threshold=0.9
        )
        
        cleaner.add_cleaning_rule(custom_rule)
        
        assert len(cleaner.cleaning_rules) == initial_count + 1
        assert custom_rule in cleaner.cleaning_rules
    
    def test_clean_data_basic(self, cleaner, sample_scraped_data):
        """Test basic data cleaning functionality."""
        cleaned_data, metrics = cleaner.clean_data(sample_scraped_data)
        
        # Check that we got results
        assert isinstance(cleaned_data, list)
        assert isinstance(metrics, DataQualityMetrics)
        
        # Check metrics
        assert metrics.total_records == 3
        assert metrics.valid_records >= 1
        assert metrics.duplicate_records >= 1  # We have duplicate content
        
        # Check that email was normalized
        for record in cleaned_data:
            if "email" in record.content and record.content["email"] == "test@example.com":
                assert True
                break
        else:
            pytest.fail("Email normalization not applied correctly")
    
    def test_duplicate_detection(self, cleaner, sample_scraped_data):
        """Test duplicate detection functionality."""
        duplicates = cleaner.detect_duplicates(sample_scraped_data)
        
        assert isinstance(duplicates, list)
        assert len(duplicates) >= 1  # Should find at least one duplicate pair
        
        # Check duplicate structure
        for duplicate in duplicates:
            assert len(duplicate) == 3  # (id1, id2, similarity_score)
            assert isinstance(duplicate[0], str)
            assert isinstance(duplicate[1], str)
            assert 0.0 <= duplicate[2] <= 1.0
    
    def test_email_cleaning(self, cleaner):
        """Test email cleaning and validation."""
        test_cases = [
            ("  TEST@EXAMPLE.COM  ", "test@example.com", 1.0),
            ("invalid-email", "invalid-email", 0.2),
            ("user@domain.com", "user@domain.com", 1.0),
            ("", "", 0.0),
            (None, None, 0.0)
        ]
        
        for input_email, expected_output, min_confidence in test_cases:
            cleaned_email, confidence = cleaner._clean_email(input_email, {"normalize_case": True})
            assert cleaned_email == expected_output
            assert confidence >= min_confidence - 0.1  # Allow small tolerance
    
    def test_phone_cleaning(self, cleaner):
        """Test phone number cleaning and normalization."""
        test_cases = [
            ("(555) 123-4567", "5551234567", 0.8),
            ("555.123.4567", "5551234567", 0.8),
            ("15551234567", "15551234567", 1.0),
            ("invalid-phone", "invalid-phone", 0.2),
            ("", "", 0.0)
        ]
        
        for input_phone, expected_output, min_confidence in test_cases:
            cleaned_phone, confidence = cleaner._clean_phone(input_phone, {"remove_formatting": True})
            assert cleaned_phone == expected_output
            assert confidence >= min_confidence - 0.1
    
    def test_url_cleaning(self, cleaner):
        """Test URL cleaning and validation."""
        test_cases = [
            ("example.com", "https://example.com", 0.9),
            ("//example.com", "https://example.com", 0.9),
            ("https://valid-url.com", "https://valid-url.com", 1.0),
            ("invalid-url", "https://invalid-url", 0.4),
            ("", "", 0.0)
        ]
        
        for input_url, expected_output, min_confidence in test_cases:
            cleaned_url, confidence = cleaner._clean_url(input_url, {"normalize_scheme": True})
            assert cleaned_url == expected_output
            assert confidence >= min_confidence - 0.1
    
    def test_text_cleaning(self, cleaner):
        """Test text cleaning and normalization."""
        test_cases = [
            ("This   has    extra     spaces", "This has extra spaces", 0.8),
            ("  Leading and trailing spaces  ", "Leading and trailing spaces", 0.8),
            ("Normal text", "Normal text", 0.9),
            ("", "", 0.0),
            ("Hi", "Hi", 0.5)  # Short text gets lower confidence
        ]
        
        for input_text, expected_output, min_confidence in test_cases:
            cleaned_text, confidence = cleaner._clean_text(input_text, {"remove_extra_whitespace": True})
            assert cleaned_text == expected_output
            assert confidence >= min_confidence - 0.1
    
    def test_price_cleaning(self, cleaner):
        """Test price cleaning and normalization."""
        test_cases = [
            ("$19.99", "$19.99", 0.8),
            ("1,234.56", "$1234.56", 0.8),
            ("Free", "Free", 0.1),
            ("", "", 0.0)
        ]
        
        for input_price, expected_output, min_confidence in test_cases:
            cleaned_price, confidence = cleaner._clean_price(
                input_price, 
                {"currency_symbol": "$", "decimal_places": 2}
            )
            assert cleaned_price == expected_output
            assert confidence >= min_confidence - 0.1
    
    def test_content_hash_generation(self, cleaner):
        """Test content hash generation for duplicate detection."""
        content1 = {"title": "Test", "description": "Content"}
        content2 = {"title": "Test", "description": "Content"}
        content3 = {"title": "Different", "description": "Content"}
        
        hash1 = cleaner._generate_content_hash(content1)
        hash2 = cleaner._generate_content_hash(content2)
        hash3 = cleaner._generate_content_hash(content3)
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != hash3  # Different content should have different hash
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hash length
    
    def test_content_similarity_calculation(self, cleaner):
        """Test content similarity calculation."""
        content1 = {"title": "Test Article", "description": "This is a test"}
        content2 = {"title": "Test Article", "description": "This is a test"}
        content3 = {"title": "Different Article", "description": "Completely different content"}
        
        similarity_identical = cleaner._calculate_content_similarity(content1, content2)
        similarity_different = cleaner._calculate_content_similarity(content1, content3)
        
        assert similarity_identical == 1.0
        assert similarity_different < 0.5
        assert 0.0 <= similarity_different <= 1.0
    
    def test_data_type_validation(self, cleaner):
        """Test data type validation functionality."""
        valid_content = {
            "string_field": "text",
            "int_field": 123,
            "float_field": 45.67,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"key": "value"}
        }
        
        invalid_content = {
            "valid_field": "text",
            "none_field": None
        }
        
        validation_errors = []
        
        valid_score = cleaner._validate_data_types(valid_content, validation_errors)
        assert valid_score == 1.0
        assert len(validation_errors) == 0
        
        validation_errors = []
        invalid_score = cleaner._validate_data_types(invalid_content, validation_errors)
        assert 0.0 <= invalid_score <= 1.0
    
    def test_quality_metrics_calculation(self, cleaner, sample_scraped_data):
        """Test quality metrics calculation."""
        cleaned_data, metrics = cleaner.clean_data(sample_scraped_data)
        
        # Check that all required metrics are calculated
        assert hasattr(metrics, 'total_records')
        assert hasattr(metrics, 'valid_records')
        assert hasattr(metrics, 'invalid_records')
        assert hasattr(metrics, 'duplicate_records')
        assert hasattr(metrics, 'overall_quality_score')
        assert hasattr(metrics, 'completeness_score')
        assert hasattr(metrics, 'accuracy_score')
        assert hasattr(metrics, 'consistency_score')
        
        # Check score ranges
        assert 0.0 <= metrics.overall_quality_score <= 1.0
        assert 0.0 <= metrics.completeness_score <= 1.0
        assert 0.0 <= metrics.accuracy_score <= 1.0
        assert 0.0 <= metrics.consistency_score <= 1.0
        
        # Check record counts
        assert metrics.total_records == len(sample_scraped_data)
        assert metrics.valid_records + metrics.invalid_records <= metrics.total_records
    
    def test_quality_report_generation(self, cleaner, sample_scraped_data):
        """Test quality report generation."""
        cleaned_data, metrics = cleaner.clean_data(sample_scraped_data)
        report = cleaner.generate_quality_report(metrics)
        
        # Check report structure
        assert "summary" in report
        assert "quality_scores" in report
        assert "field_quality" in report
        assert "validation_errors" in report
        assert "recommendations" in report
        
        # Check summary section
        summary = report["summary"]
        assert "total_records" in summary
        assert "valid_records" in summary
        assert "processing_time" in summary
        
        # Check quality scores section
        quality_scores = report["quality_scores"]
        assert "overall_quality" in quality_scores
        assert "completeness" in quality_scores
        assert "accuracy" in quality_scores
        assert "consistency" in quality_scores
    
    def test_recommendations_generation(self, cleaner):
        """Test recommendation generation based on quality metrics."""
        # Test low quality metrics
        low_quality_metrics = DataQualityMetrics(
            total_records=100,
            valid_records=50,
            invalid_records=50,
            duplicate_records=20,
            completeness_score=0.5,
            accuracy_score=0.6,
            consistency_score=0.5,
            overall_quality_score=0.5
        )
        
        recommendations = cleaner._generate_recommendations(low_quality_metrics)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should recommend improvements for low scores
        recommendation_text = " ".join(recommendations).lower()
        assert any(keyword in recommendation_text for keyword in ["improve", "review", "consider"])
    
    def test_cleaning_with_empty_data(self, cleaner):
        """Test cleaning behavior with empty data."""
        empty_data = []
        cleaned_data, metrics = cleaner.clean_data(empty_data)
        
        assert cleaned_data == []
        assert metrics.total_records == 0
        assert metrics.valid_records == 0
        assert metrics.invalid_records == 0
    
    def test_cleaning_with_malformed_data(self, cleaner):
        """Test cleaning behavior with malformed data."""
        malformed_data = [
            ScrapedData(
                id="malformed-1",
                job_id="job-1",
                url="https://example.com",
                content={},  # Empty content
                content_type=ContentType.HTML,
                confidence_score=0.5
            ),
            ScrapedData(
                id="malformed-2",
                job_id="job-1",
                url="https://example.com",
                content={"field": None},  # None values
                content_type=ContentType.HTML,
                confidence_score=0.3
            )
        ]
        
        cleaned_data, metrics = cleaner.clean_data(malformed_data)
        
        # Should handle malformed data gracefully
        assert isinstance(cleaned_data, list)
        assert isinstance(metrics, DataQualityMetrics)
        assert metrics.total_records == 2
    
    @patch('src.pipeline.cleaner.get_logger')
    def test_logging_functionality(self, mock_logger, cleaner, sample_scraped_data):
        """Test that appropriate logging occurs during cleaning."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        # Create new cleaner to use mocked logger
        test_cleaner = DataCleaner()
        test_cleaner.logger = mock_logger_instance
        
        cleaned_data, metrics = test_cleaner.clean_data(sample_scraped_data)
        
        # Verify logging calls were made
        assert mock_logger_instance.info.called
        assert mock_logger_instance.debug.called or mock_logger_instance.warning.called
    
    def test_custom_cleaning_rule_application(self, cleaner):
        """Test application of custom cleaning rules."""
        # Add a custom rule
        custom_rule = CleaningRule(
            field_name="custom_field",
            rule_type="text_cleaning",
            parameters={"remove_extra_whitespace": True},
            confidence_threshold=0.8
        )
        
        cleaner.add_cleaning_rule(custom_rule)
        
        # Create test data with custom field
        test_data = [
            ScrapedData(
                id="custom-test",
                job_id="job-1",
                url="https://example.com",
                content={"custom_field": "text   with   spaces"},
                content_type=ContentType.HTML,
                confidence_score=0.8
            )
        ]
        
        cleaned_data, metrics = cleaner.clean_data(test_data)
        
        # Check that custom rule was applied
        assert len(cleaned_data) > 0
        cleaned_content = cleaned_data[0].content
        assert "custom_field" in cleaned_content
        assert cleaned_content["custom_field"] == "text with spaces"
    
    def test_performance_with_large_dataset(self, cleaner):
        """Test performance with a larger dataset."""
        # Create a larger dataset
        large_dataset = []
        for i in range(100):
            large_dataset.append(
                ScrapedData(
                    id=f"test-{i}",
                    job_id="job-1",
                    url=f"https://example.com/page{i}",
                    content={
                        "title": f"Article {i}",
                        "email": f"user{i}@example.com",
                        "description": f"Description for article {i}"
                    },
                    content_type=ContentType.HTML,
                    confidence_score=0.8
                )
            )
        
        start_time = datetime.utcnow()
        cleaned_data, metrics = cleaner.clean_data(large_dataset)
        end_time = datetime.utcnow()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Should complete in reasonable time (less than 10 seconds for 100 records)
        assert processing_time < 10.0
        assert metrics.processing_time > 0
        assert len(cleaned_data) <= len(large_dataset)


class TestCleaningRule:
    """Test suite for CleaningRule model."""
    
    def test_cleaning_rule_creation(self):
        """Test CleaningRule model creation."""
        rule = CleaningRule(
            field_name="test_field",
            rule_type="test_rule",
            parameters={"param1": "value1"},
            confidence_threshold=0.9,
            enabled=True
        )
        
        assert rule.field_name == "test_field"
        assert rule.rule_type == "test_rule"
        assert rule.parameters == {"param1": "value1"}
        assert rule.confidence_threshold == 0.9
        assert rule.enabled is True
    
    def test_cleaning_rule_defaults(self):
        """Test CleaningRule default values."""
        rule = CleaningRule(
            field_name="test_field",
            rule_type="test_rule"
        )
        
        assert rule.parameters == {}
        assert rule.confidence_threshold == 0.8
        assert rule.enabled is True


class TestDataQualityMetrics:
    """Test suite for DataQualityMetrics model."""
    
    def test_metrics_creation(self):
        """Test DataQualityMetrics model creation."""
        metrics = DataQualityMetrics(
            total_records=100,
            valid_records=90,
            invalid_records=10,
            duplicate_records=5,
            corrected_records=15,
            overall_quality_score=0.85,
            completeness_score=0.9,
            accuracy_score=0.8,
            consistency_score=0.85
        )
        
        assert metrics.total_records == 100
        assert metrics.valid_records == 90
        assert metrics.overall_quality_score == 0.85
    
    def test_metrics_validation(self):
        """Test DataQualityMetrics validation."""
        # Test that scores are within valid range
        with pytest.raises(ValueError):
            DataQualityMetrics(
                total_records=100,
                overall_quality_score=1.5  # Invalid score > 1.0
            )
        
        with pytest.raises(ValueError):
            DataQualityMetrics(
                total_records=-1  # Invalid negative count
            )


if __name__ == "__main__":
    pytest.main([__file__])