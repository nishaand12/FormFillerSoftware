#!/usr/bin/env python3
"""
Simplified Mac Build Script for Physiotherapy Clinic Assistant
Creates a proper macOS .app bundle and DMG installer
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


class SimpleMacBuilder:
    """Simplified Mac builder with progress tracking and timeout handling"""
    
    def __init__(self):
        self.version = self._get_version()
        self.app_name = "PhysioClinicAssistant"
        self.installer_name = "PhysioClinicAssistant-Installer"
        self.dmg_name = f"{self.app_name}-{self.version}-macOS.dmg"
        self.bundle_identifier = os.getenv("APP_BUNDLE_ID", "com.ceteasystems.physioclinicassistant")
        
        # Build directories
        self.build_dir = Path("build")
        self.dist_dir = Path("dist")
        self.dmg_dir = Path("dmg_contents")
        
        # Progress tracking
        self.current_step = 0
        self.total_steps = 4  # Prepare deps, clean, build, cleanup
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
            log_files = sorted(log_dir.glob("build_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old_log in log_files[5:]:  # Keep only 5 most recent
                old_log.unlink()
            
            # Create timestamped log file (single file per build)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"build_{timestamp}.log"
            
            # Write initial header
            with open(log_file, 'w') as f:
                f.write(f"Build Log for {self.app_name} v{self.version}\n")
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
        
        dirs_to_clean = [self.build_dir, self.dist_dir, self.dmg_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        # Clean auto-generated spec files (but preserve our source-controlled spec file)
        # PyInstaller may generate temporary spec files, but we want to keep PhysioClinicAssistant.spec
        main_spec_file = Path('PhysioClinicAssistant.spec')
        for spec_file in Path('.').glob('*.spec'):
            # Only delete if it's not our main source-controlled spec file
            # Use resolve() to handle absolute vs relative path comparisons
            if spec_file.resolve() != main_spec_file.resolve():
                self._log_progress(f"Removing auto-generated spec file: {spec_file.name}")
                spec_file.unlink()
        
        return True
    
    def prepare_dependencies(self) -> bool:
        """Ensure native/universal dependencies are ready before building"""
        self._log_progress("Preparing universal dependencies", "Dependencies")

        try:
            from build_support.prepare_universal_env import ensure_universal_runtime
        except ImportError as exc:
            self._log_progress(f"Failed to import dependency preparer: {exc}", "ERROR")
            return False

        success = ensure_universal_runtime()
        if success:
            self._log_progress("Universal dependency prep completed", "Dependencies")
        else:
            self._log_progress("Universal dependency prep failed", "ERROR")
        return success

    def _prepare_app_icon(self) -> Optional[str]:
        """Prepare application icon, converting PNG to ICNS if needed"""
        try:
            # Check if logo.png exists in static directory
            logo_png = Path("static/logo.png")
            if not logo_png.exists():
                self._log_progress("Logo file not found at static/logo.png", "WARNING")
                return None
            
            # Output path for ICNS file
            icns_path = Path("static/logo.icns")
            
            # Convert PNG to ICNS using sips (built-in macOS tool)
            # Create an iconset directory
            iconset_dir = Path("static/logo.iconset")
            if iconset_dir.exists():
                shutil.rmtree(iconset_dir)
            iconset_dir.mkdir(parents=True)
            
            # Generate different icon sizes
            icon_sizes = [
                (16, "16x16"),
                (32, "16x16@2x"),
                (32, "32x32"),
                (64, "32x32@2x"),
                (128, "128x128"),
                (256, "128x128@2x"),
                (256, "256x256"),
                (512, "256x256@2x"),
                (512, "512x512"),
                (1024, "512x512@2x"),
            ]
            
            # Use sips to resize PNG to different sizes
            for size, name in icon_sizes:
                output_file = iconset_dir / f"icon_{name}.png"
                subprocess.run([
                    "sips", "-z", str(size), str(size), 
                    str(logo_png), "--out", str(output_file)
                ], capture_output=True, check=False)
            
            # Convert iconset to icns
            subprocess.run([
                "iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)
            ], capture_output=True, check=False)
            
            # Clean up iconset directory
            if iconset_dir.exists():
                shutil.rmtree(iconset_dir)
            
            if icns_path.exists():
                self._log_progress(f"Icon prepared: {icns_path}")
                return str(icns_path)
            else:
                self._log_progress("Failed to create ICNS file", "WARNING")
                return None
                
        except Exception as e:
            self._log_progress(f"Error preparing icon: {e}", "WARNING")
            return None
    
    def build_main_app(self) -> bool:
        """Build main application using PyInstaller with proper macOS bundle"""
        self._log_progress("Building main application", "Main App")
        
        # Prepare icon path - convert PNG to ICNS if needed
        icon_path = self._prepare_app_icon()
        
        # Find spec file - try current working directory first (most reliable)
        spec_path = Path.cwd() / "PhysioClinicAssistant.spec"
        if not spec_path.exists():
            # Fallback: try script directory if __file__ is available
            try:
                script_dir = Path(__file__).parent.absolute()
                spec_path = script_dir / "PhysioClinicAssistant.spec"
            except NameError:
                pass  # __file__ not available, already tried cwd
        
        if spec_path.exists():
            # Use spec file - Info.plist is already configured in the spec file
            self._log_progress("Using spec file (Info.plist configured in spec)", "Main App")
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                str(spec_path),
            ]
            if not self._run_with_timeout(cmd, timeout=1200, description="PyInstaller main app"):
                return False
            
            # Verify Info.plist was created correctly
            app_path = self.dist_dir / f"{self.app_name}.app"
            info_plist_path = app_path / "Contents" / "Info.plist"
            if info_plist_path.exists():
                self._log_progress("Info.plist created from spec file")
                # Still need to set executable permissions
                return self._set_app_permissions(app_path)
            else:
                self._log_progress("Info.plist not found after build", "ERROR")
                return False
        else:
            # Fallback: command-line build (should not happen if spec file exists)
            self._log_progress("Spec file not found - using command-line build", "WARNING")
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                "--windowed",
                "--onedir",
                "--name", self.app_name,
                "--osx-bundle-identifier", self.bundle_identifier,
                "--target-arch", "arm64",
                "--icon", "static/logo.icns",
                "--collect-all", "pvrecorder",
                "--collect-all", "faster_whisper",
                "--collect-all", "llama_cpp",
                "--collect-all", "transformers",
                "--hidden-import", "tkinter",
                "--hidden-import", "_tkinter",
                "--add-data", "config:config",
                "--add-data", "forms:forms",
                "--add-data", "auth:auth",
                "--add-data", "static:static",
                "--add-data", "resources:resources",
                "--add-data", "app_paths.py:.",
                "--add-data", "setup_wizard.py:.",
                "--add-data", "system_checker.py:.",
                "--add-data", "config_validator.py:.",
                "--add-data", "uninstaller.py:.",
                "--add-data", "main.py:.",
                "--add-data", "VERSION:.",
                "--add-data", "README.md:.",
                "--add-data", "requirements.txt:.",
                "run_app.py",
            ]
            
            if not self._run_with_timeout(cmd, timeout=1200, description="PyInstaller main app"):
                return False
            
            # Customize Info.plist with additional permissions (fallback only)
            return self._customize_app_bundle(self.app_name)
    
    def _customize_app_bundle(self, app_name: str) -> bool:
        """Customize the .app bundle Info.plist created by PyInstaller"""
        self._log_progress("Customizing .app bundle", "App Bundle")
        
        # PyInstaller creates the .app bundle automatically with --windowed
        app_path = self.dist_dir / f"{app_name}.app"
        if not app_path.exists():
            self._log_progress(f"{app_name}.app not found", "ERROR")
            return False
        
        # Path to Info.plist
        info_plist_path = app_path / "Contents" / "Info.plist"
        if not info_plist_path.exists():
            self._log_progress("Info.plist not found", "ERROR")
            return False
        
        # Read existing Info.plist
        try:
            import plistlib
            with open(info_plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            # CRITICAL: Ensure required bundle type keys are present (prevents "bundle format is ambiguous" error)
            # These are required for macOS to recognize this as an application bundle
            plist_data['CFBundlePackageType'] = 'APPL'  # Application bundle type
            if 'CFBundleExecutable' not in plist_data:
                # Find the main executable in MacOS directory
                macos_dir = app_path / "Contents" / "MacOS"
                if macos_dir.exists():
                    executables = list(macos_dir.glob("*"))
                    if executables:
                        plist_data['CFBundleExecutable'] = executables[0].name
                    else:
                        plist_data['CFBundleExecutable'] = app_name
                else:
                    plist_data['CFBundleExecutable'] = app_name
            
            # Ensure CFBundleSignature is set (4-character code, typically '????' for generic)
            if 'CFBundleSignature' not in plist_data:
                plist_data['CFBundleSignature'] = '????'
            
            # Add/update required keys for functionality
            plist_data['CFBundleIdentifier'] = self.bundle_identifier
            plist_data['NSMicrophoneUsageDescription'] = "This app needs microphone access to record patient appointments."
            plist_data['NSAudioRecorderUsageDescription'] = "This app needs audio recording access to record patient appointments."
            
            # Bluetooth permissions for wireless audio devices
            plist_data['NSBluetoothAlwaysUsageDescription'] = "This app needs Bluetooth access to connect to wireless microphones and audio devices."
            plist_data['NSBluetoothPeripheralUsageDescription'] = "This app needs Bluetooth access to use wireless audio recording devices."
            
            # Additional system permissions
            plist_data['NSHighResolutionCapable'] = True
            plist_data['LSMinimumSystemVersion'] = "10.15.0"
            
            # Set display name to match what users see in the app
            plist_data['CFBundleDisplayName'] = "Physio Clinic Assistant"
            plist_data['CFBundleName'] = "Physio Clinic Assistant"
            
            # Set icon file if it exists
            resources_dir = app_path / "Contents" / "Resources"
            icon_file = resources_dir / "logo.icns"
            
            # PyInstaller should have copied the icon, but verify
            if icon_file.exists():
                plist_data['CFBundleIconFile'] = "logo.icns"
                self._log_progress("Icon file configured in Info.plist")
            else:
                # Check if PyInstaller used a different name
                possible_icons = list(resources_dir.glob("*.icns"))
                if possible_icons:
                    icon_name = possible_icons[0].name
                    plist_data['CFBundleIconFile'] = icon_name
                    self._log_progress(f"Icon file configured: {icon_name}")
                else:
                    self._log_progress("No icon file found in Resources", "WARNING")
            
            # Set LSApplicationCategoryType for proper categorization
            plist_data['LSApplicationCategoryType'] = "public.app-category.medical"
            
            # Ensure the app doesn't appear as a document-based app
            plist_data['LSUIElement'] = False
            
            # Set proper execution permissions
            plist_data['NSAppleEventsUsageDescription'] = "This app needs to access other applications for file operations."
            
            # Write back the modified plist
            with open(info_plist_path, 'wb') as f:
                plistlib.dump(plist_data, f)
            
            self._log_progress(f"Customized {app_name}.app Info.plist")
            
            # Set proper executable permissions on the main executable
            if not self._set_app_permissions(app_path):
                return False
            
            return True
            
        except Exception as e:
            self._log_progress(f"Error customizing Info.plist: {e}", "ERROR")
            return False
    
    def _set_app_permissions(self, app_path: Path) -> bool:
        """Set proper executable permissions on the app bundle"""
        try:
            # Find the main executable
            macos_dir = app_path / "Contents" / "MacOS"
            if not macos_dir.exists():
                self._log_progress("MacOS directory not found", "ERROR")
                return False
            
            # Get all executables in MacOS directory
            executables = list(macos_dir.iterdir())
            if not executables:
                self._log_progress("No executables found in MacOS directory", "ERROR")
                return False
            
            # Set executable permissions on all files in MacOS directory
            for executable in executables:
                if executable.is_file():
                    os.chmod(executable, 0o755)
                    self._log_progress(f"Set executable permissions on {executable.name}")
            
            return True
            
        except Exception as e:
            self._log_progress(f"Error setting app permissions: {e}", "ERROR")
            return False
    
    # Installer removed - using standard macOS drag-to-Applications approach
    
    
    # DMG creation moved to sign_and_notarize.py
    
    def cleanup(self) -> bool:
        """Clean up temporary files"""
        self._log_progress("Cleaning up", "Cleanup")
        
        # Clean build directories
        for dir_path in [self.build_dir, self.dmg_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        # Clean auto-generated spec files (but preserve our source-controlled spec file)
        # PyInstaller may generate temporary spec files, but we want to keep PhysioClinicAssistant.spec
        main_spec_file = Path('PhysioClinicAssistant.spec')
        for spec_file in Path('.').glob('*.spec'):
            # Only delete if it's not our main source-controlled spec file
            # Use resolve() to handle absolute vs relative path comparisons
            if spec_file.resolve() != main_spec_file.resolve():
                self._log_progress(f"Removing auto-generated spec file: {spec_file.name}")
                spec_file.unlink()
        
        # Clean up temporary icon files (but keep logo.icns if it exists - it's needed)
        iconset_dir = Path("static/logo.iconset")
        if iconset_dir.exists() and iconset_dir.is_dir():
            shutil.rmtree(iconset_dir)
        
        # Note: We keep logo.icns as it may be needed for the build
        
        return True
    
    def build_all(self) -> bool:
        """Execute the complete build process"""
        print(f"🚀 Building {self.app_name} v{self.version}")
        print("=" * 60)
        
        build_steps = [
            ("Prepare Dependencies", self.prepare_dependencies),
            ("Clean Build Directories", self.clean_build_dirs),
            ("Build Main Application", self.build_main_app),
            ("Cleanup", self.cleanup),
        ]
        
        for step_name, step_func in build_steps:
            if not step_func():
                print(f"\n❌ Build failed at: {step_name}")
                return False
        
        total_time = time.time() - self.start_time
        print("=" * 60)
        print(f"✅ Build completed successfully in {total_time:.1f}s")
        app_path = self.dist_dir / f"{self.app_name}.app"
        if app_path.exists():
            print(f"📦 Application: {app_path}")
            print(f"   Next step: Run sign_and_notarize.py to sign and create DMG")
        
        # Log completion
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Build completed successfully in {total_time:.1f}s\n")
                    f.write(f"Application: {app_path}\n")
                    f.write(f"{'='*80}\n")
                print(f"📝 Build log saved to: {self.log_file}")
            except Exception:
                pass
        
        return True


def main():
    """Main function with signal handling"""
    def signal_handler(signum, frame):
        print("\n⚠️  Build interrupted by user")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        builder = SimpleMacBuilder()
        success = builder.build_all()
        return 0 if success else 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())