# Security Guide - AI Web Scraper

## 🛡️ Overview

This guide provides comprehensive security recommendations for deploying and operating the AI Web Scraper in production environments. Follow these guidelines to ensure your deployment is secure and follows industry best practices.

## 🔐 Environment Configuration Security

### 1. Secure Environment Files

**Use the secure template:**
```bash
cp .env.secure.example .env
chmod 600 .env  # Restrict file permissions
```

**Key security requirements:**
- Generate strong passwords (12+ characters)
- Use unique credentials for each environment
- Never commit `.env` files to version control
- Set restrictive file permissions (600)

### 2. Secret Generation

**Generate secure SECRET_KEY:**
```bash
openssl rand -hex 32
```

**Generate secure passwords:**
```bash
# For Redis password
openssl rand -base64 32

# For database password
openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
```

### 3. API Key Security

**Gemini API Key:**
- Must start with `AIza` and be exactly 39 characters
- Never use placeholder values like `your_api_key_here`
- Rotate keys regularly (monthly in production)

## 🔧 Redis Security Configuration

### 1. Secure Redis Setup

**Redis server configuration (`redis.conf`):**
```conf
# Authentication
requirepass YourSecureRedisPassword123!@#
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Network security
bind 127.0.0.1  # Localhost only
protected-mode yes
port 0          # Disable default port
unixsocket /var/run/redis/redis.sock
unixsocketperm 700

# SSL/TLS (for remote connections)
tls-port 6380
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
tls-protocols "TLSv1.2 TLSv1.3"

# Memory and performance
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 2. Environment Configuration

**Secure Redis environment variables:**
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_USERNAME=scraper_user
REDIS_PASSWORD=YourSecureRedisPassword123!@#
REDIS_SSL=true  # Enable for production
REDIS_SSL_CERT_REQS=required
REDIS_CONNECTION_TIMEOUT=30
REDIS_MAX_CONNECTIONS=20
```

### 3. Connection Security

The application uses secure Redis configuration with:
- Credential protection using Pydantic SecretStr
- SSL/TLS support for encrypted connections
- Connection pooling with timeouts
- Sanitized logging (credentials never logged)

## 🗄️ Database Security

### 1. PostgreSQL Security

**Secure database configuration:**
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=web_scraper
DB_USER=scraper_user
DB_PASSWORD=YourSecureDBPassword123!@#
DB_SSL_MODE=require
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

**PostgreSQL server security:**
```sql
-- Create dedicated user
CREATE USER scraper_user WITH PASSWORD 'YourSecureDBPassword123!@#';

-- Grant minimal permissions
GRANT CONNECT ON DATABASE web_scraper TO scraper_user;
GRANT USAGE ON SCHEMA public TO scraper_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scraper_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO scraper_user;

-- Enable SSL
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/path/to/server.crt';
ALTER SYSTEM SET ssl_key_file = '/path/to/server.key';
```

## 🌐 API Security

### 1. Authentication & Authorization

**JWT Configuration:**
```bash
JWT_SECRET_KEY=YourJWTSecretKeyDifferentFromMainSecret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

**Rate Limiting:**
```bash
API_RATE_LIMIT_PER_MINUTE=100
API_RATE_LIMIT_BURST=20
```

### 2. CORS Configuration

**Secure CORS settings:**
```bash
CORS_ORIGINS=https://yourdomain.com,https://dashboard.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE
CORS_ALLOW_HEADERS=Content-Type,Authorization
```

## 🕷️ Scraping Security

### 1. User Agent Security

**Use generic user agents to prevent fingerprinting:**
```bash
SCRAPER_USER_AGENTS="Mozilla/5.0 (compatible; WebScraper/1.0)|Mozilla/5.0 (compatible; DataCollector/1.0)|Mozilla/5.0 (compatible; ContentExtractor/1.0)"
```

### 2. Proxy Configuration

**Secure proxy setup:**
```bash
PROXY_ENABLED=true
PROXY_HTTP=http://proxy-server:8080
PROXY_HTTPS=https://proxy-server:8080
PROXY_USERNAME=proxy_user
PROXY_PASSWORD=SecureProxyPassword123!
```

### 3. Rate Limiting & Ethics

**Respectful scraping configuration:**
```bash
DEFAULT_REQUEST_DELAY=1.0
MAX_CONCURRENT_REQUESTS=5
RESPECT_ROBOTS_TXT=true
MAX_PAGES_PER_DOMAIN=1000
REQUEST_TIMEOUT=30
```

## 📊 Logging & Monitoring Security

### 1. Secure Logging

**Logging configuration:**
```bash
LOG_FORMAT=json
LOG_LEVEL=INFO  # Don't use DEBUG in production
LOG_FILE=/var/log/web-scraper/app.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5
```

**Key security features:**
- Credentials are never logged (sanitized URLs)
- Structured JSON logging for security analysis
- Log rotation to prevent disk space issues
- Separate log levels for different environments

### 2. Monitoring

**Security monitoring:**
```bash
METRICS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PORT=8080
```

## 🔍 Security Validation

### 1. Automated Security Checks

**Run security validation:**
```bash
python scripts/validate_security.py
```

This script checks for:
- Placeholder values in environment files
- Weak passwords and API keys
- Hardcoded secrets in source code
- Insecure file permissions
- Potential credential exposure in logs

### 2. Manual Security Checklist

**Before deployment:**
- [ ] All passwords are 12+ characters and unique
- [ ] SECRET_KEY generated with `openssl rand -hex 32`
- [ ] GEMINI_API_KEY is real (not placeholder)
- [ ] Database credentials are environment-specific
- [ ] SSL/TLS enabled for production
- [ ] File permissions set to 600 for .env files
- [ ] No placeholder values remain
- [ ] Rate limiting configured appropriately
- [ ] Logging doesn't expose sensitive data
- [ ] Redis authentication enabled
- [ ] Database SSL mode set to 'require'

## 🚀 Production Deployment Security

### 1. Infrastructure Security

**Docker security:**
```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Secure file permissions
COPY --chown=appuser:appuser . /app
RUN chmod 600 /app/.env
```

**Docker Compose security:**
```yaml
version: '3.8'
services:
  web-scraper:
    build: .
    environment:
      - ENVIRONMENT=production
    secrets:
      - redis_password
      - db_password
      - gemini_api_key
    networks:
      - internal

secrets:
  redis_password:
    external: true
  db_password:
    external: true
  gemini_api_key:
    external: true

networks:
  internal:
    driver: bridge
    internal: true
```

### 2. Network Security

**Firewall rules:**
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 6379/tcp   # Redis (internal only)
ufw deny 5432/tcp   # PostgreSQL (internal only)
```

**Reverse proxy (Nginx):**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔄 Security Maintenance

### 1. Regular Security Tasks

**Monthly:**
- [ ] Rotate API keys and secrets
- [ ] Update dependencies
- [ ] Review access logs for anomalies
- [ ] Run security validation script

**Quarterly:**
- [ ] Security audit of configuration
- [ ] Penetration testing
- [ ] Review and update security policies
- [ ] Update SSL certificates

**Annually:**
- [ ] Comprehensive security assessment
- [ ] Update security documentation
- [ ] Review and update incident response plan

### 2. Incident Response

**Security incident checklist:**
1. Isolate affected systems
2. Preserve evidence and logs
3. Assess scope and impact
4. Rotate all credentials
5. Apply security patches
6. Monitor for continued threats
7. Document lessons learned

## 📞 Security Support

**For security issues:**
1. Run `python scripts/validate_security.py` first
2. Review this security guide
3. Check environment configuration
4. Verify all credentials are secure
5. Test in staging environment before production

**Emergency security contacts:**
- System Administrator: [contact info]
- Security Team: [contact info]
- Cloud Provider Support: [contact info]

---

**⚠️ Remember**: Security is an ongoing process, not a one-time setup. Regularly review and update your security configuration as threats evolve.