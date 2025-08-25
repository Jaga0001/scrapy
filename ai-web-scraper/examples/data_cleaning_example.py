#!/usr/bin/env python3
"""
Example demonstrating the data cleaning and validation system.

This example shows how to use the DataCleaner class to clean scraped data,
detect duplicates, validate data types, and generate quality reports.
"""

import sys
import os
from datetime import datetime
from typing import List

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.pipeline.cleaner import DataCleaner, CleaningRule, DataQualityMetrics
from src.models.pydantic_models import ScrapedData, ContentType


def create_sample_dirty_data() -> List[ScrapedData]:
    """Create sample dirty data for demonstration."""
    return [
        ScrapedData(
            id="sample-1",
            job_id="demo-job",
            url="https://example.com/page1",
            content={
                "title": "Product Review: Amazing Widget",
                "email": "  CONTACT@EXAMPLE.COM  ",  # Needs normalization
                "phone": "(555) 123-4567",  # Needs formatting cleanup
                "price": "$29.99",
                "description": "This   is   a   great   product   with   extra   spaces",
                "url": "example.com/product/123",  # Missing protocol
                "rating": "4.5 stars"
            },
            content_type=ContentType.HTML,
            confidence_score=0.8
        ),
        ScrapedData(
            id="sample-2",
            job_id="demo-job",
            url="https://example.com/page2",
            content={
                "title": "Another Product Review",
                "email": "invalid-email-format",  # Invalid email
                "phone": "555.123.4567",  # Different formatting
                "price": "Free shipping!",  # Non-standard price
                "description": "Short desc",
                "url": "https://valid-url.com/page",
                "rating": "5"
            },
            content_type=ContentType.HTML,
            confidence_score=0.7
        ),
        ScrapedData(
            id="sample-3",
            job_id="demo-job",
            url="https://example.com/page3",
            content={
                "title": "Product Review: Amazing Widget",  # Duplicate content
                "email": "  CONTACT@EXAMPLE.COM  ",
                "phone": "(555) 123-4567",
                "price": "$29.99",
                "description": "This   is   a   great   product   with   extra   spaces",
                "url": "example.com/product/123",
                "rating": "4.5 stars"
            },
            content_type=ContentType.HTML,
            confidence_score=0.8
        ),
        ScrapedData(
            id="sample-4",
            job_id="demo-job",
            url="https://example.com/page4",
            content={
                "title": "",  # Empty title
                "email": "user@domain.co.uk",  # Valid email
                "phone": "+1-555-987-6543",  # International format
                "price": "€45.00",  # Different currency
                "description": None,  # None value
                "url": "//protocol-relative.com",
                "rating": "N/A"
            },
            content_type=ContentType.HTML,
            confidence_score=0.6
        )
    ]


def demonstrate_basic_cleaning():
    """Demonstrate basic data cleaning functionality."""
    print("=" * 60)
    print("BASIC DATA CLEANING DEMONSTRATION")
    print("=" * 60)
    
    # Create cleaner instance
    cleaner = DataCleaner()
    print(f"✓ DataCleaner initialized with {len(cleaner.cleaning_rules)} default rules")
    
    # Create sample data
    dirty_data = create_sample_dirty_data()
    print(f"✓ Created {len(dirty_data)} sample records with dirty data")
    
    # Clean the data
    print("\n🧹 Cleaning data...")
    cleaned_data, metrics = cleaner.clean_data(dirty_data)
    
    # Display results
    print(f"\n📊 CLEANING RESULTS:")
    print(f"   Total records processed: {metrics.total_records}")
    print(f"   Valid records: {metrics.valid_records}")
    print(f"   Invalid records: {metrics.invalid_records}")
    print(f"   Duplicate records: {metrics.duplicate_records}")
    print(f"   Corrected records: {metrics.corrected_records}")
    print(f"   Processing time: {metrics.processing_time:.3f}s")
    
    print(f"\n📈 QUALITY SCORES:")
    print(f"   Overall quality: {metrics.overall_quality_score:.2f}")
    print(f"   Completeness: {metrics.completeness_score:.2f}")
    print(f"   Accuracy: {metrics.accuracy_score:.2f}")
    print(f"   Consistency: {metrics.consistency_score:.2f}")
    
    # Show before/after examples
    if cleaned_data:
        print(f"\n🔍 BEFORE/AFTER EXAMPLE:")
        original = dirty_data[0]
        cleaned = cleaned_data[0]
        
        print(f"   Original email: '{original.content.get('email')}'")
        print(f"   Cleaned email:  '{cleaned.content.get('email')}'")
        
        print(f"   Original phone: '{original.content.get('phone')}'")
        print(f"   Cleaned phone:  '{cleaned.content.get('phone')}'")
        
        print(f"   Original description: '{original.content.get('description')}'")
        print(f"   Cleaned description:  '{cleaned.content.get('description')}'")


def demonstrate_duplicate_detection():
    """Demonstrate duplicate detection functionality."""
    print("\n" + "=" * 60)
    print("DUPLICATE DETECTION DEMONSTRATION")
    print("=" * 60)
    
    cleaner = DataCleaner()
    dirty_data = create_sample_dirty_data()
    
    # Detect duplicates
    print("🔍 Detecting duplicates...")
    duplicates = cleaner.detect_duplicates(dirty_data)
    
    print(f"\n📋 DUPLICATE DETECTION RESULTS:")
    print(f"   Found {len(duplicates)} duplicate pairs")
    
    for i, (id1, id2, similarity) in enumerate(duplicates, 1):
        print(f"   {i}. Records '{id1}' and '{id2}' are {similarity:.1%} similar")


def demonstrate_custom_rules():
    """Demonstrate adding custom cleaning rules."""
    print("\n" + "=" * 60)
    print("CUSTOM CLEANING RULES DEMONSTRATION")
    print("=" * 60)
    
    cleaner = DataCleaner()
    
    # Add custom rule for rating field
    custom_rule = CleaningRule(
        field_name="rating",
        rule_type="text_cleaning",
        parameters={"remove_extra_whitespace": True, "normalize_unicode": True},
        confidence_threshold=0.7
    )
    
    cleaner.add_cleaning_rule(custom_rule)
    print(f"✓ Added custom rule for 'rating' field")
    print(f"✓ Total rules now: {len(cleaner.cleaning_rules)}")
    
    # Test with sample data
    dirty_data = create_sample_dirty_data()
    cleaned_data, metrics = cleaner.clean_data(dirty_data)
    
    print(f"\n📊 Results with custom rule:")
    print(f"   Processed {metrics.total_records} records")
    print(f"   Quality score: {metrics.overall_quality_score:.2f}")


def demonstrate_quality_report():
    """Demonstrate quality report generation."""
    print("\n" + "=" * 60)
    print("QUALITY REPORT DEMONSTRATION")
    print("=" * 60)
    
    cleaner = DataCleaner()
    dirty_data = create_sample_dirty_data()
    cleaned_data, metrics = cleaner.clean_data(dirty_data)
    
    # Generate comprehensive report
    print("📋 Generating quality report...")
    report = cleaner.generate_quality_report(metrics)
    
    print(f"\n📊 COMPREHENSIVE QUALITY REPORT:")
    
    # Summary section
    summary = report["summary"]
    print(f"\n   SUMMARY:")
    for key, value in summary.items():
        print(f"     {key.replace('_', ' ').title()}: {value}")
    
    # Quality scores
    quality_scores = report["quality_scores"]
    print(f"\n   QUALITY SCORES:")
    for key, value in quality_scores.items():
        print(f"     {key.replace('_', ' ').title()}: {value:.2f}")
    
    # Field quality
    if report["field_quality"]:
        print(f"\n   FIELD QUALITY SCORES:")
        for field, score in report["field_quality"].items():
            print(f"     {field}: {score:.2f}")
    
    # Recommendations
    if report["recommendations"]:
        print(f"\n   RECOMMENDATIONS:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"     {i}. {rec}")


def demonstrate_individual_cleaners():
    """Demonstrate individual cleaning functions."""
    print("\n" + "=" * 60)
    print("INDIVIDUAL CLEANING FUNCTIONS DEMONSTRATION")
    print("=" * 60)
    
    cleaner = DataCleaner()
    
    # Test cases for different data types
    test_cases = [
        ("Email", "  JOHN.DOE@EXAMPLE.COM  ", cleaner._clean_email, {"normalize_case": True}),
        ("Phone", "(555) 123-4567", cleaner._clean_phone, {"remove_formatting": True}),
        ("URL", "example.com/page", cleaner._clean_url, {"normalize_scheme": True}),
        ("Text", "This   has    extra     spaces", cleaner._clean_text, {"remove_extra_whitespace": True}),
        ("Price", "$1,234.56", cleaner._clean_price, {"currency_symbol": "$", "decimal_places": 2})
    ]
    
    print("🧪 Testing individual cleaning functions:")
    
    for data_type, test_value, clean_func, params in test_cases:
        cleaned_value, confidence = clean_func(test_value, params)
        print(f"\n   {data_type}:")
        print(f"     Original:  '{test_value}'")
        print(f"     Cleaned:   '{cleaned_value}'")
        print(f"     Confidence: {confidence:.2f}")


def main():
    """Run all demonstrations."""
    print("🚀 DATA CLEANING AND VALIDATION SYSTEM DEMO")
    print("This demo shows the capabilities of the DataCleaner class")
    
    try:
        demonstrate_basic_cleaning()
        demonstrate_duplicate_detection()
        demonstrate_custom_rules()
        demonstrate_quality_report()
        demonstrate_individual_cleaners()
        
        print("\n" + "=" * 60)
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()