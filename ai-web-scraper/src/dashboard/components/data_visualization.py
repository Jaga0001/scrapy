"""
Data visualization component for the Streamlit dashboard.

This module provides interactive data visualization and exploration capabilities
for scraped content with filtering, search, and preview functionality.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataVisualizationComponent:
    """
    Component for visualizing and exploring scraped data.
    """
    
    def __init__(self, data_loader):
        """
        Initialize the data visualization component.
        
        Args:
            data_loader: Dashboard data loader instance
        """
        self.data_loader = data_loader
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def render(self):
        """Render the data visualization interface."""
        try:
            # Create tabs for different visualization functions
            tab1, tab2, tab3, tab4 = st.tabs([
                "🔍 Data Explorer", 
                "📊 Analytics", 
                "🎯 Content Preview", 
                "📈 Quality Metrics"
            ])
            
            with tab1:
                self._render_data_explorer_tab()
            
            with tab2:
                self._render_analytics_tab()
            
            with tab3:
                self._render_content_preview_tab()
            
            with tab4:
                self._render_quality_metrics_tab()
                
        except Exception as e:
            self.logger.error(f"Error rendering data visualization: {e}")
            st.error(f"Failed to render data visualization interface: {str(e)}")
    
    def _render_data_explorer_tab(self):
        """Render the data explorer tab with filtering and search."""
        st.subheader("🔍 Data Explorer")
        
        # Filter controls
        with st.expander("🔧 Filters & Search", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Job filter
                job_filter = st.multiselect(
                    "Filter by Job",
                    options=self._get_available_jobs(),
                    help="Select specific jobs to view data from"
                )
                
                # Date range filter
                date_range = st.date_input(
                    "Date Range",
                    value=(datetime.now() - timedelta(days=7), datetime.now()),
                    help="Filter data by extraction date"
                )
            
            with col2:
                # Quality filters
                min_confidence = st.slider(
                    "Minimum Confidence Score",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.1,
                    help="Filter by AI confidence score"
                )
                
                min_quality = st.slider(
                    "Minimum Quality Score",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.1,
                    help="Filter by data quality score"
                )
            
            with col3:
                # Content filters
                ai_processed_only = st.checkbox(
                    "AI Processed Only",
                    help="Show only AI-processed data"
                )
                
                has_errors_only = st.checkbox(
                    "Has Validation Errors",
                    help="Show only data with validation errors"
                )
                
                # Search
                search_query = st.text_input(
                    "Search Content",
                    placeholder="Search in scraped content...",
                    help="Search within scraped content"
                )
        
        # Load and display data
        try:
            data = self._load_scraped_data(
                job_filter=job_filter,
                date_range=date_range,
                min_confidence=min_confidence,
                min_quality=min_quality,
                ai_processed_only=ai_processed_only,
                has_errors_only=has_errors_only,
                search_query=search_query
            )
            
            if data:
                # Data summary
                self._render_data_summary(data)
                
                # Data table with pagination
                st.markdown("---")
                self._render_data_table(data)
                
                # Export options
                st.markdown("---")
                self._render_export_options(data)
            else:
                st.info("No data found matching the current filters.")
                
        except Exception as e:
            self.logger.error(f"Error loading scraped data: {e}")
            st.error("Failed to load scraped data")
    
    def _render_analytics_tab(self):
        """Render the analytics tab with charts and insights."""
        st.subheader("📊 Data Analytics")
        
        try:
            # Load analytics data
            analytics_data = self._load_analytics_data()
            
            if analytics_data:
                # Key metrics row
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Records",
                        analytics_data.get('total_records', 0),
                        delta=analytics_data.get('records_delta', 0)
                    )
                
                with col2:
                    st.metric(
                        "Avg Confidence",
                        f"{analytics_data.get('avg_confidence', 0):.2f}",
                        delta=f"{analytics_data.get('confidence_delta', 0):.2f}"
                    )
                
                with col3:
                    st.metric(
                        "Avg Quality",
                        f"{analytics_data.get('avg_quality', 0):.2f}",
                        delta=f"{analytics_data.get('quality_delta', 0):.2f}"
                    )
                
                with col4:
                    st.metric(
                        "AI Processed",
                        f"{analytics_data.get('ai_processed_pct', 0):.1f}%",
                        delta=f"{analytics_data.get('ai_processed_delta', 0):.1f}%"
                    )
                
                # Charts row
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📈 Data Volume Over Time")
                    self._render_volume_chart(analytics_data.get('volume_data', []))
                
                with col2:
                    st.subheader("🎯 Quality Distribution")
                    self._render_quality_distribution_chart(analytics_data.get('quality_data', {}))
                
                # Additional charts
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🌐 Top Domains")
                    self._render_domain_chart(analytics_data.get('domain_data', {}))
                
                with col2:
                    st.subheader("⚠️ Error Analysis")
                    self._render_error_analysis_chart(analytics_data.get('error_data', {}))
                
                # Content type analysis
                st.subheader("📄 Content Type Analysis")
                self._render_content_type_analysis(analytics_data.get('content_type_data', {}))
                
            else:
                st.info("No analytics data available.")
                
        except Exception as e:
            self.logger.error(f"Error loading analytics data: {e}")
            st.error("Failed to load analytics data")
    
    def _render_content_preview_tab(self):
        """Render the content preview tab."""
        st.subheader("🎯 Content Preview")
        
        # Record selector
        col1, col2 = st.columns([2, 1])
        
        with col1:
            record_id = st.text_input(
                "Record ID",
                placeholder="Enter record ID to preview...",
                help="Enter the ID of a specific data record"
            )
        
        with col2:
            if st.button("🔍 Load Record", use_container_width=True):
                if record_id:
                    self._load_and_preview_record(record_id)
        
        # Recent records selector
        st.markdown("**Or select from recent records:**")
        
        try:
            recent_records = self._load_recent_records(limit=20)
            
            if recent_records:
                selected_record = st.selectbox(
                    "Recent Records",
                    options=[(r['id'], f"{r['url'][:50]}... ({r['extracted_at']})") 
                            for r in recent_records],
                    format_func=lambda x: x[1],
                    key="recent_record_selector"
                )
                
                if selected_record:
                    record_id = selected_record[0]
                    self._load_and_preview_record(record_id)
            else:
                st.info("No recent records found.")
                
        except Exception as e:
            self.logger.error(f"Error loading recent records: {e}")
            st.error("Failed to load recent records")
    
    def _render_quality_metrics_tab(self):
        """Render the quality metrics tab."""
        st.subheader("📈 Data Quality Metrics")
        
        try:
            quality_data = self._load_quality_metrics()
            
            if quality_data:
                # Quality overview
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Overall Quality Score",
                        f"{quality_data.get('overall_quality', 0):.2f}",
                        help="Average quality score across all data"
                    )
                
                with col2:
                    st.metric(
                        "Records with Errors",
                        quality_data.get('error_count', 0),
                        help="Number of records with validation errors"
                    )
                
                with col3:
                    st.metric(
                        "Error Rate",
                        f"{quality_data.get('error_rate', 0):.1f}%",
                        help="Percentage of records with errors"
                    )
                
                # Quality trends
                st.subheader("📊 Quality Trends")
                self._render_quality_trend_chart(quality_data.get('quality_trends', []))
                
                # Error breakdown
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("⚠️ Error Types")
                    self._render_error_types_chart(quality_data.get('error_types', {}))
                
                with col2:
                    st.subheader("🎯 Confidence Distribution")
                    self._render_confidence_distribution_chart(quality_data.get('confidence_dist', {}))
                
                # Quality improvement suggestions
                st.subheader("💡 Quality Improvement Suggestions")
                self._render_quality_suggestions(quality_data.get('suggestions', []))
                
            else:
                st.info("No quality metrics available.")
                
        except Exception as e:
            self.logger.error(f"Error loading quality metrics: {e}")
            st.error("Failed to load quality metrics")
    
    def _render_data_summary(self, data: List[Dict]):
        """Render summary statistics for the loaded data."""
        if not data:
            return
        
        df = pd.DataFrame(data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Records", len(df))
        
        with col2:
            avg_confidence = df['confidence_score'].mean() if 'confidence_score' in df else 0
            st.metric("Avg Confidence", f"{avg_confidence:.2f}")
        
        with col3:
            avg_quality = df['data_quality_score'].mean() if 'data_quality_score' in df else 0
            st.metric("Avg Quality", f"{avg_quality:.2f}")
        
        with col4:
            ai_processed = len(df[df['ai_processed'] == True]) if 'ai_processed' in df else 0
            ai_pct = (ai_processed / len(df) * 100) if len(df) > 0 else 0
            st.metric("AI Processed", f"{ai_pct:.1f}%")
    
    def _render_data_table(self, data: List[Dict]):
        """Render the data table with pagination."""
        if not data:
            return
        
        df = pd.DataFrame(data)
        
        # Pagination
        page_size = st.selectbox("Records per page", [10, 25, 50, 100], index=1)
        total_pages = (len(df) - 1) // page_size + 1
        
        if total_pages > 1:
            page = st.selectbox("Page", range(1, total_pages + 1))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            df_page = df.iloc[start_idx:end_idx]
        else:
            df_page = df
        
        # Format columns for display
        display_columns = ['id', 'url', 'confidence_score', 'data_quality_score', 'ai_processed', 'extracted_at']
        display_df = df_page[display_columns].copy()
        
        # Format datetime
        if 'extracted_at' in display_df:
            display_df['extracted_at'] = pd.to_datetime(display_df['extracted_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Truncate URL
        if 'url' in display_df:
            display_df['url'] = display_df['url'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
        
        display_df.columns = ['ID', 'URL', 'Confidence', 'Quality', 'AI Processed', 'Extracted']
        
        # Display with row selection
        selected_rows = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row"
        )
        
        # Show selected row details
        if selected_rows and len(selected_rows.selection.rows) > 0:
            selected_idx = selected_rows.selection.rows[0]
            selected_record_id = df_page.iloc[selected_idx]['id']
            
            with st.expander("📋 Selected Record Details", expanded=True):
                self._show_record_details(selected_record_id, data)
    
    def _render_export_options(self, data: List[Dict]):
        """Render export options for the data."""
        st.subheader("📤 Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export as CSV", use_container_width=True):
                self._export_data(data, "csv")
        
        with col2:
            if st.button("📋 Export as JSON", use_container_width=True):
                self._export_data(data, "json")
        
        with col3:
            if st.button("📈 Export as Excel", use_container_width=True):
                self._export_data(data, "excel")
    
    def _render_volume_chart(self, volume_data: List[Dict]):
        """Render data volume over time chart."""
        if not volume_data:
            st.info("No volume data available")
            return
        
        df = pd.DataFrame(volume_data)
        
        fig = px.line(
            df,
            x='date',
            y='count',
            title='Data Records Over Time',
            markers=True
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_quality_distribution_chart(self, quality_data: Dict):
        """Render quality score distribution chart."""
        if not quality_data:
            st.info("No quality data available")
            return
        
        fig = px.histogram(
            x=list(quality_data.keys()),
            y=list(quality_data.values()),
            title='Quality Score Distribution',
            nbins=20
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_domain_chart(self, domain_data: Dict):
        """Render top domains chart."""
        if not domain_data:
            st.info("No domain data available")
            return
        
        fig = px.bar(
            x=list(domain_data.values()),
            y=list(domain_data.keys()),
            orientation='h',
            title='Top Scraped Domains'
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_error_analysis_chart(self, error_data: Dict):
        """Render error analysis chart."""
        if not error_data:
            st.info("No error data available")
            return
        
        fig = px.pie(
            values=list(error_data.values()),
            names=list(error_data.keys()),
            title='Error Distribution'
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_content_type_analysis(self, content_type_data: Dict):
        """Render content type analysis."""
        if not content_type_data:
            st.info("No content type data available")
            return
        
        # Create subplots for different content type metrics
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Content Type Distribution', 'Average Quality by Type'),
            specs=[[{"type": "pie"}, {"type": "bar"}]]
        )
        
        # Content type distribution
        fig.add_trace(
            go.Pie(
                labels=list(content_type_data.keys()),
                values=[data['count'] for data in content_type_data.values()],
                name="Distribution"
            ),
            row=1, col=1
        )
        
        # Average quality by type
        fig.add_trace(
            go.Bar(
                x=list(content_type_data.keys()),
                y=[data['avg_quality'] for data in content_type_data.values()],
                name="Avg Quality"
            ),
            row=1, col=2
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    def _load_and_preview_record(self, record_id: str):
        """Load and preview a specific record."""
        try:
            record = self._load_record_by_id(record_id)
            
            if record:
                st.success(f"✅ Loaded record: {record_id}")
                
                # Record metadata
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Metadata**")
                    st.json({
                        "ID": record.get('id'),
                        "URL": record.get('url'),
                        "Confidence Score": record.get('confidence_score'),
                        "Quality Score": record.get('data_quality_score'),
                        "AI Processed": record.get('ai_processed'),
                        "Extracted At": record.get('extracted_at')
                    })
                
                with col2:
                    st.markdown("**Validation Errors**")
                    errors = record.get('validation_errors', [])
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        st.success("No validation errors")
                
                # Content preview
                st.markdown("**Extracted Content**")
                content = record.get('content', {})
                
                if content:
                    # Display content in expandable sections
                    for key, value in content.items():
                        with st.expander(f"📄 {key.title()}", expanded=key == 'title'):
                            if isinstance(value, (dict, list)):
                                st.json(value)
                            else:
                                st.text(str(value)[:1000] + "..." if len(str(value)) > 1000 else str(value))
                else:
                    st.info("No content available")
                
                # Raw HTML preview (if available)
                if record.get('raw_html'):
                    with st.expander("🔍 Raw HTML", expanded=False):
                        st.code(record['raw_html'][:2000] + "..." if len(record['raw_html']) > 2000 else record['raw_html'], language='html')
            else:
                st.error(f"❌ Record not found: {record_id}")
                
        except Exception as e:
            self.logger.error(f"Error loading record preview: {e}")
            st.error(f"Failed to load record: {str(e)}")
    
    def _show_record_details(self, record_id: str, data: List[Dict]):
        """Show details for a selected record."""
        try:
            record = next((r for r in data if r['id'] == record_id), None)
            
            if record:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.json({
                        "Confidence": record.get('confidence_score'),
                        "Quality": record.get('data_quality_score'),
                        "AI Processed": record.get('ai_processed'),
                        "Content Length": record.get('content_length')
                    })
                
                with col2:
                    content_preview = record.get('content', {})
                    if content_preview:
                        # Show first few fields
                        preview = {k: v for k, v in list(content_preview.items())[:3]}
                        st.json(preview)
                    else:
                        st.info("No content preview available")
                        
        except Exception as e:
            self.logger.error(f"Error showing record details: {e}")
            st.error("Failed to show record details")
    
    def _get_available_jobs(self) -> List[str]:
        """Get list of available job IDs for filtering."""
        try:
            # This would typically query the database
            return ["job-001", "job-002", "job-003"]
        except Exception as e:
            self.logger.error(f"Error getting available jobs: {e}")
            return []
    
    def _load_scraped_data(self, **filters) -> List[Dict]:
        """Load scraped data based on filters."""
        try:
            # This would typically call the data repository
            # For now, return mock data
            return [
                {
                    'id': 'data-001',
                    'job_id': 'job-001',
                    'url': 'https://example.com/page1',
                    'confidence_score': 0.85,
                    'data_quality_score': 0.92,
                    'ai_processed': True,
                    'extracted_at': datetime.now() - timedelta(hours=2),
                    'content': {'title': 'Sample Title', 'content': 'Sample content...'},
                    'content_length': 1250,
                    'validation_errors': []
                }
            ]
        except Exception as e:
            self.logger.error(f"Error loading scraped data: {e}")
            return []
    
    def _load_analytics_data(self) -> Dict:
        """Load analytics data for charts and metrics."""
        try:
            # This would typically aggregate data from the database
            return {
                'total_records': 15420,
                'records_delta': 1250,
                'avg_confidence': 0.87,
                'confidence_delta': 0.03,
                'avg_quality': 0.91,
                'quality_delta': 0.02,
                'ai_processed_pct': 94.2,
                'ai_processed_delta': 2.1,
                'volume_data': [
                    {'date': datetime.now() - timedelta(days=i), 'count': 100 + i * 10}
                    for i in range(7, 0, -1)
                ],
                'quality_data': {f'0.{i}': 10 + i for i in range(10)},
                'domain_data': {
                    'example.com': 5420,
                    'test.com': 3210,
                    'sample.org': 2890
                },
                'error_data': {
                    'Validation Error': 45,
                    'Parsing Error': 23,
                    'Network Error': 12
                },
                'content_type_data': {
                    'html': {'count': 12000, 'avg_quality': 0.89},
                    'json': {'count': 2500, 'avg_quality': 0.95},
                    'text': {'count': 920, 'avg_quality': 0.82}
                }
            }
        except Exception as e:
            self.logger.error(f"Error loading analytics data: {e}")
            return {}
    
    def _load_recent_records(self, limit: int = 20) -> List[Dict]:
        """Load recent data records."""
        try:
            # This would typically query recent records
            return [
                {
                    'id': f'data-{i:03d}',
                    'url': f'https://example.com/page{i}',
                    'extracted_at': (datetime.now() - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M')
                }
                for i in range(1, limit + 1)
            ]
        except Exception as e:
            self.logger.error(f"Error loading recent records: {e}")
            return []
    
    def _load_record_by_id(self, record_id: str) -> Optional[Dict]:
        """Load a specific record by ID."""
        try:
            # This would typically query the database
            return {
                'id': record_id,
                'url': 'https://example.com/sample',
                'confidence_score': 0.87,
                'data_quality_score': 0.93,
                'ai_processed': True,
                'extracted_at': datetime.now().isoformat(),
                'content': {
                    'title': 'Sample Article Title',
                    'content': 'This is sample content from the scraped page...',
                    'author': 'John Doe',
                    'date': '2024-01-15'
                },
                'content_length': 1250,
                'validation_errors': [],
                'raw_html': '<html><head><title>Sample</title></head><body>...</body></html>'
            }
        except Exception as e:
            self.logger.error(f"Error loading record by ID: {e}")
            return None
    
    def _load_quality_metrics(self) -> Dict:
        """Load quality metrics data."""
        try:
            # This would typically aggregate quality data
            return {
                'overall_quality': 0.89,
                'error_count': 156,
                'error_rate': 1.2,
                'quality_trends': [
                    {'date': datetime.now() - timedelta(days=i), 'quality': 0.85 + i * 0.01}
                    for i in range(7, 0, -1)
                ],
                'error_types': {
                    'Missing Required Field': 45,
                    'Invalid Format': 32,
                    'Duplicate Content': 28,
                    'Low Confidence': 51
                },
                'confidence_dist': {f'0.{i}': 15 + i * 5 for i in range(10)},
                'suggestions': [
                    "Consider improving CSS selectors for better content extraction",
                    "Review validation rules for frequently failing fields",
                    "Implement duplicate detection for better data quality"
                ]
            }
        except Exception as e:
            self.logger.error(f"Error loading quality metrics: {e}")
            return {}
    
    def _render_quality_trend_chart(self, trend_data: List[Dict]):
        """Render quality trend chart."""
        if not trend_data:
            st.info("No trend data available")
            return
        
        df = pd.DataFrame(trend_data)
        
        fig = px.line(
            df,
            x='date',
            y='quality',
            title='Quality Score Trends',
            markers=True
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_error_types_chart(self, error_types: Dict):
        """Render error types chart."""
        if not error_types:
            st.info("No error data available")
            return
        
        fig = px.bar(
            x=list(error_types.keys()),
            y=list(error_types.values()),
            title='Error Types Distribution'
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        fig.update_xaxis(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_confidence_distribution_chart(self, confidence_dist: Dict):
        """Render confidence distribution chart."""
        if not confidence_dist:
            st.info("No confidence data available")
            return
        
        fig = px.histogram(
            x=list(confidence_dist.keys()),
            y=list(confidence_dist.values()),
            title='Confidence Score Distribution'
        )
        
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_quality_suggestions(self, suggestions: List[str]):
        """Render quality improvement suggestions."""
        if not suggestions:
            st.info("No suggestions available")
            return
        
        for i, suggestion in enumerate(suggestions, 1):
            st.info(f"💡 **Suggestion {i}:** {suggestion}")
    
    def _export_data(self, data: List[Dict], format: str):
        """Export data in the specified format."""
        try:
            df = pd.DataFrame(data)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format == "csv":
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"scraped_data_{timestamp}.csv",
                    mime="text/csv"
                )
            elif format == "json":
                json_data = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"scraped_data_{timestamp}.json",
                    mime="application/json"
                )
            elif format == "excel":
                # For Excel export, we'd need to use BytesIO
                st.info("Excel export functionality would be implemented here")
                
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            st.error("Failed to export data")