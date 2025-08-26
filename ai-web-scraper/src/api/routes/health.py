"""
Health check API routes.

This module contains endpoints for system health monitoring and status checks.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import HealthResponse, SystemStatsResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Track application start time for uptime calculation
_start_time = time.time()


async def get_database_status() -> bool:
    """
    Check database connectivity.
    
    Returns:
        bool: True if database is connected, False otherwise
    """
    try:
        # This would use actual database connection
        # For now, return True as placeholder
        await asyncio.sleep(0.01)  # Simulate async database check
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def get_redis_status() -> bool:
    """
    Check Redis connectivity.
    
    Returns:
        bool: True if Redis is connected, False otherwise
    """
    try:
        # This would use actual Redis connection
        # For now, return True as placeholder
        await asyncio.sleep(0.01)  # Simulate async Redis check
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


async def get_active_jobs_count() -> int:
    """
    Get count of currently active jobs.
    
    Returns:
        int: Number of active jobs
    """
    try:
        # This would query the database for active jobs
        # For now, return 0 as placeholder
        return 0
    except Exception as e:
        logger.error(f"Failed to get active jobs count: {e}")
        return -1


async def get_system_metrics() -> Dict[str, Any]:
    """
    Get current system metrics.
    
    Returns:
        Dict[str, Any]: System metrics including CPU, memory, etc.
    """
    try:
        import psutil
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            "process_count": len(psutil.pids()),
        }
    except ImportError:
        logger.warning("psutil not available, returning basic metrics")
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "load_average": None,
            "process_count": 0,
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {}


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Basic Health Check",
    description="Returns basic health status of the API service"
)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns basic health information including service status,
    database connectivity, and Redis connectivity.
    """
    try:
        # Check database connectivity
        db_connected = await get_database_status()
        
        # Check Redis connectivity
        redis_connected = await get_redis_status()
        
        # Get active jobs count
        active_jobs = await get_active_jobs_count()
        
        # Get basic system metrics
        system_metrics = await get_system_metrics()
        
        # Calculate uptime
        uptime_seconds = time.time() - _start_time
        
        # Determine overall status
        overall_status = "healthy"
        if not db_connected or not redis_connected:
            overall_status = "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime_seconds,
            database_connected=db_connected,
            redis_connected=redis_connected,
            active_jobs=active_jobs,
            system_metrics=system_metrics
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed"
        )


@router.get(
    "/detailed",
    response_model=SystemStatsResponse,
    summary="Detailed System Statistics",
    description="Returns comprehensive system statistics and performance metrics"
)
async def detailed_health_check():
    """
    Detailed health check with comprehensive system statistics.
    
    Returns detailed information about system performance,
    resource usage, and operational metrics.
    """
    try:
        import psutil
        
        # Get detailed system metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network and process information
        network_connections = len(psutil.net_connections())
        
        # Get queue size (placeholder - would use actual queue system)
        queue_size = 0
        
        # Get worker status (placeholder - would use actual worker system)
        worker_status = {
            "total_workers": 4,
            "active_workers": 4,
            "idle_workers": 0,
            "failed_workers": 0
        }
        
        # Get recent performance metrics (placeholder)
        recent_performance = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "response_time_ms": 150,
                "requests_per_second": 25,
                "error_rate": 0.02
            }
        ]
        
        return SystemStatsResponse(
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=(disk.used / disk.total) * 100,
            active_connections=network_connections,
            queue_size=queue_size,
            worker_status=worker_status,
            recent_performance=recent_performance
        )
        
    except ImportError:
        logger.warning("psutil not available for detailed metrics")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System monitoring tools not available"
        )
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Detailed health check failed"
        )


@router.get(
    "/readiness",
    summary="Readiness Probe",
    description="Kubernetes-style readiness probe for deployment health checks"
)
async def readiness_probe():
    """
    Readiness probe for container orchestration systems.
    
    Returns 200 if the service is ready to accept traffic,
    503 if the service is not ready.
    """
    try:
        # Check critical dependencies
        db_connected = await get_database_status()
        redis_connected = await get_redis_status()
        
        if db_connected and redis_connected:
            return {"status": "ready"}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready - dependencies unavailable"
            )
            
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get(
    "/liveness",
    summary="Liveness Probe",
    description="Kubernetes-style liveness probe for deployment health checks"
)
async def liveness_probe():
    """
    Liveness probe for container orchestration systems.
    
    Returns 200 if the service is alive and functioning,
    503 if the service should be restarted.
    """
    try:
        # Basic liveness check - service is responding
        return {"status": "alive", "timestamp": datetime.utcnow()}
        
    except Exception as e:
        logger.error(f"Liveness probe failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not alive"
        )


@router.get(
    "/version",
    summary="Version Information",
    description="Returns version and build information"
)
async def version_info():
    """
    Get version and build information.
    
    Returns version, build date, and other deployment information.
    """
    return {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",  # Would be set during build
        "git_commit": "unknown",  # Would be set during build
        "python_version": "3.11+",
        "api_version": "v1"
    }