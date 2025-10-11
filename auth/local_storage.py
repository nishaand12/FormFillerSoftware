"""
Local Storage Manager for authentication tokens and subscription data
Handles secure encryption/decryption and caching of sensitive data
"""

import os
import sys
import json
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Import path helper for proper writable locations
try:
    from app_paths import get_cache_path
except ImportError:
    # Fallback if app_paths not available
    def get_cache_path(relative_path: str = "") -> Path:
        """Fallback function for getting cache path"""
        app_name = "PhysioClinicAssistant"
        if sys.platform == 'darwin':
            base_path = Path.home() / "Library" / "Caches" / app_name
        else:
            base_path = Path.home() / ".cache" / app_name
        base_path.mkdir(parents=True, exist_ok=True)
        if relative_path:
            full_path = base_path / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            return full_path
        return base_path


class LocalStorageManager:
    """Manages secure local storage of authentication tokens and subscription data"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        # Use proper cache directory that's writable
        if cache_dir is None:
            self.cache_dir = get_cache_path("auth")
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache file paths
        self.token_cache_file = self.cache_dir / "auth_token.dat"
        self.subscription_cache_file = self.cache_dir / "subscription.dat"
        self.encryption_key_file = self.cache_dir / ".encryption_key"
        
        # Initialize encryption
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self) -> None:
        """Initialize or load encryption key"""
        try:
            if self.encryption_key_file.exists():
                # Load existing key
                with open(self.encryption_key_file, 'rb') as f:
                    key = f.read()
                self._fernet = Fernet(key)
            else:
                # Generate new key
                key = Fernet.generate_key()
                self._fernet = Fernet(key)
                
                # Save key securely
                with open(self.encryption_key_file, 'wb') as f:
                    f.write(key)
                
                # Set restrictive permissions on key file
                os.chmod(self.encryption_key_file, 0o600)
                
        except Exception as e:
            raise Exception(f"Failed to initialize encryption: {e}")
    
    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt string data"""
        if not self._fernet:
            raise Exception("Encryption not initialized")
        
        try:
            return self._fernet.encrypt(data.encode('utf-8'))
        except Exception as e:
            raise Exception(f"Failed to encrypt data: {e}")
    
    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt data to string"""
        if not self._fernet:
            raise Exception("Encryption not initialized")
        
        try:
            return self._fernet.decrypt(encrypted_data).decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to decrypt data: {e}")
    
    def _is_cache_expired(self, cache_file: Path, max_age_hours: int) -> bool:
        """Check if cache file is expired"""
        if not cache_file.exists():
            return True
        
        try:
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            max_age = timedelta(hours=max_age_hours)
            return file_age > max_age
        except Exception:
            return True
    
    def store_auth_token(self, token_data: Dict[str, Any], max_age_hours: int = 168) -> bool:
        """
        Store authentication token data securely
        
        Args:
            token_data: Dictionary containing token, user info, etc.
            max_age_hours: Maximum age in hours before expiration
        
        Returns:
            bool: True if stored successfully
        """
        try:
            # Add metadata
            token_data['cached_at'] = datetime.now().isoformat()
            token_data['expires_at'] = (datetime.now() + timedelta(hours=max_age_hours)).isoformat()
            
            # Serialize and encrypt
            json_data = json.dumps(token_data)
            encrypted_data = self._encrypt_data(json_data)
            
            # Write to file
            with open(self.token_cache_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(self.token_cache_file, 0o600)
            
            return True
            
        except Exception as e:
            print(f"Failed to store auth token: {e}")
            return False
    
    def load_auth_token(self) -> Optional[Dict[str, Any]]:
        """
        Load authentication token data
        
        Returns:
            Dict containing token data or None if not found/expired
        """
        try:
            if not self.token_cache_file.exists():
                return None
            
            # Read and decrypt
            with open(self.token_cache_file, 'rb') as f:
                encrypted_data = f.read()
            
            json_data = self._decrypt_data(encrypted_data)
            token_data = json.loads(json_data)
            
            # Check expiration
            expires_at = datetime.fromisoformat(token_data.get('expires_at', '1970-01-01'))
            if datetime.now() > expires_at:
                self.clear_auth_token()
                return None
            
            return token_data
            
        except Exception as e:
            print(f"Failed to load auth token: {e}")
            self.clear_auth_token()  # Clear corrupted cache
            return None
    
    def clear_auth_token(self) -> bool:
        """Clear stored authentication token"""
        try:
            if self.token_cache_file.exists():
                os.remove(self.token_cache_file)
            return True
        except Exception as e:
            print(f"Failed to clear auth token: {e}")
            return False
    
    def store_subscription_data(self, subscription_data: Dict[str, Any], max_age_hours: int = 24) -> bool:
        """
        Store subscription status data
        
        Args:
            subscription_data: Dictionary containing subscription info
            max_age_hours: Maximum age in hours before expiration
        
        Returns:
            bool: True if stored successfully
        """
        try:
            # Add metadata
            subscription_data['cached_at'] = datetime.now().isoformat()
            subscription_data['expires_at'] = (datetime.now() + timedelta(hours=max_age_hours)).isoformat()
            
            # Serialize and encrypt
            json_data = json.dumps(subscription_data)
            encrypted_data = self._encrypt_data(json_data)
            
            # Write to file
            with open(self.subscription_cache_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(self.subscription_cache_file, 0o600)
            
            return True
            
        except Exception as e:
            print(f"Failed to store subscription data: {e}")
            return False
    
    def load_subscription_data(self) -> Optional[Dict[str, Any]]:
        """
        Load subscription status data
        
        Returns:
            Dict containing subscription data or None if not found/expired
        """
        try:
            if not self.subscription_cache_file.exists():
                return None
            
            # Read and decrypt
            with open(self.subscription_cache_file, 'rb') as f:
                encrypted_data = f.read()
            
            json_data = self._decrypt_data(encrypted_data)
            subscription_data = json.loads(json_data)
            
            # Check expiration
            expires_at = datetime.fromisoformat(subscription_data.get('expires_at', '1970-01-01'))
            if datetime.now() > expires_at:
                self.clear_subscription_data()
                return None
            
            return subscription_data
            
        except Exception as e:
            print(f"Failed to load subscription data: {e}")
            self.clear_subscription_data()  # Clear corrupted cache
            return None
    
    def clear_subscription_data(self) -> bool:
        """Clear stored subscription data"""
        try:
            if self.subscription_cache_file.exists():
                os.remove(self.subscription_cache_file)
            return True
        except Exception as e:
            print(f"Failed to clear subscription data: {e}")
            return False
    
    def is_token_cached(self) -> bool:
        """Check if a valid token is cached"""
        return self.load_auth_token() is not None
    
    def is_subscription_cached(self) -> bool:
        """Check if subscription data is cached"""
        return self.load_subscription_data() is not None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached data"""
        info = {
            'has_token': self.is_token_cached(),
            'has_subscription': self.is_subscription_cached(),
            'token_file_exists': self.token_cache_file.exists(),
            'subscription_file_exists': self.subscription_cache_file.exists(),
            'encryption_key_exists': self.encryption_key_file.exists()
        }
        
        # Add file ages if they exist
        if self.token_cache_file.exists():
            token_data = self.load_auth_token()
            if token_data:
                info['token_cached_at'] = token_data.get('cached_at')
                info['token_expires_at'] = token_data.get('expires_at')
        
        if self.subscription_cache_file.exists():
            subscription_data = self.load_subscription_data()
            if subscription_data:
                info['subscription_cached_at'] = subscription_data.get('cached_at')
                info['subscription_expires_at'] = subscription_data.get('expires_at')
        
        return info
    
    def cleanup_expired_cache(self) -> Dict[str, bool]:
        """Clean up any expired cache files"""
        results = {
            'token_cleared': False,
            'subscription_cleared': False
        }
        
        try:
            # Check token cache
            if self.token_cache_file.exists():
                token_data = self.load_auth_token()
                if token_data is None:  # Expired or corrupted
                    results['token_cleared'] = True
            
            # Check subscription cache
            if self.subscription_cache_file.exists():
                subscription_data = self.load_subscription_data()
                if subscription_data is None:  # Expired or corrupted
                    results['subscription_cleared'] = True
            
        except Exception as e:
            print(f"Error during cache cleanup: {e}")
        
        return results
    
    def clear_all_cache(self) -> bool:
        """Clear all cached data"""
        try:
            token_cleared = self.clear_auth_token()
            subscription_cleared = self.clear_subscription_data()
            return token_cleared and subscription_cleared
        except Exception as e:
            print(f"Failed to clear all cache: {e}")
            return False
    
    def regenerate_encryption_key(self) -> bool:
        """
        Regenerate encryption key (will invalidate all existing cache)
        Use with caution - this will clear all cached data
        """
        try:
            # Clear all cache first
            self.clear_all_cache()
            
            # Remove old key
            if self.encryption_key_file.exists():
                os.remove(self.encryption_key_file)
            
            # Generate new key
            self._initialize_encryption()
            
            return True
            
        except Exception as e:
            print(f"Failed to regenerate encryption key: {e}")
            return False
