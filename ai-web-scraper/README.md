# AI-Powered Web Scraper

A professional, enterprise-grade web scraping system with AI-powered content analysis, real-time monitoring, and comprehensive data management capabilities.

## 🌟 Key Features

### 🤖 AI-Enhanced Scraping
- **Gemini AI Integration**: Intelligent content analysis and quality scoring
- **Smart Content Extraction**: Automatically identifies main content areas
- **Quality Assessment**: AI-powered confidence and quality scoring
- **Content Categorization**: Automatic classification of scraped content

### 🚀 Professional Scraping Engine
- **Multiple Scraping Strategies**: Simple HTTP requests + Advanced Selenium support
- **Anti-Detection**: Stealth mode, user agent rotation, respectful delays
- **Robust Error Handling**: Circuit breakers, exponential backoff, retry logic
- **Ethical Scraping**: Robots.txt compliance, rate limiting, politeness delays

### 📊 Real-Time Dashboard
- **Interactive Management**: Create, monitor, and manage scraping jobs
- **Live Analytics**: Real-time performance metrics and visualizations
- **Data Explorer**: Search, filter, and export scraped data
- **System Monitoring**: Health checks and performance tracking

### 🔒 Enterprise Security
- **Secure Configuration**: Environment-based secrets management
- **Input Validation**: Comprehensive data validation and sanitization
- **Rate Limiting**: Configurable request throttling and quotas
- **Audit Logging**: Structured logging with correlation IDs

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd ai-web-scraper

# Run setup script
python setup.py
```

### 2. Configure API Keys

Edit `.env` file and add your API keys:

```bash
# Get your Gemini API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Generate secure keys (optional, for production)
python scripts/generate_secure_keys.py
```

### 3. Test the Scraper

```bash
# Test basic scraping functionality
python test_scraper.py
```

### 4. Start the System

```bash
# Start API server and dashboard
python run_system.py
```

### 5. Access the Interface

- **Dashboard**: http://localhost:8501
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📋 System Requirements

- **Python**: 3.8 or higher
- **Memory**: 2GB RAM minimum (4GB recommended)
- **Storage**: 1GB free space
- **Network**: Internet connection for AI services

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# AI Configuration
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Scraping Settings
SCRAPER_DELAY_MIN=2          # Minimum delay between requests (seconds)
SCRAPER_DELAY_MAX=5          # Maximum delay between requests (seconds)
SCRAPER_TIMEOUT=15           # Request timeout (seconds)
SCRAPER_MAX_RETRIES=3        # Maximum retry attempts
SCRAPER_RESPECT_ROBOTS_TXT=true

# Security
RATE_LIMIT_REQUESTS=100      # Requests per window
RATE_LIMIT_WINDOW=3600       # Rate limit window (seconds)
```

### Advanced Configuration

For production deployments, see `SECURITY.md` for security hardening guidelines.

## 🎯 Usage Examples

### Basic Web Scraping

```python
from src.scraper.simple_scraper import SimpleWebScraper
from src.models.pydantic_models import ScrapingConfig

# Create configuration
config = ScrapingConfig(
    delay_between_requests=2.0,
    extract_images=True,
    extract_links=True,
    respect_robots_txt=True
)

# Scrape a URL
async with SimpleWebScraper(config) as scraper:
    result = await scraper.scrape_url("https://example.com")
    print(f"Title: {result.content['title']}")
    print(f"Quality Score: {result.data_quality_score}")
```

### API Usage

```bash
# Create a scraping job
curl -X POST "http://localhost:8000/api/v1/scraping/jobs" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Job", "url": "https://example.com", "max_pages": 1}'

# Start the job
curl -X PUT "http://localhost:8000/api/v1/scraping/jobs/{job_id}/start"

# Get scraped data
curl "http://localhost:8000/api/v1/data"
```

## 🏗️ Architecture

```
ai-web-scraper/
├── src/
│   ├── api/           # FastAPI REST API
│   ├── dashboard/     # Streamlit dashboard
│   ├── scraper/       # Core scraping engine
│   ├── models/        # Data models
│   ├── utils/         # Utilities and helpers
│   └── database.py    # Database configuration
├── scripts/           # Utility scripts
├── tests/            # Test suite
└── docs/             # Documentation
```

## 🔍 Monitoring & Debugging

### Health Checks

```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Check system status in dashboard
# Navigate to Dashboard > System Status
```

### Logs

- **API Logs**: Console output from `run_system.py`
- **Scraper Logs**: Structured JSON logs with correlation IDs
- **Error Tracking**: Automatic error categorization and reporting

## 🛡️ Security Features

- **Input Validation**: All inputs validated with Pydantic models
- **Rate Limiting**: Configurable request throttling
- **Secure Defaults**: Security-first configuration
- **Environment Isolation**: Secrets managed via environment variables
- **Audit Trail**: Comprehensive logging of all operations

## 🚨 Troubleshooting

### Common Issues

1. **"Cannot connect to API"**
   - Ensure API server is running: `python run_system.py`
   - Check port configuration in `.env`

2. **"AI analysis failed"**
   - Verify `GEMINI_API_KEY` is set correctly
   - Check internet connection

3. **"Scraping blocked"**
   - Website may have anti-bot protection
   - Try increasing delays in configuration
   - Check robots.txt compliance

### Getting Help

1. Check the logs for detailed error messages
2. Run security validation: `python scripts/validate_security.py`
3. Test individual components: `python test_scraper.py`

## 📈 Performance Optimization

- **Concurrent Jobs**: System supports multiple simultaneous scraping jobs
- **Caching**: Intelligent caching of robots.txt and metadata
- **Resource Management**: Automatic cleanup and memory management
- **Quality Scoring**: AI-powered content quality assessment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.