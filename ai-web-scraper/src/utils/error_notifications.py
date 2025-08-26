"""
Error notification system with severity-based alerting.

This module provides a comprehensive notification system that sends
alerts based on error severity levels and configurable thresholds.
"""

import asyncio
import json
import logging
import smtplib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum

from .exceptions import ScraperBaseException, ErrorSeverity
from .logger import get_logger

logger = get_logger(__name__)


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"
    CONSOLE = "console"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationConfig:
    """Configuration for notification behavior."""
    # Channel settings
    enabled_channels: Set[NotificationChannel] = field(default_factory=lambda: {NotificationChannel.LOG})
    
    # Severity mapping to priority
    severity_priority_map: Dict[ErrorSeverity, NotificationPriority] = field(default_factory=lambda: {
        ErrorSeverity.LOW: NotificationPriority.LOW,
        ErrorSeverity.MEDIUM: NotificationPriority.NORMAL,
        ErrorSeverity.HIGH: NotificationPriority.HIGH,
        ErrorSeverity.CRITICAL: NotificationPriority.URGENT
    })
    
    # Rate limiting
    rate_limit_window: int = 300  # 5 minutes
    max_notifications_per_window: int = 10
    
    # Aggregation settings
    aggregate_similar_errors: bool = True
    aggregation_window: int = 60  # 1 minute
    
    # Email settings
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    
    # Webhook settings
    webhook_urls: List[str] = field(default_factory=list)
    webhook_timeout: float = 10.0
    
    # Escalation settings
    escalation_threshold: int = 5  # Number of high/critical errors before escalation
    escalation_window: int = 600  # 10 minutes
    escalation_channels: Set[NotificationChannel] = field(default_factory=lambda: {NotificationChannel.EMAIL})


@dataclass
class ErrorNotification:
    """Represents an error notification."""
    error_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    priority: NotificationPriority
    timestamp: datetime
    context: Dict[str, Any]
    source_component: str
    correlation_id: Optional[str] = None
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False


class NotificationChannel_ABC(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    async def send_notification(self, notification: ErrorNotification) -> bool:
        """Send a notification through this channel."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this channel is available."""
        pass


class EmailNotificationChannel(NotificationChannel_ABC):
    """Email notification channel."""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send_notification(self, notification: ErrorNotification) -> bool:
        """Send email notification."""
        if not self.is_available():
            logger.warning("Email notification channel not properly configured")
            return False
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_from
            msg['To'] = ', '.join(self.config.email_to)
            msg['Subject'] = f"[{notification.priority.value.upper()}] {notification.error_type}: {notification.message[:50]}..."
            
            # Create email body
            body = self._create_email_body(notification)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            await asyncio.to_thread(self._send_email, msg)
            
            logger.info(
                f"Email notification sent for error {notification.error_id}",
                extra={"notification_id": notification.error_id, "channel": "email"}
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_email(self, msg: MIMEMultipart) -> None:
        """Send email using SMTP."""
        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            if self.config.smtp_use_tls:
                server.starttls()
            
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)
            
            server.send_message(msg)
    
    def _create_email_body(self, notification: ErrorNotification) -> str:
        """Create HTML email body."""
        priority_colors = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.NORMAL: "#ffc107",
            NotificationPriority.HIGH: "#fd7e14",
            NotificationPriority.URGENT: "#dc3545"
        }
        
        color = priority_colors.get(notification.priority, "#6c757d")
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{notification.priority.value.upper()} - {notification.error_type}</h2>
                </div>
                
                <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
                    <h3>Error Details</h3>
                    <p><strong>Message:</strong> {notification.message}</p>
                    <p><strong>Severity:</strong> {notification.severity.value}</p>
                    <p><strong>Component:</strong> {notification.source_component}</p>
                    <p><strong>Timestamp:</strong> {notification.timestamp.isoformat()}</p>
                    
                    {f'<p><strong>Correlation ID:</strong> {notification.correlation_id}</p>' if notification.correlation_id else ''}
                    
                    <h3>Context Information</h3>
                    <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto;">
{json.dumps(notification.context, indent=2)}
                    </pre>
                    
                    {f'''
                    <h3>Stack Trace</h3>
                    <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; font-size: 12px;">
{notification.stack_trace}
                    </pre>
                    ''' if notification.stack_trace else ''}
                    
                    <h3>Recovery Status</h3>
                    <p><strong>Recovery Attempted:</strong> {'Yes' if notification.recovery_attempted else 'No'}</p>
                    {f'<p><strong>Recovery Successful:</strong> {"Yes" if notification.recovery_successful else "No"}</p>' if notification.recovery_attempted else ''}
                </div>
            </div>
        </body>
        </html>
        """
    
    def is_available(self) -> bool:
        """Check if email configuration is complete."""
        return all([
            self.config.smtp_host,
            self.config.email_from,
            self.config.email_to
        ])


class WebhookNotificationChannel(NotificationChannel_ABC):
    """Webhook notification channel."""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send_notification(self, notification: ErrorNotification) -> bool:
        """Send webhook notification."""
        if not self.is_available():
            logger.warning("Webhook notification channel not configured")
            return False
        
        payload = {
            "error_id": notification.error_id,
            "error_type": notification.error_type,
            "message": notification.message,
            "severity": notification.severity.value,
            "priority": notification.priority.value,
            "timestamp": notification.timestamp.isoformat(),
            "context": notification.context,
            "source_component": notification.source_component,
            "correlation_id": notification.correlation_id,
            "recovery_attempted": notification.recovery_attempted,
            "recovery_successful": notification.recovery_successful
        }
        
        success_count = 0
        for webhook_url in self.config.webhook_urls:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.config.webhook_timeout)
                    ) as response:
                        if response.status < 400:
                            success_count += 1
                            logger.info(
                                f"Webhook notification sent to {webhook_url}",
                                extra={"notification_id": notification.error_id, "webhook_url": webhook_url}
                            )
                        else:
                            logger.warning(f"Webhook notification failed: HTTP {response.status}")
                            
            except Exception as e:
                logger.error(f"Failed to send webhook notification to {webhook_url}: {e}")
        
        return success_count > 0
    
    def is_available(self) -> bool:
        """Check if webhook URLs are configured."""
        return len(self.config.webhook_urls) > 0


class LogNotificationChannel(NotificationChannel_ABC):
    """Log-based notification channel."""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send_notification(self, notification: ErrorNotification) -> bool:
        """Log the notification."""
        log_level = {
            NotificationPriority.LOW: logging.INFO,
            NotificationPriority.NORMAL: logging.WARNING,
            NotificationPriority.HIGH: logging.ERROR,
            NotificationPriority.URGENT: logging.CRITICAL
        }.get(notification.priority, logging.WARNING)
        
        logger.log(
            log_level,
            f"ERROR NOTIFICATION: {notification.error_type} - {notification.message}",
            extra={
                "notification_id": notification.error_id,
                "error_type": notification.error_type,
                "severity": notification.severity.value,
                "priority": notification.priority.value,
                "source_component": notification.source_component,
                "context": notification.context,
                "correlation_id": notification.correlation_id,
                "recovery_attempted": notification.recovery_attempted,
                "recovery_successful": notification.recovery_successful
            }
        )
        return True
    
    def is_available(self) -> bool:
        """Log channel is always available."""
        return True


class ConsoleNotificationChannel(NotificationChannel_ABC):
    """Console notification channel."""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send_notification(self, notification: ErrorNotification) -> bool:
        """Print notification to console."""
        priority_symbols = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.NORMAL: "⚠️",
            NotificationPriority.HIGH: "🚨",
            NotificationPriority.URGENT: "🔥"
        }
        
        symbol = priority_symbols.get(notification.priority, "❗")
        
        print(f"\n{symbol} ERROR NOTIFICATION [{notification.priority.value.upper()}]")
        print(f"Type: {notification.error_type}")
        print(f"Message: {notification.message}")
        print(f"Component: {notification.source_component}")
        print(f"Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if notification.correlation_id:
            print(f"Correlation ID: {notification.correlation_id}")
        print(f"Recovery: {'Attempted' if notification.recovery_attempted else 'Not attempted'}")
        if notification.recovery_attempted:
            print(f"Recovery Success: {'Yes' if notification.recovery_successful else 'No'}")
        print("-" * 50)
        
        return True
    
    def is_available(self) -> bool:
        """Console channel is always available."""
        return True


class ErrorNotificationSystem:
    """
    Comprehensive error notification system.
    
    Manages error notifications with rate limiting, aggregation,
    and multiple delivery channels.
    """
    
    def __init__(self, config: NotificationConfig = None):
        """Initialize notification system."""
        self.config = config or NotificationConfig()
        self.channels = self._initialize_channels()
        
        # Rate limiting and aggregation tracking
        self._notification_history: List[ErrorNotification] = []
        self._aggregated_errors: Dict[str, List[ErrorNotification]] = {}
        self._last_cleanup = time.time()
        
        # Statistics
        self._stats = {
            "total_notifications": 0,
            "notifications_sent": 0,
            "notifications_rate_limited": 0,
            "notifications_aggregated": 0,
            "escalations_triggered": 0
        }
    
    def _initialize_channels(self) -> Dict[NotificationChannel, NotificationChannel_ABC]:
        """Initialize notification channels."""
        channels = {}
        
        if NotificationChannel.EMAIL in self.config.enabled_channels:
            channels[NotificationChannel.EMAIL] = EmailNotificationChannel(self.config)
        
        if NotificationChannel.WEBHOOK in self.config.enabled_channels:
            channels[NotificationChannel.WEBHOOK] = WebhookNotificationChannel(self.config)
        
        if NotificationChannel.LOG in self.config.enabled_channels:
            channels[NotificationChannel.LOG] = LogNotificationChannel(self.config)
        
        if NotificationChannel.CONSOLE in self.config.enabled_channels:
            channels[NotificationChannel.CONSOLE] = ConsoleNotificationChannel(self.config)
        
        return channels
    
    async def notify_error(
        self,
        exception: Exception,
        source_component: str,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        recovery_attempted: bool = False,
        recovery_successful: bool = False
    ) -> bool:
        """
        Send error notification.
        
        Args:
            exception: The exception that occurred
            source_component: Component where the error occurred
            context: Additional context information
            correlation_id: Request correlation ID
            recovery_attempted: Whether recovery was attempted
            recovery_successful: Whether recovery was successful
            
        Returns:
            True if notification was sent successfully
        """
        self._stats["total_notifications"] += 1
        
        # Create notification
        notification = self._create_notification(
            exception, source_component, context, correlation_id,
            recovery_attempted, recovery_successful
        )
        
        # Check rate limiting
        if self._is_rate_limited():
            self._stats["notifications_rate_limited"] += 1
            logger.debug(f"Notification rate limited for error {notification.error_id}")
            return False
        
        # Check aggregation
        if self.config.aggregate_similar_errors:
            if self._should_aggregate(notification):
                self._stats["notifications_aggregated"] += 1
                logger.debug(f"Notification aggregated for error {notification.error_id}")
                return True
        
        # Send notification
        success = await self._send_notification(notification)
        
        if success:
            self._stats["notifications_sent"] += 1
            self._notification_history.append(notification)
            
            # Check for escalation
            await self._check_escalation()
        
        # Cleanup old data
        self._cleanup_old_data()
        
        return success
    
    def _create_notification(
        self,
        exception: Exception,
        source_component: str,
        context: Optional[Dict[str, Any]],
        correlation_id: Optional[str],
        recovery_attempted: bool,
        recovery_successful: bool
    ) -> ErrorNotification:
        """Create notification from exception."""
        import traceback
        import uuid
        
        # Determine severity and priority
        if isinstance(exception, ScraperBaseException):
            severity = exception.severity
            error_context = {**(context or {}), **exception.context}
        else:
            severity = ErrorSeverity.MEDIUM
            error_context = context or {}
        
        priority = self.config.severity_priority_map.get(severity, NotificationPriority.NORMAL)
        
        return ErrorNotification(
            error_id=str(uuid.uuid4()),
            error_type=type(exception).__name__,
            message=str(exception),
            severity=severity,
            priority=priority,
            timestamp=datetime.utcnow(),
            context=error_context,
            source_component=source_component,
            correlation_id=correlation_id,
            stack_trace=traceback.format_exc(),
            recovery_attempted=recovery_attempted,
            recovery_successful=recovery_successful
        )
    
    def _is_rate_limited(self) -> bool:
        """Check if notifications are rate limited."""
        current_time = time.time()
        window_start = current_time - self.config.rate_limit_window
        
        recent_notifications = [
            n for n in self._notification_history
            if n.timestamp.timestamp() > window_start
        ]
        
        return len(recent_notifications) >= self.config.max_notifications_per_window
    
    def _should_aggregate(self, notification: ErrorNotification) -> bool:
        """Check if notification should be aggregated."""
        aggregation_key = f"{notification.error_type}:{notification.source_component}"
        current_time = time.time()
        
        if aggregation_key not in self._aggregated_errors:
            self._aggregated_errors[aggregation_key] = []
        
        # Remove old aggregated errors
        window_start = current_time - self.config.aggregation_window
        self._aggregated_errors[aggregation_key] = [
            n for n in self._aggregated_errors[aggregation_key]
            if n.timestamp.timestamp() > window_start
        ]
        
        # Add current notification to aggregation
        self._aggregated_errors[aggregation_key].append(notification)
        
        # Return True if this should be aggregated (not the first in window)
        return len(self._aggregated_errors[aggregation_key]) > 1
    
    async def _send_notification(self, notification: ErrorNotification) -> bool:
        """Send notification through all available channels."""
        success_count = 0
        total_channels = len(self.channels)
        
        for channel_type, channel in self.channels.items():
            if channel.is_available():
                try:
                    if await channel.send_notification(notification):
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel_type.value}: {e}")
            else:
                logger.warning(f"Notification channel {channel_type.value} is not available")
        
        return success_count > 0
    
    async def _check_escalation(self) -> None:
        """Check if error escalation is needed."""
        current_time = time.time()
        window_start = current_time - self.config.escalation_window
        
        high_priority_errors = [
            n for n in self._notification_history
            if (n.timestamp.timestamp() > window_start and 
                n.priority in [NotificationPriority.HIGH, NotificationPriority.URGENT])
        ]
        
        if len(high_priority_errors) >= self.config.escalation_threshold:
            await self._trigger_escalation(high_priority_errors)
    
    async def _trigger_escalation(self, errors: List[ErrorNotification]) -> None:
        """Trigger error escalation."""
        self._stats["escalations_triggered"] += 1
        
        escalation_notification = ErrorNotification(
            error_id=f"escalation_{int(time.time())}",
            error_type="SystemEscalation",
            message=f"Escalation triggered: {len(errors)} high-priority errors in {self.config.escalation_window}s",
            severity=ErrorSeverity.CRITICAL,
            priority=NotificationPriority.URGENT,
            timestamp=datetime.utcnow(),
            context={
                "escalation_threshold": self.config.escalation_threshold,
                "escalation_window": self.config.escalation_window,
                "error_count": len(errors),
                "error_types": list(set(e.error_type for e in errors)),
                "affected_components": list(set(e.source_component for e in errors))
            },
            source_component="notification_system"
        )
        
        # Send escalation through escalation channels only
        for channel_type in self.config.escalation_channels:
            if channel_type in self.channels:
                channel = self.channels[channel_type]
                if channel.is_available():
                    try:
                        await channel.send_notification(escalation_notification)
                        logger.critical(f"Escalation notification sent via {channel_type.value}")
                    except Exception as e:
                        logger.error(f"Failed to send escalation via {channel_type.value}: {e}")
    
    def _cleanup_old_data(self) -> None:
        """Clean up old notification data."""
        current_time = time.time()
        
        # Only cleanup every 5 minutes
        if current_time - self._last_cleanup < 300:
            return
        
        # Remove old notifications (keep 24 hours)
        cutoff_time = current_time - 86400
        self._notification_history = [
            n for n in self._notification_history
            if n.timestamp.timestamp() > cutoff_time
        ]
        
        # Clean up aggregated errors
        for key in list(self._aggregated_errors.keys()):
            self._aggregated_errors[key] = [
                n for n in self._aggregated_errors[key]
                if n.timestamp.timestamp() > cutoff_time
            ]
            if not self._aggregated_errors[key]:
                del self._aggregated_errors[key]
        
        self._last_cleanup = current_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification system statistics."""
        return {
            **self._stats,
            "active_channels": len([c for c in self.channels.values() if c.is_available()]),
            "total_channels": len(self.channels),
            "recent_notifications": len(self._notification_history),
            "aggregated_error_types": len(self._aggregated_errors)
        }
    
    def reset_stats(self) -> None:
        """Reset notification statistics."""
        self._stats = {
            "total_notifications": 0,
            "notifications_sent": 0,
            "notifications_rate_limited": 0,
            "notifications_aggregated": 0,
            "escalations_triggered": 0
        }


# Global notification system
notification_system = ErrorNotificationSystem()


async def notify_error(
    exception: Exception,
    source_component: str,
    context: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    recovery_attempted: bool = False,
    recovery_successful: bool = False
) -> bool:
    """
    Convenience function to send error notification.
    
    Args:
        exception: The exception that occurred
        source_component: Component where the error occurred
        context: Additional context information
        correlation_id: Request correlation ID
        recovery_attempted: Whether recovery was attempted
        recovery_successful: Whether recovery was successful
        
    Returns:
        True if notification was sent successfully
    """
    return await notification_system.notify_error(
        exception, source_component, context, correlation_id,
        recovery_attempted, recovery_successful
    )