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
        self.total_steps = 6  # Streamlined with native PyInstaller bundles
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
    
    def build_main_app(self) -> bool:
        """Build main application using PyInstaller with proper macOS bundle"""
        self._log_progress("Building main application", "Main App")
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--windowed",  # Creates native macOS .app bundle
            "--onedir",    # Use onedir for better compatibility
            "--name", self.app_name,
            "--osx-bundle-identifier", "com.physioclinic.assistant",
            "--add-data", "config:config",
            "--add-data", "forms:forms",
            "--add-data", "auth:auth",
            # "--add-data", "models:models",  # Exclude models - download separately
            "--add-data", "setup_wizard.py:.",
            "--add-data", "system_checker.py:.",
            "--add-data", "config_validator.py:.",
            "--add-data", "uninstaller.py:.",
            "--add-data", "VERSION:.",
            "--add-data", "README.md:.",
            "--add-data", "requirements.txt:.",
            "--hidden-import", "tkinter",
            "--hidden-import", "tkinter.ttk",
            "--hidden-import", "tkinter.messagebox",
            "--hidden-import", "tkinter.filedialog",
            "--hidden-import", "threading",
            "--hidden-import", "multiprocessing",
            "--hidden-import", "pvrecorder",
            "--hidden-import", "faster_whisper",
            "--hidden-import", "llama_cpp_python",
            "--hidden-import", "cryptography",
            "--hidden-import", "supabase",
            "--hidden-import", "numpy",
            "--hidden-import", "scipy",
            "--hidden-import", "PIL",
            "--hidden-import", "reportlab",
            "--hidden-import", "sounddevice",
            "--hidden-import", "sqlite3",
            "main.py"
        ]
        
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
            
            # Add/update required keys
            plist_data['NSMicrophoneUsageDescription'] = "This app needs microphone access to record patient appointments."
            plist_data['NSAudioRecorderUsageDescription'] = "This app needs audio recording access to record patient appointments."
            plist_data['NSHighResolutionCapable'] = True
            plist_data['LSMinimumSystemVersion'] = "10.15.0"
            plist_data['CFBundleDisplayName'] = app_name
            
            # Write back the modified plist
            with open(info_plist_path, 'wb') as f:
                plistlib.dump(plist_data, f)
            
            self._log_progress(f"Customized {app_name}.app Info.plist")
            return True
            
        except Exception as e:
            self._log_progress(f"Error customizing Info.plist: {e}", "ERROR")
            return False
    
    def build_installer_app(self) -> bool:
        """Build installer application"""
        self._log_progress("Building installer application", "Installer")
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--windowed",  # Creates native macOS .app bundle
            "--onedir",
            "--name", self.installer_name,
            "--osx-bundle-identifier", "com.physioclinic.installer",
            "--add-data", "config:config",
            "--add-data", "forms:forms",
            "--add-data", "auth:auth",
            # "--add-data", "models:models",  # Exclude models - download separately
            "--add-data", "setup_wizard.py:.",
            "--add-data", "system_checker.py:.",
            "--add-data", "config_validator.py:.",
            "--add-data", "uninstaller.py:.",
            "--add-data", "main.py:.",
            "--add-data", "VERSION:.",
            "--add-data", "README.md:.",
            "--add-data", "requirements.txt:.",
            "--hidden-import", "tkinter",
            "--hidden-import", "tkinter.ttk",
            "--hidden-import", "tkinter.messagebox",
            "--hidden-import", "tkinter.filedialog",
            "mac_installer.py"
        ]
        
        if not self._run_with_timeout(cmd, timeout=600, description="PyInstaller installer"):
            return False
        
        # Customize Info.plist
        return self._customize_app_bundle(self.installer_name)
    
    
    def bundle_app_into_installer(self) -> bool:
        """Bundle the main app inside the installer (must happen BEFORE signing)"""
        self._log_progress("Bundling main app into installer", "Bundling")
        
        installer_app = self.dist_dir / f"{self.installer_name}.app"
        main_app = self.dist_dir / f"{self.app_name}.app"
        
        if not installer_app.exists():
            self._log_progress("Installer app not found", "ERROR")
            return False
        
        if not main_app.exists():
            self._log_progress("Main app not found", "ERROR")
            return False
        
        # Copy main app into installer's Resources directory
        installer_resources = installer_app / "Contents" / "Resources"
        bundled_app_path = installer_resources / f"{self.app_name}.app"
        
        # Remove if it already exists (from previous build)
        if bundled_app_path.exists():
            shutil.rmtree(bundled_app_path)
        
        self._log_progress(f"Copying {self.app_name}.app into installer...")
        shutil.copytree(main_app, bundled_app_path)
        self._log_progress(f"✅ Main app bundled into installer successfully")
        
        return True
    
    def create_dmg(self) -> bool:
        """Create DMG installer"""
        self._log_progress("Creating DMG installer", "DMG Creation")
        
        # Installer should already have main app bundled at this point
        installer_app = self.dist_dir / f"{self.installer_name}.app"
        
        if not installer_app.exists():
            self._log_progress("Installer app not found", "ERROR")
            return False
        
        # Create DMG contents
        if self.dmg_dir.exists():
            shutil.rmtree(self.dmg_dir)
        self.dmg_dir.mkdir()
        
        # Copy installer app (now containing main app) to DMG
        installer_dst = self.dmg_dir / f"{self.installer_name}.app"
        shutil.copytree(installer_app, installer_dst)
        
        # Create Applications symlink
        applications_link = self.dmg_dir / "Applications"
        applications_link.symlink_to("/Applications")
        
        # Create README
        readme_content = f"""Physiotherapy Clinic Assistant - Installer

Version {self.version}

To install:
1. Double-click the installer app
2. Follow the installation wizard
3. Drag the app to Applications folder

IMPORTANT: On first run, the app will download AI models (~4.3GB).
This ensures you always have the latest models and keeps the installer small.

System Requirements:
• macOS 10.15+ (Catalina or later)
• 8GB RAM minimum (16GB recommended)
• 10GB free disk space (plus 4.3GB for models)
• Microphone access
• Internet connection (for initial setup and model download)

For support, visit: https://physioclinic.com/support
"""
        
        with open(self.dmg_dir / "README.txt", 'w') as f:
            f.write(readme_content)
        
        # Flush filesystem buffers and wait (prevents "Resource busy" on GitHub Actions)
        subprocess.run(["sync"], check=False)
        time.sleep(2)
        
        # Detach any existing DMG mounts
        subprocess.run(["hdiutil", "detach", "/Volumes/PhysioClinicAssistant Installer"], 
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
                "-volname", "PhysioClinicAssistant Installer",
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
        """Sign both main app and installer app (installer must already have main app bundled)"""
        self._log_progress("Signing applications", "Code Signing")
        
        # Sign main app first (it's bundled inside installer, but we sign it standalone too)
        main_app_path = self.dist_dir / f"{self.app_name}.app"
        if main_app_path.exists():
            if not self.sign_app(main_app_path):
                return False
        
        # Sign the bundled main app inside installer
        installer_app_path = self.dist_dir / f"{self.installer_name}.app"
        bundled_main_app = installer_app_path / "Contents" / "Resources" / f"{self.app_name}.app"
        if bundled_main_app.exists():
            self._log_progress("Signing bundled app inside installer...")
            if not self.sign_app(bundled_main_app):
                return False
        
        # Sign installer app last (after its contents are signed)
        if installer_app_path.exists():
            if not self.sign_app(installer_app_path):
                return False
        
        return True
    
    def notarize_applications(self) -> bool:
        """Notarize both main app and installer app"""
        self._log_progress("Notarizing applications", "Notarization")
        
        # Notarize main app
        main_app_path = self.dist_dir / f"{self.app_name}.app"
        if main_app_path.exists():
            if not self.notarize_app(main_app_path):
                return False
        
        # Notarize installer app
        installer_app_path = self.dist_dir / f"{self.installer_name}.app"
        if installer_app_path.exists():
            if not self.notarize_app(installer_app_path):
                return False
        
        return True
    
    def build_all(self) -> bool:
        """Execute the complete build process"""
        print(f"🚀 Building {self.app_name} v{self.version}")
        print("=" * 60)
        
        build_steps = [
            ("Clean Build Directories", self.clean_build_dirs),
            ("Build Main Application", self.build_main_app),
            ("Build Installer Application", self.build_installer_app),
            ("Bundle App into Installer", self.bundle_app_into_installer),  # Must be before signing!
            ("Sign Applications", self.sign_applications),
            ("Notarize Applications", self.notarize_applications),
            ("Create DMG Installer", self.create_dmg),
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