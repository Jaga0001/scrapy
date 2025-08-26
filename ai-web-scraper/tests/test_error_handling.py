"""
Unit tests for error handling and recovery mechanisms.

Tests the custom exceptions, circuit breaker, error recovery,
and notification systems.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.utils.exceptions import (
    ScraperBaseException, ErrorSeverity, WebDriverException,
    AIServiceException, DataValidationException, NetworkException,
    is_recoverable_error, get_retry_delay
)
from src.utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState,
    CircuitBreakerError, circuit_manager
)
from src.utils.error_recovery import (
    ErrorRecoveryManager, RecoveryConfig, RecoveryStrategy,
    RecoveryAction, with_recovery
)
from src.utils.error_notifications import (
    ErrorNotificationSystem, NotificationConfig, NotificationChannel,
    NotificationPriority, ErrorNotification, notify_error
)


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_scraper_base_exception_creation(self):
        """Test creating base exception with all parameters."""
        context = {"url": "https://example.com", "attempt": 1}
        exception = ScraperBaseException(
            message="Test error",
            severity=ErrorSeverity.HIGH,
            context=context,
            recoverable=True,
            retry_after=30.0
        )
        
        assert exception.message == "Test error"
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.context == context
        assert exception.recoverable is True
        assert exception.retry_after == 30.0
    
    def test_exception_to_dict(self):
        """Test exception serialization to dictionary."""
        exception = WebDriverException(
            message="Driver failed",
            driver_type="chrome",
            severity=ErrorSeverity.MEDIUM
        )
        
        result = exception.to_dict()
        
        assert result["error_type"] == "WebDriverException"
        assert result["message"] == "Driver failed"
        assert result["severity"] == "medium"
        assert result["context"]["driver_type"] == "chrome"
        assert result["recoverable"] is True
    
    def test_ai_service_exception(self):
        """Test AI service specific exception."""
        exception = AIServiceException(
            message="API rate limit exceeded",
            service_name="gemini",
            api_error_code="RATE_LIMIT_EXCEEDED"
        )
        
        assert exception.context["service_name"] == "gemini"
        assert exception.context["api_error_code"] == "RATE_LIMIT_EXCEEDED"
    
    def test_is_recoverable_error(self):
        """Test error recoverability detection."""
        # Recoverable custom exception
        recoverable_exc = NetworkException("Connection timeout")
        assert is_recoverable_error(recoverable_exc) is True
        
        # Non-recoverable custom exception
        non_recoverable_exc = ScraperBaseException(
            "Critical error", 
            recoverable=False
        )
        assert is_recoverable_error(non_recoverable_exc) is False
        
        # Standard recoverable exceptions
        assert is_recoverable_error(ConnectionError()) is True
        assert is_recoverable_error(TimeoutError()) is True
        
        # Standard non-recoverable exceptions
        assert is_recoverable_error(ValueError()) is False
        assert is_recoverable_error(TypeError()) is False
    
    def test_get_retry_delay(self):
        """Test retry delay extraction."""
        # Custom exception with retry_after
        exception = NetworkException("Timeout", retry_after=45.0)
        assert get_retry_delay(exception) == 45.0
        
        # Standard exceptions with default delays
        assert get_retry_delay(ConnectionError()) == 30.0
        assert get_retry_delay(TimeoutError()) == 60.0
        
        # Exception without specific delay
        assert get_retry_delay(ValueError()) is None


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def circuit_config(self):
        """Circuit breaker configuration for testing."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2,
            timeout=0.5
        )
    
    @pytest.fixture
    def circuit_breaker(self, circuit_config):
        """Circuit breaker instance for testing."""
        return CircuitBreaker("test_circuit", circuit_config)
    
    @pytest.mark.asyncio
    async def test_successful_operation(self, circuit_breaker):
        """Test successful operation through circuit breaker."""
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test circuit opens after threshold failures."""
        async def failing_func():
            raise Exception("Test failure")
        
        # Cause failures to reach threshold
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_blocks_when_open(self, circuit_breaker):
        """Test circuit blocks requests when open."""
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Should now raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failing_func)
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_transition(self, circuit_breaker):
        """Test transition to half-open state."""
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should transition to half-open
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)
        
        # Should be back to open after failure in half-open
        assert circuit_breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_success(self, circuit_breaker):
        """Test circuit closes after successful recovery."""
        async def failing_func():
            raise Exception("Test failure")
        
        async def success_func():
            return "recovered"
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Succeed enough times to close circuit
        for i in range(2):
            result = await circuit_breaker.call(success_func)
            assert result == "recovered"
        
        assert circuit_breaker.state == CircuitState.CLOSED
    
    def test_circuit_breaker_stats(self, circuit_breaker):
        """Test circuit breaker statistics."""
        stats = circuit_breaker.get_stats()
        
        assert stats["name"] == "test_circuit"
        assert stats["state"] == CircuitState.CLOSED.value
        assert stats["total_requests"] == 0
        assert stats["success_rate"] == 0.0
    
    def test_circuit_manager(self):
        """Test circuit breaker manager."""
        breaker1 = circuit_manager.get_breaker("test1")
        breaker2 = circuit_manager.get_breaker("test1")  # Same name
        breaker3 = circuit_manager.get_breaker("test2")  # Different name
        
        assert breaker1 is breaker2  # Same instance
        assert breaker1 is not breaker3  # Different instances
        
        stats = circuit_manager.get_all_stats()
        assert "test1" in stats
        assert "test2" in stats


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    @pytest.fixture
    def recovery_config(self):
        """Recovery configuration for testing."""
        return RecoveryConfig(
            max_retries=2,
            base_delay=0.1,
            max_delay=1.0,
            backoff_multiplier=2.0
        )
    
    @pytest.fixture
    def recovery_manager(self, recovery_config):
        """Recovery manager for testing."""
        return ErrorRecoveryManager(recovery_config)
    
    @pytest.mark.asyncio
    async def test_successful_retry(self, recovery_manager):
        """Test successful operation after retry."""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkException("Temporary failure")
            return "success"
        
        result = await recovery_manager.handle_error(
            NetworkException("Temporary failure"),
            "test_operation",
            flaky_func
        )
        
        assert result == "success"
        assert call_count == 2
        assert recovery_manager._recovery_stats["recovered_errors"] == 1
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, recovery_manager):
        """Test retry exhaustion leads to failure."""
        async def always_failing_func():
            raise NetworkException("Persistent failure")
        
        with pytest.raises(NetworkException):
            await recovery_manager.handle_error(
                NetworkException("Persistent failure"),
                "test_operation",
                always_failing_func
            )
        
        assert recovery_manager._recovery_stats["failed_recoveries"] == 1
    
    @pytest.mark.asyncio
    async def test_fallback_strategy(self, recovery_manager):
        """Test fallback strategy usage."""
        async def fallback_func():
            return "fallback_result"
        
        recovery_manager.register_fallback("test_operation", fallback_func)
        
        result = await recovery_manager.handle_error(
            AIServiceException("Service unavailable"),
            "test_operation",
            Mock()  # Original function won't be called
        )
        
        assert result == "fallback_result"
        assert recovery_manager._recovery_stats["fallback_uses"] == 1
    
    @pytest.mark.asyncio
    async def test_skip_strategy(self, recovery_manager):
        """Test skip strategy for low-severity errors."""
        low_severity_error = ScraperBaseException(
            "Minor issue",
            severity=ErrorSeverity.LOW
        )
        
        result = await recovery_manager.handle_error(
            low_severity_error,
            "scrape_operation",
            Mock()
        )
        
        assert result["success"] is False
        assert result["skipped"] is True
    
    @pytest.mark.asyncio
    async def test_with_recovery_decorator(self):
        """Test recovery decorator functionality."""
        call_count = 0
        
        @with_recovery("decorated_operation")
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkException("Temporary failure")
            return "decorated_success"
        
        result = await decorated_func()
        assert result == "decorated_success"
        assert call_count == 2
    
    def test_recovery_stats(self, recovery_manager):
        """Test recovery statistics tracking."""
        stats = recovery_manager.get_stats()
        
        assert "total_errors" in stats
        assert "recovered_errors" in stats
        assert "recovery_rate" in stats
        assert stats["recovery_rate"] == 0.0  # No errors yet


class TestErrorNotifications:
    """Test error notification system."""
    
    @pytest.fixture
    def notification_config(self):
        """Notification configuration for testing."""
        return NotificationConfig(
            enabled_channels={NotificationChannel.LOG, NotificationChannel.CONSOLE},
            rate_limit_window=60,
            max_notifications_per_window=5
        )
    
    @pytest.fixture
    def notification_system(self, notification_config):
        """Notification system for testing."""
        return ErrorNotificationSystem(notification_config)
    
    @pytest.mark.asyncio
    async def test_basic_notification(self, notification_system):
        """Test basic error notification."""
        exception = WebDriverException("Driver crashed")
        
        result = await notification_system.notify_error(
            exception,
            "scraper_component",
            context={"url": "https://example.com"}
        )
        
        assert result is True
        stats = notification_system.get_stats()
        assert stats["total_notifications"] == 1
        assert stats["notifications_sent"] == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, notification_system):
        """Test notification rate limiting."""
        exception = NetworkException("Connection failed")
        
        # Send notifications up to limit
        for i in range(5):
            result = await notification_system.notify_error(
                exception, "network_component"
            )
            assert result is True
        
        # Next notification should be rate limited
        result = await notification_system.notify_error(
            exception, "network_component"
        )
        assert result is False
        
        stats = notification_system.get_stats()
        assert stats["notifications_rate_limited"] == 1
    
    @pytest.mark.asyncio
    async def test_severity_priority_mapping(self, notification_system):
        """Test severity to priority mapping."""
        critical_exception = ScraperBaseException(
            "Critical failure",
            severity=ErrorSeverity.CRITICAL
        )
        
        notification = notification_system._create_notification(
            critical_exception, "test_component", None, None, False, False
        )
        
        assert notification.severity == ErrorSeverity.CRITICAL
        assert notification.priority == NotificationPriority.URGENT
    
    @pytest.mark.asyncio
    async def test_notification_aggregation(self, notification_system):
        """Test error notification aggregation."""
        notification_system.config.aggregate_similar_errors = True
        exception = DataValidationException("Validation failed")
        
        # First notification should be sent
        result1 = await notification_system.notify_error(
            exception, "data_component"
        )
        assert result1 is True
        
        # Second similar notification should be aggregated
        result2 = await notification_system.notify_error(
            exception, "data_component"
        )
        assert result2 is True  # Returns True but is aggregated
        
        stats = notification_system.get_stats()
        assert stats["notifications_aggregated"] >= 1
    
    @pytest.mark.asyncio
    async def test_escalation_trigger(self, notification_system):
        """Test error escalation triggering."""
        notification_system.config.escalation_threshold = 2
        notification_system.config.escalation_window = 60
        
        high_priority_exception = ScraperBaseException(
            "High priority error",
            severity=ErrorSeverity.HIGH
        )
        
        # Send high priority errors to trigger escalation
        for i in range(3):
            await notification_system.notify_error(
                high_priority_exception, f"component_{i}"
            )
        
        stats = notification_system.get_stats()
        assert stats["escalations_triggered"] >= 1
    
    def test_notification_creation(self, notification_system):
        """Test notification object creation."""
        exception = AIServiceException(
            "API failed",
            service_name="gemini",
            api_error_code="TIMEOUT"
        )
        
        notification = notification_system._create_notification(
            exception, "ai_component", {"request_id": "123"}, "corr-456", True, False
        )
        
        assert notification.error_type == "AIServiceException"
        assert notification.message == "API failed"
        assert notification.source_component == "ai_component"
        assert notification.correlation_id == "corr-456"
        assert notification.recovery_attempted is True
        assert notification.recovery_successful is False
        assert "service_name" in notification.context
        assert "request_id" in notification.context
    
    @pytest.mark.asyncio
    async def test_global_notify_function(self):
        """Test global notify_error function."""
        exception = NetworkException("Network timeout")
        
        result = await notify_error(
            exception,
            "global_component",
            context={"timeout": 30},
            correlation_id="test-123"
        )
        
        # Should succeed with default log channel
        assert result is True


class TestIntegration:
    """Integration tests for error handling components."""
    
    @pytest.mark.asyncio
    async def test_full_error_handling_flow(self):
        """Test complete error handling flow with all components."""
        # Setup components
        recovery_config = RecoveryConfig(max_retries=2, base_delay=0.1)
        recovery_manager = ErrorRecoveryManager(recovery_config)
        
        notification_config = NotificationConfig(
            enabled_channels={NotificationChannel.LOG}
        )
        notification_system = ErrorNotificationSystem(notification_config)
        
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise NetworkException("Temporary network issue")
            return "operation_success"
        
        # Simulate error handling flow
        try:
            result = await recovery_manager.handle_error(
                NetworkException("Initial failure"),
                "integration_test",
                flaky_operation
            )
            
            # Should succeed after retries
            assert result == "operation_success"
            
            # Notify about the recovery
            await notification_system.notify_error(
                NetworkException("Initial failure"),
                "integration_test",
                recovery_attempted=True,
                recovery_successful=True
            )
            
        except Exception as e:
            # If recovery fails, notify about failure
            await notification_system.notify_error(
                e,
                "integration_test",
                recovery_attempted=True,
                recovery_successful=False
            )
            raise
        
        # Verify statistics
        recovery_stats = recovery_manager.get_stats()
        notification_stats = notification_system.get_stats()
        
        assert recovery_stats["recovered_errors"] == 1
        assert notification_stats["notifications_sent"] == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_recovery(self):
        """Test circuit breaker integration with recovery system."""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.5
        )
        
        recovery_config = RecoveryConfig(
            max_retries=1,
            circuit_breaker_config=circuit_config
        )
        
        recovery_manager = ErrorRecoveryManager(recovery_config)
        
        async def failing_operation():
            raise NetworkException("Service unavailable")
        
        # First few attempts should fail and open circuit
        for i in range(3):
            with pytest.raises((NetworkException, CircuitBreakerError)):
                await recovery_manager.handle_error(
                    NetworkException("Service unavailable"),
                    "circuit_test",
                    failing_operation
                )
        
        # Verify circuit breaker is being used
        breaker = circuit_manager.get_breaker("recovery_circuit_test")
        assert breaker.state in [CircuitState.OPEN, CircuitState.HALF_OPEN]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])