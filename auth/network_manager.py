"""
Network Manager for detecting connectivity and managing online/offline states
Handles automatic re-authentication and background subscription checking
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from .auth_manager import AuthManager
from .subscription_checker import SubscriptionChecker


class NetworkManager:
    """Manages network connectivity and automatic re-authentication"""
    
    def __init__(self, auth_manager: AuthManager, subscription_checker: SubscriptionChecker):
        self.auth_manager = auth_manager
        self.subscription_checker = subscription_checker
        
        # Network state
        self.is_online = False
        self.last_online_check = None
        self.check_interval = 3600  # 1 hour - reduced from 30 seconds to conserve battery
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Callbacks
        self.online_callback: Optional[Callable] = None
        self.offline_callback: Optional[Callable] = None
        self.status_change_callback: Optional[Callable] = None
        
        # Background checking
        self.background_check_interval = 3600  # 1 hour
        self.last_background_check = None
        self.is_background_checking = False
    
    def start_monitoring(self, check_interval: int = 3600) -> bool:
        """
        Start monitoring network connectivity
        
        Args:
            check_interval: Interval in seconds between connectivity checks (default: 3600 = 1 hour)
        
        Returns:
            bool: True if monitoring started successfully
        """
        try:
            if self.is_monitoring:
                return True  # Already monitoring
            
            self.check_interval = check_interval
            self.is_monitoring = True
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            # Perform initial check
            self._check_connectivity()
            
            return True
            
        except Exception as e:
            print(f"Failed to start network monitoring: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop monitoring network connectivity"""
        try:
            self.is_monitoring = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                # Wait for thread to finish (with timeout)
                self.monitor_thread.join(timeout=5.0)
            
            return True
            
        except Exception as e:
            print(f"Failed to stop network monitoring: {e}")
            return False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                self._check_connectivity()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in network monitoring loop: {e}")
                time.sleep(self.check_interval)
    
    def _check_connectivity(self) -> bool:
        """
        Check network connectivity and update state
        
        Returns:
            bool: True if online, False if offline
        """
        try:
            # Check connectivity using auth manager
            was_online = self.is_online
            self.is_online = self.auth_manager.is_online()
            self.last_online_check = datetime.now()
            
            # If status changed, handle it
            if was_online != self.is_online:
                self._handle_connectivity_change(was_online, self.is_online)
            
            # If just came online, attempt re-authentication
            if self.is_online and not was_online:
                self._handle_came_online()
            
            return self.is_online
            
        except Exception as e:
            print(f"Error checking connectivity: {e}")
            self.is_online = False
            return False
    
    def _handle_connectivity_change(self, was_online: bool, is_online: bool):
        """Handle connectivity status changes"""
        try:
            # Call status change callback
            if self.status_change_callback:
                self.status_change_callback(is_online)
            
            # Call specific callbacks
            if is_online and self.online_callback:
                self.online_callback()
            elif not is_online and self.offline_callback:
                self.offline_callback()
                
        except Exception as e:
            print(f"Error handling connectivity change: {e}")
    
    def _handle_came_online(self):
        """Handle when connection comes back online"""
        try:
            print("🌐 Network connection restored - attempting re-authentication")
            
            # Attempt to re-authenticate
            auth_success, auth_message = self.auth_manager.attempt_reauthentication()
            if auth_success:
                print("✅ Re-authentication successful")
            else:
                print(f"⚠️  Re-authentication failed: {auth_message}")
            
            # Attempt to refresh subscription
            sub_success, sub_message = self.subscription_checker.attempt_subscription_refresh()
            if sub_success:
                print("✅ Subscription data refreshed")
            else:
                print(f"⚠️  Subscription refresh failed: {sub_message}")
                
        except Exception as e:
            print(f"Error handling came online: {e}")
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get current network status information"""
        return {
            'is_online': self.is_online,
            'is_monitoring': self.is_monitoring,
            'last_check': self.last_online_check.isoformat() if self.last_online_check else None,
            'check_interval': self.check_interval,
            'is_background_checking': self.is_background_checking
        }
    
    def set_online_callback(self, callback: Callable):
        """Set callback for when connection comes online"""
        self.online_callback = callback
    
    def set_offline_callback(self, callback: Callable):
        """Set callback for when connection goes offline"""
        self.offline_callback = callback
    
    def set_status_change_callback(self, callback: Callable):
        """Set callback for any connectivity status change"""
        self.status_change_callback = callback
    
    def force_connectivity_check(self) -> bool:
        """Force an immediate connectivity check"""
        return self._check_connectivity()
    
    def start_background_checking(self, interval_hours: int = 1) -> bool:
        """
        Start background subscription checking
        
        Args:
            interval_hours: Interval in hours between background checks
        
        Returns:
            bool: True if background checking started successfully
        """
        try:
            if self.is_background_checking:
                return True  # Already running
            
            self.background_check_interval = interval_hours * 3600  # Convert to seconds
            self.is_background_checking = True
            
            # Start background checking thread
            bg_thread = threading.Thread(target=self._background_check_loop, daemon=True)
            bg_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Failed to start background checking: {e}")
            return False
    
    def _background_check_loop(self):
        """Background checking loop for subscription validation"""
        while self.is_background_checking:
            try:
                # Only check if online
                if self.is_online:
                    self._perform_background_check()
                
                # Wait for next check
                time.sleep(self.background_check_interval)
                
            except Exception as e:
                print(f"Error in background check loop: {e}")
                time.sleep(self.background_check_interval)
    
    def _perform_background_check(self):
        """Perform background subscription check"""
        try:
            print("🔄 Performing background subscription check")
            
            # Check subscription status
            status, message = self.subscription_checker.check_subscription_status(force_online=True)
            print(f"📋 Background check result: {status} - {message}")
            
            # Update last background check time
            self.last_background_check = datetime.now()
            
        except Exception as e:
            print(f"Error in background check: {e}")
    
    def stop_background_checking(self) -> bool:
        """Stop background subscription checking"""
        try:
            self.is_background_checking = False
            return True
        except Exception as e:
            print(f"Failed to stop background checking: {e}")
            return False
    
    def get_background_check_info(self) -> Dict[str, Any]:
        """Get background checking information"""
        return {
            'is_running': self.is_background_checking,
            'interval_hours': self.background_check_interval / 3600,
            'last_check': self.last_background_check.isoformat() if self.last_background_check else None
        }
    
    def cleanup(self):
        """Cleanup network manager resources"""
        try:
            self.stop_monitoring()
            self.stop_background_checking()
        except Exception as e:
            print(f"Error during network manager cleanup: {e}")


class OfflineIndicator:
    """Simple offline indicator for GUI display"""
    
    def __init__(self, network_manager: NetworkManager):
        self.network_manager = network_manager
        self.is_offline_mode = False
        self.offline_start_time = None
    
    def update_status(self, is_online: bool):
        """Update offline indicator status"""
        if not is_online and not self.is_offline_mode:
            # Just went offline
            self.is_offline_mode = True
            self.offline_start_time = datetime.now()
        elif is_online and self.is_offline_mode:
            # Just came back online
            self.is_offline_mode = False
            self.offline_start_time = None
    
    def get_offline_info(self) -> Dict[str, Any]:
        """Get offline mode information"""
        if not self.is_offline_mode:
            return {
                'is_offline': False,
                'message': 'Online',
                'duration': None
            }
        
        duration = None
        if self.offline_start_time:
            duration = datetime.now() - self.offline_start_time
        
        return {
            'is_offline': True,
            'message': f'Offline for {duration}' if duration else 'Offline',
            'duration': duration.total_seconds() if duration else None,
            'start_time': self.offline_start_time.isoformat() if self.offline_start_time else None
        }
    
    def get_status_text(self) -> str:
        """Get formatted status text for display"""
        info = self.get_offline_info()
        return info['message']
