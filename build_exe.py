#!/usr/bin/env python3
"""
Build script for Engraver Camera Assistant Windows executable.
Creates a standalone .exe file with all dependencies bundled.
"""

import os
import sys
import subprocess
import shutil

def build_executable():
    """Build the standalone executable using PyInstaller."""
    
    # PyInstaller options
    options = [
        '--name=EngraverHelper',
        '--onefile',  # Create single .exe file
        '--windowed',  # No console window
        '--clean',  # Clean temporary files
        '--noconfirm',  # Don't ask for confirmation
        '--distpath=dist',  # Output directory
        '--workpath=build',  # Build directory
        '--specpath=.',  # Spec file location
        '--add-data=config.py;.',  # Include config file
        '--icon=icon.ico',  # Application icon (will create later)
        'main.py'  # Main script
    ]
    
    # Build command
    cmd = ['pyinstaller'] + options
    
    print("Building executable...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(f"Executable created: dist/EngraverHelper.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
