# Security Configuration Guide

## Environment Variables Security Checklist

### 🔐 **Critical Security Variables**

These variables MUST be set securely in production:

```bash
# Generate with: openssl rand -hex 32
SECRET_KEY=your_64_character_secret_key_here

# Get from Google AI Studio: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=AIzaSyYourActualGeminiAPIKey123456789012345678

# Database credentials (never use defaults)
DB_PASSWORD=YourSecureDBPassword123!@#
DB_USER=scraper_user_not_postgres

# Redis authentication
REDIS_PASSWORD=YourSecureRedisPassword123!@#
```

### 🛡️ **Security Best Practices**

#### 1. **API Key Management**
```bash
# ✅ SECURE - Environment variable
GEMINI_API_KEY=${GEMINI_API_KEY}

# ❌ INSECURE - Hardcoded
GEMINI_API_KEY=AIzaSyActualKeyHere
```

#### 2. **Database Connection Security**
```bash
# ✅ SECURE - Separate components
DB_HOST=your-db-host.com
DB_PORT=5432
DB_NAME=webscraper_prod
DB_USER=scraper_user
DB_PASSWORD=${DB_PASSWORD}
DB_SSL_MODE=require

# ❌ INSECURE - Credentials in URL
DATABASE_URL=postgresql://user:password@host:5432/db
```

#### 3. **Proxy Configuration Security**
```bash
# ✅ SECURE - Separate authentication
PROXY_HOST=proxy.example.com
PROXY_PORT=8080
PROXY_USERNAME=${PROXY_USERNAME}
PROXY_PASSWORD=${PROXY_PASSWORD}
PROXY_PROTOCOL=https

# ❌ INSECURE - Credentials in URL
PROXY_URL=http://user:pass@proxy.com:8080
```

#### 4. **User Agent Security**
```bash
# ✅ SECURE - Generic agents to prevent fingerprinting
SCRAPER_USER_AGENTS="Mozilla/5.0 (compatible; WebScraper/1.0)|Mozilla/5.0 (compatible; DataCollector/1.0)"

# ❌ INSECURE - System-specific information
SCRAPER_USER_AGENTS="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

### 🔧 **Secure Configuration Examples**

#### Production .env Template
```bash
# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=${SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Database (SSL required in production)
DB_HOST=${DB_HOST}
DB_PORT=5432
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_SSL_MODE=require
DB_POOL_SIZE=20

# Redis (with authentication)
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_SSL=true

# AI Services
GEMINI_API_KEY=${GEMINI_API_KEY}
GEMINI_MODEL=gemini-2.0-flash-exp

# API Security
API_RATE_LIMIT_PER_MINUTE=100
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Scraping Security
SCRAPER_RESPECT_ROBOTS_TXT=true
SCRAPER_VALIDATE_SSL=true
SCRAPER_MAX_CONCURRENT_JOBS=5
SCRAPER_USER_AGENT_ROTATION=true

# Metrics Security
METRICS_DISK_PATH=/var/lib/webscraper
```

### 🚨 **Security Validation Commands**

#### Generate Secure Keys
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT secret
openssl rand -base64 32

# Generate database password
openssl rand -base64 24
```

#### Validate Configuration
```bash
# Check .env file permissions
ls -la .env
# Should show: -rw------- (600 permissions)

# Set secure permissions
chmod 600 .env

# Validate configuration
python -c "from config.security_validator import validate_environment_file; print(validate_environment_file())"
```

### 🔍 **Security Monitoring**

#### Log Security Events
```python
# Monitor for security events in logs
import logging
security_logger = logging.getLogger('security')

# Log authentication attempts
security_logger.info("API authentication attempt", extra={
    "user_agent": request.headers.get("User-Agent"),
    "ip_address": request.client.host,
    "endpoint": request.url.path
})
```

#### Metrics Security
```python
# Monitor for suspicious activity
from src.utils.metrics import get_metrics_collector

collector = get_metrics_collector()
collector.increment_counter('security_events')
collector.record_performance('auth_attempt', duration_ms, success=False, error_type='InvalidCredentials')
```

### 📋 **Pre-Deployment Security Checklist**

- [ ] All environment variables use `${VAR}` syntax or are properly externalized
- [ ] No hardcoded credentials in source code
- [ ] `.env` file has 600 permissions (`chmod 600 .env`)
- [ ] SECRET_KEY is 64+ characters generated with `openssl rand -hex 32`
- [ ] Database SSL is enabled (`DB_SSL_MODE=require`)
- [ ] Redis authentication is configured
- [ ] CORS origins are specific domains (no wildcards)
- [ ] User agents are generic (no system-specific info)
- [ ] API rate limiting is configured
- [ ] Debug mode is disabled in production
- [ ] Log level is INFO or higher in production
- [ ] All placeholder values are replaced with real credentials

### 🛠️ **Environment-Specific Configurations**

#### Development
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DB_SSL_MODE=prefer
REDIS_SSL=false
```

#### Staging
```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
DB_SSL_MODE=require
REDIS_SSL=true
```

#### Production
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
DB_SSL_MODE=require
REDIS_SSL=true
API_RATE_LIMIT_PER_MINUTE=60
```

### 🔐 **Credential Rotation Schedule**

- **SECRET_KEY**: Rotate monthly
- **Database passwords**: Rotate quarterly
- **API keys**: Rotate when compromised or annually
- **Redis passwords**: Rotate quarterly
- **Proxy credentials**: Rotate monthly

### 🧪 **Test Environment Security**

#### Secure Test Configuration
```bash
# Use environment variables for test credentials
TEST_DATABASE_URL=${TEST_DATABASE_URL}
TEST_REDIS_URL=${TEST_REDIS_URL}
TEST_GEMINI_API_KEY=${TEST_GEMINI_API_KEY}

# Generic test user agents
TEST_USER_AGENTS="Mozilla/5.0 (compatible; TestBot/1.0)|Mozilla/5.0 (compatible; IntegrationTest/1.0)"
```

#### GitHub Actions Security
```yaml
# Use GitHub Secrets instead of hardcoded values
- name: Set up environment
  run: |
    echo "DATABASE_URL=${{ secrets.TEST_DATABASE_URL }}" >> $GITHUB_ENV
    echo "REDIS_URL=${{ secrets.TEST_REDIS_URL }}" >> $GITHUB_ENV
    echo "GEMINI_API_KEY=${{ secrets.TEST_GEMINI_API_KEY }}" >> $GITHUB_ENV
```

#### Test Security Checklist
- [ ] No hardcoded credentials in test files
- [ ] Use environment variables for all sensitive data
- [ ] Generate unique test credentials (never use production)
- [ ] Use generic user agents in tests
- [ ] Use test services (httpbin.org) for external requests
- [ ] Set GitHub Secrets for CI/CD credentials
- [ ] Sanitize test data to remove sensitive information

### 📞 **Security Incident Response**

If credentials are compromised:

1. **Immediate**: Rotate all affected credentials
2. **Review**: Check logs for unauthorized access
3. **Update**: Deploy new credentials to all environments
4. **Monitor**: Watch for suspicious activity
5. **Document**: Record incident and response actions