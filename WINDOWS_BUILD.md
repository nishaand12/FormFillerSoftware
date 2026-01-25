# Windows Build Guide for PhysioClinicAssistant

This document provides instructions for building and running PhysioClinicAssistant on Windows.

## Prerequisites

### 1. Python Installation
- Download and install Python 3.10 or 3.11 from [python.org](https://www.python.org/downloads/)
- **Important**: Check "Add Python to PATH" during installation
- Verify installation: `python --version`

### 2. Git (for cloning the repository)
- Download from [git-scm.com](https://git-scm.com/download/win)
- Or use Windows Package Manager: `winget install Git.Git`

### 3. Visual Studio Build Tools (for native dependencies)
Some Python packages require C++ compilation. Install Visual Studio Build Tools:
- Download from [Visual Studio Downloads](https://visualstudio.microsoft.com/downloads/)
- Select "Build Tools for Visual Studio"
- In the installer, select "Desktop development with C++"

### 4. FFmpeg (required for audio processing)
The `pydub` library requires FFmpeg for audio format conversion.

**Option A: Using Chocolatey (recommended)**
```powershell
choco install ffmpeg
```

**Option B: Using winget**
```powershell
winget install FFmpeg
```

**Option C: Manual Installation**
1. Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your system PATH

Verify installation: `ffmpeg -version`

## Setting Up the Development Environment

### 1. Clone the Repository
```powershell
git clone <repository-url>
cd FormFillerSoftware
```

### 2. Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Windows-Specific llama-cpp-python

The default `llama-cpp-python` may not have optimal performance on Windows. Choose based on your hardware:

**For CPU-only (safest option):**
```powershell
pip install llama-cpp-python
```

**For NVIDIA GPU with CUDA:**
```powershell
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

Note: CUDA 12.1 must be installed for GPU acceleration. Download from [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit).

### 5. Create Windows Icon (Optional)
If you need to convert the PNG logo to ICO format:
```powershell
pip install Pillow
python -c "from PIL import Image; img = Image.open('static/logo.png'); img.save('static/logo.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])"
```

## Running the Application

### Development Mode
```powershell
python run_app.py
```

Or directly:
```powershell
python main.py
```

## Building the Windows Executable

### 1. Install PyInstaller
```powershell
pip install pyinstaller
```

### 2. Build Using the Build Script
```powershell
python build_windows.py
```

### 3. Or Build Using the Spec File Directly
```powershell
pyinstaller --clean --noconfirm PhysioClinicAssistant_windows.spec
```

### Build Output
After a successful build, you'll find:
- `dist/PhysioClinicAssistant/` - The application folder with all dependencies
- `dist/PhysioClinicAssistant/PhysioClinicAssistant.exe` - The main executable
- `dist/PhysioClinicAssistant-{version}-Windows-Portable.zip` - Portable package

## Application Data Locations

On Windows, the application stores data in these locations:

| Data Type | Location |
|-----------|----------|
| Application Data | `%APPDATA%\PhysioClinicAssistant\` |
| Cache | `%LOCALAPPDATA%\PhysioClinicAssistant\Cache\` |
| Logs | `%LOCALAPPDATA%\PhysioClinicAssistant\Logs\` |
| AI Models | `%APPDATA%\PhysioClinicAssistant\models\` |
| Database | `%APPDATA%\PhysioClinicAssistant\data\clinic_data.db` |

To access these folders, open File Explorer and paste the path (e.g., `%APPDATA%\PhysioClinicAssistant`).

## Troubleshooting

### "Python was not found" Error
- Ensure Python is added to PATH during installation
- Reinstall Python and check "Add Python to PATH"

### "Microsoft Visual C++ 14.0 or greater is required" Error
- Install Visual Studio Build Tools with C++ support

### Audio Recording Issues
- Ensure microphone permissions are granted in Windows Settings
- Check Windows Privacy Settings > Microphone > Allow apps to access your microphone

### FFmpeg Not Found
- Verify FFmpeg is in your PATH: `ffmpeg -version`
- Restart terminal/command prompt after adding to PATH

### Model Download Fails
- Check internet connection
- Ensure sufficient disk space (models require ~4-5GB)
- Try running as Administrator if permission issues occur

### Application Won't Start
1. Check the log files in `%LOCALAPPDATA%\PhysioClinicAssistant\Logs\`
2. Run from command prompt to see error messages:
   ```powershell
   cd dist\PhysioClinicAssistant
   .\PhysioClinicAssistant.exe
   ```

### GPU Acceleration Not Working
- Verify NVIDIA drivers are up to date
- Confirm CUDA toolkit is installed (for CUDA builds)
- Check that `llama-cpp-python` was installed with CUDA support

## Performance Notes

### CPU vs GPU
- **With NVIDIA GPU (CUDA)**: Significantly faster inference for data extraction
- **CPU-only**: Works well but slower; the app automatically selects smaller models

### Memory Requirements
- Minimum: 8GB RAM
- Recommended: 16GB RAM for larger models

### Disk Space
- Application: ~500MB
- AI Models: ~4-5GB
- Total recommended free space: 10GB

## Creating an Installer (Optional)

For distribution, you may want to create a proper Windows installer using tools like:

### Inno Setup (Free)
1. Download from [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)
2. Create a script to package the `dist/PhysioClinicAssistant` folder

### NSIS (Free)
1. Download from [nsis.sourceforge.io](https://nsis.sourceforge.io/)
2. Create an installer script

## Support

For issues specific to the Windows build, please include:
- Windows version (e.g., Windows 10/11)
- Python version
- Contents of log files from `%LOCALAPPDATA%\PhysioClinicAssistant\Logs\`
- Any error messages from the command prompt
