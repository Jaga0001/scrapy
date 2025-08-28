# AI Web Scraper

An enterprise-grade intelligent web scraping system that combines Selenium automation with Gemini AI processing capabilities to extract, analyze, and serve structured data from any website through real-time monitoring and RESTful APIs.

## Features

- **Intelligent Content Processing**: Gemini AI automatically understands and categorizes scraped content
- **Real-time Monitoring**: Live dashboard showing scraping progress, data quality, and system health
- **Production-Ready Architecture**: Scalable, fault-tolerant system with comprehensive error handling
- **Multi-format Export**: Clean, structured data available in CSV, JSON, and API formats

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure environment:**
   - Add your Gemini API key to `.env`:
     ```
     GEMINI_API_KEY=your_actual_api_key_here
     ```
   - Get your API key from: https://makersuite.google.com/app/apikey

3. **Start the API server:**
   ```bash
   uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Start the dashboard (in another terminal):**
   ```bash
   uv run streamlit run src/dashboard/main.py --server.port 8501
   ```

## Project Structure

```
ai-web-scraper/
├── src/
│   ├── scraper/     # Core scraping logic
│   ├── ai/          # Gemini AI integration
│   ├── api/         # FastAPI endpoints
│   ├── dashboard/   # Streamlit components
│   ├── pipeline/    # Data processing
│   ├── models/      # Pydantic data models
│   └── utils/       # Shared utilities
├── tests/           # Test suites
└── data/           # Sample data and exports
```

## Requirements

- Python 3.12+
- Chrome/Chromium browser for Selenium
- Gemini API key