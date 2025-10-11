"""
Configuration manager for authentication settings
Handles loading and managing Supabase configuration
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """Manages authentication configuration from files and environment variables"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.supabase_config_file = self.config_dir / "supabase_config.json"
        self._config_cache: Optional[Dict[str, Any]] = None
    
    def load_supabase_config(self) -> Dict[str, Any]:
        """Load Supabase configuration from JSON file"""
        if self._config_cache is not None:
            return self._config_cache
        
        try:
            if not self.supabase_config_file.exists():
                raise FileNotFoundError(f"Supabase config file not found: {self.supabase_config_file}")
            
            with open(self.supabase_config_file, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = ['supabase_url', 'supabase_anon_key']
            for field in required_fields:
                if field not in config or not config[field]:
                    raise ValueError(f"Missing or empty required field: {field}")
            
            # Check for placeholder values
            if "YOUR_SUPABASE_URL_HERE" in config['supabase_url']:
                raise ValueError("Please update supabase_url in config file with your actual Supabase URL")
            if "YOUR_SUPABASE_ANON_KEY_HERE" in config['supabase_anon_key']:
                raise ValueError("Please update supabase_anon_key in config file with your actual Supabase anon key")
            
            self._config_cache = config
            return config
            
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to load Supabase configuration: {e}")
    
    def get_supabase_url(self) -> str:
        """Get Supabase URL from configuration"""
        config = self.load_supabase_config()
        return config['supabase_url']
    
    def get_supabase_anon_key(self) -> str:
        """Get Supabase anon key from configuration"""
        config = self.load_supabase_config()
        return config['supabase_anon_key']
    
    def get_auth_settings(self) -> Dict[str, Any]:
        """Get authentication settings from configuration"""
        config = self.load_supabase_config()
        return config.get('auth_settings', {})
    
    def get_subscription_settings(self) -> Dict[str, Any]:
        """Get subscription settings from configuration"""
        config = self.load_supabase_config()
        return config.get('subscription_settings', {})
    
    def get_cache_settings(self) -> Dict[str, Any]:
        """Get cache settings from configuration"""
        config = self.load_supabase_config()
        return config.get('cache_settings', {})
    
    def validate_config(self) -> bool:
        """Validate that configuration is properly set up"""
        try:
            config = self.load_supabase_config()
            
            # Check that URLs are properly formatted
            url = config['supabase_url']
            if not url.startswith('https://'):
                raise ValueError("Supabase URL must start with https://")
            
            # Check that anon key looks like a JWT
            anon_key = config['supabase_anon_key']
            if not anon_key or len(anon_key) < 100:
                raise ValueError("Supabase anon key appears to be invalid")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False
    
    def create_example_config(self) -> None:
        """Create an example configuration file"""
        example_config = {
            "supabase_url": "YOUR_SUPABASE_URL_HERE",
            "supabase_anon_key": "YOUR_SUPABASE_ANON_KEY_HERE",
            "auth_settings": {
                "redirect_url": "http://localhost:3000",
                "jwt_expiry": 3600,
                "refresh_token_expiry": 2592000
            },
            "subscription_settings": {
                "grace_period_days": 14,
                "trial_period_days": 14,
                "offline_check_interval_hours": 24
            },
            "cache_settings": {
                "token_cache_duration_hours": 168,
                "subscription_cache_duration_hours": 24,
                "encryption_key_file": "auth/cache/.encryption_key"
            }
        }
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        # Write example config
        with open(self.supabase_config_file, 'w') as f:
            json.dump(example_config, f, indent=2)
        
        print(f"Created example configuration file: {self.supabase_config_file}")
        print("Please edit this file with your actual Supabase credentials.")
