"""
Authentication Manager for Supabase integration
Handles user login, registration, token management, and offline validation
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from supabase import create_client, Client
from .config_manager import ConfigManager
from .local_storage import LocalStorageManager
from .session_manager import SessionManager
from .input_validator import InputValidator
from .error_logger import ErrorLogger, SecurityEvent
from .rate_limiter import RateLimiter


class AuthManager:
    """Manages user authentication with Supabase and local caching"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.local_storage = LocalStorageManager()
        self.session_manager = SessionManager(self)
        self.input_validator = InputValidator()
        self.error_logger = ErrorLogger()
        self.rate_limiter = RateLimiter()
        self.supabase: Optional[Client] = None
        self.current_user: Optional[Dict[str, Any]] = None
        
        # Initialize Supabase client
        self._initialize_supabase()
    
    def _initialize_supabase(self) -> None:
        """Initialize Supabase client"""
        try:
            url = self.config_manager.get_supabase_url()
            key = self.config_manager.get_supabase_anon_key()
            self.supabase = create_client(url, key)
        except Exception as e:
            raise Exception(f"Failed to initialize Supabase client: {e}")
    
    def _check_internet_connection(self) -> bool:
        """Check if internet connection is available"""
        try:
            # Try to make a simple request to Supabase
            if self.supabase:
                # This will fail if no internet connection
                self.supabase.table('user_profiles').select('id').limit(1).execute()
                return True
        except Exception:
            pass
        return False
    
    def register_user(self, email: str, password: str, full_name: str = "", clinic_name: str = "") -> Tuple[bool, str]:
        """
        Register a new user
        
        Args:
            email: User email address
            password: User password
            full_name: User's full name
            clinic_name: Clinic name
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Sanitize and validate input
            registration_data = {
                'email': email,
                'password': password,
                'full_name': full_name,
                'clinic_name': clinic_name,
                'subscription_plan': 'trial'  # Default to trial
            }
            
            sanitized_data = self.input_validator.sanitize_registration_data(registration_data)
            
            # Validate input
            is_valid, errors = self.input_validator.validate_registration_data(sanitized_data)
            
            if not is_valid:
                error_msg = "; ".join(errors)
                self.error_logger.log_invalid_input("registration", email, error_msg)
                return False, error_msg
            
            # Check rate limiting
            is_limited, reason, retry_after = self.rate_limiter.is_rate_limited(email, 'registration')
            if is_limited:
                self.error_logger.log_security_event(
                    SecurityEvent.RATE_LIMIT_EXCEEDED,
                    {'email': email, 'reason': reason, 'retry_after': retry_after}
                )
                return False, reason
            
            if not self._check_internet_connection():
                return False, "No internet connection. Please check your network and try again."
            
            # Register with Supabase Auth
            response = self.supabase.auth.sign_up({
                'email': email,
                'password': password,
                'options': {
                    'data': {
                        'full_name': full_name,
                        'clinic_name': clinic_name
                    }
                }
            })
            
            if response.user:
                # Log successful registration
                self.error_logger.log_registration_attempt(email, True, "", response.user.id)
                self.rate_limiter.record_attempt(email, 'registration', True)
                return True, "Registration successful! Please check your email to verify your account."
            else:
                # Log failed registration
                self.error_logger.log_registration_attempt(email, False, "Registration failed")
                self.rate_limiter.record_attempt(email, 'registration', False)
                return False, "Registration failed. Please try again."
                
        except Exception as e:
            error_msg = str(e)
            
            # Log failed registration attempt
            self.error_logger.log_registration_attempt(email, False, error_msg)
            self.rate_limiter.record_attempt(email, 'registration', False)
            self.error_logger.log_error(e, "Registration attempt failed")
            
            if "already registered" in error_msg.lower():
                return False, "An account with this email already exists."
            elif "password" in error_msg.lower():
                return False, "Password must be at least 6 characters long."
            elif "email" in error_msg.lower():
                return False, "Please enter a valid email address."
            else:
                return False, f"Registration failed: {error_msg}"
    
    def login_user(self, email: str, password: str) -> Tuple[bool, str]:
        """
        Login user with email and password
        
        Args:
            email: User email address
            password: User password
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Sanitize and validate input
            sanitized_data = self.input_validator.sanitize_login_data({
                'email': email,
                'password': password
            })
            
            email = sanitized_data['email']
            password = sanitized_data['password']
            
            # Validate input
            is_valid, errors = self.input_validator.validate_login_data({
                'email': email,
                'password': password
            })
            
            if not is_valid:
                error_msg = "; ".join(errors)
                self.error_logger.log_invalid_input("login", email, error_msg)
                return False, error_msg
            
            # Check rate limiting
            is_limited, reason, retry_after = self.rate_limiter.is_rate_limited(email, 'login')
            if is_limited:
                self.error_logger.log_security_event(
                    SecurityEvent.RATE_LIMIT_EXCEEDED,
                    {'email': email, 'reason': reason, 'retry_after': retry_after}
                )
                return False, reason
            
            if not self._check_internet_connection():
                return False, "No internet connection. Please check your network and try again."
            
            # Login with Supabase Auth
            response = self.supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if response.user and response.session:
                # Store user data and session
                user_data = {
                    'user_id': response.user.id,
                    'email': response.user.email,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at,
                    'user_metadata': response.user.user_metadata or {}
                }
                
                # Register device session for single-device enforcement
                session_success, session_message = self.session_manager.register_device_session(
                    user_data['user_id'], user_data['access_token']
                )
                
                if not session_success:
                    # Another device is already logged in
                    return False, session_message
                
                # Cache the authentication data
                cache_settings = self.config_manager.get_cache_settings()
                max_age_hours = cache_settings.get('token_cache_duration_hours', 168)
                
                self.local_storage.store_auth_token(user_data, max_age_hours)
                
                # Update current user
                self.current_user = user_data
                
                # Log successful login
                self.error_logger.log_login_attempt(email, True, "", user_data['user_id'])
                self.rate_limiter.record_attempt(email, 'login', True)
                
                return True, "Login successful!"
            else:
                # Log failed login
                self.error_logger.log_login_attempt(email, False, "Invalid credentials")
                self.rate_limiter.record_attempt(email, 'login', False)
                return False, "Login failed. Please check your credentials."
                
        except Exception as e:
            error_msg = str(e)
            
            # Log failed login attempt
            self.error_logger.log_login_attempt(email, False, error_msg)
            self.rate_limiter.record_attempt(email, 'login', False)
            self.error_logger.log_error(e, "Login attempt failed")
            
            if "invalid" in error_msg.lower():
                return False, "Invalid email or password."
            elif "email not confirmed" in error_msg.lower():
                return False, "Please verify your email address before logging in."
            else:
                return False, f"Login failed: {error_msg}"
    
    def logout_user(self) -> bool:
        """
        Logout current user
        
        Returns:
            bool: True if logout successful
        """
        try:
            # Revoke device session
            if self.current_user:
                user_id = self.current_user.get('user_id')
                if user_id:
                    self.session_manager.revoke_device_session(user_id)
            
            # Clear local cache
            self.local_storage.clear_auth_token()
            self.local_storage.clear_subscription_data()
            
            # Clear current user
            self.current_user = None
            
            # Sign out from Supabase if online
            if self._check_internet_connection() and self.supabase:
                try:
                    self.supabase.auth.sign_out()
                except:
                    pass  # Ignore errors if already signed out
            
            return True
            
        except Exception as e:
            print(f"Error during logout: {e}")
            return False
    
    def check_auth_status(self) -> str:
        """
        Check current authentication status
        
        Returns:
            str: Authentication status ('authenticated', 'unauthenticated', 'expired', 'offline')
        """
        try:
            # Try to load cached token
            cached_token = self.local_storage.load_auth_token()
            
            if not cached_token:
                return 'unauthenticated'
            
            # Check if token is expired
            expires_at = cached_token.get('expires_at')
            if expires_at:
                try:
                    expires_datetime = datetime.fromisoformat(expires_at)
                    if datetime.now() > expires_datetime:
                        return 'expired'
                except:
                    return 'expired'
            
            # Validate device session
            user_id = cached_token.get('user_id')
            access_token = cached_token.get('access_token')
            
            if user_id and access_token:
                device_valid, device_message = self.session_manager.validate_device_session(user_id, access_token)
                if not device_valid:
                    # Device session invalid - clear cache and require re-login
                    self.local_storage.clear_auth_token()
                    return 'unauthenticated'
            
            # Check if we're online and can validate token
            if self._check_internet_connection():
                # Try to refresh token if needed
                if self._should_refresh_token(cached_token):
                    if self._refresh_token():
                        self.current_user = cached_token
                        return 'authenticated'
                    else:
                        return 'expired'
                else:
                    self.current_user = cached_token
                    return 'authenticated'
            else:
                # Offline mode - use cached token
                self.current_user = cached_token
                return 'authenticated'  # Assume valid if not expired
                
        except Exception as e:
            print(f"Error checking auth status: {e}")
            return 'unauthenticated'
    
    def _should_refresh_token(self, token_data: Dict[str, Any]) -> bool:
        """Check if token should be refreshed"""
        try:
            expires_at = token_data.get('expires_at')
            if not expires_at:
                return True
            
            expires_datetime = datetime.fromisoformat(expires_at)
            # Refresh if token expires within 1 hour
            return datetime.now() > (expires_datetime - timedelta(hours=1))
            
        except:
            return True
    
    def _refresh_token(self) -> bool:
        """Refresh authentication token"""
        try:
            cached_token = self.local_storage.load_auth_token()
            if not cached_token or 'refresh_token' not in cached_token:
                return False
            
            # Set the session for refresh
            self.supabase.auth.set_session(cached_token['access_token'], cached_token['refresh_token'])
            
            # Refresh the session
            response = self.supabase.auth.refresh_session()
            
            if response.session:
                # Update cached token
                user_data = {
                    'user_id': cached_token['user_id'],
                    'email': cached_token['email'],
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at,
                    'user_metadata': cached_token.get('user_metadata', {})
                }
                
                cache_settings = self.config_manager.get_cache_settings()
                max_age_hours = cache_settings.get('token_cache_duration_hours', 168)
                
                return self.local_storage.store_auth_token(user_data, max_age_hours)
            
            return False
            
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return False
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user data"""
        if self.current_user:
            return self.current_user
        
        # Try to load from cache
        cached_token = self.local_storage.load_auth_token()
        if cached_token:
            self.current_user = cached_token
        
        return self.current_user
    
    def get_user_id(self) -> Optional[str]:
        """Get current user ID"""
        user = self.get_current_user()
        return user.get('user_id') if user else None
    
    def get_required_user_id(self) -> str:
        """Get current user ID, raising an exception if not authenticated"""
        user_id = self.get_user_id()
        if not user_id:
            raise Exception("No authenticated user found. Please log in to perform this operation.")
        return user_id
    
    def get_user_email(self) -> Optional[str]:
        """Get current user email"""
        user = self.get_current_user()
        return user.get('email') if user else None
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        status = self.check_auth_status()
        return status in ['authenticated', 'offline']
    
    def is_online(self) -> bool:
        """Check if internet connection is available"""
        return self._check_internet_connection()
    
    def get_auth_info(self) -> Dict[str, Any]:
        """Get comprehensive authentication information"""
        status = self.check_auth_status()
        user = self.get_current_user()
        
        info = {
            'status': status,
            'is_authenticated': self.is_authenticated(),
            'is_online': self.is_online(),
            'user_id': self.get_user_id(),
            'user_email': self.get_user_email(),
            'has_cached_token': self.local_storage.is_token_cached(),
            'has_cached_subscription': self.local_storage.is_subscription_cached()
        }
        
        if user:
            info['user_metadata'] = user.get('user_metadata', {})
            info['token_expires_at'] = user.get('expires_at')
        
        # Add cache info
        cache_info = self.local_storage.get_cache_info()
        info.update(cache_info)
        
        return info
    
    def validate_offline_access(self, grace_period_days: int = 14) -> Tuple[bool, str]:
        """
        Validate if user can access app offline
        
        Args:
            grace_period_days: Number of days to allow offline access
        
        Returns:
            Tuple of (can_access, message)
        """
        try:
            cached_token = self.local_storage.load_auth_token()
            
            if not cached_token:
                return False, "No cached authentication found. Please log in online."
            
            # Check when token was cached
            cached_at = cached_token.get('cached_at')
            if cached_at:
                cached_datetime = datetime.fromisoformat(cached_at)
                grace_period_end = cached_datetime + timedelta(days=grace_period_days)
                
                if datetime.now() > grace_period_end:
                    days_expired = (datetime.now() - grace_period_end).days
                    return False, f"Offline access expired {days_expired} days ago. Please connect to internet to verify your subscription."
            
            return True, "Offline access granted"
            
        except Exception as e:
            return False, f"Error validating offline access: {e}"
    
    def get_offline_access_info(self, grace_period_days: int = 14) -> Dict[str, Any]:
        """
        Get detailed offline access information
        
        Args:
            grace_period_days: Number of days to allow offline access
        
        Returns:
            Dict containing offline access details
        """
        try:
            cached_token = self.local_storage.load_auth_token()
            
            info = {
                'has_cached_token': cached_token is not None,
                'can_access_offline': False,
                'days_remaining': 0,
                'expires_at': None,
                'message': 'No cached authentication'
            }
            
            if cached_token:
                cached_at = cached_token.get('cached_at')
                if cached_at:
                    cached_datetime = datetime.fromisoformat(cached_at)
                    grace_period_end = cached_datetime + timedelta(days=grace_period_days)
                    now = datetime.now()
                    
                    info['expires_at'] = grace_period_end.isoformat()
                    info['cached_at'] = cached_at
                    
                    if now <= grace_period_end:
                        info['can_access_offline'] = True
                        info['days_remaining'] = (grace_period_end - now).days
                        info['message'] = f"Offline access granted. {info['days_remaining']} days remaining."
                    else:
                        days_expired = (now - grace_period_end).days
                        info['message'] = f"Offline access expired {days_expired} days ago."
            
            return info
            
        except Exception as e:
            return {
                'has_cached_token': False,
                'can_access_offline': False,
                'days_remaining': 0,
                'expires_at': None,
                'message': f'Error: {e}'
            }
    
    def attempt_reauthentication(self) -> Tuple[bool, str]:
        """
        Attempt to re-authenticate when coming back online
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self._check_internet_connection():
                return False, "No internet connection available"
            
            cached_token = self.local_storage.load_auth_token()
            if not cached_token:
                return False, "No cached authentication to refresh"
            
            # Try to refresh the token
            if self._refresh_token():
                return True, "Successfully re-authenticated"
            else:
                return False, "Failed to refresh authentication token"
                
        except Exception as e:
            return False, f"Error during re-authentication: {e}"
    
    def reset_password(self, email: str) -> Tuple[bool, str]:
        """
        Send password reset email
        
        Args:
            email: User's email address
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self._check_internet_connection():
                return False, "No internet connection available"
            
            print(f"🔄 Attempting password reset for: {email}")
            
            # Send password reset email
            response = self.supabase.auth.reset_password_email(email)
            
            print(f"📧 Password reset response: {response}")
            
            # Supabase reset_password_email returns None on success, not a truthy value
            # The actual success is indicated by no exception being thrown
            return True, f"Password reset link sent to {email}"
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Password reset error: {error_msg}")
            
            if "rate limit" in error_msg.lower():
                return False, "Too many reset attempts. Please wait a few minutes."
            elif "not found" in error_msg.lower():
                return False, "No account found with this email address."
            elif "invalid" in error_msg.lower():
                return False, "Please enter a valid email address."
            elif "email" in error_msg.lower() and "not confirmed" in error_msg.lower():
                return False, "Please verify your email address before resetting password."
            elif "disabled" in error_msg.lower():
                return False, "Password reset is currently disabled. Please contact support."
            else:
                return False, f"Failed to send reset email: {error_msg}"
    
    def is_single_device_enabled(self) -> bool:
        """
        Check if single-device authentication is enabled
        
        Returns:
            bool: True if single-device authentication is active
        """
        # For now, we'll assume custom implementation is always enabled
        # In a real implementation, you might check Supabase settings
        return True
    
    def force_logout_user_from_all_devices(self, user_id: str) -> Tuple[bool, str]:
        """
        Force logout a user from all devices (admin function)
        
        Args:
            user_id: User ID to force logout
            
        Returns:
            Tuple of (success, message)
        """
        try:
            success = self.session_manager.force_logout_user(user_id)
            if success:
                return True, f"User {user_id} has been logged out from all devices"
            else:
                return False, f"Failed to logout user {user_id}"
        except Exception as e:
            return False, f"Error force logging out user: {e}"
    
    def get_active_sessions_info(self) -> Dict[str, Any]:
        """
        Get information about active sessions (admin function)
        
        Returns:
            Dict containing active sessions information
        """
        try:
            sessions = self.session_manager.get_active_sessions()
            return {
                'active_sessions': sessions,
                'session_count': len(sessions),
                'single_device_enabled': self.is_single_device_enabled()
            }
        except Exception as e:
            return {
                'active_sessions': {},
                'session_count': 0,
                'single_device_enabled': False,
                'error': str(e)
            }
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            return self.session_manager.cleanup_all_expired_sessions()
        except Exception as e:
            print(f"Error cleaning up expired sessions: {e}")
            return 0
