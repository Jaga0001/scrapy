"""
Unit tests for AI Structure Extractor module.

Tests the StructureExtractor class with mock Gemini responses to ensure
proper structure identification and data extraction functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.structure_extractor import StructureExtractor
from src.models.pydantic_models import ContentType


class TestStructureExtractor:
    """Test cases for StructureExtractor class."""
    
    @pytest.fixture
    def mock_gemini_model(self):
        """Mock Gemini model for testing."""
        model = MagicMock()
        return model
    
    @pytest.fixture
    def structure_extractor(self, mock_gemini_model):
        """Create StructureExtractor instance with mocked model."""
        return StructureExtractor(mock_gemini_model)
    
    @pytest.mark.asyncio
    async def test_extract_html_structure_success(self, structure_extractor):
        """Test successful HTML structure extraction."""
        html_content = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Title</h1>
                <div class="product">
                    <h2>Product Name</h2>
                    <span class="price">$99.99</span>
                    <p>Product description</p>
                </div>
                <table>
                    <tr><th>Name</th><th>Value</th></tr>
                    <tr><td>Item 1</td><td>Value 1</td></tr>
                </table>
            </body>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "structured_data": {
                "products": [
                    {
                        "name": "Product Name",
                        "price": "$99.99",
                        "description": "Product description",
                        "availability": "in_stock",
                        "rating": 4.5,
                        "reviews_count": 123
                    }
                ],
                "tables": [
                    {
                        "headers": ["Name", "Value"],
                        "rows": [["Item 1", "Value 1"]],
                        "caption": ""
                    }
                ],
                "navigation": [
                    {"text": "Home", "url": "/home", "level": 1}
                ]
            },
            "metadata": {
                "page_title": "Test Page",
                "meta_description": "Test description",
                "keywords": ["test", "page"],
                "language": "en",
                "structure_complexity": "moderate",
                "data_richness": "high"
            }
        })
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await structure_extractor.extract_structure(
                content=html_content,
                content_type=ContentType.HTML,
                source_url="https://example.com"
            )
            
            assert "structured_data" in result
            assert "metadata" in result
            
            # Check products extraction
            products = result["structured_data"]["products"]
            assert len(products) == 1
            assert products[0]["name"] == "Product Name"
            assert products[0]["price"] == "$99.99"
            
            # Check tables extraction
            tables = result["structured_data"]["tables"]
            assert len(tables) == 1
            assert tables[0]["headers"] == ["Name", "Value"]
            
            # Check metadata
            assert result["metadata"]["page_title"] == "Test Page"
            assert "processing_timestamp" in result["metadata"]
            assert result["metadata"]["source_url"] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_extract_json_structure_success(self, structure_extractor):
        """Test successful JSON structure extraction."""
        json_content = json.dumps({
            "users": [
                {"id": 1, "name": "John Doe", "email": "john@example.com"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
            ],
            "metadata": {
                "total": 2,
                "page": 1
            }
        })
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "structured_data": {
                "schema_analysis": {
                    "top_level_keys": ["users", "metadata"],
                    "data_types": {"users": "array", "metadata": "object"},
                    "nested_levels": 2,
                    "array_lengths": {"users": 2}
                },
                "extracted_entities": [
                    {
                        "path": "users[0].name",
                        "type": "person_name",
                        "value": "John Doe"
                    }
                ],
                "patterns": [
                    {
                        "pattern_type": "user_data",
                        "confidence": 0.9,
                        "description": "User listing with contact information"
                    }
                ]
            },
            "metadata": {
                "json_valid": True,
                "structure_type": "api_response",
                "complexity": "moderate"
            }
        })
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await structure_extractor.extract_structure(
                content=json_content,
                content_type=ContentType.JSON,
                source_url="https://api.example.com/users"
            )
            
            assert "structured_data" in result
            assert result["structured_data"]["schema_analysis"]["top_level_keys"] == ["users", "metadata"]
            assert result["metadata"]["json_valid"] is True
            assert result["metadata"]["structure_type"] == "api_response"
    
    @pytest.mark.asyncio
    async def test_extract_text_structure_success(self, structure_extractor):
        """Test successful text structure extraction."""
        text_content = """
        Company Information
        
        Address: 123 Main St, City, State 12345
        Phone: (555) 123-4567
        Email: info@company.com
        
        Services:
        - Web Development
        - Mobile Apps
        - Consulting
        
        Founded: January 1, 2020
        """
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "structured_data": {
                "sections": [
                    {
                        "title": "Company Information",
                        "content": "Contact and service details",
                        "type": "header"
                    }
                ],
                "key_value_pairs": [
                    {"key": "Address", "value": "123 Main St, City, State 12345"},
                    {"key": "Phone", "value": "(555) 123-4567"},
                    {"key": "Email", "value": "info@company.com"}
                ],
                "lists": [
                    {
                        "type": "unordered",
                        "items": ["Web Development", "Mobile Apps", "Consulting"]
                    }
                ],
                "dates_times": [
                    {
                        "raw_text": "January 1, 2020",
                        "parsed_date": "2020-01-01",
                        "type": "founding_date"
                    }
                ]
            },
            "metadata": {
                "text_structure": "structured",
                "information_density": "high"
            }
        })
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await structure_extractor.extract_structure(
                content=text_content,
                content_type=ContentType.TEXT,
                source_url="https://example.com/about"
            )
            
            assert "structured_data" in result
            
            # Check key-value pairs
            kv_pairs = result["structured_data"]["key_value_pairs"]
            assert len(kv_pairs) == 3
            assert any(pair["key"] == "Address" for pair in kv_pairs)
            
            # Check lists
            lists = result["structured_data"]["lists"]
            assert len(lists) == 1
            assert lists[0]["type"] == "unordered"
            assert "Web Development" in lists[0]["items"]
    
    @pytest.mark.asyncio
    async def test_fallback_html_extraction(self, structure_extractor):
        """Test fallback HTML extraction using BeautifulSoup."""
        html_content = """
        <html>
            <head><title>Fallback Test</title></head>
            <body>
                <a href="/home">Home</a>
                <a href="/about">About</a>
                <form action="/submit" method="POST">
                    <input type="text" name="username" required>
                    <input type="email" name="email">
                    <button type="submit">Submit</button>
                </form>
                <table>
                    <caption>Data Table</caption>
                    <tr><th>Col1</th><th>Col2</th></tr>
                    <tr><td>Data1</td><td>Data2</td></tr>
                </table>
                <img src="/image.jpg" alt="Test Image">
            </body>
        </html>
        """
        
        result = await structure_extractor._fallback_html_extraction(
            html_content, "https://example.com"
        )
        
        assert "structured_data" in result
        assert "metadata" in result
        
        # Check navigation extraction
        navigation = result["structured_data"]["navigation"]
        assert len(navigation) >= 2
        assert any(nav["text"] == "Home" for nav in navigation)
        
        # Check forms extraction
        forms = result["structured_data"]["forms"]
        assert len(forms) == 1
        assert forms[0]["action"] == "/submit"
        assert forms[0]["method"] == "POST"
        assert len(forms[0]["fields"]) >= 2
        
        # Check tables extraction
        tables = result["structured_data"]["tables"]
        assert len(tables) == 1
        assert tables[0]["caption"] == "Data Table"
        assert tables[0]["headers"] == ["Col1", "Col2"]
        
        # Check media extraction
        media = result["structured_data"]["media"]
        assert len(media) >= 1
        assert media[0]["type"] == "image"
        assert media[0]["alt"] == "Test Image"
        
        # Check metadata
        assert result["metadata"]["page_title"] == "Fallback Test"
        assert result["metadata"]["extraction_method"] == "fallback_beautifulsoup"
    
    @pytest.mark.asyncio
    async def test_fallback_text_extraction(self, structure_extractor):
        """Test fallback text structure extraction using regex."""
        text_content = """
        MAIN HEADING
        
        Contact Information:
        Name: John Doe
        Email: john@example.com
        Phone: 555-123-4567
        
        Important Dates:
        Start Date: 01/15/2024
        End Date: 12/31/2024
        Meeting: March 15, 2024
        """
        
        result = await structure_extractor._fallback_text_extraction(
            text_content, "https://example.com"
        )
        
        assert "structured_data" in result
        
        # Check sections (headers)
        sections = result["structured_data"]["sections"]
        assert len(sections) > 0
        assert any("MAIN HEADING" in section["title"] for section in sections)
        
        # Check key-value pairs
        kv_pairs = result["structured_data"]["key_value_pairs"]
        assert len(kv_pairs) > 0
        assert any(pair["key"] == "Name" and pair["value"] == "John Doe" for pair in kv_pairs)
        
        # Check dates extraction
        dates = result["structured_data"]["dates_times"]
        assert len(dates) > 0
        
        assert result["metadata"]["extraction_method"] == "fallback_regex"
    
    @pytest.mark.asyncio
    async def test_invalid_json_content(self, structure_extractor):
        """Test handling of invalid JSON content."""
        invalid_json = "{ invalid json content"
        
        result = await structure_extractor.extract_structure(
            content=invalid_json,
            content_type=ContentType.JSON,
            source_url="https://example.com"
        )
        
        assert "structured_data" in result
        assert "metadata" in result
        assert "error" in result["metadata"]
        assert "Invalid JSON" in result["metadata"]["error"]
    
    @pytest.mark.asyncio
    async def test_gemini_json_parse_error(self, structure_extractor):
        """Test handling of Gemini JSON parse errors."""
        mock_response = MagicMock()
        mock_response.text = "Invalid JSON response from Gemini"
        
        with patch('asyncio.to_thread', return_value=mock_response):
            with patch.object(structure_extractor, '_fallback_html_extraction') as mock_fallback:
                mock_fallback.return_value = {"structured_data": {}, "metadata": {}}
                
                result = await structure_extractor.extract_structure(
                    content="<html><body>Test</body></html>",
                    content_type=ContentType.HTML,
                    source_url="https://example.com"
                )
                
                mock_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_specific_structure(self, structure_extractor):
        """Test extraction of specific structure types."""
        with patch.object(structure_extractor, 'extract_structure') as mock_extract:
            mock_extract.return_value = {"structured_data": {"products": []}, "metadata": {}}
            
            result = await structure_extractor.extract_specific_structure(
                content="<html><body>Product page</body></html>",
                structure_type="products",
                content_type=ContentType.HTML
            )
            
            mock_extract.assert_called_once_with(
                content="<html><body>Product page</body></html>",
                content_type=ContentType.HTML,
                source_url="",
                extraction_focus="products"
            )
    
    @pytest.mark.asyncio
    async def test_gemini_api_error_handling(self, structure_extractor):
        """Test handling of Gemini API errors."""
        with patch('asyncio.to_thread', side_effect=Exception("Gemini API Error")):
            result = await structure_extractor.extract_structure(
                content="<html><body>Test</body></html>",
                content_type=ContentType.HTML,
                source_url="https://example.com"
            )
            
            # Should return error result
            assert "metadata" in result
            assert "error" in result["metadata"]
            assert "Gemini API Error" in result["metadata"]["error"]
    
    def test_create_error_result(self, structure_extractor):
        """Test error result creation."""
        error_message = "Test error message"
        result = structure_extractor._create_error_result(error_message)
        
        assert result["structured_data"] == {}
        assert result["metadata"]["error"] == error_message
        assert result["metadata"]["extraction_method"] == "error"
        assert "processing_timestamp" in result["metadata"]
    
    @pytest.mark.asyncio
    async def test_extract_generic_structure(self, structure_extractor):
        """Test generic structure extraction for unknown content types."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "structured_data": {
                "identified_patterns": [
                    {
                        "pattern_type": "key_value_data",
                        "data": {"key1": "value1", "key2": "value2"},
                        "confidence": 0.8
                    }
                ]
            },
            "metadata": {
                "content_type_guess": "configuration",
                "structure_found": True
            }
        })
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await structure_extractor._extract_generic_structure(
                content="key1=value1\nkey2=value2",
                source_url="https://example.com"
            )
            
            assert "structured_data" in result
            patterns = result["structured_data"]["identified_patterns"]
            assert len(patterns) == 1
            assert patterns[0]["pattern_type"] == "key_value_data"
            assert result["metadata"]["content_type_guess"] == "configuration"