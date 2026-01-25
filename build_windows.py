#!/usr/bin/env python3
"""
Windows Build Script for Physiotherapy Clinic Assistant
Creates a proper Windows executable and installer package
"""

import os
import sys
import subprocess
import shutil
import time
import signal
import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime


class WindowsBuilder:
    """Windows builder with progress tracking and timeout handling"""
    
    def __init__(self):
        self.version = self._get_version()
        self.app_name = "PhysioClinicAssistant"
        self.exe_name = f"{self.app_name}.exe"
        self.installer_name = f"{self.app_name}-{self.version}-Windows-Setup"
        
        # Build directories
        self.build_dir = Path("build")
        self.dist_dir = Path("dist")
        
        # Progress tracking
        self.current_step = 0
        self.total_steps = 4  # Clean, build, post-process, package
        self.start_time = time.time()
        
        # Single build log file (timestamped to avoid duplicates)
        self.log_file = self._setup_log_file()
        
    def _get_version(self) -> str:
        """Get application version from VERSION file"""
        try:
            with open("VERSION", 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "2.0.0"
    
    def _setup_log_file(self) -> Optional[Path]:
        """Setup a single build log file and clean up old logs"""
        try:
            # Create build log directory
            log_dir = Path("build_logs")
            log_dir.mkdir(exist_ok=True)
            
            # Clean up old log files (keep only last 5)
            log_files = sorted(log_dir.glob("build_windows_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old_log in log_files[5:]:  # Keep only 5 most recent
                old_log.unlink()
            
            # Create timestamped log file (single file per build)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"build_windows_{timestamp}.log"
            
            # Write initial header
            with open(log_file, 'w') as f:
                f.write(f"Windows Build Log for {self.app_name} v{self.version}\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
            
            return log_file
        except Exception as e:
            print(f"Warning: Could not setup log file: {e}")
            return None
    
    def _log_progress(self, message: str, step_name: str = ""):
        """Log progress with step counter and elapsed time"""
        self.current_step += 1
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s"
        
        if step_name:
            log_msg = f"[{self.current_step}/{self.total_steps}] {step_name} - {message} ({elapsed_str})"
        else:
            log_msg = f"[{self.current_step}/{self.total_steps}] {message} ({elapsed_str})"
        
        # Print to console
        print(log_msg)
        
        # Write to log file
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(log_msg + "\n")
            except Exception:
                pass  # Don't fail if log write fails
    
    def _run_with_timeout(self, cmd: list, timeout: int = 1800, description: str = "") -> bool:
        """Run command with timeout, progress tracking, and streaming output to log"""
        if description:
            self._log_progress(f"Starting: {description}")
        
        # Log the command being run
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(f"Command: {' '.join(cmd)}\n\n")
            except Exception:
                pass
        
        try:
            # Start process with streaming output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress with timeout and stream output
            start_time = time.time()
            last_output_time = start_time
            last_progress_time = start_time
            output_lines = []
            
            # Stream output in real-time
            while process.poll() is None:
                # Check timeout
                if time.time() - start_time > timeout:
                    process.terminate()
                    self._log_progress(f"Timeout after {timeout}s: {description}", "ERROR")
                    return False
                
                # Read available output (non-blocking)
                try:
                    line = process.stdout.readline()
                    if line:
                        line = line.rstrip()
                        output_lines.append(line)
                        last_output_time = time.time()
                        
                        # Write to log file immediately
                        if self.log_file:
                            try:
                                with open(self.log_file, 'a') as f:
                                    f.write(line + "\n")
                            except Exception:
                                pass
                        
                        # Print important lines to console (filter verbose output)
                        if any(keyword in line.lower() for keyword in ['error', 'warning', 'failed', 'success', 'complete']):
                            print(f"  {line}")
                    else:
                        # No output, check if we should show progress
                        if time.time() - last_progress_time > 30:  # Show progress every 30s
                            elapsed = time.time() - start_time
                            self._log_progress(f"Still running... ({elapsed:.0f}s elapsed)")
                            last_progress_time = time.time()
                        
                        # Small sleep to avoid busy-waiting
                        time.sleep(0.1)
                except Exception:
                    # If readline fails, wait a bit and check process status
                    time.sleep(0.1)
                    continue
            
            # Get any remaining output
            remaining_output = process.stdout.read()
            if remaining_output:
                output_lines.extend(remaining_output.rstrip().split('\n'))
                if self.log_file:
                    try:
                        with open(self.log_file, 'a') as f:
                            f.write(remaining_output)
                    except Exception:
                        pass
            
            # Check result
            if process.returncode == 0:
                self._log_progress(f"Completed: {description}")
                return True
            else:
                self._log_progress(f"Failed: {description}", "ERROR")
                # Write error summary to log
                if self.log_file:
                    try:
                        with open(self.log_file, 'a') as f:
                            f.write(f"\n{'='*80}\n")
                            f.write(f"BUILD FAILED - Return code: {process.returncode}\n")
                            f.write(f"{'='*80}\n")
                    except Exception:
                        pass
                # Print last few error lines to console
                error_lines = [line for line in output_lines if any(kw in line.lower() for kw in ['error', 'failed', 'exception'])]
                if error_lines:
                    print("\nLast error lines:")
                    for line in error_lines[-5:]:  # Show last 5 error lines
                        print(f"  {line}")
                return False
                
        except Exception as e:
            self._log_progress(f"Exception: {description} - {e}", "ERROR")
            if self.log_file:
                try:
                    with open(self.log_file, 'a') as f:
                        f.write(f"\nException: {e}\n")
                        import traceback
                        f.write(traceback.format_exc())
                except Exception:
                    pass
            return False
    
    def clean_build_dirs(self) -> bool:
        """Clean previous build artifacts"""
        self._log_progress("Cleaning previous builds", "Cleanup")
        
        dirs_to_clean = [self.build_dir, self.dist_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        # Clean auto-generated spec files (but preserve source-controlled spec file)
        main_spec_file = Path('PhysioClinicAssistant_windows.spec')
        for spec_file in Path('.').glob('*.spec'):
            if spec_file.resolve() != main_spec_file.resolve() and 'windows' not in spec_file.name.lower():
                # Only clean non-windows spec files that aren't our main one
                pass  # Keep all spec files for now
        
        return True
    
    def _prepare_app_icon(self) -> Optional[str]:
        """Prepare application icon for Windows (.ico format)"""
        try:
            # Check if logo.png exists in static directory
            logo_png = Path("static/logo.png")
            if not logo_png.exists():
                self._log_progress("Logo file not found at static/logo.png", "WARNING")
                return None
            
            # Output path for ICO file
            ico_path = Path("static/logo.ico")
            
            # If ICO already exists, use it
            if ico_path.exists():
                self._log_progress(f"Using existing icon: {ico_path}")
                return str(ico_path)
            
            # Try to convert PNG to ICO using Pillow
            try:
                from PIL import Image
                
                # Open the PNG image
                img = Image.open(logo_png)
                
                # Create ICO with multiple sizes
                icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                img.save(ico_path, format='ICO', sizes=icon_sizes)
                
                self._log_progress(f"Icon converted to ICO: {ico_path}")
                return str(ico_path)
                
            except ImportError:
                self._log_progress("Pillow not available for icon conversion", "WARNING")
                self._log_progress("Install Pillow with: pip install Pillow")
                return None
            except Exception as e:
                self._log_progress(f"Error converting icon: {e}", "WARNING")
                return None
                
        except Exception as e:
            self._log_progress(f"Error preparing icon: {e}", "WARNING")
            return None
    
    def build_main_app(self) -> bool:
        """Build main application using PyInstaller for Windows"""
        self._log_progress("Building main application for Windows", "Main App")
        
        # Prepare icon path
        icon_path = self._prepare_app_icon()
        
        # Check for Windows-specific spec file first
        spec_path = Path("PhysioClinicAssistant_windows.spec")
        
        if spec_path.exists():
            # Use spec file
            self._log_progress("Using Windows spec file", "Main App")
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                str(spec_path),
            ]
        else:
            # Build with command line arguments
            self._log_progress("Building with command-line arguments (no spec file found)", "Main App")
            
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                "--windowed",  # No console window
                "--onedir",
                "--name", self.app_name,
                "--collect-all", "pvrecorder",
                "--collect-all", "faster_whisper",
                "--collect-all", "llama_cpp",
                "--collect-all", "transformers",
                "--hidden-import", "tkinter",
                "--hidden-import", "_tkinter",
                "--add-data", "config;config",  # Windows uses semicolon
                "--add-data", "forms;forms",
                "--add-data", "auth;auth",
                "--add-data", "static;static",
                "--add-data", "resources;resources",
                "--add-data", "app_paths.py;.",
                "--add-data", "setup_wizard.py;.",
                "--add-data", "system_checker.py;.",
                "--add-data", "config_validator.py;.",
                "--add-data", "uninstaller.py;.",
                "--add-data", "main.py;.",
                "--add-data", "VERSION;.",
                "--add-data", "README.md;.",
                "--add-data", "requirements.txt;.",
            ]
            
            # Add icon if available
            if icon_path:
                cmd.extend(["--icon", icon_path])
            
            # Add main entry point
            cmd.append("run_app.py")
        
        if not self._run_with_timeout(cmd, timeout=1800, description="PyInstaller Windows build"):
            return False
        
        # Verify the build output
        exe_path = self.dist_dir / self.app_name / self.exe_name
        if not exe_path.exists():
            self._log_progress(f"Expected executable not found: {exe_path}", "ERROR")
            return False
        
        self._log_progress(f"Executable created: {exe_path}")
        return True
    
    def create_portable_package(self) -> bool:
        """Create a portable ZIP package of the application"""
        self._log_progress("Creating portable ZIP package", "Package")
        
        app_dir = self.dist_dir / self.app_name
        if not app_dir.exists():
            self._log_progress("Application directory not found", "ERROR")
            return False
        
        # Create ZIP file
        zip_name = f"{self.app_name}-{self.version}-Windows-Portable"
        zip_path = self.dist_dir / zip_name
        
        try:
            shutil.make_archive(str(zip_path), 'zip', self.dist_dir, self.app_name)
            self._log_progress(f"Created portable package: {zip_path}.zip")
            return True
        except Exception as e:
            self._log_progress(f"Failed to create ZIP package: {e}", "ERROR")
            return False
    
    def cleanup(self) -> bool:
        """Clean up temporary files"""
        self._log_progress("Cleaning up", "Cleanup")
        
        # Clean build directory (keep dist)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        return True
    
    def build_all(self) -> bool:
        """Execute the complete build process"""
        print(f"Building {self.app_name} v{self.version} for Windows")
        print("=" * 60)
        
        # Check if we're on Windows
        if sys.platform != 'win32':
            print("\nWARNING: This script is designed to run on Windows.")
            print("Cross-compilation from macOS/Linux is not supported.")
            print("Please run this script on a Windows machine.")
            print("\nContinuing anyway for testing purposes...\n")
        
        build_steps = [
            ("Clean Build Directories", self.clean_build_dirs),
            ("Build Main Application", self.build_main_app),
            ("Create Portable Package", self.create_portable_package),
            ("Cleanup", self.cleanup),
        ]
        
        for step_name, step_func in build_steps:
            if not step_func():
                print(f"\n Build failed at: {step_name}")
                return False
        
        total_time = time.time() - self.start_time
        print("=" * 60)
        print(f"Build completed successfully in {total_time:.1f}s")
        
        # Print output locations
        exe_path = self.dist_dir / self.app_name / self.exe_name
        zip_path = self.dist_dir / f"{self.app_name}-{self.version}-Windows-Portable.zip"
        
        if exe_path.exists():
            print(f"Executable: {exe_path}")
        if zip_path.exists():
            print(f"Portable Package: {zip_path}")
        
        # Log completion
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Build completed successfully in {total_time:.1f}s\n")
                    f.write(f"Executable: {exe_path}\n")
                    f.write(f"{'='*80}\n")
                print(f"Build log saved to: {self.log_file}")
            except Exception:
                pass
        
        return True


def main():
    """Main function with signal handling"""
    def signal_handler(signum, frame):
        print("\nBuild interrupted by user")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        builder = WindowsBuilder()
        success = builder.build_all()
        return 0 if success else 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
