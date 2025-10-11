# Mac Installer for Physiotherapy Clinic Assistant

## Overview

This Mac installer provides a seamless installation experience for Mac users, eliminating the need for command line access. Users can simply download a DMG file and be guided through the complete setup process.

## How It Works

### 1. **Download & Mount**
- User downloads `PhysioClinicAssistant-X.X.X-macOS-Installer.dmg` from your website
- User double-clicks DMG to mount it

### 2. **Installation**
- User double-clicks the installer app
- Installer window opens with welcome screen
- User clicks "Place App on Desktop"
- Progress bar shows installation steps
- Application is placed on Desktop for user to drag

### 3. **Drag to Applications**
- User drags the app from Desktop to Applications folder
- This follows the standard Mac installation process

### 4. **Setup Wizard**
- Setup wizard launches automatically when user first runs the app
- Guides user through:
  - System requirements check
  - Python environment setup
  - AI model download
  - Audio device configuration
  - Database setup

### 5. **Ready to Use**
- Application is fully configured and ready
- User can launch from Applications folder
- All components are properly set up

## Building the Installer

### Prerequisites
- macOS 10.15+ (Catalina or later)
- Python 3.13+
- PyInstaller
- Xcode Command Line Tools

### Build Process
```bash
# Build the Mac installer
python build_mac_installer.py
```

This creates:
- `PhysioClinicAssistant-Installer.app` - The installer application
- `PhysioClinicAssistant-X.X.X-macOS-Installer.dmg` - The DMG package

### Testing
```bash
# Test the installer
python test_installer.py
```

## File Structure

```
build_mac_installer.py          # Main build script
mac_installer.py                # Installer application
test_installer.py               # Test script
PhysioClinicAssistant.spec      # PyInstaller spec for main app
PhysioClinicAssistant-Installer.spec  # PyInstaller spec for installer
```

## User Experience Flow

```
User Downloads DMG
        ↓
User Mounts DMG
        ↓
User Clicks Installer App
        ↓
Installer Window Opens
        ↓
User Clicks "Install Application"
        ↓
Progress Bar Shows Steps
        ↓
Setup Wizard Launches
        ↓
User Completes Configuration
        ↓
Application Ready to Use
```

## Technical Details

### Installer Features
- **System Requirements Check** - Validates macOS version, RAM, disk space
- **Automatic Installation** - Installs to Applications folder
- **Permission Setting** - Sets proper file permissions
- **Directory Creation** - Creates necessary support directories
- **Setup Integration** - Automatically launches setup wizard

### Security
- **Code Signing** - Ready for Apple Developer ID signing
- **Sandboxing** - Follows macOS security guidelines
- **Permissions** - Requests only necessary permissions

### Compatibility
- **macOS 10.15+** - Supports Catalina and later
- **Apple Silicon** - Compatible with M1/M2 Macs
- **Intel Macs** - Compatible with Intel-based Macs

## Uninstallation

### Standard Mac Uninstallation
**Simple Method (Basic Removal):**
- Drag the app from Applications folder to Trash
- This removes the main application but may leave some user data

**Complete Uninstallation:**
- Run the included `Uninstaller.py` script
- This removes the application and all associated files:
  - Application bundle
  - User data and settings
  - Configuration files
  - Cache and log files
  - Preferences

### What Gets Removed
- `/Applications/PhysioClinicAssistant.app`
- `~/Library/Application Support/PhysioClinicAssistant/`
- `~/Library/Preferences/com.physioclinic.physioclinicassistant.plist`
- `~/Library/Caches/PhysioClinicAssistant/`
- `~/Library/Logs/PhysioClinicAssistant/`
- `~/Library/Saved Application State/`
- `~/Documents/PhysioClinicAssistant/` (if exists)
- `~/.physioclinicassistant/` (if exists)

## Distribution

### Website Integration
1. Upload DMG to your website
2. Provide download link
3. Include system requirements
4. Add installation instructions

### Example Download Page
```html
<h2>Download for Mac</h2>
<p>System Requirements: macOS 10.15+, 8GB RAM, 10GB free space</p>
<a href="PhysioClinicAssistant-2.0.0-macOS-Installer.dmg" download>
    Download Installer (DMG)
</a>
<p>After downloading, double-click the DMG file and follow the installer.</p>
```

## Troubleshooting

### Common Issues
1. **"App can't be opened"** - Right-click → Open (first time)
2. **"Insufficient permissions"** - Check System Preferences → Security
3. **"Installation failed"** - Ensure sufficient disk space

### Support
- Check system requirements
- Verify macOS version
- Ensure sufficient disk space
- Check internet connection for setup

## Future Enhancements

- **Auto-updates** - Integrate with update system
- **Custom branding** - Add company logos
- **Silent installation** - For enterprise deployment
- **Uninstaller** - Remove application completely
