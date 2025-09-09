#!/usr/bin/env python3
"""
Secure key generation script for AI Web Scraper.
Generates cryptographically secure keys for production use.
"""

import secrets
import string
import os
from pathlib import Path


def generate_secret_key(length: int = 64) -> str:
    """Generate a cryptographically secure secret key."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_encryption_key() -> str:
    """Generate a secure encryption key."""
    return secrets.token_urlsafe(32)


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret key."""
    return secrets.token_urlsafe(64)


def generate_user_agents() -> list:
    """Generate a list of secure, generic user agents."""
    return [
        "Mozilla/5.0 (compatible; WebScraper/1.0; +https://example.com/bot)",
        "Mozilla/5.0 (compatible; DataCollector/1.0)",
        "Mozilla/5.0 (compatible; ContentAnalyzer/1.0)",
        "Mozilla/5.0 (compatible; ResearchBot/1.0)",
        "Mozilla/5.0 (compatible; InfoGatherer/1.0)"
    ]


def update_env_file():
    """Update .env file with secure keys."""
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("❌ .env file not found. Please create it first.")
        return
    
    # Read current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Generate new secure keys
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    jwt_secret = generate_jwt_secret()
    user_agents = generate_user_agents()
    
    # Update lines with secure values
    updated_lines = []
    for line in lines:
        if line.startswith('SECRET_KEY=') and 'INSECURE' in line:
            updated_lines.append(f'SECRET_KEY={secret_key}\n')
            print("✅ Updated SECRET_KEY")
        elif line.startswith('ENCRYPTION_MASTER_KEY=') and 'INSECURE' in line:
            updated_lines.append(f'ENCRYPTION_MASTER_KEY={encryption_key}\n')
            print("✅ Updated ENCRYPTION_MASTER_KEY")
        elif line.startswith('JWT_SECRET_KEY=') and ('change-this' in line or 'INSECURE' in line):
            updated_lines.append(f'JWT_SECRET_KEY={jwt_secret}\n')
            print("✅ Updated JWT_SECRET_KEY")
        elif line.startswith('SCRAPER_USER_AGENTS='):
            user_agent_string = ','.join(user_agents)
            updated_lines.append(f'SCRAPER_USER_AGENTS={user_agent_string}\n')
            print("✅ Updated SCRAPER_USER_AGENTS")
        else:
            updated_lines.append(line)
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"\n🔒 Secure keys generated and saved to {env_path}")
    print("⚠️  Make sure to:")
    print("   1. Add your actual GEMINI_API_KEY")
    print("   2. Review other configuration values")
    print("   3. Never commit .env to version control")


def create_env_template():
    """Create a secure .env.template file."""
    template_path = Path(__file__).parent.parent / ".env.template"
    
    template_content = """# AI Web Scraper - Secure Environment Template
# Copy this file to .env and replace placeholder values with actual configuration

# Essential Configuration
APP_NAME="AI Web Scraper"
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# Database - Use secure connection strings in production
DATABASE_URL=sqlite:///webscraper.db

# AI Configuration - REPLACE WITH YOUR ACTUAL API KEY
# Get your Gemini API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000

# SECURITY: Generate secure keys using: python scripts/generate_secure_keys.py
SECRET_KEY=generate_secure_key_using_script
ENCRYPTION_MASTER_KEY=generate_secure_key_using_script
JWT_SECRET_KEY=generate_secure_key_using_script

# Dashboard
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8501
API_BASE_URL=http://localhost:8000/api/v1

# Security Configuration - Restrict CORS in production
CORS_ORIGINS=http://127.0.0.1:8501,http://localhost:8501
SCRAPER_RESPECT_ROBOTS_TXT=true

# Rate Limiting & Security
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
SCRAPER_DELAY_MIN=2
SCRAPER_DELAY_MAX=5
SCRAPER_TIMEOUT=15
SCRAPER_MAX_RETRIES=3

# Scraper Security - Generate using script for production
SCRAPER_USER_AGENTS=generate_user_agents_using_script

# Production Security Settings (uncomment for production)
# ENVIRONMENT=production
# DEBUG=false
# API_HOST=0.0.0.0
# DASHBOARD_HOST=0.0.0.0
# CORS_ORIGINS=https://yourdomain.com
# DATABASE_URL=postgresql://user:password@localhost/dbname
"""
    
    with open(template_path, 'w') as f:
        f.write(template_content)
    
    print(f"✅ Created secure .env.template at {template_path}")


def main():
    """Main function."""
    print("🔐 AI Web Scraper - Secure Key Generator")
    print("=" * 50)
    
    print("\n1. Generating secure keys...")
    
    # Show examples of what will be generated
    print(f"   SECRET_KEY (64 chars): {generate_secret_key()[:20]}...")
    print(f"   ENCRYPTION_KEY: {generate_encryption_key()[:20]}...")
    print(f"   JWT_SECRET: {generate_jwt_secret()[:20]}...")
    
    print("\n2. Secure User Agents:")
    for ua in generate_user_agents():
        print(f"   - {ua}")
    
    print("\n3. Updating configuration files...")
    
    # Create template
    create_env_template()
    
    # Update .env if it exists
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        response = input(f"\n❓ Update existing .env file with secure keys? (y/N): ")
        if response.lower() in ['y', 'yes']:
            update_env_file()
        else:
            print("⏭️  Skipped .env update")
    else:
        print("ℹ️  No .env file found. Copy .env.template to .env and run this script again.")
    
    print("\n✅ Security key generation completed!")
    print("\n🔒 Security Checklist:")
    print("   ✓ Generate and use secure keys")
    print("   ✓ Set actual GEMINI_API_KEY")
    print("   ✓ Review CORS origins for production")
    print("   ✓ Use HTTPS in production")
    print("   ✓ Set ENVIRONMENT=production for production")
    print("   ✓ Use secure database connection strings")
    print("   ✓ Never commit .env to version control")


if __name__ == "__main__":
    main()