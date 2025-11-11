#!/bin/bash

# AX5 Simple Plotter App Launcher
# This script helps launch the simple plotter application with proper setup

echo "AX5 Simple Plotter Application Launcher"
echo "======================================="

# Check if we're in the right directory
if [ ! -f "simple_plotter_app.py" ]; then
    echo "Error: simple_plotter_app.py not found"
    echo "Please run this script from the AX5 plotter project directory"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    echo "Please install Python 3 first"
    exit 1
fi

# Check for config
if [ ! -f "config/settings.yaml" ]; then
    if [ -f "config/settings.example.yaml" ]; then
        echo "Configuration file not found."
        echo "Copying example configuration..."
        cp config/settings.example.yaml config/settings.yaml
        echo "Please edit config/settings.yaml with your plotter settings"
        echo "Especially update the 'port' setting to match your Arduino connection"
        echo ""
        read -p "Press Enter after updating the configuration file..."
    else
        echo "Error: No configuration files found"
        exit 1
    fi
fi

# Check for tkinter first (required for GUI)
echo "Checking for tkinter..."
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ tkinter is not installed!"
    echo ""
    echo "On macOS, install with:"
    echo "  brew install python-tk@3.11"
    echo ""
    echo "On Ubuntu/Debian, install with:"
    echo "  sudo apt-get install python3-tk"
    echo ""
    read -p "Press Enter after installing tkinter..."
    exit 1
fi

# Check for basic dependencies
echo "Checking Python dependencies..."
python3 -c "import cv2, numpy, PIL, yaml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Some dependencies are missing."
    echo "Installing required packages..."
    pip3 install -r requirements-simple.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies"
        echo "Try running: pip3 install -r requirements-simple.txt"
        exit 1
    fi
fi

# Create required directories
mkdir -p logs output uploads

echo "Starting AX5 Simple Plotter Application..."
echo "Close the GUI window to exit"
echo ""

# Launch the application
python3 simple_plotter_app.py