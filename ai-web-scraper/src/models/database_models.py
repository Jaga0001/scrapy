"""
SQLAlchemy ORM models for database tables.

This module contains the SQLAlchemy ORM models that define the database schema
and relationships between tables.
"""

from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ScrapingJobORM(Base):
    """SQLAlchemy model for scraping jobs table."""
    
    __tablename__ = "scraping_jobs"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # Basic job information
    url = Column(String(2048), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    
    # Configuration (stored as JSON)
    config = Column(JSON, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Progress tracking
    total_pages = Column(Integer, default=0, nullable=False)
    pages_completed = Column(Integer, default=0, nullable=False)
    pages_failed = Column(Integer, default=0, nullable=False)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Additional metadata
    user_id = Column(String(36), nullable=True, index=True)
    tags = Column(JSON, default=list, nullable=False)
    priority = Column(Integer, default=5, nullable=False, index=True)
    
    # Relationships
    scraped_data = relationship("ScrapedDataORM", back_populates="job", cascade="all, delete-orphan")
    job_logs = relationship("JobLogORM", back_populates="job", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_job_status_created', 'status', 'created_at'),
        Index('idx_job_user_status', 'user_id', 'status'),
        Index('idx_job_priority_created', 'priority', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScrapingJob(id={self.id}, url={self.url}, status={self.status})>"


class ScrapedDataORM(Base):
    """SQLAlchemy model for scraped data table."""
    
    __tablename__ = "scraped_data"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # Foreign key to job
    job_id = Column(String(36), ForeignKey("scraping_jobs.id"), nullable=False, index=True)
    
    # Source information
    url = Column(String(2048), nullable=False, index=True)
    content_type = Column(String(20), default="html", nullable=False)
    
    # Content data (stored as JSON for flexibility)
    content = Column(JSON, nullable=False)
    raw_html = Column(Text, nullable=True)
    
    # Metadata
    content_metadata = Column(JSON, default=dict, nullable=False)
    
    # AI processing results
    confidence_score = Column(Float, default=0.0, nullable=False, index=True)
    ai_processed = Column(Boolean, default=False, nullable=False, index=True)
    ai_metadata = Column(JSON, default=dict, nullable=False)
    
    # Quality metrics
    data_quality_score = Column(Float, default=0.0, nullable=False, index=True)
    validation_errors = Column(JSON, default=list, nullable=False)
    
    # Timestamps
    extracted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Content metrics
    content_length = Column(Integer, default=0, nullable=False)
    load_time = Column(Float, default=0.0, nullable=False)
    
    # Relationships
    job = relationship("ScrapingJobORM", back_populates="scraped_data")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_data_job_extracted', 'job_id', 'extracted_at'),
        Index('idx_data_confidence_quality', 'confidence_score', 'data_quality_score'),
        Index('idx_data_url_extracted', 'url', 'extracted_at'),
        Index('idx_data_ai_processed', 'ai_processed', 'extracted_at'),
    )
    
    def __repr__(self):
        return f"<ScrapedData(id={self.id}, job_id={self.job_id}, url={self.url})>"


class JobLogORM(Base):
    """SQLAlchemy model for job logs table."""
    
    __tablename__ = "job_logs"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # Foreign key to job
    job_id = Column(String(36), ForeignKey("scraping_jobs.id"), nullable=False, index=True)
    
    # Log information
    level = Column(String(10), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    
    # Additional context
    context = Column(JSON, default=dict, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    job = relationship("ScrapingJobORM", back_populates="job_logs")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_log_job_level', 'job_id', 'level'),
        Index('idx_log_created_level', 'created_at', 'level'),
    )
    
    def __repr__(self):
        return f"<JobLog(id={self.id}, job_id={self.job_id}, level={self.level})>"


class SystemMetricORM(Base):
    """SQLAlchemy model for system metrics table."""
    
    __tablename__ = "system_metrics"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # Metric information
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)
    
    # Additional context
    tags = Column(JSON, default=dict, nullable=False)
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_metric_name_recorded', 'metric_name', 'recorded_at'),
        Index('idx_metric_recorded', 'recorded_at'),
    )
    
    def __repr__(self):
        return f"<SystemMetric(name={self.metric_name}, value={self.metric_value}, recorded_at={self.recorded_at})>"


class DataExportORM(Base):
    """SQLAlchemy model for data export requests table."""
    
    __tablename__ = "data_exports"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # Export information
    format = Column(String(10), nullable=False)  # csv, json, xlsx
    status = Column(String(20), nullable=False, default="pending", index=True)
    
    # Export parameters
    job_ids = Column(JSON, default=list, nullable=False)
    date_from = Column(DateTime(timezone=True), nullable=True)
    date_to = Column(DateTime(timezone=True), nullable=True)
    min_confidence = Column(Float, default=0.0, nullable=False)
    include_raw_html = Column(Boolean, default=False, nullable=False)
    fields = Column(JSON, default=list, nullable=False)
    
    # File information
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # User information
    user_id = Column(String(36), nullable=True, index=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_export_status_requested', 'status', 'requested_at'),
        Index('idx_export_user_requested', 'user_id', 'requested_at'),
    )
    
    def __repr__(self):
        return f"<DataExport(id={self.id}, format={self.format}, status={self.status})>"


class UserSessionORM(Base):
    """SQLAlchemy model for user sessions table (for API authentication)."""
    
    __tablename__ = "user_sessions"
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)
    
    # User information
    user_id = Column(String(36), nullable=False, index=True)
    session_token = Column(String(255), nullable=False, unique=True, index=True)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"