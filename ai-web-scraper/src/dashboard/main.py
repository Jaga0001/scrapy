"""
Simple Streamlit dashboard for web scraper.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import streamlit as st
import requests
import json


class WebScraperDashboard:
    def __init__(self):
        st.set_page_config(
            page_title="Web Scraper Dashboard",
            page_icon="🕷️",
            layout="wide"
        )
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'Overview'
        
        # API base URL from environment
        self.api_base = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    def _call_api(self, method, endpoint, data=None):
        """Helper method to call API endpoints"""
        try:
            url = f"{self.api_base}{endpoint}"
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data)
            elif method == "PUT":
                response = requests.put(url)
            elif method == "DELETE":
                response = requests.delete(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error: {response.status_code}")
                return None
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API. Make sure the API server is running on http://localhost:8000")
            return None
        except Exception as e:
            st.error(f"Error calling API: {str(e)}")
            return None
    
    def run(self):
        self._render_sidebar()
        self._render_main_content()
    
    def _render_sidebar(self):
        with st.sidebar:
            st.title("🕷️ Web Scraper")
            st.markdown("---")
            
            # Use radio buttons for better navigation
            page = st.radio(
                "Navigate to:",
                ["Overview", "Job Management", "Data Explorer", "Settings"],
                index=["Overview", "Job Management", "Data Explorer", "Settings"].index(st.session_state.current_page)
            )
            
            if page != st.session_state.current_page:
                st.session_state.current_page = page
                st.rerun()
    
    def _render_main_content(self):
        page = st.session_state.get('current_page', 'Overview')
        
        if page == "Overview":
            self._render_overview_page()
        elif page == "Job Management":
            self._render_job_management_page()
        elif page == "Data Explorer":
            self._render_data_explorer_page()
        elif page == "Settings":
            self._render_settings_page()
    
    def _render_overview_page(self):
        st.title("📊 Web Scraper Dashboard")
        
        st.success("🟢 System Online")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Get metrics from API
        jobs_response = self._call_api("GET", "/scraping/jobs")
        
        if jobs_response:
            jobs = jobs_response.get('jobs', [])
            total_jobs = len(jobs)
            running_jobs = len([job for job in jobs if job['status'] == 'Running'])
            completed_jobs = len([job for job in jobs if job['status'] == 'Completed'])
            
            with col1:
                st.metric("Active Jobs", running_jobs)
            with col2:
                st.metric("Total Jobs", total_jobs)
            with col3:
                success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")
            with col4:
                st.metric("Pages Processed", running_jobs * 10)  # Estimate
        else:
            with col1:
                st.metric("Active Jobs", "N/A")
            with col2:
                st.metric("Total Jobs", "N/A")
            with col3:
                st.metric("Success Rate", "N/A")
            with col4:
                st.metric("Pages Processed", "N/A")
        
        st.markdown("---")
        st.subheader("Quick Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Create New Job", use_container_width=True):
                st.session_state.current_page = "Job Management"
                st.rerun()
        
        with col2:
            if st.button("📊 View Data", use_container_width=True):
                st.session_state.current_page = "Data Explorer"
                st.rerun()
        
        st.info("Welcome! Create your first scraping job to get started.")
    
    def _render_job_management_page(self):
        st.title("⚙️ Job Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Create New Job")
            
            with st.form("job_form"):
                url = st.text_input("Website URL", placeholder="https://example.com")
                job_name = st.text_input("Job Name", placeholder="My Scraping Job")
                max_pages = st.number_input("Max Pages", min_value=1, value=10)
                
                if st.form_submit_button("Create Job"):
                    if url and job_name:
                        # Call API to create job
                        job_data = {
                            "name": job_name,
                            "url": url,
                            "max_pages": max_pages
                        }
                        
                        result = self._call_api("POST", "/scraping/jobs", job_data)
                        if result:
                            st.success(f"Job '{job_name}' created successfully!")
                            st.rerun()
                    else:
                        st.error("Please fill all fields")
        
        with col2:
            st.subheader("Active Jobs")
            
            # Get jobs from API
            jobs_response = self._call_api("GET", "/scraping/jobs")
            
            if jobs_response and jobs_response.get('jobs'):
                jobs = jobs_response['jobs']
                
                for job in jobs:
                    with st.container():
                        col_a, col_b, col_c = st.columns([3, 1, 1])
                        with col_a:
                            st.write(f"**{job['name']}**")
                            st.write(f"URL: {job['url']}")
                            st.write(f"Status: {job['status']}")
                        with col_b:
                            if job['status'] != 'Running':
                                if st.button("▶️", key=f"start_{job['id']}", help="Start job"):
                                    result = self._call_api("PUT", f"/scraping/jobs/{job['id']}/start")
                                    if result:
                                        st.success("Job started!")
                                        st.rerun()
                        with col_c:
                            if st.button("🗑️", key=f"delete_{job['id']}", help="Delete job"):
                                result = self._call_api("DELETE", f"/scraping/jobs/{job['id']}")
                                if result:
                                    st.success("Job deleted!")
                                    st.rerun()
                        st.divider()
            else:
                st.info("No jobs created yet")
    
    def _render_data_explorer_page(self):
        st.title("🔍 Data Explorer")
        
        search_query = st.text_input("Search", placeholder="Search scraped data...")
        
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("From Date", value=datetime.now().date() - timedelta(days=7))
        with col2:
            date_to = st.date_input("To Date", value=datetime.now().date())
        
        # Get data from API
        data_response = self._call_api("GET", "/data")
        
        if data_response and data_response.get('data'):
            scraped_data = data_response['data']
            
            if scraped_data:
                st.subheader("Scraped Data")
                
                # Convert to DataFrame
                df = pd.DataFrame(scraped_data)
                
                # Apply search filter
                if search_query:
                    df = df[df.apply(lambda row: search_query.lower() in row.astype(str).str.lower().to_string(), axis=1)]
                
                # Apply date filter
                if 'scraped_at' in df.columns:
                    df['scraped_date'] = pd.to_datetime(df['scraped_at']).dt.date
                    df = df[(df['scraped_date'] >= date_from) & (df['scraped_date'] <= date_to)]
                
                st.dataframe(df, use_container_width=True)
                
                # Export buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📄 Export CSV"):
                        csv = df.to_csv(index=False)
                        st.download_button("Download CSV", csv, "scraped_data.csv", "text/csv")
                with col2:
                    if st.button("📋 Export JSON"):
                        json_data = df.to_json(orient='records')
                        st.download_button("Download JSON", json_data, "scraped_data.json", "application/json")
                with col3:
                    st.button("📊 Export Excel", disabled=True, help="Excel export coming soon")
            else:
                st.info("No scraped data available. Start a scraping job to collect data.")
        else:
            st.info("No data available yet. Create and run scraping jobs to see results here.")
    
    def _render_system_metrics_page(self):
        """Render the system metrics page."""
        st.title("📊 System Metrics")
        
        # System status overview
        st.subheader("System Health")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # This would get actual system metrics
            st.metric("API Status", "Online", help="Current API server status")
        
        with col2:
            st.metric("Database", "Connected", help="Database connection status")
        
        with col3:
            st.metric("Queue Status", "Ready", help="Job queue system status")
        
        with col4:
            st.metric("AI Service", "Available", help="AI processing service status")
        
        # Performance monitoring
        st.markdown("---")
        st.subheader("Performance Monitoring")
        
        # Resource usage section
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Resource Usage")
            st.info("System resource monitoring will be displayed here when jobs are running")
            
            # Placeholder for actual metrics
            st.text("CPU Usage: Monitoring...")
            st.text("Memory Usage: Monitoring...")
            st.text("Disk I/O: Monitoring...")
            st.text("Network I/O: Monitoring...")
        
        with col2:
            st.subheader("Service Health")
            
            # Service status checks
            services = [
                ("Web Scraper Engine", "Ready"),
                ("AI Content Processor", "Ready"),
                ("Data Pipeline", "Ready"),
                ("Export Manager", "Ready")
            ]
            
            for service, status in services:
                if status == "Ready":
                    st.success(f"✅ {service}: {status}")
                else:
                    st.error(f"❌ {service}: {status}")
        
        # Logs section
        st.markdown("---")
        st.subheader("System Logs")
        
        log_level = st.selectbox("Log Level", ["INFO", "WARNING", "ERROR", "DEBUG"])
        
        if st.button("Refresh Logs"):
            st.info("Log refresh functionality will be implemented here")
        
        # This would show actual system logs
        st.text_area(
            "Recent Logs",
            value="System initialized successfully\nWaiting for scraping jobs...",
            height=200,
            disabled=True
        )
    
    def _render_settings_page(self):
        st.title("⚙️ Settings")
        
        # Initialize settings in session state
        if 'settings' not in st.session_state:
            st.session_state.settings = {
                'theme': 'Light',
                'retention_days': 30,
                'export_format': 'CSV'
            }
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Display Settings")
            theme = st.selectbox("Theme", ["Light", "Dark"], 
                                index=0 if st.session_state.settings['theme'] == 'Light' else 1)
            
            st.subheader("Data Settings")
            retention_days = st.number_input("Data retention (days)", 
                                           value=st.session_state.settings['retention_days'],
                                           min_value=1, max_value=365)
            
            export_format = st.selectbox("Default export format", 
                                       ["CSV", "JSON", "Excel"],
                                       index=["CSV", "JSON", "Excel"].index(st.session_state.settings['export_format']))
        
        with col2:
            st.subheader("System Information")
            st.info("**Web Scraper Dashboard v1.0**")
            st.write("- Simple web scraping interface")
            st.write("- Job management system")
            st.write("- Data export capabilities")
            st.write("- Real-time monitoring")
            
            st.subheader("Statistics")
            
            # Get API health
            health_response = self._call_api("GET", "/health")
            if health_response:
                st.success("✅ API Connected")
                
                # Get job statistics
                jobs_response = self._call_api("GET", "/scraping/jobs")
                if jobs_response:
                    total_jobs = jobs_response.get('total', 0)
                    st.metric("Total Jobs Created", total_jobs)
                else:
                    st.metric("Total Jobs Created", "N/A")
            else:
                st.error("❌ API Disconnected")
            
        if st.button("Save Settings", type="primary"):
            st.session_state.settings = {
                'theme': theme,
                'retention_days': retention_days,
                'export_format': export_format
            }
            st.success("Settings saved successfully!")
            
        if st.button("Reset All Data", type="secondary"):
            st.warning("This will delete all jobs from the API server!")
            if st.button("Confirm Reset", type="secondary"):
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
    
def main():
    dashboard = WebScraperDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()