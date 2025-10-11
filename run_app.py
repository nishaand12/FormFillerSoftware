#!/usr/bin/env python3
"""
Wrapper script to run the Physiotherapy Clinic Application
with proper multiprocessing resource management
"""

import os
import sys
import signal
import atexit
import multiprocessing
import multiprocessing.resource_tracker

# Set OpenMP environment variables to prevent runtime conflicts
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

def cleanup_multiprocessing_resources():
    """Clean up multiprocessing resources to prevent semaphore leaks"""
    try:
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
            
    except Exception as e:
        print(f"Warning: Error during multiprocessing cleanup: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    cleanup_multiprocessing_resources()
    sys.exit(0)


def main():
    """Main entry point with proper cleanup"""
    # Register cleanup functions
    atexit.register(cleanup_multiprocessing_resources)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set multiprocessing start method to prevent issues
    if sys.platform == 'darwin':
        multiprocessing.set_start_method('spawn', force=True)
    
    try:
        # Import and run the main application
        from main import main as run_main_app
        run_main_app()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Error running application: {e}")
    finally:
        # Ensure cleanup happens
        cleanup_multiprocessing_resources()


if __name__ == "__main__":
    main()
