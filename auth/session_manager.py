"""
Session Manager for Single Device Authentication
Handles device tracking and session enforcement when Supabase Pro features are not available
"""

import os
import json
import hashlib
import platform
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from .config_manager import ConfigManager
from .local_storage import LocalStorageManager


class SessionManager:
    """Manages user sessions and enforces single-device authentication"""
    
    def __init__(self, auth_manager=None):
        self.config_manager = ConfigManager()
        self.local_storage = LocalStorageManager()
        self.auth_manager = auth_manager
        
        # Session tracking file
        self.session_file = self.local_storage.cache_dir / "active_sessions.dat"
        
    def _generate_device_fingerprint(self) -> str:
        """Generate a unique device fingerprint"""
        try:
            # Combine system information to create a device fingerprint
            system_info = {
                'platform': platform.system(),
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'hostname': platform.node(),
            }
            
            # Create a hash of the system information
            fingerprint_data = json.dumps(system_info, sort_keys=True)
            device_fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
            
            return device_fingerprint
            
        except Exception as e:
            print(f"Error generating device fingerprint: {e}")
            # Fallback to a random UUID if fingerprinting fails
            return str(uuid.uuid4())[:16]
    
    def _load_active_sessions(self) -> Dict[str, Any]:
        """Load active sessions from storage"""
        try:
            if not self.session_file.exists():
                return {}
            
            with open(self.session_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"Error loading active sessions: {e}")
            return {}
    
    def _save_active_sessions(self, sessions: Dict[str, Any]) -> bool:
        """Save active sessions to storage"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(sessions, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(self.session_file, 0o600)
            return True
            
        except Exception as e:
            print(f"Error saving active sessions: {e}")
            return False
    
    def _is_session_expired(self, session_data: Dict[str, Any], max_age_hours: int = 24) -> bool:
        """Check if a session is expired"""
        try:
            created_at = datetime.fromisoformat(session_data.get('created_at', '1970-01-01'))
            max_age = timedelta(hours=max_age_hours)
            return datetime.now() > (created_at + max_age)
        except:
            return True
    
    def _cleanup_expired_sessions(self, sessions: Dict[str, Any]) -> Dict[str, Any]:
        """Remove expired sessions"""
        cleaned_sessions = {}
        
        for user_id, session_data in sessions.items():
            if not self._is_session_expired(session_data):
                cleaned_sessions[user_id] = session_data
        
        return cleaned_sessions
    
    def register_device_session(self, user_id: str, access_token: str) -> Tuple[bool, str]:
        """
        Register a new device session for a user
        
        Args:
            user_id: User ID from Supabase
            access_token: Current access token
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Generate device fingerprint
            device_fingerprint = self._generate_device_fingerprint()
            
            # Load existing sessions
            sessions = self._load_active_sessions()
            
            # Clean up expired sessions
            sessions = self._cleanup_expired_sessions(sessions)
            
            # Check if user already has an active session
            if user_id in sessions:
                existing_session = sessions[user_id]
                existing_device = existing_session.get('device_fingerprint')
                
                # If it's the same device, update the session
                if existing_device == device_fingerprint:
                    sessions[user_id] = {
                        'device_fingerprint': device_fingerprint,
                        'access_token': access_token,
                        'created_at': existing_session.get('created_at', datetime.now().isoformat()),  # Keep original creation time
                        'last_activity': datetime.now().isoformat()
                    }
                    
                    self._save_active_sessions(sessions)
                    return True, "Session updated for existing device"
                
                else:
                    # Different device - this violates single-device policy
                    return False, "Another device is already logged in with this account. Please log out from the other device first."
            
            # Register new session
            sessions[user_id] = {
                'device_fingerprint': device_fingerprint,
                'access_token': access_token,
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            
            self._save_active_sessions(sessions)
            return True, "Device session registered successfully"
            
        except Exception as e:
            return False, f"Error registering device session: {e}"
    
    def validate_device_session(self, user_id: str, access_token: str) -> Tuple[bool, str]:
        """
        Validate if the current device session is valid
        
        Args:
            user_id: User ID from Supabase
            access_token: Current access token
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Load active sessions
            sessions = self._load_active_sessions()
            
            # Clean up expired sessions
            sessions = self._cleanup_expired_sessions(sessions)
            self._save_active_sessions(sessions)  # Save cleaned sessions
            
            if user_id not in sessions:
                return False, "No active session found for this user"
            
            session_data = sessions[user_id]
            
            # Check if session is expired
            if self._is_session_expired(session_data):
                # Remove expired session
                del sessions[user_id]
                self._save_active_sessions(sessions)
                return False, "Session has expired"
            
            # Generate current device fingerprint
            current_device = self._generate_device_fingerprint()
            session_device = session_data.get('device_fingerprint')
            
            # Check if device matches
            if current_device != session_device:
                return False, "Device mismatch - please log in again"
            
            # Update last activity
            session_data['last_activity'] = datetime.now().isoformat()
            self._save_active_sessions(sessions)
            
            return True, "Device session is valid"
            
        except Exception as e:
            return False, f"Error validating device session: {e}"
    
    def revoke_device_session(self, user_id: str) -> bool:
        """
        Revoke device session for a user (logout)
        
        Args:
            user_id: User ID from Supabase
            
        Returns:
            bool: True if session was revoked successfully
        """
        try:
            sessions = self._load_active_sessions()
            
            if user_id in sessions:
                del sessions[user_id]
                self._save_active_sessions(sessions)
            
            return True
            
        except Exception as e:
            print(f"Error revoking device session: {e}")
            return False
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """Get all active sessions (for debugging/admin purposes)"""
        try:
            sessions = self._load_active_sessions()
            return self._cleanup_expired_sessions(sessions)
        except Exception as e:
            print(f"Error getting active sessions: {e}")
            return {}
    
    def force_logout_user(self, user_id: str) -> bool:
        """
        Force logout a user from all devices (admin function)
        
        Args:
            user_id: User ID from Supabase
            
        Returns:
            bool: True if logout was successful
        """
        return self.revoke_device_session(user_id)
    
    def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information for a user
        
        Args:
            user_id: User ID from Supabase
            
        Returns:
            Dict containing session info or None if no active session
        """
        try:
            sessions = self._load_active_sessions()
            
            if user_id in sessions:
                session_data = sessions[user_id].copy()
                
                # Add computed fields
                session_data['is_expired'] = self._is_session_expired(session_data)
                session_data['device_matches'] = (
                    session_data.get('device_fingerprint') == self._generate_device_fingerprint()
                )
                
                return session_data
            
            return None
            
        except Exception as e:
            print(f"Error getting session info: {e}")
            return None
    
    def cleanup_all_expired_sessions(self) -> int:
        """
        Clean up all expired sessions
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            sessions = self._load_active_sessions()
            original_count = len(sessions)
            
            cleaned_sessions = self._cleanup_expired_sessions(sessions)
            self._save_active_sessions(cleaned_sessions)
            
            cleaned_count = original_count - len(cleaned_sessions)
            return cleaned_count
            
        except Exception as e:
            print(f"Error cleaning up expired sessions: {e}")
            return 0
