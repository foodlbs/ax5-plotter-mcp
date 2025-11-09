#!/bin/bash
# Installation script for AX5 Plotter MCP Server

set -e  # Exit on error

echo "======================================"
echo "AX5 Plotter MCP Server - Installation"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root${NC}"
    exit 1
fi

echo "Step 1: Checking system dependencies..."

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo -e "${YELLOW}Python 3.11 not found. Installing...${NC}"
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3-pip
else
    echo -e "${GREEN}✓ Python 3.11 found${NC}"
fi

# Check Redis
if ! command -v redis-server &> /dev/null; then
    echo -e "${YELLOW}Redis not found. Installing...${NC}"
    sudo apt install -y redis-server
else
    echo -e "${GREEN}✓ Redis found${NC}"
fi

echo ""
echo "Step 2: Setting up Python virtual environment..."

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate virtual environment
source .venv/bin/activate

echo ""
echo "Step 3: Installing Python dependencies..."
uv pip install -r requirements.txt

echo ""
echo "Step 4: Setting up configuration..."

# Copy example configuration if settings.yaml doesn't exist
if [ ! -f "config/settings.yaml" ]; then
    echo "Creating configuration file..."
    cp config/settings.example.yaml config/settings.yaml
    echo -e "${YELLOW}Please edit config/settings.yaml with your settings${NC}"
else
    echo -e "${GREEN}✓ Configuration file exists${NC}"
fi

echo ""
echo "Step 5: Setting up serial port permissions..."

# Add user to dialout group
if ! groups $USER | grep -q dialout; then
    echo "Adding user to dialout group..."
    sudo usermod -aG dialout $USER
    echo -e "${YELLOW}You need to log out and back in for this to take effect${NC}"
else
    echo -e "${GREEN}✓ User is in dialout group${NC}"
fi

echo ""
echo "Step 6: Creating directory structure..."
mkdir -p uploads output logs

echo ""
echo "Step 7: Starting Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

if systemctl is-active --quiet redis-server; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
fi

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit config/settings.yaml with your serial port and preferences"
echo "2. Connect your Arduino/GRBL plotter"
echo "3. Run tests: python tests/test_basic.py"
echo "4. Start API server: uvicorn src.api.main:app --reload"
echo "5. Start worker: python src/workers/plot_worker.py"
echo ""
echo "For ZimaBoard deployment, see: docs/zimaboard_deployment.md"
echo ""
echo "Optional: Install systemd services"
echo "  sudo cp scripts/systemd/*.service /etc/systemd/system/"
echo "  sudo systemctl enable ax5-api ax5-worker"
echo ""
