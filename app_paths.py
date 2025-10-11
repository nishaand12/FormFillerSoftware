"""
Application Path Manager
Provides proper file paths for macOS app bundles and development environments
"""

import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str = "") -> Path:
    """
    Get the absolute path to a bundled resource file (read-only).
    Use this for accessing config files, forms, templates, etc.
    
    Args:
        relative_path: Path relative to the resource directory
        
    Returns:
        Absolute path to the resource
    """
    if getattr(sys, '_MEIPASS', None):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent
    
    if relative_path:
        return base_path / relative_path
    return base_path


def get_writable_path(relative_path: str = "") -> Path:
    """
    Get a writable path in the user's Application Support directory.
    Use this for databases, user data, models, etc.
    
    Args:
        relative_path: Path relative to the application support directory
        
    Returns:
        Absolute path in Application Support
    """
    app_name = "PhysioClinicAssistant"
    
    if sys.platform == 'darwin':
        # macOS: ~/Library/Application Support/PhysioClinicAssistant/
        base_path = Path.home() / "Library" / "Application Support" / app_name
    elif sys.platform == 'win32':
        # Windows: %APPDATA%\PhysioClinicAssistant\
        base_path = Path(os.getenv('APPDATA', Path.home())) / app_name
    else:
        # Linux: ~/.local/share/PhysioClinicAssistant/
        base_path = Path.home() / ".local" / "share" / app_name
    
    # Create base directory if it doesn't exist
    base_path.mkdir(parents=True, exist_ok=True)
    
    if relative_path:
        full_path = base_path / relative_path
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path
    return base_path


def get_cache_path(relative_path: str = "") -> Path:
    """
    Get a writable path in the user's Cache directory.
    Use this for authentication tokens, temporary caches, etc.
    
    Args:
        relative_path: Path relative to the cache directory
        
    Returns:
        Absolute path in Caches
    """
    app_name = "PhysioClinicAssistant"
    
    if sys.platform == 'darwin':
        # macOS: ~/Library/Caches/PhysioClinicAssistant/
        base_path = Path.home() / "Library" / "Caches" / app_name
    elif sys.platform == 'win32':
        # Windows: %LOCALAPPDATA%\PhysioClinicAssistant\Cache\
        base_path = Path(os.getenv('LOCALAPPDATA', Path.home())) / app_name / "Cache"
    else:
        # Linux: ~/.cache/PhysioClinicAssistant/
        base_path = Path.home() / ".cache" / app_name
    
    # Create base directory if it doesn't exist
    base_path.mkdir(parents=True, exist_ok=True)
    
    if relative_path:
        full_path = base_path / relative_path
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path
    return base_path


def get_log_path(relative_path: str = "") -> Path:
    """
    Get a writable path in the user's Logs directory.
    Use this for application logs.
    
    Args:
        relative_path: Path relative to the logs directory
        
    Returns:
        Absolute path in Logs
    """
    app_name = "PhysioClinicAssistant"
    
    if sys.platform == 'darwin':
        # macOS: ~/Library/Logs/PhysioClinicAssistant/
        base_path = Path.home() / "Library" / "Logs" / app_name
    elif sys.platform == 'win32':
        # Windows: %LOCALAPPDATA%\PhysioClinicAssistant\Logs\
        base_path = Path(os.getenv('LOCALAPPDATA', Path.home())) / app_name / "Logs"
    else:
        # Linux: ~/.local/share/PhysioClinicAssistant/logs/
        base_path = Path.home() / ".local" / "share" / app_name / "logs"
    
    # Create base directory if it doesn't exist
    base_path.mkdir(parents=True, exist_ok=True)
    
    if relative_path:
        full_path = base_path / relative_path
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path
    return base_path


def get_temp_path(relative_path: str = "") -> Path:
    """
    Get a temporary path for processing files.
    Use this for temporary audio files, processing artifacts, etc.
    
    Args:
        relative_path: Path relative to the temp directory
        
    Returns:
        Absolute path in temp directory
    """
    import tempfile
    app_name = "PhysioClinicAssistant"
    
    # Use system temp directory with app-specific subdirectory
    base_path = Path(tempfile.gettempdir()) / app_name
    base_path.mkdir(parents=True, exist_ok=True)
    
    if relative_path:
        full_path = base_path / relative_path
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path
    return base_path


# Convenience functions for common paths
def get_data_dir() -> Path:
    """Get the data directory for patient files and appointments"""
    return get_writable_path("data")


def get_database_path() -> Path:
    """Get the path to the SQLite database"""
    return get_writable_path("data/clinic_data.db")


def get_models_dir() -> Path:
    """Get the directory for AI models"""
    return get_writable_path("models")


def get_config_dir() -> Path:
    """Get the directory for config files (read-only from bundle)"""
    return get_resource_path("config")


def get_forms_dir() -> Path:
    """Get the directory for form templates (read-only from bundle)"""
    return get_resource_path("forms")


# Print diagnostic information if run directly
if __name__ == "__main__":
    print("Application Path Configuration")
    print("=" * 60)
    print(f"Resource Path (read-only): {get_resource_path()}")
    print(f"Writable Path: {get_writable_path()}")
    print(f"Cache Path: {get_cache_path()}")
    print(f"Log Path: {get_log_path()}")
    print(f"Temp Path: {get_temp_path()}")
    print()
    print("Common Paths:")
    print(f"  Data Directory: {get_data_dir()}")
    print(f"  Database: {get_database_path()}")
    print(f"  Models Directory: {get_models_dir()}")
    print(f"  Config Directory: {get_config_dir()}")
    print(f"  Forms Directory: {get_forms_dir()}")

