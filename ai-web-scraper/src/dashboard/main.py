"""
Main Streamlit dashboard application for the Intelligent Web Scraper.

This module provides a comprehensive real-time monitoring and management interface
for web scraping operations with multi-page layout and interactive components.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.dashboard.components.job_management import JobManagementComponent
from src.dashboard.components.data_visualization import DataVisualizationComponent
from src.dashboard.components.system_metrics import SystemMetricsComponent
from src.dashboard.utils.data_loader import DashboardDataLoader
from src.dashboard.utils.session_manager import SessionManager
from src.models.pydantic_models import JobStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IntelligentScraperDashboard:
    """
    Main dashboard class that orchestrates all dashboard components.
    """
    
    def __init__(self):
        """Initialize the dashboard with required components."""
        self.data_loader = DashboardDataLoader()
        self.session_manager = SessionManager()
        self.job_management = JobManagementComponent(self.data_loader)
        self.data_visualization = DataVisualizationComponent(self.data_loader)
        self.system_metrics = SystemMetricsComponent(self.data_loader)
        
        # Configure page
        st.set_page_config(
            page_title="Intelligent Web Scraper Dashboard",
            page_icon="🕷️",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Initialize session state
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
        
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 5  # seconds
        
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = datetime.now()
        
        if 'selected_jobs' not in st.session_state:
            st.session_state.selected_jobs = []
        
        if 'dashboard_data' not in st.session_state:
            st.session_state.dashboard_data = {}
    
    def run(self):
        """Main dashboard entry point."""
        try:
            # Sidebar configuration
            self._render_sidebar()
            
            # Main content area
            self._render_main_content()
            
            # Auto-refresh logic
            self._handle_auto_refresh()
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}", exc_info=True)
            st.error(f"Dashboard error: {str(e)}")
    
    def _render_sidebar(self):
        """Render the sidebar with navigation and settings."""
        with st.sidebar:
            st.title("🕷️ Web Scraper")
            st.markdown("---")
            
            # Navigation
            page = st.selectbox(
                "Navigate to:",
                ["Overview", "Job Management", "Data Explorer", "System Metrics", "Settings"],
                key="navigation"
            )
            
            st.session_state.current_page = page
            
            st.markdown("---")
            
            # Auto-refresh settings
            st.subheader("⚙️ Settings")
            
            st.session_state.auto_refresh = st.checkbox(
                "Auto-refresh",
                value=st.session_state.auto_refresh,
                help="Automatically refresh dashboard data"
            )
            
            if st.session_state.auto_refresh:
                st.session_state.refresh_interval = st.slider(
                    "Refresh interval (seconds)",
                    min_value=1,
                    max_value=60,
                    value=st.session_state.refresh_interval,
                    step=1
                )
            
            # Manual refresh button
            if st.button("🔄 Refresh Now", use_container_width=True):
                self._refresh_data()
            
            # Last refresh time
            st.caption(f"Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
            
            st.markdown("---")
            
            # Quick stats
            self._render_quick_stats()
    
    def _render_quick_stats(self):
        """Render quick statistics in the sidebar."""
        st.subheader("📊 Quick Stats")
        
        try:
            # Get cached data or load fresh
            stats = self._get_cached_stats()
            
            if stats:
                st.metric("Active Jobs", stats.get('active_jobs', 0))
                st.metric("Total Data Records", stats.get('total_records', 0))
                st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
                st.metric("Avg Quality Score", f"{stats.get('avg_quality', 0):.2f}")
            else:
                st.info("Loading statistics...")
                
        except Exception as e:
            logger.error(f"Error loading quick stats: {e}")
            st.error("Failed to load statistics")
    
    def _render_main_content(self):
        """Render the main content area based on selected page."""
        page = st.session_state.get('current_page', 'Overview')
        
        if page == "Overview":
            self._render_overview_page()
        elif page == "Job Management":
            self._render_job_management_page()
        elif page == "Data Explorer":
            self._render_data_explorer_page()
        elif page == "System Metrics":
            self._render_system_metrics_page()
        elif page == "Settings":
            self._render_settings_page()
    
    def _render_overview_page(self):
        """Render the overview dashboard page."""
        st.title("📊 Dashboard Overview")
        
        # Key metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            overview_data = self._get_overview_data()
            
            with col1:
                st.metric(
                    "Running Jobs",
                    overview_data.get('running_jobs', 0),
                    delta=overview_data.get('running_jobs_delta', 0)
                )
            
            with col2:
                st.metric(
                    "Completed Today",
                    overview_data.get('completed_today', 0),
                    delta=overview_data.get('completed_today_delta', 0)
                )
            
            with col3:
                st.metric(
                    "Success Rate",
                    f"{overview_data.get('success_rate', 0):.1f}%",
                    delta=f"{overview_data.get('success_rate_delta', 0):.1f}%"
                )
            
            with col4:
                st.metric(
                    "Pages/Hour",
                    overview_data.get('pages_per_hour', 0),
                    delta=overview_data.get('pages_per_hour_delta', 0)
                )
            
            # Charts row
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Job Status Distribution")
                self._render_job_status_chart(overview_data.get('job_status_data', {}))
            
            with col2:
                st.subheader("⏱️ Performance Trends")
                self._render_performance_trend_chart(overview_data.get('performance_data', []))
            
            # Recent activity
            st.subheader("🕒 Recent Activity")
            self._render_recent_activity(overview_data.get('recent_jobs', []))
            
        except Exception as e:
            logger.error(f"Error rendering overview: {e}")
            st.error("Failed to load overview data")
    
    def _render_job_management_page(self):
        """Render the job management page."""
        st.title("⚙️ Job Management")
        self.job_management.render()
    
    def _render_data_explorer_page(self):
        """Render the data explorer page."""
        st.title("🔍 Data Explorer")
        self.data_visualization.render()
    
    def _render_system_metrics_page(self):
        """Render the system metrics page."""
        st.title("📊 System Metrics")
        self.system_metrics.render()
    
    def _render_settings_page(self):
        """Render the settings page."""
        st.title("⚙️ Settings")
        
        st.subheader("Dashboard Configuration")
        
        # Theme settings
        theme = st.selectbox(
            "Dashboard Theme",
            ["Light", "Dark", "Auto"],
            index=0
        )
        
        # Data retention settings
        st.subheader("Data Management")
        
        retention_days = st.number_input(
            "Data retention (days)",
            min_value=1,
            max_value=365,
            value=30,
            help="How long to keep scraped data"
        )
        
        # Export settings
        st.subheader("Export Configuration")
        
        default_format = st.selectbox(
            "Default export format",
            ["CSV", "JSON", "Excel"],
            index=0
        )
        
        max_export_records = st.number_input(
            "Maximum records per export",
            min_value=100,
            max_value=100000,
            value=10000,
            step=100
        )
        
        # Save settings
        if st.button("💾 Save Settings", use_container_width=True):
            # Here you would save settings to database or config file
            st.success("Settings saved successfully!")
    
    def _render_job_status_chart(self, status_data: Dict):
        """Render job status distribution pie chart."""
        if not status_data:
            st.info("No job data available")
            return
        
        fig = px.pie(
            values=list(status_data.values()),
            names=list(status_data.keys()),
            color_discrete_map={
                'completed': '#28a745',
                'running': '#007bff',
                'pending': '#ffc107',
                'failed': '#dc3545',
                'cancelled': '#6c757d'
            }
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_performance_trend_chart(self, performance_data: List[Dict]):
        """Render performance trend line chart."""
        if not performance_data:
            st.info("No performance data available")
            return
        
        df = pd.DataFrame(performance_data)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['pages_per_minute'],
            mode='lines+markers',
            name='Pages/Min',
            line=dict(color='#007bff', width=2)
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(t=0, b=0, l=0, r=0),
            xaxis_title="Time",
            yaxis_title="Pages per Minute"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_recent_activity(self, recent_jobs: List[Dict]):
        """Render recent job activity table."""
        if not recent_jobs:
            st.info("No recent activity")
            return
        
        df = pd.DataFrame(recent_jobs)
        
        # Format the dataframe for display
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%H:%M:%S')
            df = df[['id', 'url', 'status', 'pages_completed', 'created_at']]
            df.columns = ['Job ID', 'URL', 'Status', 'Pages', 'Time']
            
            # Add status styling
            def style_status(val):
                colors = {
                    'completed': 'background-color: #d4edda; color: #155724',
                    'running': 'background-color: #d1ecf1; color: #0c5460',
                    'pending': 'background-color: #fff3cd; color: #856404',
                    'failed': 'background-color: #f8d7da; color: #721c24',
                    'cancelled': 'background-color: #e2e3e5; color: #383d41'
                }
                return colors.get(val, '')
            
            styled_df = df.style.applymap(style_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent jobs found")
    
    def _get_overview_data(self) -> Dict:
        """Get overview data for the dashboard."""
        try:
            # This would typically call the data loader
            # For now, return mock data structure
            return {
                'running_jobs': 3,
                'running_jobs_delta': 1,
                'completed_today': 15,
                'completed_today_delta': 5,
                'success_rate': 94.2,
                'success_rate_delta': 2.1,
                'pages_per_hour': 1250,
                'pages_per_hour_delta': 150,
                'job_status_data': {
                    'completed': 45,
                    'running': 3,
                    'pending': 2,
                    'failed': 1
                },
                'performance_data': [
                    {'timestamp': datetime.now() - timedelta(hours=i), 'pages_per_minute': 20 + i * 2}
                    for i in range(24, 0, -1)
                ],
                'recent_jobs': []
            }
        except Exception as e:
            logger.error(f"Error getting overview data: {e}")
            return {}
    
    def _get_cached_stats(self) -> Dict:
        """Get cached statistics for quick display."""
        try:
            # Check if we have cached data that's still fresh
            cache_key = 'quick_stats'
            cache_timeout = 30  # seconds
            
            now = datetime.now()
            if (cache_key in st.session_state.dashboard_data and
                'timestamp' in st.session_state.dashboard_data[cache_key] and
                (now - st.session_state.dashboard_data[cache_key]['timestamp']).seconds < cache_timeout):
                return st.session_state.dashboard_data[cache_key]['data']
            
            # Load fresh data
            stats = {
                'active_jobs': 3,
                'total_records': 15420,
                'success_rate': 94.2,
                'avg_quality': 0.87
            }
            
            # Cache the data
            st.session_state.dashboard_data[cache_key] = {
                'data': stats,
                'timestamp': now
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cached stats: {e}")
            return {}
    
    def _refresh_data(self):
        """Refresh all dashboard data."""
        try:
            # Clear cached data
            st.session_state.dashboard_data = {}
            st.session_state.last_refresh = datetime.now()
            
            # Force rerun to refresh UI
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            st.error("Failed to refresh data")
    
    def _handle_auto_refresh(self):
        """Handle automatic dashboard refresh."""
        if st.session_state.auto_refresh:
            # Check if it's time to refresh
            now = datetime.now()
            time_since_refresh = (now - st.session_state.last_refresh).seconds
            
            if time_since_refresh >= st.session_state.refresh_interval:
                self._refresh_data()


def main():
    """Main entry point for the Streamlit dashboard."""
    try:
        dashboard = IntelligentScraperDashboard()
        dashboard.run()
    except Exception as e:
        logger.error(f"Dashboard startup error: {e}", exc_info=True)
        st.error(f"Failed to start dashboard: {str(e)}")


if __name__ == "__main__":
    main()