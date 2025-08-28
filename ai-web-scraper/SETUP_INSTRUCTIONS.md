# Virtual Environment Setup Instructions

## 🚀 Quick Start (Recommended)

### Using UV (Fastest)
```bash
# Install UV if not already installed
pip install uv

# Navigate to project directory
cd ai-web-scraper

# Create and activate virtual environment with dependencies
uv sync

# Activate the environment
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### Using Standard Python
```bash
# Create virtual environment
python -m venv .venv

# Activate environment
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -e .
```

## 🔧 Development Setup

### Install Development Dependencies
```bash
# With UV
uv sync --dev

# With pip
pip install -e ".[dev]"
```

### Verify Installation
```bash
# Check Python version
python --version  # Should be 3.12+

# Verify key packages
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import selenium; print(f'Selenium: {selenium.__version__}')"
python -c "import google.generativeai; print('Gemini AI: OK')"
```

## 🌐 Browser Setup for Selenium

### Chrome (Recommended)
```bash
# Chrome will be auto-detected by Selenium 4.15+
# Ensure Chrome 120+ is installed
```

### Firefox Alternative
```bash
# Install geckodriver (if using Firefox)
# Windows (with chocolatey)
choco install geckodriver

# macOS (with homebrew)
brew install geckodriver

# Linux
sudo apt-get install firefox-geckodriver
```

## 📋 Environment Configuration

### 1. Copy Environment Template
```bash
cp .env.template .env
```

### 2. Configure Required Variables
```bash
# Edit .env file with your values
GEMINI_API_KEY=your_actual_gemini_api_key_here
SECRET_KEY=your_secure_secret_key_32_chars_min
ENCRYPTION_MASTER_KEY=your_encryption_key_64_chars
```

### 3. Generate Secure Keys
```bash
# Generate SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate ENCRYPTION_MASTER_KEY
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_MASTER_KEY=' + Fernet.generate_key().decode())"
```

## 🧪 Testing Setup

### Run Tests
```bash
# Install test dependencies
uv sync --dev

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality Checks
```bash
# Format code
black src/
isort src/

# Lint code
flake8 src/
```

## 🚀 Running the Application

### Start API Server
```bash
# Development mode
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Start Dashboard
```bash
# In a separate terminal
streamlit run src/dashboard/main.py --server.port 8501
```

### Access Applications
- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501
- **Health Check**: http://localhost:8000/api/v1/health

## 🔍 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure project root is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Selenium WebDriver Issues
```bash
# Clear browser cache and restart
# Update Chrome to latest version
# Check firewall settings
```

#### Database Issues
```bash
# Reset database
rm webscraper.db
python -c "from src.database import create_tables; create_tables()"
```

#### Permission Errors (Windows)
```bash
# Run as administrator or check antivirus settings
# Ensure .venv directory is not read-only
```

### Performance Optimization
```bash
# For better performance, consider:
pip install uvloop  # Linux/macOS only
pip install orjson  # Faster JSON processing
```

## 📊 Monitoring Setup

### Enable Structured Logging
```bash
# Set log level in .env
LOG_LEVEL=INFO

# View logs
tail -f logs/app.log
```

### Health Monitoring
```bash
# Check system health
curl http://localhost:8000/api/v1/health
```