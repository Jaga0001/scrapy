# Security Guide for AI Web Scraper

## Overview

This document outlines security best practices and configuration requirements for the AI Web Scraper application.

## Environment Variables Security

### Critical Environment Variables

These variables MUST be set securely in production:

```bash
# Generate with: openssl rand -hex 32
SECRET_KEY=your_secure_256_bit_secret_key_here

# Use strong database credentials
DB_PASSWORD=your_secure_database_password

# Set environment explicitly
ENVIRONMENT=production
```

### API Keys

```bash
# Obtain from Google AI Studio: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_gemini_api_key

# Never use placeholder values in production
# ❌ WRONG: GEMINI_API_KEY=your_gemini_api_key_here
# ✅ CORRECT: GEMINI_API_KEY=AIzaSyC...actual_key_here
```

### Database Security

```bash
# Use strong, unique credentials
DB_USER=webscraper_app_user  # Not 'postgres' or 'root'
DB_PASSWORD=complex_secure_password_123!

# For production, prefer connection URLs
DATABASE_URL=postgresql://user:password@host:port/database
```

## File Permissions

Ensure sensitive files have restricted permissions:

```bash
# Environment files should not be world-readable
chmod 600 .env
chmod 600 .env.production

# Configuration files
chmod 644 config/*.py

# Data directories
chmod 700 data/
chmod 700 data/exports/
```

## Production Deployment Checklist

### Before Deployment

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Generate secure `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Configure strong database credentials
- [ ] Set valid `GEMINI_API_KEY`
- [ ] Configure `CORS_ORIGINS` appropriately
- [ ] Set up rate limiting
- [ ] Review file permissions

### Security Validation

Run the security audit before deployment:

```python
from config.settings import get_settings
from config.security_validator import run_security_audit

settings = get_settings()
audit_results = run_security_audit(settings)

if audit_results["status"] == "CRITICAL_ISSUES":
    print("❌ Critical security issues found!")
    for error in audit_results["errors"]:
        print(f"  - {error}")
    exit(1)
```

## Common Security Mistakes

### ❌ Don't Do This

```bash
# Weak secret keys
SECRET_KEY=secret
SECRET_KEY=your-secret-key-change-in-production

# Default database credentials
DB_USER=postgres
DB_PASSWORD=password

# Placeholder API keys
GEMINI_API_KEY=your_gemini_api_key_here

# Debug mode in production
DEBUG=true
```

### ✅ Do This Instead

```bash
# Strong secret key
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# Unique database credentials
DB_USER=webscraper_prod_user
DB_PASSWORD=Str0ng_P@ssw0rd_2024!

# Real API key
GEMINI_API_KEY=AIzaSyC8X9Y7Z6A5B4C3D2E1F0...

# Production settings
DEBUG=false
ENVIRONMENT=production
```

## Monitoring and Auditing

### Log Security Events

The application logs security-relevant events:

- Authentication attempts
- Configuration validation errors
- API key usage
- Database connection issues

### Regular Security Audits

Run security audits regularly:

```bash
# Manual audit
python -c "
from config.settings import get_settings
from config.security_validator import run_security_audit
import json
settings = get_settings()
results = run_security_audit(settings)
print(json.dumps(results, indent=2))
"
```

## Incident Response

If you suspect a security breach:

1. **Immediately** rotate all secrets:
   - Generate new `SECRET_KEY`
   - Rotate database passwords
   - Regenerate API keys

2. **Review logs** for suspicious activity

3. **Update dependencies** to latest secure versions

4. **Run security audit** to identify vulnerabilities

## Contact

For security issues, please contact the development team immediately.

**Do not** create public GitHub issues for security vulnerabilities.