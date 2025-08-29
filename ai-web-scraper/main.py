#!/usr/bin/env python3
"""
AI Web Scraper - Simple startup script
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def setup_environment():
    """Setup basic environment and database"""
    print("🔧 Setting up environment...")
    
    # Create database tables
    try:
        from src.database import create_tables
        create_tables()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database setup warning: {e}")
    
    # Check for .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file from template...")
        template_file = Path(".env.template")
        if template_file.exists():
            import shutil
            shutil.copy(template_file, env_file)
            print("✅ .env file created - please add your API keys")
        else:
            # Create minimal .env with secure defaults
            with open(".env", "w") as f:
                f.write("# AI Web Scraper Environment Configuration\n")
                f.write("# IMPORTANT: Replace placeholder values before production use!\n\n")
                f.write("# Get your API key from: https://makersuite.google.com/app/apikey\n")
                f.write("GEMINI_API_KEY=your_actual_gemini_api_key_here\n\n")
                f.write("# Generate secure keys with: python scripts/generate_secure_keys.py\n")
                f.write("SECRET_KEY=INSECURE_DEV_KEY_REPLACE_BEFORE_PRODUCTION\n")
                f.write("ENCRYPTION_MASTER_KEY=INSECURE_DEV_KEY_REPLACE_BEFORE_PRODUCTION\n\n")
                f.write("# Database\n")
                f.write("DATABASE_URL=sqlite:///webscraper.db\n\n")
                f.write("# API Configuration\n")
                f.write("API_HOST=0.0.0.0\n")
                f.write("API_PORT=8000\n\n")
                f.write("# Dashboard\n")
                f.write("DASHBOARD_HOST=0.0.0.0\n")
                f.write("DASHBOARD_PORT=8501\n")
                f.write("API_BASE_URL=http://localhost:8000/api/v1\n\n")
                f.write("# Security\n")
                f.write("CORS_ORIGINS=http://localhost:3000,http://localhost:8501\n")
                f.write("SCRAPER_RESPECT_ROBOTS_TXT=true\n")
            print("✅ Basic .env file created with security reminders")

def start_api():
    """Start the API server"""
    print("🚀 Starting API server...")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "src.api.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")

def start_dashboard():
    """Start the dashboard"""
    print("🎨 Starting dashboard...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "src/dashboard/main.py", 
            "--server.port", "8501"
        ], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")

def start_both():
    """Start both API and dashboard"""
    import threading
    
    setup_environment()
    
    print("🚀 Starting both API and Dashboard...")
    print("📡 API will be available at: http://localhost:8000")
    print("🎨 Dashboard will be available at: http://localhost:8501")
    print("📚 API docs at: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both services\n")
    
    # Start API in a separate thread
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    
    # Wait a moment for API to start
    time.sleep(3)
    
    # Start dashboard in main thread
    try:
        start_dashboard()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "api":
            setup_environment()
            start_api()
        elif command == "dashboard":
            start_dashboard()
        elif command == "setup":
            setup_environment()
            print("✅ Setup complete! Run 'python main.py' to start both services")
        else:
            print("Usage:")
            print("  python main.py          - Start both API and dashboard")
            print("  python main.py api      - Start only API server")
            print("  python main.py dashboard - Start only dashboard")
            print("  python main.py setup    - Setup environment only")
    else:
        start_both()

if __name__ == "__main__":
    main()
