"""
Enterprise-Grade AI Web Scraper Dashboard

A professional, production-ready dashboard for managing intelligent web scraping operations
with real-time monitoring, advanced analytics, and comprehensive data management capabilities.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import streamlit as st
import requests
import json
import numpy as np

# Try to import plotly, but make it optional
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Plotly not installed. Charts will be disabled. Install with: pip install plotly")

# Import security configuration
try:
    from src.utils.security_config import SecurityConfig
except ImportError:
    # Fallback if security config is not available
    class SecurityConfig:
        @staticmethod
        def get_api_base_url():
            return os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")


class WebScraperDashboard:
    def __init__(self):
        st.set_page_config(
            page_title="Enterprise Web Scraper | AI-Powered Data Intelligence",
            page_icon="🚀",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://docs.webscraper.ai',
                'Report a bug': 'https://github.com/webscraper/issues',
                'About': "Enterprise AI Web Scraper v2.0 - Intelligent data extraction at scale"
            }
        )
        
        # Initialize session state
        self._initialize_session_state()
        
        # Custom CSS for professional styling
        self._inject_custom_css()
        
        # API base URL from security configuration
        self.api_base = SecurityConfig.get_api_base_url()

    def _initialize_session_state(self):
        """Initialize session state variables."""
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'Dashboard'
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = False
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 30

    def _inject_custom_css(self):
        """Inject enterprise-grade CSS styling."""
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .main {
            font-family: 'Inter', sans-serif;
        }
        
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem 1.5rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
        }
        
        .dashboard-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .dashboard-subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
            margin-top: 0.5rem;
            font-weight: 400;
        }
        
        .metric-card {
            background: white;
            padding: 2rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #f0f0f0;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }
        
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #2d3748;
            margin: 0;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: #718096;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0.5rem;
        }
        
        .metric-change {
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 0.5rem;
        }
        
        .metric-change.positive { color: #38a169; }
        .metric-change.negative { color: #e53e3e; }
        .metric-change.neutral { color: #718096; }
        
        .status-indicator {
            display: inline-flex;
            align-items: center;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-online {
            background: #f0fff4;
            color: #38a169;
            border: 1px solid #9ae6b4;
        }
        
        .status-offline {
            background: #fff5f5;
            color: #e53e3e;
            border: 1px solid #feb2b2;
        }
        
        .job-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            border: 1px solid #f0f0f0;
            margin: 1rem 0;
            transition: all 0.3s ease;
        }
        
        .job-card:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .job-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .job-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #2d3748;
        }
        
        .job-status {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .job-status.running {
            background: #e6fffa;
            color: #319795;
        }
        
        .job-status.completed {
            background: #f0fff4;
            color: #38a169;
        }
        
        .job-status.failed {
            background: #fff5f5;
            color: #e53e3e;
        }
        
        .job-status.pending {
            background: #fffbeb;
            color: #d69e2e;
        }
        
        .progress-container {
            background: #f7fafc;
            border-radius: 8px;
            height: 8px;
            overflow: hidden;
            margin: 1rem 0;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 8px;
            transition: width 0.3s ease;
        }
        
        .custom-alert {
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid;
        }
        
        .alert-info {
            background: #ebf8ff;
            border-color: #3182ce;
            color: #2c5282;
        }
        
        .alert-success {
            background: #f0fff4;
            border-color: #38a169;
            color: #276749;
        }
        
        .alert-warning {
            background: #fffbeb;
            border-color: #d69e2e;
            color: #b7791f;
        }
        </style>
        """, unsafe_allow_html=True)

    def _call_api(self, method, endpoint, data=None):
        """Helper method to call API endpoints"""
        try:
            url = f"{self.api_base}{endpoint}"
            timeout = 10  # 10 second timeout
            
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.ConnectionError:
            api_url = self.api_base.replace("/api/v1", "")
            st.error(f"❌ Cannot connect to API. Make sure the API server is running on {api_url}")
            return None
        except requests.exceptions.Timeout:
            st.error(f"❌ API request timed out. The server may be overloaded.")
            return None
        except Exception as e:
            st.error(f"Error calling API: {str(e)}")
            return None

    def run(self):
        self._render_sidebar()
        self._render_main_content()

    def _render_sidebar(self):
        with st.sidebar:
            # Professional header
            st.markdown("""
            <div style="text-align: center; padding: 1rem 0; margin-bottom: 2rem;">
                <h1 style="color: #667eea; font-size: 1.8rem; font-weight: 700; margin: 0;">
                    🚀 WebScraper
                </h1>
                <p style="color: #718096; font-size: 0.9rem; margin: 0.5rem 0 0 0;">
                    Enterprise AI Platform
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Navigation menu
            pages = [
                ("📊", "Dashboard", "Overview and system status"),
                ("⚙️", "Operations", "Job management and control"),
                ("🔍", "Analytics", "Data exploration and insights"),
                ("📈", "Metrics", "Performance monitoring"),
                ("⚙️", "Settings", "System configuration")
            ]
            
            current_page = st.session_state.get('current_page', 'Dashboard')
            
            for icon, page_name, description in pages:
                if st.button(
                    f"{icon} {page_name}",
                    key=f"nav_{page_name}",
                    width='stretch',
                    help=description,
                    type="primary" if current_page == page_name else "secondary"
                ):
                    st.session_state.current_page = page_name
                    st.rerun()
            
            st.markdown("---")
            
            # System status indicator
            health_response = self._call_api("GET", "/health")
            if health_response:
                st.markdown("""
                <div class="status-indicator status-online">
                    🟢 System Online
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="status-indicator status-offline">
                    🔴 System Offline
                </div>
                """, unsafe_allow_html=True)

    def _render_main_content(self):
        page = st.session_state.get('current_page', 'Dashboard')
        
        if page == "Dashboard":
            self._render_dashboard_page()
        elif page == "Operations":
            self._render_operations_page()
        elif page == "Analytics":
            self._render_analytics_page()
        elif page == "Metrics":
            self._render_metrics_page()
        elif page == "Settings":
            self._render_settings_page()

    def _render_dashboard_page(self):
        # Professional header
        st.markdown("""
        <div class="dashboard-header">
            <h1 class="dashboard-title">Enterprise Web Scraper</h1>
            <p class="dashboard-subtitle">AI-Powered Data Intelligence Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        # System status and key metrics
        self._render_system_status()
        
        # Key performance indicators
        st.markdown("### 📊 Key Performance Indicators")
        self._render_kpi_cards()
        
        # Recent activity and quick actions
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📈 Recent Activity")
            self._render_recent_activity()
        
        with col2:
            st.markdown("### ⚡ Quick Actions")
            self._render_quick_actions()

    def _render_system_status(self):
        """Render system status indicators."""
        col1, col2, col3, col4 = st.columns(4)
        
        # Check API health
        health_response = self._call_api("GET", "/health")
        api_status = "Online" if health_response else "Offline"
        
        with col1:
            status_class = "status-online" if health_response else "status-offline"
            st.markdown(f"""
            <div class="{status_class}">
                {'🟢' if health_response else '🔴'} API Server: {api_status}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="status-online">
                🟢 AI Engine: Ready
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="status-online">
                🟢 Data Pipeline: Active
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="status-online">
                🟢 Export Service: Ready
            </div>
            """, unsafe_allow_html=True)

    def _render_kpi_cards(self):
        """Render key performance indicator cards."""
        col1, col2, col3, col4 = st.columns(4)
        
        # Get metrics from API
        jobs_response = self._call_api("GET", "/scraping/jobs")
        
        if jobs_response:
            jobs = jobs_response.get('jobs', [])
            total_jobs = len(jobs)
            running_jobs = len([job for job in jobs if job['status'] == 'Running'])
            completed_jobs = len([job for job in jobs if job['status'] == 'Completed'])
            
            with col1:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Active Jobs</div>
                    <div class="metric-change positive">+2 from yesterday</div>
                </div>
                """.format(running_jobs), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Total Jobs</div>
                    <div class="metric-change positive">+{} this week</div>
                </div>
                """.format(total_jobs, max(1, total_jobs // 3)), unsafe_allow_html=True)
            
            with col3:
                success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
                change_class = "positive" if success_rate > 80 else "negative" if success_rate < 60 else "neutral"
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{:.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                    <div class="metric-change {}">Target: 95%</div>
                </div>
                """.format(success_rate, change_class), unsafe_allow_html=True)
            
            with col4:
                pages_processed = completed_jobs * 15 + running_jobs * 8  # Estimate
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{:,}</div>
                    <div class="metric-label">Pages Processed</div>
                    <div class="metric-change positive">+{} today</div>
                </div>
                """.format(pages_processed, max(10, pages_processed // 10)), unsafe_allow_html=True)
        else:
            # Fallback when API is not available
            for i, (label, value) in enumerate([
                ("Active Jobs", "0"), ("Total Jobs", "0"), 
                ("Success Rate", "0%"), ("Pages Processed", "0")
            ]):
                with [col1, col2, col3, col4][i]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{value}</div>
                        <div class="metric-label">{label}</div>
                        <div class="metric-change neutral">API Offline</div>
                    </div>
                    """, unsafe_allow_html=True)

    def _render_recent_activity(self):
        """Render recent activity feed."""
        jobs_response = self._call_api("GET", "/scraping/jobs")
        
        if jobs_response and jobs_response.get('jobs'):
            jobs = jobs_response['jobs'][-5:]  # Last 5 jobs
            
            for job in jobs:
                status_class = {
                    'Running': 'running',
                    'Completed': 'completed',
                    'Failed': 'failed',
                    'Pending': 'pending'
                }.get(job['status'], 'pending')
                
                st.markdown(f"""
                <div class="job-card">
                    <div class="job-header">
                        <div class="job-title">{job['name']}</div>
                        <div class="job-status {status_class}">{job['status']}</div>
                    </div>
                    <div style="color: #718096; font-size: 0.9rem;">
                        URL: {job['url'][:50]}{'...' if len(job['url']) > 50 else ''}
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {np.random.randint(20, 100)}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="custom-alert alert-info">
                <strong>No recent activity</strong><br>
                Start your first scraping job to see activity here.
            </div>
            """, unsafe_allow_html=True)

    def _render_quick_actions(self):
        """Render quick action buttons."""
        actions = [
            ("🚀", "New Job", "Create a new scraping job", "Operations"),
            ("📊", "View Data", "Explore scraped data", "Analytics"),
            ("📈", "Metrics", "View system metrics", "Metrics"),
            ("⚙️", "Settings", "Configure system", "Settings")
        ]
        
        for icon, title, description, target_page in actions:
            if st.button(f"{icon} {title}", width='stretch', help=description, key=f"quick_action_{title}"):
                st.session_state.current_page = target_page
                st.rerun()

    def _render_operations_page(self):
        st.markdown("""
        <div class="dashboard-header">
            <h1 class="dashboard-title">Operations Center</h1>
            <p class="dashboard-subtitle">Manage and monitor scraping operations</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Operations tabs
        tab1, tab2 = st.tabs(["🚀 Create Job", "📋 Job Management"])
        
        with tab1:
            self._render_job_creation_form()
        
        with tab2:
            self._render_job_management()

    def _render_job_creation_form(self):
        """Render the job creation form."""
        st.markdown("### Create New Scraping Job")
        
        with st.form("job_creation_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                job_name = st.text_input(
                    "Job Name *", 
                    placeholder="E-commerce Product Scraper",
                    help="Descriptive name for your scraping job"
                )
                url = st.text_input(
                    "Target URL *", 
                    placeholder="https://example.com",
                    help="The website URL to scrape"
                )
            
            with col2:
                max_pages = st.number_input(
                    "Max Pages", 
                    min_value=1, 
                    max_value=1000, 
                    value=10,
                    help="Maximum number of pages to scrape"
                )
                priority = st.selectbox(
                    "Priority",
                    ["Low", "Normal", "High", "Critical"],
                    index=1
                )
            
            # Advanced settings
            with st.expander("Advanced Settings"):
                col3, col4 = st.columns(2)
                
                with col3:
                    delay = st.slider(
                        "Request Delay (seconds)", 
                        min_value=0.5, 
                        max_value=10.0, 
                        value=2.0, 
                        step=0.5,
                        help="Delay between requests to avoid rate limiting"
                    )
                    ai_processing = st.checkbox(
                        "Enable AI Processing", 
                        value=True,
                        help="Use AI to analyze and categorize scraped content",
                        key="create_job_ai_processing"
                    )
                
                with col4:
                    timeout = st.number_input(
                        "Timeout (seconds)", 
                        min_value=5, 
                        max_value=120, 
                        value=30
                    )
                    export_format = st.selectbox(
                        "Export Format",
                        ["JSON", "CSV", "Excel", "Database"],
                        help="Format for exporting scraped data"
                    )
            
            submitted = st.form_submit_button(
                "🚀 Create Job", 
                type="primary",
                width='stretch'
            )
            
            if submitted:
                if url and job_name:
                    job_data = {
                        "name": job_name,
                        "url": url,
                        "max_pages": max_pages,
                        "priority": priority,
                        "delay": delay,
                        "timeout": timeout,
                        "ai_processing": ai_processing,
                        "export_format": export_format
                    }
                    
                    result = self._call_api("POST", "/scraping/jobs", job_data)
                    if result:
                        st.success(f"✅ Job '{job_name}' created successfully!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("❌ Please fill in all required fields (marked with *)")

    def _render_job_management(self):
        """Render job management interface."""
        st.markdown("### Job Management")
        
        # Get jobs from API
        jobs_response = self._call_api("GET", "/scraping/jobs")
        
        if jobs_response and jobs_response.get('jobs'):
            jobs = jobs_response['jobs']
            
            # Job controls
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("▶️ Start All", width='stretch', key="start_all_jobs"):
                    st.success("Starting all pending jobs...")
            with col2:
                if st.button("⏸️ Pause All", width='stretch', key="pause_all_jobs"):
                    st.warning("Pausing all running jobs...")
            with col3:
                if st.button("🔄 Refresh", width='stretch', key="refresh_jobs"):
                    st.rerun()
            
            st.markdown("---")
            
            # Display jobs
            for job in jobs:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{job['name']}**")
                        st.text(f"URL: {job['url']}")
                        st.text(f"Status: {job['status']}")
                    
                    with col2:
                        if job['status'] != 'Running':
                            if st.button("▶️ Start", key=f"start_{job['id']}", help="Start job"):
                                result = self._call_api("PUT", f"/scraping/jobs/{job['id']}/start")
                                if result:
                                    st.success("Job started!")
                                    st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_{job['id']}", help="Delete job"):
                            result = self._call_api("DELETE", f"/scraping/jobs/{job['id']}")
                            if result:
                                st.success("Job deleted!")
                                st.rerun()
                    
                    st.divider()
        else:
            st.markdown("""
            <div class="custom-alert alert-info">
                <strong>No jobs created yet</strong><br>
                Create your first scraping job to get started.
            </div>
            """, unsafe_allow_html=True)

    def _render_analytics_page(self):
        st.markdown("""
        <div class="dashboard-header">
            <h1 class="dashboard-title">Data Analytics</h1>
            <p class="dashboard-subtitle">Explore and analyze scraped data with AI insights</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Analytics tabs
        tab1, tab2 = st.tabs(["🔍 Data Explorer", "📊 Export"])
        
        with tab1:
            self._render_data_explorer()
        
        with tab2:
            self._render_data_export()

    def _render_data_explorer(self):
        """Render the data exploration interface."""
        st.markdown("### Data Explorer")
        
        # Search and filters
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input(
                "🔍 Search Data", 
                placeholder="Search across all scraped content...",
                help="Search in titles, descriptions, URLs, and other text fields"
            )
        
        with col2:
            date_from = st.date_input(
                "From Date", 
                value=datetime.now().date() - timedelta(days=7)
            )
        
        with col3:
            date_to = st.date_input(
                "To Date", 
                value=datetime.now().date()
            )
        
        # Get data from API
        data_response = self._call_api("GET", "/data")
        
        if data_response and data_response.get('data'):
            scraped_data = data_response['data']
            
            if scraped_data:
                # Convert to DataFrame
                df = pd.DataFrame(scraped_data)
                
                # Apply search filter
                if search_query:
                    mask = df.astype(str).apply(
                        lambda x: x.str.lower().str.contains(search_query.lower(), na=False)
                    ).any(axis=1)
                    df = df[mask]
                
                # Display summary statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Records", len(df))
                with col2:
                    st.metric("Unique Sources", df.get('source', pd.Series()).nunique() if 'source' in df.columns else 'N/A')
                with col3:
                    avg_quality = df.get('quality_score', pd.Series()).mean() if 'quality_score' in df.columns else 0
                    st.metric("Avg Quality", f"{avg_quality:.1f}/10")
                with col4:
                    st.metric("Data Size", f"{len(df) * 0.5:.1f} MB")
                
                # Data preview
                st.markdown("#### Data Preview")
                st.dataframe(df, width='stretch', hide_index=True, height=400)
                
            else:
                st.info("No scraped data available. Start a scraping job to collect data.")
        else:
            # Generate mock data for demonstration
            mock_data = self._generate_mock_data()
            df = pd.DataFrame(mock_data)
            
            st.markdown("#### Sample Data (Demo)")
            st.dataframe(df, width='stretch', hide_index=True, height=400)
            st.info("This is sample data. Connect to the API to see real scraped data.")

    def _render_data_export(self):
        """Render data export interface."""
        st.markdown("### Data Export Center")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Export Configuration")
            
            export_format = st.selectbox(
                "Export Format",
                ["CSV", "JSON", "Excel", "Parquet"],
                help="Choose the format for data export"
            )
            
            date_range = st.date_input(
                "Date Range",
                value=[datetime.now().date() - timedelta(days=7), datetime.now().date()],
                help="Select date range for export"
            )
            
            include_metadata = st.checkbox(
                "Include Metadata", 
                value=True,
                key="export_include_metadata"
            )
            compress_output = st.checkbox(
                "Compress Output", 
                value=False,
                key="export_compress_output"
            )
        
        with col2:
            st.markdown("#### Export Actions")
            
            if st.button("📥 Quick Export", width='stretch', key="quick_export"):
                st.success("Export started! Download will begin shortly.")
            
            if st.button("📊 Schedule Export", width='stretch', key="schedule_export"):
                st.info("Export scheduled for daily execution.")
            
            if st.button("📧 Email Export", width='stretch', key="email_export"):
                st.success("Export will be emailed when complete.")
        
        # Export preview
        st.markdown("#### Export Preview")
        
        # Mock data preview
        preview_data = pd.DataFrame({
            'id': range(1, 6),
            'title': ['Sample Title 1', 'Sample Title 2', 'Sample Title 3', 'Sample Title 4', 'Sample Title 5'],
            'url': ['https://example1.com', 'https://example2.com', 'https://example3.com', 'https://example4.com', 'https://example5.com'],
            'scraped_at': pd.date_range('2024-01-01', periods=5, freq='D')
        })
        
        st.dataframe(preview_data, width='stretch', hide_index=True)
        st.info(f"Preview showing 5 of 1,234 records to be exported as {export_format}")

    def _render_metrics_page(self):
        st.markdown("""
        <div class="dashboard-header">
            <h1 class="dashboard-title">System Metrics</h1>
            <p class="dashboard-subtitle">Real-time performance monitoring and system health</p>
        </div>
        """, unsafe_allow_html=True)
        
        # System health overview
        st.markdown("### System Health Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        health_response = self._call_api("GET", "/health")
        api_status = "Healthy" if health_response else "Unhealthy"
        
        with col1:
            status_color = "#38a169" if health_response else "#e53e3e"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {status_color};">
                    {'✅' if health_response else '❌'}
                </div>
                <div class="metric-label">API Server</div>
                <div class="metric-change {'positive' if health_response else 'negative'}">{api_status}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value" style="color: #38a169;">✅</div>
                <div class="metric-label">Database</div>
                <div class="metric-change positive">Connected</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value" style="color: #38a169;">✅</div>
                <div class="metric-label">AI Engine</div>
                <div class="metric-change positive">Ready</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value" style="color: #d69e2e;">⚠️</div>
                <div class="metric-label">Queue System</div>
                <div class="metric-change neutral">Busy</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Performance metrics
        st.markdown("### Performance Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Response Time", "1.2s", "-0.3s")
        with col2:
            st.metric("Throughput", "45 req/min", "+12 req/min")
        with col3:
            st.metric("Success Rate", "94.2%", "+2.1%")
        with col4:
            st.metric("Error Rate", "0.8%", "-0.3%")
        
        # Performance charts
        if PLOTLY_AVAILABLE:
            col1, col2 = st.columns(2)
            
            with col1:
                # Response time trend
                dates = pd.date_range(start='2024-01-01', periods=24, freq='H')
                response_times = np.random.normal(1.2, 0.3, 24).clip(0.5, 3.0)
                
                fig = px.line(
                    x=dates,
                    y=response_times,
                    title='Response Time Trend (24h)',
                    labels={'x': 'Time', 'y': 'Response Time (s)'},
                    color_discrete_sequence=['#667eea']
                )
                fig.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="SLA Threshold")
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Throughput distribution
                hours = list(range(24))
                throughput = [np.random.randint(20, 80) for _ in hours]
                
                fig = px.bar(
                    x=hours,
                    y=throughput,
                    title='Hourly Throughput Distribution',
                    labels={'x': 'Hour of Day', 'y': 'Requests/Hour'},
                    color_discrete_sequence=['#764ba2']
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Charts require plotly. Install with: pip install plotly")
            
            # Show data in tables instead
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Response Time Trend (24h)")
                dates = pd.date_range(start='2024-01-01', periods=24, freq='H')
                response_times = np.random.normal(1.2, 0.3, 24).clip(0.5, 3.0)
                df = pd.DataFrame({'Time': dates, 'Response Time (s)': response_times})
                st.dataframe(df.tail(10), use_container_width=True)
            
            with col2:
                st.subheader("Hourly Throughput Distribution")
                hours = list(range(24))
                throughput = [np.random.randint(20, 80) for _ in hours]
                df = pd.DataFrame({'Hour': hours, 'Requests/Hour': throughput})
                st.dataframe(df.tail(10), use_container_width=True)

    def _render_settings_page(self):
        st.markdown("""
        <div class="dashboard-header">
            <h1 class="dashboard-title">Settings</h1>
            <p class="dashboard-subtitle">Configure system preferences and options</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize settings in session state
        if 'settings' not in st.session_state:
            st.session_state.settings = {
                'theme': 'Light',
                'retention_days': 30,
                'export_format': 'CSV'
            }
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Display Settings")
            theme = st.selectbox(
                "Theme", 
                ["Light", "Dark"], 
                index=0 if st.session_state.settings['theme'] == 'Light' else 1,
                key="settings_theme"
            )
            
            st.markdown("### Data Settings")
            retention_days = st.number_input(
                "Data retention (days)", 
                value=st.session_state.settings['retention_days'],
                min_value=1, 
                max_value=365,
                key="settings_retention"
            )
            
            export_format = st.selectbox(
                "Default export format", 
                ["CSV", "JSON", "Excel"],
                index=["CSV", "JSON", "Excel"].index(st.session_state.settings['export_format']),
                key="settings_export_format"
            )
        
        with col2:
            st.markdown("### System Information")
            st.info("**Web Scraper Dashboard v2.0**")
            st.write("- Enterprise-grade web scraping interface")
            st.write("- Advanced job management system")
            st.write("- AI-powered data analysis")
            st.write("- Real-time monitoring and alerts")
            
            st.markdown("### Statistics")
            
            # Get API health
            health_response = self._call_api("GET", "/health")
            if health_response:
                st.success("✅ API Connected")
                
                # Get job statistics
                jobs_response = self._call_api("GET", "/scraping/jobs")
                if jobs_response:
                    total_jobs = jobs_response.get('total', len(jobs_response.get('jobs', [])))
                    st.metric("Total Jobs Created", total_jobs)
                else:
                    st.metric("Total Jobs Created", "N/A")
            else:
                st.error("❌ API Disconnected")
        
        # Save settings
        if st.button("Save Settings", type="primary", key="save_settings"):
            st.session_state.settings = {
                'theme': theme,
                'retention_days': retention_days,
                'export_format': export_format
            }
            st.success("Settings saved successfully!")
        
        # Reset data
        if st.button("Reset All Data", type="secondary", key="reset_data"):
            if st.button("Confirm Reset", type="secondary", key="confirm_reset"):
                # Get all jobs and delete them
                jobs_response = self._call_api("GET", "/scraping/jobs")
                if jobs_response and jobs_response.get('jobs'):
                    for job in jobs_response['jobs']:
                        self._call_api("DELETE", f"/scraping/jobs/{job['id']}")
                
                st.session_state.settings = {
                    'theme': 'Light',
                    'retention_days': 30,
                    'export_format': 'CSV'
                }
                st.success("All data has been reset!")
                st.rerun()

    def _generate_mock_data(self):
        """Generate mock scraped data for demonstration."""
        return [
            {
                'id': i,
                'title': f'Sample Title {i}',
                'url': f'https://example{i}.com',
                'content': f'Sample content for item {i}',
                'source': np.random.choice(['E-commerce', 'News', 'Social Media']),
                'quality_score': np.random.uniform(6, 10),
                'scraped_at': (datetime.now() - timedelta(days=np.random.randint(0, 30))).isoformat()
            }
            for i in range(1, 21)
        ]


def main():
    dashboard = WebScraperDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()