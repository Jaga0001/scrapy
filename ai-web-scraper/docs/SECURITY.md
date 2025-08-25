# Security Guide for AI Web Scraper

## Overview

This document outlines security best practices and configurations for the AI Web Scraper project. Following these guidelines ensures secure operation and protects against common vulnerabilities.

## Environment Variables Security

### Required Environment Variables

All sensitive configuration must be externalized using environment variables:

```bash
# Database Configuration - NEVER hardcode these
DB_HOST=your-database-host
DB_PORT=5432
DB_NAME=webscraper
DB_USER=your-db-user
DB_PASSWORD=your-secure-db-password

# Alternative: Use complete DATABASE_URL (recommended for production)
DATABASE_URL=postgresql://user:password@host:port/database

# AI API Keys - NEVER commit these to version control
GEMINI_API_KEY=your-gemini-api-key-here

# Security Keys - Generate with: openssl rand -hex 32
SECRET_KEY=your-256-bit-secret-key-generate-with-openssl-rand-hex-32

# Redis Configuration
REDIS_URL=redis://:password@host:port/db
```

### Generating Secure Keys

```bash
# Generate a secure SECRET_KEY
openssl rand -hex 32

# Generate a secure database password
openssl rand -base64 32

# Generate API keys (service-specific)
python -c "import secrets; print(secrets.token_hex(32))"
```

## Scraping Security Configuration

### User Agent Security

**❌ AVOID**: Hardcoded user agents
```python
# BAD - Easily detected
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

**✅ RECOMMENDED**: Environment-based user agent rotation
```bash
# .env file
SCRAPER_DEFAULT_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SCRAPER_USER_AGENT_ROTATION=true
SCRAPER_CUSTOM_USER_AGENTS="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36,Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

### Proxy Configuration Security

**❌ AVOID**: Hardcoded proxy credentials
```python
# BAD - Credentials exposed
proxy_url = "http://username:password@proxy.example.com:8080"
```

**✅ RECOMMENDED**: Environment-based proxy configuration
```bash
# .env file
SCRAPER_DEFAULT_PROXY_URL="${PROXY_PROTOCOL}://${PROXY_USER}:${PROXY_PASS}@${PROXY_HOST}:${PROXY_PORT}"
PROXY_PROTOCOL=http
PROXY_HOST=your-proxy-host
PROXY_PORT=8080
PROXY_USER=your-proxy-username
PROXY_PASS=your-proxy-password
```

### Domain Security

Configure allowed and blocked domains:

```bash
# .env file
SECURITY_ALLOWED_DOMAINS="example.com,trusted-site.com"
SECURITY_BLOCKED_DOMAINS="malicious-site.com,blocked-domain.com"
```

## Database Security

### Connection Security

**✅ RECOMMENDED**: Use connection pooling and SSL
```python
# Secure database configuration
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_ECHO=false  # Disable in production to avoid logging queries
```

### Credential Management

1. **Never commit database credentials to version control**
2. **Use strong, unique passwords**
3. **Enable SSL/TLS for database connections**
4. **Implement connection pooling**
5. **Use read-only database users where possible**

## API Security

### Authentication

```bash
# .env file
SECRET_KEY=your-256-bit-secret-key-generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
```

### Rate Limiting

```bash
# .env file
API_RATE_LIMIT_PER_MINUTE=60
API_MAX_REQUEST_SIZE=10485760  # 10MB
```

## AI API Security

### Gemini API Configuration

```bash
# .env file
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MAX_TOKENS=8192
```

### Best Practices

1. **Rotate API keys regularly**
2. **Monitor API usage and costs**
3. **Implement request timeouts**
4. **Validate AI responses before processing**
5. **Never log API keys or responses containing sensitive data**

## Deployment Security

### Production Environment

```bash
# .env.production
DEBUG=false
LOG_LEVEL=WARNING
ENVIRONMENT=production

# Security headers
ALLOWED_HOSTS=your-domain.com
CORS_ORIGINS=https://your-frontend.com

# Database
DATABASE_URL=postgresql://user:password@prod-db:5432/webscraper?sslmode=require

# Redis
REDIS_URL=redis://:password@prod-redis:6379/0
```

### Docker Security

```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Don't include .env files in Docker images
# Use Docker secrets or environment variables instead
```

## Monitoring and Logging

### Secure Logging

```python
# Log configuration - NEVER log sensitive data
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

# Example: Safe logging
logger.info(f"Scraping job started for domain: {domain}")
# NEVER: logger.info(f"Using API key: {api_key}")
```

### Security Monitoring

Monitor for:
- Failed authentication attempts
- Unusual scraping patterns
- API rate limit violations
- Database connection failures
- Proxy connection issues

## Security Checklist

### Before Deployment

- [ ] All credentials externalized to environment variables
- [ ] Strong, unique passwords generated
- [ ] SSL/TLS enabled for all connections
- [ ] User agent rotation configured
- [ ] Domain allowlists/blocklists configured
- [ ] Rate limiting enabled
- [ ] Logging configured (without sensitive data)
- [ ] Security headers implemented
- [ ] API authentication enabled
- [ ] Database access restricted

### Regular Security Tasks

- [ ] Rotate API keys monthly
- [ ] Update user agent strings quarterly
- [ ] Review and update domain lists
- [ ] Monitor for security vulnerabilities
- [ ] Update dependencies regularly
- [ ] Review access logs for anomalies
- [ ] Test backup and recovery procedures

## Common Security Mistakes to Avoid

1. **Hardcoding credentials in source code**
2. **Using weak or default passwords**
3. **Exposing sensitive data in logs**
4. **Not validating user inputs**
5. **Using outdated dependencies**
6. **Not implementing rate limiting**
7. **Ignoring SSL certificate validation**
8. **Not rotating credentials regularly**
9. **Using obvious bot-like user agents**
10. **Not respecting robots.txt and rate limits**

## Incident Response

If you suspect a security breach:

1. **Immediately rotate all credentials**
2. **Review access logs for unauthorized activity**
3. **Check for data exfiltration**
4. **Update security configurations**
5. **Document the incident**
6. **Implement additional monitoring**

## Security Resources

- [OWASP Web Application Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Python Security Best Practices](https://python.org/dev/security/)
- [PostgreSQL Security Documentation](https://www.postgresql.org/docs/current/security.html)
- [Redis Security Documentation](https://redis.io/topics/security)

## Contact

For security-related questions or to report vulnerabilities, please contact the development team through secure channels.