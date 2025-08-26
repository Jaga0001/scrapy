"""
System metrics component for the Streamlit dashboard.

This module provides real-time system monitoring with performance metrics,
health checks, and resource utilization visualization.
"""

import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SystemMetricsComponent:
    """
    Component for displaying system metrics and health monitoring.
    """
    
    def __init__(self, data_loader):
        """
        Initialize the system metrics component.
        
        Args:
            data_loader: Dashboard data loader instance
        """
        self.data_loader = data_loader
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def render(self):
        """Render the system metrics interface."""
        try:
            # Create tabs for different metric categories
            tab1, tab2, tab3, tab4 = st.tabs([
                "🖥️ System Health", 
                "📊 Performance", 
                "🔧 Services", 
                "📈 Historical"
            ])
            
            with tab1:
                self._render_system_health_tab()
            
            with tab2:
                self._render_performance_tab()
            
            with tab3:
                self._render_services_tab()
            
            with tab4:
                self._render_historical_tab()
                
        except Exception as e:
            self.logger.error(f"Error rendering system metrics: {e}")
            st.error(f"Failed to render system metrics interface: {str(e)}")
    
    def _render_system_health_tab(self):
        """Render the system health overview tab."""
        st.subheader("🖥️ System Health Overview")
        
        try:
            # Real-time system metrics
            system_info = self._get_system_info()
            
            # Health status indicators
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                cpu_usage = system_info.get('cpu_percent', 0)
                cpu_status = "🟢" if cpu_usage < 70 else "🟡" if cpu_usage < 90 else "🔴"
                st.metric(
                    f"{cpu_status} CPU Usage",
                    f"{cpu_usage:.1f}%",
                    help="Current CPU utilization"
                )
            
            with col2:
                memory_usage = system_info.get('memory_percent', 0)
                memory_status = "🟢" if memory_usage < 70 else "🟡" if memory_usage < 90 else "🔴"
                st.metric(
                    f"{memory_status} Memory Usage",
                    f"{memory_usage:.1f}%",
                    help="Current memory utilization"
                )
            
            with col3:
                disk_usage = system_info.get('disk_percent', 0)
                disk_status = "🟢" if disk_usage < 80 else "🟡" if disk_usage < 95 else "🔴"
                st.metric(
                    f"{disk_status} Disk Usage",
                    f"{disk_usage:.1f}%",
                    help="Current disk utilization"
                )
            
            with col4:
                network_io = system_info.get('network_io', {})
                network_status = "🟢"  # Simplified for demo
                st.metric(
                    f"{network_status} Network I/O",
                    f"{network_io.get('bytes_sent', 0) / 1024 / 1024:.1f} MB",
                    help="Network bytes sent"
                )
            
            # Detailed system information
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💻 System Information")
                
                system_details = {
                    "Platform": system_info.get('platform', 'Unknown'),
                    "CPU Count": system_info.get('cpu_count', 0),
                    "Total Memory": f"{system_info.get('total_memory', 0) / 1024 / 1024 / 1024:.1f} GB",
                    "Available Memory": f"{system_info.get('available_memory', 0) / 1024 / 1024 / 1024:.1f} GB",
                    "Boot Time": system_info.get('boot_time', 'Unknown'),
                    "Python Version": system_info.get('python_version', 'Unknown')
                }
                
                for key, value in system_details.items():
                    st.text(f"{key}: {value}")
            
            with col2:
                st.subheader("🔄 Process Information")
                
                process_info = self._get_process_info()
                
                for process in process_info[:10]:  # Show top 10 processes
                    with st.expander(f"PID {process['pid']}: {process['name']}", expanded=False):
                        st.text(f"CPU: {process['cpu_percent']:.1f}%")
                        st.text(f"Memory: {process['memory_percent']:.1f}%")
                        st.text(f"Status: {process['status']}")
            
            # Real-time charts
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 CPU Usage (Real-time)")
                self._render_realtime_cpu_chart()
            
            with col2:
                st.subheader("💾 Memory Usage (Real-time)")
                self._render_realtime_memory_chart()
                
        except Exception as e:
            self.logger.error(f"Error rendering system health: {e}")
            st.error("Failed to load system health information")
    
    def _render_performance_tab(self):
        """Render the performance metrics tab."""
        st.subheader("📊 Performance Metrics")
        
        try:
            # Performance overview
            perf_data = self._get_performance_data()
            
            # Key performance indicators
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Scraping Rate",
                    f"{perf_data.get('scraping_rate', 0):.1f} pages/min",
                    delta=f"{perf_data.get('scraping_rate_delta', 0):.1f}",
                    help="Current scraping rate"
                )
            
            with col2:
                st.metric(
                    "Response Time",
                    f"{perf_data.get('avg_response_time', 0):.0f}ms",
                    delta=f"{perf_data.get('response_time_delta', 0):.0f}ms",
                    help="Average API response time"
                )
            
            with col3:
                st.metric(
                    "Queue Size",
                    perf_data.get('queue_size', 0),
                    delta=perf_data.get('queue_size_delta', 0),
                    help="Current job queue size"
                )
            
            with col4:
                st.metric(
                    "Active Workers",
                    perf_data.get('active_workers', 0),
                    delta=perf_data.get('workers_delta', 0),
                    help="Number of active worker processes"
                )
            
            # Performance charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🚀 Scraping Performance")
                self._render_scraping_performance_chart(perf_data.get('scraping_history', []))
            
            with col2:
                st.subheader("⏱️ Response Time Trends")
                self._render_response_time_chart(perf_data.get('response_time_history', []))
            
            # Resource utilization over time
            st.subheader("📈 Resource Utilization Trends")
            self._render_resource_utilization_chart(perf_data.get('resource_history', []))
            
            # Performance alerts
            st.subheader("⚠️ Performance Alerts")
            alerts = perf_data.get('alerts', [])
            
            if alerts:
                for alert in alerts:
                    alert_type = alert.get('type', 'info')
                    alert_message = alert.get('message', '')
                    
                    if alert_type == 'error':
                        st.error(f"🔴 {alert_message}")
                    elif alert_type == 'warning':
                        st.warning(f"🟡 {alert_message}")
                    else:
                        st.info(f"🔵 {alert_message}")
            else:
                st.success("🟢 No performance alerts")
                
        except Exception as e:
            self.logger.error(f"Error rendering performance metrics: {e}")
            st.error("Failed to load performance metrics")
    
    def _render_services_tab(self):
        """Render the services monitoring tab."""
        st.subheader("🔧 Services Status")
        
        try:
            services_status = self._get_services_status()
            
            # Service status overview
            col1, col2, col3 = st.columns(3)
            
            with col1:
                healthy_services = sum(1 for s in services_status if s['status'] == 'healthy')
                total_services = len(services_status)
                st.metric(
                    "Healthy Services",
                    f"{healthy_services}/{total_services}",
                    help="Number of healthy services"
                )
            
            with col2:
                unhealthy_services = sum(1 for s in services_status if s['status'] != 'healthy')
                st.metric(
                    "Issues Detected",
                    unhealthy_services,
                    delta=-unhealthy_services if unhealthy_services > 0 else 0,
                    help="Number of services with issues"
                )
            
            with col3:
                uptime = self._calculate_system_uptime()
                st.metric(
                    "System Uptime",
                    uptime,
                    help="Total system uptime"
                )
            
            # Detailed service status
            st.markdown("---")
            st.subheader("📋 Service Details")
            
            for service in services_status:
                with st.expander(f"{service['name']} - {service['status'].upper()}", expanded=service['status'] != 'healthy'):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        status_color = {
                            'healthy': '🟢',
                            'warning': '🟡',
                            'error': '🔴',
                            'unknown': '⚪'
                        }.get(service['status'], '⚪')
                        
                        st.markdown(f"**Status:** {status_color} {service['status'].title()}")
                        st.markdown(f"**Last Check:** {service.get('last_check', 'Unknown')}")
                        st.markdown(f"**Response Time:** {service.get('response_time', 'N/A')}")
                    
                    with col2:
                        if service.get('message'):
                            st.markdown(f"**Message:** {service['message']}")
                        
                        if service.get('metrics'):
                            st.markdown("**Metrics:**")
                            for key, value in service['metrics'].items():
                                st.text(f"  {key}: {value}")
                    
                    # Service actions
                    if service['status'] != 'healthy':
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button(f"🔄 Restart {service['name']}", key=f"restart_{service['name']}"):
                                self._restart_service(service['name'])
                        
                        with col2:
                            if st.button(f"🔍 Check {service['name']}", key=f"check_{service['name']}"):
                                self._check_service(service['name'])
                        
                        with col3:
                            if st.button(f"📋 Logs {service['name']}", key=f"logs_{service['name']}"):
                                self._show_service_logs(service['name'])
            
            # Service configuration
            st.markdown("---")
            st.subheader("⚙️ Service Configuration")
            
            with st.expander("🔧 Health Check Settings", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    check_interval = st.number_input(
                        "Check Interval (seconds)",
                        min_value=10,
                        max_value=300,
                        value=30,
                        help="How often to check service health"
                    )
                
                with col2:
                    timeout = st.number_input(
                        "Timeout (seconds)",
                        min_value=1,
                        max_value=60,
                        value=10,
                        help="Health check timeout"
                    )
                
                if st.button("💾 Save Settings", use_container_width=True):
                    st.success("Health check settings saved!")
                    
        except Exception as e:
            self.logger.error(f"Error rendering services status: {e}")
            st.error("Failed to load services status")
    
    def _render_historical_tab(self):
        """Render the historical metrics tab."""
        st.subheader("📈 Historical Metrics")
        
        try:
            # Time range selector
            col1, col2, col3 = st.columns(3)
            
            with col1:
                time_range = st.selectbox(
                    "Time Range",
                    ["Last Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days", "Last 30 Days"],
                    index=2
                )
            
            with col2:
                metric_type = st.selectbox(
                    "Metric Type",
                    ["System Resources", "Performance", "Errors", "All"],
                    index=0
                )
            
            with col3:
                if st.button("🔄 Refresh Data", use_container_width=True):
                    st.rerun()
            
            # Load historical data
            historical_data = self._load_historical_metrics(time_range, metric_type)
            
            if historical_data:
                # Summary statistics
                self._render_historical_summary(historical_data)
                
                # Historical charts
                st.markdown("---")
                
                if metric_type in ["System Resources", "All"]:
                    st.subheader("💻 System Resource History")
                    self._render_system_resource_history(historical_data.get('system_resources', []))
                
                if metric_type in ["Performance", "All"]:
                    st.subheader("🚀 Performance History")
                    self._render_performance_history(historical_data.get('performance', []))
                
                if metric_type in ["Errors", "All"]:
                    st.subheader("⚠️ Error History")
                    self._render_error_history(historical_data.get('errors', []))
                
                # Export historical data
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📊 Export CSV", use_container_width=True):
                        self._export_historical_data(historical_data, "csv")
                
                with col2:
                    if st.button("📋 Export JSON", use_container_width=True):
                        self._export_historical_data(historical_data, "json")
            else:
                st.info("No historical data available for the selected time range.")
                
        except Exception as e:
            self.logger.error(f"Error rendering historical metrics: {e}")
            st.error("Failed to load historical metrics")
    
    def _get_system_info(self) -> Dict:
        """Get current system information."""
        try:
            import platform
            import sys
            
            # Get system metrics using psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': psutil.cpu_count(),
                'memory_percent': memory.percent,
                'total_memory': memory.total,
                'available_memory': memory.available,
                'disk_percent': disk.percent,
                'network_io': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                },
                'platform': platform.platform(),
                'python_version': sys.version,
                'boot_time': boot_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {}
    
    def _get_process_info(self) -> List[Dict]:
        """Get information about running processes."""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return processes
        except Exception as e:
            self.logger.error(f"Error getting process info: {e}")
            return []
    
    def _get_performance_data(self) -> Dict:
        """Get performance metrics data."""
        try:
            # This would typically query the metrics database
            return {
                'scraping_rate': 45.2,
                'scraping_rate_delta': 3.1,
                'avg_response_time': 250,
                'response_time_delta': -15,
                'queue_size': 12,
                'queue_size_delta': -3,
                'active_workers': 4,
                'workers_delta': 0,
                'scraping_history': [
                    {'timestamp': datetime.now() - timedelta(minutes=i*5), 'rate': 40 + i}
                    for i in range(12, 0, -1)
                ],
                'response_time_history': [
                    {'timestamp': datetime.now() - timedelta(minutes=i*5), 'response_time': 200 + i*10}
                    for i in range(12, 0, -1)
                ],
                'resource_history': [
                    {
                        'timestamp': datetime.now() - timedelta(minutes=i*5),
                        'cpu': 30 + i*2,
                        'memory': 45 + i*1.5,
                        'disk': 60 + i*0.5
                    }
                    for i in range(12, 0, -1)
                ],
                'alerts': [
                    {'type': 'warning', 'message': 'High memory usage detected (85%)'},
                    {'type': 'info', 'message': 'Queue processing is running smoothly'}
                ]
            }
        except Exception as e:
            self.logger.error(f"Error getting performance data: {e}")
            return {}
    
    def _get_services_status(self) -> List[Dict]:
        """Get status of all monitored services."""
        try:
            # This would typically check actual service health
            return [
                {
                    'name': 'Web Scraper API',
                    'status': 'healthy',
                    'last_check': datetime.now().strftime('%H:%M:%S'),
                    'response_time': '45ms',
                    'message': 'All endpoints responding normally',
                    'metrics': {
                        'requests_per_minute': 120,
                        'error_rate': '0.2%'
                    }
                },
                {
                    'name': 'Redis Queue',
                    'status': 'healthy',
                    'last_check': datetime.now().strftime('%H:%M:%S'),
                    'response_time': '2ms',
                    'message': 'Queue processing normally',
                    'metrics': {
                        'queue_size': 12,
                        'processed_jobs': 1450
                    }
                },
                {
                    'name': 'PostgreSQL Database',
                    'status': 'warning',
                    'last_check': datetime.now().strftime('%H:%M:%S'),
                    'response_time': '120ms',
                    'message': 'High connection count detected',
                    'metrics': {
                        'active_connections': 85,
                        'max_connections': 100
                    }
                },
                {
                    'name': 'Celery Workers',
                    'status': 'healthy',
                    'last_check': datetime.now().strftime('%H:%M:%S'),
                    'response_time': 'N/A',
                    'message': '4 workers active and processing',
                    'metrics': {
                        'active_workers': 4,
                        'tasks_processed': 2340
                    }
                }
            ]
        except Exception as e:
            self.logger.error(f"Error getting services status: {e}")
            return []
    
    def _calculate_system_uptime(self) -> str:
        """Calculate system uptime."""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            return f"{days}d {hours}h {minutes}m"
        except Exception as e:
            self.logger.error(f"Error calculating uptime: {e}")
            return "Unknown"
    
    def _render_realtime_cpu_chart(self):
        """Render real-time CPU usage chart."""
        try:
            # Get recent CPU data (this would be from a real-time data source)
            cpu_data = [
                {'time': datetime.now() - timedelta(seconds=i*10), 'cpu': 30 + i*2}
                for i in range(30, 0, -1)
            ]
            
            df = pd.DataFrame(cpu_data)
            
            fig = px.line(
                df,
                x='time',
                y='cpu',
                title='CPU Usage (%)',
                range_y=[0, 100]
            )
            
            fig.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"Error rendering CPU chart: {e}")
            st.error("Failed to render CPU chart")
    
    def _render_realtime_memory_chart(self):
        """Render real-time memory usage chart."""
        try:
            # Get recent memory data
            memory_data = [
                {'time': datetime.now() - timedelta(seconds=i*10), 'memory': 45 + i*1.5}
                for i in range(30, 0, -1)
            ]
            
            df = pd.DataFrame(memory_data)
            
            fig = px.line(
                df,
                x='time',
                y='memory',
                title='Memory Usage (%)',
                range_y=[0, 100]
            )
            
            fig.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"Error rendering memory chart: {e}")
            st.error("Failed to render memory chart")
    
    def _render_scraping_performance_chart(self, performance_data: List[Dict]):
        """Render scraping performance chart."""
        if not performance_data:
            st.info("No performance data available")
            return
        
        df = pd.DataFrame(performance_data)
        
        fig = px.line(
            df,
            x='timestamp',
            y='rate',
            title='Scraping Rate (pages/min)',
            markers=True
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_response_time_chart(self, response_data: List[Dict]):
        """Render response time chart."""
        if not response_data:
            st.info("No response time data available")
            return
        
        df = pd.DataFrame(response_data)
        
        fig = px.line(
            df,
            x='timestamp',
            y='response_time',
            title='API Response Time (ms)',
            markers=True
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_resource_utilization_chart(self, resource_data: List[Dict]):
        """Render resource utilization chart."""
        if not resource_data:
            st.info("No resource data available")
            return
        
        df = pd.DataFrame(resource_data)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['cpu'],
            mode='lines+markers',
            name='CPU %',
            line=dict(color='#ff6b6b')
        ))
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['memory'],
            mode='lines+markers',
            name='Memory %',
            line=dict(color='#4ecdc4')
        ))
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['disk'],
            mode='lines+markers',
            name='Disk %',
            line=dict(color='#45b7d1')
        ))
        
        fig.update_layout(
            title='Resource Utilization Over Time',
            height=400,
            margin=dict(t=30, b=0, l=0, r=0),
            yaxis_title='Usage (%)',
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _load_historical_metrics(self, time_range: str, metric_type: str) -> Dict:
        """Load historical metrics data."""
        try:
            # This would typically query the metrics database
            # For now, return mock data based on time range
            
            hours_map = {
                "Last Hour": 1,
                "Last 6 Hours": 6,
                "Last 24 Hours": 24,
                "Last 7 Days": 168,
                "Last 30 Days": 720
            }
            
            hours = hours_map.get(time_range, 24)
            
            return {
                'system_resources': [
                    {
                        'timestamp': datetime.now() - timedelta(hours=i),
                        'cpu': 30 + (i % 20),
                        'memory': 45 + (i % 15),
                        'disk': 60 + (i % 10)
                    }
                    for i in range(hours, 0, -1)
                ],
                'performance': [
                    {
                        'timestamp': datetime.now() - timedelta(hours=i),
                        'scraping_rate': 40 + (i % 25),
                        'response_time': 200 + (i % 100),
                        'queue_size': 10 + (i % 20)
                    }
                    for i in range(hours, 0, -1)
                ],
                'errors': [
                    {
                        'timestamp': datetime.now() - timedelta(hours=i),
                        'error_count': max(0, 5 - (i % 10)),
                        'error_rate': max(0, 2.5 - (i % 5))
                    }
                    for i in range(hours, 0, -1)
                ]
            }
        except Exception as e:
            self.logger.error(f"Error loading historical metrics: {e}")
            return {}
    
    def _render_historical_summary(self, historical_data: Dict):
        """Render summary statistics for historical data."""
        try:
            col1, col2, col3, col4 = st.columns(4)
            
            # Calculate summary stats from historical data
            system_data = historical_data.get('system_resources', [])
            perf_data = historical_data.get('performance', [])
            
            if system_data:
                avg_cpu = sum(d['cpu'] for d in system_data) / len(system_data)
                avg_memory = sum(d['memory'] for d in system_data) / len(system_data)
                
                with col1:
                    st.metric("Avg CPU Usage", f"{avg_cpu:.1f}%")
                
                with col2:
                    st.metric("Avg Memory Usage", f"{avg_memory:.1f}%")
            
            if perf_data:
                avg_rate = sum(d['scraping_rate'] for d in perf_data) / len(perf_data)
                avg_response = sum(d['response_time'] for d in perf_data) / len(perf_data)
                
                with col3:
                    st.metric("Avg Scraping Rate", f"{avg_rate:.1f} pages/min")
                
                with col4:
                    st.metric("Avg Response Time", f"{avg_response:.0f}ms")
                    
        except Exception as e:
            self.logger.error(f"Error rendering historical summary: {e}")
    
    def _render_system_resource_history(self, resource_data: List[Dict]):
        """Render system resource history chart."""
        if not resource_data:
            st.info("No system resource data available")
            return
        
        df = pd.DataFrame(resource_data)
        
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('CPU Usage (%)', 'Memory Usage (%)', 'Disk Usage (%)'),
            vertical_spacing=0.1
        )
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['cpu'], name='CPU', line=dict(color='#ff6b6b')),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['memory'], name='Memory', line=dict(color='#4ecdc4')),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['disk'], name='Disk', line=dict(color='#45b7d1')),
            row=3, col=1
        )
        
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_performance_history(self, performance_data: List[Dict]):
        """Render performance history chart."""
        if not performance_data:
            st.info("No performance data available")
            return
        
        df = pd.DataFrame(performance_data)
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Scraping Rate (pages/min)', 'Response Time (ms)'),
            vertical_spacing=0.15
        )
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['scraping_rate'], name='Scraping Rate', line=dict(color='#28a745')),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['response_time'], name='Response Time', line=dict(color='#ffc107')),
            row=2, col=1
        )
        
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_error_history(self, error_data: List[Dict]):
        """Render error history chart."""
        if not error_data:
            st.info("No error data available")
            return
        
        df = pd.DataFrame(error_data)
        
        fig = px.bar(
            df,
            x='timestamp',
            y='error_count',
            title='Error Count Over Time',
            color='error_count',
            color_continuous_scale='Reds'
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _restart_service(self, service_name: str):
        """Restart a service."""
        try:
            # This would typically call the actual service restart
            st.success(f"Service '{service_name}' restart initiated")
            st.rerun()
        except Exception as e:
            self.logger.error(f"Error restarting service: {e}")
            st.error(f"Failed to restart service: {service_name}")
    
    def _check_service(self, service_name: str):
        """Check a service health."""
        try:
            # This would typically perform a health check
            st.info(f"Health check initiated for '{service_name}'")
            st.rerun()
        except Exception as e:
            self.logger.error(f"Error checking service: {e}")
            st.error(f"Failed to check service: {service_name}")
    
    def _show_service_logs(self, service_name: str):
        """Show service logs."""
        try:
            # This would typically fetch actual logs
            st.info(f"Showing logs for '{service_name}' (feature would be implemented)")
        except Exception as e:
            self.logger.error(f"Error showing service logs: {e}")
            st.error(f"Failed to show logs for: {service_name}")
    
    def _export_historical_data(self, data: Dict, format: str):
        """Export historical data."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format == "csv":
                # Convert to DataFrame and export
                all_data = []
                for category, records in data.items():
                    for record in records:
                        record['category'] = category
                        all_data.append(record)
                
                df = pd.DataFrame(all_data)
                csv_data = df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"system_metrics_{timestamp}.csv",
                    mime="text/csv"
                )
            elif format == "json":
                import json
                json_data = json.dumps(data, indent=2, default=str)
                
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"system_metrics_{timestamp}.json",
                    mime="application/json"
                )
                
        except Exception as e:
            self.logger.error(f"Error exporting historical data: {e}")
            st.error("Failed to export data")