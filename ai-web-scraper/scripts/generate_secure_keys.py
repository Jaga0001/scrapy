#!/usr/bin/env python3
"""
Generate secure keys and configuration for AI Web Scraper.
This script creates cryptographically secure keys and updates environment files.
"""

import secrets
import string
import os
import random
from pathlib import Path

def generate_secure_key(length: int = 64) -> str:
    """Generate a cryptographically secure random key."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_jwt_secret() -> str:
    """Generate a secure JWT secret key."""
    return secrets.token_urlsafe(64)

def generate_encryption_key() -> str:
    """Generate a secure encryption master key."""
    return secrets.token_urlsafe(32)

def get_secure_user_agents() -> list:
    """Generate a list of secure, non-identifying user agents."""
    # Use generic, non-identifying user agents that don't leak information
    # Avoid specific version numbers or identifying information
    generic_agents = [
        "Mozilla/5.0 (compatible; WebScraper/1.0; +http://example.com/bot)",
        "Mozilla/5.0 (compatible; DataCollector/1.0)",
        "Mozilla/5.0 (compatible; ContentAnalyzer/1.0)",
        "Mozilla/5.0 (compatible; ResearchBot/1.0)",
        "Mozilla/5.0 (compatible; InfoGatherer/1.0)",
        "Mozilla/5.0 (compatible; WebCrawler/1.0)"
    ]
    
    # For production, use more realistic but still generic agents
    realistic_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101"
    ]
    
    # Choose based on environment
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        # Use more realistic agents for production to avoid detection
        selected_count = random.randint(3, 5)
        return random.sample(realistic_agents, selected_count)
    else:
        # Use clearly identified bot agents for development/testing
        selected_count = random.randint(3, 4)
        return random.sample(generic_agents, selected_count)

def create_secure_env():
    """Create a secure .env file with generated keys."""
    env_path = Path(".env")
    env_template_path = Path(".env.template")
    
    # Generate secure keys
    secret_key = generate_secure_key(64)
    encryption_key = generate_encryption_key()
    jwt_secret = generate_jwt_secret()
    user_agents = get_secure_user_agents()
    
    # Create secure environment configuration
    secure_config = f"""# AI Web Scraper - Secure Configuration
# Generated on: {os.popen('date').read().strip()}
# IMPORTANT: Keep this file secure and never commit to version control

# Essential Configuration
APP_NAME="AI Web Scraper"
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=sqlite:///webscraper.db

# AI Configuration - REPLACE WITH YOUR ACTUAL API KEY
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Security Keys - Generated securely
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

# CORS Security - Restrict to specific origins
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

# Scraper Security Settings
SCRAPER_RESPECT_ROBOTS_TXT=true
SCRAPER_DELAY_MIN=1
SCRAPER_DELAY_MAX=3
SCRAPER_TIMEOUT=10
SCRAPER_MAX_RETRIES=3

# Secure User Agents - Generic, non-identifying agents
SCRAPER_USER_AGENTS={','.join(user_agents)}

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Session Security
SESSION_TIMEOUT=3600
SECURE_COOKIES=true
"""

    # Write secure configuration
    with open(env_path, 'w') as f:
        f.write(secure_config)
    
    print("✅ Secure .env file created successfully!")
    print(f"📁 Location: {env_path.absolute()}")
    print("\n🔐 Generated secure keys:")
    print(f"   - SECRET_KEY: {len(secret_key)} characters")
    print(f"   - ENCRYPTION_MASTER_KEY: {len(encryption_key)} characters") 
    print(f"   - JWT_SECRET_KEY: {len(jwt_secret)} characters")
    print(f"   - USER_AGENTS: {len(user_agents)} agents selected")
    
    print("\n⚠️  IMPORTANT NEXT STEPS:")
    print("   1. Replace 'your_actual_gemini_api_key_here' with your real Gemini API key")
    print("   2. Update CORS_ORIGINS for your production domains")
    print("   3. Set ENVIRONMENT=production for production deployment")
    print("   4. Never commit the .env file to version control")
    
    return {
        'secret_key': secret_key,
        'encryption_key': encryption_key,
        'jwt_secret': jwt_secret,
        'user_agents': user_agents
    }

def update_gitignore():
    """Ensure .env files are in .gitignore."""
    gitignore_path = Path(".gitignore")
    
    env_patterns = [
        "# Environment files",
        ".env",
        ".env.local", 
        ".env.production",
        ".env.staging",
        "*.env",
        "",
        "# Security files",
        "security_report.json",
        "*.key",
        "*.pem",
        ""
    ]
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            existing_content = f.read()
        
        # Check if .env is already ignored
        if ".env" not in existing_content:
            with open(gitignore_path, 'a') as f:
                f.write("\n" + "\n".join(env_patterns))
            print("✅ Updated .gitignore to exclude environment files")
    else:
        with open(gitignore_path, 'w') as f:
            f.write("\n".join(env_patterns))
        print("✅ Created .gitignore with security exclusions")

def main():
    """Main function to generate secure configuration."""
    print("🔐 AI Web Scraper Security Key Generator")
    print("=" * 50)
    
    # Change to the correct directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Generate secure configuration
    keys = create_secure_env()
    
    # Update gitignore
    update_gitignore()
    
    print("\n🎉 Security setup complete!")
    print("\n💡 Additional Security Recommendations:")
    print("   - Use environment-specific .env files (.env.production, .env.staging)")
    print("   - Implement API key rotation policies")
    print("   - Monitor for unusual scraping patterns")
    print("   - Use HTTPS in production")
    print("   - Implement request rate limiting")
    print("   - Regular security audits with scripts/validate_security.py")

if __name__ == "__main__":
    main()