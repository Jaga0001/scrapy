"""
Session manager utility for the Streamlit dashboard.

This module provides session state management, user preferences,
and dashboard configuration persistence.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import streamlit as st

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages Streamlit session state and user preferences.
    """
    
    def __init__(self):
        """Initialize the session manager."""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize default session state variables."""
        defaults = {
            # Dashboard settings
            'auto_refresh': True,
            'refresh_interval': 5,
            'theme': 'light',
            'page_size': 25,
            
            # User preferences
            'default_job_priority': 5,
            'default_export_format': 'csv',
            'show_advanced_options': False,
            
            # Navigation state
            'current_page': 'Overview',
            'last_visited_pages': [],
            
            # Data filters
            'job_status_filter': ['running', 'pending'],
            'min_confidence_filter': 0.0,
            'min_quality_filter': 0.0,
            'date_range_filter': (datetime.now() - timedelta(days=7), datetime.now()),
            
            # UI state
            'selected_jobs': [],
            'selected_data_records': [],
            'expanded_sections': {},
            
            # Cache and performance
            'last_refresh': datetime.now(),
            'cache_enabled': True,
            'performance_mode': False,
            
            # Notifications
            'show_notifications': True,
            'notification_level': 'info',
            'dismissed_notifications': [],
            
            # Dashboard layout
            'sidebar_expanded': True,
            'show_metrics_sidebar': True,
            'chart_height': 300,
            
            # Export settings
            'export_include_metadata': True,
            'export_max_records': 10000,
            'export_compression': False
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from session state.
        
        Args:
            key: Session state key
            default: Default value if key doesn't exist
            
        Returns:
            Session state value or default
        """
        return st.session_state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in session state.
        
        Args:
            key: Session state key
            value: Value to set
        """
        st.session_state[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple session state values.
        
        Args:
            updates: Dictionary of key-value pairs to update
        """
        for key, value in updates.items():
            st.session_state[key] = value
    
    def delete(self, key: str) -> None:
        """
        Delete a key from session state.
        
        Args:
            key: Session state key to delete
        """
        if key in st.session_state:
            del st.session_state[key]
    
    def clear_filters(self) -> None:
        """Clear all filter settings."""
        filter_keys = [
            'job_status_filter',
            'min_confidence_filter',
            'min_quality_filter',
            'date_range_filter'
        ]
        
        for key in filter_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # Reinitialize with defaults
        self._initialize_session_state()
    
    def save_user_preferences(self) -> bool:
        """
        Save user preferences to persistent storage.
        
        Returns:
            True if preferences were saved successfully
        """
        try:
            preferences = {
                'auto_refresh': self.get('auto_refresh'),
                'refresh_interval': self.get('refresh_interval'),
                'theme': self.get('theme'),
                'page_size': self.get('page_size'),
                'default_job_priority': self.get('default_job_priority'),
                'default_export_format': self.get('default_export_format'),
                'show_advanced_options': self.get('show_advanced_options'),
                'show_notifications': self.get('show_notifications'),
                'notification_level': self.get('notification_level'),
                'sidebar_expanded': self.get('sidebar_expanded'),
                'show_metrics_sidebar': self.get('show_metrics_sidebar'),
                'chart_height': self.get('chart_height'),
                'export_include_metadata': self.get('export_include_metadata'),
                'export_max_records': self.get('export_max_records'),
                'export_compression': self.get('export_compression'),
                'cache_enabled': self.get('cache_enabled'),
                'performance_mode': self.get('performance_mode')
            }
            
            # In a real implementation, this would save to a database or file
            # For now, we'll store in session state
            st.session_state['saved_preferences'] = preferences
            st.session_state['preferences_saved_at'] = datetime.now()
            
            self.logger.info("User preferences saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving user preferences: {e}")
            return False
    
    def load_user_preferences(self) -> bool:
        """
        Load user preferences from persistent storage.
        
        Returns:
            True if preferences were loaded successfully
        """
        try:
            saved_preferences = st.session_state.get('saved_preferences')
            
            if saved_preferences:
                self.update(saved_preferences)
                self.logger.info("User preferences loaded successfully")
                return True
            else:
                self.logger.info("No saved preferences found, using defaults")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading user preferences: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        try:
            # Clear all session state
            for key in list(st.session_state.keys()):
                if not key.startswith('_'):  # Keep Streamlit internal keys
                    del st.session_state[key]
            
            # Reinitialize with defaults
            self._initialize_session_state()
            
            self.logger.info("Session state reset to defaults")
            
        except Exception as e:
            self.logger.error(f"Error resetting to defaults: {e}")
    
    def add_to_history(self, page: str) -> None:
        """
        Add a page to the navigation history.
        
        Args:
            page: Page name to add to history
        """
        try:
            history = self.get('last_visited_pages', [])
            
            # Remove if already in history
            if page in history:
                history.remove(page)
            
            # Add to beginning
            history.insert(0, page)
            
            # Keep only last 10 pages
            history = history[:10]
            
            self.set('last_visited_pages', history)
            
        except Exception as e:
            self.logger.error(f"Error adding to history: {e}")
    
    def get_navigation_history(self) -> list:
        """
        Get navigation history.
        
        Returns:
            List of recently visited pages
        """
        return self.get('last_visited_pages', [])
    
    def add_notification(self, message: str, level: str = 'info', persistent: bool = False) -> None:
        """
        Add a notification to the session.
        
        Args:
            message: Notification message
            level: Notification level (info, warning, error, success)
            persistent: Whether notification persists across page refreshes
        """
        try:
            notifications = self.get('notifications', [])
            
            notification = {
                'id': f"notif_{len(notifications)}_{datetime.now().timestamp()}",
                'message': message,
                'level': level,
                'timestamp': datetime.now(),
                'persistent': persistent,
                'dismissed': False
            }
            
            notifications.append(notification)
            
            # Keep only last 50 notifications
            notifications = notifications[-50:]
            
            self.set('notifications', notifications)
            
        except Exception as e:
            self.logger.error(f"Error adding notification: {e}")
    
    def get_notifications(self, include_dismissed: bool = False) -> list:
        """
        Get current notifications.
        
        Args:
            include_dismissed: Whether to include dismissed notifications
            
        Returns:
            List of notification dictionaries
        """
        try:
            notifications = self.get('notifications', [])
            
            if not include_dismissed:
                notifications = [n for n in notifications if not n.get('dismissed', False)]
            
            return notifications
            
        except Exception as e:
            self.logger.error(f"Error getting notifications: {e}")
            return []
    
    def dismiss_notification(self, notification_id: str) -> None:
        """
        Dismiss a notification.
        
        Args:
            notification_id: ID of notification to dismiss
        """
        try:
            notifications = self.get('notifications', [])
            
            for notification in notifications:
                if notification.get('id') == notification_id:
                    notification['dismissed'] = True
                    break
            
            self.set('notifications', notifications)
            
            # Also add to dismissed list
            dismissed = self.get('dismissed_notifications', [])
            if notification_id not in dismissed:
                dismissed.append(notification_id)
                self.set('dismissed_notifications', dismissed)
            
        except Exception as e:
            self.logger.error(f"Error dismissing notification: {e}")
    
    def clear_notifications(self) -> None:
        """Clear all notifications."""
        self.set('notifications', [])
    
    def set_expanded_section(self, section_id: str, expanded: bool) -> None:
        """
        Set the expanded state of a section.
        
        Args:
            section_id: Section identifier
            expanded: Whether section is expanded
        """
        expanded_sections = self.get('expanded_sections', {})
        expanded_sections[section_id] = expanded
        self.set('expanded_sections', expanded_sections)
    
    def is_section_expanded(self, section_id: str, default: bool = False) -> bool:
        """
        Check if a section is expanded.
        
        Args:
            section_id: Section identifier
            default: Default expanded state
            
        Returns:
            True if section is expanded
        """
        expanded_sections = self.get('expanded_sections', {})
        return expanded_sections.get(section_id, default)
    
    def update_last_refresh(self) -> None:
        """Update the last refresh timestamp."""
        self.set('last_refresh', datetime.now())
    
    def get_time_since_refresh(self) -> timedelta:
        """
        Get time since last refresh.
        
        Returns:
            Time delta since last refresh
        """
        last_refresh = self.get('last_refresh', datetime.now())
        return datetime.now() - last_refresh
    
    def should_auto_refresh(self) -> bool:
        """
        Check if auto refresh should occur.
        
        Returns:
            True if auto refresh should occur
        """
        if not self.get('auto_refresh', True):
            return False
        
        refresh_interval = self.get('refresh_interval', 5)
        time_since_refresh = self.get_time_since_refresh()
        
        return time_since_refresh.total_seconds() >= refresh_interval
    
    def get_filter_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current filter settings.
        
        Returns:
            Dictionary containing filter summary
        """
        return {
            'job_status_filter': self.get('job_status_filter', []),
            'min_confidence_filter': self.get('min_confidence_filter', 0.0),
            'min_quality_filter': self.get('min_quality_filter', 0.0),
            'date_range_filter': self.get('date_range_filter'),
            'active_filters_count': self._count_active_filters()
        }
    
    def _count_active_filters(self) -> int:
        """Count the number of active filters."""
        count = 0
        
        # Job status filter
        status_filter = self.get('job_status_filter', [])
        if status_filter and len(status_filter) < 5:  # Less than all statuses
            count += 1
        
        # Confidence filter
        if self.get('min_confidence_filter', 0.0) > 0:
            count += 1
        
        # Quality filter
        if self.get('min_quality_filter', 0.0) > 0:
            count += 1
        
        # Date range filter (if not default 7 days)
        date_range = self.get('date_range_filter')
        if date_range and isinstance(date_range, tuple):
            start_date, end_date = date_range
            if (end_date - start_date).days != 7:
                count += 1
        
        return count
    
    def export_session_state(self) -> str:
        """
        Export session state as JSON string.
        
        Returns:
            JSON string of exportable session state
        """
        try:
            exportable_keys = [
                'auto_refresh', 'refresh_interval', 'theme', 'page_size',
                'default_job_priority', 'default_export_format', 'show_advanced_options',
                'show_notifications', 'notification_level', 'sidebar_expanded',
                'show_metrics_sidebar', 'chart_height', 'export_include_metadata',
                'export_max_records', 'export_compression', 'cache_enabled',
                'performance_mode'
            ]
            
            export_data = {}
            for key in exportable_keys:
                if key in st.session_state:
                    value = st.session_state[key]
                    # Convert datetime objects to strings
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    elif isinstance(value, tuple) and len(value) == 2:
                        # Handle date range tuples
                        if all(isinstance(d, datetime) for d in value):
                            value = [d.isoformat() for d in value]
                    export_data[key] = value
            
            return json.dumps(export_data, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error exporting session state: {e}")
            return "{}"
    
    def import_session_state(self, json_data: str) -> bool:
        """
        Import session state from JSON string.
        
        Args:
            json_data: JSON string containing session state
            
        Returns:
            True if import was successful
        """
        try:
            import_data = json.loads(json_data)
            
            for key, value in import_data.items():
                # Convert ISO datetime strings back to datetime objects
                if isinstance(value, str) and 'T' in value:
                    try:
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        pass  # Not a datetime string
                elif isinstance(value, list) and len(value) == 2:
                    # Handle date range lists
                    try:
                        if all(isinstance(d, str) and 'T' in d for d in value):
                            value = tuple(datetime.fromisoformat(d.replace('Z', '+00:00')) for d in value)
                    except ValueError:
                        pass  # Not datetime strings
                
                st.session_state[key] = value
            
            self.logger.info("Session state imported successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing session state: {e}")
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dictionary containing session information
        """
        try:
            return {
                'session_keys_count': len(st.session_state.keys()),
                'last_refresh': self.get('last_refresh'),
                'time_since_refresh': self.get_time_since_refresh().total_seconds(),
                'auto_refresh_enabled': self.get('auto_refresh'),
                'refresh_interval': self.get('refresh_interval'),
                'current_page': self.get('current_page'),
                'navigation_history_length': len(self.get('last_visited_pages', [])),
                'active_filters_count': self._count_active_filters(),
                'notifications_count': len(self.get_notifications()),
                'cache_enabled': self.get('cache_enabled'),
                'performance_mode': self.get('performance_mode')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting session info: {e}")
            return {}