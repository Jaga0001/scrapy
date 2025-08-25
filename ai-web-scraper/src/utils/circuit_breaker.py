"""
Circuit breaker pattern implementation for handling failures gracefully.

This module provides a circuit breaker implementation that prevents
cascading failures by temporarily disabling failing operations.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass, field

from .logger import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Operation timeout in seconds
    
    # Exponential backoff settings
    initial_delay: float = 1.0
    max_delay: float = 300.0  # 5 minutes max
    backoff_multiplier: float = 2.0
    jitter: bool = True


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation with exponential backoff.
    
    Prevents cascading failures by temporarily blocking requests
    to failing services and implementing intelligent retry logic.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """
        Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            config: Configuration settings
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.next_attempt_time = 0.0
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_changes: Dict[str, int] = {
            CircuitState.CLOSED: 0,
            CircuitState.OPEN: 0,
            CircuitState.HALF_OPEN: 0
        }
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: When circuit is open
            Exception: Original function exceptions
        """
        self.total_requests += 1
        
        # Check if circuit should remain open
        if self.state == CircuitState.OPEN:
            if time.time() < self.next_attempt_time:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Next attempt in {self.next_attempt_time - time.time():.1f}s"
                )
            else:
                # Try to transition to half-open
                self._transition_to_half_open()
        
        try:
            # Execute the function with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, func, *args, **kwargs),
                    timeout=self.config.timeout
                )
            
            # Success - handle state transitions
            self._on_success()
            return result
            
        except Exception as e:
            # Failure - handle state transitions
            self._on_failure(e)
            raise
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        self.total_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed operation."""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(
            f"Circuit breaker '{self.name}' recorded failure: {str(exception)}",
            extra={
                "circuit_name": self.name,
                "failure_count": self.failure_count,
                "state": self.state.value,
                "exception_type": type(exception).__name__
            }
        )
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state goes back to open
            self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition circuit breaker to OPEN state."""
        self.state = CircuitState.OPEN
        self.state_changes[CircuitState.OPEN] += 1
        
        # Calculate next attempt time with exponential backoff
        delay = self._calculate_backoff_delay()
        self.next_attempt_time = time.time() + delay
        
        logger.error(
            f"Circuit breaker '{self.name}' opened after {self.failure_count} failures. "
            f"Next attempt in {delay:.1f}s",
            extra={
                "circuit_name": self.name,
                "failure_count": self.failure_count,
                "backoff_delay": delay,
                "next_attempt_time": self.next_attempt_time
            }
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.state_changes[CircuitState.HALF_OPEN] += 1
        self.success_count = 0
        
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to HALF_OPEN",
            extra={
                "circuit_name": self.name,
                "time_since_failure": time.time() - self.last_failure_time
            }
        )
    
    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.state_changes[CircuitState.CLOSED] += 1
        self.failure_count = 0
        self.success_count = 0
        
        logger.info(
            f"Circuit breaker '{self.name}' closed after successful recovery",
            extra={
                "circuit_name": self.name,
                "recovery_time": time.time() - self.last_failure_time
            }
        )
    
    def _calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay."""
        # Base delay increases exponentially with failure count
        delay = min(
            self.config.initial_delay * (self.config.backoff_multiplier ** (self.failure_count - 1)),
            self.config.max_delay
        )
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            import random
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(delay, self.config.initial_delay)
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.next_attempt_time = 0.0
        
        logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "success_rate": (
                self.total_successes / self.total_requests 
                if self.total_requests > 0 else 0.0
            ),
            "state_changes": dict(self.state_changes),
            "last_failure_time": self.last_failure_time,
            "next_attempt_time": self.next_attempt_time if self.state == CircuitState.OPEN else None,
            "time_until_next_attempt": (
                max(0, self.next_attempt_time - time.time()) 
                if self.state == CircuitState.OPEN else 0
            )
        }


class CircuitBreakerManager:
    """Manages multiple circuit breakers by name."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
    
    def get_breaker(
        self, 
        name: str, 
        config: CircuitBreakerConfig = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker by name.
        
        Args:
            name: Circuit breaker name
            config: Optional configuration (uses default if None)
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name, 
                config or self._default_config
            )
        
        return self._breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: breaker.get_stats() 
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
    
    def cleanup_inactive(self, max_age_seconds: float = 3600) -> None:
        """Remove circuit breakers that haven't been used recently."""
        current_time = time.time()
        inactive_breakers = []
        
        for name, breaker in self._breakers.items():
            if (current_time - breaker.last_failure_time > max_age_seconds and 
                breaker.total_requests == 0):
                inactive_breakers.append(name)
        
        for name in inactive_breakers:
            del self._breakers[name]
            logger.info(f"Removed inactive circuit breaker: {name}")


# Global circuit breaker manager
circuit_manager = CircuitBreakerManager()


# Decorator for easy circuit breaker usage
def circuit_breaker(
    name: str = None, 
    config: CircuitBreakerConfig = None
):
    """
    Decorator to add circuit breaker protection to functions.
    
    Args:
        name: Circuit breaker name (uses function name if None)
        config: Circuit breaker configuration
    """
    def decorator(func):
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        
        async def wrapper(*args, **kwargs):
            breaker = circuit_manager.get_breaker(breaker_name, config)
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator