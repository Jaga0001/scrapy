"""
Confidence Scorer module for assessing data quality and extraction confidence.

This module provides quality assessment capabilities for AI-processed content,
calculating confidence scores based on multiple factors including data completeness,
consistency, and extraction quality.
"""

import asyncio
import logging
import math
from typing import Any, Dict, List, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Quality assessment and confidence scoring for AI-processed content.
    
    Evaluates the quality and reliability of extracted data based on multiple
    factors including completeness, consistency, and extraction confidence.
    """
    
    def __init__(self):
        """Initialize the confidence scorer."""
        self.logger = logging.getLogger(__name__)
        
        # Scoring weights for different factors
        self.weights = {
            "completeness": 0.25,
            "consistency": 0.20,
            "entity_confidence": 0.20,
            "structure_quality": 0.15,
            "content_richness": 0.10,
            "validation_score": 0.10
        }
    
    async def calculate_confidence(
        self,
        structured_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        classification: Dict[str, Any],
        raw_content: str,
        additional_factors: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate overall confidence score for processed content.
        
        Args:
            structured_data: Extracted structured data
            entities: Extracted entities
            classification: Content classification
            raw_content: Original raw content
            additional_factors: Additional scoring factors
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Calculate individual scoring components
            completeness_score = self._calculate_completeness_score(
                structured_data, entities, raw_content
            )
            
            consistency_score = self._calculate_consistency_score(
                structured_data, entities, classification
            )
            
            entity_confidence_score = self._calculate_entity_confidence_score(entities)
            
            structure_quality_score = self._calculate_structure_quality_score(structured_data)
            
            content_richness_score = self._calculate_content_richness_score(
                structured_data, entities, raw_content
            )
            
            validation_score = await self._calculate_validation_score(
                structured_data, entities, raw_content
            )
            
            # Apply additional factors if provided
            if additional_factors:
                self._apply_additional_factors(additional_factors)
            
            # Calculate weighted final score
            final_score = (
                completeness_score * self.weights["completeness"] +
                consistency_score * self.weights["consistency"] +
                entity_confidence_score * self.weights["entity_confidence"] +
                structure_quality_score * self.weights["structure_quality"] +
                content_richness_score * self.weights["content_richness"] +
                validation_score * self.weights["validation_score"]
            )
            
            # Ensure score is within bounds
            final_score = max(0.0, min(1.0, final_score))
            
            self.logger.debug(f"Confidence score calculated: {final_score:.3f}")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            return 0.0  # Return low confidence on error
    
    def _calculate_completeness_score(
        self,
        structured_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        raw_content: str
    ) -> float:
        """Calculate completeness score based on data extraction coverage."""
        
        # Factors that indicate good completeness
        factors = []
        
        # Check if structured data has meaningful content
        if structured_data:
            non_empty_sections = sum(
                1 for key, value in structured_data.items()
                if value and (
                    (isinstance(value, list) and len(value) > 0) or
                    (isinstance(value, dict) and len(value) > 0) or
                    (isinstance(value, str) and len(value.strip()) > 0)
                )
            )
            total_sections = len(structured_data)
            if total_sections > 0:
                factors.append(non_empty_sections / total_sections)
        
        # Check entity extraction coverage
        content_length = len(raw_content)
        if content_length > 0:
            # Estimate expected entities based on content length
            expected_entities = min(content_length // 500, 20)  # Rough estimate
            actual_entities = len(entities)
            entity_coverage = min(actual_entities / max(expected_entities, 1), 1.0)
            factors.append(entity_coverage)
        
        # Check for presence of key data types
        key_data_types = ['title', 'content', 'text', 'name', 'description']
        found_key_types = sum(
            1 for key_type in key_data_types
            if any(key_type in str(key).lower() for key in structured_data.keys())
        )
        if len(key_data_types) > 0:
            factors.append(found_key_types / len(key_data_types))
        
        # Return average of all factors
        return sum(factors) / len(factors) if factors else 0.0
    
    def _calculate_consistency_score(
        self,
        structured_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        classification: Dict[str, Any]
    ) -> float:
        """Calculate consistency score based on data coherence."""
        
        factors = []
        
        # Check entity confidence consistency
        if entities:
            confidences = [
                entity.get('confidence', 0.5) for entity in entities
                if isinstance(entity.get('confidence'), (int, float))
            ]
            if confidences:
                # Lower variance in confidence scores indicates better consistency
                mean_confidence = sum(confidences) / len(confidences)
                variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
                consistency_factor = max(0, 1 - variance)
                factors.append(consistency_factor)
        
        # Check classification confidence
        classification_confidence = classification.get('confidence', 0.5)
        if isinstance(classification_confidence, (int, float)):
            factors.append(classification_confidence)
        
        # Check for data type consistency within structured data
        type_consistency = self._check_data_type_consistency(structured_data)
        factors.append(type_consistency)
        
        return sum(factors) / len(factors) if factors else 0.5
    
    def _calculate_entity_confidence_score(self, entities: List[Dict[str, Any]]) -> float:
        """Calculate average confidence score from extracted entities."""
        
        if not entities:
            return 0.0
        
        confidences = []
        for entity in entities:
            confidence = entity.get('confidence', 0.5)
            if isinstance(confidence, (int, float)):
                confidences.append(confidence)
        
        if not confidences:
            return 0.0
        
        # Calculate weighted average (higher confidence entities get more weight)
        total_weight = sum(confidences)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(c * c for c in confidences)  # Square for weighting
        return weighted_sum / total_weight
    
    def _calculate_structure_quality_score(self, structured_data: Dict[str, Any]) -> float:
        """Calculate quality score based on structure organization."""
        
        if not structured_data:
            return 0.0
        
        factors = []
        
        # Check depth and organization
        max_depth = self._calculate_data_depth(structured_data)
        # Optimal depth is 2-4 levels
        depth_score = 1.0 - abs(max_depth - 3) / 5.0
        factors.append(max(0.0, depth_score))
        
        # Check for balanced structure (not too many empty vs full sections)
        empty_sections = sum(
            1 for value in structured_data.values()
            if not value or (isinstance(value, (list, dict)) and len(value) == 0)
        )
        total_sections = len(structured_data)
        balance_score = 1.0 - (empty_sections / total_sections) if total_sections > 0 else 0.0
        factors.append(balance_score)
        
        # Check for appropriate data types
        type_appropriateness = self._check_type_appropriateness(structured_data)
        factors.append(type_appropriateness)
        
        return sum(factors) / len(factors) if factors else 0.0
    
    def _calculate_content_richness_score(
        self,
        structured_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        raw_content: str
    ) -> float:
        """Calculate score based on content richness and information density."""
        
        factors = []
        
        # Information extraction ratio
        extracted_text_length = self._estimate_extracted_text_length(structured_data)
        raw_content_length = len(raw_content.strip())
        
        if raw_content_length > 0:
            extraction_ratio = min(extracted_text_length / raw_content_length, 1.0)
            # Optimal extraction ratio is 0.3-0.8 (not too little, not everything)
            if 0.3 <= extraction_ratio <= 0.8:
                ratio_score = 1.0
            elif extraction_ratio < 0.3:
                ratio_score = extraction_ratio / 0.3
            else:
                ratio_score = 1.0 - (extraction_ratio - 0.8) / 0.2
            factors.append(max(0.0, ratio_score))
        
        # Entity diversity
        if entities:
            entity_types = set(entity.get('type', 'unknown') for entity in entities)
            diversity_score = min(len(entity_types) / 5.0, 1.0)  # Up to 5 types is good
            factors.append(diversity_score)
        
        # Structured data variety
        if structured_data:
            data_variety = len([k for k, v in structured_data.items() if v])
            variety_score = min(data_variety / 8.0, 1.0)  # Up to 8 different data types
            factors.append(variety_score)
        
        return sum(factors) / len(factors) if factors else 0.0
    
    async def _calculate_validation_score(
        self,
        structured_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        raw_content: str
    ) -> float:
        """Calculate validation score based on data quality checks."""
        
        factors = []
        
        # Email validation
        email_entities = [e for e in entities if e.get('type') == 'EMAIL']
        if email_entities:
            valid_emails = sum(
                1 for email in email_entities
                if self._validate_email(email.get('value', ''))
            )
            email_score = valid_emails / len(email_entities)
            factors.append(email_score)
        
        # URL validation
        url_entities = [e for e in entities if e.get('type') == 'URL']
        if url_entities:
            valid_urls = sum(
                1 for url in url_entities
                if self._validate_url(url.get('value', ''))
            )
            url_score = valid_urls / len(url_entities)
            factors.append(url_score)
        
        # Phone number validation
        phone_entities = [e for e in entities if e.get('type') == 'PHONE']
        if phone_entities:
            valid_phones = sum(
                1 for phone in phone_entities
                if self._validate_phone(phone.get('value', ''))
            )
            phone_score = valid_phones / len(phone_entities)
            factors.append(phone_score)
        
        # Data consistency validation
        consistency_score = self._validate_data_consistency(structured_data)
        factors.append(consistency_score)
        
        return sum(factors) / len(factors) if factors else 0.8  # Default good score
    
    def _check_data_type_consistency(self, data: Dict[str, Any]) -> float:
        """Check consistency of data types within the structure."""
        
        if not data:
            return 0.0
        
        consistency_issues = 0
        total_checks = 0
        
        for key, value in data.items():
            total_checks += 1
            
            # Check if arrays contain consistent types
            if isinstance(value, list) and value:
                first_type = type(value[0])
                if not all(isinstance(item, first_type) for item in value):
                    consistency_issues += 1
            
            # Check if expected data types match content
            if 'date' in key.lower() and isinstance(value, str):
                if not self._looks_like_date(value):
                    consistency_issues += 1
            
            if 'price' in key.lower() or 'cost' in key.lower():
                if not self._looks_like_price(str(value)):
                    consistency_issues += 1
        
        if total_checks == 0:
            return 1.0
        
        return 1.0 - (consistency_issues / total_checks)
    
    def _calculate_data_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate maximum depth of nested data structure."""
        
        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(
                self._calculate_data_depth(value, current_depth + 1)
                for value in data.values()
            )
        elif isinstance(data, list):
            if not data:
                return current_depth
            return max(
                self._calculate_data_depth(item, current_depth + 1)
                for item in data
            )
        else:
            return current_depth
    
    def _check_type_appropriateness(self, data: Dict[str, Any]) -> float:
        """Check if data types are appropriate for their keys."""
        
        appropriate_count = 0
        total_count = 0
        
        for key, value in data.items():
            total_count += 1
            key_lower = key.lower()
            
            # Check type appropriateness
            if 'list' in key_lower or 'items' in key_lower:
                if isinstance(value, list):
                    appropriate_count += 1
            elif 'count' in key_lower or 'number' in key_lower:
                if isinstance(value, (int, float)):
                    appropriate_count += 1
            elif 'url' in key_lower or 'link' in key_lower:
                if isinstance(value, str) and ('http' in value or value.startswith('/')):
                    appropriate_count += 1
            else:
                # Default: most keys should have non-empty values
                if value is not None and value != "":
                    appropriate_count += 1
        
        return appropriate_count / total_count if total_count > 0 else 1.0
    
    def _estimate_extracted_text_length(self, structured_data: Dict[str, Any]) -> int:
        """Estimate total length of extracted text content."""
        
        total_length = 0
        
        def count_text_length(obj):
            nonlocal total_length
            if isinstance(obj, str):
                total_length += len(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    count_text_length(value)
            elif isinstance(obj, list):
                for item in obj:
                    count_text_length(item)
        
        count_text_length(structured_data)
        return total_length
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_url(self, url: str) -> bool:
        """Basic URL validation."""
        return url.startswith(('http://', 'https://', 'ftp://')) and '.' in url
    
    def _validate_phone(self, phone: str) -> bool:
        """Basic phone number validation."""
        import re
        # Remove common formatting characters
        cleaned = re.sub(r'[^\d+]', '', phone)
        # Check if it looks like a phone number (7-15 digits)
        return 7 <= len(cleaned) <= 15 and (cleaned.isdigit() or cleaned.startswith('+'))
    
    def _validate_data_consistency(self, structured_data: Dict[str, Any]) -> float:
        """Validate internal consistency of structured data."""
        
        consistency_score = 1.0
        
        # Check for duplicate information
        text_values = []
        
        def collect_text_values(obj):
            if isinstance(obj, str) and len(obj.strip()) > 3:
                text_values.append(obj.strip().lower())
            elif isinstance(obj, dict):
                for value in obj.values():
                    collect_text_values(value)
            elif isinstance(obj, list):
                for item in obj:
                    collect_text_values(item)
        
        collect_text_values(structured_data)
        
        if text_values:
            unique_values = set(text_values)
            duplicate_ratio = 1.0 - (len(unique_values) / len(text_values))
            # Some duplication is normal, penalize excessive duplication
            if duplicate_ratio > 0.5:
                consistency_score *= 0.7
        
        return consistency_score
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if string looks like a date."""
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}',
            r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}'
        ]
        return any(re.search(pattern, value) for pattern in date_patterns)
    
    def _looks_like_price(self, value: str) -> bool:
        """Check if string looks like a price."""
        import re
        price_patterns = [
            r'\$\d+\.?\d*',
            r'\d+\.?\d*\s*USD',
            r'\d+\.?\d*\s*EUR',
            r'£\d+\.?\d*',
            r'\d+\.?\d*'
        ]
        return any(re.search(pattern, value) for pattern in price_patterns)
    
    def _apply_additional_factors(self, additional_factors: Dict[str, Any]) -> None:
        """Apply additional scoring factors to weights."""
        
        # Adjust weights based on additional factors
        if 'processing_time' in additional_factors:
            processing_time = additional_factors['processing_time']
            # Penalize very slow processing (might indicate issues)
            if processing_time > 30:  # seconds
                self.weights['validation_score'] *= 0.8
        
        if 'source_reliability' in additional_factors:
            reliability = additional_factors['source_reliability']
            # Boost confidence for reliable sources
            if reliability > 0.8:
                for key in self.weights:
                    self.weights[key] *= 1.1
    
    def get_detailed_score_breakdown(
        self,
        structured_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        classification: Dict[str, Any],
        raw_content: str
    ) -> Dict[str, float]:
        """
        Get detailed breakdown of confidence score components.
        
        Returns:
            Dictionary with individual component scores
        """
        
        return {
            "completeness": self._calculate_completeness_score(
                structured_data, entities, raw_content
            ),
            "consistency": self._calculate_consistency_score(
                structured_data, entities, classification
            ),
            "entity_confidence": self._calculate_entity_confidence_score(entities),
            "structure_quality": self._calculate_structure_quality_score(structured_data),
            "content_richness": self._calculate_content_richness_score(
                structured_data, entities, raw_content
            )
        }