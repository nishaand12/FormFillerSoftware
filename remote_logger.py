#!/usr/bin/env python3
"""
Remote Logging System
Sends critical errors and system events to Supabase database for centralized monitoring
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import platform
import socket

# Import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: Supabase not available. Remote logging disabled.")

# Import configuration using proper resource path
try:
    import json
    import sys
    from pathlib import Path
    
    # Get proper resource path
    try:
        from app_paths import get_resource_path
        config_path = get_resource_path("config/supabase_config.json")
    except ImportError:
        # Fallback
        if getattr(sys, '_MEIPASS', None):
            config_path = Path(sys._MEIPASS) / "config/supabase_config.json"
        else:
            config_path = Path(__file__).parent / "config/supabase_config.json"
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    SUPABASE_URL = config.get('supabase_url')
    SUPABASE_KEY = config.get('supabase_anon_key')
except Exception as e:
    print(f"Warning: Could not load Supabase config: {e}")
    SUPABASE_URL = None
    SUPABASE_KEY = None


class RemoteLogger:
    """Remote logging system for centralized error monitoring"""
    
    def __init__(self, enabled: bool = True, batch_size: int = 10):
        self.enabled = enabled and SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY
        self.batch_size = batch_size
        self.pending_logs: List[Dict[str, Any]] = []
        
        if self.enabled:
            try:
                self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                self._setup_database_tables()
            except Exception as e:
                print(f"Failed to initialize Supabase client: {e}")
                self.enabled = False
        else:
            self.supabase = None
        
        # System information
        self.system_info = self._get_system_info()
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for logging context"""
        try:
            return {
                'hostname': socket.gethostname(),
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'architecture': platform.architecture()[0],
                'machine': platform.machine(),
                'processor': platform.processor() or 'Unknown'
            }
        except Exception:
            return {'error': 'Could not get system info'}
    
    def _setup_database_tables(self):
        """Setup database tables for remote logging"""
        if not self.enabled:
            return
        
        try:
            # Create error_logs table if it doesn't exist
            # This would typically be done via SQL migration, but we'll handle it here
            # Note: In production, you should create these tables via Supabase dashboard
            
            # For now, we'll assume the tables exist and handle errors gracefully
            pass
        except Exception as e:
            print(f"Warning: Could not setup database tables: {e}")
    
    def log_error(self, error: Exception, context: str = "", 
                  user_id: Optional[str] = None, severity: str = "ERROR") -> bool:
        """
        Log an error to the remote database
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            user_id: User ID if available (UUID from auth.users.id)
                     If None, will log as system error (pre-login errors)
            severity: Error severity level
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Determine if this is a user-specific error or system error
            is_user_error = user_id is not None
            
            error_data = {
                'timestamp': datetime.now().isoformat(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc(),
                'context': f"{'User error' if is_user_error else 'System error'}: {context}",
                'user_id': user_id,  # NULL for system errors, UUID for user errors
                'severity': severity,
                'system_info': json.dumps(self.system_info),
                'application_version': self._get_app_version(),
                'log_level': 'ERROR'
            }
            
            return self._send_log_entry(error_data)
            
        except Exception as e:
            print(f"Failed to log error remotely: {e}")
            return False
    
    def log_system_event(self, event_type: str, message: str, 
                        user_id: Optional[str] = None, 
                        severity: str = "INFO") -> bool:
        """
        Log a system event to the remote database
        
        Args:
            event_type: Type of event (e.g., 'STARTUP', 'SHUTDOWN', 'BACKUP')
            message: Event message
            user_id: User ID if available
            severity: Event severity level
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Determine if this is a user-specific event or system event
            is_user_event = user_id is not None
            
            event_data = {
                'timestamp': datetime.now().isoformat(),
                'error_type': event_type,
                'error_message': message,
                'traceback': None,
                'context': f"{'User event' if is_user_event else 'System event'}: {event_type}",
                'user_id': user_id,  # NULL for system events, UUID for user events
                'severity': severity,
                'system_info': json.dumps(self.system_info),
                'application_version': self._get_app_version(),
                'log_level': 'INFO'
            }
            
            return self._send_log_entry(event_data)
            
        except Exception as e:
            print(f"Failed to log system event remotely: {e}")
            return False
    
    def log_security_event(self, event_type: str, details: Dict[str, Any],
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None) -> bool:
        """
        Log a security event to the remote database
        
        Args:
            event_type: Type of security event
            details: Additional event details
            user_id: User ID if available
            ip_address: IP address if available
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            security_data = {
                'timestamp': datetime.now().isoformat(),
                'error_type': f"SECURITY_{event_type}",
                'error_message': f"Security event: {event_type}",
                'traceback': None,
                'context': json.dumps(details),
                'user_id': user_id,
                'severity': 'SECURITY',
                'system_info': json.dumps({
                    **self.system_info,
                    'ip_address': ip_address
                }),
                'application_version': self._get_app_version(),
                'log_level': 'WARNING'
            }
            
            return self._send_log_entry(security_data)
            
        except Exception as e:
            print(f"Failed to log security event remotely: {e}")
            return False
    
    def _send_log_entry(self, log_data: Dict[str, Any]) -> bool:
        """Send a log entry to the remote database"""
        try:
            if not self.enabled or not self.supabase:
                return False
            
            # Insert into remote database
            response = self.supabase.table('error_logs').insert(log_data).execute()
            
            if response.data:
                return True
            else:
                print(f"Failed to insert log entry: {response}")
                return False
                
        except Exception as e:
            print(f"Error sending log entry to remote database: {e}")
            return False
    
    def _get_app_version(self) -> str:
        """Get application version"""
        try:
            version_file = Path("VERSION")
            if version_file.exists():
                return version_file.read_text().strip()
            else:
                return "Unknown"
        except Exception:
            return "Unknown"
    
    def get_recent_logs(self, limit: int = 100, 
                       severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve recent log entries from the remote database
        
        Args:
            limit: Maximum number of logs to retrieve
            severity: Filter by severity level
            
        Returns:
            List of log entries
        """
        if not self.enabled or not self.supabase:
            return []
        
        try:
            query = self.supabase.table('error_logs').select('*').order('timestamp', desc=True).limit(limit)
            
            if severity:
                query = query.eq('severity', severity)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            print(f"Error retrieving logs from remote database: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> bool:
        """
        Clean up old log entries from the remote database
        
        Args:
            days_to_keep: Number of days to keep logs
            
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        if not self.enabled or not self.supabase:
            return False
        
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
            
            response = self.supabase.table('error_logs').delete().lt('timestamp', cutoff_date.isoformat()).execute()
            
            print(f"Cleaned up old logs: {len(response.data) if response.data else 0} entries removed")
            return True
            
        except Exception as e:
            print(f"Error cleaning up old logs: {e}")
            return False


# Global instance
_remote_logger = None

def get_remote_logger() -> RemoteLogger:
    """Get the global remote logger instance"""
    global _remote_logger
    if _remote_logger is None:
        _remote_logger = RemoteLogger()
    return _remote_logger

def log_error_remotely(error: Exception, context: str = "", 
                      user_id: Optional[str] = None, severity: str = "ERROR") -> bool:
    """Convenience function to log an error remotely"""
    return get_remote_logger().log_error(error, context, user_id, severity)

def log_system_event_remotely(event_type: str, message: str, 
                             user_id: Optional[str] = None, severity: str = "INFO") -> bool:
    """Convenience function to log a system event remotely"""
    return get_remote_logger().log_system_event(event_type, message, user_id, severity)

def log_security_event_remotely(event_type: str, details: Dict[str, Any],
                               user_id: Optional[str] = None, 
                               ip_address: Optional[str] = None) -> bool:
    """Convenience function to log a security event remotely"""
    return get_remote_logger().log_security_event(event_type, details, user_id, ip_address)
