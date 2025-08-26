"""
Error recovery and graceful degradation system.

This module provides automatic recovery strategies for common failure
scenarios and implements graceful degradation when services are unavailable.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass, field

from .exceptions import (
    ScraperBaseException, ErrorSeverity, AIServiceException,
    WebDriverException, NetworkException, DatabaseException,
    is_recoverable_error, get_retry_delay
)
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_manager
from .logger import get_logger

logger = get_logger(__name__)


class RecoveryStrategy(str, Enum):
    """Available recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    DEGRADE = "degrade"
    SKIP = "skip"
    FAIL_FAST = "fail_fast"


class RecoveryAction(str, Enum):
    """Recovery action results."""
    RETRY_OPERATION = "retry_operation"
    USE_FALLBACK = "use_fallback"
    DEGRADE_SERVICE = "degrade_service"
    SKIP_OPERATION = "skip_operation"
    ESCALATE_ERROR = "escalate_error"


@dataclass
class RecoveryConfig:
    """Configuration for error recovery behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    
    # Strategy preferences by error type
    strategy_map: Dict[Type[Exception], RecoveryStrategy] = field(default_factory=dict)
    
    # Fallback functions by operation type
    fallback_functions: Dict[str, Callable] = field(default_factory=dict)
    
    # Circuit breaker settings
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None


class ErrorRecoveryManager:
    """
    Manages error recovery strategies and graceful degradation.
    
    Provides automatic recovery for common failure scenarios and
    implements fallback mechanisms when primary services fail.
    """
    
    def __init__(self, config: RecoveryConfig = None):
        """
        Initialize error recovery manager.
        
        Args:
            config: Recovery configuration settings
        """
        self.config = config or RecoveryConfig()
        self._setup_default_strategies()
        self._recovery_stats = {
            "total_errors": 0,
            "recovered_errors": 0,
            "fallback_uses": 0,
            "degraded_operations": 0,
            "failed_recoveries": 0
        }
    
    def _setup_default_strategies(self) -> None:
        """Set up default recovery strategies for common exceptions."""
        default_strategies = {
            # Network and connection errors - retry with backoff
            NetworkException: RecoveryStrategy.RETRY,
            ConnectionError: RecoveryStrategy.RETRY,
            TimeoutError: RecoveryStrategy.RETRY,
            
            # AI service errors - fallback to rule-based processing
            AIServiceException: RecoveryStrategy.FALLBACK,
            
            # WebDriver errors - retry with fresh driver
            WebDriverException: RecoveryStrategy.RETRY,
            
            # Database errors - retry with connection refresh
            DatabaseException: RecoveryStrategy.RETRY,
            
            # Configuration errors - fail fast
            ValueError: RecoveryStrategy.FAIL_FAST,
            TypeError: RecoveryStrategy.FAIL_FAST,
        }
        
        # Update config with defaults if not already set
        for exc_type, strategy in default_strategies.items():
            if exc_type not in self.config.strategy_map:
                self.config.strategy_map[exc_type] = strategy
    
    async def handle_error(
        self,
        exception: Exception,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            exception: The exception that occurred
            operation_name: Name of the operation that failed
            operation_func: Function to retry if recovery is attempted
            *args: Arguments for the operation function
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            Result of recovery attempt or raises exception
        """
        self._recovery_stats["total_errors"] += 1
        
        logger.error(
            f"Error in operation '{operation_name}': {str(exception)}",
            extra={
                "operation": operation_name,
                "exception_type": type(exception).__name__,
                "recoverable": is_recoverable_error(exception)
            }
        )
        
        # Determine recovery strategy
        strategy = self._get_recovery_strategy(exception)
        
        try:
            if strategy == RecoveryStrategy.RETRY:
                return await self._retry_operation(
                    exception, operation_name, operation_func, *args, **kwargs
                )
            elif strategy == RecoveryStrategy.FALLBACK:
                return await self._use_fallback(
                    exception, operation_name, *args, **kwargs
                )
            elif strategy == RecoveryStrategy.DEGRADE:
                return await self._degrade_service(
                    exception, operation_name, operation_func, *args, **kwargs
                )
            elif strategy == RecoveryStrategy.SKIP:
                return await self._skip_operation(
                    exception, operation_name, *args, **kwargs
                )
            else:  # FAIL_FAST
                self._recovery_stats["failed_recoveries"] += 1
                raise exception
                
        except Exception as recovery_error:
            logger.error(
                f"Recovery failed for operation '{operation_name}': {str(recovery_error)}",
                extra={
                    "original_error": str(exception),
                    "recovery_error": str(recovery_error),
                    "strategy_used": strategy.value
                }
            )
            self._recovery_stats["failed_recoveries"] += 1
            raise recovery_error
    
    def _get_recovery_strategy(self, exception: Exception) -> RecoveryStrategy:
        """Determine the appropriate recovery strategy for an exception."""
        # Check for specific exception type mapping
        for exc_type, strategy in self.config.strategy_map.items():
            if isinstance(exception, exc_type):
                return strategy
        
        # Check for ScraperBaseException with severity-based strategy
        if isinstance(exception, ScraperBaseException):
            if exception.severity == ErrorSeverity.CRITICAL:
                return RecoveryStrategy.FAIL_FAST
            elif exception.severity == ErrorSeverity.HIGH:
                return RecoveryStrategy.FALLBACK
            elif exception.severity == ErrorSeverity.MEDIUM:
                return RecoveryStrategy.RETRY
            else:  # LOW
                return RecoveryStrategy.SKIP
        
        # Default strategy based on recoverability
        if is_recoverable_error(exception):
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.FAIL_FAST
    
    async def _retry_operation(
        self,
        exception: Exception,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Retry an operation with exponential backoff."""
        max_retries = self.config.max_retries
        base_delay = get_retry_delay(exception) or self.config.base_delay
        
        for attempt in range(max_retries):
            if attempt > 0:  # Don't delay on first retry
                delay = min(
                    base_delay * (self.config.backoff_multiplier ** (attempt - 1)),
                    self.config.max_delay
                )
                
                # Add jitter to prevent thundering herd
                if self.config.jitter:
                    import random
                    jitter = delay * 0.1 * random.uniform(-1, 1)
                    delay += jitter
                
                logger.info(
                    f"Retrying operation '{operation_name}' in {delay:.2f}s (attempt {attempt + 1}/{max_retries})",
                    extra={
                        "operation": operation_name,
                        "attempt": attempt + 1,
                        "delay": delay
                    }
                )
                
                await asyncio.sleep(delay)
            
            try:
                # Use circuit breaker if configured
                if self.config.circuit_breaker_config:
                    breaker = circuit_manager.get_breaker(
                        f"recovery_{operation_name}",
                        self.config.circuit_breaker_config
                    )
                    result = await breaker.call(operation_func, *args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(operation_func):
                        result = await operation_func(*args, **kwargs)
                    else:
                        result = operation_func(*args, **kwargs)
                
                logger.info(
                    f"Operation '{operation_name}' succeeded on retry attempt {attempt + 1}",
                    extra={
                        "operation": operation_name,
                        "successful_attempt": attempt + 1
                    }
                )
                
                self._recovery_stats["recovered_errors"] += 1
                return result
                
            except Exception as retry_error:
                if attempt == max_retries - 1:  # Last attempt
                    logger.error(
                        f"Operation '{operation_name}' failed after {max_retries} attempts",
                        extra={
                            "operation": operation_name,
                            "final_error": str(retry_error),
                            "total_attempts": max_retries
                        }
                    )
                    raise retry_error
                else:
                    logger.warning(
                        f"Retry attempt {attempt + 1} failed for operation '{operation_name}': {str(retry_error)}",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt + 1,
                            "error": str(retry_error)
                        }
                    )
        
        # Should not reach here, but just in case
        raise exception
    
    async def _use_fallback(
        self,
        exception: Exception,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Use fallback function for the operation."""
        fallback_func = self.config.fallback_functions.get(operation_name)
        
        if not fallback_func:
            logger.warning(
                f"No fallback function configured for operation '{operation_name}'",
                extra={"operation": operation_name}
            )
            raise exception
        
        logger.info(
            f"Using fallback for operation '{operation_name}'",
            extra={
                "operation": operation_name,
                "original_error": str(exception)
            }
        )
        
        try:
            if asyncio.iscoroutinefunction(fallback_func):
                result = await fallback_func(*args, **kwargs)
            else:
                result = fallback_func(*args, **kwargs)
            
            self._recovery_stats["fallback_uses"] += 1
            return result
            
        except Exception as fallback_error:
            logger.error(
                f"Fallback function failed for operation '{operation_name}': {str(fallback_error)}",
                extra={
                    "operation": operation_name,
                    "fallback_error": str(fallback_error),
                    "original_error": str(exception)
                }
            )
            raise fallback_error
    
    async def _degrade_service(
        self,
        exception: Exception,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Degrade service quality but continue operation."""
        logger.warning(
            f"Degrading service for operation '{operation_name}' due to error: {str(exception)}",
            extra={
                "operation": operation_name,
                "degradation_reason": str(exception)
            }
        )
        
        # Implement service degradation logic
        # This could involve reducing quality, disabling features, etc.
        degraded_kwargs = kwargs.copy()
        
        # Example degradation strategies
        if "quality" in degraded_kwargs:
            degraded_kwargs["quality"] = "low"
        if "timeout" in degraded_kwargs:
            degraded_kwargs["timeout"] = min(degraded_kwargs["timeout"], 10.0)
        if "max_items" in degraded_kwargs:
            degraded_kwargs["max_items"] = min(degraded_kwargs["max_items"], 10)
        
        try:
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **degraded_kwargs)
            else:
                result = operation_func(*args, **degraded_kwargs)
            
            self._recovery_stats["degraded_operations"] += 1
            return result
            
        except Exception as degrade_error:
            logger.error(
                f"Degraded operation '{operation_name}' still failed: {str(degrade_error)}",
                extra={
                    "operation": operation_name,
                    "degrade_error": str(degrade_error),
                    "original_error": str(exception)
                }
            )
            raise degrade_error
    
    async def _skip_operation(
        self,
        exception: Exception,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Skip the operation and return a safe default."""
        logger.info(
            f"Skipping operation '{operation_name}' due to error: {str(exception)}",
            extra={
                "operation": operation_name,
                "skip_reason": str(exception)
            }
        )
        
        # Return safe defaults based on operation type
        safe_defaults = {
            "scrape": {"content": "", "success": False, "error": str(exception)},
            "process": {"processed_data": {}, "confidence": 0.0, "error": str(exception)},
            "analyze": {"analysis": {}, "entities": [], "error": str(exception)},
            "export": {"exported": False, "file_path": None, "error": str(exception)}
        }
        
        # Try to match operation name to default
        for op_type, default in safe_defaults.items():
            if op_type in operation_name.lower():
                return default
        
        # Generic safe default
        return {"success": False, "error": str(exception), "skipped": True}
    
    def register_fallback(self, operation_name: str, fallback_func: Callable) -> None:
        """Register a fallback function for an operation."""
        self.config.fallback_functions[operation_name] = fallback_func
        logger.info(f"Registered fallback function for operation '{operation_name}'")
    
    def register_strategy(self, exception_type: Type[Exception], strategy: RecoveryStrategy) -> None:
        """Register a recovery strategy for an exception type."""
        self.config.strategy_map[exception_type] = strategy
        logger.info(f"Registered {strategy.value} strategy for {exception_type.__name__}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total_errors = self._recovery_stats["total_errors"]
        recovery_rate = (
            self._recovery_stats["recovered_errors"] / total_errors
            if total_errors > 0 else 0.0
        )
        
        return {
            **self._recovery_stats,
            "recovery_rate": recovery_rate,
            "registered_strategies": len(self.config.strategy_map),
            "registered_fallbacks": len(self.config.fallback_functions)
        }
    
    def reset_stats(self) -> None:
        """Reset recovery statistics."""
        self._recovery_stats = {
            "total_errors": 0,
            "recovered_errors": 0,
            "fallback_uses": 0,
            "degraded_operations": 0,
            "failed_recoveries": 0
        }


# Global error recovery manager
recovery_manager = ErrorRecoveryManager()


# Decorator for automatic error recovery
def with_recovery(
    operation_name: str = None,
    config: RecoveryConfig = None,
    manager: ErrorRecoveryManager = None
):
    """
    Decorator to add automatic error recovery to functions.
    
    Args:
        operation_name: Name of the operation (uses function name if None)
        config: Custom recovery configuration
        manager: Custom recovery manager (uses global if None)
    """
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        recovery_mgr = manager or recovery_manager
        if config:
            recovery_mgr.config = config
        
        async def async_wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                return await recovery_mgr.handle_error(e, operation_name, func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # For sync functions, we need to run recovery in event loop
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(
                    recovery_mgr.handle_error(e, operation_name, func, *args, **kwargs)
                )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator