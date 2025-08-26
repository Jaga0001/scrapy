#!/usr/bin/env python3
"""
Dashboard runner script for the Intelligent Web Scraper.

This script provides an easy way to launch the Streamlit dashboard
with proper configuration and error handling.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'streamlit',
        'plotly',
        'pandas',
        'psutil'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True


def setup_environment():
    """Set up environment variables for the dashboard."""
    # Set default environment variables if not already set
    env_vars = {
        'STREAMLIT_SERVER_PORT': '8501',
        'STREAMLIT_SERVER_ADDRESS': '0.0.0.0',
        'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'false',
        'STREAMLIT_SERVER_HEADLESS': 'true'
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value


def create_streamlit_config():
    """Create Streamlit configuration file if it doesn't exist."""
    config_dir = Path.home() / '.streamlit'
    config_file = config_dir / 'config.toml'
    
    if not config_file.exists():
        config_dir.mkdir(exist_ok=True)
        
        config_content = """
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[logger]
level = "info"
"""
        
        with open(config_file, 'w') as f:
            f.write(config_content.strip())
        
        print(f"✅ Created Streamlit config at {config_file}")


def run_dashboard(host='0.0.0.0', port=8501, debug=False):
    """Run the Streamlit dashboard."""
    dashboard_path = Path(__file__).parent / "src" / "dashboard" / "main.py"
    
    if not dashboard_path.exists():
        print(f"❌ Dashboard file not found: {dashboard_path}")
        return False
    
    # Prepare Streamlit command
    cmd = [
        sys.executable, '-m', 'streamlit', 'run',
        str(dashboard_path),
        '--server.address', host,
        '--server.port', str(port),
        '--server.headless', 'true',
        '--browser.gatherUsageStats', 'false'
    ]
    
    if debug:
        cmd.extend(['--logger.level', 'debug'])
    
    print(f"🚀 Starting Intelligent Web Scraper Dashboard...")
    print(f"📍 URL: http://{host}:{port}")
    print(f"🔧 Debug mode: {'enabled' if debug else 'disabled'}")
    print("Press Ctrl+C to stop the dashboard")
    print("-" * 50)
    
    try:
        # Run Streamlit
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start dashboard: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Intelligent Web Scraper Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dashboard.py                    # Run with default settings
  python run_dashboard.py --port 8502       # Run on custom port
  python run_dashboard.py --debug           # Run with debug logging
  python run_dashboard.py --host localhost  # Run on localhost only
        """
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host address to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8501,
        help='Port to run the dashboard on (default: 8501)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--no-check',
        action='store_true',
        help='Skip dependency checks'
    )
    
    args = parser.parse_args()
    
    print("🕷️  Intelligent Web Scraper Dashboard")
    print("=" * 50)
    
    # Check dependencies unless skipped
    if not args.no_check:
        if not check_dependencies():
            sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Create Streamlit config
    create_streamlit_config()
    
    # Run dashboard
    success = run_dashboard(
        host=args.host,
        port=args.port,
        debug=args.debug
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()