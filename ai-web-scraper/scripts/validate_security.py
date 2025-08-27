#!/usr/bin/env python3
"""
Security validation script for AI Web Scraper.

This script checks for common security issues and validates
that sensitive configuration is properly set up.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

def check_env_file() -> List[Tuple[str, str]]:
    """Check .env file for security issues."""
    issues = []
    env_path = Path(".env")
    
    if not env_path.exists():
        issues.append(("ERROR", ".env file not found. Copy .env.template to .env"))
        return issues
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Check for placeholder values
    placeholders = [
        ("GEMINI_API_KEY=your_gemini_api_key_here", "Gemini API key is still placeholder"),
        ("SECRET_KEY=your_secure_secret_key", "Secret key is still placeholder"),
        ("ENCRYPTION_MASTER_KEY=your_encryption_master_key", "Encryption key is still placeholder"),
        ("SECRET_KEY=2004", "Secret key is weak (was example value)"),
    ]
    
    for placeholder, message in placeholders:
        if placeholder in content:
            issues.append(("ERROR", message))
    
    # Check for weak patterns
    if re.search(r'SECRET_KEY=.{1,10}$', content, re.MULTILINE):
        issues.append(("WARNING", "Secret key appears to be too short (should be 32+ characters)"))
    
    if re.search(r'GEMINI_API_KEY=test|demo|example', content, re.IGNORECASE):
        issues.append(("ERROR", "Gemini API key appears to be a test/demo value"))
    
    # Check for development settings in production
    if "ENVIRONMENT=production" in content:
        if "DEBUG=true" in content:
            issues.append(("WARNING", "Debug mode enabled in production environment"))
        if "localhost" in content:
            issues.append(("WARNING", "Localhost URLs found in production environment"))
    
    return issues

def check_file_permissions() -> List[Tuple[str, str]]:
    """Check file permissions for sensitive files."""
    issues = []
    
    sensitive_files = [".env", "config/secure_config.enc"]
    
    for file_path in sensitive_files:
        path = Path(file_path)
        if path.exists():
            # Check if file is readable by others (Unix-like systems)
            if hasattr(os, 'stat'):
                import stat
                file_stat = path.stat()
                if file_stat.st_mode & stat.S_IROTH:
                    issues.append(("WARNING", f"{file_path} is readable by others"))
                if file_stat.st_mode & stat.S_IWOTH:
                    issues.append(("ERROR", f"{file_path} is writable by others"))
    
    return issues

def check_hardcoded_secrets() -> List[Tuple[str, str]]:
    """Check for hardcoded secrets in Python files."""
    issues = []
    
    # Patterns that might indicate hardcoded secrets
    secret_patterns = [
        (r'api_key\s*=\s*["\'][^"\']{20,}["\']', "Possible hardcoded API key"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Possible hardcoded password"),
        (r'secret\s*=\s*["\'][^"\']{10,}["\']', "Possible hardcoded secret"),
        (r'token\s*=\s*["\'][^"\']{20,}["\']', "Possible hardcoded token"),
    ]
    
    python_files = Path("src").rglob("*.py")
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern, message in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Skip if it's clearly using environment variables
                    if not any("os.getenv" in match or "getenv" in match for match in matches):
                        issues.append(("WARNING", f"{py_file}: {message}"))
        
        except Exception as e:
            issues.append(("WARNING", f"Could not read {py_file}: {e}"))
    
    return issues

def check_dependencies() -> List[Tuple[str, str]]:
    """Check for security-related dependency issues."""
    issues = []
    
    requirements_path = Path("requirements.txt")
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            content = f.read()
        
        # Check for pinned versions
        unpinned = re.findall(r'^([a-zA-Z0-9_-]+)(?:\[[^\]]+\])?$', content, re.MULTILINE)
        if unpinned:
            issues.append(("WARNING", f"Unpinned dependencies found: {', '.join(unpinned[:5])}"))
        
        # Check for known vulnerable packages (basic check)
        vulnerable_patterns = [
            "requests<2.20.0",
            "urllib3<1.24.2",
            "cryptography<3.0.0"
        ]
        
        for pattern in vulnerable_patterns:
            if pattern in content:
                issues.append(("ERROR", f"Potentially vulnerable dependency: {pattern}"))
    
    return issues

def main():
    """Run all security checks."""
    print("🔒 AI Web Scraper Security Validation")
    print("=" * 40)
    
    all_issues = []
    
    # Run all checks
    checks = [
        ("Environment Configuration", check_env_file),
        ("File Permissions", check_file_permissions),
        ("Hardcoded Secrets", check_hardcoded_secrets),
        ("Dependencies", check_dependencies),
    ]
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 30)
        
        try:
            issues = check_func()
            if not issues:
                print("✅ No issues found")
            else:
                for level, message in issues:
                    icon = "❌" if level == "ERROR" else "⚠️"
                    print(f"{icon} {level}: {message}")
                all_issues.extend(issues)
        
        except Exception as e:
            print(f"❌ ERROR: Check failed: {e}")
            all_issues.append(("ERROR", f"{check_name} check failed: {e}"))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 Security Validation Summary")
    print("=" * 40)
    
    errors = [issue for issue in all_issues if issue[0] == "ERROR"]
    warnings = [issue for issue in all_issues if issue[0] == "WARNING"]
    
    print(f"❌ Errors: {len(errors)}")
    print(f"⚠️  Warnings: {len(warnings)}")
    
    if errors:
        print("\n🚨 CRITICAL: Fix all errors before deploying to production!")
        sys.exit(1)
    elif warnings:
        print("\n⚠️  Review warnings and fix as needed.")
        sys.exit(0)
    else:
        print("\n✅ All security checks passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()