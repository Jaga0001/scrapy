#!/usr/bin/env python3
"""
Security validation script for the web scraper project.
Run this before deployment to check for security issues.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.security_validator import SecurityConfigValidator, validate_environment_file
from config.settings import get_settings

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Run comprehensive security validation."""
    print("🔍 Running Security Validation...")
    print("=" * 50)
    
    total_errors = 0
    total_warnings = 0
    
    # 1. Validate environment file
    print("\n📁 Validating .env file...")
    env_results = validate_environment_file()
    
    if env_results["errors"]:
        print("❌ Environment File Errors:")
        for error in env_results["errors"]:
            print(f"   • {error}")
        total_errors += len(env_results["errors"])
    
    if env_results["warnings"]:
        print("⚠️  Environment File Warnings:")
        for warning in env_results["warnings"]:
            print(f"   • {warning}")
        total_warnings += len(env_results["warnings"])
    
    if not env_results["errors"] and not env_results["warnings"]:
        print("✅ Environment file validation passed")
    
    # 2. Validate application settings
    print("\n⚙️  Validating application settings...")
    try:
        settings = get_settings()
        validator = SecurityConfigValidator()
        config_results = validator.validate_production_config(settings)
        
        if config_results["errors"]:
            print("❌ Configuration Errors:")
            for error in config_results["errors"]:
                print(f"   • {error}")
            total_errors += len(config_results["errors"])
        
        if config_results["warnings"]:
            print("⚠️  Configuration Warnings:")
            for warning in config_results["warnings"]:
                print(f"   • {warning}")
            total_warnings += len(config_results["warnings"])
        
        if not config_results["errors"] and not config_results["warnings"]:
            print("✅ Application settings validation passed")
            
    except Exception as e:
        print(f"❌ Failed to validate settings: {e}")
        total_errors += 1
    
    # 3. Check file permissions
    print("\n🔒 Checking file permissions...")
    env_file = Path(".env")
    if env_file.exists():
        import stat
        file_stat = env_file.stat()
        
        # Check if file is readable by others (Unix-like systems)
        if hasattr(stat, 'S_IROTH') and file_stat.st_mode & stat.S_IROTH:
            print("⚠️  .env file is readable by others - consider: chmod 600 .env")
            total_warnings += 1
        
        if hasattr(stat, 'S_IWOTH') and file_stat.st_mode & stat.S_IWOTH:
            print("❌ .env file is writable by others - this is a security risk!")
            total_errors += 1
        
        if total_errors == 0 and total_warnings == 0:
            print("✅ File permissions are secure")
    else:
        print("⚠️  .env file not found")
        total_warnings += 1
    
    # 4. Check for common security files
    print("\n📋 Checking security files...")
    security_files = [
        ".gitignore",
        "requirements.txt",
        "config/security.py",
        "config/security_validator.py",
        ".env.secure.example",
        ".env.test.example",
        "docs/GITHUB_SECRETS_SETUP.md"
    ]
    
    missing_files = []
    for file_path in security_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("⚠️  Missing security-related files:")
        for file_path in missing_files:
            print(f"   • {file_path}")
        total_warnings += len(missing_files)
    else:
        print("✅ All security files present")
    
    # 5. Summary
    print("\n" + "=" * 50)
    print("📊 Security Validation Summary")
    print("=" * 50)
    
    if total_errors == 0 and total_warnings == 0:
        print("🎉 All security checks passed!")
        print("✅ Your configuration appears secure for deployment.")
        return 0
    
    if total_errors > 0:
        print(f"❌ Found {total_errors} security error(s) that must be fixed")
        
    if total_warnings > 0:
        print(f"⚠️  Found {total_warnings} security warning(s) to review")
    
    print("\n📖 For detailed security guidance, see:")
    print("   • SECURITY_CONFIGURATION_GUIDE.md")
    print("   • .env.secure.example")
    print("   • .env.test.example")
    print("   • docs/GITHUB_SECRETS_SETUP.md")
    
    # Return non-zero exit code if there are errors
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)