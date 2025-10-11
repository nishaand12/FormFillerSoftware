"""
Authentication module for Physiotherapy Clinic Assistant
Handles user authentication, subscription management, and offline functionality
"""

__version__ = "1.0.0"
__author__ = "Physiotherapy Clinic Assistant"

# Import main authentication components
from .config_manager import ConfigManager
from .local_storage import LocalStorageManager
from .session_manager import SessionManager
from .auth_manager import AuthManager
from .subscription_checker import SubscriptionChecker
from .login_gui import LoginGUI, show_login_dialog
from .network_manager import NetworkManager, OfflineIndicator

# Import security and UX components
from .input_validator import InputValidator
from .error_logger import ErrorLogger, SecurityEvent, LogLevel
from .rate_limiter import RateLimiter, RateLimitRule
from .loading_animations import LoadingAnimation, ProgressIndicator, StatusOverlay, LoadingManager
from .keyboard_shortcuts import KeyboardShortcuts, ShortcutAction, AccessibilityManager
from .user_onboarding import OnboardingManager, OnboardingStep

__all__ = [
    # Core authentication
    'ConfigManager',
    'LocalStorageManager',
    'SessionManager',
    'AuthManager',
    'SubscriptionChecker',
    'LoginGUI',
    'show_login_dialog',
    'NetworkManager',
    'OfflineIndicator',
    
    # Security components
    'InputValidator',
    'ErrorLogger',
    'SecurityEvent',
    'LogLevel',
    'RateLimiter',
    'RateLimitRule',
    
    # UX components
    'LoadingAnimation',
    'ProgressIndicator',
    'StatusOverlay',
    'LoadingManager',
    'KeyboardShortcuts',
    'ShortcutAction',
    'AccessibilityManager',
    'OnboardingManager',
    'OnboardingStep'
]
