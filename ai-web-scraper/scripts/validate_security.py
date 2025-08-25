#!/usr/bin/env python3
"""
Security validation script for the AI Web Scraper project.

This script validates the security configuration and identifies potential
security issues before deployment.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SecurityValidator:
    """Validates security configuration and identifies vulnerabilities."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
        
    def validate_environment_file(self, env_file: Path) -> None:
        """Validate .env file for security issues."""
        if not env_file.exists():
            self.warnings.append(f"Environment file not found: {env_file}")
            return
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Check for placeholder values
        placeholder_patterns = [
            r'your_.*',
            r'example.*',
            r'test.*',
            r'placeholder.*',
            r'changeme.*',
            r'password123',
            r'admin',
            r'root'
        ]
        
        for line_num, line in enumerate(content.split('\n'), 1):
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                # Check for placeholder values
                for pattern in placeholder_patterns:
                    if re.match(pattern, value.lower()):
                        self.issues.append(
                            f"{env_file}:{line_num} - Placeholder value detected: {key}={value}"
                        )
                
                # Check specific security requirements
                if key == 'SECRET_KEY' and len(value) < 32:
                    self.issues.append(
                        f"{env_file}:{line_num} - SECRET_KEY too short (minimum 32 characters)"
                    )
                
                if key == 'GEMINI_API_KEY':
                    if not value.startswith('AIza') or len(value) != 39:
                        self.issues.append(
                            f"{env_file}:{line_num} - Invalid Gemini API key format"
                        )
                
                if 'PASSWORD' in key and len(value) < 12:
                    self.issues.append(
                        f"{env_file}:{line_num} - Password too short: {key} (minimum 12 characters)"
                    )
                
                if key.endswith('_URL') and 'localhost' not in value:
                    parsed = urlparse(value)
                    if parsed.password:
                        self.warnings.append(
                            f"{env_file}:{line_num} - URL contains embedded credentials: {key}"
                        )
    
    def validate_redis_configuration(self) -> None:
        """Validate Redis configuration security."""
        try:
            from src.config.redis_config import RedisSettings, validate_redis_configuration
            
            # Test Redis settings validation
            try:
                validate_redis_configuration()
                self.info.append("Redis configuration validation passed")
            except Exception as e:
                self.issues.append(f"Redis configuration validation failed: {str(e)}")
                
        except ImportError:
            self.warnings.append("Redis configuration module not found")
    
    def scan_source_code(self) -> None:
        """Scan source code for hardcoded secrets."""
        source_dirs = [
            project_root / "src",
            project_root / "tests",
            project_root / "scripts"
        ]
        
        # Patterns to look for
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
            (r'redis://[^@]*:[^@]*@', "Redis URL with credentials"),
            (r'postgresql://[^@]*:[^@]*@', "PostgreSQL URL with credentials"),
            (r'AIza[0-9A-Za-z-_]{35}', "Google API key"),
        ]
        
        for source_dir in source_dirs:
            if not source_dir.exists():
                continue
                
            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for line_num, line in enumerate(content.split('\n'), 1):
                        for pattern, description in secret_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                # Skip comments, test files, and pattern definitions
                                if (line.strip().startswith('#') or 
                                    'test' in str(py_file).lower() and 
                                    any(test_word in line.lower() for test_word in ['test', 'mock', 'example']) or
                                    'pattern' in line.lower() or
                                    'r\'' in line or
                                    'security_patterns' in line.lower() or
                                    'secret_patterns' in line.lower()):
                                    continue
                                
                                self.issues.append(
                                    f"{py_file}:{line_num} - {description}: {line.strip()}"
                                )
                                
                except Exception as e:
                    self.warnings.append(f"Could not scan {py_file}: {str(e)}")
    
    def check_file_permissions(self) -> None:
        """Check file permissions for sensitive files."""
        sensitive_files = [
            project_root / ".env",
            project_root / ".env.local",
            project_root / ".env.production",
        ]
        
        for file_path in sensitive_files:
            if file_path.exists():
                stat = file_path.stat()
                mode = oct(stat.st_mode)[-3:]
                
                if mode != '600':
                    self.warnings.append(
                        f"Insecure file permissions for {file_path}: {mode} (should be 600)"
                    )
                else:
                    self.info.append(f"Secure file permissions for {file_path}: {mode}")
    
    def validate_logging_security(self) -> None:
        """Check for potential credential exposure in logging."""
        log_patterns = [
            (r'logger\.(info|debug|warning|error).*redis_url', "Redis URL in logs"),
            (r'logger\.(info|debug|warning|error).*password', "Password in logs"),
            (r'logger\.(info|debug|warning|error).*api_key', "API key in logs"),
            (r'logger\.(info|debug|warning|error).*secret', "Secret in logs"),
        ]
        
        source_files = list((project_root / "src").rglob("*.py"))
        
        for py_file in source_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern, description in log_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check if it's using a sanitized version
                            if 'sanitize' in line.lower() or 'safe' in line.lower():
                                self.info.append(
                                    f"{py_file}:{line_num} - Secure logging detected: {description}"
                                )
                            else:
                                self.warnings.append(
                                    f"{py_file}:{line_num} - Potential credential exposure: {description}"
                                )
                                
            except Exception as e:
                self.warnings.append(f"Could not scan {py_file}: {str(e)}")
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all security validations."""
        print("🔍 Running security validation...")
        
        # Validate environment files
        env_files = [
            project_root / ".env",
            project_root / ".env.local",
            project_root / ".env.production",
        ]
        
        for env_file in env_files:
            self.validate_environment_file(env_file)
        
        # Run other validations
        self.validate_redis_configuration()
        self.scan_source_code()
        self.check_file_permissions()
        self.validate_logging_security()
        
        return {
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info
        }
    
    def print_results(self, results: Dict[str, Any]) -> int:
        """Print validation results and return exit code."""
        issues = results["issues"]
        warnings = results["warnings"]
        info = results["info"]
        
        print("\n" + "="*60)
        print("SECURITY VALIDATION RESULTS")
        print("="*60)
        
        if issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(issues)}):")
            for issue in issues:
                print(f"   ❌ {issue}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"   ⚠️  {warning}")
        
        if info:
            print(f"\n✅ INFORMATION ({len(info)}):")
            for item in info:
                print(f"   ℹ️  {item}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Critical Issues: {len(issues)}")
        print(f"   Warnings: {len(warnings)}")
        print(f"   Info Items: {len(info)}")
        
        if issues:
            print(f"\n❌ VALIDATION FAILED - {len(issues)} critical issues found")
            print("   Please fix all critical issues before deployment.")
            return 1
        elif warnings:
            print(f"\n⚠️  VALIDATION PASSED WITH WARNINGS - {len(warnings)} warnings")
            print("   Consider addressing warnings for better security.")
            return 0
        else:
            print(f"\n✅ VALIDATION PASSED - No security issues found")
            return 0


def main():
    """Main function."""
    validator = SecurityValidator()
    results = validator.run_all_validations()
    exit_code = validator.print_results(results)
    
    if exit_code == 0:
        print("\n🛡️  Security validation completed successfully!")
        print("   Your configuration appears to be secure.")
    else:
        print("\n🔧 NEXT STEPS:")
        print("   1. Fix all critical issues listed above")
        print("   2. Review and address warnings")
        print("   3. Run this script again to verify fixes")
        print("   4. Use .env.secure.example as a reference")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()