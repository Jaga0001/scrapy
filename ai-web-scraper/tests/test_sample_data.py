"""
Tests for sample data validation and schema consistency.
"""

import pytest
import json
from datetime import datetime
from uuid import uuid4

from src.models.pydantic_models import (
    ScrapingConfig, ScrapingJob, ScrapedData, ScrapingResult,
    JobStatus, ContentType
)


class TestSampleDataValidation:
    """Test sample data creation and validation."""
    
    def test_create_valid_sample_job(self):
        """Test creating a valid sample scraping job."""
        config = ScrapingConfig(
            name="Sample E-commerce Scraper",
            max_pages=25,
            wait_time=3,
            extract_images=True,
            extract_links=True,
            custom_selectors={
                "product_title": "h1.product-title",
                "price": ".price-current",
                "description": ".product-description",
                "rating": ".rating-stars",
                "availability": ".stock-status"
            },
            exclude_selectors=[".advertisement", ".related-products"]
        )
        
        job = ScrapingJob(
            url="https://example-store.com/products",
            config=config,
            status=JobStatus.PENDING,
            total_pages=25,
            user_id="sample_user_123",
            tags=["ecommerce", "products", "sample"],
            priority=3
        )
        
        # Validate job creation
        assert job.url == "https://example-store.com/products"
        assert job.config.name == "Sample E-commerce Scraper"
        assert job.config.max_pages == 25
        assert len(job.config.custom_selectors) == 5
        assert "product_title" in job.config.custom_selectors
        assert job.status == JobStatus.PENDING
        assert "ecommerce" in job.tags
    
    def test_create_sample_news_scraping_data(self):
        """Test creating sample news article scraping data."""
        sample_content = {
            "title": "Breaking: AI Technology Advances in Web Scraping",
            "text": "Recent developments in artificial intelligence have revolutionized web scraping capabilities. Modern AI systems can now understand context, extract meaningful information, and provide quality assessments of scraped content. This advancement enables more accurate data collection and reduces the need for manual validation.",
            "headings": [
                {"level": 1, "text": "Breaking: AI Technology Advances in Web Scraping", "id": "main-title", "class": ["headline"]},
                {"level": 2, "text": "Key Developments", "id": "key-dev", "class": ["subheading"]},
                {"level": 2, "text": "Industry Impact", "id": "impact", "class": ["subheading"]}
            ],
            "paragraphs": [
                "Recent developments in artificial intelligence have revolutionized web scraping capabilities.",
                "Modern AI systems can now understand context, extract meaningful information, and provide quality assessments.",
                "This advancement enables more accurate data collection and reduces manual validation needs."
            ],
            "lists": [
                {
                    "type": "ul",
                    "items": [
                        "Improved content understanding",
                        "Automated quality assessment",
                        "Reduced manual intervention",
                        "Better data accuracy"
                    ]
                }
            ],
            "metadata": {
                "author": "Tech Reporter",
                "publish_date": "2024-01-15",
                "category": "Technology",
                "word_count": 156
            }
        }
        
        scraped_data = ScrapedData(
            job_id=str(uuid4()),
            url="https://tech-news.com/ai-web-scraping-advances",
            content=sample_content,
            content_type=ContentType.HTML,
            content_metadata={
                "page_load_time": 2.3,
                "response_code": 200,
                "content_encoding": "utf-8",
                "last_modified": "2024-01-15T10:30:00Z"
            },
            confidence_score=0.92,
            ai_processed=True,
            ai_metadata={
                "summary": "Article discusses recent AI advances in web scraping technology and their industry impact.",
                "topics": ["artificial intelligence", "web scraping", "technology", "automation"],
                "quality_score": 0.88,
                "content_category": "news",
                "language": "en",
                "readability_score": 0.75,
                "key_info": [
                    "AI revolutionizes web scraping",
                    "Context understanding improved",
                    "Quality assessment automated",
                    "Manual validation reduced"
                ]
            },
            data_quality_score=0.90,
            validation_errors=[],
            content_length=len(sample_content["text"]),
            load_time=2.3
        )
        
        # Validate scraped data
        assert scraped_data.content["title"] == "Breaking: AI Technology Advances in Web Scraping"
        assert len(scraped_data.content["paragraphs"]) == 3
        assert len(scraped_data.content["headings"]) == 3
        assert scraped_data.confidence_score == 0.92
        assert scraped_data.ai_processed is True
        assert "artificial intelligence" in scraped_data.ai_metadata["topics"]
        assert scraped_data.data_quality_score == 0.90
        assert len(scraped_data.validation_errors) == 0
    
    def test_create_sample_product_data(self):
        """Test creating sample e-commerce product data."""
        product_content = {
            "title": "Premium Wireless Headphones - Noise Cancelling",
            "text": "Experience superior sound quality with our premium wireless headphones featuring active noise cancellation technology. Perfect for music lovers and professionals who demand the best audio experience.",
            "custom_fields": {
                "price": "$299.99",
                "original_price": "$399.99",
                "discount": "25% OFF",
                "rating": "4.8/5",
                "review_count": "2,847 reviews",
                "availability": "In Stock",
                "brand": "AudioTech Pro",
                "model": "AT-WH-1000XM5",
                "color_options": ["Black", "Silver", "Blue"],
                "features": [
                    "Active Noise Cancellation",
                    "30-hour battery life",
                    "Quick charge (3 min = 3 hours)",
                    "Premium comfort design",
                    "Multi-device connectivity"
                ]
            },
            "specifications": {
                "driver_size": "40mm",
                "frequency_response": "4Hz-40kHz",
                "impedance": "16 ohms",
                "weight": "254g",
                "connectivity": "Bluetooth 5.2, USB-C, 3.5mm"
            }
        }
        
        scraped_data = ScrapedData(
            job_id=str(uuid4()),
            url="https://electronics-store.com/headphones/premium-wireless-at-wh-1000xm5",
            content=product_content,
            content_type=ContentType.HTML,
            confidence_score=0.95,
            ai_processed=True,
            ai_metadata={
                "summary": "Premium wireless headphones with noise cancellation, 30-hour battery, priced at $299.99",
                "topics": ["electronics", "headphones", "audio", "wireless", "noise cancellation"],
                "quality_score": 0.93,
                "content_category": "product",
                "language": "en",
                "key_info": [
                    "Premium wireless headphones",
                    "Active noise cancellation",
                    "30-hour battery life",
                    "$299.99 price point",
                    "4.8/5 rating with 2,847 reviews"
                ]
            },
            data_quality_score=0.94,
            content_length=len(product_content["text"]),
            load_time=1.8
        )
        
        # Validate product data
        assert "Premium Wireless Headphones" in scraped_data.content["title"]
        assert scraped_data.content["custom_fields"]["price"] == "$299.99"
        assert scraped_data.content["custom_fields"]["rating"] == "4.8/5"
        assert "Black" in scraped_data.content["custom_fields"]["color_options"]
        assert len(scraped_data.content["custom_fields"]["features"]) == 5
        assert scraped_data.confidence_score == 0.95
        assert "electronics" in scraped_data.ai_metadata["topics"]
    
    def test_create_sample_blog_data(self):
        """Test creating sample blog post data."""
        blog_content = {
            "title": "10 Best Practices for Ethical Web Scraping in 2024",
            "text": "Web scraping has become an essential tool for data collection, but it's crucial to follow ethical guidelines. This comprehensive guide covers the top 10 best practices every developer should know when implementing web scraping solutions.",
            "headings": [
                {"level": 1, "text": "10 Best Practices for Ethical Web Scraping in 2024", "id": "main", "class": ["post-title"]},
                {"level": 2, "text": "1. Respect robots.txt Files", "id": "robots", "class": ["practice-heading"]},
                {"level": 2, "text": "2. Implement Rate Limiting", "id": "rate-limit", "class": ["practice-heading"]},
                {"level": 2, "text": "3. Use Proper User Agents", "id": "user-agents", "class": ["practice-heading"]}
            ],
            "paragraphs": [
                "Web scraping has become an essential tool for data collection in the modern digital landscape.",
                "However, with great power comes great responsibility, and it's crucial to follow ethical guidelines.",
                "This comprehensive guide covers the top 10 best practices every developer should know.",
                "By following these practices, you can ensure your scraping activities are both effective and respectful."
            ],
            "lists": [
                {
                    "type": "ol",
                    "items": [
                        "Respect robots.txt files",
                        "Implement proper rate limiting",
                        "Use appropriate user agents",
                        "Handle errors gracefully",
                        "Cache responses when possible",
                        "Monitor server load",
                        "Respect copyright and terms of service",
                        "Implement circuit breakers",
                        "Use rotating proxies responsibly",
                        "Document your scraping activities"
                    ]
                }
            ],
            "metadata": {
                "author": "Sarah Johnson",
                "publish_date": "2024-01-10",
                "category": "Web Development",
                "tags": ["web scraping", "ethics", "best practices", "development"],
                "reading_time": "8 minutes",
                "word_count": 2150
            }
        }
        
        scraped_data = ScrapedData(
            job_id=str(uuid4()),
            url="https://dev-blog.com/ethical-web-scraping-best-practices-2024",
            content=blog_content,
            content_type=ContentType.HTML,
            confidence_score=0.89,
            ai_processed=True,
            ai_metadata={
                "summary": "Comprehensive guide covering 10 essential best practices for ethical web scraping in 2024.",
                "topics": ["web scraping", "ethics", "best practices", "development", "guidelines"],
                "quality_score": 0.91,
                "content_category": "blog",
                "language": "en",
                "readability_score": 0.82,
                "key_info": [
                    "10 best practices for ethical scraping",
                    "Importance of respecting robots.txt",
                    "Rate limiting implementation",
                    "Proper user agent usage",
                    "Error handling strategies"
                ]
            },
            data_quality_score=0.88,
            content_length=len(blog_content["text"]),
            load_time=1.5
        )
        
        # Validate blog data
        assert "Best Practices" in scraped_data.content["title"]
        assert len(scraped_data.content["lists"][0]["items"]) == 10
        assert scraped_data.content["metadata"]["author"] == "Sarah Johnson"
        assert scraped_data.content["metadata"]["reading_time"] == "8 minutes"
        assert scraped_data.ai_metadata["content_category"] == "blog"
        assert scraped_data.ai_metadata["readability_score"] == 0.82
    
    def test_sample_scraping_result_aggregation(self):
        """Test creating sample scraping result with multiple data points."""
        # Create multiple sample data points
        data_points = []
        
        for i in range(5):
            content = {
                "title": f"Sample Article {i+1}",
                "text": f"This is sample content for article number {i+1}. It contains relevant information for testing purposes.",
                "metadata": {"article_number": i+1}
            }
            
            data_point = ScrapedData(
                job_id="sample-job-123",
                url=f"https://example.com/article-{i+1}",
                content=content,
                confidence_score=0.8 + (i * 0.02),  # Varying confidence scores
                ai_processed=True,
                data_quality_score=0.75 + (i * 0.03),
                content_length=len(content["text"]),
                load_time=1.0 + (i * 0.2)
            )
            data_points.append(data_point)
        
        # Create scraping result
        result = ScrapingResult(
            job_id="sample-job-123",
            success=True,
            data=data_points,
            total_time=15.5,
            pages_scraped=5,
            pages_failed=0,
            data_quality_summary={
                "total_articles": 5,
                "avg_confidence": sum(d.confidence_score for d in data_points) / len(data_points),
                "avg_quality": sum(d.data_quality_score for d in data_points) / len(data_points),
                "total_content_length": sum(d.content_length for d in data_points),
                "avg_load_time": sum(d.load_time for d in data_points) / len(data_points)
            }
        )
        
        # Validate aggregated result
        assert result.success is True
        assert len(result.data) == 5
        assert result.pages_scraped == 5
        assert result.pages_failed == 0
        assert result.average_confidence > 0.8
        assert result.data_quality_summary["total_articles"] == 5
        assert result.data_quality_summary["avg_confidence"] > 0.8
        assert result.data_quality_summary["total_content_length"] > 0
    
    def test_sample_data_json_serialization(self):
        """Test that sample data can be properly serialized to JSON."""
        config = ScrapingConfig(
            name="JSON Test Job",
            custom_selectors={"title": "h1", "content": ".main-content"}
        )
        
        job = ScrapingJob(
            url="https://example.com",
            config=config,
            tags=["test", "json"]
        )
        
        # Test JSON serialization
        job_json = job.model_dump_json()
        parsed_job = json.loads(job_json)
        
        assert parsed_job["url"] == "https://example.com"
        assert parsed_job["config"]["name"] == "JSON Test Job"
        assert "test" in parsed_job["tags"]
        
        # Test that we can recreate the object from JSON
        recreated_job = ScrapingJob.model_validate(parsed_job)
        assert recreated_job.url == job.url
        assert recreated_job.config.name == job.config.name
        assert recreated_job.tags == job.tags