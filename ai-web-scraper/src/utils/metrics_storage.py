"""
Database storage service for metrics and monitoring data.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from ..models.database_models import (
    SystemMetricORM, ApplicationMetricORM, PerformanceMetricORM,
    HealthCheckORM, AlertORM
)
from .logger import get_logger
from .metrics import SystemMetrics, ApplicationMetrics, PerformanceMetrics

logger = get_logger(__name__)


class MetricsStorage:
    """Handles storage and retrieval of metrics data in the database."""
    
    def __init__(self, db_session: Session):
        """
        Initialize metrics storage.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def store_system_metrics(self, metrics: SystemMetrics) -> str:
        """
        Store system metrics in the database.
        
        Args:
            metrics: System metrics to store
            
        Returns:
            ID of the stored metric record
        """
        try:
            metric_record = SystemMetricORM(
                id=str(uuid.uuid4()),
                metric_name="system_snapshot",
                metric_value=metrics.cpu_percent,
                metric_unit="percent",
                cpu_percent=metrics.cpu_percent,
                memory_percent=metrics.memory_percent,
                memory_used_mb=metrics.memory_used_mb,
                memory_available_mb=metrics.memory_available_mb,
                disk_usage_percent=metrics.disk_usage_percent,
                network_bytes_sent=metrics.network_bytes_sent,
                network_bytes_recv=metrics.network_bytes_recv,
                active_connections=metrics.active_connections,
                process_count=metrics.process_count,
                recorded_at=metrics.timestamp
            )
            
            self.db.add(metric_record)
            self.db.commit()
            
            logger.debug("Stored system metrics", metric_id=metric_record.id)
            return metric_record.id
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to store system metrics", error=str(e))
            raise
    
    def store_application_metrics(self, metrics: ApplicationMetrics) -> str:
        """
        Store application metrics in the database.
        
        Args:
            metrics: Application metrics to store
            
        Returns:
            ID of the stored metric record
        """
        try:
            metric_record = ApplicationMetricORM(
                id=str(uuid.uuid4()),
                active_scraping_jobs=metrics.active_scraping_jobs,
                completed_jobs_last_hour=metrics.completed_jobs_last_hour,
                failed_jobs_last_hour=metrics.failed_jobs_last_hour,
                avg_response_time_ms=metrics.avg_response_time_ms,
                total_pages_scraped=metrics.total_pages_scraped,
                data_quality_score=metrics.data_quality_score,
                api_requests_per_minute=metrics.api_requests_per_minute,
                error_rate_percent=metrics.error_rate_percent,
                recorded_at=metrics.timestamp
            )
            
            self.db.add(metric_record)
            self.db.commit()
            
            logger.debug("Stored application metrics", metric_id=metric_record.id)
            return metric_record.id
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to store application metrics", error=str(e))
            raise
    
    def store_performance_metrics(self, metrics: PerformanceMetrics, 
                                 correlation_id: Optional[str] = None) -> str:
        """
        Store performance metrics in the database.
        
        Args:
            metrics: Performance metrics to store
            correlation_id: Optional correlation ID for request tracking
            
        Returns:
            ID of the stored metric record
        """
        try:
            metric_record = PerformanceMetricORM(
                id=str(uuid.uuid4()),
                operation_name=metrics.operation_name,
                duration_ms=metrics.duration_ms,
                success=metrics.success,
                error_type=metrics.error_type,
                metadata=metrics.metadata,
                correlation_id=correlation_id,
                recorded_at=metrics.timestamp
            )
            
            self.db.add(metric_record)
            self.db.commit()
            
            logger.debug("Stored performance metrics", 
                        metric_id=metric_record.id,
                        operation=metrics.operation_name,
                        correlation_id=correlation_id)
            return metric_record.id
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to store performance metrics", error=str(e))
            raise
    
    def store_health_check(self, service_name: str, status: str, 
                          response_time_ms: float, details: Dict[str, Any] = None,
                          error_message: Optional[str] = None) -> str:
        """
        Store health check result in the database.
        
        Args:
            service_name: Name of the service checked
            status: Health status (healthy, degraded, unhealthy)
            response_time_ms: Response time in milliseconds
            details: Additional health check details
            error_message: Error message if unhealthy
            
        Returns:
            ID of the stored health check record
        """
        try:
            health_record = HealthCheckORM(
                id=str(uuid.uuid4()),
                service_name=service_name,
                status=status,
                response_time_ms=response_time_ms,
                details=details or {},
                error_message=error_message,
                checked_at=datetime.utcnow()
            )
            
            self.db.add(health_record)
            self.db.commit()
            
            logger.debug("Stored health check", 
                        health_id=health_record.id,
                        service=service_name,
                        status=status)
            return health_record.id
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to store health check", error=str(e))
            raise
    
    def create_alert(self, alert_type: str, severity: str, title: str, 
                    message: str, source_service: Optional[str] = None,
                    metric_name: Optional[str] = None, threshold_value: Optional[float] = None,
                    actual_value: Optional[float] = None, metadata: Dict[str, Any] = None) -> str:
        """
        Create a new alert in the database.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity (low, medium, high, critical)
            title: Alert title
            message: Alert message
            source_service: Service that triggered the alert
            metric_name: Metric that triggered the alert
            threshold_value: Threshold value that was exceeded
            actual_value: Actual value that triggered the alert
            metadata: Additional alert metadata
            
        Returns:
            ID of the created alert
        """
        try:
            alert_record = AlertORM(
                id=str(uuid.uuid4()),
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                source_service=source_service,
                metric_name=metric_name,
                threshold_value=threshold_value,
                actual_value=actual_value,
                metadata=metadata or {},
                triggered_at=datetime.utcnow()
            )
            
            self.db.add(alert_record)
            self.db.commit()
            
            logger.warning("Created alert", 
                          alert_id=alert_record.id,
                          type=alert_type,
                          severity=severity,
                          title=title)
            return alert_record.id
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create alert", error=str(e))
            raise
    
    def get_system_metrics_history(self, hours: int = 24) -> List[SystemMetricORM]:
        """
        Get system metrics history for the specified time period.
        
        Args:
            hours: Number of hours of history to retrieve
            
        Returns:
            List of system metrics records
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            metrics = self.db.query(SystemMetricORM).filter(
                SystemMetricORM.recorded_at >= cutoff
            ).order_by(desc(SystemMetricORM.recorded_at)).all()
            
            logger.debug("Retrieved system metrics history", 
                        count=len(metrics), hours=hours)
            return metrics
            
        except Exception as e:
            logger.error("Failed to retrieve system metrics history", error=str(e))
            raise
    
    def get_application_metrics_history(self, hours: int = 24) -> List[ApplicationMetricORM]:
        """
        Get application metrics history for the specified time period.
        
        Args:
            hours: Number of hours of history to retrieve
            
        Returns:
            List of application metrics records
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            metrics = self.db.query(ApplicationMetricORM).filter(
                ApplicationMetricORM.recorded_at >= cutoff
            ).order_by(desc(ApplicationMetricORM.recorded_at)).all()
            
            logger.debug("Retrieved application metrics history", 
                        count=len(metrics), hours=hours)
            return metrics
            
        except Exception as e:
            logger.error("Failed to retrieve application metrics history", error=str(e))
            raise
    
    def get_performance_metrics(self, operation: Optional[str] = None,
                               hours: int = 24) -> List[PerformanceMetricORM]:
        """
        Get performance metrics for a specific operation or all operations.
        
        Args:
            operation: Optional operation name to filter by
            hours: Number of hours of history to retrieve
            
        Returns:
            List of performance metrics records
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = self.db.query(PerformanceMetricORM).filter(
                PerformanceMetricORM.recorded_at >= cutoff
            )
            
            if operation:
                query = query.filter(PerformanceMetricORM.operation_name == operation)
            
            metrics = query.order_by(desc(PerformanceMetricORM.recorded_at)).all()
            
            logger.debug("Retrieved performance metrics", 
                        count=len(metrics), operation=operation, hours=hours)
            return metrics
            
        except Exception as e:
            logger.error("Failed to retrieve performance metrics", error=str(e))
            raise
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[AlertORM]:
        """
        Get active alerts, optionally filtered by severity.
        
        Args:
            severity: Optional severity filter (low, medium, high, critical)
            
        Returns:
            List of active alert records
        """
        try:
            query = self.db.query(AlertORM).filter(
                AlertORM.status == "active"
            )
            
            if severity:
                query = query.filter(AlertORM.severity == severity)
            
            alerts = query.order_by(desc(AlertORM.triggered_at)).all()
            
            logger.debug("Retrieved active alerts", 
                        count=len(alerts), severity=severity)
            return alerts
            
        except Exception as e:
            logger.error("Failed to retrieve active alerts", error=str(e))
            raise
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alert = self.db.query(AlertORM).filter(AlertORM.id == alert_id).first()
            if not alert:
                logger.warning("Alert not found for acknowledgment", alert_id=alert_id)
                return False
            
            alert.status = "acknowledged"
            alert.acknowledged_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info("Acknowledged alert", alert_id=alert_id)
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: ID of the alert to resolve
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alert = self.db.query(AlertORM).filter(AlertORM.id == alert_id).first()
            if not alert:
                logger.warning("Alert not found for resolution", alert_id=alert_id)
                return False
            
            alert.status = "resolved"
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info("Resolved alert", alert_id=alert_id)
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return False
    
    def cleanup_old_metrics(self, days: int = 30) -> int:
        """
        Clean up old metrics data to prevent database bloat.
        
        Args:
            days: Number of days of data to keep
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted_count = 0
            
            # Clean up system metrics
            system_deleted = self.db.query(SystemMetricORM).filter(
                SystemMetricORM.recorded_at < cutoff
            ).delete()
            deleted_count += system_deleted
            
            # Clean up application metrics
            app_deleted = self.db.query(ApplicationMetricORM).filter(
                ApplicationMetricORM.recorded_at < cutoff
            ).delete()
            deleted_count += app_deleted
            
            # Clean up performance metrics
            perf_deleted = self.db.query(PerformanceMetricORM).filter(
                PerformanceMetricORM.recorded_at < cutoff
            ).delete()
            deleted_count += perf_deleted
            
            # Clean up health checks
            health_deleted = self.db.query(HealthCheckORM).filter(
                HealthCheckORM.checked_at < cutoff
            ).delete()
            deleted_count += health_deleted
            
            # Clean up resolved alerts older than cutoff
            alert_deleted = self.db.query(AlertORM).filter(
                and_(
                    AlertORM.status == "resolved",
                    AlertORM.resolved_at < cutoff
                )
            ).delete()
            deleted_count += alert_deleted
            
            self.db.commit()
            
            logger.info("Cleaned up old metrics data", 
                       deleted_count=deleted_count, days=days)
            return deleted_count
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to cleanup old metrics", error=str(e))
            raise
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get a summary of metrics for the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary containing metrics summary
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            # System metrics summary
            system_metrics = self.db.query(SystemMetricORM).filter(
                SystemMetricORM.recorded_at >= cutoff
            ).all()
            
            # Application metrics summary
            app_metrics = self.db.query(ApplicationMetricORM).filter(
                ApplicationMetricORM.recorded_at >= cutoff
            ).all()
            
            # Performance metrics summary
            perf_metrics = self.db.query(PerformanceMetricORM).filter(
                PerformanceMetricORM.recorded_at >= cutoff
            ).all()
            
            # Active alerts
            active_alerts = self.db.query(AlertORM).filter(
                AlertORM.status == "active"
            ).count()
            
            # Calculate averages and totals
            avg_cpu = sum(m.cpu_percent or 0 for m in system_metrics) / len(system_metrics) if system_metrics else 0
            avg_memory = sum(m.memory_percent or 0 for m in system_metrics) / len(system_metrics) if system_metrics else 0
            
            total_operations = len(perf_metrics)
            successful_operations = sum(1 for m in perf_metrics if m.success)
            success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
            
            avg_response_time = sum(m.duration_ms for m in perf_metrics) / len(perf_metrics) if perf_metrics else 0
            
            summary = {
                "period_hours": hours,
                "system_metrics": {
                    "avg_cpu_percent": round(avg_cpu, 2),
                    "avg_memory_percent": round(avg_memory, 2),
                    "data_points": len(system_metrics)
                },
                "application_metrics": {
                    "data_points": len(app_metrics)
                },
                "performance_metrics": {
                    "total_operations": total_operations,
                    "success_rate_percent": round(success_rate, 2),
                    "avg_response_time_ms": round(avg_response_time, 2)
                },
                "alerts": {
                    "active_count": active_alerts
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.debug("Generated metrics summary", summary=summary)
            return summary
            
        except Exception as e:
            logger.error("Failed to generate metrics summary", error=str(e))
            raise