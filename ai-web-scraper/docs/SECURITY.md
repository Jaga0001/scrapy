# Security Configuration Guide

## Environment Variables Setup

### 1. Generate Secure Keys

```bash
# Generate a secure JWT secret key
openssl rand -hex 32

# Generate a secure database password
openssl rand -base64 32

# Generate a secure Redis password
openssl rand -base64 24
```

### 2. Production Environment Variables

Create a `.env` file with the following secure configuration:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Database (Use individual components OR full URL, not both)
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=webscraper_prod
DB_USER=webscraper_user
DB_PASSWORD=your-secure-generated-password

# Alternative: Full database URL (preferred for production)
# DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-secure-redis-password

# AI Configuration
GEMINI_API_KEY=your-actual-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash-exp

# API Security
SECRET_KEY=your-generated-256-bit-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15

# Network Security
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://dashboard.yourdomain.com
RATE_LIMIT_PER_MINUTE=30

# Scraping Security
SCRAPER_RESPECT_ROBOTS_TXT=true
SCRAPER_MAX_CONCURRENT_JOBS=5
SCRAPER_DEFAULT_DELAY=2.0
SCRAPER_VALIDATE_SSL=true
```

### 3. Security Best Practices

#### API Keys and Secrets
- **Never commit** `.env` files to version control
- Use different keys for development, staging, and production
- Rotate keys regularly (every 90 days)
- Use key management services (AWS Secrets Manager, Azure Key Vault) in production

#### Database Security
- Use strong, unique passwords for database users
- Create dedicated database users with minimal required permissions
- Enable SSL/TLS for database connections
- Use connection pooling with proper limits

#### Network Security
- Restrict `ALLOWED_HOSTS` to your actual domains
- Configure `CORS_ORIGINS` to only allow trusted origins
- Use HTTPS in production
- Implement rate limiting to prevent abuse

#### Scraping Ethics
- Always respect `robots.txt`
- Implement reasonable delays between requests
- Use appropriate user agents (don't impersonate real browsers maliciously)
- Monitor and respect rate limits from target websites

### 4. Environment-Specific Configurations

#### Development
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DB_HOST=localhost
REDIS_HOST=localhost
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000,http://localhost:8501
```

#### Staging
```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
# Use staging-specific credentials
```

#### Production
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
# Use production credentials with maximum security
```

### 5. Credential Validation

The application includes built-in validation for:
- Secret key length and complexity
- API key format validation
- Database URL security checks
- Host and origin validation

### 6. Monitoring and Alerting

Set up monitoring for:
- Failed authentication attempts
- Unusual scraping patterns
- API rate limit violations
- Database connection failures
- SSL certificate expiration

### 7. Data Protection

- Enable data encryption at rest when `ENCRYPT_STORED_DATA=true`
- Configure data retention policies with `DATA_RETENTION_DAYS`
- Implement proper data anonymization for sensitive content
- Regular security audits and penetration testing

## Quick Security Checklist

- [ ] All secrets stored in environment variables
- [ ] Strong, unique passwords generated
- [ ] SSL/TLS enabled for all connections
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Robots.txt respected
- [ ] Input validation enabled
- [ ] Logging configured (without exposing secrets)
- [ ] Regular security updates applied
- [ ] Monitoring and alerting set up