# AI Web Scraper

A simple AI-powered web scraping system with a dashboard interface.

## Quick Start

1. **Install dependencies:**
   ```bash
   cd ai-web-scraper
   pip install -e .
   ```

2. **Add your API key:**
   ```bash
   # Edit .env file (created automatically)
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

That's it! The system will start both the API server and dashboard.

## Access Points

- **Dashboard:** http://localhost:8501
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Individual Services

Start only specific services if needed:

```bash
python main.py api        # API server only
python main.py dashboard  # Dashboard only
python main.py setup      # Setup environment only
```

## Features

- Simple web scraping with AI content analysis
- Real-time dashboard for job management
- Data export (CSV, JSON)
- RESTful API for automation

## Requirements

- Python 3.12+
- Chrome browser (for Selenium)
- Gemini API key (optional, for AI features)

## Usage

1. Open the dashboard at http://localhost:8501
2. Create a new scraping job with a URL
3. Start the job and monitor progress
4. Export scraped data when complete

The system handles everything else automatically!