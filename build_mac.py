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
from pathlib import Path
from typing import Optional


class SimpleMacBuilder:
    """Simplified Mac builder with progress tracking and timeout handling"""
    
    def __init__(self):
        self.version = self._get_version()
        self.app_name = "PhysioClinicAssistant"
        self.installer_name = "PhysioClinicAssistant-Installer"
        self.dmg_name = f"{self.app_name}-{self.version}-macOS.dmg"
        
        # Build directories
        self.build_dir = Path("build")
        self.dist_dir = Path("dist")
        self.dmg_dir = Path("dmg_contents")
        
        # Code signing (set these environment variables)
        self.signing_identity = os.getenv("SIGNING_IDENTITY", "")
        self.notarization_team_id = os.getenv("NOTARIZATION_TEAM_ID", "")
        self.notarization_username = os.getenv("NOTARIZATION_USERNAME", "")
        self.notarization_password = os.getenv("NOTARIZATION_PASSWORD", "")
        
        # Progress tracking
        self.current_step = 0
        self.total_steps = 6  # Streamlined: clean, build, sign, notarize, dmg, cleanup
        self.start_time = time.time()
        
    def _get_version(self) -> str:
        """Get application version from VERSION file"""
        try:
            with open("VERSION", 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "2.0.0"
    
    def _log_progress(self, message: str, step_name: str = ""):
        """Log progress with step counter and elapsed time"""
        self.current_step += 1
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s"
        
        if step_name:
            print(f"[{self.current_step}/{self.total_steps}] {step_name} - {message} ({elapsed_str})")
        else:
            print(f"[{self.current_step}/{self.total_steps}] {message} ({elapsed_str})")
    
    def _run_with_timeout(self, cmd: list, timeout: int = 1800, description: str = "") -> bool:
        """Run command with timeout and progress tracking"""
        if description:
            self._log_progress(f"Starting: {description}")
        
        try:
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress with timeout
            start_time = time.time()
            last_output_time = start_time
            
            while process.poll() is None:
                # Check timeout
                if time.time() - start_time > timeout:
                    process.terminate()
                    self._log_progress(f"Timeout after {timeout}s: {description}", "ERROR")
                    return False
                
                # Check for output (indicates progress)
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # Still running, check if we should show progress
                    if time.time() - last_output_time > 30:  # Show progress every 30s
                        elapsed = time.time() - start_time
                        self._log_progress(f"Still running... ({elapsed:.0f}s elapsed)")
                        last_output_time = time.time()
                    continue
            
            # Get final result
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self._log_progress(f"Completed: {description}")
                return True
            else:
                self._log_progress(f"Failed: {description}", "ERROR")
                if stderr:
                    print(f"Error: {stderr}")
                return False
                
        except Exception as e:
            self._log_progress(f"Exception: {description} - {e}", "ERROR")
            return False
    
    def clean_build_dirs(self) -> bool:
        """Clean previous build artifacts"""
        self._log_progress("Cleaning previous builds", "Cleanup")
        
        dirs_to_clean = [self.build_dir, self.dist_dir, self.dmg_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        # Clean spec files
        for spec_file in Path('.').glob('*.spec'):
            spec_file.unlink()
        
        return True
    
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
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--windowed",  # Creates native macOS .app bundle
            "--onedir",    # Use onedir for better compatibility
            "--name", self.app_name,
            "--osx-bundle-identifier", "com.physioclinic.assistant",
        ]
        
        # Add icon if available
        if icon_path:
            cmd.extend(["--icon", icon_path])
        
        # Add data files
        cmd.extend([
            "--add-data", "config:config",
            "--add-data", "forms:forms",
            "--add-data", "auth:auth",
            "--add-data", "static:static",  # Include static directory with logo
            # "--add-data", "models:models",  # Exclude models - download separately
            "--add-data", "app_paths.py:.",  # Path helper for writable directories
            "--add-data", "setup_wizard.py:.",
            "--add-data", "system_checker.py:.",
            "--add-data", "config_validator.py:.",
            "--add-data", "uninstaller.py:.",
            "--add-data", "main.py:.",  # Include main.py as a resource
            "--add-data", "VERSION:.",
            "--add-data", "README.md:.",
            "--add-data", "requirements.txt:.",
        ])
        
        # Add hidden imports (comprehensive list for all dependencies)
        cmd.extend([
            # Core GUI
            "--hidden-import", "tkinter",
            "--hidden-import", "tkinter.ttk",
            "--hidden-import", "tkinter.messagebox",
            "--hidden-import", "tkinter.filedialog",
            "--hidden-import", "tkinter.scrolledtext",
            "--hidden-import", "_tkinter",
            
            # PIL/Pillow with tkinter
            "--hidden-import", "PIL",
            "--hidden-import", "PIL._tkinter_finder",
            "--hidden-import", "PIL.Image",
            "--hidden-import", "PIL.ImageTk",
            
            # System libraries
            "--hidden-import", "threading",
            "--hidden-import", "multiprocessing",
            "--hidden-import", "multiprocessing.pool",
            "--hidden-import", "multiprocessing.resource_tracker",
            "--hidden-import", "multiprocessing.synchronize",
            "--hidden-import", "queue",
            "--hidden-import", "plistlib",
            
            # Audio recording
            "--hidden-import", "pvrecorder",
            "--hidden-import", "sounddevice",
            
            # AI/ML models
            "--hidden-import", "faster_whisper",
            "--hidden-import", "faster_whisper.transcribe",
            "--hidden-import", "faster_whisper.vad",
            "--hidden-import", "faster_whisper.audio",
            "--hidden-import", "llama_cpp",
            "--hidden-import", "llama_cpp_python",
            "--hidden-import", "transformers",
            "--hidden-import", "transformers.models",
            
            # Scientific computing
            "--hidden-import", "numpy",
            "--hidden-import", "numpy.core",
            "--hidden-import", "scipy",
            "--hidden-import", "scipy.special",
            
            # PDF handling
            "--hidden-import", "reportlab",
            "--hidden-import", "reportlab.pdfgen",
            "--hidden-import", "pypdf",
            "--hidden-import", "PyPDF2",
            
            # Database and encryption
            "--hidden-import", "sqlite3",
            "--hidden-import", "cryptography",
            "--hidden-import", "cryptography.fernet",
            "--hidden-import", "cryptography.hazmat",
            "--hidden-import", "cryptography.hazmat.backends",
            "--hidden-import", "cryptography.hazmat.primitives",
            
            # Supabase and networking
            "--hidden-import", "supabase",
            "--hidden-import", "supabase.client",
            "--hidden-import", "supabase.lib",
            "--hidden-import", "postgrest",
            "--hidden-import", "realtime",
            "--hidden-import", "storage3",
            "--hidden-import", "httpx",
            "--hidden-import", "requests",
            "--hidden-import", "certifi",
            "--hidden-import", "ssl",
            "--hidden-import", "socket",
            
            # Utilities
            "--hidden-import", "json",
            "--hidden-import", "pkg_resources",
            "--hidden-import", "pkg_resources.py2_warn",
            "--hidden-import", "packaging",
        ])
        
        # Collect all submodules for complex packages (including native libraries)
        cmd.extend([
            "--collect-all", "pvrecorder",  # Includes libpv_recorder.dylib
            "--collect-all", "faster_whisper",
            "--collect-all", "llama_cpp",
            "--collect-all", "transformers",
        ])
        
        # Use run_app.py as entry point for better multiprocessing cleanup
        cmd.append("run_app.py")
        
        if not self._run_with_timeout(cmd, timeout=1200, description="PyInstaller main app"):
            return False
        
        # Customize Info.plist with additional permissions
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
            
            # Add/update required keys for functionality
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
    
    
    # Bundling step removed - main app goes directly in DMG
    
    def create_dmg(self) -> bool:
        """Create DMG with main app (standard macOS distribution)"""
        self._log_progress("Creating DMG", "DMG Creation")
        
        # Use main app directly (no installer wrapper)
        main_app = self.dist_dir / f"{self.app_name}.app"
        
        if not main_app.exists():
            self._log_progress("Main app not found", "ERROR")
            return False
        
        # Create DMG contents
        if self.dmg_dir.exists():
            shutil.rmtree(self.dmg_dir)
        self.dmg_dir.mkdir()
        
        # Copy main app to DMG
        app_dst = self.dmg_dir / f"{self.app_name}.app"
        shutil.copytree(main_app, app_dst)
        
        # Create Applications symlink
        applications_link = self.dmg_dir / "Applications"
        applications_link.symlink_to("/Applications")
        
        # Create README with comprehensive first-run instructions
        readme_content = f"""Physiotherapy Clinic Assistant

Version {self.version}

INSTALLATION INSTRUCTIONS:
1. Drag "PhysioClinicAssistant.app" to the Applications folder (or any location)
2. Navigate to where you installed the app
3. Right-click (or Control-click) on "PhysioClinicAssistant.app"
4. Select "Open" from the menu
5. Click "Open" in the security dialog that appears

IMPORTANT - FIRST LAUNCH:
The first time you open the app, macOS Gatekeeper will show a security warning.
This is normal for apps downloaded from the internet.

To open the app:
→ Right-click on the app and select "Open" (DO NOT double-click on first launch)
→ Click "Open" in the dialog that appears
→ After the first successful launch, you can open the app normally

If the app doesn't open or shows "damaged" error:
1. Open Terminal (Applications > Utilities > Terminal)
2. Type: xattr -cr /Applications/PhysioClinicAssistant.app
3. Press Enter and try opening the app again

FIRST RUN SETUP:
On first launch, the app will:
✓ Check system requirements
✓ Download AI models (~4.3GB) - this is a one-time download
✓ Configure your microphone
✓ Set up secure authentication

This initial setup may take 10-15 minutes depending on your internet connection.

SYSTEM REQUIREMENTS:
• macOS 10.15+ (Catalina or later)
• 8GB RAM minimum (16GB recommended)
• 10GB free disk space (plus 4.3GB for AI models)
• Microphone access
• Internet connection (for initial setup and model download)

PERMISSIONS:
The app will request permission to:
• Access your microphone (for recording appointments)
• Access files (for saving appointments and forms)

These permissions are required for the app to function properly.

TROUBLESHOOTING:
- If the app crashes on launch, ensure you have enough disk space
- If models fail to download, check your internet connection
- If you see "App is damaged" error, use the Terminal command above
- For persistent issues, try moving the app to /Applications folder

For support and documentation:
Email: support@physioclinic.com
Website: https://physioclinic.com/support

Thank you for using Physio Clinic Assistant!
"""
        
        with open(self.dmg_dir / "README.txt", 'w') as f:
            f.write(readme_content)
        
        # Flush filesystem buffers and wait (prevents "Resource busy" on GitHub Actions)
        subprocess.run(["sync"], check=False)
        time.sleep(2)
        
        # Detach any existing DMG mounts
        subprocess.run(["hdiutil", "detach", "/Volumes/PhysioClinicAssistant"], 
                      capture_output=True, check=False)
        
        # Create DMG using hdiutil (more reliable than create-dmg)
        temp_dmg = "temp_installer.dmg"
        
        # Remove temp DMG if it exists
        if Path(temp_dmg).exists():
            Path(temp_dmg).unlink()
        
        # Create temporary DMG with retry logic (GitHub Actions can have filesystem delays)
        max_retries = 3
        for attempt in range(max_retries):
            cmd = [
                "hdiutil", "create", "-srcfolder", str(self.dmg_dir),
                "-volname", "PhysioClinicAssistant",
                "-fs", "HFS+",
                "-ov",  # Overwrite if exists
                temp_dmg
            ]
            
            if self._run_with_timeout(cmd, timeout=300, description=f"Create temporary DMG (attempt {attempt + 1}/{max_retries})"):
                break
            
            if attempt < max_retries - 1:
                self._log_progress(f"Retrying after delay...", "WARNING")
                time.sleep(5)
            else:
                return False
        
        # Convert to final compressed DMG
        cmd = [
            "hdiutil", "convert", temp_dmg,
            "-format", "UDZO",
            "-o", self.dmg_name
        ]
        
        if not self._run_with_timeout(cmd, timeout=300, description="Compress DMG"):
            return False
        
        # Clean up
        if Path(temp_dmg).exists():
            Path(temp_dmg).unlink()
        shutil.rmtree(self.dmg_dir)
        
        # Verify DMG was created
        if not Path(self.dmg_name).exists():
            self._log_progress("DMG file not created", "ERROR")
            return False
        
        dmg_size = Path(self.dmg_name).stat().st_size / (1024 * 1024)  # MB
        self._log_progress(f"DMG created: {self.dmg_name} ({dmg_size:.1f} MB)")
        
        return True
    
    def cleanup(self) -> bool:
        """Clean up temporary files"""
        self._log_progress("Cleaning up", "Cleanup")
        
        # Clean build directories
        for dir_path in [self.build_dir, self.dmg_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        # Clean spec files
        for spec_file in Path('.').glob('*.spec'):
            spec_file.unlink()
        
        # Clean up temporary icon files
        icon_files = [
            Path("static/logo.icns"),
            Path("static/logo.iconset")
        ]
        for icon_file in icon_files:
            if icon_file.exists():
                if icon_file.is_dir():
                    shutil.rmtree(icon_file)
                else:
                    icon_file.unlink()
        
        return True
    
    def sign_app(self, app_path: Path) -> bool:
        """Sign the application with code signing certificate"""
        if not self.signing_identity:
            self._log_progress("No signing identity provided - skipping code signing", "WARNING")
            return True
        
        self._log_progress(f"Signing {app_path.name}", "Code Signing")
        
        # Sign the app bundle
        cmd = [
            "codesign", "--force", "--deep", "--sign", self.signing_identity,
            "--options", "runtime",
            "--timestamp",
            str(app_path)
        ]
        
        if not self._run_with_timeout(cmd, timeout=300, description=f"Sign {app_path.name}"):
            return False
        
        # Verify the signature
        cmd = ["codesign", "--verify", "--verbose", str(app_path)]
        if not self._run_with_timeout(cmd, timeout=60, description=f"Verify {app_path.name}"):
            return False
        
        self._log_progress(f"Successfully signed {app_path.name}")
        return True
    
    def notarize_app(self, app_path: Path) -> bool:
        """Notarize the application with Apple"""
        if not all([self.notarization_team_id, self.notarization_username, self.notarization_password]):
            self._log_progress("Notarization credentials not provided - skipping notarization", "WARNING")
            return True
        
        self._log_progress(f"Notarizing {app_path.name}", "Notarization")
        
        # Create zip file for notarization
        zip_path = app_path.with_suffix('.zip')
        cmd = ["ditto", "-c", "-k", "--keepParent", str(app_path), str(zip_path)]
        
        if not self._run_with_timeout(cmd, timeout=300, description="Create zip for notarization"):
            return False
        
        # Submit for notarization
        cmd = [
            "xcrun", "notarytool", "submit", str(zip_path),
            "--team-id", self.notarization_team_id,
            "--apple-id", self.notarization_username,
            "--password", self.notarization_password,
            "--wait"
        ]
        
        if not self._run_with_timeout(cmd, timeout=1800, description="Submit for notarization"):  # 30 min timeout
            return False
        
        # Staple the notarization
        cmd = ["xcrun", "stapler", "staple", str(app_path)]
        if not self._run_with_timeout(cmd, timeout=300, description="Staple notarization"):
            return False
        
        # Clean up zip file
        if zip_path.exists():
            zip_path.unlink()
        
        self._log_progress(f"Successfully notarized {app_path.name}")
        return True
    
    def sign_applications(self) -> bool:
        """Sign main application"""
        self._log_progress("Signing application", "Code Signing")
        
        # Sign main app only (no installer)
        main_app_path = self.dist_dir / f"{self.app_name}.app"
        if main_app_path.exists():
            if not self.sign_app(main_app_path):
                return False
        
        return True
    
    def notarize_applications(self) -> bool:
        """Notarize main application"""
        self._log_progress("Notarizing application", "Notarization")
        
        # Notarize main app only
        main_app_path = self.dist_dir / f"{self.app_name}.app"
        if main_app_path.exists():
            if not self.notarize_app(main_app_path):
                return False
        
        return True
    
    def build_all(self) -> bool:
        """Execute the complete build process"""
        print(f"🚀 Building {self.app_name} v{self.version}")
        print("=" * 60)
        
        build_steps = [
            ("Clean Build Directories", self.clean_build_dirs),
            ("Build Main Application", self.build_main_app),
            ("Sign Application", self.sign_applications),
            ("Notarize Application", self.notarize_applications),
            ("Create DMG", self.create_dmg),
            ("Cleanup", self.cleanup),
        ]
        
        for step_name, step_func in build_steps:
            if not step_func():
                print(f"\n❌ Build failed at: {step_name}")
                return False
        
        total_time = time.time() - self.start_time
        print("=" * 60)
        print(f"✅ Build completed successfully in {total_time:.1f}s")
        print(f"📦 DMG file: {self.dmg_name}")
        
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