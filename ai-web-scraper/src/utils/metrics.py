"""
System metrics collection for CPU, memory, and network usage monitoring.
"""
import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import psutil
import threading
from collections import defaultdict, deque

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    process_count: int


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    timestamp: datetime
    active_scraping_jobs: int
    completed_jobs_last_hour: int
    failed_jobs_last_hour: int
    avg_response_time_ms: float
    total_pages_scraped: int
    data_quality_score: float
    api_requests_per_minute: int
    error_rate_percent: float


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics."""
    timestamp: datetime
    operation_name: str
    duration_ms: float
    success: bool
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and manages system and application metrics."""
    
    def __init__(self, collection_interval: int = 30, history_size: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            collection_interval: Seconds between metric collections
            history_size: Maximum number of metric snapshots to keep
        """
        self.collection_interval = collection_interval
        self.history_size = history_size
        
        # Metric storage
        self.system_metrics: deque = deque(maxlen=history_size)
        self.app_metrics: deque = deque(maxlen=history_size)
        self.performance_metrics: deque = deque(maxlen=history_size * 10)
        
        # Application counters
        self._app_counters = defaultdict(int)
        self._response_times = deque(maxlen=100)
        self._error_counts = defaultdict(int)
        
        # Collection control
        self._collecting = False
        self._collection_thread: Optional[threading.Thread] = None
        
        # Network baseline for calculating deltas
        self._last_network_stats = None
        
        logger.info("MetricsCollector initialized", 
                   interval=collection_interval, 
                   history_size=history_size)
    
    def start_collection(self) -> None:
        """Start automatic metrics collection."""
        if self._collecting:
            logger.warning("Metrics collection already running")
            return
        
        self._collecting = True
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="MetricsCollector"
        )
        self._collection_thread.start()
        logger.info("Started metrics collection")
    
    def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        if not self._collecting:
            return
        
        self._collecting = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
        logger.info("Stopped metrics collection")
    
    def _collection_loop(self) -> None:
        """Main collection loop running in background thread."""
        while self._collecting:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error("Error in metrics collection loop", error=str(e))
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics - use configurable path for cross-platform compatibility
            disk_path = os.getenv('METRICS_DISK_PATH', '/' if os.name != 'nt' else 'C:')
            disk = psutil.disk_usage(disk_path)
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process_count = len(psutil.pids())
            active_connections = len(psutil.net_connections())
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                active_connections=active_connections,
                process_count=process_count
            )
            
            self.system_metrics.append(metrics)
            
            logger.debug("Collected system metrics",
                        cpu_percent=cpu_percent,
                        memory_percent=memory.percent,
                        disk_percent=disk.percent)
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
    
    def _collect_application_metrics(self) -> None:
        """Collect application-specific metrics."""
        try:
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            
            # Calculate averages and rates
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times else 0.0
            )
            
            # Error rate calculation
            total_requests = self._app_counters.get('total_requests', 0)
            total_errors = sum(self._error_counts.values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
            
            metrics = ApplicationMetrics(
                timestamp=now,
                active_scraping_jobs=self._app_counters.get('active_jobs', 0),
                completed_jobs_last_hour=self._app_counters.get('completed_jobs_hour', 0),
                failed_jobs_last_hour=self._app_counters.get('failed_jobs_hour', 0),
                avg_response_time_ms=avg_response_time,
                total_pages_scraped=self._app_counters.get('pages_scraped', 0),
                data_quality_score=self._app_counters.get('quality_score', 0.0),
                api_requests_per_minute=self._app_counters.get('api_requests_minute', 0),
                error_rate_percent=error_rate
            )
            
            self.app_metrics.append(metrics)
            
            logger.debug("Collected application metrics",
                        active_jobs=metrics.active_scraping_jobs,
                        avg_response_time=avg_response_time,
                        error_rate=error_rate)
            
        except Exception as e:
            logger.error("Failed to collect application metrics", error=str(e))
    
    def record_performance(self, operation: str, duration_ms: float, 
                          success: bool = True, error_type: Optional[str] = None,
                          **metadata) -> None:
        """
        Record performance metrics for an operation.
        
        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            error_type: Type of error if failed
            **metadata: Additional metadata
        """
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            operation_name=operation,
            duration_ms=duration_ms,
            success=success,
            error_type=error_type,
            metadata=metadata
        )
        
        self.performance_metrics.append(metrics)
        
        # Update response time tracking
        if success:
            self._response_times.append(duration_ms)
        
        # Update error tracking
        if not success and error_type:
            self._error_counts[error_type] += 1
        
        # Update request counter
        self._app_counters['total_requests'] += 1
        
        logger.debug("Recorded performance metric",
                    operation=operation,
                    duration_ms=duration_ms,
                    success=success,
                    error_type=error_type)
    
    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """Increment an application counter."""
        self._app_counters[counter_name] += value
        logger.debug("Incremented counter", counter=counter_name, value=value)
    
    def set_gauge(self, gauge_name: str, value: float) -> None:
        """Set a gauge value."""
        self._app_counters[gauge_name] = value
        logger.debug("Set gauge", gauge=gauge_name, value=value)
    
    def get_latest_system_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent system metrics."""
        return self.system_metrics[-1] if self.system_metrics else None
    
    def get_latest_app_metrics(self) -> Optional[ApplicationMetrics]:
        """Get the most recent application metrics."""
        return self.app_metrics[-1] if self.app_metrics else None
    
    def get_system_metrics_history(self, minutes: int = 60) -> List[SystemMetrics]:
        """
        Get system metrics history for the specified time period.
        
        Args:
            minutes: Number of minutes of history to return
            
        Returns:
            List of system metrics within the time period
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [m for m in self.system_metrics if m.timestamp >= cutoff]
    
    def get_performance_metrics(self, operation: Optional[str] = None,
                               minutes: int = 60) -> List[PerformanceMetrics]:
        """
        Get performance metrics for a specific operation or all operations.
        
        Args:
            operation: Optional operation name to filter by
            minutes: Number of minutes of history to return
            
        Returns:
            List of performance metrics
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        metrics = [m for m in self.performance_metrics if m.timestamp >= cutoff]
        
        if operation:
            metrics = [m for m in metrics if m.operation_name == operation]
        
        return metrics
    
    def get_error_summary(self, minutes: int = 60) -> Dict[str, int]:
        """
        Get error summary for the specified time period.
        
        Args:
            minutes: Number of minutes to analyze
            
        Returns:
            Dictionary of error types and their counts
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        error_counts = defaultdict(int)
        
        for metric in self.performance_metrics:
            if (metric.timestamp >= cutoff and 
                not metric.success and 
                metric.error_type):
                error_counts[metric.error_type] += 1
        
        return dict(error_counts)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dictionary containing health indicators
        """
        latest_system = self.get_latest_system_metrics()
        latest_app = self.get_latest_app_metrics()
        
        if not latest_system or not latest_app:
            return {"status": "unknown", "reason": "insufficient_data"}
        
        # Health thresholds
        cpu_threshold = 80.0
        memory_threshold = 85.0
        error_rate_threshold = 5.0
        
        issues = []
        
        if latest_system.cpu_percent > cpu_threshold:
            issues.append(f"High CPU usage: {latest_system.cpu_percent:.1f}%")
        
        if latest_system.memory_percent > memory_threshold:
            issues.append(f"High memory usage: {latest_system.memory_percent:.1f}%")
        
        if latest_app.error_rate_percent > error_rate_threshold:
            issues.append(f"High error rate: {latest_app.error_rate_percent:.1f}%")
        
        if issues:
            return {
                "status": "degraded",
                "issues": issues,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def start_metrics_collection() -> None:
    """Start global metrics collection."""
    collector = get_metrics_collector()
    collector.start_collection()


def stop_metrics_collection() -> None:
    """Stop global metrics collection."""
    collector = get_metrics_collector()
    collector.stop_collection()


class MetricsContext:
    """Context manager for tracking operation performance."""
    
    def __init__(self, operation_name: str, **metadata):
        self.operation_name = operation_name
        self.metadata = metadata
        self.start_time = None
        self.collector = get_metrics_collector()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        success = exc_type is None
        error_type = exc_type.__name__ if exc_type else None
        
        self.collector.record_performance(
            operation=self.operation_name,
            duration_ms=duration_ms,
            success=success,
            error_type=error_type,
            **self.metadata
        )


def track_performance(operation_name: str, **metadata):
    """Decorator for tracking function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with MetricsContext(operation_name, **metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator