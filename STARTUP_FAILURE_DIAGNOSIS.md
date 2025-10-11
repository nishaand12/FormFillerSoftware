# Application Startup Failure Diagnosis

## Problem
Application icon appears correctly, but the app fails to launch when opened (even with right-click → Open).

## Most Likely Culprits (Ranked by Probability)

### 1. **Missing Hidden Imports** (90% probability)
**Symptoms:** App tries to open briefly then closes
**Cause:** PyInstaller doesn't detect all dependencies automatically
**Solution:** Add more `--hidden-import` flags

**Common Missing Imports:**
- `PIL._tkinter_finder` (Pillow + tkinter)
- `pkg_resources.py2_warn`
- `plistlib`
- `pypdf` or `PyPDF2` (for PDF operations)
- `llama_cpp`
- `faster_whisper.transcribe`
- `transformers` submodules
- `supabase` submodules

### 2. **Path Resolution Issues** (80% probability)
**Symptoms:** "File not found" errors, resources not loading
**Cause:** Code looks for files relative to current directory instead of `sys._MEIPASS`
**Solution:** All file paths must use proper resource resolution

**Problem Code Pattern:**
```python
# BAD - won't work in bundle
config_path = "config/field_map.json"

# GOOD - works in bundle
def get_resource_path(relative_path):
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(sys._MEIPASS, relative_path)
    return relative_path

config_path = get_resource_path("config/field_map.json")
```

### 3. **Tkinter Bundle Issues** (70% probability)
**Symptoms:** Silent failure, no window appears
**Cause:** macOS PyInstaller + tkinter can be problematic
**Solutions:**
- Ensure `--windowed` flag is used
- May need to manually specify tcl/tk paths
- Check if `_tkinter.so` is in bundle

### 4. **Multiprocessing Issues** (60% probability)
**Symptoms:** Crash on startup, semaphore errors
**Cause:** `multiprocessing.set_start_method('spawn', force=True)` called after fork
**Solution:** Set start method as early as possible, before any imports

### 5. **Missing Python Standard Library Modules** (50% probability)
**Symptoms:** ImportError for stdlib modules
**Cause:** PyInstaller might not include all stdlib modules
**Solution:** Add as hidden imports or copy manually

### 6. **Incorrect Entry Point** (40% probability)
**Symptoms:** Nothing happens, no crash
**Cause:** Entry point script has errors or wrong function called
**Solution:** Verify `run_app.py` correctly imports and calls `main()`

### 7. **Code Signing / Gatekeeper Issues** (30% probability)
**Symptoms:** App "damaged" or won't verify
**Cause:** Unsigned code, quarantine attributes
**Solution:** Proper signing or user must run `xattr -cr` command

### 8. **Permissions Issues** (20% probability)
**Symptoms:** Permission denied errors
**Cause:** Executable not marked as executable
**Solution:** `chmod +x` or set during build

## Diagnostic Steps

### Step 1: Check Startup Log
The improved `run_app.py` now creates detailed logs:
```
~/Library/Logs/PhysioClinicAssistant/startup.log
```

This log will show:
- Python version and environment
- Bundle status (is `sys._MEIPASS` set?)
- Available directories and files
- Import errors
- Exact exception that caused failure

### Step 2: Run from Terminal
```bash
# Navigate to the .app bundle
cd /path/to/PhysioClinicAssistant.app/Contents/MacOS

# Run the executable directly
./PhysioClinicAssistant
```

This will show console output that Finder doesn't display.

### Step 3: Check Console.app
```bash
# Open macOS Console app
open /Applications/Utilities/Console.app

# Filter for "PhysioClinicAssistant"
# Look for crash reports or error messages
```

### Step 4: Verify Bundle Contents
```bash
# Check if executable exists
ls -la /path/to/PhysioClinicAssistant.app/Contents/MacOS/

# Check if resources exist
ls -la /path/to/PhysioClinicAssistant.app/Contents/Resources/

# Check if config files are bundled
find /path/to/PhysioClinicAssistant.app -name "*.json" | head -10
```

### Step 5: Test Import Chain
Create a minimal test script in the bundle:
```python
import sys
print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")

# Try each import
try:
    import tkinter
    print("✓ tkinter")
except Exception as e:
    print(f"✗ tkinter: {e}")

try:
    from main import main
    print("✓ main")
except Exception as e:
    print(f"✗ main: {e}")
```

## Build Script Improvements Needed

### Additional Hidden Imports
```python
"--hidden-import", "PIL._tkinter_finder",
"--hidden-import", "pkg_resources.py2_warn",
"--hidden-import", "plistlib",
"--hidden-import", "pypdf",
"--hidden-import", "PyPDF2",
"--hidden-import", "llama_cpp",
"--hidden-import", "faster_whisper.transcribe",
"--hidden-import", "faster_whisper.vad",
"--hidden-import", "transformers.models",
"--hidden-import", "supabase.client",
"--hidden-import", "supabase.lib",
"--hidden-import", "postgrest",
"--hidden-import", "realtime",
"--hidden-import", "storage3",
```

### Collect-All for Complex Packages
```python
"--collect-all", "faster_whisper",
"--collect-all", "llama_cpp",
"--collect-all", "supabase",
```

### Additional PyInstaller Flags
```python
"--noupx",  # Don't use UPX compression (can cause issues)
"--log-level", "DEBUG",  # More verbose logging during build
```

## Code Changes Needed in main.py

### Add Resource Path Helper
```python
import sys
import os

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if getattr(sys, '_MEIPASS', None):
        # Running in PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    # Running in development
    return os.path.join(os.path.dirname(__file__), relative_path)
```

### Update All File Paths
Every file path in the codebase needs to use this helper:
```python
# Before
config_path = "config/field_map.json"

# After
config_path = get_resource_path("config/field_map.json")
```

## Testing Strategy

### 1. Test with Diagnostic Version
Build with improved logging and test on fresh Mac

### 2. Check Log Output
Look at `~/Library/Logs/PhysioClinicAssistant/startup.log`

### 3. Identify Exact Failure Point
- If no log created → crash before Python starts (binary issue)
- If log shows environment → crash during imports (dependency issue)
- If log shows "Starting application import" → import error
- If log shows "Launching application" → runtime error in main()

### 4. Fix and Rebuild
Based on log output, add missing imports or fix path issues

### 5. Verify
Test on multiple Macs with different macOS versions

## Quick Fix Commands

### If App Won't Open (Quarantine)
```bash
xattr -cr /Applications/PhysioClinicAssistant.app
```

### If Missing Permissions
```bash
chmod +x /Applications/PhysioClinicAssistant.app/Contents/MacOS/*
```

### If Path Issues
Check all uses of file paths in code - must use `get_resource_path()`

### If Import Issues
Add missing modules to PyInstaller's `--hidden-import`

## Expected Startup Sequence

1. User double-clicks .app
2. macOS launches executable at `Contents/MacOS/PhysioClinicAssistant`
3. PyInstaller bootstrap extracts to temp dir (if using onefile) or sets `sys._MEIPASS`
4. Python interpreter starts
5. `run_app.py` executes
6. Environment check runs, logs to file
7. `main` module imported
8. tkinter window appears
9. App GUI loads

**If app fails, the log will show exactly where in this sequence it stops.**

## Next Steps

1. ✅ Build with improved `run_app.py` (comprehensive logging)
2. ⏳ Add missing hidden imports to `build_mac.py`
3. ⏳ Test and check startup log
4. ⏳ Fix identified issues
5. ⏳ Rebuild and retest

## Summary

The most likely issue is **missing hidden imports** causing ImportError during startup. The improved `run_app.py` will create a detailed log showing exactly what fails, allowing us to quickly identify and fix the issue.

