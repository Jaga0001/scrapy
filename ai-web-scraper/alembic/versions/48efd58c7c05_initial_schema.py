"""Initial schema

Revision ID: 48efd58c7c05
Revises: 
Create Date: 2025-08-25 20:21:02.661233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48efd58c7c05'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create scraping_jobs table
    op.create_table(
        'scraping_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('config', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_pages', sa.Integer(), default=0, nullable=False),
        sa.Column('pages_completed', sa.Integer(), default=0, nullable=False),
        sa.Column('pages_failed', sa.Integer(), default=0, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0, nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('tags', sa.JSON(), default=list, nullable=False),
        sa.Column('priority', sa.Integer(), default=5, nullable=False),
    )
    
    # Create indexes for scraping_jobs
    op.create_index('idx_job_status_created', 'scraping_jobs', ['status', 'created_at'])
    op.create_index('idx_job_user_status', 'scraping_jobs', ['user_id', 'status'])
    op.create_index('idx_job_priority_created', 'scraping_jobs', ['priority', 'created_at'])
    op.create_index('ix_scraping_jobs_id', 'scraping_jobs', ['id'])
    op.create_index('ix_scraping_jobs_url', 'scraping_jobs', ['url'])
    op.create_index('ix_scraping_jobs_status', 'scraping_jobs', ['status'])
    op.create_index('ix_scraping_jobs_created_at', 'scraping_jobs', ['created_at'])
    op.create_index('ix_scraping_jobs_user_id', 'scraping_jobs', ['user_id'])
    op.create_index('ix_scraping_jobs_priority', 'scraping_jobs', ['priority'])
    
    # Create scraped_data table
    op.create_table(
        'scraped_data',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('job_id', sa.String(36), sa.ForeignKey('scraping_jobs.id'), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('content_type', sa.String(20), default='html', nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('raw_html', sa.Text(), nullable=True),
        sa.Column('content_metadata', sa.JSON(), default=dict, nullable=False),
        sa.Column('confidence_score', sa.Float(), default=0.0, nullable=False),
        sa.Column('ai_processed', sa.Boolean(), default=False, nullable=False),
        sa.Column('ai_metadata', sa.JSON(), default=dict, nullable=False),
        sa.Column('data_quality_score', sa.Float(), default=0.0, nullable=False),
        sa.Column('validation_errors', sa.JSON(), default=list, nullable=False),
        sa.Column('extracted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_length', sa.Integer(), default=0, nullable=False),
        sa.Column('load_time', sa.Float(), default=0.0, nullable=False),
    )
    
    # Create indexes for scraped_data
    op.create_index('idx_data_job_extracted', 'scraped_data', ['job_id', 'extracted_at'])
    op.create_index('idx_data_confidence_quality', 'scraped_data', ['confidence_score', 'data_quality_score'])
    op.create_index('idx_data_url_extracted', 'scraped_data', ['url', 'extracted_at'])
    op.create_index('idx_data_ai_processed', 'scraped_data', ['ai_processed', 'extracted_at'])
    op.create_index('ix_scraped_data_id', 'scraped_data', ['id'])
    op.create_index('ix_scraped_data_job_id', 'scraped_data', ['job_id'])
    op.create_index('ix_scraped_data_url', 'scraped_data', ['url'])
    op.create_index('ix_scraped_data_confidence_score', 'scraped_data', ['confidence_score'])
    op.create_index('ix_scraped_data_ai_processed', 'scraped_data', ['ai_processed'])
    op.create_index('ix_scraped_data_data_quality_score', 'scraped_data', ['data_quality_score'])
    op.create_index('ix_scraped_data_extracted_at', 'scraped_data', ['extracted_at'])
    
    # Create job_logs table
    op.create_table(
        'job_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('job_id', sa.String(36), sa.ForeignKey('scraping_jobs.id'), nullable=False),
        sa.Column('level', sa.String(10), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context', sa.JSON(), default=dict, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for job_logs
    op.create_index('idx_log_job_level', 'job_logs', ['job_id', 'level'])
    op.create_index('idx_log_created_level', 'job_logs', ['created_at', 'level'])
    op.create_index('ix_job_logs_id', 'job_logs', ['id'])
    op.create_index('ix_job_logs_job_id', 'job_logs', ['job_id'])
    op.create_index('ix_job_logs_level', 'job_logs', ['level'])
    op.create_index('ix_job_logs_created_at', 'job_logs', ['created_at'])
    
    # Create system_metrics table
    op.create_table(
        'system_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(20), nullable=True),
        sa.Column('tags', sa.JSON(), default=dict, nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for system_metrics
    op.create_index('idx_metric_name_recorded', 'system_metrics', ['metric_name', 'recorded_at'])
    op.create_index('idx_metric_recorded', 'system_metrics', ['recorded_at'])
    op.create_index('ix_system_metrics_id', 'system_metrics', ['id'])
    op.create_index('ix_system_metrics_metric_name', 'system_metrics', ['metric_name'])
    op.create_index('ix_system_metrics_recorded_at', 'system_metrics', ['recorded_at'])
    
    # Create data_exports table
    op.create_table(
        'data_exports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('format', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('job_ids', sa.JSON(), default=list, nullable=False),
        sa.Column('date_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('min_confidence', sa.Float(), default=0.0, nullable=False),
        sa.Column('include_raw_html', sa.Boolean(), default=False, nullable=False),
        sa.Column('fields', sa.JSON(), default=list, nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    
    # Create indexes for data_exports
    op.create_index('idx_export_status_requested', 'data_exports', ['status', 'requested_at'])
    op.create_index('idx_export_user_requested', 'data_exports', ['user_id', 'requested_at'])
    op.create_index('ix_data_exports_id', 'data_exports', ['id'])
    op.create_index('ix_data_exports_status', 'data_exports', ['status'])
    op.create_index('ix_data_exports_requested_at', 'data_exports', ['requested_at'])
    op.create_index('ix_data_exports_user_id', 'data_exports', ['user_id'])
    
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False, unique=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_accessed', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
    )
    
    # Create indexes for user_sessions
    op.create_index('idx_session_user_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('idx_session_expires', 'user_sessions', ['expires_at'])
    op.create_index('ix_user_sessions_id', 'user_sessions', ['id'])
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_session_token', 'user_sessions', ['session_token'])
    op.create_index('ix_user_sessions_expires_at', 'user_sessions', ['expires_at'])
    op.create_index('ix_user_sessions_is_active', 'user_sessions', ['is_active'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('user_sessions')
    op.drop_table('data_exports')
    op.drop_table('system_metrics')
    op.drop_table('job_logs')
    op.drop_table('scraped_data')
    op.drop_table('scraping_jobs')
