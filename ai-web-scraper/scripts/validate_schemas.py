#!/usr/bin/env python3
"""
Schema validation and consistency checker.

This script validates all Pydantic models and API schemas for consistency,
proper validation, and alignment with the authentication system changes.
"""

import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import ValidationError

# Import all models and schemas
from src.models.pydantic_models import (
    User, UserRole, JWTPayload, ScrapingJob, ScrapedData, 
    ScrapingConfig, JobStatus, ContentType
)
from src.api.schemas import (
    LoginRequest, LoginResponse, UserRegistrationRequest, UserResponse,
    TokenValidationResponse, RefreshTokenRequest, RefreshTokenResponse,
    CreateJobRequest, DataQueryRequest, JobResponse, DataResponse
)


class SchemaValidator:
    """Validates schema consistency and data integrity."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        
    def log_error(self, message: str):
        """Log a validation error."""
        self.errors.append(message)
        print(f"❌ ERROR: {message}")
    
    def log_warning(self, message: str):
        """Log a validation warning."""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")
    
    def log_success(self, message: str):
        """Log a successful validation."""
        self.success_count += 1
        print(f"✅ SUCCESS: {message}")
    
    def validate_user_models(self):
        """Validate User and related authentication models."""
        print("\n🔍 Validating User Models...")
        
        # Test valid user creation
        try:
            user = User(
                user_id="test-001",
                username="testuser",
                email="test@example.com",
                roles=[UserRole.USER]
            )
            self.log_success("User model creation with valid data")
        except Exception as e:
            self.log_error(f"User model creation failed: {e}")
        
        # Test email validation
        try:
            User(
                user_id="test-002",
                username="testuser2",
                email="invalid-email",
                roles=[UserRole.USER]
            )
            self.log_error("User model should reject invalid email")
        except ValidationError:
            self.log_success("User model correctly rejects invalid email")
        except Exception as e:
            self.log_error(f"Unexpected error in email validation: {e}")
        
        # Test username validation
        try:
            User(
                user_id="test-003",
                username="invalid@username!",
                email="test@example.com",
                roles=[UserRole.USER]
            )
            self.log_error("User model should reject invalid username")
        except ValidationError:
            self.log_success("User model correctly rejects invalid username")
        except Exception as e:
            self.log_error(f"Unexpected error in username validation: {e}")
    
    def validate_jwt_models(self):
        """Validate JWT payload models."""
        print("\n🔍 Validating JWT Models...")
        
        current_time = int(time.time())
        
        # Test valid JWT payload
        try:
            payload = JWTPayload(
                user_id="test-001",
                username="testuser",
                email="test@example.com",
                roles=["user"],
                exp=current_time + 3600,
                iat=current_time,
                type="access"
            )
            self.log_success("JWTPayload model creation with valid data")
        except Exception as e:
            self.log_error(f"JWTPayload model creation failed: {e}")
        
        # Test expired token validation
        try:
            JWTPayload(
                user_id="test-002",
                username="testuser2",
                exp=current_time - 3600,  # Expired
                iat=current_time - 7200,
                type="access"
            )
            self.log_error("JWTPayload should reject expired tokens")
        except ValidationError:
            self.log_success("JWTPayload correctly rejects expired tokens")
        except Exception as e:
            self.log_error(f"Unexpected error in JWT expiration validation: {e}")
        
        # Test invalid token type
        try:
            JWTPayload(
                user_id="test-003",
                username="testuser3",
                exp=current_time + 3600,
                iat=current_time,
                type="invalid"
            )
            self.log_error("JWTPayload should reject invalid token types")
        except ValidationError:
            self.log_success("JWTPayload correctly rejects invalid token types")
        except Exception as e:
            self.log_error(f"Unexpected error in JWT type validation: {e}")
    
    def validate_api_schemas(self):
        """Validate API request/response schemas."""
        print("\n🔍 Validating API Schemas...")
        
        # Test LoginRequest
        try:
            login_req = LoginRequest(
                username="testuser",
                password="TestPass123!"
            )
            self.log_success("LoginRequest schema validation")
        except Exception as e:
            self.log_error(f"LoginRequest schema validation failed: {e}")
        
        # Test UserRegistrationRequest
        try:
            reg_req = UserRegistrationRequest(
                username="newuser",
                email="new@example.com",
                password="StrongPass123!",
                full_name="New User"
            )
            self.log_success("UserRegistrationRequest schema validation")
        except Exception as e:
            self.log_error(f"UserRegistrationRequest schema validation failed: {e}")
        
        # Test weak password rejection
        try:
            UserRegistrationRequest(
                username="newuser",
                email="new@example.com",
                password="weak",
                full_name="New User"
            )
            self.log_error("UserRegistrationRequest should reject weak passwords")
        except ValidationError:
            self.log_success("UserRegistrationRequest correctly rejects weak passwords")
        except Exception as e:
            self.log_error(f"Unexpected error in password validation: {e}")
    
    def validate_scraping_models(self):
        """Validate scraping-related models for consistency."""
        print("\n🔍 Validating Scraping Models...")
        
        # Test ScrapingJob with user_id field
        try:
            job = ScrapingJob(
                url="https://example.com",
                user_id="test-user-001"
            )
            self.log_success("ScrapingJob model includes user_id field")
        except Exception as e:
            self.log_error(f"ScrapingJob model validation failed: {e}")
        
        # Test ScrapedData model
        try:
            data = ScrapedData(
                job_id="job-001",
                url="https://example.com",
                content={"title": "Test Page", "text": "Sample content"}
            )
            self.log_success("ScrapedData model validation")
        except Exception as e:
            self.log_error(f"ScrapedData model validation failed: {e}")
    
    def validate_export_consistency(self):
        """Validate export format consistency."""
        print("\n🔍 Validating Export Format Consistency...")
        
        # Create sample data
        try:
            user = User(
                user_id="export-test-001",
                username="exportuser",
                email="export@example.com",
                roles=[UserRole.USER]
            )
            
            job = ScrapingJob(
                url="https://example.com",
                user_id=user.user_id
            )
            
            data = ScrapedData(
                job_id=job.id,
                url=job.url,
                content={"title": "Export Test", "data": "Sample"}
            )
            
            # Check if all required fields are present for export
            export_fields = ["id", "job_id", "url", "content", "extracted_at"]
            missing_fields = []
            
            for field in export_fields:
                if not hasattr(data, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self.log_error(f"ScrapedData missing export fields: {missing_fields}")
            else:
                self.log_success("ScrapedData contains all required export fields")
                
        except Exception as e:
            self.log_error(f"Export consistency validation failed: {e}")
    
    def validate_ai_processing_alignment(self):
        """Validate AI processing schema alignment."""
        print("\n🔍 Validating AI Processing Alignment...")
        
        try:
            # Test ScrapedData with AI processing fields
            data = ScrapedData(
                job_id="ai-test-001",
                url="https://example.com",
                content={"title": "AI Test", "text": "Content for AI processing"},
                ai_processed=True,
                confidence_score=0.95,
                ai_metadata={
                    "model": "gemini-2.5",
                    "processing_time": 1.2,
                    "categories": ["technology", "web"]
                }
            )
            
            # Validate AI-specific fields
            if data.ai_processed and data.confidence_score > 0:
                self.log_success("ScrapedData AI processing fields are consistent")
            else:
                self.log_error("ScrapedData AI processing fields are inconsistent")
                
        except Exception as e:
            self.log_error(f"AI processing alignment validation failed: {e}")
    
    def generate_sample_data_tests(self):
        """Generate sample data for testing."""
        print("\n🔍 Generating Sample Data Tests...")
        
        try:
            # Generate sample user
            sample_user = User(
                user_id="sample-001",
                username="sampleuser",
                email="sample@example.com",
                full_name="Sample User",
                roles=[UserRole.USER]
            )
            
            # Generate sample job
            sample_job = ScrapingJob(
                url="https://example.com/sample",
                user_id=sample_user.user_id,
                tags=["sample", "test"]
            )
            
            # Generate sample data
            sample_data = ScrapedData(
                job_id=sample_job.id,
                url=sample_job.url,
                content={
                    "title": "Sample Page",
                    "description": "This is a sample page for testing",
                    "links": ["https://example.com/link1", "https://example.com/link2"],
                    "metadata": {"author": "Test Author", "date": "2024-01-01"}
                },
                confidence_score=0.88,
                ai_processed=True
            )
            
            self.log_success("Sample data generation completed")
            
            # Save sample data to file for testing
            sample_data_dict = {
                "user": sample_user.model_dump(),
                "job": sample_job.model_dump(),
                "data": sample_data.model_dump()
            }
            
            with open("sample_test_data.json", "w") as f:
                json.dump(sample_data_dict, f, indent=2, default=str)
            
            self.log_success("Sample data saved to sample_test_data.json")
            
        except Exception as e:
            self.log_error(f"Sample data generation failed: {e}")
    
    def run_all_validations(self):
        """Run all validation checks."""
        print("🚀 Starting Schema Validation and Consistency Checks...")
        
        self.validate_user_models()
        self.validate_jwt_models()
        self.validate_api_schemas()
        self.validate_scraping_models()
        self.validate_export_consistency()
        self.validate_ai_processing_alignment()
        self.generate_sample_data_tests()
        
        # Print summary
        print(f"\n📊 Validation Summary:")
        print(f"✅ Successful validations: {self.success_count}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.errors:
            print(f"\n❌ Errors found:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        return len(self.errors) == 0


if __name__ == "__main__":
    validator = SchemaValidator()
    success = validator.run_all_validations()
    
    if success:
        print(f"\n🎉 All validations passed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Validation failed with {len(validator.errors)} errors")
        sys.exit(1)