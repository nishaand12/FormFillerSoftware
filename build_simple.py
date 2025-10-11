#!/usr/bin/env python3
"""
Simplified Mac Build Script
Uses PyInstaller's auto-detection for a more reliable build
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path


def get_version():
    """Get application version"""
    try:
        with open("VERSION", 'r') as f:
            return f.read().strip()
    except:
        return "2.0.0"


def log(message):
    """Log message with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def run_command(cmd, description):
    """Run command with error handling"""
    log(f"Running: {description}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        log(f"✓ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        log(f"✗ {description} failed: {e.stderr}")
        return False


def build_main_app():
    """Build main application with simplified PyInstaller command"""
    log("Building main application...")
    
    # Clean previous builds
    for dir_name in ["build", "dist"]:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            log(f"Cleaned {dir_name}")
    
    # Build with PyInstaller using auto-detection
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",  # Use onedir instead of onefile for better compatibility
        "--windowed",  # No console window
        "--name", "PhysioClinicAssistant",
        "--add-data", "config:config",
        "--add-data", "forms:forms", 
        "--add-data", "auth:auth",
        "--add-data", "models:models",
        "--add-data", "setup_wizard.py:.",
        "--add-data", "system_checker.py:.",
        "--add-data", "config_validator.py:.",
        "--add-data", "uninstaller.py:.",
        "--add-data", "VERSION:.",
        "--add-data", "README.md:.",
        "--add-data", "requirements.txt:.",
        "main.py"
    ]
    
    if not run_command(cmd, "PyInstaller build"):
        return False
    
    # Check if app was created
    app_path = Path("dist") / "PhysioClinicAssistant"
    if not app_path.exists():
        log("Main app not found after build")
        return False
    
    log(f"Main app created: {app_path}")
    return True


def build_installer_app():
    """Build installer application"""
    log("Building installer application...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "PhysioClinicAssistant-Installer",
        "--add-data", "config:config",
        "--add-data", "forms:forms",
        "--add-data", "auth:auth", 
        "--add-data", "models:models",
        "--add-data", "setup_wizard.py:.",
        "--add-data", "system_checker.py:.",
        "--add-data", "config_validator.py:.",
        "--add-data", "uninstaller.py:.",
        "--add-data", "main.py:.",
        "--add-data", "VERSION:.",
        "--add-data", "README.md:.",
        "--add-data", "requirements.txt:.",
        "mac_installer.py"
    ]
    
    if not run_command(cmd, "Installer PyInstaller build"):
        return False
    
    # Check if installer was created
    installer_path = Path("dist") / "PhysioClinicAssistant-Installer"
    if not installer_path.exists():
        log("Installer app not found after build")
        return False
    
    log(f"Installer app created: {installer_path}")
    return True


def create_dmg():
    """Create DMG using create-dmg"""
    log("Creating DMG...")
    
    version = get_version()
    dmg_name = f"PhysioClinicAssistant-{version}-macOS.dmg"
    
    # Create DMG contents directory
    dmg_dir = Path("dmg_contents")
    if dmg_dir.exists():
        shutil.rmtree(dmg_dir)
    dmg_dir.mkdir()
    
    # Copy installer to DMG contents
    installer_src = Path("dist") / "PhysioClinicAssistant-Installer"
    installer_dst = dmg_dir / "PhysioClinicAssistant-Installer"
    shutil.copytree(installer_src, installer_dst)
    
    # Create Applications symlink
    applications_link = dmg_dir / "Applications"
    applications_link.symlink_to("/Applications")
    
    # Create README
    readme_content = f"""Physiotherapy Clinic Assistant - Installer

Version {version}

To install:
1. Double-click the installer app
2. Follow the installation wizard
3. Drag the app to Applications folder

System Requirements:
• macOS 10.15+ (Catalina or later)
• 8GB RAM minimum
• 10GB free disk space
• Microphone access
"""
    
    with open(dmg_dir / "README.txt", 'w') as f:
        f.write(readme_content)
    
    # Create DMG
    cmd = [
        "create-dmg",
        "--volname", "PhysioClinicAssistant Installer",
        "--window-pos", "200", "120",
        "--window-size", "800", "500",
        "--icon-size", "100",
        "--icon", "PhysioClinicAssistant-Installer", "200", "190",
        "--app-drop-link", "580", "190",
        "--no-internet-enable",
        dmg_name,
        str(dmg_dir)
    ]
    
    if not run_command(cmd, "DMG creation"):
        return False
    
    # Clean up
    shutil.rmtree(dmg_dir)
    
    log(f"DMG created: {dmg_name}")
    return True


def main():
    """Main build function"""
    log("Starting simplified Mac build process")
    log("=" * 50)
    
    steps = [
        ("Build Main Application", build_main_app),
        ("Build Installer Application", build_installer_app),
        ("Create DMG", create_dmg),
    ]
    
    for step_name, step_func in steps:
        log(f"Step: {step_name}")
        if not step_func():
            log(f"Build failed at: {step_name}")
            return 1
    
    log("=" * 50)
    log("Build completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
