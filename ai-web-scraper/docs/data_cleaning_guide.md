# Data Cleaning and Validation System Guide

## Overview

The Data Cleaning and Validation System provides comprehensive automated cleaning, validation, and quality assessment capabilities for scraped web data. It includes duplicate detection, data type validation, format normalization, and automated data correction with confidence scoring.

## Key Features

- **Automated Cleaning Rules**: Pre-configured rules for common data types (email, phone, URL, text, price)
- **Duplicate Detection**: Content hashing and similarity-based duplicate identification
- **Data Type Validation**: Comprehensive validation with format normalization using Pandas
- **Quality Assessment**: Detailed quality metrics and scoring system
- **Automated Correction**: Intelligent data correction with confidence scoring
- **Extensible Rules**: Support for custom cleaning rules
- **Comprehensive Reporting**: Detailed quality reports with recommendations

## Quick Start

```python
from src.pipeline.cleaner import DataCleaner
from src.models.pydantic_models import ScrapedData, ContentType

# Initialize the cleaner
cleaner = DataCleaner()

# Clean your scraped data
cleaned_data, metrics = cleaner.clean_data(scraped_data_list)

# Generate quality report
report = cleaner.generate_quality_report(metrics)
```

## Core Components

### DataCleaner Class

The main class that orchestrates all cleaning operations:

```python
cleaner = DataCleaner()

# Clean data
cleaned_data, metrics = cleaner.clean_data(data_list)

# Detect duplicates
duplicates = cleaner.detect_duplicates(data_list)

# Generate quality report
report = cleaner.generate_quality_report(metrics)
```

### CleaningRule Model

Define custom cleaning rules:

```python
from src.pipeline.cleaner import CleaningRule

custom_rule = CleaningRule(
    field_name="custom_field",
    rule_type="text_cleaning",
    parameters={"remove_extra_whitespace": True},
    confidence_threshold=0.8
)

cleaner.add_cleaning_rule(custom_rule)
```

### DataQualityMetrics Model

Comprehensive quality metrics:

- `total_records`: Total number of records processed
- `valid_records`: Number of valid records
- `invalid_records`: Number of invalid records
- `duplicate_records`: Number of duplicate records found
- `corrected_records`: Number of records that were auto-corrected
- `overall_quality_score`: Overall data quality score (0.0-1.0)
- `completeness_score`: Data completeness score (0.0-1.0)
- `accuracy_score`: Data accuracy score (0.0-1.0)
- `consistency_score`: Data consistency score (0.0-1.0)

## Built-in Cleaning Rules

### Email Validation
- Normalizes case (converts to lowercase)
- Validates email format using regex
- Provides confidence scoring based on format validity

### Phone Normalization
- Removes formatting characters (spaces, dashes, parentheses)
- Validates phone number format
- Supports international formats

### URL Validation
- Adds missing protocol (http/https)
- Handles protocol-relative URLs
- Validates URL structure
- Optional fragment removal

### Text Cleaning
- Removes extra whitespace
- Normalizes Unicode characters
- Confidence scoring based on text quality

### Price Normalization
- Extracts numeric values from price strings
- Formats with specified decimal places
- Adds currency symbols
- Handles various price formats

## Usage Examples

### Basic Data Cleaning

```python
from src.pipeline.cleaner import DataCleaner
from src.models.pydantic_models import ScrapedData, ContentType

# Sample dirty data
dirty_data = [
    ScrapedData(
        id="test-1",
        job_id="job-1",
        url="https://example.com",
        content={
            "email": "  USER@EXAMPLE.COM  ",
            "phone": "(555) 123-4567",
            "text": "This   has   extra   spaces"
        },
        content_type=ContentType.HTML,
        confidence_score=0.8
    )
]

# Clean the data
cleaner = DataCleaner()
cleaned_data, metrics = cleaner.clean_data(dirty_data)

print(f"Processed {metrics.total_records} records")
print(f"Quality score: {metrics.overall_quality_score:.2f}")
```

### Custom Cleaning Rules

```python
from src.pipeline.cleaner import CleaningRule

# Add custom rule for product ratings
rating_rule = CleaningRule(
    field_name="rating",
    rule_type="text_cleaning",
    parameters={
        "remove_extra_whitespace": True,
        "normalize_unicode": True
    },
    confidence_threshold=0.7
)

cleaner.add_cleaning_rule(rating_rule)
```

### Duplicate Detection

```python
# Detect duplicates in your data
duplicates = cleaner.detect_duplicates(scraped_data)

for record_id1, record_id2, similarity in duplicates:
    print(f"Records {record_id1} and {record_id2} are {similarity:.1%} similar")
```

### Quality Reporting

```python
# Generate comprehensive quality report
report = cleaner.generate_quality_report(metrics)

print("Summary:", report["summary"])
print("Quality Scores:", report["quality_scores"])
print("Recommendations:", report["recommendations"])
```

## Configuration Options

### Similarity Threshold
Control duplicate detection sensitivity:

```python
cleaner.similarity_threshold = 0.9  # Higher = more strict
```

### Custom Cleaning Parameters

Each cleaning rule type supports different parameters:

- **email_validation**: `normalize_case` (bool)
- **phone_normalization**: `remove_formatting` (bool), `add_country_code` (bool)
- **url_validation**: `normalize_scheme` (bool), `remove_fragments` (bool)
- **text_cleaning**: `remove_extra_whitespace` (bool), `normalize_unicode` (bool)
- **price_normalization**: `currency_symbol` (str), `decimal_places` (int)

## Quality Metrics Interpretation

### Overall Quality Score
Weighted combination of completeness, accuracy, and consistency:
- **0.9-1.0**: Excellent quality
- **0.7-0.9**: Good quality
- **0.5-0.7**: Fair quality
- **0.0-0.5**: Poor quality

### Completeness Score
Percentage of valid records vs. total records

### Accuracy Score
Based on validation errors and data correction success

### Consistency Score
Based on field quality scores across all records

## Best Practices

1. **Review Quality Reports**: Always check quality metrics and recommendations
2. **Custom Rules**: Add domain-specific cleaning rules for your data
3. **Threshold Tuning**: Adjust confidence thresholds based on your quality requirements
4. **Regular Monitoring**: Track quality metrics over time to identify trends
5. **Validation**: Manually review samples of cleaned data to verify results

## Integration with Pipeline

The DataCleaner integrates seamlessly with the scraping pipeline:

```python
# In your scraping workflow
from src.pipeline.cleaner import DataCleaner

# After scraping and AI processing
cleaner = DataCleaner()
cleaned_data, quality_metrics = cleaner.clean_data(scraped_results)

# Store cleaned data and quality metrics
repository.save_cleaned_data(cleaned_data, quality_metrics)
```

## Performance Considerations

- The cleaner processes data in batches for optimal performance
- Large datasets are handled efficiently with streaming operations
- Quality calculations are optimized for minimal memory usage
- Processing time scales linearly with data size

## Troubleshooting

### Common Issues

1. **Low Quality Scores**: Review cleaning rules and adjust confidence thresholds
2. **High Duplicate Count**: Implement stronger duplicate detection during scraping
3. **Poor Field Quality**: Add custom cleaning rules for specific data types
4. **Performance Issues**: Process data in smaller batches for very large datasets

### Debugging

Enable debug logging to see detailed cleaning operations:

```python
import logging
logging.getLogger('src.pipeline.cleaner').setLevel(logging.DEBUG)
```

## API Reference

See the complete API documentation in the source code docstrings:
- `DataCleaner` class methods
- `CleaningRule` model fields
- `DataQualityMetrics` model fields
- Individual cleaning function parameters