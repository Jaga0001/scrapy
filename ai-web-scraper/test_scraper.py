#!/usr/bin/env python3
"""
Test script for the enhanced web scraper.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.scraper.simple_scraper import SimpleWebScraper
from src.models.pydantic_models import ScrapingConfig


async def test_scraper():
    """Test the enhanced web scraper with various URLs."""
    
    # Test URLs
    test_urls = [
        "https://httpbin.org/html",  # Simple test page
        "https://example.com",       # Basic example
        "https://news.ycombinator.com",  # Real content
    ]
    
    # Create enhanced configuration
    config = ScrapingConfig(
        wait_time=2,
        max_retries=2,
        timeout=10,
        delay_between_requests=1.0,
        extract_images=True,
        extract_links=True,
        respect_robots_txt=True
    )
    
    print("🚀 Testing Enhanced Web Scraper")
    print("=" * 50)
    
    async with SimpleWebScraper(config) as scraper:
        for i, url in enumerate(test_urls, 1):
            print(f"\n📄 Test {i}: Scraping {url}")
            print("-" * 40)
            
            try:
                result = await scraper.scrape_url(url, f"test_job_{i}")
                
                if result:
                    print(f"✅ Success!")
                    print(f"   Title: {result.content.get('title', 'No title')[:60]}...")
                    print(f"   Text Length: {len(result.content.get('text', ''))} chars")
                    print(f"   Headings: {len(result.content.get('headings', []))}")
                    print(f"   Links: {len(result.content.get('links', []))}")
                    print(f"   Images: {len(result.content.get('images', []))}")
                    print(f"   Confidence: {result.confidence_score:.2f}")
                    print(f"   Quality: {result.data_quality_score:.2f}")
                    print(f"   Load Time: {result.load_time:.2f}s")
                    print(f"   AI Processed: {result.ai_processed}")
                    
                    if result.ai_metadata:
                        print(f"   AI Summary: {result.ai_metadata.get('summary', 'N/A')[:80]}...")
                else:
                    print("❌ Failed to scrape")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    print("\n🎉 Testing completed!")


async def test_multiple_urls():
    """Test scraping multiple URLs."""
    
    urls = [
        "https://httpbin.org/html",
        "https://example.com"
    ]
    
    config = ScrapingConfig(
        delay_between_requests=0.5,
        extract_links=False,  # Faster testing
        extract_images=False
    )
    
    print("\n🔄 Testing Multiple URL Scraping")
    print("=" * 50)
    
    async with SimpleWebScraper(config) as scraper:
        results = await scraper.scrape_multiple(urls, "multi_test_job")
        
        print(f"✅ Scraped {len(results)}/{len(urls)} URLs successfully")
        
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result.url} - Quality: {result.data_quality_score:.2f}")


def main():
    """Main test function."""
    print("🧪 Enhanced Web Scraper Test Suite")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not set. AI analysis will be disabled.")
    else:
        print("✅ GEMINI_API_KEY found. AI analysis enabled.")
    
    try:
        # Run single URL tests
        asyncio.run(test_scraper())
        
        # Run multiple URL tests
        asyncio.run(test_multiple_urls())
        
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()