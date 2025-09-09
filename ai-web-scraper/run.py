#!/usr/bin/env python3
"""
Simple launcher script to run both API server and Streamlit dashboard.
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def load_environment():
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded from .env")
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment")

def start_api_server():
    """Start the FastAPI server."""
    print("🚀 Starting API server...")
    
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = os.getenv("API_PORT", "8000")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api.main:app",
        "--host", api_host,
        "--port", api_port,
        "--reload"
    ]
    
    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")

def start_dashboard():
    """Start the Streamlit dashboard."""
    print("📊 Starting dashboard...")
    
    dashboard_host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    dashboard_port = os.getenv("DASHBOARD_PORT", "8501")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "src/dashboard/main.py",
        "--server.address", dashboard_host,
        "--server.port", dashboard_port,
        "--server.headless", "true"
    ]
    
    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")

def main():
    """Main function to run both services."""
    print("🚀 AI Web Scraper Launcher")
    print("=" * 40)
    
    # Load environment
    load_environment()
    
    # Check configuration
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = os.getenv("API_PORT", "8000")
    dashboard_host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    dashboard_port = os.getenv("DASHBOARD_PORT", "8501")
    
    print(f"📡 API will run on: http://{api_host}:{api_port}")
    print(f"📊 Dashboard will run on: http://{dashboard_host}:{dashboard_port}")
    print(f"📖 API Docs: http://{api_host}:{api_port}/docs")
    print("\nChoose an option:")
    print("1. Start API server only")
    print("2. Start dashboard only")
    print("3. Start both (recommended)")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            start_api_server()
        elif choice == "2":
            start_dashboard()
        elif choice == "3":
            print("\n🚀 Starting both services...")
            print("Press Ctrl+C to stop both services")
            
            # Start API server in a separate thread
            api_thread = threading.Thread(target=start_api_server, daemon=True)
            api_thread.start()
            
            # Wait a moment for API to start
            time.sleep(3)
            
            # Start dashboard in main thread
            start_dashboard()
        else:
            print("❌ Invalid choice. Please run again and select 1, 2, or 3.")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
