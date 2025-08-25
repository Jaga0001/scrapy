# AI Web Scraper

An enterprise-grade intelligent web scraping system that combines Selenium automation with Gemini AI processing capabilities to extract, analyze, and serve structured data from any website.

## Features

- **Intelligent Content Processing**: Gemini AI automatically understands and categorizes scraped content
- **Real-time Monitoring**: Live dashboard showing scraping progress, data quality, and system health
- **Production-Ready Architecture**: Scalable, fault-tolerant system with comprehensive error handling
- **Multi-format Export**: Clean, structured data available in CSV, JSON, and API formats

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd ai-web-scraper
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run the Application**
   ```bash
   # Start API server
   python -m src.api.main
   
   # Start dashboard (in another terminal)
   streamlit run src/dashboard/main.py
   ```

## Project Structure

```
ai-web-scraper/
├── src/
│   ├── scraper/        # Core scraping logic
│   ├── ai/             # Gemini AI integration
│   ├── api/            # FastAPI endpoints
│   ├── dashboard/      # Streamlit components
│   ├── pipeline/       # Data processing
│   ├── models/         # Pydantic data models
│   └── utils/          # Shared utilities
├── tests/              # Test suites
├── config/             # Configuration files
└── data/               # Sample data and exports
```

## Configuration

See `.env.example` for all available configuration options.

## Development

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run tests:
   ```bash
   pytest
   ```

3. Format code:
   ```bash
   black src/
   isort src/
   ```

## License

MIT License