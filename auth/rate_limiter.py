"""
Rate Limiting System
Implements comprehensive rate limiting for authentication attempts and API calls
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class RateLimitRule:
    """Rate limit rule configuration"""
    max_attempts: int
    time_window_seconds: int
    block_duration_seconds: int = 0  # 0 means no additional blocking


class RateLimiter:
    """Comprehensive rate limiting system"""
    
    def __init__(self):
        # Track attempts by identifier (email, IP, etc.)
        self.attempts: Dict[str, deque] = defaultdict(deque)
        
        # Track blocked identifiers
        self.blocked_until: Dict[str, datetime] = {}
        
        # Default rate limit rules
        self.rules = {
            'login': RateLimitRule(
                max_attempts=5,
                time_window_seconds=900,  # 15 minutes
                block_duration_seconds=1800  # 30 minutes
            ),
            'registration': RateLimitRule(
                max_attempts=3,
                time_window_seconds=3600,  # 1 hour
                block_duration_seconds=3600  # 1 hour
            ),
            'password_reset': RateLimitRule(
                max_attempts=3,
                time_window_seconds=3600,  # 1 hour
                block_duration_seconds=1800  # 30 minutes
            ),
            'api_calls': RateLimitRule(
                max_attempts=100,
                time_window_seconds=3600,  # 1 hour
                block_duration_seconds=0
            )
        }
    
    def is_rate_limited(self, identifier: str, action_type: str = 'login') -> Tuple[bool, str, int]:
        """
        Check if an identifier is rate limited for a specific action
        
        Args:
            identifier: Unique identifier (email, IP, etc.)
            action_type: Type of action being attempted
            
        Returns:
            Tuple of (is_limited, reason, retry_after_seconds)
        """
        # Check if currently blocked
        if identifier in self.blocked_until:
            block_until = self.blocked_until[identifier]
            if datetime.now() < block_until:
                retry_after = int((block_until - datetime.now()).total_seconds())
                return True, f"Account temporarily blocked. Try again in {retry_after} seconds.", retry_after
            else:
                # Block period expired, remove from blocked list
                del self.blocked_until[identifier]
        
        # Get rate limit rule for this action
        rule = self.rules.get(action_type, self.rules['login'])
        
        # Get attempts for this identifier
        attempts = self.attempts[identifier]
        now = datetime.now()
        
        # Remove old attempts outside time window
        cutoff_time = now - timedelta(seconds=rule.time_window_seconds)
        while attempts and attempts[0] < cutoff_time:
            attempts.popleft()
        
        # Check if rate limit exceeded
        if len(attempts) >= rule.max_attempts:
            # Block the identifier if block duration is specified
            if rule.block_duration_seconds > 0:
                self.blocked_until[identifier] = now + timedelta(seconds=rule.block_duration_seconds)
                return True, f"Too many attempts. Account blocked for {rule.block_duration_seconds} seconds.", rule.block_duration_seconds
            else:
                # Just rate limited, no blocking
                oldest_attempt = attempts[0]
                retry_after = int((oldest_attempt + timedelta(seconds=rule.time_window_seconds) - now).total_seconds())
                return True, f"Rate limit exceeded. Try again in {retry_after} seconds.", retry_after
        
        return False, "", 0
    
    def record_attempt(self, identifier: str, action_type: str = 'login', success: bool = False):
        """
        Record an attempt for rate limiting
        
        Args:
            identifier: Unique identifier
            action_type: Type of action
            success: Whether the attempt was successful
        """
        now = datetime.now()
        
        # Record the attempt
        self.attempts[identifier].append(now)
        
        # If successful, clear some recent failed attempts for this identifier
        if success and action_type in ['login', 'registration']:
            # Remove last 2 failed attempts to allow for some retry flexibility
            attempts = self.attempts[identifier]
            for _ in range(min(2, len(attempts))):
                if attempts:
                    attempts.pop()
    
    def get_attempt_count(self, identifier: str, action_type: str = 'login') -> int:
        """Get current attempt count for an identifier"""
        rule = self.rules.get(action_type, self.rules['login'])
        attempts = self.attempts[identifier]
        now = datetime.now()
        
        # Remove old attempts
        cutoff_time = now - timedelta(seconds=rule.time_window_seconds)
        while attempts and attempts[0] < cutoff_time:
            attempts.popleft()
        
        return len(attempts)
    
    def get_remaining_attempts(self, identifier: str, action_type: str = 'login') -> int:
        """Get remaining attempts before rate limit"""
        rule = self.rules.get(action_type, self.rules['login'])
        current_attempts = self.get_attempt_count(identifier, action_type)
        return max(0, rule.max_attempts - current_attempts)
    
    def get_time_until_reset(self, identifier: str, action_type: str = 'login') -> int:
        """Get seconds until rate limit resets"""
        rule = self.rules.get(action_type, self.rules['login'])
        attempts = self.attempts[identifier]
        
        if not attempts:
            return 0
        
        now = datetime.now()
        oldest_attempt = attempts[0]
        reset_time = oldest_attempt + timedelta(seconds=rule.time_window_seconds)
        
        if reset_time <= now:
            return 0
        
        return int((reset_time - now).total_seconds())
    
    def clear_attempts(self, identifier: str, action_type: Optional[str] = None):
        """Clear attempts for an identifier"""
        if action_type:
            # Clear attempts for specific action type
            # Note: This is a simplified implementation
            # In a real system, you might want to track attempts per action type
            self.attempts[identifier].clear()
        else:
            # Clear all attempts for this identifier
            self.attempts[identifier].clear()
        
        # Also remove from blocked list
        if identifier in self.blocked_until:
            del self.blocked_until[identifier]
    
    def set_custom_rule(self, action_type: str, rule: RateLimitRule):
        """Set a custom rate limit rule for an action type"""
        self.rules[action_type] = rule
    
    def get_rate_limit_info(self, identifier: str, action_type: str = 'login') -> Dict[str, any]:
        """Get comprehensive rate limit information for an identifier"""
        rule = self.rules.get(action_type, self.rules['login'])
        current_attempts = self.get_attempt_count(identifier, action_type)
        remaining_attempts = self.get_remaining_attempts(identifier, action_type)
        time_until_reset = self.get_time_until_reset(identifier, action_type)
        is_blocked = identifier in self.blocked_until
        
        block_until = None
        if is_blocked:
            block_until = self.blocked_until[identifier].isoformat()
        
        return {
            'identifier': identifier,
            'action_type': action_type,
            'current_attempts': current_attempts,
            'max_attempts': rule.max_attempts,
            'remaining_attempts': remaining_attempts,
            'time_window_seconds': rule.time_window_seconds,
            'time_until_reset_seconds': time_until_reset,
            'is_blocked': is_blocked,
            'block_until': block_until,
            'block_duration_seconds': rule.block_duration_seconds
        }
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old attempt data to prevent memory leaks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for identifier in list(self.attempts.keys()):
            attempts = self.attempts[identifier]
            
            # Remove old attempts
            while attempts and attempts[0] < cutoff_time:
                attempts.popleft()
            
            # Remove identifier if no attempts left
            if not attempts:
                del self.attempts[identifier]
        
        # Clean up expired blocks
        now = datetime.now()
        expired_blocks = [
            identifier for identifier, block_until in self.blocked_until.items()
            if block_until < now
        ]
        
        for identifier in expired_blocks:
            del self.blocked_until[identifier]
    
    def get_statistics(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        total_identifiers = len(self.attempts)
        total_blocked = len(self.blocked_until)
        
        # Count attempts by action type (simplified)
        total_attempts = sum(len(attempts) for attempts in self.attempts.values())
        
        return {
            'total_identifiers_tracked': total_identifiers,
            'total_blocked_identifiers': total_blocked,
            'total_attempts_tracked': total_attempts,
            'rules_configured': len(self.rules),
            'memory_usage_estimate': total_attempts * 8  # Rough estimate in bytes
        }
