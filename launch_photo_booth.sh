#!/bin/bash

# AX5 Plotter Photo Booth Launcher
# Quick start script for the photo booth application

echo "🎨 AX5 Plotter Photo Booth"
echo "=========================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if config exists
if [ ! -f "config/settings.yaml" ]; then
    echo "⚠️  Warning: config/settings.yaml not found"
    echo "Copying from settings.example.yaml..."
    cp config/settings.example.yaml config/settings.yaml
    echo "✅ Config file created"
    echo ""
fi

# Create output directories
mkdir -p output/captures
mkdir -p output/processed
mkdir -p output/gcode
mkdir -p logs

echo "📦 Checking dependencies..."

# Check if required packages are installed
python3 -c "
import sys
try:
    import cv2
    import numpy
    import PIL
    import yaml
    print('✅ All dependencies installed')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    print('')
    print('Installing dependencies...')
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-simple.txt'])
" || {
    echo "Installing dependencies..."
    python3 -m pip install -r requirements-simple.txt
}

echo ""
echo "🚀 Starting Photo Booth..."
echo "Press Ctrl+C to stop"
echo ""

# Run the application
python3 photo_booth_app.py
