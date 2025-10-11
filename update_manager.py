"""
Update Manager for handling application updates
Integrates with existing authentication and subscription system
"""

import os
import sys
import json
import requests
import hashlib
import zipfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import platform_utils


class UpdateManager:
    """Manages application updates and version checking"""
    
    def __init__(self, auth_manager=None):
        self.auth_manager = auth_manager
        self.update_server_url = "https://api.physioclinic.com/updates"  # Replace with actual URL
        self.current_version = self._get_current_version()
        self.update_cache_file = os.path.join(platform_utils.PlatformUtils.get_config_dir(), "update_cache.json")
        self.download_dir = os.path.join(platform_utils.PlatformUtils.get_app_data_dir(), "updates")
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.update_cache_file), exist_ok=True)
        os.makedirs(self.download_dir, exist_ok=True)
    
    def _get_current_version(self) -> str:
        """Get current application version"""
        try:
            # Try to read from version file
            version_file = os.path.join(os.path.dirname(__file__), "VERSION")
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    return f.read().strip()
            
            # Fallback to hardcoded version
            return "2.0.0"
        except:
            return "2.0.0"
    
    def check_for_updates(self, force_check: bool = False) -> Dict[str, Any]:
        """
        Check for available updates
        
        Args:
            force_check: Force online check even if cached data exists
        
        Returns:
            Dict containing update information
        """
        try:
            # Check if we should check for updates
            if not self._should_check_for_updates(force_check):
                return self._load_cached_update_info()
            
            # Check authentication
            if not self.auth_manager or not self.auth_manager.is_authenticated():
                return {
                    'status': 'unauthenticated',
                    'message': 'User not authenticated',
                    'update_available': False
                }
            
            # Check internet connection
            if not self.auth_manager.is_online():
                return {
                    'status': 'offline',
                    'message': 'No internet connection available',
                    'update_available': False,
                    'cached_info': self._load_cached_update_info()
                }
            
            # Get update information from server
            update_info = self._fetch_update_info()
            
            if update_info:
                # Cache the update information
                self._cache_update_info(update_info)
                
                # Check if update is available
                latest_version = update_info.get('version', '')
                update_available = self._is_newer_version(latest_version, self.current_version)
                
                return {
                    'status': 'success',
                    'update_available': update_available,
                    'current_version': self.current_version,
                    'latest_version': latest_version,
                    'update_info': update_info,
                    'message': f"Latest version {latest_version} available" if update_available else "Application is up to date"
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Failed to fetch update information',
                    'update_available': False
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error checking for updates: {e}',
                'update_available': False
            }
    
    def _should_check_for_updates(self, force_check: bool = False) -> bool:
        """Determine if we should check for updates"""
        if force_check:
            return True
        
        # Check cache age
        if os.path.exists(self.update_cache_file):
            try:
                with open(self.update_cache_file, 'r') as f:
                    cache_data = json.load(f)
                    last_check = datetime.fromisoformat(cache_data.get('last_check', '1970-01-01'))
                    
                    # Check every 24 hours
                    if datetime.now() - last_check < timedelta(hours=24):
                        return False
            except:
                pass
        
        return True
    
    def _fetch_update_info(self) -> Optional[Dict[str, Any]]:
        """Fetch update information from server"""
        try:
            # Get user authentication token
            token = self.auth_manager.get_access_token()
            if not token:
                return None
            
            # Make request to update server
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get platform-specific update info
            platform = platform_utils.PlatformUtils.get_platform_name().lower()
            architecture = platform_utils.PlatformUtils.get_system_info()['architecture']
            
            params = {
                'platform': platform,
                'architecture': architecture,
                'current_version': self.current_version
            }
            
            response = requests.get(
                f"{self.update_server_url}/check",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Update server returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching update info: {e}")
            return None
    
    def _cache_update_info(self, update_info: Dict[str, Any]) -> None:
        """Cache update information"""
        try:
            cache_data = {
                'last_check': datetime.now().isoformat(),
                'update_info': update_info
            }
            
            with open(self.update_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            print(f"Error caching update info: {e}")
    
    def _load_cached_update_info(self) -> Dict[str, Any]:
        """Load cached update information"""
        try:
            if os.path.exists(self.update_cache_file):
                with open(self.update_cache_file, 'r') as f:
                    cache_data = json.load(f)
                    update_info = cache_data.get('update_info', {})
                    
                    if update_info:
                        latest_version = update_info.get('version', '')
                        update_available = self._is_newer_version(latest_version, self.current_version)
                        
                        return {
                            'status': 'cached',
                            'update_available': update_available,
                            'current_version': self.current_version,
                            'latest_version': latest_version,
                            'update_info': update_info,
                            'message': f"Cached info: Latest version {latest_version}" if update_available else "Cached info: Application is up to date"
                        }
        except Exception as e:
            print(f"Error loading cached update info: {e}")
        
        return {
            'status': 'no_cache',
            'update_available': False,
            'message': 'No cached update information available'
        }
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Compare version strings to determine if version1 is newer than version2"""
        try:
            def version_tuple(version):
                return tuple(map(int, version.split('.')))
            
            return version_tuple(version1) > version_tuple(version2)
        except:
            return False
    
    def download_update(self, update_info: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Download update package
        
        Args:
            update_info: Update information from server
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get download URL
            download_url = update_info.get('download_url')
            if not download_url:
                return False, "No download URL provided"
            
            # Get file hash for verification
            expected_hash = update_info.get('file_hash')
            
            # Download file
            print(f"Downloading update from {download_url}")
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Save to temporary file
            temp_file = os.path.join(self.download_dir, f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file hash if provided
            if expected_hash:
                if not self._verify_file_hash(temp_file, expected_hash):
                    os.remove(temp_file)
                    return False, "Downloaded file hash verification failed"
            
            # Extract update package
            extract_dir = os.path.join(self.download_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Clean up temporary file
            os.remove(temp_file)
            
            return True, f"Update downloaded and extracted to {extract_dir}"
            
        except Exception as e:
            return False, f"Error downloading update: {e}"
    
    def _verify_file_hash(self, file_path: str, expected_hash: str) -> bool:
        """Verify file hash"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                return file_hash == expected_hash
        except:
            return False
    
    def install_update(self, update_info: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Install downloaded update
        
        Args:
            update_info: Update information
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # This is a simplified installation process
            # In a real implementation, you'd need more sophisticated handling
            
            extract_dir = os.path.join(self.download_dir, "extracted")
            if not os.path.exists(extract_dir):
                return False, "No extracted update files found"
            
            # Backup current application
            backup_dir = os.path.join(self.download_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup of current application
            app_dir = os.path.dirname(os.path.dirname(__file__))
            backup_app_dir = os.path.join(backup_dir, f"app_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            shutil.copytree(app_dir, backup_app_dir)
            
            # Install new files
            # This is a simplified version - in practice, you'd need more careful handling
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    src = os.path.join(root, file)
                    dst = os.path.join(app_dir, os.path.relpath(src, extract_dir))
                    
                    # Create destination directory if needed
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(src, dst)
            
            return True, "Update installed successfully. Please restart the application."
            
        except Exception as e:
            return False, f"Error installing update: {e}"
    
    def get_update_status(self) -> Dict[str, Any]:
        """Get current update status"""
        try:
            # Check if update is in progress
            update_in_progress = os.path.exists(os.path.join(self.download_dir, "extracted"))
            
            # Get cached update info
            cached_info = self._load_cached_update_info()
            
            return {
                'current_version': self.current_version,
                'update_in_progress': update_in_progress,
                'download_directory': self.download_dir,
                'cache_file': self.update_cache_file,
                'cached_info': cached_info
            }
            
        except Exception as e:
            return {
                'error': f"Error getting update status: {e}",
                'current_version': self.current_version
            }
    
    def cleanup_update_files(self) -> bool:
        """Clean up update files"""
        try:
            if os.path.exists(self.download_dir):
                shutil.rmtree(self.download_dir)
                os.makedirs(self.download_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error cleaning up update files: {e}")
            return False
    
    def create_version_file(self) -> None:
        """Create version file for the application"""
        try:
            version_file = os.path.join(os.path.dirname(__file__), "VERSION")
            with open(version_file, 'w') as f:
                f.write(self.current_version)
        except Exception as e:
            print(f"Error creating version file: {e}")


# Convenience functions
def check_for_updates(auth_manager=None, force_check: bool = False) -> Dict[str, Any]:
    """Check for available updates"""
    update_manager = UpdateManager(auth_manager)
    return update_manager.check_for_updates(force_check)


def download_and_install_update(update_info: Dict[str, Any], auth_manager=None) -> Tuple[bool, str]:
    """Download and install update"""
    update_manager = UpdateManager(auth_manager)
    
    # Download update
    success, message = update_manager.download_update(update_info)
    if not success:
        return False, message
    
    # Install update
    return update_manager.install_update(update_info)
