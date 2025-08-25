# Project Structure

## Directory Organization

The project follows a microservices-inspired architecture with clear separation of concerns:

```
intelligent-web-scraper/
├── .kiro/                      # Kiro configuration and specs
│   ├── specs/                  # Feature specifications
│   ├── steering/               # AI assistant guidance rules
│   └── hooks/                  # Automated workflow hooks
├── ai-web-scraper/
│   ├── src/
│       ├── scraper/ # Core scraping logic
│       ├── ai/ # Claude 4.0 integration
│       ├── api/ # FastAPI endpoints
│       ├── dashboard/ # Streamlit components
│       ├── pipeline/ # Data processing
│       ├── models/ # Pydantic data models
│       └── utils/ # Shared utilities
│   ├── tests/ # Test suites
│   ├── docs/ # Documentation
│   ├── config/ # Configuration files
│   └── data/ # Sample data and exports
```


## Naming Conventions
**Files**: snake_case (e.g., `web_scraper.py`, `ai_processor.py`)
**Classes**: PascalCase (e.g., `WebScraperEngine`, `AIContentProcessor`)  
**Functions/Variables**: snake_case (e.g., `extract_data()`, `scraping_results`)
**Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_ATTEMPTS`, `DEFAULT_TIMEOUT`)

## Import Organization
1. Standard library imports
2. Third-party packages  
3. Local application imports
4. Always use absolute imports from project root

## Component Architecture
**Scraper Module**: Handle all Selenium operations, browser management, content extraction
**AI Module**: Claude 4.0 integration, content analysis, data validation
**API Module**: FastAPI routes, authentication, response formatting
**Pipeline Module**: Data cleaning, transformation, export functionality
**Dashboard Module**: Streamlit pages, real-time updates, user controls

## Configuration Management
- Environment variables for all external dependencies
- Separate config files for different environments (dev/staging/prod)
- Use Pydantic Settings for type-safe configuration
- Never commit secrets or API keys to version control
