"""
Error Logging and Monitoring System
Provides comprehensive error logging, monitoring, and security event tracking
"""

import os
import json
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum


class LogLevel(Enum):
    """Log levels for different types of events"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"


class SecurityEvent(Enum):
    """Types of security events to track"""
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    REGISTRATION_ATTEMPT = "registration_attempt"
    REGISTRATION_SUCCESS = "registration_success"
    REGISTRATION_FAILURE = "registration_failure"
    PASSWORD_RESET_ATTEMPT = "password_reset_attempt"
    PASSWORD_RESET_SUCCESS = "password_reset_success"
    PASSWORD_RESET_FAILURE = "password_reset_failure"
    INVALID_INPUT = "invalid_input"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    CACHE_CORRUPTION = "cache_corruption"
    ENCRYPTION_ERROR = "encryption_error"


class ErrorLogger:
    """Comprehensive error logging and monitoring system"""
    
    def __init__(self, log_dir: str = "logs", max_log_size: int = 10 * 1024 * 1024):  # 10MB
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_log_size = max_log_size
        
        # Security events log
        self.security_log_file = self.log_dir / "security.log"
        
        # Application errors log
        self.error_log_file = self.log_dir / "errors.log"
        
        # Authentication events log
        self.auth_log_file = self.log_dir / "auth.log"
        
        # Setup loggers
        self._setup_loggers()
        
        # Security event tracking
        self.security_events: List[Dict[str, Any]] = []
        self.rate_limit_tracker: Dict[str, List[datetime]] = {}
        
    def _setup_loggers(self):
        """Setup logging configuration with rotation"""
        from logging.handlers import RotatingFileHandler
        
        # Security logger with rotation
        self.security_logger = logging.getLogger('security')
        self.security_logger.setLevel(logging.INFO)
        security_handler = RotatingFileHandler(
            self.security_log_file, 
            maxBytes=self.max_log_size, 
            backupCount=5
        )
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.security_logger.addHandler(security_handler)
        
        # Error logger with rotation
        self.error_logger = logging.getLogger('errors')
        self.error_logger.setLevel(logging.ERROR)
        error_handler = RotatingFileHandler(
            self.error_log_file, 
            maxBytes=self.max_log_size, 
            backupCount=5
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.error_logger.addHandler(error_handler)
        
        # Auth logger with rotation
        self.auth_logger = logging.getLogger('auth')
        self.auth_logger.setLevel(logging.INFO)
        auth_handler = RotatingFileHandler(
            self.auth_log_file, 
            maxBytes=self.max_log_size, 
            backupCount=5
        )
        auth_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.auth_logger.addHandler(auth_handler)
    
    def log_security_event(self, event_type: SecurityEvent, details: Dict[str, Any], 
                          user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """
        Log a security event
        
        Args:
            event_type: Type of security event
            details: Additional details about the event
            user_id: User ID if available
            ip_address: IP address if available
        """
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type.value,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details
        }
        
        # Add to in-memory tracking
        self.security_events.append(event_data)
        
        # Keep only last 1000 events in memory
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Log to file
        self.security_logger.info(json.dumps(event_data))
        
        # Also log to remote database for centralized monitoring
        try:
            from remote_logger import log_security_event_remotely
            log_security_event_remotely(event_type.value, details, user_id, ip_address)
        except Exception as e:
            # Don't fail local logging if remote logging fails
            print(f"Warning: Failed to log security event remotely: {e}")
        
        # Check for suspicious patterns
        self._check_suspicious_patterns(event_data)
    
    def log_error(self, error: Exception, context: str = "", user_id: Optional[str] = None):
        """
        Log an application error
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            user_id: User ID if available
        """
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id,
            'traceback': traceback.format_exc()
        }
        
        self.error_logger.error(json.dumps(error_data))
        
        # Also log to remote database for centralized monitoring
        try:
            from remote_logger import log_error_remotely
            log_error_remotely(error, context, user_id, "ERROR")
        except Exception as e:
            # Don't fail local logging if remote logging fails
            print(f"Warning: Failed to log error remotely: {e}")
    
    def log_auth_event(self, event: str, details: Dict[str, Any], user_id: Optional[str] = None):
        """
        Log an authentication event
        
        Args:
            event: Description of the event
            details: Additional details
            user_id: User ID if available
        """
        auth_data = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'user_id': user_id,
            'details': details
        }
        
        self.auth_logger.info(json.dumps(auth_data))
    
    def log_login_attempt(self, email: str, success: bool, error_message: str = "", 
                         user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log a login attempt"""
        event_type = SecurityEvent.LOGIN_SUCCESS if success else SecurityEvent.LOGIN_FAILURE
        details = {
            'email': email,
            'success': success,
            'error_message': error_message
        }
        
        self.log_security_event(event_type, details, user_id, ip_address)
        self.log_auth_event(f"Login {'success' if success else 'failure'}", details, user_id)
    
    def log_registration_attempt(self, email: str, success: bool, error_message: str = "", 
                                user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log a registration attempt"""
        event_type = SecurityEvent.REGISTRATION_SUCCESS if success else SecurityEvent.REGISTRATION_FAILURE
        details = {
            'email': email,
            'success': success,
            'error_message': error_message
        }
        
        self.log_security_event(event_type, details, user_id, ip_address)
        self.log_auth_event(f"Registration {'success' if success else 'failure'}", details, user_id)
    
    def log_password_reset_attempt(self, email: str, success: bool, error_message: str = "", 
                                  user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log a password reset attempt"""
        event_type = SecurityEvent.PASSWORD_RESET_SUCCESS if success else SecurityEvent.PASSWORD_RESET_FAILURE
        details = {
            'email': email,
            'success': success,
            'error_message': error_message
        }
        
        self.log_security_event(event_type, details, user_id, ip_address)
        self.log_auth_event(f"Password reset {'success' if success else 'failure'}", details, user_id)
    
    def log_invalid_input(self, input_type: str, value: str, reason: str, 
                         user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log invalid input attempts"""
        details = {
            'input_type': input_type,
            'value': value[:100],  # Truncate for security
            'reason': reason
        }
        
        self.log_security_event(SecurityEvent.INVALID_INPUT, details, user_id, ip_address)
    
    def log_suspicious_activity(self, activity: str, details: Dict[str, Any], 
                               user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log suspicious activity"""
        event_details = {
            'activity': activity,
            **details
        }
        
        self.log_security_event(SecurityEvent.SUSPICIOUS_ACTIVITY, event_details, user_id, ip_address)
    
    def check_rate_limit(self, identifier: str, max_attempts: int = 5, 
                        time_window_minutes: int = 15) -> bool:
        """
        Check if rate limit has been exceeded
        
        Args:
            identifier: Unique identifier (email, IP, etc.)
            max_attempts: Maximum attempts allowed
            time_window_minutes: Time window in minutes
            
        Returns:
            True if rate limit exceeded, False otherwise
        """
        now = datetime.now()
        time_window = timedelta(minutes=time_window_minutes)
        
        # Get attempts for this identifier
        attempts = self.rate_limit_tracker.get(identifier, [])
        
        # Remove old attempts outside time window
        attempts = [attempt for attempt in attempts if now - attempt < time_window]
        
        # Check if limit exceeded
        if len(attempts) >= max_attempts:
            self.log_security_event(
                SecurityEvent.RATE_LIMIT_EXCEEDED,
                {
                    'identifier': identifier,
                    'attempts': len(attempts),
                    'max_attempts': max_attempts,
                    'time_window_minutes': time_window_minutes
                }
            )
            return True
        
        # Add current attempt
        attempts.append(now)
        self.rate_limit_tracker[identifier] = attempts
        
        return False
    
    def _check_suspicious_patterns(self, event_data: Dict[str, Any]):
        """Check for suspicious patterns in security events"""
        event_type = event_data.get('event_type')
        details = event_data.get('details', {})
        
        # Check for rapid failed login attempts
        if event_type == SecurityEvent.LOGIN_FAILURE.value:
            email = details.get('email', '')
            if email:
                # Count recent failures for this email
                recent_failures = [
                    event for event in self.security_events[-10:]  # Last 10 events
                    if (event.get('event_type') == SecurityEvent.LOGIN_FAILURE.value and
                        event.get('details', {}).get('email') == email and
                        datetime.fromisoformat(event['timestamp']) > datetime.now() - timedelta(minutes=5))
                ]
                
                if len(recent_failures) >= 3:
                    self.log_suspicious_activity(
                        "Multiple failed login attempts",
                        {
                            'email': email,
                            'failure_count': len(recent_failures),
                            'time_window': '5 minutes'
                        },
                        event_data.get('user_id'),
                        event_data.get('ip_address')
                    )
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security event summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event['timestamp']) > cutoff_time
        ]
        
        summary = {
            'total_events': len(recent_events),
            'login_attempts': len([e for e in recent_events if e['event_type'] == SecurityEvent.LOGIN_ATTEMPT.value]),
            'login_successes': len([e for e in recent_events if e['event_type'] == SecurityEvent.LOGIN_SUCCESS.value]),
            'login_failures': len([e for e in recent_events if e['event_type'] == SecurityEvent.LOGIN_FAILURE.value]),
            'registration_attempts': len([e for e in recent_events if e['event_type'] == SecurityEvent.REGISTRATION_ATTEMPT.value]),
            'suspicious_activities': len([e for e in recent_events if e['event_type'] == SecurityEvent.SUSPICIOUS_ACTIVITY.value]),
            'rate_limit_exceeded': len([e for e in recent_events if e['event_type'] == SecurityEvent.RATE_LIMIT_EXCEEDED.value])
        }
        
        return summary
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for log_file in [self.security_log_file, self.error_log_file, self.auth_log_file]:
            if log_file.exists():
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        log_file.unlink()
                    except Exception as e:
                        self.log_error(e, f"Failed to cleanup log file: {log_file}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about log files"""
        stats = {}
        
        for log_name, log_file in [
            ('security', self.security_log_file),
            ('errors', self.error_log_file),
            ('auth', self.auth_log_file)
        ]:
            if log_file.exists():
                file_size = log_file.stat().st_size
                file_age = datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)
                stats[log_name] = {
                    'size_bytes': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'age_hours': round(file_age.total_seconds() / 3600, 2),
                    'exists': True
                }
            else:
                stats[log_name] = {'exists': False}
        
        return stats
