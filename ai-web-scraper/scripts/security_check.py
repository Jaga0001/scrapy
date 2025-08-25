#!/usr/bin/env python3
"""
Security validation script for the AI Web Scraper project.
Run this script to check for common security issues.
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def check_env_file() -> List[str]:
    """Check .env file for security issues."""
    issues = []
    env_path = Path(".env")
    
    if not env_path.exists():
        issues.append("❌ .env file not found - copy from .env.example and configure")
        return issues
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Check for weak secret keys
    if "your-secret-key-change-in-production" in content:
        issues.append("❌ Default secret key found in .env - generate a secure key")
    
    if "SECRET_KEY=" in content:
        secret_match = re.search(r'SECRET_KEY=(.+)', content)
        if secret_match:
            secret = secret_match.group(1).strip()
            if len(secret) < 32:
                issues.append("❌ SECRET_KEY is too short - use at least 32 characters")
    
    # Check for hardcoded credentials
    if "user:password" in content:
        issues.append("❌ Hardcoded database credentials found in .env")
    
    # Check for placeholder values
    placeholders = [
        "your_gemini_api_key_here",
        "your_db_user",
        "your_db_password",
        "generate-a-strong-secret-key-here"
    ]
    
    for placeholder in placeholders:
        if placeholder in content:
            issues.append(f"❌ Placeholder value '{placeholder}' found in .env - replace with actual value")
    
    return issues


def check_source_files() -> List[str]:
    """Check source files for hardcoded secrets."""
    issues = []
    
    # Patterns to look for
    secret_patterns = [
        r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']',
        r'password\s*=\s*["\'][^"\']+["\']',
        r'secret\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']{10,}["\']',
    ]
    
    # Check Python files
    for py_file in Path("src").rglob("*.py"):
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        for pattern in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(f"❌ Potential hardcoded secret in {py_file}: {matches[0][:50]}...")
    
    return issues


def check_git_ignore() -> List[str]:
    """Check if sensitive files are properly ignored."""
    issues = []
    gitignore_path = Path(".gitignore")
    
    if not gitignore_path.exists():
        issues.append("❌ .gitignore file not found")
        return issues
    
    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()
    
    required_ignores = [".env", "*.log", "*.db", "*.sqlite"]
    
    for ignore_pattern in required_ignores:
        if ignore_pattern not in gitignore_content:
            issues.append(f"❌ {ignore_pattern} not found in .gitignore")
    
    return issues


def check_file_permissions() -> List[str]:
    """Check file permissions for sensitive files."""
    issues = []
    
    sensitive_files = [".env", "config/settings.py"]
    
    for file_path in sensitive_files:
        path = Path(file_path)
        if path.exists():
            # Check if file is readable by others (Unix-like systems)
            if hasattr(os, 'stat'):
                stat_info = path.stat()
                if stat_info.st_mode & 0o044:  # Check if readable by group/others
                    issues.append(f"⚠️  {file_path} is readable by others - consider restricting permissions")
    
    return issues


def generate_secure_key() -> str:
    """Generate a secure secret key."""
    import secrets
    return secrets.token_urlsafe(32)


def main():
    """Run all security checks."""
    print("🔒 AI Web Scraper Security Check")
    print("=" * 40)
    
    all_issues = []
    
    # Run checks
    checks = [
        ("Environment File", check_env_file),
        ("Source Files", check_source_files),
        ("Git Ignore", check_git_ignore),
        ("File Permissions", check_file_permissions),
    ]
    
    for check_name, check_func in checks:
        print(f"\n📋 Checking {check_name}...")
        issues = check_func()
        
        if issues:
            all_issues.extend(issues)
            for issue in issues:
                print(f"  {issue}")
        else:
            print(f"  ✅ {check_name} - No issues found")
    
    # Summary
    print("\n" + "=" * 40)
    if all_issues:
        print(f"❌ Found {len(all_issues)} security issues that need attention:")
        for issue in all_issues:
            print(f"  {issue}")
        
        print(f"\n💡 Quick fixes:")
        print(f"  • Generate secure key: python -c \"import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))\"")
        print(f"  • Copy .env.example to .env and configure with real values")
        print(f"  • Never commit .env files to version control")
        print(f"  • Use environment variables in production")
        
        sys.exit(1)
    else:
        print("✅ All security checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()