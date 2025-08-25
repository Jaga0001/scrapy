---
inclusion: always
---

# Web Scraper Technology Stack & Standards

## Core Python Stack
**Scraping Engine**: Selenium 4.15+ with BeautifulSoup4 for robust dynamic content handling
**AI Integration**: Gemini 2.5 API via Google AI Studio for intelligent content processing
**Web Framework**: FastAPI with async/await for high-performance API endpoints
**Dashboard**: Streamlit for real-time monitoring and control interface
**Data Processing**: Pandas + NumPy for automated cleaning and transformation

## Architecture Principles
- **Async-First**: Use asyncio and async/await patterns for all I/O operations
- **Type Safety**: Implement comprehensive type hints with Pydantic models
- **Error Resilience**: Circuit breaker patterns with exponential backoff
- **Scalability**: Designed for horizontal scaling with queue-based job processing
- **Security**: All credentials externalized, input validation, rate limiting

## Development Standards
**Code Style**: Black formatter, isort imports, flake8 linting
**Testing**: pytest with 90%+ coverage, separate unit/integration/e2e test suites  
**Documentation**: Comprehensive docstrings, OpenAPI auto-generation, README-driven development
**Logging**: Structured JSON logs with correlation IDs, multiple log levels
**Configuration**: Environment-based config with python-dotenv, no hardcoded values

## Performance Requirements  
- **Scraping Speed**: Target 50+ pages/minute with proper rate limiting
- **API Response**: <500ms average response time for data retrieval
- **Memory Efficiency**: Process large datasets without memory leaks
- **Concurrent Operations**: Support 10+ simultaneous scraping jobs
- **Database Performance**: Optimized queries with proper indexing

## Security & Compliance
- **Anti-Detection**: Rotate user agents, respect robots.txt, implement delays
- **Data Privacy**: Hash PII, implement data retention policies  
- **API Security**: JWT authentication, rate limiting, input sanitization
- **Infrastructure**: Secure credential storage, encrypted data at rest
