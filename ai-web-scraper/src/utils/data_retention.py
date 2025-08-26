"""
Data retention and automated cleanup system.

This module implements data retention policies with automated cleanup
for maintaining compliance and managing storage efficiently.
"""

import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, func
from sqlalchemy.orm import sessionmaker

from src.models.database_models import (
    ScrapedDataORM, JobLogORM, SystemMetricORM, ApplicationMetricORM,
    PerformanceMetricORM, HealthCheckORM, AlertORM, DataExportORM,
    UserSessionORM
)
from src.utils.audit_logger import AuditLogORM, audit_logger, AuditEventType, AuditSeverity
from src.utils.logger import get_logger
from src.utils.security import data_protection_manager

logger = get_logger(__name__)


class DataRetentionManager:
    """
    Manages data retention policies and automated cleanup.
    
    This class implements configurable retention policies for different
    data types and provides automated cleanup functionality.
    """
    
    def __init__(self, db_session_factory):
        """
        Initialize data retention manager.
        
        Args:
            db_session_factory: Database session factory
        """
        self.db_session_factory = db_session_factory
        self.retention_policies = self._load_retention_policies()
        self.cleanup_batch_size = int(os.getenv("CLEANUP_BATCH_SIZE", "1000"))
        self.dry_run = os.getenv("RETENTION_DRY_RUN", "false").lower() == "true"
    
    def _load_retention_policies(self) -> Dict[str, timedelta]:
        """
        Load retention policies from configuration.
        
        Returns:
            Dict[str, timedelta]: Retention policies by data type
        """
        return {
            "scraped_data": timedelta(days=int(os.getenv("RETENTION_SCRAPED_DATA_DAYS", "365"))),
            "job_logs": timedelta(days=int(os.getenv("RETENTION_JOB_LOGS_DAYS", "90"))),
            "system_metrics": timedelta(days=int(os.getenv("RETENTION_SYSTEM_METRICS_DAYS", "30"))),
            "application_metrics": timedelta(days=int(os.getenv("RETENTION_APPLICATION_METRICS_DAYS", "30"))),
            "performance_metrics": timedelta(days=int(os.getenv("RETENTION_PERFORMANCE_METRICS_DAYS", "30"))),
            "health_checks": timedelta(days=int(os.getenv("RETENTION_HEALTH_CHECKS_DAYS", "7"))),
            "alerts": timedelta(days=int(os.getenv("RETENTION_ALERTS_DAYS", "180"))),
            "data_exports": timedelta(days=int(os.getenv("RETENTION_DATA_EXPORTS_DAYS", "30"))),
            "user_sessions": timedelta(days=int(os.getenv("RETENTION_USER_SESSIONS_DAYS", "30"))),
            "audit_logs": timedelta(days=int(os.getenv("RETENTION_AUDIT_LOGS_DAYS", "2555")))  # 7 years default
        }
    
    def run_cleanup(self, data_types: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Run automated cleanup for specified data types.
        
        Args:
            data_types: List of data types to clean up (all if None)
            
        Returns:
            Dict[str, int]: Number of records cleaned up by data type
        """
        if data_types is None:
            data_types = list(self.retention_policies.keys())
        
        cleanup_results = {}
        total_cleaned = 0
        
        logger.info(f"Starting data retention cleanup (dry_run={self.dry_run})")
        
        # Log cleanup start
        audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_START,
            event_description=f"Data retention cleanup started (dry_run={self.dry_run})",
            severity=AuditSeverity.MEDIUM,
            metadata={"data_types": data_types, "dry_run": self.dry_run}
        )
        
        try:
            for data_type in data_types:
                if data_type in self.retention_policies:
                    logger.info(f"Cleaning up {data_type}")
                    cleaned_count = self._cleanup_data_type(data_type)
                    cleanup_results[data_type] = cleaned_count
                    total_cleaned += cleaned_count
                    logger.info(f"Cleaned up {cleaned_count} {data_type} records")
                else:
                    logger.warning(f"No retention policy found for data type: {data_type}")
            
            # Log cleanup completion
            audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_STOP,
                event_description=f"Data retention cleanup completed. Total records cleaned: {total_cleaned}",
                severity=AuditSeverity.MEDIUM,
                metadata={"cleanup_results": cleanup_results, "total_cleaned": total_cleaned}
            )
            
            logger.info(f"Data retention cleanup completed. Total records cleaned: {total_cleaned}")
            
        except Exception as e:
            logger.error(f"Data retention cleanup failed: {e}")
            audit_logger.log_event(
                event_type=AuditEventType.SECURITY_ALERT,
                event_description=f"Data retention cleanup failed: {str(e)}",
                severity=AuditSeverity.HIGH,
                metadata={"error": str(e)}
            )
            raise
        
        return cleanup_results
    
    def _cleanup_data_type(self, data_type: str) -> int:
        """
        Clean up expired data for a specific data type.
        
        Args:
            data_type: Type of data to clean up
            
        Returns:
            int: Number of records cleaned up
        """
        retention_period = self.retention_policies[data_type]
        cutoff_date = datetime.utcnow() - retention_period
        
        # Map data types to ORM models and date columns
        model_mapping = {
            "scraped_data": (ScrapedDataORM, ScrapedDataORM.extracted_at),
            "job_logs": (JobLogORM, JobLogORM.created_at),
            "system_metrics": (SystemMetricORM, SystemMetricORM.recorded_at),
            "application_metrics": (ApplicationMetricORM, ApplicationMetricORM.recorded_at),
            "performance_metrics": (PerformanceMetricORM, PerformanceMetricORM.recorded_at),
            "health_checks": (HealthCheckORM, HealthCheckORM.checked_at),
            "alerts": (AlertORM, AlertORM.triggered_at),
            "data_exports": (DataExportORM, DataExportORM.requested_at),
            "user_sessions": (UserSessionORM, UserSessionORM.created_at),
            "audit_logs": (AuditLogORM, AuditLogORM.timestamp)
        }
        
        if data_type not in model_mapping:
            logger.warning(f"No model mapping found for data type: {data_type}")
            return 0
        
        model_class, date_column = model_mapping[data_type]
        
        session = self.db_session_factory()
        total_cleaned = 0
        
        try:
            # Count total records to be cleaned
            total_to_clean = session.query(model_class).filter(
                date_column < cutoff_date
            ).count()
            
            if total_to_clean == 0:
                logger.info(f"No expired {data_type} records found")
                return 0
            
            logger.info(f"Found {total_to_clean} expired {data_type} records to clean")
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would clean {total_to_clean} {data_type} records")
                return total_to_clean
            
            # Clean up in batches to avoid memory issues
            while True:
                # Get batch of expired records
                expired_records = session.query(model_class).filter(
                    date_column < cutoff_date
                ).limit(self.cleanup_batch_size).all()
                
                if not expired_records:
                    break
                
                # Handle special cleanup for certain data types
                if data_type == "scraped_data":
                    self._cleanup_scraped_data_files(expired_records)
                elif data_type == "data_exports":
                    self._cleanup_export_files(expired_records)
                
                # Delete records from database
                for record in expired_records:
                    session.delete(record)
                
                session.commit()
                batch_size = len(expired_records)
                total_cleaned += batch_size
                
                logger.info(f"Cleaned {batch_size} {data_type} records (total: {total_cleaned})")
                
                # Break if we got less than batch size (last batch)
                if batch_size < self.cleanup_batch_size:
                    break
            
            return total_cleaned
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup {data_type}: {e}")
            raise
        finally:
            session.close()
    
    def _cleanup_scraped_data_files(self, scraped_data_records: List[ScrapedDataORM]) -> None:
        """
        Clean up associated files for scraped data records.
        
        Args:
            scraped_data_records: List of scraped data records to clean up
        """
        for record in scraped_data_records:
            try:
                # Check if there are associated files to clean up
                metadata = record.content_metadata or {}
                
                # Clean up any stored files referenced in metadata
                if "file_paths" in metadata:
                    for file_path in metadata["file_paths"]:
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                logger.debug(f"Removed file: {file_path}")
                            except Exception as e:
                                logger.warning(f"Failed to remove file {file_path}: {e}")
                
                # Clean up any cached content files
                if "cache_file" in metadata:
                    cache_file = metadata["cache_file"]
                    if os.path.exists(cache_file):
                        try:
                            os.remove(cache_file)
                            logger.debug(f"Removed cache file: {cache_file}")
                        except Exception as e:
                            logger.warning(f"Failed to remove cache file {cache_file}: {e}")
                            
            except Exception as e:
                logger.warning(f"Failed to cleanup files for scraped data {record.id}: {e}")
    
    def _cleanup_export_files(self, export_records: List[DataExportORM]) -> None:
        """
        Clean up export files for data export records.
        
        Args:
            export_records: List of data export records to clean up
        """
        for record in export_records:
            try:
                if record.file_path and os.path.exists(record.file_path):
                    try:
                        os.remove(record.file_path)
                        logger.debug(f"Removed export file: {record.file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove export file {record.file_path}: {e}")
                        
            except Exception as e:
                logger.warning(f"Failed to cleanup export file for record {record.id}: {e}")
    
    def get_retention_summary(self) -> Dict[str, Dict[str, any]]:
        """
        Get summary of data retention status for all data types.
        
        Returns:
            Dict[str, Dict[str, any]]: Retention summary by data type
        """
        summary = {}
        session = self.db_session_factory()
        
        try:
            # Map data types to ORM models and date columns
            model_mapping = {
                "scraped_data": (ScrapedDataORM, ScrapedDataORM.extracted_at),
                "job_logs": (JobLogORM, JobLogORM.created_at),
                "system_metrics": (SystemMetricORM, SystemMetricORM.recorded_at),
                "application_metrics": (ApplicationMetricORM, ApplicationMetricORM.recorded_at),
                "performance_metrics": (PerformanceMetricORM, PerformanceMetricORM.recorded_at),
                "health_checks": (HealthCheckORM, HealthCheckORM.checked_at),
                "alerts": (AlertORM, AlertORM.triggered_at),
                "data_exports": (DataExportORM, DataExportORM.requested_at),
                "user_sessions": (UserSessionORM, UserSessionORM.created_at),
                "audit_logs": (AuditLogORM, AuditLogORM.timestamp)
            }
            
            for data_type, (model_class, date_column) in model_mapping.items():
                try:
                    retention_period = self.retention_policies.get(data_type, timedelta(days=365))
                    cutoff_date = datetime.utcnow() - retention_period
                    
                    # Count total records
                    total_records = session.query(model_class).count()
                    
                    # Count expired records
                    expired_records = session.query(model_class).filter(
                        date_column < cutoff_date
                    ).count()
                    
                    # Get oldest record date
                    oldest_record = session.query(func.min(date_column)).scalar()
                    
                    # Get newest record date
                    newest_record = session.query(func.max(date_column)).scalar()
                    
                    summary[data_type] = {
                        "retention_days": retention_period.days,
                        "total_records": total_records,
                        "expired_records": expired_records,
                        "active_records": total_records - expired_records,
                        "oldest_record": oldest_record.isoformat() if oldest_record else None,
                        "newest_record": newest_record.isoformat() if newest_record else None,
                        "cutoff_date": cutoff_date.isoformat()
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to get retention summary for {data_type}: {e}")
                    summary[data_type] = {
                        "error": str(e)
                    }
            
            return summary
            
        finally:
            session.close()
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired user sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        session = self.db_session_factory()
        cleaned_count = 0
        
        try:
            # Find expired sessions
            expired_sessions = session.query(UserSessionORM).filter(
                UserSessionORM.expires_at < datetime.utcnow()
            ).all()
            
            if not expired_sessions:
                return 0
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would clean {len(expired_sessions)} expired sessions")
                return len(expired_sessions)
            
            # Delete expired sessions
            for session_record in expired_sessions:
                session.delete(session_record)
                cleaned_count += 1
            
            session.commit()
            
            logger.info(f"Cleaned up {cleaned_count} expired user sessions")
            
            # Log cleanup
            audit_logger.log_event(
                event_type=AuditEventType.DATA_DELETE,
                event_description=f"Cleaned up {cleaned_count} expired user sessions",
                severity=AuditSeverity.LOW,
                metadata={"cleaned_count": cleaned_count}
            )
            
            return cleaned_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup expired sessions: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_old_alerts(self, resolved_only: bool = True) -> int:
        """
        Clean up old alerts based on retention policy.
        
        Args:
            resolved_only: Whether to only clean up resolved alerts
            
        Returns:
            int: Number of alerts cleaned up
        """
        retention_period = self.retention_policies.get("alerts", timedelta(days=180))
        cutoff_date = datetime.utcnow() - retention_period
        
        session = self.db_session_factory()
        cleaned_count = 0
        
        try:
            # Build query
            query = session.query(AlertORM).filter(
                AlertORM.triggered_at < cutoff_date
            )
            
            if resolved_only:
                query = query.filter(AlertORM.status == "resolved")
            
            old_alerts = query.all()
            
            if not old_alerts:
                return 0
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would clean {len(old_alerts)} old alerts")
                return len(old_alerts)
            
            # Delete old alerts
            for alert in old_alerts:
                session.delete(alert)
                cleaned_count += 1
            
            session.commit()
            
            logger.info(f"Cleaned up {cleaned_count} old alerts")
            
            # Log cleanup
            audit_logger.log_event(
                event_type=AuditEventType.DATA_DELETE,
                event_description=f"Cleaned up {cleaned_count} old alerts",
                severity=AuditSeverity.LOW,
                metadata={"cleaned_count": cleaned_count, "resolved_only": resolved_only}
            )
            
            return cleaned_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup old alerts: {e}")
            raise
        finally:
            session.close()
    
    def get_storage_usage(self) -> Dict[str, Dict[str, any]]:
        """
        Get storage usage statistics for data retention planning.
        
        Returns:
            Dict[str, Dict[str, any]]: Storage usage by data type
        """
        session = self.db_session_factory()
        usage_stats = {}
        
        try:
            # Get database size estimates
            model_mapping = {
                "scraped_data": ScrapedDataORM,
                "job_logs": JobLogORM,
                "system_metrics": SystemMetricORM,
                "application_metrics": ApplicationMetricORM,
                "performance_metrics": PerformanceMetricORM,
                "health_checks": HealthCheckORM,
                "alerts": AlertORM,
                "data_exports": DataExportORM,
                "user_sessions": UserSessionORM,
                "audit_logs": AuditLogORM
            }
            
            for data_type, model_class in model_mapping.items():
                try:
                    record_count = session.query(model_class).count()
                    
                    # Estimate storage size (rough calculation)
                    # This is a simplified estimation - actual implementation
                    # would need database-specific queries for accurate sizes
                    estimated_size_mb = record_count * 0.001  # Rough estimate
                    
                    usage_stats[data_type] = {
                        "record_count": record_count,
                        "estimated_size_mb": round(estimated_size_mb, 2),
                        "retention_days": self.retention_policies.get(data_type, timedelta(days=365)).days
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to get usage stats for {data_type}: {e}")
                    usage_stats[data_type] = {"error": str(e)}
            
            return usage_stats
            
        finally:
            session.close()


# Global data retention manager instance (will be initialized with db session factory)
data_retention_manager = None


def initialize_data_retention_manager(db_session_factory):
    """
    Initialize the global data retention manager.
    
    Args:
        db_session_factory: Database session factory
    """
    global data_retention_manager
    data_retention_manager = DataRetentionManager(db_session_factory)