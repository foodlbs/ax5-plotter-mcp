@echo off
REM AX5 Plotter Photo Booth Launcher (Windows)

echo.
echo 🎨 AX5 Plotter Photo Booth
echo ==========================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

REM Check if config exists
if not exist "config\settings.yaml" (
    echo ⚠️  Warning: config\settings.yaml not found
    echo Copying from settings.example.yaml...
    copy config\settings.example.yaml config\settings.yaml
    echo ✅ Config file created
    echo.
)

REM Create output directories
if not exist "output\captures" mkdir output\captures
if not exist "output\processed" mkdir output\processed
if not exist "output\gcode" mkdir output\gcode
if not exist "logs" mkdir logs

echo 📦 Checking dependencies...
echo.

REM Check and install dependencies
python -c "import cv2, numpy, PIL, yaml" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install -r requirements-simple.txt
    echo.
) else (
    echo ✅ All dependencies installed
    echo.
)

echo 🚀 Starting Photo Booth...
echo Press Ctrl+C to stop
echo.

REM Run the application
python photo_booth_app.py

pause
