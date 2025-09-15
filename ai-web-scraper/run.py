#!/usr/bin/env python3
"""
Simple launcher script to run both API server and Streamlit dashboard.
"""

import os
import sys
import subprocess
import time
import threading
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = {
        'uvicorn': 'uvicorn',
        'streamlit': 'streamlit',
        'fastapi': 'fastapi',
        'requests': 'requests'
    }
    
    missing_packages = []
    for package, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is missing")
    
    if missing_packages:
        print(f"\n❌ Missing required packages: {', '.join(missing_packages)}")
        print("   Install them with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All required dependencies are installed")
    return True

def test_streamlit():
    """Test if Streamlit can be run."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "streamlit", "--version"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ Streamlit version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Streamlit test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Streamlit test error: {e}")
        return False

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
        "--reload",
        "--log-level", "info"
    ]
    
    process = None
    try:
        process = subprocess.Popen(cmd, cwd=project_root)
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping API server...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing API server...")
                process.kill()
        print("✅ API server stopped")

def start_dashboard():
    """Start the Streamlit dashboard."""
    print("📊 Starting dashboard...")
    
    dashboard_host = os.getenv("DASHBOARD_HOST", "localhost")
    dashboard_port = os.getenv("DASHBOARD_PORT", "8501")
    
    # Check if dashboard file exists
    dashboard_file = project_root / "src" / "dashboard" / "main.py"
    if not dashboard_file.exists():
        print(f"❌ Dashboard file not found: {dashboard_file}")
        print("   Creating a simple dashboard...")
        create_simple_dashboard()
        dashboard_file = project_root / "src" / "dashboard" / "main.py"  # Update path after creation
    
    # Verify the file was created successfully
    if not dashboard_file.exists():
        print(f"❌ Failed to create dashboard file: {dashboard_file}")
        return
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_file),
        "--server.address", "localhost",
        "--server.port", dashboard_port,
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false"
    ]
    
    print(f"📊 Dashboard will open at: http://localhost:{dashboard_port}")
    
    process = None
    try:
        # Start the process without capturing output to allow browser to open
        process = subprocess.Popen(cmd, cwd=project_root)
        
        print("📊 Dashboard started! Check your browser or the URL above.")
        print("   Press Ctrl+C to stop the dashboard")
        
        # Wait for the process to complete
        process.wait()
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping dashboard...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing dashboard...")
                process.kill()
        print("✅ Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        if process:
            process.terminate()

def create_simple_dashboard():
    """Create a simple dashboard if it doesn't exist."""
    dashboard_dir = project_root / "src" / "dashboard"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py file
    init_file = dashboard_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")
    
    simple_dashboard = '''"""
Simple Web Scraper Dashboard
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

st.set_page_config(
    page_title="Web Scraper Dashboard",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Web Scraper Dashboard")
st.markdown("---")

# API base URL
API_BASE = "http://127.0.0.1:8000/api/v1"

def call_api(endpoint, method="GET", data=None):
    """Helper to call API endpoints"""
    try:
        url = f"{API_BASE}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Make sure the API server is running on http://127.0.0.1:8000")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Dashboard", "Create Job", "View Jobs", "View Data"])

if page == "Dashboard":
    st.header("📊 System Overview")
    
    # Health check
    health = call_api("/health")
    if health:
        st.success("✅ API Server is running")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", health.get("status", "Unknown"))
        with col2:
            st.metric("Database", "Connected" if health.get("database_connected") else "Disconnected")
        with col3:
            ai_status = health.get("services", {}).get("ai_service", "unknown")
            st.metric("AI Service", ai_status.title())
    else:
        st.error("❌ API Server is not responding")

elif page == "Create Job":
    st.header("🚀 Create New Scraping Job")
    
    with st.form("create_job"):
        name = st.text_input("Job Name", placeholder="My Scraping Job")
        url = st.text_input("URL to Scrape", placeholder="https://example.com")
        max_pages = st.number_input("Max Pages", min_value=1, max_value=100, value=1)
        
        if st.form_submit_button("Create Job"):
            if name and url:
                job_data = {
                    "name": name,
                    "url": url,
                    "max_pages": max_pages
                }
                result = call_api("/scraping/jobs", "POST", job_data)
                if result:
                    st.success(f"✅ Job '{name}' created successfully!")
                    st.json(result)
            else:
                st.error("Please fill in all fields")

elif page == "View Jobs":
    st.header("📋 Scraping Jobs")
    
    jobs = call_api("/scraping/jobs")
    if jobs and jobs.get("jobs"):
        for job in jobs["jobs"]:
            with st.expander(f"{job['name']} - {job['status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**URL:** {job['url']}")
                    st.write(f"**Status:** {job['status']}")
                    st.write(f"**Created:** {job.get('created_at', 'Unknown')}")
                
                with col2:
                    if job['status'] != 'Running':
                        if st.button(f"Start Job", key=f"start_{job['id']}"):
                            result = call_api(f"/scraping/jobs/{job['id']}/start", "PUT")
                            if result:
                                st.success("Job started!")
                                st.rerun()
                    
                    if st.button(f"Delete Job", key=f"delete_{job['id']}"):
                        result = call_api(f"/scraping/jobs/{job['id']}", "DELETE")
                        if result:
                            st.success("Job deleted!")
                            st.rerun()
    else:
        st.info("No jobs found. Create your first job!")

elif page == "View Data":
    st.header("📊 Scraped Data")
    
    data = call_api("/data")
    if data and data.get("data"):
        df = pd.DataFrame(data["data"])
        st.write(f"Total records: {len(df)}")
        st.dataframe(df, use_container_width=True)
        
        if st.button("Clear All Data"):
            result = call_api("/data", "DELETE")
            if result:
                st.success("All data cleared!")
                st.rerun()
    else:
        st.info("No data found. Run some scraping jobs first!")

# Auto-refresh option
if st.sidebar.checkbox("Auto-refresh (30s)"):
    time.sleep(30)
    st.rerun()
'''
    
    dashboard_file = dashboard_dir / "main.py"
    try:
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(simple_dashboard)
        print(f"✅ Created simple dashboard at {dashboard_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to create dashboard file: {e}")
        return False

def main():
    """Main function to run both services."""
    print("🚀 AI Web Scraper Launcher")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Test Streamlit
    if not test_streamlit():
        print("⚠️  Streamlit may not work properly, but continuing...")
    
    # Load environment
    load_environment()
    
    # Check configuration
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = os.getenv("API_PORT", "8000")
    dashboard_host = os.getenv("DASHBOARD_HOST", "localhost")
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
            
            # Start API server in a separate process
            api_process = None
            dashboard_process = None
            
            try:
                # Start API server
                api_cmd = [
                    sys.executable, "-m", "uvicorn",
                    "src.api.main:app",
                    "--host", api_host,
                    "--port", api_port,
                    "--reload",
                    "--log-level", "info"
                ]
                
                print("🚀 Starting API server...")
                api_process = subprocess.Popen(api_cmd, cwd=project_root)
                
                # Wait for API to start
                print("⏳ Waiting for API server to start...")
                time.sleep(5)
                
                # Check if API is running
                try:
                    import requests
                    response = requests.get(f"http://{api_host}:{api_port}/api/v1/health", timeout=5)
                    if response.status_code == 200:
                        print("✅ API server is running")
                    else:
                        print("⚠️  API server may not be fully ready")
                except:
                    print("⚠️  API server may not be fully ready")
                
                # Start dashboard
                dashboard_file = project_root / "src" / "dashboard" / "main.py"
                if not dashboard_file.exists():
                    print("📊 Creating simple dashboard...")
                    create_simple_dashboard()
                
                dashboard_cmd = [
                    sys.executable, "-m", "streamlit", "run",
                    str(dashboard_file),
                    "--server.address", "localhost",
                    "--server.port", dashboard_port,
                    "--server.headless", "false",
                    "--browser.gatherUsageStats", "false"
                ]
                
                print("📊 Starting dashboard...")
                print(f"📊 Dashboard will open at: http://localhost:{dashboard_port}")
                dashboard_process = subprocess.Popen(dashboard_cmd, cwd=project_root)
                
                # Wait for both processes
                while True:
                    if api_process.poll() is not None:
                        print("❌ API server stopped unexpectedly")
                        break
                    if dashboard_process.poll() is not None:
                        print("❌ Dashboard stopped unexpectedly")
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n🛑 Shutting down both services...")
                
                if dashboard_process:
                    dashboard_process.terminate()
                    try:
                        dashboard_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        dashboard_process.kill()
                
                if api_process:
                    api_process.terminate()
                    try:
                        api_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        api_process.kill()
                
                print("✅ Both services stopped")
        else:
            print("❌ Invalid choice. Please run again and select 1, 2, or 3.")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
