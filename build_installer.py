#!/usr/bin/env python3
"""
Build script to create the Windows installer using NSIS.
"""

import os
import sys
import subprocess
import shutil

def build_installer():
    """Build the Windows installer using NSIS."""
    
    # Check if NSIS is available
    nsis_path = r"C:\Program Files (x86)\NSIS\makensis.exe"
    if not os.path.exists(nsis_path):
        # Try alternative path
        nsis_path = r"C:\Program Files\NSIS\makensis.exe"
        if not os.path.exists(nsis_path):
            print("NSIS not found. Please install NSIS first.")
            return False
    
    # Check if executable exists
    exe_path = "dist/EngraverHelper.exe"
    if not os.path.exists(exe_path):
        print(f"Executable not found: {exe_path}")
        print("Please build the executable first with PyInstaller.")
        return False
    
    # Build installer
    cmd = [nsis_path, "installer.nsi"]
    
    print("Building installer...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Installer built successfully!")
        
        # Check if installer was created
        installer_file = "EngraverHelper-Setup.exe"
        if os.path.exists(installer_file):
            print(f"Installer created: {installer_file}")
            size = os.path.getsize(installer_file)
            print(f"Size: {size / (1024*1024):.1f} MB")
            return True
        else:
            print("Installer file not found after build.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    success = build_installer()
    sys.exit(0 if success else 1)
