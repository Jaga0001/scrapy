"""
Data cleaning and validation system for scraped content.

This module provides comprehensive data cleaning, validation, and quality assessment
capabilities for scraped web data. It includes duplicate detection, data type validation,
format normalization, and automated data correction with confidence scoring.
"""

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import pandas as pd
from pydantic import BaseModel, Field

from ..models.pydantic_models import ScrapedData
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataQualityMetrics(BaseModel):
    """Model for data quality assessment metrics."""
    
    total_records: int = Field(ge=0, description="Total number of records processed")
    valid_records: int = Field(ge=0, description="Number of valid records")
    invalid_records: int = Field(ge=0, description="Number of invalid records")
    duplicate_records: int = Field(ge=0, description="Number of duplicate records found")
    corrected_records: int = Field(ge=0, description="Number of records that were auto-corrected")
    
    # Quality scores
    overall_quality_score: float = Field(ge=0.0, le=1.0, description="Overall data quality score")
    completeness_score: float = Field(ge=0.0, le=1.0, description="Data completeness score")
    accuracy_score: float = Field(ge=0.0, le=1.0, description="Data accuracy score")
    consistency_score: float = Field(ge=0.0, le=1.0, description="Data consistency score")
    
    # Error breakdown
    validation_errors: Dict[str, int] = Field(default_factory=dict, description="Count of each validation error type")
    field_quality_scores: Dict[str, float] = Field(default_factory=dict, description="Quality score per field")
    
    # Processing metadata
    processing_time: float = Field(ge=0.0, description="Time taken for cleaning process")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="When processing completed")


class CleaningRule(BaseModel):
    """Model for defining data cleaning rules."""
    
    field_name: str = Field(..., description="Name of the field to apply rule to")
    rule_type: str = Field(..., description="Type of cleaning rule")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Rule parameters")
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence threshold for applying rule")
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class DataCleaner:
    """
    Comprehensive data cleaning and validation system.
    
    Provides automated cleaning rules, duplicate detection, data type validation,
    format normalization, and quality assessment for scraped web data.
    """
    
    def __init__(self):
        """Initialize the DataCleaner with default cleaning rules."""
        self.logger = get_logger(self.__class__.__name__)
        self.cleaning_rules: List[CleaningRule] = []
        self.content_hashes: Set[str] = set()
        self.similarity_threshold = 0.85
        
        # Initialize default cleaning rules
        self._initialize_default_rules()
        
        # Common patterns for data validation
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.phone_pattern = re.compile(r'^[\+]?[1-9][\d]{0,15}$')
        self.url_pattern = re.compile(r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$')
        
    def _initialize_default_rules(self) -> None:
        """Initialize default cleaning rules for common data types."""
        default_rules = [
            CleaningRule(
                field_name="email",
                rule_type="email_validation",
                parameters={"normalize_case": True},
                confidence_threshold=0.9
            ),
            CleaningRule(
                field_name="phone",
                rule_type="phone_normalization",
                parameters={"remove_formatting": True, "add_country_code": False},
                confidence_threshold=0.8
            ),
            CleaningRule(
                field_name="url",
                rule_type="url_validation",
                parameters={"normalize_scheme": True, "remove_fragments": False},
                confidence_threshold=0.9
            ),
            CleaningRule(
                field_name="text",
                rule_type="text_cleaning",
                parameters={"remove_extra_whitespace": True, "normalize_unicode": True},
                confidence_threshold=0.7
            ),
            CleaningRule(
                field_name="price",
                rule_type="price_normalization",
                parameters={"currency_symbol": "$", "decimal_places": 2},
                confidence_threshold=0.8
            )
        ]
        
        self.cleaning_rules.extend(default_rules)
        self.logger.info(f"Initialized {len(default_rules)} default cleaning rules")
    
    def add_cleaning_rule(self, rule: CleaningRule) -> None:
        """Add a custom cleaning rule."""
        self.cleaning_rules.append(rule)
        self.logger.info(f"Added cleaning rule for field '{rule.field_name}' with type '{rule.rule_type}'")
    
    def clean_data(self, data: List[ScrapedData]) -> Tuple[List[ScrapedData], DataQualityMetrics]:
        """
        Clean and validate a list of scraped data records.
        
        Args:
            data: List of ScrapedData objects to clean
            
        Returns:
            Tuple of (cleaned_data, quality_metrics)
        """
        start_time = datetime.utcnow()
        self.logger.info(f"Starting data cleaning process for {len(data)} records")
        
        # Initialize metrics
        metrics = DataQualityMetrics(
            total_records=len(data),
            valid_records=0,
            invalid_records=0,
            duplicate_records=0,
            corrected_records=0,
            overall_quality_score=0.0,
            completeness_score=0.0,
            accuracy_score=0.0,
            consistency_score=0.0,
            processing_time=0.0
        )
        cleaned_data = []
        
        # Track duplicates
        seen_hashes = set()
        duplicate_count = 0
        
        for record in data:
            try:
                # Check for duplicates
                content_hash = self._generate_content_hash(record.content)
                if content_hash in seen_hashes:
                    duplicate_count += 1
                    self.logger.debug(f"Duplicate record found: {record.id}")
                    continue
                seen_hashes.add(content_hash)
                
                # Clean the record
                cleaned_record, record_metrics = self._clean_single_record(record)
                
                if cleaned_record:
                    cleaned_data.append(cleaned_record)
                    metrics.valid_records += 1
                    
                    # Update field quality scores
                    for field, score in record_metrics.get('field_scores', {}).items():
                        if field not in metrics.field_quality_scores:
                            metrics.field_quality_scores[field] = []
                        metrics.field_quality_scores[field].append(score)
                    
                    # Track corrections
                    if record_metrics.get('corrected', False):
                        metrics.corrected_records += 1
                else:
                    metrics.invalid_records += 1
                    
            except Exception as e:
                self.logger.error(f"Error cleaning record {record.id}: {str(e)}")
                metrics.invalid_records += 1
        
        # Update metrics
        metrics.duplicate_records = duplicate_count
        
        # Calculate quality scores
        metrics = self._calculate_quality_scores(metrics, cleaned_data)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        metrics.processing_time = processing_time
        
        self.logger.info(
            f"Data cleaning completed. Valid: {metrics.valid_records}, "
            f"Invalid: {metrics.invalid_records}, Duplicates: {metrics.duplicate_records}, "
            f"Processing time: {processing_time:.2f}s"
        )
        
        return cleaned_data, metrics
    
    def _clean_single_record(self, record: ScrapedData) -> Tuple[Optional[ScrapedData], Dict[str, Any]]:
        """
        Clean a single scraped data record.
        
        Args:
            record: ScrapedData object to clean
            
        Returns:
            Tuple of (cleaned_record, record_metrics)
        """
        record_metrics = {
            'field_scores': {},
            'corrected': False,
            'validation_errors': []
        }
        
        try:
            # Create a copy of the record for cleaning
            cleaned_content = record.content.copy()
            validation_errors = []
            
            # Apply cleaning rules to each field
            for field_name, field_value in cleaned_content.items():
                if field_value is None:
                    continue
                    
                # Find applicable cleaning rules
                applicable_rules = [
                    rule for rule in self.cleaning_rules 
                    if rule.enabled and (rule.field_name == field_name or rule.field_name == "text")
                ]
                
                field_score = 1.0
                field_corrected = False
                
                for rule in applicable_rules:
                    try:
                        cleaned_value, rule_score, was_corrected = self._apply_cleaning_rule(
                            field_value, rule
                        )
                        
                        if was_corrected:
                            cleaned_content[field_name] = cleaned_value
                            field_corrected = True
                            record_metrics['corrected'] = True
                        
                        field_score = min(field_score, rule_score)
                        
                    except Exception as e:
                        self.logger.warning(f"Error applying rule {rule.rule_type} to field {field_name}: {str(e)}")
                        validation_errors.append(f"Rule {rule.rule_type} failed: {str(e)}")
                        field_score *= 0.8  # Penalize for rule failure
                
                record_metrics['field_scores'][field_name] = field_score
            
            # Validate data types and formats
            type_validation_score = self._validate_data_types(cleaned_content, validation_errors)
            
            # Calculate overall record quality score
            field_scores = list(record_metrics['field_scores'].values())
            if field_scores:
                avg_field_score = sum(field_scores) / len(field_scores)
            else:
                avg_field_score = 0.5
            
            overall_score = (avg_field_score + type_validation_score) / 2
            
            # Update the record with cleaned data
            cleaned_record = ScrapedData(
                id=record.id,
                job_id=record.job_id,
                url=record.url,
                content=cleaned_content,
                raw_html=record.raw_html,
                content_type=record.content_type,
                content_metadata=record.content_metadata,
                confidence_score=record.confidence_score,
                ai_processed=record.ai_processed,
                ai_metadata=record.ai_metadata,
                data_quality_score=overall_score,
                validation_errors=validation_errors,
                extracted_at=record.extracted_at,
                processed_at=record.processed_at,
                content_length=record.content_length,
                load_time=record.load_time
            )
            
            record_metrics['validation_errors'] = validation_errors
            
            # Only return record if quality score meets minimum threshold
            if overall_score >= 0.3:  # Minimum quality threshold
                return cleaned_record, record_metrics
            else:
                self.logger.debug(f"Record {record.id} rejected due to low quality score: {overall_score}")
                return None, record_metrics
                
        except Exception as e:
            self.logger.error(f"Error cleaning record {record.id}: {str(e)}")
            record_metrics['validation_errors'].append(f"Cleaning failed: {str(e)}")
            return None, record_metrics
    
    def _apply_cleaning_rule(self, value: Any, rule: CleaningRule) -> Tuple[Any, float, bool]:
        """
        Apply a specific cleaning rule to a field value.
        
        Args:
            value: The field value to clean
            rule: The cleaning rule to apply
            
        Returns:
            Tuple of (cleaned_value, confidence_score, was_corrected)
        """
        if not isinstance(value, str):
            value = str(value)
        
        original_value = value
        confidence_score = 1.0
        was_corrected = False
        
        try:
            if rule.rule_type == "email_validation":
                value, confidence_score = self._clean_email(value, rule.parameters)
                
            elif rule.rule_type == "phone_normalization":
                value, confidence_score = self._clean_phone(value, rule.parameters)
                
            elif rule.rule_type == "url_validation":
                value, confidence_score = self._clean_url(value, rule.parameters)
                
            elif rule.rule_type == "text_cleaning":
                value, confidence_score = self._clean_text(value, rule.parameters)
                
            elif rule.rule_type == "price_normalization":
                value, confidence_score = self._clean_price(value, rule.parameters)
                
            else:
                self.logger.warning(f"Unknown cleaning rule type: {rule.rule_type}")
                confidence_score = 0.5
            
            was_corrected = (value != original_value)
            
        except Exception as e:
            self.logger.error(f"Error applying cleaning rule {rule.rule_type}: {str(e)}")
            confidence_score = 0.3
        
        return value, confidence_score, was_corrected
    
    def _clean_email(self, email: str, parameters: Dict[str, Any]) -> Tuple[str, float]:
        """Clean and validate email addresses."""
        if not email or not isinstance(email, str):
            return email, 0.0
        
        cleaned_email = email.strip()
        
        # Normalize case if requested
        if parameters.get("normalize_case", True):
            cleaned_email = cleaned_email.lower()
        
        # Validate email format
        if self.email_pattern.match(cleaned_email):
            return cleaned_email, 1.0
        else:
            # Try to fix common issues
            if "@" in cleaned_email and "." in cleaned_email.split("@")[-1]:
                return cleaned_email, 0.7  # Partial confidence
            else:
                return cleaned_email, 0.2  # Low confidence
    
    def _clean_phone(self, phone: str, parameters: Dict[str, Any]) -> Tuple[str, float]:
        """Clean and normalize phone numbers."""
        if not phone or not isinstance(phone, str):
            return phone, 0.0
        
        cleaned_phone = phone.strip()
        
        # Remove formatting if requested
        if parameters.get("remove_formatting", True):
            cleaned_phone = re.sub(r'[\s\-\(\)\.]', '', cleaned_phone)
        
        # Validate phone format
        if self.phone_pattern.match(cleaned_phone):
            return cleaned_phone, 1.0
        else:
            # Check if it looks like a phone number
            digits_only = re.sub(r'\D', '', cleaned_phone)
            if 7 <= len(digits_only) <= 15:
                return digits_only, 0.8
            else:
                return cleaned_phone, 0.2
    
    def _clean_url(self, url: str, parameters: Dict[str, Any]) -> Tuple[str, float]:
        """Clean and validate URLs."""
        if not url or not isinstance(url, str):
            return url, 0.0
        
        cleaned_url = url.strip()
        
        # Normalize scheme if requested
        if parameters.get("normalize_scheme", True):
            if not cleaned_url.startswith(('http://', 'https://')):
                if cleaned_url.startswith('//'):
                    cleaned_url = 'https:' + cleaned_url
                elif '.' in cleaned_url:
                    cleaned_url = 'https://' + cleaned_url
        
        # Remove fragments if requested
        if parameters.get("remove_fragments", False):
            cleaned_url = cleaned_url.split('#')[0]
        
        # Validate URL format
        try:
            parsed = urlparse(cleaned_url)
            if parsed.scheme and parsed.netloc:
                return cleaned_url, 1.0
            else:
                return cleaned_url, 0.4
        except Exception:
            return cleaned_url, 0.2
    
    def _clean_text(self, text: str, parameters: Dict[str, Any]) -> Tuple[str, float]:
        """Clean and normalize text content."""
        if not text or not isinstance(text, str):
            return text, 0.0
        
        cleaned_text = text
        
        # Remove extra whitespace if requested
        if parameters.get("remove_extra_whitespace", True):
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text.strip())
        
        # Normalize unicode if requested
        if parameters.get("normalize_unicode", True):
            import unicodedata
            cleaned_text = unicodedata.normalize('NFKC', cleaned_text)
        
        # Calculate confidence based on text quality
        if len(cleaned_text) == 0:
            confidence = 0.0
        elif len(cleaned_text) < 3:
            confidence = 0.5
        else:
            # Check for reasonable character distribution
            alpha_ratio = sum(c.isalpha() for c in cleaned_text) / len(cleaned_text)
            if alpha_ratio > 0.3:
                confidence = 0.9
            else:
                confidence = 0.6
        
        return cleaned_text, confidence
    
    def _clean_price(self, price: str, parameters: Dict[str, Any]) -> Tuple[str, float]:
        """Clean and normalize price values."""
        if not price or not isinstance(price, str):
            return price, 0.0
        
        cleaned_price = price.strip()
        
        # Extract numeric value
        numeric_match = re.search(r'[\d,]+\.?\d*', cleaned_price)
        if numeric_match:
            numeric_value = numeric_match.group().replace(',', '')
            try:
                float_value = float(numeric_value)
                
                # Format with specified decimal places
                decimal_places = parameters.get("decimal_places", 2)
                formatted_price = f"{float_value:.{decimal_places}f}"
                
                # Add currency symbol if specified
                currency_symbol = parameters.get("currency_symbol")
                if currency_symbol:
                    formatted_price = currency_symbol + formatted_price
                
                return formatted_price, 0.9
            except ValueError:
                return cleaned_price, 0.3
        else:
            return cleaned_price, 0.1
    
    def _validate_data_types(self, content: Dict[str, Any], validation_errors: List[str]) -> float:
        """Validate data types and formats in content."""
        if not content:
            return 0.0
        
        valid_fields = 0
        total_fields = len(content)
        
        for field_name, field_value in content.items():
            if field_value is None:
                continue
            
            try:
                # Basic type validation
                if isinstance(field_value, (str, int, float, bool, list, dict)):
                    valid_fields += 1
                else:
                    validation_errors.append(f"Invalid type for field {field_name}: {type(field_value)}")
                    
            except Exception as e:
                validation_errors.append(f"Type validation error for field {field_name}: {str(e)}")
        
        return valid_fields / total_fields if total_fields > 0 else 0.0
    
    def _generate_content_hash(self, content: Dict[str, Any]) -> str:
        """Generate a hash for content to detect duplicates."""
        # Create a normalized string representation of the content
        content_str = str(sorted(content.items()))
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def detect_duplicates(self, data: List[ScrapedData]) -> List[Tuple[str, str, float]]:
        """
        Detect duplicate records using content hashing and similarity algorithms.
        
        Args:
            data: List of ScrapedData objects to check for duplicates
            
        Returns:
            List of tuples (record_id1, record_id2, similarity_score)
        """
        duplicates = []
        content_hashes = {}
        
        # First pass: exact duplicates using hashes
        for record in data:
            content_hash = self._generate_content_hash(record.content)
            
            if content_hash in content_hashes:
                duplicates.append((content_hashes[content_hash], record.id, 1.0))
            else:
                content_hashes[content_hash] = record.id
        
        # Second pass: similarity-based duplicates
        for i, record1 in enumerate(data):
            for j, record2 in enumerate(data[i+1:], i+1):
                similarity = self._calculate_content_similarity(record1.content, record2.content)
                
                if similarity >= self.similarity_threshold:
                    duplicates.append((record1.id, record2.id, similarity))
        
        self.logger.info(f"Found {len(duplicates)} duplicate pairs")
        return duplicates
    
    def _calculate_content_similarity(self, content1: Dict[str, Any], content2: Dict[str, Any]) -> float:
        """Calculate similarity between two content dictionaries."""
        if not content1 or not content2:
            return 0.0
        
        # Convert to pandas Series for easier comparison
        try:
            df1 = pd.Series(content1)
            df2 = pd.Series(content2)
            
            # Find common keys
            common_keys = set(df1.index) & set(df2.index)
            if not common_keys:
                return 0.0
            
            # Calculate similarity for common fields
            similarities = []
            for key in common_keys:
                val1, val2 = str(df1[key]), str(df2[key])
                
                if val1 == val2:
                    similarities.append(1.0)
                else:
                    # Simple string similarity (Jaccard similarity on words)
                    words1 = set(val1.lower().split())
                    words2 = set(val2.lower().split())
                    
                    if words1 or words2:
                        intersection = len(words1 & words2)
                        union = len(words1 | words2)
                        similarities.append(intersection / union if union > 0 else 0.0)
                    else:
                        similarities.append(0.0)
            
            return sum(similarities) / len(similarities) if similarities else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating content similarity: {str(e)}")
            return 0.0
    
    def _calculate_quality_scores(self, metrics: DataQualityMetrics, cleaned_data: List[ScrapedData]) -> DataQualityMetrics:
        """Calculate overall quality scores for the dataset."""
        if metrics.total_records == 0:
            return metrics
        
        # Calculate completeness score
        metrics.completeness_score = metrics.valid_records / metrics.total_records
        
        # Calculate accuracy score based on validation errors
        total_errors = sum(len(record.validation_errors) for record in cleaned_data)
        max_possible_errors = metrics.valid_records * 5  # Assume max 5 errors per record
        metrics.accuracy_score = max(0.0, 1.0 - (total_errors / max_possible_errors)) if max_possible_errors > 0 else 1.0
        
        # Calculate consistency score based on field quality scores
        if metrics.field_quality_scores:
            field_averages = []
            for field, scores in metrics.field_quality_scores.items():
                if isinstance(scores, list):
                    avg_score = sum(scores) / len(scores)
                    metrics.field_quality_scores[field] = avg_score
                    field_averages.append(avg_score)
                else:
                    field_averages.append(scores)
            
            metrics.consistency_score = sum(field_averages) / len(field_averages) if field_averages else 0.0
        else:
            metrics.consistency_score = 0.0
        
        # Calculate overall quality score
        metrics.overall_quality_score = (
            metrics.completeness_score * 0.4 +
            metrics.accuracy_score * 0.4 +
            metrics.consistency_score * 0.2
        )
        
        return metrics
    
    def generate_quality_report(self, metrics: DataQualityMetrics) -> Dict[str, Any]:
        """Generate a comprehensive data quality report."""
        report = {
            "summary": {
                "total_records": metrics.total_records,
                "valid_records": metrics.valid_records,
                "invalid_records": metrics.invalid_records,
                "duplicate_records": metrics.duplicate_records,
                "corrected_records": metrics.corrected_records,
                "processing_time": metrics.processing_time
            },
            "quality_scores": {
                "overall_quality": metrics.overall_quality_score,
                "completeness": metrics.completeness_score,
                "accuracy": metrics.accuracy_score,
                "consistency": metrics.consistency_score
            },
            "field_quality": metrics.field_quality_scores,
            "validation_errors": metrics.validation_errors,
            "recommendations": self._generate_recommendations(metrics)
        }
        
        return report
    
    def _generate_recommendations(self, metrics: DataQualityMetrics) -> List[str]:
        """Generate recommendations based on quality metrics."""
        recommendations = []
        
        if metrics.completeness_score < 0.8:
            recommendations.append("Consider improving data extraction rules to capture more complete records")
        
        if metrics.accuracy_score < 0.7:
            recommendations.append("Review validation rules and consider additional data cleaning steps")
        
        if metrics.consistency_score < 0.6:
            recommendations.append("Implement more standardized data extraction patterns")
        
        if metrics.duplicate_records > metrics.total_records * 0.1:
            recommendations.append("Implement stronger duplicate detection during scraping")
        
        if metrics.overall_quality_score < 0.7:
            recommendations.append("Consider manual review of cleaning rules and extraction logic")
        
        return recommendations