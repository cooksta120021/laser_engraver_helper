@echo off
echo ==========================================
echo   Engraver Camera Assistant
echo ==========================================
echo.

REM Kill any previous instances
taskkill /F /IM python.exe >nul 2>&1

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Install dependencies if needed
echo [INFO] Checking dependencies...
pip install -q -r requirements.txt

echo.
echo [INFO] Starting camera window...
echo.

python main.py
