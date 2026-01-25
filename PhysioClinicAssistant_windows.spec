# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PhysioClinicAssistant Windows build
This file contains all build configuration for Windows executable
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# Read version from VERSION file
version = '2.2.0'  # Default fallback
version_file = Path('VERSION')
if version_file.exists():
    try:
        version = version_file.read_text().strip()
    except Exception:
        pass  # Use default if reading fails

# Windows uses semicolon as path separator in --add-data
# Format: (source, dest_folder)
datas = [
    ('config', 'config'),
    ('forms', 'forms'),
    ('auth', 'auth'),
    ('static', 'static'),
    ('resources', 'resources'),
    ('app_paths.py', '.'),
    ('setup_wizard.py', '.'),
    ('system_checker.py', '.'),
    ('config_validator.py', '.'),
    ('uninstaller.py', '.'),
    ('main.py', '.'),
    ('VERSION', '.'),
    ('README.md', '.'),
    ('requirements.txt', '.'),
]

binaries = []
hiddenimports = ['tkinter', '_tkinter']

# Collect all dependencies for these packages
tmp_ret = collect_all('pvrecorder')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('faster_whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('llama_cpp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('transformers')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Additional hidden imports that may be needed on Windows
hiddenimports += [
    'PIL',
    'PIL._tkinter_finder',
    'pydub',
    'numpy',
    'scipy',
    'certifi',
    'cryptography',
    'httpx',
    'supabase',
    'gotrue',
    'postgrest',
]

# Determine icon path
icon_path = None
ico_file = Path('static/logo.ico')
png_file = Path('static/logo.png')
if ico_file.exists():
    icon_path = str(ico_file)
elif png_file.exists():
    # PyInstaller on Windows can sometimes use PNG directly
    icon_path = str(png_file)

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude macOS-specific modules
        'macholib',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PhysioClinicAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    # Windows-specific options
    icon=icon_path if icon_path else None,
    # Version info for Windows (shows in file properties)
    version_file=None,  # Can be set to a .txt file with version info
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhysioClinicAssistant',
)

# Note: No BUNDLE step on Windows - that's macOS-specific
# The COLLECT step creates the distribution folder with all dependencies
