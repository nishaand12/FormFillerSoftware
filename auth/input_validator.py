"""
Input Validation and Sanitization Module
Provides comprehensive input validation, sanitization, and security checks
"""

import re
import html
import unicodedata
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime


class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    # Common patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
    NAME_PATTERN = re.compile(r'^[a-zA-Z\s\-\'\.]{2,50}$')
    CLINIC_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-\'\.&,()]{2,100}$')
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script.*?>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'vbscript:',  # VBScript protocol
        r'on\w+\s*=',  # Event handlers
        r'<iframe.*?>',  # Iframe tags
        r'<object.*?>',  # Object tags
        r'<embed.*?>',  # Embed tags
        r'<link.*?>',  # Link tags
        r'<meta.*?>',  # Meta tags
        r'<style.*?>',  # Style tags
        r'expression\s*\(',  # CSS expressions
        r'url\s*\(',  # CSS url functions
        r'@import',  # CSS imports
        r'<.*?>',  # Any HTML tags
    ]
    
    def __init__(self):
        self.compiled_dangerous_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]
    
    def sanitize_string(self, input_string: str, max_length: int = 1000, html_escape: bool = True) -> str:
        """
        Sanitize a string input by removing dangerous content and normalizing
        
        Args:
            input_string: The string to sanitize
            max_length: Maximum allowed length
            html_escape: Whether to HTML escape the string
            
        Returns:
            Sanitized string
        """
        if not isinstance(input_string, str):
            return ""
        
        # Truncate if too long
        if len(input_string) > max_length:
            input_string = input_string[:max_length]
        
        # Remove null bytes and control characters
        input_string = ''.join(char for char in input_string if ord(char) >= 32 or char in '\t\n\r')
        
        # Normalize Unicode
        input_string = unicodedata.normalize('NFKC', input_string)
        
        # HTML escape (only if requested)
        if html_escape:
            input_string = html.escape(input_string, quote=True)
        
        # Remove any remaining dangerous patterns
        for pattern in self.compiled_dangerous_patterns:
            input_string = pattern.sub('', input_string)
        
        # Strip whitespace
        input_string = input_string.strip()
        
        return input_string
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """
        Validate email address format and security
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email address is required"
        
        # Sanitize first
        email = self.sanitize_string(email, 254)  # RFC 5321 limit
        
        if not email:
            return False, "Email address is required"
        
        # Check for dangerous patterns
        if self._contains_dangerous_patterns(email):
            return False, "Email address contains invalid characters"
        
        # Validate format
        if not self.EMAIL_PATTERN.match(email):
            return False, "Please enter a valid email address"
        
        # Additional security checks
        if len(email) > 254:
            return False, "Email address is too long"
        
        if email.count('@') != 1:
            return False, "Email address must contain exactly one @ symbol"
        
        local, domain = email.split('@')
        if len(local) > 64:
            return False, "Email local part is too long"
        
        if len(domain) > 253:
            return False, "Email domain is too long"
        
        return True, ""
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength and security
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password is too long"
        
        # Check for dangerous patterns
        if self._contains_dangerous_patterns(password):
            return False, "Password contains invalid characters"
        
        # Check for common weak passwords
        weak_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        
        if password.lower() in weak_passwords:
            return False, "Password is too common. Please choose a stronger password"
        
        # Check for character variety
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_lower and has_upper and has_digit):
            return False, "Password must contain at least one uppercase letter, one lowercase letter, and one number"
        
        return True, ""
    
    def validate_name(self, name: str, field_name: str = "Name") -> Tuple[bool, str]:
        """
        Validate name fields (full name, clinic name, etc.)
        
        Args:
            name: Name to validate
            field_name: Name of the field for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, f"{field_name} is required"
        
        # Sanitize first (don't HTML escape names)
        name = self.sanitize_string(name, 100, html_escape=False)
        
        if not name:
            return False, f"{field_name} is required"
        
        # Check for dangerous patterns
        if self._contains_dangerous_patterns(name):
            return False, f"{field_name} contains invalid characters"
        
        # Validate format
        if not self.NAME_PATTERN.match(name):
            return False, f"{field_name} can only contain letters, spaces, hyphens, apostrophes, and periods"
        
        if len(name) < 2:
            return False, f"{field_name} must be at least 2 characters long"
        
        if len(name) > 50:
            return False, f"{field_name} is too long"
        
        return True, ""
    
    def validate_clinic_name(self, clinic_name: str) -> Tuple[bool, str]:
        """
        Validate clinic name
        
        Args:
            clinic_name: Clinic name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not clinic_name:
            return False, "Clinic name is required"
        
        # Sanitize first (don't HTML escape names)
        clinic_name = self.sanitize_string(clinic_name, 100, html_escape=False)
        
        if not clinic_name:
            return False, "Clinic name is required"
        
        # Check for dangerous patterns
        if self._contains_dangerous_patterns(clinic_name):
            return False, "Clinic name contains invalid characters"
        
        # Validate format
        if not self.CLINIC_PATTERN.match(clinic_name):
            return False, "Clinic name can only contain letters, numbers, spaces, and common punctuation"
        
        if len(clinic_name) < 2:
            return False, "Clinic name must be at least 2 characters long"
        
        if len(clinic_name) > 100:
            return False, "Clinic name is too long"
        
        return True, ""
    
    def validate_registration_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete registration data
        
        Args:
            data: Dictionary containing registration form data
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate full name
        name_valid, name_error = self.validate_name(data.get('full_name', ''), "Full name")
        if not name_valid:
            errors.append(name_error)
        
        # Validate email
        email_valid, email_error = self.validate_email(data.get('email', ''))
        if not email_valid:
            errors.append(email_error)
        
        # Validate clinic name
        clinic_valid, clinic_error = self.validate_clinic_name(data.get('clinic_name', ''))
        if not clinic_valid:
            errors.append(clinic_error)
        
        # Validate password
        password_valid, password_error = self.validate_password(data.get('password', ''))
        if not password_valid:
            errors.append(password_error)
        
        # Validate password confirmation (only if confirm_password is provided)
        confirm_password = data.get('confirm_password')
        if confirm_password is not None and confirm_password != '' and data.get('password') != confirm_password:
            errors.append("Passwords do not match")
        
        # Validate subscription plan
        valid_plans = ['trial', 'basic', 'premium', 'enterprise']
        if data.get('subscription_plan') not in valid_plans:
            errors.append("Please select a valid subscription plan")
        
        return len(errors) == 0, errors
    
    def validate_login_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate login form data
        
        Args:
            data: Dictionary containing login form data
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate email
        email_valid, email_error = self.validate_email(data.get('email', ''))
        if not email_valid:
            errors.append(email_error)
        
        # Validate password (basic check for login)
        password = data.get('password', '')
        if not password:
            errors.append("Password is required")
        elif len(password) > 128:
            errors.append("Password is too long")
        
        return len(errors) == 0, errors
    
    def _contains_dangerous_patterns(self, text: str) -> bool:
        """Check if text contains dangerous patterns"""
        for pattern in self.compiled_dangerous_patterns:
            if pattern.search(text):
                return True
        return False
    
    def sanitize_registration_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize all registration data
        
        Args:
            data: Raw registration data
            
        Returns:
            Sanitized registration data
        """
        sanitized = {
            'full_name': self.sanitize_string(data.get('full_name', ''), 50),
            'email': self.sanitize_string(data.get('email', ''), 254).lower(),
            'clinic_name': self.sanitize_string(data.get('clinic_name', ''), 100),
            'password': data.get('password', ''),  # Don't sanitize password
            'subscription_plan': data.get('subscription_plan', 'trial')
        }
        
        # Only include confirm_password if it was provided
        if 'confirm_password' in data:
            sanitized['confirm_password'] = data.get('confirm_password', '')
        
        return sanitized
    
    def sanitize_login_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize login data
        
        Args:
            data: Raw login data
            
        Returns:
            Sanitized login data
        """
        return {
            'email': self.sanitize_string(data.get('email', ''), 254).lower(),
            'password': data.get('password', '')  # Don't sanitize password
        }
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules for frontend display"""
        return {
            'email': {
                'required': True,
                'max_length': 254,
                'pattern': 'Valid email address format'
            },
            'password': {
                'required': True,
                'min_length': 8,
                'max_length': 128,
                'requirements': [
                    'At least 8 characters',
                    'At least one uppercase letter',
                    'At least one lowercase letter',
                    'At least one number'
                ]
            },
            'full_name': {
                'required': True,
                'min_length': 2,
                'max_length': 50,
                'pattern': 'Letters, spaces, hyphens, apostrophes, and periods only'
            },
            'clinic_name': {
                'required': True,
                'min_length': 2,
                'max_length': 100,
                'pattern': 'Letters, numbers, spaces, and common punctuation'
            }
        }
