#!/usr/bin/env python3
"""
Security validation script for the AI Web Scraper project.

This script validates security configuration and identifies potential vulnerabilities.
Run this before deploying to production.
"""

import os
import re
import sys
from typing import List, Dict, Any
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from src.config.security_config import get_security_settings, validate_security_configuration
    from src.utils.security_init import validate_runtime_security
except ImportError as e:
    print(f"Error importing security modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class SecurityValidator:
    """Comprehensive security validator for the web scraper project."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed_checks = []
    
    def validate_environment_variables(self) -> None:
        """Validate critical environment variables."""
        print("🔍 Validating environment variables...")
        
        # Critical environment variables that must be set
        critical_vars = {
            "JWT_SECRET_KEY": {
                "min_length": 32,
                "description": "JWT signing secret"
            },
            "ENCRYPTION_MASTER_KEY": {
                "min_length": 32,
                "description": "Master encryption key"
            },
            "AUDIT_CHECKSUM_SALT": {
                "min_length": 16,
                "description": "Audit log integrity salt"
            },
            "GEMINI_API_KEY": {
                "pattern": r"^AIza[A-Za-z0-9_-]{35}$",
                "description": "Gemini API key"
            }
        }
        
        for var_name, requirements in critical_vars.items():
            value = os.getenv(var_name)
            
            if not value:
                self.issues.append(f"❌ {var_name} is not set (required for {requirements['description']})")
                continue
            
            # Check minimum length
            if "min_length" in requirements and len(value) < requirements["min_length"]:
                self.issues.append(
                    f"❌ {var_name} is too short (minimum {requirements['min_length']} characters)"
                )
                continue
            
            # Check pattern
            if "pattern" in requirements and not re.match(requirements["pattern"], value):
                self.issues.append(f"❌ {var_name} format is invalid")
                continue
            
            self.passed_checks.append(f"✅ {var_name} is properly configured")
        
        # Check for insecure defaults
        insecure_defaults = {
            "JWT_SECRET_KEY": ["change-this-in-production", "secret", "key", "test"],
            "ENCRYPTION_MASTER_KEY": ["change-this", "secret", "key", "test"],
            "DB_PASSWORD": ["password", "admin", "root", "test"],
            "REDIS_PASSWORD": ["password", "admin", "redis", "test"]
        }
        
        for var_name, bad_values in insecure_defaults.items():
            value = os.getenv(var_name, "").lower()
            if any(bad_val in value for bad_val in bad_values):
                self.issues.append(f"❌ {var_name} appears to use an insecure default value")
    
    def validate_file_permissions(self) -> None:
        """Validate file permissions for security-sensitive files."""
        print("🔍 Validating file permissions...")
        
        sensitive_files = [
            ".env",
            ".env.production",
            "config/secure_config.enc",
            "logs/audit.log"
        ]
        
        for file_path in sensitive_files:
            if os.path.exists(file_path):
                file_stat = os.stat(file_path)
                file_mode = file_stat.st_mode & 0o777
                
                # Check if file is readable by others (should be 600 or 640)
                if file_mode & 0o044:
                    self.issues.append(f"❌ {file_path} is readable by others (permissions: {oct(file_mode)})")
                
                # Check if file is writable by others
                if file_mode & 0o022:
                    self.issues.append(f"❌ {file_path} is writable by others (permissions: {oct(file_mode)})")
                
                if file_mode == 0o600:
                    self.passed_checks.append(f"✅ {file_path} has secure permissions")
    
    def validate_cors_configuration(self) -> None:
        """Validate CORS configuration."""
        print("🔍 Validating CORS configuration...")
        
        cors_origins = os.getenv("CORS_ORIGINS", "")
        
        if not cors_origins:
            self.warnings.append("⚠️  CORS_ORIGINS not configured - using defaults")
            return
        
        origins = [origin.strip() for origin in cors_origins.split(",")]
        
        for origin in origins:
            if origin == "*":
                self.issues.append("❌ CORS allows all origins (*) - security risk in production")
            elif origin.startswith("http://") and os.getenv("ENVIRONMENT") == "production":
                self.warnings.append(f"⚠️  CORS origin uses HTTP in production: {origin}")
            elif origin.startswith("https://"):
                self.passed_checks.append(f"✅ CORS origin uses HTTPS: {origin}")
    
    def validate_database_security(self) -> None:
        """Validate database security configuration."""
        print("🔍 Validating database security...")
        
        db_ssl_mode = os.getenv("DB_SSL_MODE", "prefer")
        environment = os.getenv("ENVIRONMENT", "development")
        
        if environment == "production" and db_ssl_mode not in ["require", "verify-ca", "verify-full"]:
            self.issues.append(f"❌ Database SSL mode '{db_ssl_mode}' is not secure for production")
        elif db_ssl_mode in ["require", "verify-ca", "verify-full"]:
            self.passed_checks.append(f"✅ Database SSL mode is secure: {db_ssl_mode}")
        
        # Check for database URL format (may expose credentials in logs)
        if os.getenv("DATABASE_URL"):
            self.warnings.append("⚠️  DATABASE_URL format detected - consider using separate DB_* variables")
    
    def validate_scraping_security(self) -> None:
        """Validate scraping security configuration."""
        print("🔍 Validating scraping security...")
        
        # Check user agents
        user_agents = os.getenv("SCRAPER_USER_AGENTS", "")
        if user_agents:
            agents = user_agents.split("|")
            for agent in agents:
                # Check for system-specific information that could fingerprint
                if any(keyword in agent.lower() for keyword in ["windows", "mac", "linux", "chrome", "firefox", "safari"]):
                    self.warnings.append(f"⚠️  User agent may be fingerprintable: {agent[:50]}...")
                else:
                    self.passed_checks.append("✅ User agents appear generic")
                    break
        
        # Check robots.txt respect
        respect_robots = os.getenv("SCRAPER_RESPECT_ROBOTS_TXT", "true").lower()
        if respect_robots == "true":
            self.passed_checks.append("✅ Robots.txt respect is enabled")
        else:
            self.warnings.append("⚠️  Robots.txt respect is disabled - may violate website policies")
        
        # Check SSL validation
        validate_ssl = os.getenv("SCRAPER_VALIDATE_SSL", "true").lower()
        if validate_ssl == "true":
            self.passed_checks.append("✅ SSL validation is enabled")
        else:
            self.issues.append("❌ SSL validation is disabled - security risk")
    
    def validate_logging_security(self) -> None:
        """Validate logging security configuration."""
        print("🔍 Validating logging security...")
        
        log_level = os.getenv("LOG_LEVEL", "INFO")
        environment = os.getenv("ENVIRONMENT", "development")
        
        if environment == "production" and log_level == "DEBUG":
            self.warnings.append("⚠️  DEBUG logging enabled in production - may expose sensitive data")
        
        # Check if logs are structured (JSON format is more secure)
        log_format = os.getenv("LOG_FORMAT", "text")
        if log_format == "json":
            self.passed_checks.append("✅ Structured JSON logging is enabled")
        else:
            self.warnings.append("⚠️  Consider using JSON log format for better security")
    
    def check_for_hardcoded_secrets(self) -> None:
        """Check source code for hardcoded secrets."""
        print("🔍 Scanning for hardcoded secrets...")
        
        # Patterns that might indicate hardcoded secrets
        secret_patterns = [
            (r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']', "API key"),
            (r'secret\s*=\s*["\'][^"\']{10,}["\']', "Secret"),
            (r'password\s*=\s*["\'][^"\']{5,}["\']', "Password"),
            (r'token\s*=\s*["\'][^"\']{10,}["\']', "Token"),
            (r'AIza[A-Za-z0-9_-]{35}', "Google API key"),
            (r'sk-[A-Za-z0-9]{20,}', "OpenAI API key"),
        ]
        
        python_files = list(Path("src").rglob("*.py"))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern, secret_type in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        self.issues.append(
                            f"❌ Potential hardcoded {secret_type} in {file_path}:{line_num}"
                        )
            except Exception as e:
                self.warnings.append(f"⚠️  Could not scan {file_path}: {e}")
        
        if not any("hardcoded" in issue for issue in self.issues):
            self.passed_checks.append("✅ No hardcoded secrets detected in source code")
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all security validations."""
        print("🛡️  Starting comprehensive security validation...\n")
        
        self.validate_environment_variables()
        self.validate_file_permissions()
        self.validate_cors_configuration()
        self.validate_database_security()
        self.validate_scraping_security()
        self.validate_logging_security()
        self.check_for_hardcoded_secrets()
        
        # Run built-in validations
        try:
            config_warnings = validate_security_configuration()
            runtime_issues = validate_runtime_security()
            
            self.warnings.extend([f"⚠️  {w}" for w in config_warnings])
            self.issues.extend([f"❌ {i}" for i in runtime_issues])
        except Exception as e:
            self.warnings.append(f"⚠️  Could not run built-in validations: {e}")
        
        return {
            "issues": self.issues,
            "warnings": self.warnings,
            "passed_checks": self.passed_checks,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings),
            "total_passed": len(self.passed_checks)
        }


def generate_security_report(results: Dict[str, Any]) -> None:
    """Generate a comprehensive security report."""
    print("\n" + "="*80)
    print("🛡️  SECURITY VALIDATION REPORT")
    print("="*80)
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   ✅ Passed Checks: {results['total_passed']}")
    print(f"   ⚠️  Warnings: {results['total_warnings']}")
    print(f"   ❌ Issues: {results['total_issues']}")
    
    # Security score
    total_checks = results['total_passed'] + results['total_warnings'] + results['total_issues']
    if total_checks > 0:
        score = (results['total_passed'] / total_checks) * 100
        print(f"   🎯 Security Score: {score:.1f}%")
    
    # Issues (Critical)
    if results['issues']:
        print(f"\n❌ CRITICAL ISSUES ({len(results['issues'])}):")
        for issue in results['issues']:
            print(f"   {issue}")
    
    # Warnings
    if results['warnings']:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"   {warning}")
    
    # Passed checks
    if results['passed_checks']:
        print(f"\n✅ PASSED CHECKS ({len(results['passed_checks'])}):")
        for check in results['passed_checks']:
            print(f"   {check}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if results['issues']:
        print("   1. Fix all critical issues before deploying to production")
        print("   2. Generate secure secrets with: openssl rand -hex 32")
        print("   3. Set proper file permissions: chmod 600 .env")
        print("   4. Use HTTPS for all external connections in production")
    
    if results['total_issues'] == 0:
        print("   🎉 Great! No critical security issues found.")
        print("   📋 Review warnings and consider implementing suggested improvements.")
    
    print("\n" + "="*80)


def main():
    """Main function to run security validation."""
    validator = SecurityValidator()
    results = validator.run_all_validations()
    generate_security_report(results)
    
    # Exit with error code if critical issues found
    if results['total_issues'] > 0:
        print(f"\n🚨 Security validation failed with {results['total_issues']} critical issues!")
        print("   Please fix these issues before deploying to production.")
        sys.exit(1)
    else:
        print(f"\n🎉 Security validation passed!")
        if results['total_warnings'] > 0:
            print(f"   Consider addressing {results['total_warnings']} warnings for improved security.")
        sys.exit(0)


if __name__ == "__main__":
    main()