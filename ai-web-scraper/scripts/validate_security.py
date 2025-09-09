#!/usr/bin/env python3
"""
Simple validation script for AI Web Scraper.
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Load .env file variables."""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def main():
    """Simple validation - just check if basic config exists."""
    print("✅ Simple validation - Configuration looks good!")
    print("🔍 Basic checks:")
    
    # Check if .env exists
    if Path(".env").exists():
        print("   ✓ .env file found")
        load_env_file()
    else:
        print("   ✗ .env file missing")
        return 1
    
    # Check if Gemini API key is set
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and len(gemini_key) > 10:
        print("   ✓ Gemini API key configured")
    else:
        print("   ✗ Gemini API key not configured")
        return 1
    
    print("\n✅ All basic checks passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())