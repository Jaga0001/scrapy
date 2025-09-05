#!/usr/bin/env python3
"""
Setup script for the AI Web Scraper project.
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True


def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    
    try:
        # Upgrade pip first
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment():
    """Setup environment configuration."""
    print("⚙️  Setting up environment...")
    
    env_file = Path(".env")
    env_template = Path(".env.template")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_template.exists():
        # Copy template to .env
        shutil.copy(env_template, env_file)
        print("✅ Created .env from template")
        
        print("\n⚠️  Important: Please edit .env file and set:")
        print("   - GEMINI_API_KEY (get from https://makersuite.google.com/app/apikey)")
        print("   - SECRET_KEY (run: python scripts/generate_secure_keys.py)")
        print("   - ENCRYPTION_MASTER_KEY (run: python scripts/generate_secure_keys.py)")
        
        return True
    else:
        # Create basic .env file
        env_content = """# AI Web Scraper Configuration

# Essential Configuration
APP_NAME="AI Web Scraper"
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///webscraper.db

# AI Configuration - REPLACE WITH YOUR ACTUAL API KEY
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
SECRET_KEY=INSECURE_DEV_KEY_REPLACE_IN_PRODUCTION
ENCRYPTION_MASTER_KEY=INSECURE_DEV_KEY_REPLACE_IN_PRODUCTION

# Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8501
API_BASE_URL=http://localhost:8000/api/v1

# Security Configuration
CORS_ORIGINS=http://127.0.0.1:8501,http://localhost:8501
SCRAPER_RESPECT_ROBOTS_TXT=true

# Rate Limiting & Security
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
SCRAPER_DELAY_MIN=2
SCRAPER_DELAY_MAX=5
SCRAPER_TIMEOUT=15
SCRAPER_MAX_RETRIES=3

# Scraper Security
SCRAPER_USER_AGENTS=Mozilla/5.0 (compatible; WebScraper/1.0),Mozilla/5.0 (compatible; DataCollector/1.0),Mozilla/5.0 (compatible; ContentAnalyzer/1.0)
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print("✅ Created basic .env file")
        print("\n⚠️  Important: Please edit .env file and set your API keys")
        
        return True


def create_directories():
    """Create necessary directories."""
    print("📁 Creating directories...")
    
    directories = [
        "data",
        "logs",
        "exports",
        "temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created")
    return True


def run_security_validation():
    """Run security validation if available."""
    print("🔒 Running security validation...")
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/validate_security.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Security validation passed")
        else:
            print("⚠️  Security validation found issues:")
            print(result.stdout)
            print(result.stderr)
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not run security validation: {e}")
        return True  # Non-critical


def main():
    """Main setup function."""
    print("🚀 AI Web Scraper Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Setup environment
    if not setup_environment():
        return False
    
    # Create directories
    if not create_directories():
        return False
    
    # Run security validation
    run_security_validation()
    
    print("\n🎉 Setup completed successfully!")
    print("=" * 40)
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python test_scraper.py (to test scraping)")
    print("3. Run: python run_system.py (to start the full system)")
    print("\nFor help, check the README.md file")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)