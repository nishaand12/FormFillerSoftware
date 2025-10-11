"""
Subscription Checker for managing user subscription status
Handles online verification, offline validation, and feature restrictions
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from .config_manager import ConfigManager
from .local_storage import LocalStorageManager


class SubscriptionChecker:
    """Manages user subscription status and feature access"""
    
    def __init__(self, auth_manager=None):
        self.config_manager = ConfigManager()
        self.local_storage = LocalStorageManager()
        self.auth_manager = auth_manager
        
        # Subscription plans and their features
        self.subscription_plans = {
            'trial': {
                'name': 'Trial',
                'duration_days': 14,
                'features': ['recording', 'transcription', 'basic_forms'],
                'max_appointments_per_month': 5,
                'price': 0
            },
            'basic': {
                'name': 'Basic',
                'duration_days': 30,
                'features': ['recording', 'transcription', 'all_forms', 'appointment_history'],
                'max_appointments_per_month': 50,
                'price': 29
            },
            'premium': {
                'name': 'Premium',
                'duration_days': 30,
                'features': ['recording', 'transcription', 'all_forms', 'appointment_history', 'advanced_analytics'],
                'max_appointments_per_month': 200,
                'price': 79
            },
            'enterprise': {
                'name': 'Enterprise',
                'duration_days': 30,
                'features': ['recording', 'transcription', 'all_forms', 'appointment_history', 'advanced_analytics', 'custom_integrations'],
                'max_appointments_per_month': -1,  # Unlimited
                'price': 199
            }
        }
    
    def _check_internet_connection(self) -> bool:
        """Check if internet connection is available"""
        if self.auth_manager:
            return self.auth_manager.is_online()
        return False
    
    def get_subscription_from_supabase(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription status from Supabase (online only)
        
        Args:
            user_id: User ID to check subscription for
        
        Returns:
            Dict containing subscription data or None if not found
        """
        try:
            if not self._check_internet_connection():
                return None
            
            # This would normally query Supabase
            # For now, we'll return a mock subscription
            # In a real implementation, you'd query the user_profiles table
            
            if self.auth_manager and self.auth_manager.supabase:
                response = self.auth_manager.supabase.table('user_profiles').select('*').eq('id', user_id).execute()
                
                if response.data and len(response.data) > 0:
                    user_profile = response.data[0]
                    
                    subscription_data = {
                        'user_id': user_id,
                        'plan': user_profile.get('subscription_plan', 'trial'),
                        'status': user_profile.get('subscription_status', 'trial'),
                        'expires_at': user_profile.get('subscription_expires_at'),
                        'created_at': user_profile.get('created_at'),
                        'last_checked': datetime.now().isoformat()
                    }
                    
                    return subscription_data
            
            return None
            
        except Exception as e:
            print(f"Error getting subscription from Supabase: {e}")
            return None
    
    def check_subscription_status(self, force_online: bool = False) -> Tuple[str, str]:
        """
        Check user's subscription status
        
        Args:
            force_online: Force online check even if cached data exists
        
        Returns:
            Tuple of (status, message)
        """
        try:
            user_id = None
            if self.auth_manager:
                user_id = self.auth_manager.get_user_id()
            
            if not user_id:
                return 'unauthenticated', 'User not authenticated'
            
            # Try online check first if internet is available
            if self._check_internet_connection() and (force_online or not self.local_storage.is_subscription_cached()):
                online_subscription = self.get_subscription_from_supabase(user_id)
                
                if online_subscription:
                    # Cache the subscription data
                    cache_settings = self.config_manager.get_cache_settings()
                    max_age_hours = cache_settings.get('subscription_cache_duration_hours', 24)
                    
                    self.local_storage.store_subscription_data(online_subscription, max_age_hours)
                    return self._evaluate_subscription_status(online_subscription)
            
            # Fall back to cached data
            cached_subscription = self.local_storage.load_subscription_data()
            
            if cached_subscription:
                return self._evaluate_subscription_status(cached_subscription)
            
            # No subscription data available
            return 'unknown', 'No subscription information available'
            
        except Exception as e:
            return 'error', f'Error checking subscription: {e}'
    
    def _evaluate_subscription_status(self, subscription_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Evaluate subscription data and return status
        
        Args:
            subscription_data: Subscription data from cache or Supabase
        
        Returns:
            Tuple of (status, message)
        """
        try:
            plan = subscription_data.get('plan', 'trial')
            status = subscription_data.get('status', 'trial')
            expires_at = subscription_data.get('expires_at')
            
            # Check if subscription has expired
            if expires_at:
                try:
                    expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.now(expires_datetime.tzinfo) > expires_datetime:
                        return 'expired', f'Your {plan.title()} subscription has expired. Please renew to continue using the app.'
                except:
                    pass
            
            # Return status based on subscription data
            if status == 'active':
                return 'active', f'Active {plan.title()} subscription'
            elif status == 'trial':
                return 'trial', f'Trial subscription active'
            elif status == 'cancelled':
                return 'cancelled', f'Subscription cancelled. Access until expiry.'
            elif status == 'past_due':
                return 'past_due', f'Payment overdue. Please update your payment method.'
            else:
                return 'unknown', f'Unknown subscription status: {status}'
                
        except Exception as e:
            return 'error', f'Error evaluating subscription: {e}'
    
    def validate_feature_access(self, feature: str) -> Tuple[bool, str]:
        """
        Validate if user can access a specific feature
        
        Args:
            feature: Feature name to check
        
        Returns:
            Tuple of (can_access, message)
        """
        try:
            # Check authentication first
            if not self.auth_manager or not self.auth_manager.is_authenticated():
                return False, 'User not authenticated'
            
            # Get subscription status
            status, message = self.check_subscription_status()
            
            if status == 'unauthenticated':
                return False, 'User not authenticated'
            elif status == 'error':
                return False, f'Error checking subscription: {message}'
            elif status == 'expired':
                return False, 'Subscription expired. Please renew to access features.'
            
            # Get cached subscription data
            cached_subscription = self.local_storage.load_subscription_data()
            
            if not cached_subscription:
                # Default to trial if no subscription data
                plan = 'trial'
            else:
                plan = cached_subscription.get('plan', 'trial')
            
            # Check if feature is available in the plan
            plan_info = self.subscription_plans.get(plan, self.subscription_plans['trial'])
            available_features = plan_info.get('features', [])
            
            if feature in available_features:
                return True, f'Feature {feature} is available with {plan_info["name"]} plan'
            else:
                return False, f'Feature {feature} requires {plan_info["name"]} plan or higher'
                
        except Exception as e:
            return False, f'Error validating feature access: {e}'
    
    def get_available_features(self) -> List[str]:
        """Get list of available features for current user"""
        try:
            if not self.auth_manager or not self.auth_manager.is_authenticated():
                return []
            
            cached_subscription = self.local_storage.load_subscription_data()
            
            if not cached_subscription:
                plan = 'trial'
            else:
                plan = cached_subscription.get('plan', 'trial')
            
            plan_info = self.subscription_plans.get(plan, self.subscription_plans['trial'])
            return plan_info.get('features', [])
            
        except Exception as e:
            print(f'Error getting available features: {e}')
            return []
    
    def get_subscription_info(self) -> Dict[str, Any]:
        """Get comprehensive subscription information"""
        try:
            info = {
                'status': 'unknown',
                'plan': 'trial',
                'message': 'No subscription data',
                'features': [],
                'is_online': self._check_internet_connection(),
                'has_cached_data': self.local_storage.is_subscription_cached()
            }
            
            if not self.auth_manager or not self.auth_manager.is_authenticated():
                info['status'] = 'unauthenticated'
                info['message'] = 'User not authenticated'
                return info
            
            # Get subscription status
            status, message = self.check_subscription_status()
            info['status'] = status
            info['message'] = message
            
            # Get cached subscription data
            cached_subscription = self.local_storage.load_subscription_data()
            
            if cached_subscription:
                info['plan'] = cached_subscription.get('plan', 'trial')
                info['expires_at'] = cached_subscription.get('expires_at')
                info['created_at'] = cached_subscription.get('created_at')
                info['last_checked'] = cached_subscription.get('last_checked')
            
            # Get available features
            info['features'] = self.get_available_features()
            
            # Get plan details
            plan_info = self.subscription_plans.get(info['plan'], self.subscription_plans['trial'])
            info['plan_details'] = plan_info
            
            return info
            
        except Exception as e:
            return {
                'status': 'error',
                'plan': 'unknown',
                'message': f'Error getting subscription info: {e}',
                'features': [],
                'is_online': False,
                'has_cached_data': False
            }
    
    def check_grace_period(self, grace_period_days: int = 14) -> Tuple[bool, str]:
        """
        Check if user is within grace period for offline access
        
        Args:
            grace_period_days: Number of days to allow offline access
        
        Returns:
            Tuple of (in_grace_period, message)
        """
        try:
            cached_subscription = self.local_storage.load_subscription_data()
            
            if not cached_subscription:
                return False, 'No cached subscription data available'
            
            last_checked = cached_subscription.get('last_checked')
            if not last_checked:
                return False, 'No last check time available'
            
            try:
                last_checked_datetime = datetime.fromisoformat(last_checked)
                grace_period_end = last_checked_datetime + timedelta(days=grace_period_days)
                
                if datetime.now() > grace_period_end:
                    days_expired = (datetime.now() - grace_period_end).days
                    return False, f'Grace period expired {days_expired} days ago. Please connect to internet to verify subscription.'
                
                days_remaining = (grace_period_end - datetime.now()).days
                return True, f'Grace period active. {days_remaining} days remaining.'
                
            except:
                return False, 'Invalid last check time format'
                
        except Exception as e:
            return False, f'Error checking grace period: {e}'
    
    def get_offline_subscription_info(self, grace_period_days: int = 14) -> Dict[str, Any]:
        """
        Get detailed offline subscription information
        
        Args:
            grace_period_days: Number of days to allow offline access
        
        Returns:
            Dict containing offline subscription details
        """
        try:
            cached_subscription = self.local_storage.load_subscription_data()
            
            info = {
                'has_cached_data': cached_subscription is not None,
                'can_access_offline': False,
                'days_remaining': 0,
                'expires_at': None,
                'plan': 'trial',
                'status': 'unknown',
                'message': 'No cached subscription data'
            }
            
            if cached_subscription:
                info.update({
                    'plan': cached_subscription.get('plan', 'trial'),
                    'status': cached_subscription.get('status', 'unknown'),
                    'last_checked': cached_subscription.get('last_checked')
                })
                
                last_checked = cached_subscription.get('last_checked')
                if last_checked:
                    try:
                        last_checked_datetime = datetime.fromisoformat(last_checked)
                        grace_period_end = last_checked_datetime + timedelta(days=grace_period_days)
                        now = datetime.now()
                        
                        info['expires_at'] = grace_period_end.isoformat()
                        
                        if now <= grace_period_end:
                            info['can_access_offline'] = True
                            info['days_remaining'] = (grace_period_end - now).days
                            info['message'] = f'Offline access granted. {info["days_remaining"]} days remaining.'
                        else:
                            days_expired = (now - grace_period_end).days
                            info['message'] = f'Offline access expired {days_expired} days ago.'
                    except:
                        info['message'] = 'Invalid cached data format'
            
            return info
            
        except Exception as e:
            return {
                'has_cached_data': False,
                'can_access_offline': False,
                'days_remaining': 0,
                'expires_at': None,
                'plan': 'unknown',
                'status': 'error',
                'message': f'Error: {e}'
            }
    
    def attempt_subscription_refresh(self) -> Tuple[bool, str]:
        """
        Attempt to refresh subscription data when coming back online
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self._check_internet_connection():
                return False, "No internet connection available"
            
            if not self.auth_manager or not self.auth_manager.get_user_id():
                return False, "No authenticated user to check subscription for"
            
            # Force online subscription check
            status, message = self.check_subscription_status(force_online=True)
            
            if status in ['active', 'trial']:
                return True, "Successfully refreshed subscription data"
            else:
                return False, f"Subscription check failed: {message}"
                
        except Exception as e:
            return False, f"Error refreshing subscription: {e}"
    
    def get_subscription_plans(self) -> Dict[str, Dict[str, Any]]:
        """Get available subscription plans"""
        return self.subscription_plans.copy()
    
    def clear_subscription_cache(self) -> bool:
        """Clear cached subscription data"""
        return self.local_storage.clear_subscription_data()
