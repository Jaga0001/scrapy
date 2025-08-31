# 🔒 Security Configuration Guide

## Overview
This guide provides comprehensive security recommendations for the AI Web Scraper project, including secure environment configuration, credential management, and production deployment best practices.

## 🚨 Critical Security Issues Found

### 1. Insecure API Keys and Secrets
**Risk**: High - Placeholder values and weak secrets can be exploited
**Files**: `.env`, `.env.template`

**Issues**:
- Placeholder API keys (`your_gemini_api_key_here`)
- Weak, predictable secret keys
- Development-only encryption keys

### 2. Hardcoded URLs and Endpoints
**Risk**: Medium - Exposes internal infrastructure
**Files**: Multiple configuration files

**Issues**:
- Hardcoded localhost URLs in production configs
- Development CORS origins in production

### 3. Debug Mode and Information Disclosure
**Risk**: Medium - Can expose sensitive system information
**Files**: `.env`

**Issues**:
- Debug mode enabled by default
- Verbose error messages in production

## 🛡️ Secure Configuration Examples

### Environment Variables (.env)

```bash
# Production Environment Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Database - Use environment-specific URLs
DATABASE_URL=${DATABASE_URL:-sqlite:///webscraper.db}

# AI Configuration - Use secure key management
GEMINI_API_KEY=${GEMINI_API_KEY}
GEMINI_MODEL=gemini-2.0-flash-exp

# Security Keys - Generate using: python scripts/generate_secure_keys.py
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_MASTER_KEY=${ENCRYPTION_MASTER_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# API Configuration - Secure binding
API_HOST=127.0.0.1
API_PORT=8000
API_PROTOCOL=https

# Dashboard Configuration
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8501
API_BASE_URL=${API_PROTOCOL}://${API_HOST}:${API_PORT}/api/v1

# CORS Security - Restrict to specific domains
CORS_ORIGINS=${CORS_ORIGINS:-https://yourdomain.com,https://dashboard.yourdomain.com}

# Scraper Security Settings
SCRAPER_RESPECT_ROBOTS_TXT=true
SCRAPER_DELAY_MIN=2
SCRAPER_DELAY_MAX=5
SCRAPER_TIMEOUT=15
SCRAPER_MAX_RETRIES=3

# Generic User Agents - No identifying information
SCRAPER_USER_AGENTS=Mozilla/5.0 (compatible; WebScraper/1.0),Mozilla/5.0 (compatible; DataCollector/1.0),Mozilla/5.0 (compatible; ContentAnalyzer/1.0)

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Session Security
SESSION_TIMEOUT=1800
SECURE_COOKIES=true
```

### Docker Environment Variables

```bash
# docker-compose.yml or Kubernetes secrets
environment:
  - GEMINI_API_KEY_FILE=/run/secrets/gemini_api_key
  - SECRET_KEY_FILE=/run/secrets/secret_key
  - ENCRYPTION_MASTER_KEY_FILE=/run/secrets/encryption_key
  - DATABASE_URL_FILE=/run/secrets/database_url
```

### AWS/Cloud Environment Variables

```bash
# Use AWS Systems Manager Parameter Store or Secrets Manager
GEMINI_API_KEY=arn:aws:ssm:region:account:parameter/webscraper/gemini-api-key
SECRET_KEY=arn:aws:secretsmanager:region:account:secret:webscraper/secret-key
DATABASE_URL=arn:aws:secretsmanager:region:account:secret:webscraper/database-url
```

## 🔐 Credential Management Best Practices

### 1. API Key Security

```python
# ❌ NEVER do this
GEMINI_API_KEY = "AIzaSyC-your-actual-api-key-here"

# ✅ Use environment variables
import os
from typing import Optional

def get_gemini_api_key() -> Optional[str]:
    """Securely retrieve Gemini API key from environment."""
    # Try multiple sources in order of preference
    api_key = (
        os.getenv("GEMINI_API_KEY") or
        os.getenv("GOOGLE_AI_API_KEY") or
        read_secret_file("/run/secrets/gemini_api_key")
    )
    
    if not api_key:
        logger.error("Gemini API key not found in environment")
        return None
    
    if api_key.startswith("your_") or len(api_key) < 20:
        logger.error("Invalid or placeholder API key detected")
        return None
    
    return api_key

def read_secret_file(filepath: str) -> Optional[str]:
    """Read secret from file (Docker secrets, Kubernetes, etc.)."""
    try:
        with open(filepath, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
```

### 2. Database Connection Security

```python
# ❌ Hardcoded connection strings
DATABASE_URL = "postgresql://user:password@localhost:5432/webscraper"

# ✅ Secure connection management
import os
from urllib.parse import urlparse

def get_secure_database_url() -> str:
    """Get database URL with security validation."""
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse and validate URL
    parsed = urlparse(db_url)
    
    # Ensure SSL for production PostgreSQL/MySQL
    if parsed.scheme in ['postgresql', 'mysql'] and 'sslmode' not in db_url:
        if os.getenv("ENVIRONMENT") == "production":
            db_url += "?sslmode=require"
    
    return db_url
```

### 3. User Agent Rotation Security

```python
# ❌ Identifying user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36 MyCompany/1.0"
]

# ✅ Generic, non-identifying user agents
def get_secure_user_agents() -> List[str]:
    """Get secure, non-identifying user agents."""
    agents = os.getenv("SCRAPER_USER_AGENTS", "").split(",")
    
    if not agents or agents == [""]:
        # Fallback to generic agents
        return [
            "Mozilla/5.0 (compatible; WebScraper/1.0)",
            "Mozilla/5.0 (compatible; DataCollector/1.0)",
            "Mozilla/5.0 (compatible; ContentAnalyzer/1.0)"
        ]
    
    # Validate agents don't contain identifying information
    safe_agents = []
    for agent in agents:
        agent = agent.strip()
        # Remove specific version numbers and identifying info
        if not any(pattern in agent.lower() for pattern in [
            'company', 'organization', 'specific-tool', 'internal'
        ]):
            safe_agents.append(agent)
    
    return safe_agents if safe_agents else [
        "Mozilla/5.0 (compatible; WebScraper/1.0)"
    ]
```

## 🚀 Production Deployment Security

### 1. Environment-Specific Configuration

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=ERROR
API_PROTOCOL=https
SECURE_COOKIES=true
SESSION_TIMEOUT=1800

# .env.staging
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=WARNING
API_PROTOCOL=https

# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
API_PROTOCOL=http
```

### 2. Docker Security

```dockerfile
# Use non-root user
FROM python:3.11-slim
RUN groupadd -r webscraper && useradd -r -g webscraper webscraper

# Copy application
COPY --chown=webscraper:webscraper . /app
WORKDIR /app

# Switch to non-root user
USER webscraper

# Use secrets for sensitive data
COPY --from=secrets /run/secrets/ /run/secrets/
```

### 3. Kubernetes Security

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: webscraper-secrets
type: Opaque
data:
  gemini-api-key: <base64-encoded-key>
  secret-key: <base64-encoded-secret>
  encryption-key: <base64-encoded-encryption-key>

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webscraper
spec:
  template:
    spec:
      containers:
      - name: webscraper
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: webscraper-secrets
              key: gemini-api-key
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: webscraper-secrets
              key: secret-key
```

## 🔍 Security Validation

### Automated Security Checks

```python
# Add to your CI/CD pipeline
def validate_production_security():
    """Validate security configuration before deployment."""
    issues = SecurityConfig.validate_environment()
    
    if issues['critical']:
        print("❌ Critical security issues found:")
        for issue in issues['critical']:
            print(f"  - {issue}")
        sys.exit(1)
    
    if issues['warnings']:
        print("⚠️ Security warnings:")
        for warning in issues['warnings']:
            print(f"  - {warning}")
    
    print("✅ Security validation passed")
```

### Manual Security Checklist

- [ ] All API keys are stored in environment variables or secret management
- [ ] No placeholder values in production environment
- [ ] HTTPS enforced for all production endpoints
- [ ] CORS origins restricted to specific domains
- [ ] Debug mode disabled in production
- [ ] User agents are generic and non-identifying
- [ ] Database connections use SSL in production
- [ ] Rate limiting configured appropriately
- [ ] Session timeouts configured
- [ ] Logging doesn't expose sensitive information

## 🛠️ Security Tools and Scripts

### Generate Secure Keys

```bash
# Generate all required secure keys
python scripts/generate_secure_keys.py

# Generate specific key types
python -c "import secrets; print(secrets.token_urlsafe(64))"  # API keys
python -c "import secrets; print(secrets.token_hex(32))"      # Encryption keys
```

### Security Audit Script

```bash
# Run security validation
python -c "from src.utils.security_config import validate_security_on_startup; validate_security_on_startup()"

# Check for common security issues
grep -r "password\|secret\|key" --include="*.py" --exclude-dir=".git" .
```

## 📚 Additional Resources

- [OWASP Web Application Security](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python-security.readthedocs.io/)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

## 🆘 Security Incident Response

If you discover a security vulnerability:

1. **Do not** commit sensitive information to version control
2. Rotate all potentially compromised credentials immediately
3. Review access logs for unauthorized activity
4. Update security configurations following this guide
5. Consider implementing additional monitoring and alerting

---

**Remember**: Security is an ongoing process, not a one-time setup. Regularly review and update your security configurations as your application evolves.