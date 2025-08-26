"""
Integration module for error handling components.

This module demonstrates how to integrate all error handling components
and provides convenience functions for setting up error handling across
the application.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .exceptions import (
    ScraperBaseException, ErrorSeverity, WebDriverException,
    AIServiceException, NetworkException, DatabaseException
)
from .circuit_breaker import CircuitBreakerConfig, circuit_manager
from .error_recovery import (
    ErrorRecoveryManager, RecoveryConfig, RecoveryStrategy,
    recovery_manager, with_recovery
)
from .error_notifications import (
    ErrorNotificationSystem, NotificationConfig, NotificationChannel,
    notification_system, notify_error
)
from .logger import get_logger, set_correlation_id

logger = get_logger(__name__)


class IntegratedErrorHandler:
    """
    Integrated error handler that combines all error handling components.
    
    Provides a unified interface for error handling, recovery, and notifications
    across the entire application.
    """
    
    def __init__(
        self,
        recovery_config: Optional[RecoveryConfig] = None,
        notification_config: Optional[NotificationConfig] = None
    ):
        """
        Initialize integrated error handler.
        
        Args:
            recovery_config: Configuration for error recovery
            notification_config: Configuration for notifications
        """
        self.recovery_manager = ErrorRecoveryManager(recovery_config)
        self.notification_system = ErrorNotificationSystem(notification_config)
        self._setup_default_configurations()
    
    def _setup_default_configurations(self) -> None:
        """Set up default error handling configurations."""
        # Configure circuit breakers for common services
        circuit_configs = {
            "ai_service": CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0,
                success_threshold=3
            ),
            "database": CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                success_threshold=2
            ),
            "web_scraping": CircuitBreakerConfig(
                failure_threshold=10,
                recovery_timeout=120.0,
                success_threshold=5
            )
        }
        
        for service, config in circuit_configs.items():
            circuit_manager.get_breaker(service, config)
        
        # Register recovery strategies
        self.recovery_manager.register_strategy(
            AIServiceException, RecoveryStrategy.FALLBACK
        )
        self.recovery_manager.register_strategy(
            WebDriverException, RecoveryStrategy.RETRY
        )
        self.recovery_manager.register_strategy(
            NetworkException, RecoveryStrategy.RETRY
        )
        self.recovery_manager.register_strategy(
            DatabaseException, RecoveryStrategy.RETRY
        )
        
        logger.info("Integrated error handler configured with default settings")
    
    async def handle_error_with_full_pipeline(
        self,
        exception: Exception,
        operation_name: str,
        component_name: str,
        operation_func: Any = None,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Handle error with full pipeline: recovery + notification.
        
        Args:
            exception: The exception that occurred
            operation_name: Name of the operation that failed
            component_name: Name of the component where error occurred
            operation_func: Function to retry if recovery is attempted
            context: Additional context information
            correlation_id: Request correlation ID
            *args: Arguments for operation function
            **kwargs: Keyword arguments for operation function
            
        Returns:
            Result of recovery attempt or raises exception
        """
        recovery_attempted = False
        recovery_successful = False
        
        try:
            if operation_func:
                # Attempt recovery
                recovery_attempted = True
                result = await self.recovery_manager.handle_error(
                    exception, operation_name, operation_func, *args, **kwargs
                )
                recovery_successful = True
                
                # Notify about successful recovery
                await self.notification_system.notify_error(
                    exception,
                    component_name,
                    context=context,
                    correlation_id=correlation_id,
                    recovery_attempted=recovery_attempted,
                    recovery_successful=recovery_successful
                )
                
                return result
            else:
                # Just notify about the error
                await self.notification_system.notify_error(
                    exception,
                    component_name,
                    context=context,
                    correlation_id=correlation_id,
                    recovery_attempted=recovery_attempted,
                    recovery_successful=recovery_successful
                )
                raise exception
                
        except Exception as recovery_error:
            # Recovery failed, notify about failure
            await self.notification_system.notify_error(
                recovery_error,
                component_name,
                context={
                    **(context or {}),
                    "original_error": str(exception),
                    "recovery_error": str(recovery_error)
                },
                correlation_id=correlation_id,
                recovery_attempted=recovery_attempted,
                recovery_successful=recovery_successful
            )
            raise recovery_error
    
    def register_fallback_function(self, operation_name: str, fallback_func: Any) -> None:
        """Register a fallback function for an operation."""
        self.recovery_manager.register_fallback(operation_name, fallback_func)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all error handling components."""
        return {
            "recovery_stats": self.recovery_manager.get_stats(),
            "notification_stats": self.notification_system.get_stats(),
            "circuit_breaker_stats": circuit_manager.get_all_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global integrated error handler
integrated_handler = IntegratedErrorHandler()


def setup_application_error_handling(
    recovery_config: Optional[RecoveryConfig] = None,
    notification_config: Optional[NotificationConfig] = None
) -> IntegratedErrorHandler:
    """
    Set up application-wide error handling.
    
    Args:
        recovery_config: Custom recovery configuration
        notification_config: Custom notification configuration
        
    Returns:
        Configured integrated error handler
    """
    global integrated_handler
    
    if recovery_config or notification_config:
        integrated_handler = IntegratedErrorHandler(recovery_config, notification_config)
    
    logger.info("Application error handling setup completed")
    return integrated_handler


# Convenience decorators
def with_integrated_error_handling(
    operation_name: str = None,
    component_name: str = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for integrated error handling with recovery and notifications.
    
    Args:
        operation_name: Name of the operation
        component_name: Name of the component
        context: Additional context information
    """
    def decorator(func):
        nonlocal operation_name, component_name
        
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        if component_name is None:
            component_name = func.__module__.split('.')[-1]
        
        async def async_wrapper(*args, **kwargs):
            correlation_id = set_correlation_id()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                return await integrated_handler.handle_error_with_full_pipeline(
                    e, operation_name, component_name, func, context, correlation_id, *args, **kwargs
                )
        
        def sync_wrapper(*args, **kwargs):
            correlation_id = set_correlation_id()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # For sync functions, run in event loop
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(
                    integrated_handler.handle_error_with_full_pipeline(
                        e, operation_name, component_name, func, context, correlation_id, *args, **kwargs
                    )
                )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Example usage functions
async def demonstrate_error_handling():
    """Demonstrate comprehensive error handling capabilities."""
    logger.info("Starting error handling demonstration")
    
    # Example 1: Network error with retry
    @with_integrated_error_handling("network_operation", "demo_component")
    async def flaky_network_operation():
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise NetworkException("Connection timeout")
        return "Network operation successful"
    
    try:
        result = await flaky_network_operation()
        logger.info(f"Network operation result: {result}")
    except Exception as e:
        logger.error(f"Network operation failed: {e}")
    
    # Example 2: AI service error with fallback
    async def ai_fallback():
        return {"result": "fallback_data", "confidence": 0.3}
    
    integrated_handler.register_fallback_function("ai_operation", ai_fallback)
    
    @with_integrated_error_handling("ai_operation", "ai_component")
    async def ai_operation():
        raise AIServiceException("AI service unavailable", service_name="gemini")
    
    try:
        result = await ai_operation()
        logger.info(f"AI operation result: {result}")
    except Exception as e:
        logger.error(f"AI operation failed: {e}")
    
    # Example 3: Database error with circuit breaker
    @with_integrated_error_handling("database_operation", "database_component")
    async def database_operation():
        raise DatabaseException("Connection pool exhausted", operation="SELECT")
    
    # Simulate multiple database failures to trigger circuit breaker
    for i in range(5):
        try:
            await database_operation()
        except Exception as e:
            logger.warning(f"Database operation {i+1} failed: {e}")
    
    # Show comprehensive stats
    stats = integrated_handler.get_comprehensive_stats()
    logger.info(f"Error handling stats: {stats}")


if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demonstrate_error_handling())