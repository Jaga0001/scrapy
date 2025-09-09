# Security Guide for AI Web Scraper

This document outlines security best practices and configuration guidelines for the AI Web Scraper project.

## 🔒 Security Overview

The AI Web Scraper implements multiple layers of security to protect against common vulnerabilities and ensure safe operation in production environments.

## 🚨 Critical Security Issues Fixed

### 1. Insecure Default Credentials
**Issue:** Hardcoded placeholder credentials in `.env` file
**Fix:** Use the secure key generation script

```bash
# Generate secure keys
python scripts/generate_secure_keys.py

# Validate security configuration
python scripts/validate_security.py
```

### 2. API Key Management
**Issue:** Placeholder API keys that could cause failures
**Solution:** Proper environment variable management

```bash
# Set your actual Gemini API key
GEMINI_API_KEY=your_actual_api_key_from_google_ai_studio
```

### 3. User Agent Security
**Issue:** Hardcoded user agents that can be fingerprinted
**Solution:** Dynamic, generic user agents

```bash
# Use generic, non-identifying user agents
SCRAPER_USER_AGENTS=Mozilla/5.0 (compatible; WebScraper/1.0),Mozilla/5.0 (compatible; DataCollector/1.0)
```

## 🛡️ Security Configuration

### Environment Variables Security

#### Required Secure Keys
```bash
# Generate these using: python scripts/generate_secure_keys.py
SECRET_KEY=<64-character-secure-key>
ENCRYPTION_MASTER_KEY=<32-character-base64-key>
JWT_SECRET_KEY=<64-character-jwt-secret>
```

#### API Security
```bash
# Actual API key from Google AI Studio
GEMINI_API_KEY=<your-actual-gemini-api-key>

# Restrict API access
API_HOST=127.0.0.1  # Development
API_HOST=0.0.0.0    # Production (with proper firewall)
```

#### CORS Security
```bash
# Development
CORS_ORIGINS=http://127.0.0.1:8501,http://localhost:8501

# Production - restrict to your domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

#### Database Security
```bash
# Development
DATABASE_URL=sqlite:///webscraper.db

# Production - use encrypted connections
DATABASE_URL=postgresql://user:password@localhost/dbname?sslmode=require
```

### Scraping Security

#### Respectful Scraping
```bash
SCRAPER_RESPECT_ROBOTS_TXT=true
SCRAPER_DELAY_MIN=2
SCRAPER_DELAY_MAX=5
SCRAPER_TIMEOUT=15
SCRAPER_MAX_RETRIES=3
```

#### User Agent Rotation
```bash
# Use generic, non-identifying user agents
SCRAPER_USER_AGENTS=Mozilla/5.0 (compatible; WebScraper/1.0; +https://example.com/bot),Mozilla/5.0 (compatible; DataCollector/1.0),Mozilla/5.0 (compatible; ContentAnalyzer/1.0)
```

## 🔐 Production Security Checklist

### Before Deployment

- [ ] Run `python scripts/generate_secure_keys.py`
- [ ] Run `python scripts/validate_security.py`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure proper CORS origins
- [ ] Use HTTPS for all endpoints
- [ ] Set up secure database connections
- [ ] Configure proper firewall rules
- [ ] Set up SSL/TLS certificates
- [ ] Enable audit logging
- [ ] Configure data retention policies

### Environment Configuration

```bash
# Production environment settings
ENVIRONMENT=production
DEBUG=false

# Use HTTPS
API_BASE_URL=https://yourdomain.com/api/v1

# Secure database
DATABASE_URL=postgresql://user:password@localhost/dbname?sslmode=require

# Restrict CORS
CORS_ORIGINS=https://yourdomain.com

# Secure API binding
API_HOST=0.0.0.0  # With proper firewall/proxy
```

### Security Headers

The application automatically sets security headers:

- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security` (production only)

## 🔍 Security Monitoring

### Audit Logging

The system includes comprehensive audit logging:

```python
# Audit log configuration
AUDIT_LOG_FILE=logs/audit.log
AUDIT_LOG_MAX_SIZE_MB=100
AUDIT_LOG_BACKUP_COUNT=5
```

### Security Validation

Regular security validation:

```bash
# Run security validation
python scripts/validate_security.py

# Check for vulnerable dependencies
pip install pip-audit
pip-audit

# Alternative dependency checker
pip install safety
safety check
```

## 🚫 Security Anti-Patterns to Avoid

### ❌ Don't Do This

```bash
# Insecure configurations
SECRET_KEY=dev_key
CORS_ORIGINS=*
DEBUG=true  # in production
API_HOST=0.0.0.0  # without firewall
DATABASE_URL=sqlite:///db.sqlite  # in production
```

### ✅ Do This Instead

```bash
# Secure configurations
SECRET_KEY=<64-character-secure-key>
CORS_ORIGINS=https://yourdomain.com
DEBUG=false
API_HOST=127.0.0.1  # or 0.0.0.0 with proper firewall
DATABASE_URL=postgresql://user:password@localhost/dbname?sslmode=require
```

## 🔧 Security Tools

### Key Generation
```bash
python scripts/generate_secure_keys.py
```

### Security Validation
```bash
python scripts/validate_security.py
```

### Dependency Scanning
```bash
pip install pip-audit safety
pip-audit
safety check
```

## 📋 Security Incident Response

### If Security Issue Detected

1. **Immediate Actions:**
   - Stop the application
   - Rotate all API keys and secrets
   - Check logs for unauthorized access
   - Assess data exposure

2. **Investigation:**
   - Run security validation
   - Check audit logs
   - Review recent changes
   - Scan for vulnerabilities

3. **Remediation:**
   - Fix identified vulnerabilities
   - Update security configurations
   - Regenerate all secrets
   - Update dependencies

4. **Prevention:**
   - Implement additional monitoring
   - Update security policies
   - Conduct security review
   - Train team on security practices

## 🔗 Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.org/dev/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Streamlit Security](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)

## 📞 Security Contact

For security issues or questions:
- Review this security guide
- Run the security validation script
- Check the audit logs
- Follow the incident response procedures

Remember: Security is an ongoing process, not a one-time setup. Regularly review and update your security configuration.