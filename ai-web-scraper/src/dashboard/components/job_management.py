"""
Job management component for the Streamlit dashboard.

This module provides the interface for creating, monitoring, and managing
scraping jobs through the dashboard.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from streamlit_ace import st_ace

from src.models.pydantic_models import JobStatus, ScrapingConfig, ScrapingJob
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JobManagementComponent:
    """
    Component for managing scraping jobs in the dashboard.
    """
    
    def __init__(self, data_loader):
        """
        Initialize the job management component.
        
        Args:
            data_loader: Dashboard data loader instance
        """
        self.data_loader = data_loader
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def render(self):
        """Render the job management interface."""
        try:
            # Create tabs for different job management functions
            tab1, tab2, tab3, tab4 = st.tabs([
                "🚀 Create Job", 
                "📋 Active Jobs", 
                "📊 Job History", 
                "⚙️ Job Templates"
            ])
            
            with tab1:
                self._render_create_job_tab()
            
            with tab2:
                self._render_active_jobs_tab()
            
            with tab3:
                self._render_job_history_tab()
            
            with tab4:
                self._render_job_templates_tab()
                
        except Exception as e:
            self.logger.error(f"Error rendering job management: {e}")
            st.error(f"Failed to render job management interface: {str(e)}")
    
    def _render_create_job_tab(self):
        """Render the create job tab."""
        st.subheader("🚀 Create New Scraping Job")
        
        with st.form("create_job_form"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Basic job configuration
                st.markdown("**Basic Configuration**")
                
                url = st.text_input(
                    "Target URL *",
                    placeholder="https://example.com",
                    help="The URL to scrape"
                )
                
                job_name = st.text_input(
                    "Job Name",
                    placeholder="My Scraping Job",
                    help="Optional name for the job"
                )
                
                priority = st.slider(
                    "Priority",
                    min_value=1,
                    max_value=10,
                    value=5,
                    help="Job priority (1=highest, 10=lowest)"
                )
                
                tags = st.text_input(
                    "Tags",
                    placeholder="ecommerce, products, daily",
                    help="Comma-separated tags for organization"
                )
            
            with col2:
                # Quick presets
                st.markdown("**Quick Presets**")
                
                preset = st.selectbox(
                    "Configuration Preset",
                    ["Custom", "E-commerce", "News Site", "Social Media", "API Endpoint"],
                    help="Pre-configured settings for common use cases"
                )
                
                if preset != "Custom":
                    st.info(f"Using {preset} preset configuration")
            
            # Advanced configuration
            with st.expander("🔧 Advanced Configuration", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Browser Settings**")
                    
                    headless = st.checkbox("Headless Mode", value=True)
                    use_stealth = st.checkbox("Stealth Mode", value=True)
                    javascript_enabled = st.checkbox("Enable JavaScript", value=True)
                    load_images = st.checkbox("Load Images", value=False)
                    
                    wait_time = st.number_input(
                        "Page Load Wait (seconds)",
                        min_value=1,
                        max_value=60,
                        value=5
                    )
                    
                    timeout = st.number_input(
                        "Request Timeout (seconds)",
                        min_value=5,
                        max_value=300,
                        value=30
                    )
                
                with col2:
                    st.markdown("**Extraction Settings**")
                    
                    extract_images = st.checkbox("Extract Images", value=False)
                    extract_links = st.checkbox("Extract Links", value=False)
                    follow_links = st.checkbox("Follow Links", value=False)
                    
                    if follow_links:
                        max_depth = st.number_input(
                            "Maximum Depth",
                            min_value=1,
                            max_value=5,
                            value=1
                        )
                    else:
                        max_depth = 1
                    
                    max_retries = st.number_input(
                        "Max Retries",
                        min_value=0,
                        max_value=10,
                        value=3
                    )
                    
                    delay_between_requests = st.number_input(
                        "Delay Between Requests (seconds)",
                        min_value=0.1,
                        max_value=10.0,
                        value=1.0,
                        step=0.1
                    )
            
            # Custom selectors
            with st.expander("🎯 Custom CSS Selectors", expanded=False):
                st.markdown("Define custom CSS selectors for specific data extraction:")
                
                selector_config = st_ace(
                    value='{\n  "title": "h1, .title",\n  "content": ".content, .article-body",\n  "price": ".price, .cost"\n}',
                    language='json',
                    theme='monokai',
                    height=150,
                    key="custom_selectors"
                )
            
            # Submit button
            submitted = st.form_submit_button(
                "🚀 Create Job",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                self._handle_job_creation(
                    url=url,
                    job_name=job_name,
                    priority=priority,
                    tags=tags.split(',') if tags else [],
                    preset=preset,
                    headless=headless,
                    use_stealth=use_stealth,
                    javascript_enabled=javascript_enabled,
                    load_images=load_images,
                    wait_time=wait_time,
                    timeout=timeout,
                    extract_images=extract_images,
                    extract_links=extract_links,
                    follow_links=follow_links,
                    max_depth=max_depth,
                    max_retries=max_retries,
                    delay_between_requests=delay_between_requests,
                    selector_config=selector_config
                )
    
    def _render_active_jobs_tab(self):
        """Render the active jobs monitoring tab."""
        st.subheader("📋 Active Jobs")
        
        # Filter controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                ["running", "pending", "completed", "failed", "cancelled"],
                default=["running", "pending"]
            )
        
        with col2:
            priority_filter = st.slider(
                "Max Priority",
                min_value=1,
                max_value=10,
                value=10
            )
        
        with col3:
            user_filter = st.text_input("Filter by User", placeholder="user_id")
        
        with col4:
            if st.button("🔄 Refresh Jobs"):
                st.rerun()
        
        # Load and display active jobs
        try:
            jobs = self._load_active_jobs(status_filter, priority_filter, user_filter)
            
            if jobs:
                # Display jobs in an interactive table
                self._render_jobs_table(jobs, show_actions=True)
                
                # Bulk actions
                st.markdown("---")
                st.subheader("Bulk Actions")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("⏸️ Pause Selected", use_container_width=True):
                        self._handle_bulk_action("pause")
                
                with col2:
                    if st.button("▶️ Resume Selected", use_container_width=True):
                        self._handle_bulk_action("resume")
                
                with col3:
                    if st.button("🛑 Cancel Selected", use_container_width=True):
                        self._handle_bulk_action("cancel")
            else:
                st.info("No active jobs found matching the current filters.")
                
        except Exception as e:
            self.logger.error(f"Error loading active jobs: {e}")
            st.error("Failed to load active jobs")
    
    def _render_job_history_tab(self):
        """Render the job history tab."""
        st.subheader("📊 Job History")
        
        # Date range selector
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=7)
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now()
            )
        
        # Load historical jobs
        try:
            historical_jobs = self._load_historical_jobs(start_date, end_date)
            
            if historical_jobs:
                # Summary metrics
                self._render_history_metrics(historical_jobs)
                
                # Jobs table
                st.markdown("---")
                self._render_jobs_table(historical_jobs, show_actions=False)
                
                # Export options
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📊 Export to CSV", use_container_width=True):
                        self._export_jobs_data(historical_jobs, "csv")
                
                with col2:
                    if st.button("📋 Export to JSON", use_container_width=True):
                        self._export_jobs_data(historical_jobs, "json")
            else:
                st.info("No jobs found for the selected date range.")
                
        except Exception as e:
            self.logger.error(f"Error loading job history: {e}")
            st.error("Failed to load job history")
    
    def _render_job_templates_tab(self):
        """Render the job templates tab."""
        st.subheader("⚙️ Job Templates")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**Saved Templates**")
            
            # Load saved templates
            templates = self._load_job_templates()
            
            if templates:
                selected_template = st.selectbox(
                    "Select Template",
                    options=list(templates.keys()),
                    key="template_selector"
                )
                
                if selected_template:
                    template_data = templates[selected_template]
                    
                    st.json(template_data)
                    
                    col1_1, col1_2 = st.columns(2)
                    
                    with col1_1:
                        if st.button("📝 Edit", use_container_width=True):
                            st.session_state.editing_template = selected_template
                    
                    with col1_2:
                        if st.button("🗑️ Delete", use_container_width=True):
                            self._delete_template(selected_template)
                            st.rerun()
            else:
                st.info("No saved templates found.")
        
        with col2:
            st.markdown("**Create/Edit Template**")
            
            with st.form("template_form"):
                template_name = st.text_input(
                    "Template Name",
                    value=st.session_state.get('editing_template', '')
                )
                
                template_description = st.text_area(
                    "Description",
                    placeholder="Describe what this template is for..."
                )
                
                # Template configuration
                template_config = st_ace(
                    value=self._get_template_default_config(),
                    language='json',
                    theme='monokai',
                    height=300,
                    key="template_config"
                )
                
                col2_1, col2_2 = st.columns(2)
                
                with col2_1:
                    if st.form_submit_button("💾 Save Template", use_container_width=True):
                        self._save_template(template_name, template_description, template_config)
                
                with col2_2:
                    if st.form_submit_button("🚀 Use Template", use_container_width=True):
                        self._use_template(template_config)
    
    def _render_jobs_table(self, jobs: List[Dict], show_actions: bool = True):
        """Render a table of jobs with optional action buttons."""
        if not jobs:
            return
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(jobs)
        
        # Format columns
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        if 'url' in df.columns:
            df['url'] = df['url'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
        
        # Select columns to display
        display_columns = ['id', 'url', 'status', 'pages_completed', 'pages_failed', 'created_at']
        display_df = df[display_columns].copy()
        display_df.columns = ['Job ID', 'URL', 'Status', 'Completed', 'Failed', 'Created']
        
        if show_actions:
            # Add selection checkboxes
            selected_jobs = []
            for idx, row in display_df.iterrows():
                col1, col2 = st.columns([0.1, 0.9])
                
                with col1:
                    if st.checkbox("", key=f"job_select_{row['Job ID']}"):
                        selected_jobs.append(row['Job ID'])
                
                with col2:
                    # Display job row with action buttons
                    cols = st.columns([2, 1, 1, 1, 1, 1, 1])
                    
                    with cols[0]:
                        st.text(row['URL'])
                    with cols[1]:
                        st.text(row['Status'])
                    with cols[2]:
                        st.text(str(row['Completed']))
                    with cols[3]:
                        st.text(str(row['Failed']))
                    with cols[4]:
                        st.text(row['Created'])
                    with cols[5]:
                        if st.button("👁️", key=f"view_{row['Job ID']}", help="View Details"):
                            self._show_job_details(row['Job ID'])
                    with cols[6]:
                        if row['Status'] in ['running', 'pending']:
                            if st.button("🛑", key=f"stop_{row['Job ID']}", help="Stop Job"):
                                self._stop_job(row['Job ID'])
            
            # Store selected jobs in session state
            st.session_state.selected_jobs = selected_jobs
        else:
            # Simple table display for history
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    def _render_history_metrics(self, jobs: List[Dict]):
        """Render summary metrics for historical jobs."""
        if not jobs:
            return
        
        df = pd.DataFrame(jobs)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_jobs = len(df)
            st.metric("Total Jobs", total_jobs)
        
        with col2:
            completed_jobs = len(df[df['status'] == 'completed'])
            success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        with col3:
            total_pages = df['pages_completed'].sum()
            st.metric("Total Pages", total_pages)
        
        with col4:
            avg_pages = df['pages_completed'].mean()
            st.metric("Avg Pages/Job", f"{avg_pages:.1f}")
    
    def _handle_job_creation(self, **kwargs):
        """Handle job creation form submission."""
        try:
            # Validate required fields
            if not kwargs.get('url'):
                st.error("URL is required")
                return
            
            # Parse custom selectors
            custom_selectors = {}
            if kwargs.get('selector_config'):
                try:
                    custom_selectors = json.loads(kwargs['selector_config'])
                except json.JSONDecodeError:
                    st.warning("Invalid JSON in custom selectors, using empty selectors")
            
            # Create scraping configuration
            config = ScrapingConfig(
                wait_time=kwargs.get('wait_time', 5),
                max_retries=kwargs.get('max_retries', 3),
                timeout=kwargs.get('timeout', 30),
                use_stealth=kwargs.get('use_stealth', True),
                headless=kwargs.get('headless', True),
                extract_images=kwargs.get('extract_images', False),
                extract_links=kwargs.get('extract_links', False),
                follow_links=kwargs.get('follow_links', False),
                max_depth=kwargs.get('max_depth', 1),
                custom_selectors=custom_selectors,
                delay_between_requests=kwargs.get('delay_between_requests', 1.0),
                javascript_enabled=kwargs.get('javascript_enabled', True),
                load_images=kwargs.get('load_images', False)
            )
            
            # Create job
            job = ScrapingJob(
                url=kwargs['url'],
                config=config,
                tags=kwargs.get('tags', []),
                priority=kwargs.get('priority', 5)
            )
            
            # Submit job (this would call the actual job creation API)
            success = self._submit_job(job)
            
            if success:
                st.success(f"✅ Job created successfully! Job ID: {job.id}")
                st.balloons()
            else:
                st.error("❌ Failed to create job")
                
        except Exception as e:
            self.logger.error(f"Error creating job: {e}")
            st.error(f"Failed to create job: {str(e)}")
    
    def _submit_job(self, job: ScrapingJob) -> bool:
        """Submit a job to the scraping system."""
        try:
            # This would typically call the API or job queue
            # For now, return True to simulate success
            self.logger.info(f"Submitting job {job.id} for URL: {job.url}")
            return True
        except Exception as e:
            self.logger.error(f"Error submitting job: {e}")
            return False
    
    def _load_active_jobs(self, status_filter: List[str], priority_filter: int, user_filter: str) -> List[Dict]:
        """Load active jobs based on filters."""
        try:
            # This would typically call the data loader
            # For now, return mock data
            return [
                {
                    'id': 'job-001',
                    'url': 'https://example.com/products',
                    'status': 'running',
                    'pages_completed': 45,
                    'pages_failed': 2,
                    'created_at': datetime.now() - timedelta(hours=2),
                    'priority': 3
                },
                {
                    'id': 'job-002',
                    'url': 'https://news.example.com',
                    'status': 'pending',
                    'pages_completed': 0,
                    'pages_failed': 0,
                    'created_at': datetime.now() - timedelta(minutes=30),
                    'priority': 5
                }
            ]
        except Exception as e:
            self.logger.error(f"Error loading active jobs: {e}")
            return []
    
    def _load_historical_jobs(self, start_date, end_date) -> List[Dict]:
        """Load historical jobs for the specified date range."""
        try:
            # This would typically call the data loader
            # For now, return mock data
            return [
                {
                    'id': 'job-003',
                    'url': 'https://example.com/archive',
                    'status': 'completed',
                    'pages_completed': 120,
                    'pages_failed': 3,
                    'created_at': datetime.now() - timedelta(days=1)
                }
            ]
        except Exception as e:
            self.logger.error(f"Error loading historical jobs: {e}")
            return []
    
    def _load_job_templates(self) -> Dict:
        """Load saved job templates."""
        try:
            # This would typically load from database or file
            return {
                "E-commerce Product Scraper": {
                    "description": "Template for scraping product information",
                    "config": {
                        "custom_selectors": {
                            "title": ".product-title, h1",
                            "price": ".price, .cost",
                            "description": ".product-description"
                        },
                        "extract_images": True,
                        "wait_time": 3
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
            return {}
    
    def _get_template_default_config(self) -> str:
        """Get default template configuration JSON."""
        return json.dumps({
            "wait_time": 5,
            "max_retries": 3,
            "use_stealth": True,
            "custom_selectors": {
                "title": "h1, .title",
                "content": ".content, .main"
            }
        }, indent=2)
    
    def _save_template(self, name: str, description: str, config: str):
        """Save a job template."""
        try:
            if not name:
                st.error("Template name is required")
                return
            
            # Validate JSON config
            try:
                json.loads(config)
            except json.JSONDecodeError:
                st.error("Invalid JSON configuration")
                return
            
            # Save template (this would typically save to database)
            st.success(f"Template '{name}' saved successfully!")
            
        except Exception as e:
            self.logger.error(f"Error saving template: {e}")
            st.error("Failed to save template")
    
    def _use_template(self, config: str):
        """Use a template configuration for job creation."""
        try:
            # This would populate the job creation form with template data
            st.info("Template configuration loaded. Switch to 'Create Job' tab to use it.")
        except Exception as e:
            self.logger.error(f"Error using template: {e}")
            st.error("Failed to use template")
    
    def _delete_template(self, template_name: str):
        """Delete a job template."""
        try:
            # This would delete from database
            st.success(f"Template '{template_name}' deleted successfully!")
        except Exception as e:
            self.logger.error(f"Error deleting template: {e}")
            st.error("Failed to delete template")
    
    def _show_job_details(self, job_id: str):
        """Show detailed information about a job."""
        try:
            # This would load detailed job information
            st.info(f"Showing details for job {job_id}")
        except Exception as e:
            self.logger.error(f"Error showing job details: {e}")
            st.error("Failed to load job details")
    
    def _stop_job(self, job_id: str):
        """Stop a running job."""
        try:
            # This would call the API to stop the job
            st.success(f"Job {job_id} stopped successfully!")
            st.rerun()
        except Exception as e:
            self.logger.error(f"Error stopping job: {e}")
            st.error("Failed to stop job")
    
    def _handle_bulk_action(self, action: str):
        """Handle bulk actions on selected jobs."""
        try:
            selected_jobs = st.session_state.get('selected_jobs', [])
            
            if not selected_jobs:
                st.warning("No jobs selected")
                return
            
            # Perform bulk action
            for job_id in selected_jobs:
                # This would call the appropriate API endpoint
                pass
            
            st.success(f"Bulk {action} completed for {len(selected_jobs)} jobs")
            st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error performing bulk action: {e}")
            st.error(f"Failed to perform bulk {action}")
    
    def _export_jobs_data(self, jobs: List[Dict], format: str):
        """Export jobs data in the specified format."""
        try:
            df = pd.DataFrame(jobs)
            
            if format == "csv":
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"jobs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            elif format == "json":
                json_data = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"jobs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                
        except Exception as e:
            self.logger.error(f"Error exporting jobs data: {e}")
            st.error("Failed to export data")