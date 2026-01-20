#!/bin/bash

# AquaForge.ai - Mac Setup Script
# Automated installation of all dependencies and prerequisites

set -e  # Exit on error

echo "=========================================="
echo "  AquaForge.ai - Mac Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS only."
    exit 1
fi

echo -e "${BLUE}[1/7] Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo -e "${GREEN}✓ Homebrew already installed${NC}"
fi

echo ""
echo -e "${BLUE}[2/7] Installing Python 3.11...${NC}"
if ! command -v python3.11 &> /dev/null; then
    brew install python@3.11
    echo -e "${GREEN}✓ Python 3.11 installed${NC}"
else
    echo -e "${GREEN}✓ Python 3.11 already installed${NC}"
fi

echo ""
echo -e "${BLUE}[3/7] Installing Node.js...${NC}"
if ! command -v node &> /dev/null; then
    brew install node
    echo -e "${GREEN}✓ Node.js installed${NC}"
else
    echo -e "${GREEN}✓ Node.js already installed ($(node --version))${NC}"
fi

echo ""
echo -e "${BLUE}[4/7] Creating Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3.11 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

echo ""
echo -e "${BLUE}[5/7] Installing Python dependencies...${NC}"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

echo ""
echo -e "${BLUE}[6/7] Installing Node.js dependencies...${NC}"
cd frontend
npm install
cd ..
echo -e "${GREEN}✓ Node.js dependencies installed${NC}"

echo ""
echo -e "${BLUE}[7/7] Optional: Installing development tools...${NC}"
read -p "Install Expo CLI for mobile development? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    npm install -g expo-cli
    echo -e "${GREEN}✓ Expo CLI installed${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Start the application:"
echo "     ./start_dev.sh"
echo ""
echo "  (Or run backend and frontend separately)"
echo ""
echo "For more details, see TRANSFER_TO_MAC.md"
echo ""
