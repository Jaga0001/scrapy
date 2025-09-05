#!/usr/bin/env python3
"""
Startup script for the AI Web Scraper system.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class SystemRunner:
    """Manages the startup and shutdown of the web scraper system."""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
    def check_environment(self):
        """Check if the environment is properly configured."""
        print("🔍 Checking environment configuration...")
        
        # Check required environment variables
        required_vars = [
            "DATABASE_URL",
            "API_HOST", 
            "API_PORT",
            "DASHBOARD_HOST",
            "DASHBOARD_PORT"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("   Please check your .env file")
            return False
        
        # Check optional but recommended variables
        optional_vars = ["GEMINI_API_KEY", "SECRET_KEY", "ENCRYPTION_MASTER_KEY"]
        for var in optional_vars:
            if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
                print(f"⚠️  Warning: {var} not properly configured")
        
        print("✅ Environment check completed")
        return True
    
    def setup_database(self):
        """Initialize the database."""
        print("🗄️  Setting up database...")
        
        try:
            # Import database setup
            from src.database import engine, Base
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            print("✅ Database setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Database setup failed: {str(e)}")
            return False
    
    def start_api_server(self):
        """Start the FastAPI server."""
        print("🚀 Starting API server...")
        
        try:
            api_host = os.getenv("API_HOST", "127.0.0.1")
            api_port = os.getenv("API_PORT", "8000")
            
            # Start API server
            cmd = [
                sys.executable, "-m", "uvicorn",
                "src.api.main:app",
                "--host", api_host,
                "--port", api_port,
                "--reload"
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes.append(("API Server", process))
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                print(f"✅ API server started on http://{api_host}:{api_port}")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ API server failed to start")
                print(f"   stdout: {stdout.decode()}")
                print(f"   stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start API server: {str(e)}")
            return False
    
    def start_dashboard(self):
        """Start the Streamlit dashboard."""
        print("📊 Starting dashboard...")
        
        try:
            dashboard_host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
            dashboard_port = os.getenv("DASHBOARD_PORT", "8501")
            
            # Start dashboard
            cmd = [
                sys.executable, "-m", "streamlit", "run",
                "src/dashboard/main.py",
                "--server.address", dashboard_host,
                "--server.port", dashboard_port,
                "--server.headless", "true"
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes.append(("Dashboard", process))
            
            # Wait a moment for server to start
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                print(f"✅ Dashboard started on http://{dashboard_host}:{dashboard_port}")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Dashboard failed to start")
                print(f"   stdout: {stdout.decode()}")
                print(f"   stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start dashboard: {str(e)}")
            return False
    
    def monitor_processes(self):
        """Monitor running processes."""
        while self.running:
            try:
                for name, process in self.processes:
                    if process.poll() is not None:
                        print(f"⚠️  {name} process has stopped")
                        # Could implement restart logic here
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"❌ Error monitoring processes: {str(e)}")
                break
    
    def shutdown(self):
        """Shutdown all processes gracefully."""
        print("\n🛑 Shutting down system...")
        self.running = False
        
        for name, process in self.processes:
            try:
                print(f"   Stopping {name}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"   Force killing {name}...")
                    process.kill()
                    
            except Exception as e:
                print(f"   Error stopping {name}: {str(e)}")
        
        print("✅ System shutdown completed")
    
    def run(self):
        """Run the complete system."""
        print("🚀 AI Web Scraper System Startup")
        print("=" * 50)
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Step 1: Check environment
            if not self.check_environment():
                return False
            
            # Step 2: Setup database
            if not self.setup_database():
                return False
            
            # Step 3: Start API server
            if not self.start_api_server():
                return False
            
            # Step 4: Start dashboard
            if not self.start_dashboard():
                return False
            
            print("\n🎉 System startup completed successfully!")
            print("=" * 50)
            print(f"📊 Dashboard: http://{os.getenv('DASHBOARD_HOST', '0.0.0.0')}:{os.getenv('DASHBOARD_PORT', '8501')}")
            print(f"🔌 API: http://{os.getenv('API_HOST', '127.0.0.1')}:{os.getenv('API_PORT', '8000')}")
            print(f"📖 API Docs: http://{os.getenv('API_HOST', '127.0.0.1')}:{os.getenv('API_PORT', '8000')}/docs")
            print("\nPress Ctrl+C to shutdown")
            
            # Start monitoring in a separate thread
            monitor_thread = threading.Thread(target=self.monitor_processes)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
            
            return True
            
        except KeyboardInterrupt:
            self.shutdown()
            return True
        except Exception as e:
            print(f"❌ System startup failed: {str(e)}")
            self.shutdown()
            return False


def main():
    """Main entry point."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the system
    runner = SystemRunner()
    success = runner.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()