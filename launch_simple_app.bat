@echo off
REM AX5 Simple Plotter App Launcher for Windows
REM This script helps launch the simple plotter application with proper setup

echo AX5 Simple Plotter Application Launcher
echo =======================================

REM Check if we're in the right directory
if not exist "simple_plotter_app.py" (
    echo Error: simple_plotter_app.py not found
    echo Please run this script from the AX5 plotter project directory
    pause
    exit /b 1
)

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    echo Please install Python 3 first
    pause
    exit /b 1
)

REM Check for config
if not exist "config\settings.yaml" (
    if exist "config\settings.example.yaml" (
        echo Configuration file not found.
        echo Copying example configuration...
        copy "config\settings.example.yaml" "config\settings.yaml"
        echo Please edit config\settings.yaml with your plotter settings
        echo Especially update the 'port' setting to match your Arduino connection
        echo Example: COM3, COM4, etc.
        echo.
        pause
    ) else (
        echo Error: No configuration files found
        pause
        exit /b 1
    )
)

REM Check for basic dependencies
echo Checking Python dependencies...
python -c "import cv2, numpy, PIL, yaml" >nul 2>&1
if errorlevel 1 (
    echo Some dependencies are missing.
    echo Installing required packages...
    pip install -r requirements-simple.txt
    if errorlevel 1 (
        echo Failed to install dependencies
        echo Try running: pip install -r requirements-simple.txt
        pause
        exit /b 1
    )
)

REM Create required directories
if not exist "logs" mkdir logs
if not exist "output" mkdir output
if not exist "uploads" mkdir uploads

echo Starting AX5 Simple Plotter Application...
echo Close the GUI window to exit
echo.

REM Launch the application
python simple_plotter_app.py

pause