#!/usr/bin/env python3
"""
Wrapper script to run the Physiotherapy Clinic Application
with proper multiprocessing resource management and comprehensive error logging
"""

import os
import sys
import signal
import atexit
import multiprocessing
import multiprocessing.resource_tracker
import traceback
from datetime import datetime
from pathlib import Path

# Set OpenMP environment variables to prevent runtime conflicts
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

# Set SSL certificate path for bundled app
if getattr(sys, '_MEIPASS', None):
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    os.environ['CURL_CA_BUNDLE'] = certifi.where()


def get_log_path():
    """Get path for startup log file"""
    # Try multiple locations for log file
    possible_paths = [
        Path.home() / "Library" / "Logs" / "PhysioClinicAssistant",
        Path.home() / ".physioclinic",
        Path("/tmp") / "physioclinic",
    ]
    
    for log_dir in possible_paths:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "startup.log"
            # Test write access
            with open(log_file, 'a') as f:
                f.write("")
            return log_file
        except:
            continue
    
    # Fallback to temp file
    return Path("/tmp") / "physioclinic_startup.log"


def log_startup(message, is_error=False):
    """Log startup messages to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    
    # Always print to console
    print(log_message)
    
    # Try to write to log file
    try:
        log_path = get_log_path()
        with open(log_path, 'a') as f:
            f.write(log_message + "\n")
            if is_error:
                f.write(traceback.format_exc() + "\n")
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")


def get_resource_path():
    """Get the correct resource path for PyInstaller bundled app"""
    if getattr(sys, '_MEIPASS', None):
        # Running in PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running in normal Python environment
        return Path(__file__).parent


def check_environment():
    """Check and log the runtime environment"""
    log_startup("=" * 80)
    log_startup("PHYSIOTHERAPY CLINIC ASSISTANT - STARTUP DIAGNOSTICS")
    log_startup("=" * 80)
    log_startup(f"Python Version: {sys.version}")
    log_startup(f"Python Executable: {sys.executable}")
    log_startup(f"Platform: {sys.platform}")
    log_startup(f"Current Working Directory: {os.getcwd()}")
    log_startup(f"Script Location: {__file__}")
    
    # Check if running in PyInstaller bundle
    if getattr(sys, '_MEIPASS', None):
        log_startup(f"Running in PyInstaller bundle: {sys._MEIPASS}")
        log_startup(f"Bundle contents:")
        try:
            bundle_path = Path(sys._MEIPASS)
            for item in sorted(bundle_path.iterdir())[:20]:  # First 20 items
                log_startup(f"  - {item.name}")
        except Exception as e:
            log_startup(f"Could not list bundle contents: {e}", is_error=True)
    else:
        log_startup("Running in development mode (not bundled)")
    
    # Check critical directories
    resource_path = get_resource_path()
    log_startup(f"Resource Path: {resource_path}")
    
    critical_paths = ['config', 'forms', 'auth', 'static']
    for path_name in critical_paths:
        path = resource_path / path_name
        exists = path.exists()
        log_startup(f"  {path_name}/: {'✓ EXISTS' if exists else '✗ MISSING'}")
    
    # Check Python path
    log_startup(f"Python Path:")
    for path in sys.path[:10]:  # First 10 paths
        log_startup(f"  - {path}")
    
    log_startup("=" * 80)


def cleanup_multiprocessing_resources():
    """Clean up multiprocessing resources to prevent semaphore leaks"""
    try:
        log_startup("🧹 Cleaning up multiprocessing resources...")
        
        # Clean up any remaining multiprocessing resources
        if hasattr(multiprocessing.resource_tracker, '_CLEANUP_CALLS'):
            for cleanup_call in multiprocessing.resource_tracker._CLEANUP_CALLS:
                try:
                    cleanup_call()
                except:
                    pass
        
        # Force cleanup of resource tracker
        if hasattr(multiprocessing.resource_tracker, '_REGISTRY'):
            multiprocessing.resource_tracker._REGISTRY.clear()
        
        log_startup("✅ Multiprocessing cleanup completed")
            
    except Exception as e:
        log_startup(f"Warning: Error during multiprocessing cleanup: {e}", is_error=True)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    log_startup(f"🔄 Received signal {signum}, cleaning up...")
    cleanup_multiprocessing_resources()
    sys.exit(0)


def show_error_dialog(error_message):
    """Show error dialog to user with log file location"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()
        
        log_path = get_log_path()
        full_message = (
            f"The application failed to start:\n\n"
            f"{error_message}\n\n"
            f"Detailed logs saved to:\n{log_path}\n\n"
            f"Please share this log file with support."
        )
        
        messagebox.showerror("Startup Error", full_message)
        root.destroy()
    except:
        # If even tkinter fails, just print
        pass


def main():
    """Main entry point with proper cleanup and error handling"""
    
    # Redirect stdout/stderr to log files for GUI app
    # This is CRITICAL for pvrecorder to work when launched from Finder
    if not sys.stdout.isatty():
        try:
            log_dir = Path.home() / "Library" / "Logs" / "PhysioClinicAssistant"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            stdout_log = log_dir / "app_output.log"
            stderr_log = log_dir / "app_errors.log"
            
            # Open log files in append mode
            sys.stdout = open(stdout_log, 'a', buffering=1)  # Line buffered
            sys.stderr = open(stderr_log, 'a', buffering=1)
            
            print(f"\n{'='*60}")
            print(f"App started at {datetime.now()}")
            print(f"stdout/stderr redirected to log files")
            print(f"{'='*60}\n")
        except Exception as e:
            # If redirection fails, continue anyway
            pass
    
    # Check environment first
    try:
        check_environment()
    except Exception as e:
        log_startup(f"Error during environment check: {e}", is_error=True)
    
    # Register cleanup functions
    atexit.register(cleanup_multiprocessing_resources)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set multiprocessing start method to prevent issues
    if sys.platform == 'darwin':
        try:
            multiprocessing.set_start_method('spawn', force=True)
            log_startup("✓ Set multiprocessing start method to 'spawn'")
        except Exception as e:
            log_startup(f"Warning: Could not set multiprocessing start method: {e}", is_error=True)
    
    try:
        log_startup("🚀 Starting application import...")
        
        # Add resource path to Python path if bundled
        resource_path = get_resource_path()
        if resource_path not in sys.path:
            sys.path.insert(0, str(resource_path))
            log_startup(f"✓ Added resource path to sys.path: {resource_path}")
        
        # Import and run the main application
        log_startup("📦 Importing main module...")
        from main import main as run_main_app
        
        log_startup("✓ Main module imported successfully")
        log_startup("🎯 Launching application...")
        
        run_main_app()
        
        log_startup("✅ Application exited normally")
        
    except ImportError as e:
        error_msg = f"Import Error: {str(e)}"
        log_startup(f"❌ {error_msg}", is_error=True)
        log_startup("This usually means a required Python package is missing or not bundled correctly.")
        show_error_dialog(error_msg)
        return 1
        
    except Exception as e:
        error_msg = f"Startup Error: {str(e)}"
        log_startup(f"❌ {error_msg}", is_error=True)
        show_error_dialog(error_msg)
        return 1
        
    except KeyboardInterrupt:
        log_startup("\n⚠️ Application interrupted by user")
        return 0
        
    finally:
        # Ensure cleanup happens
        try:
            cleanup_multiprocessing_resources()
        except:
            pass
    
    return 0


if __name__ == "__main__":
    # Critical: freeze_support() must be called first in frozen PyInstaller apps
    # to prevent duplicate app instances when multiprocessing spawns child processes
    multiprocessing.freeze_support()
    
    exit_code = main()
    sys.exit(exit_code)
