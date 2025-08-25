# Security Configuration Recommendations

## 1. API Key Management

### Current Issue
```python
# VULNERABLE: Direct API key access
genai.configure(api_key=self.settings.gemini_api_key)
```

### Secure Solution
```python
# SECURE: Validate and sanitize API key access
def _initialize_gemini(self) -> None:
    """Initialize Gemini API configuration with security validation."""
    api_key = self._get_secure_api_key()
    if not api_key:
        logger.warning("Gemini API key not configured - AI processing will be disabled")
        return
    
    try:
        # Validate API key format before use
        if not self._validate_api_key_format(api_key):
            logger.error("Invalid Gemini API key format")
            return
            
        genai.configure(api_key=api_key)
        # ... rest of initialization
    except Exception as e:
        # Never log the actual API key
        logger.error("Failed to initialize Gemini API: Authentication failed")
        self._model = None

def _get_secure_api_key(self) -> Optional[str]:
    """Securely retrieve API key with validation."""
    api_key = self.settings.gemini_api_key
    
    if not api_key:
        return None
    
    # Check for placeholder values
    placeholder_indicators = ["your_", "example", "test", "demo", "change_me"]
    if any(indicator in api_key.lower() for indicator in placeholder_indicators):
        logger.error("Gemini API key appears to be a placeholder value")
        return None
    
    # Validate minimum length
    if len(api_key) < 20:
        logger.error("Gemini API key appears to be too short")
        return None
    
    return api_key

def _validate_api_key_format(self, api_key: str) -> bool:
    """Validate API key format without exposing the key."""
    # Basic format validation for Google API keys
    import re
    # Google API keys typically start with AIza and are 39 characters
    pattern = r'^AIza[0-9A-Za-z_-]{35}$'
    return bool(re.match(pattern, api_key))
```

### Environment Variables
```bash
# .env - SECURE
GEMINI_API_KEY=AIzaSyD4vX8F2mN9kL3pQ7rT1uY6wE8sA5bC2dF0gH4
GEMINI_API_KEY_VALIDATION=true
```

## 2. Database Security

### Current Issue
```python
# VULNERABLE: Potential credential exposure
database_url: str = Field(
    default="postgresql://localhost:5432/webscraper",
    description="PostgreSQL database URL"
)
```

### Secure Solution
```python
# SECURE: Separate components with validation
class DatabaseSettings(BaseSettings):
    """Secure database configuration."""
    
    db_host: str = Field(..., description="Database host")
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = Field(..., min_length=1, description="Database name")
    db_user: str = Field(..., min_length=1, description="Database user")
    db_password: SecretStr = Field(..., min_length=8, description="Database password")
    db_ssl_mode: str = Field(default="require", description="SSL mode")
    
    @property
    def database_url(self) -> str:
        """Build secure database URL."""
        password = self.db_password.get_secret_value()
        return (
            f"postgresql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?sslmode={self.db_ssl_mode}"
        )
    
    @validator('db_password')
    def validate_password_strength(cls, v):
        """Validate database password strength."""
        if isinstance(v, str):
            password = v
        else:
            password = v.get_secret_value()
        
        if len(password) < 12:
            raise ValueError("Database password must be at least 12 characters")
        
        # Check for common weak passwords
        weak_passwords = ["password", "admin", "root", "postgres", "123456"]
        if password.lower() in weak_passwords:
            raise ValueError("Database password is too weak")
        
        return v
```

### Environment Variables
```bash
# .env - SECURE
DB_HOST=localhost
DB_PORT=5432
DB_NAME=webscraper_prod
DB_USER=scraper_user
DB_PASSWORD=SecureP@ssw0rd123!WithSpecialChars
DB_SSL_MODE=require
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

## 3. User Agent Security

### Current Issue
```python
# VULNERABLE: Hardcoded user agents that can fingerprint
SCRAPER_DEFAULT_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

### Secure Solution
```python
# SECURE: Dynamic user agent management
class UserAgentManager:
    """Secure user agent management with rotation."""
    
    def __init__(self):
        self._user_agents = self._load_user_agents()
        self._current_index = 0
    
    def _load_user_agents(self) -> List[str]:
        """Load user agents from secure configuration."""
        # Load from environment or secure config file
        agents_str = os.getenv('SCRAPER_USER_AGENTS', '')
        if agents_str:
            return [ua.strip() for ua in agents_str.split('|') if ua.strip()]
        
        # Fallback to generic agents (no system-specific info)
        return [
            "Mozilla/5.0 (compatible; WebScraper/1.0)",
            "Mozilla/5.0 (compatible; DataCollector/1.0)",
            "Mozilla/5.0 (compatible; ContentAnalyzer/1.0)"
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent without system fingerprinting."""
        import random
        return random.choice(self._user_agents)
    
    def rotate_user_agent(self) -> str:
        """Rotate through user agents systematically."""
        agent = self._user_agents[self._current_index]
        self._current_index = (self._current_index + 1) % len(self._user_agents)
        return agent
```

### Environment Variables
```bash
# .env - SECURE (Generic user agents)
SCRAPER_USER_AGENTS="Mozilla/5.0 (compatible; WebScraper/1.0)|Mozilla/5.0 (compatible; DataCollector/1.0)|Mozilla/5.0 (compatible; ContentAnalyzer/1.0)"
SCRAPER_USER_AGENT_ROTATION=true
SCRAPER_RANDOMIZE_USER_AGENTS=true
```

## 4. Proxy Security

### Current Issue
```python
# VULNERABLE: Proxy URLs with credentials in logs
proxy_url="http://user:pass@proxy.example.com:8080"
```

### Secure Solution
```python
# SECURE: Separate proxy configuration
class ProxySettings(BaseSettings):
    """Secure proxy configuration."""
    
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = Field(None, ge=1, le=65535)
    proxy_username: Optional[str] = None
    proxy_password: Optional[SecretStr] = None
    proxy_protocol: str = Field(default="http", regex="^(http|https|socks4|socks5)$")
    
    @property
    def proxy_url(self) -> Optional[str]:
        """Build secure proxy URL."""
        if not self.proxy_host:
            return None
        
        auth = ""
        if self.proxy_username and self.proxy_password:
            password = self.proxy_password.get_secret_value()
            auth = f"{self.proxy_username}:{password}@"
        
        return f"{self.proxy_protocol}://{auth}{self.proxy_host}:{self.proxy_port}"
    
    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration for requests."""
        if not self.proxy_url:
            return None
        
        return {
            "http": self.proxy_url,
            "https": self.proxy_url
        }
```

### Environment Variables
```bash
# .env - SECURE
PROXY_HOST=proxy.company.com
PROXY_PORT=8080
PROXY_USERNAME=scraper_user
PROXY_PASSWORD=SecureProxyP@ss123!
PROXY_PROTOCOL=http
PROXY_ROTATION_ENABLED=true
```

## 5. Session Security

### Current Issue
```python
# VULNERABLE: Weak session tokens
session_token="abc123def456"
```

### Secure Solution
```python
# SECURE: Cryptographically secure session management
import secrets
import hashlib
from datetime import datetime, timedelta

class SecureSessionManager:
    """Secure session token management."""
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate cryptographically secure session token."""
        # Generate 32 bytes of random data
        random_bytes = secrets.token_bytes(32)
        # Create timestamp
        timestamp = str(int(datetime.utcnow().timestamp()))
        # Combine and hash
        combined = random_bytes + timestamp.encode()
        return hashlib.sha256(combined).hexdigest()
    
    @staticmethod
    def validate_session_token(token: str) -> bool:
        """Validate session token format."""
        if not token or len(token) != 64:
            return False
        
        # Check if it's a valid hex string
        try:
            int(token, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_token_expired(created_at: datetime, expires_in_hours: int = 24) -> bool:
        """Check if session token is expired."""
        expiry_time = created_at + timedelta(hours=expires_in_hours)
        return datetime.utcnow() > expiry_time
```

## 6. Logging Security

### Current Issue
```python
# VULNERABLE: Potential credential logging
logger.error(f"Failed to connect with URL: {database_url}")
```

### Secure Solution
```python
# SECURE: Sanitized logging
import re
from typing import Any

class SecureLogger:
    """Logger with automatic credential sanitization."""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self._sensitive_patterns = [
            r'password=([^&\s]+)',
            r'api_key=([^&\s]+)',
            r'token=([^&\s]+)',
            r'secret=([^&\s]+)',
            r'://[^:]+:([^@]+)@',  # URLs with passwords
        ]
    
    def _sanitize_message(self, message: str) -> str:
        """Remove sensitive information from log messages."""
        sanitized = message
        for pattern in self._sensitive_patterns:
            sanitized = re.sub(pattern, lambda m: f"{m.group(0).split('=')[0]}=***", sanitized)
        return sanitized
    
    def error(self, message: str, *args, **kwargs):
        """Log error with sanitization."""
        sanitized_message = self._sanitize_message(str(message))
        self.logger.error(sanitized_message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info with sanitization."""
        sanitized_message = self._sanitize_message(str(message))
        self.logger.info(sanitized_message, *args, **kwargs)
```

## 7. Complete Secure .env Template

```bash
# .env.secure - Production Template
# Copy this file to .env and fill in your actual values

# Application Configuration
APP_NAME="AI Web Scraper"
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration (Use individual components for security)
DB_HOST=your-db-host.com
DB_PORT=5432
DB_NAME=webscraper_prod
DB_USER=scraper_user
DB_PASSWORD=YourSecureDBPassword123!@#
DB_SSL_MODE=require
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis Configuration
REDIS_HOST=your-redis-host.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=YourSecureRedisPassword456!@#
REDIS_SSL=true

# AI Configuration
GEMINI_API_KEY=AIzaSyYourActualGeminiAPIKey123456789
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MAX_TOKENS=8192
GEMINI_API_KEY_VALIDATION=true

# API Security
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=YourSecure64CharacterSecretKeyGeneratedWithOpensslRandHex32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Security Configuration
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://dashboard.yourdomain.com
RATE_LIMIT_PER_MINUTE=60
ENABLE_HTTPS_ONLY=true

# Scraping Security
SCRAPER_USER_AGENTS="Mozilla/5.0 (compatible; YourBot/1.0)|Mozilla/5.0 (compatible; DataCollector/1.0)"
SCRAPER_RESPECT_ROBOTS_TXT=true
SCRAPER_VALIDATE_SSL=true
SCRAPER_MAX_REDIRECTS=5
SCRAPER_TIMEOUT=30

# Proxy Configuration (if needed)
PROXY_HOST=your-proxy-host.com
PROXY_PORT=8080
PROXY_USERNAME=proxy_user
PROXY_PASSWORD=YourSecureProxyPassword789!@#
PROXY_PROTOCOL=http

# Dashboard Configuration
DASHBOARD_HOST=127.0.0.1  # Restrict to localhost for security
DASHBOARD_PORT=8501
```

## Implementation Priority

1. **HIGH**: Fix API key exposure in content_processor.py
2. **HIGH**: Implement secure database credential handling
3. **MEDIUM**: Replace hardcoded user agents with dynamic management
4. **MEDIUM**: Secure proxy configuration
5. **LOW**: Improve session token generation in tests