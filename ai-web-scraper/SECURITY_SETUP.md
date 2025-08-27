# Security Configuration Guide

## Critical Security Setup Required

### 1. Generate Secure Keys

**SECRET_KEY**: Generate a secure 32+ character secret key:
```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

**ENCRYPTION_MASTER_KEY**: Generate a 64-character encryption key:
```bash
# Using Python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Secure API Key Configuration

**GEMINI_API_KEY**: Get your API key from Google AI Studio:
1. Visit https://makersuite.google.com/app/apikey
2. Create a new API key
3. Replace `your_gemini_api_key_here` in `.env`

### 3. Environment Variables Setup

Update your `.env` file with secure values:

```env
# Replace these placeholder values:
SECRET_KEY=your_generated_secret_key_here
ENCRYPTION_MASTER_KEY=your_generated_encryption_key_here
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 4. Production Security Checklist

- [ ] Replace all placeholder values in `.env`
- [ ] Set `ENVIRONMENT=production` for production deployments
- [ ] Use HTTPS in production (`API_BASE_URL=https://your-domain.com/api/v1`)
- [ ] Restrict CORS origins to your actual domains
- [ ] Enable SSL for database connections in production
- [ ] Set up proper firewall rules
- [ ] Use environment-specific configuration files
- [ ] Never commit `.env` files to version control

### 5. Database Security

For production, use a secure database URL:
```env
# PostgreSQL example
DATABASE_URL=postgresql://username:password@host:port/database

# MySQL example  
DATABASE_URL=mysql://username:password@host:port/database
```

### 6. User Agent Rotation

The system now uses rotating user agents from environment variables:
```env
SCRAPER_USER_AGENTS=agent1,agent2,agent3
```

### 7. API Endpoint Configuration

Dashboard API endpoint is now configurable:
```env
API_BASE_URL=http://localhost:8000/api/v1  # Development
API_BASE_URL=https://your-api.com/api/v1   # Production
```

## Security Best Practices

1. **Never hardcode credentials** in source code
2. **Use environment variables** for all sensitive configuration
3. **Rotate API keys** regularly
4. **Monitor API usage** for unusual activity
5. **Use HTTPS** in production
6. **Implement rate limiting** to prevent abuse
7. **Log security events** for monitoring
8. **Keep dependencies updated** for security patches

## Monitoring Security

The application includes built-in security monitoring:
- API key validation
- Rate limiting
- Input validation
- Error logging
- Audit trails

Check logs regularly for security warnings and errors.