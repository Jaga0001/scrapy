#!/usr/bin/env python3
"""
Generate secure keys for AI Web Scraper production deployment.
"""

import secrets
import os
from pathlib import Path

def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure secret key."""
    return secrets.token_urlsafe(length)

def generate_encryption_key() -> str:
    """Generate a Fernet encryption key."""
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        print("⚠️  cryptography package not installed. Using fallback method.")
        return secrets.token_urlsafe(44)  # Fernet keys are 44 characters

def generate_jwt_secret() -> str:
    """Generate JWT secret key."""
    return secrets.token_urlsafe(64)

def create_secure_env_file():
    """Create a secure .env.production file with generated keys."""
    
    print("🔐 Generating secure keys for production...")
    
    # Generate all keys
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    jwt_secret = generate_jwt_secret()
    
    # Create secure environment template
    secure_env_content = f"""# AI Web Scraper - Production Environment Configuration
# Generated on: {os.popen('date').read().strip()}
# IMPORTANT: Keep this file secure and never commit to version control!

# Essential Configuration
APP_NAME="AI Web Scraper"
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Database Configuration (Use separate variables for security)
DATABASE_URL=sqlite:///webscraper.db
# For PostgreSQL/MySQL, use these instead:
# DB_TYPE=postgresql
# DB_HOST=your_db_host
# DB_PORT=5432
# DB_NAME=webscraper
# DB_USER=your_db_user
# DB_PASSWORD=your_secure_db_password

# AI Configuration - REPLACE WITH YOUR ACTUAL API KEY
GEMINI_API_KEY=your_actual_gemini_api_key_from_google_ai_studio
GEMINI_MODEL=gemini-2.0-flash-exp

# Security Keys (GENERATED - DO NOT CHANGE)
SECRET_KEY={secret_key}
ENCRYPTION_MASTER_KEY={encryption_key}
JWT_SECRET_KEY={jwt_secret}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8501
API_BASE_URL=http://localhost:8000/api/v1

# Security Settings
CORS_ORIGINS=http://localhost:3000,http://localhost:8501
SCRAPER_RESPECT_ROBOTS_TXT=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
SESSION_TIMEOUT_MINUTES=30

# Scraper Security - Use current user agents
SCRAPER_USER_AGENTS=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/120.0.0.0 Safari/537.36,Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML like Gecko) Chrome/120.0.0.0 Safari/537.36,Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/120.0.0.0 Safari/537.36

# Data Retention Settings
RETENTION_SCRAPED_DATA_DAYS=365
RETENTION_JOB_LOGS_DAYS=90
RETENTION_SYSTEM_METRICS_DAYS=30

# Redis Configuration (Optional)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=your_secure_redis_password
# REDIS_SSL=false
"""
    
    # Write to file
    output_file = Path(".env.production")
    output_file.write_text(secure_env_content)
    
    # Set secure permissions (Unix-like systems)
    try:
        os.chmod(output_file, 0o600)  # Read/write for owner only
    except:
        pass  # Windows doesn't support chmod
    
    print(f"✅ Secure environment file created: {output_file}")
    print("\n🔑 Generated Keys:")
    print(f"SECRET_KEY: {secret_key[:20]}...")
    print(f"ENCRYPTION_MASTER_KEY: {encryption_key[:20]}...")
    print(f"JWT_SECRET_KEY: {jwt_secret[:20]}...")
    
    print("\n⚠️  IMPORTANT NEXT STEPS:")
    print("1. Add your actual Gemini API key to .env.production")
    print("2. Configure database settings if using PostgreSQL/MySQL")
    print("3. Update CORS_ORIGINS for your production domains")
    print("4. Never commit .env.production to version control!")
    print("5. Copy .env.production to .env for local development")

def main():
    """Main function."""
    print("🚀 AI Web Scraper - Secure Key Generator")
    print("=" * 50)
    
    # Check if .env.production already exists
    if Path(".env.production").exists():
        response = input("⚠️  .env.production already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Aborted. Existing file preserved.")
            return
    
    create_secure_env_file()
    
    print("\n🎯 Quick Start Commands:")
    print("# Copy production config for local development:")
    print("cp .env.production .env")
    print("\n# Edit with your API key:")
    print("nano .env")
    print("\n# Start the application:")
    print("python main.py")

if __name__ == "__main__":
    main()