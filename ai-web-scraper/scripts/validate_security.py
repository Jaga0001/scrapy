#!/usr/bin/env python3
"""
Security validation script for AI Web Scraper.
Checks for common security issues and misconfigurations.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any
import json

class SecurityValidator:
    """Security validation for AI Web Scraper."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
    
    def check_hardcoded_secrets(self) -> List[Tuple[str, str]]:
        """Check for hardcoded secrets in Python files."""
        issues = []
        
        # Patterns to look for
        secret_patterns = [
            (r'SECRET_KEY\s*=\s*["\'](?!.*\$\{)[^"\']{10,}["\']', 'Hardcoded SECRET_KEY'),
            (r'API_KEY\s*=\s*["\'](?!.*\$\{)[^"\']{10,}["\']', 'Hardcoded API_KEY'),
            (r'PASSWORD\s*=\s*["\'](?!.*\$\{)[^"\']{5,}["\']', 'Hardcoded PASSWORD'),
            (r'TOKEN\s*=\s*["\'](?!.*\$\{)[^"\']{10,}["\']', 'Hardcoded TOKEN'),
            (r'postgresql://[^:]+:[^@]+@', 'Database URL with embedded credentials'),
            (r'mysql://[^:]+:[^@]+@', 'Database URL with embedded credentials'),
            (r'redis://[^:]*:[^@]+@', 'Redis URL with embedded credentials'),
        ]
        
        # Check Python files
        for py_file in Path('.').rglob('*.py'):
            if any(skip in str(py_file) for skip in ['venv', '__pycache__', '.git', 'node_modules']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip if it's a comment or example
                        line = content[content.rfind('\n', 0, match.start())+1:content.find('\n', match.end())]
                        if '#' in line and line.index('#') < line.index(match.group()):
                            continue
                        issues.append((str(py_file), description, match.group()[:50] + "..."))
            except Exception as e:
                self.warnings.append(f"Could not read {py_file}: {e}")
        
        return issues
    
    def check_environment_files(self) -> List[str]:
        """Check environment files for security issues."""
        issues = []
        
        env_files = ['.env', '.env.template', '.env.local', '.env.production', '.env.development']
        dangerous_values = [
            'your_api_key_here',
            'your_gemini_api_key_here',
            'dev_secret_key',
            'change_in_production',
            'your_secure_secret_key',
            'ai_web_scraper_secret_key_2025_development_only',
            'ai_web_scraper_encryption_master_key_2025_development_only',
            'your_jwt_secret_key_here',
            'your_redis_password_here',
            'your_encryption_master_key',
        ]
        
        for env_file in env_files:
            if not os.path.exists(env_file):
                continue
                
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        for dangerous in dangerous_values:
                            if dangerous.lower() in line.lower():
                                issues.append(f"{env_file}:{line_num} - Contains placeholder value '{dangerous}'")
                        
                        # Check for weak keys
                        if '=' in line:
                            key, value = line.split('=', 1)
                            if any(secret in key.upper() for secret in ['SECRET', 'KEY', 'PASSWORD', 'TOKEN']):
                                if len(value.strip()) < 16:
                                    issues.append(f"{env_file}:{line_num} - {key} appears to be too short for security")
                                
            except Exception as e:
                self.warnings.append(f"Could not read {env_file}: {e}")
        
        return issues
    
    def check_cors_configuration(self) -> List[str]:
        """Check CORS configuration for security issues."""
        issues = []
        
        # Check Python files for CORS configuration
        for py_file in Path('.').rglob('*.py'):
            if any(skip in str(py_file) for skip in ['venv', '__pycache__', '.git']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for overly permissive CORS
                if 'allow_origins=["*"]' in content or "allow_origins=['*']" in content:
                    issues.append(f"{py_file} - CORS allows all origins (*)")
                
                if 'allow_credentials=True' in content and ('allow_origins=["*"]' in content or "allow_origins=['*']" in content):
                    issues.append(f"{py_file} - CORS allows credentials with wildcard origins (security risk)")
                
            except Exception:
                continue
        
        return issues
    
    def check_database_configuration(self) -> List[str]:
        """Check database configuration for security issues."""
        issues = []
        
        # Check for database URLs in environment files
        env_files = ['.env', '.env.template', '.env.local', '.env.production']
        
        for env_file in env_files:
            if not os.path.exists(env_file):
                continue
                
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for database URLs with embedded credentials
                    db_patterns = [
                        r'postgresql://[^:]+:[^@]+@[^/]+/\w+',
                        r'mysql://[^:]+:[^@]+@[^/]+/\w+',
                        r'mongodb://[^:]+:[^@]+@[^/]+/\w+',
                    ]
                    
                    for pattern in db_patterns:
                        if re.search(pattern, content):
                            issues.append(f"{env_file} - Database URL contains embedded credentials")
                            break
                            
            except Exception:
                continue
        
        return issues
    
    def check_test_urls(self) -> List[str]:
        """Check for hardcoded URLs in test files that might leak information."""
        issues = []
        
        test_files = list(Path('tests').rglob('*.py')) if Path('tests').exists() else []
        
        suspicious_domains = [
            'example-store.com',
            'tech-news.com',
            'electronics-store.com',
            'dev-blog.com',
        ]
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                for domain in suspicious_domains:
                    if domain in content:
                        issues.append(f"{test_file} - Contains potentially identifying test URL: {domain}")
            except Exception:
                continue
        
        return issues
    
    def check_logging_configuration(self) -> List[str]:
        """Check logging configuration for potential information leakage."""
        issues = []
        
        for py_file in Path('.').rglob('*.py'):
            if any(skip in str(py_file) for skip in ['venv', '__pycache__', '.git']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for potentially sensitive logging
                sensitive_patterns = [
                    r'log.*password',
                    r'log.*secret',
                    r'log.*token',
                    r'log.*key',
                    r'print.*password',
                    r'print.*secret',
                    r'print.*token',
                ]
                
                for pattern in sensitive_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append(f"{py_file} - Potentially logs sensitive information")
                        break
                        
            except Exception:
                continue
        
        return issues
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        report = {
            "timestamp": os.popen('date').read().strip(),
            "summary": {
                "critical_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "warnings": len(self.warnings),
                "info": len(self.info)
            },
            "issues": {
                "hardcoded_secrets": [],
                "environment_files": [],
                "cors_configuration": [],
                "database_configuration": [],
                "test_urls": [],
                "logging_configuration": []
            },
            "recommendations": []
        }
        
        # Check all categories
        report["issues"]["hardcoded_secrets"] = self.check_hardcoded_secrets()
        report["issues"]["environment_files"] = self.check_environment_files()
        report["issues"]["cors_configuration"] = self.check_cors_configuration()
        report["issues"]["database_configuration"] = self.check_database_configuration()
        report["issues"]["test_urls"] = self.check_test_urls()
        report["issues"]["logging_configuration"] = self.check_logging_configuration()
        
        # Count issues by severity
        critical_issues = len(report["issues"]["hardcoded_secrets"]) + len(report["issues"]["environment_files"])
        medium_issues = len(report["issues"]["cors_configuration"]) + len(report["issues"]["database_configuration"])
        low_issues = len(report["issues"]["test_urls"]) + len(report["issues"]["logging_configuration"])
        
        report["summary"]["critical_issues"] = critical_issues
        report["summary"]["medium_issues"] = medium_issues
        report["summary"]["low_issues"] = low_issues
        
        # Generate recommendations
        if critical_issues > 0:
            report["recommendations"].append("🔴 CRITICAL: Replace all placeholder credentials immediately")
            report["recommendations"].append("🔴 CRITICAL: Generate secure keys using scripts/generate_secure_keys.py")
        
        if medium_issues > 0:
            report["recommendations"].append("🟡 MEDIUM: Review CORS and database configurations")
        
        if low_issues > 0:
            report["recommendations"].append("🟢 LOW: Update test files to use environment variables for URLs")
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted security report."""
        print("🔒 AI Web Scraper Security Validation Report")
        print("=" * 60)
        print(f"Generated: {report['timestamp']}")
        print()
        
        # Summary
        summary = report['summary']
        total_issues = summary['critical_issues'] + summary['medium_issues'] + summary['low_issues']
        
        if total_issues == 0:
            print("✅ No security issues found!")
            return
        
        print(f"📊 Summary: {total_issues} issues found")
        print(f"   🔴 Critical: {summary['critical_issues']}")
        print(f"   🟡 Medium:   {summary['medium_issues']}")
        print(f"   🟢 Low:      {summary['low_issues']}")
        print(f"   ⚠️  Warnings: {summary['warnings']}")
        print()
        
        # Detailed issues
        issues = report['issues']
        
        if issues['hardcoded_secrets']:
            print("🔴 CRITICAL: Hardcoded Secrets Found")
            for file_path, description, snippet in issues['hardcoded_secrets']:
                print(f"   - {file_path}: {description}")
                print(f"     Snippet: {snippet}")
            print()
        
        if issues['environment_files']:
            print("🔴 CRITICAL: Environment File Issues")
            for issue in issues['environment_files']:
                print(f"   - {issue}")
            print()
        
        if issues['cors_configuration']:
            print("🟡 MEDIUM: CORS Configuration Issues")
            for issue in issues['cors_configuration']:
                print(f"   - {issue}")
            print()
        
        if issues['database_configuration']:
            print("🟡 MEDIUM: Database Configuration Issues")
            for issue in issues['database_configuration']:
                print(f"   - {issue}")
            print()
        
        if issues['test_urls']:
            print("🟢 LOW: Test URL Issues")
            for issue in issues['test_urls']:
                print(f"   - {issue}")
            print()
        
        if issues['logging_configuration']:
            print("🟢 LOW: Logging Configuration Issues")
            for issue in issues['logging_configuration']:
                print(f"   - {issue}")
            print()
        
        # Recommendations
        if report['recommendations']:
            print("💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"   {rec}")
            print()
        
        # Warnings
        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
            print()

def main():
    """Main function."""
    validator = SecurityValidator()
    
    print("🚀 Running AI Web Scraper Security Validation...")
    print()
    
    # Generate and print report
    report = validator.generate_security_report()
    validator.print_report(report)
    
    # Save report to file
    report_file = Path("security_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Detailed report saved to: {report_file}")
    
    # Exit with appropriate code
    total_issues = report['summary']['critical_issues'] + report['summary']['medium_issues'] + report['summary']['low_issues']
    
    if total_issues == 0:
        print("\n🎉 All security checks passed!")
        return 0
    else:
        print(f"\n⚠️  Found {total_issues} security issues that need attention.")
        print("\n🔧 Quick fixes:")
        print("   1. Run: python scripts/generate_secure_keys.py")
        print("   2. Update .env with your actual API keys")
        print("   3. Review CORS settings in src/api/main.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())