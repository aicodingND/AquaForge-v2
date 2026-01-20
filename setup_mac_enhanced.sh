#!/bin/bash

# AquaForge.ai - Enhanced Mac Development Setup
# Complete development environment with all recommended tools

set -e

echo "=============================================="
echo "  AquaForge.ai - Enhanced Mac Dev Setup"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS only."
    exit 1
fi

# ============================================================
# SECTION 1: Core Prerequisites
# ============================================================

echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 1: Core Prerequisites${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}[1.1] Installing/Updating Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Apple Silicon PATH setup
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo -e "${GREEN}✓ Homebrew installed, updating...${NC}"
    brew update
fi

echo -e "${BLUE}[1.2] Installing Python 3.11...${NC}"
brew install python@3.11 || true
echo -e "${GREEN}✓ Python $(python3.11 --version)${NC}"

echo -e "${BLUE}[1.3] Installing Node.js LTS...${NC}"
brew install node@20 || true
echo -e "${GREEN}✓ Node $(node --version)${NC}"

echo -e "${BLUE}[1.4] Installing Git (latest)...${NC}"
brew install git || true
echo -e "${GREEN}✓ Git $(git --version | cut -d' ' -f3)${NC}"

# ============================================================
# SECTION 2: Development Productivity Tools
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 2: Development Productivity${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}[2.1] Installing CLI productivity tools...${NC}"
brew install \
    jq \
    yq \
    fd \
    ripgrep \
    bat \
    tree \
    watch \
    htop \
    httpie \
    || true

echo -e "${GREEN}✓ CLI tools installed:${NC}"
echo "    • jq/yq     - JSON/YAML processing"
echo "    • fd        - Fast file finder"
echo "    • ripgrep   - Fast code search"
echo "    • bat       - Better cat with syntax highlighting"
echo "    • tree      - Directory visualization"
echo "    • httpie    - User-friendly HTTP client"
echo "    • htop      - System resource monitoring"

echo -e "${BLUE}[2.2] Installing Git tools...${NC}"
brew install \
    gh \
    git-lfs \
    lazygit \
    || true
git lfs install || true

echo -e "${GREEN}✓ Git tools installed:${NC}"
echo "    • gh        - GitHub CLI"
echo "    • git-lfs   - Large file storage"
echo "    • lazygit   - Terminal UI for git"

# ============================================================
# SECTION 3: Database & Caching Tools
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 3: Database & Caching${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}[3.1] Installing Redis (caching)...${NC}"
brew install redis || true
echo -e "${GREEN}✓ Redis installed (start with: brew services start redis)${NC}"

echo -e "${BLUE}[3.2] Installing PostgreSQL (optional database)...${NC}"
brew install postgresql@15 || true
echo -e "${GREEN}✓ PostgreSQL installed (start with: brew services start postgresql@15)${NC}"

echo -e "${BLUE}[3.3] Installing SQLite tools...${NC}"
brew install sqlite || true
echo -e "${GREEN}✓ SQLite $(sqlite3 --version | cut -d' ' -f1)${NC}"

# ============================================================
# SECTION 4: iOS & Mobile Development
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 4: iOS & Mobile Development${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}[4.1] Checking Xcode Command Line Tools...${NC}"
if ! xcode-select -p &> /dev/null; then
    echo "Installing Xcode Command Line Tools..."
    xcode-select --install
    echo -e "${YELLOW}⚠ Complete Xcode CLT installation, then re-run this script${NC}"
else
    echo -e "${GREEN}✓ Xcode Command Line Tools installed${NC}"
fi

echo -e "${BLUE}[4.2] Installing CocoaPods (iOS dependencies)...${NC}"
brew install cocoapods || true
echo -e "${GREEN}✓ CocoaPods installed${NC}"

echo -e "${BLUE}[4.3] Installing Watchman (React Native)...${NC}"
brew install watchman || true
echo -e "${GREEN}✓ Watchman installed${NC}"

echo -e "${BLUE}[4.4] Installing global npm packages for mobile dev...${NC}"
npm install -g \
    expo-cli \
    eas-cli \
    @react-native-community/cli \
    || true

echo -e "${GREEN}✓ Mobile CLI tools installed:${NC}"
echo "    • expo-cli  - Expo development"
echo "    • eas-cli   - Expo Application Services (builds)"
echo "    • react-native-cli - Direct RN development"

# ============================================================
# SECTION 5: Python Environment Setup
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 5: Python Environment${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}[5.1] Creating Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3.11 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

echo -e "${BLUE}[5.2] Installing Python dependencies...${NC}"
source .venv/bin/activate
pip install --upgrade pip wheel setuptools

# Main requirements
pip install -r requirements.txt

# Dev requirements
pip install -r requirements-dev.txt

# Additional recommended packages
echo -e "${BLUE}[5.3] Installing additional Python dev tools...${NC}"
pip install \
    pytest-timeout \
    pytest-xdist \
    pytest-sugar \
    pre-commit \
    ipdb \
    python-dotenv \
    faker \
    locust \
    memory-profiler \
    py-spy \
    scalene \
    || true

echo -e "${GREEN}✓ Additional Python tools installed:${NC}"
echo "    • pytest-timeout   - Test timeout protection"
echo "    • pytest-xdist     - Parallel test execution"
echo "    • pytest-sugar     - Pretty test output"
echo "    • pre-commit       - Git hook management"
echo "    • ipdb             - Enhanced debugger"
echo "    • faker            - Test data generation"
echo "    • locust           - Load testing"
echo "    • memory-profiler  - Memory profiling"
echo "    • py-spy           - Performance sampling profiler"
echo "    • scalene          - CPU/memory/GPU profiler"

# ============================================================
# SECTION 6: Node.js Dependencies
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 6: Frontend Dependencies${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}[6.1] Installing frontend dependencies...${NC}"
cd frontend
npm install
cd ..
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# ============================================================
# SECTION 7: Pre-commit Hooks
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 7: Code Quality Hooks${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}[7.1] Setting up pre-commit hooks...${NC}"
if [ ! -f ".pre-commit-config.yaml" ]; then
    cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
        args: [--ignore-missing-imports]
EOF
    echo -e "${GREEN}✓ Pre-commit config created${NC}"
fi

source .venv/bin/activate
pre-commit install || true
echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"

# ============================================================
# SECTION 8: Production Dependencies (Optional)
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 8: Production Dependencies (Optional)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

read -p "Install enterprise/production dependencies? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "requirements-prod.txt" ]; then
        source .venv/bin/activate
        pip install -r requirements-prod.txt
        echo -e "${GREEN}✓ Production dependencies installed:${NC}"
        echo "    • structlog, sentry-sdk - Logging & error tracking"
        echo "    • arq - Background job processing"
        echo "    • tenacity - Retry/resilience patterns"
        echo "    • python-jose, passlib - JWT auth"
        echo "    • prometheus-client, opentelemetry - Metrics & tracing"
    else
        echo -e "${YELLOW}⚠ requirements-prod.txt not found${NC}"
    fi
else
    echo -e "${YELLOW}Skipped production dependencies${NC}"
fi

# ============================================================
# SECTION 9: VS Code Extensions (Optional)
# ============================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SECTION 8: VS Code Extensions (Optional)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""

if command -v code &> /dev/null; then
    read -p "Install recommended VS Code extensions? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        code --install-extension ms-python.python
        code --install-extension ms-python.vscode-pylance
        code --install-extension charliermarsh.ruff
        code --install-extension bradlc.vscode-tailwindcss
        code --install-extension dbaeumer.vscode-eslint
        code --install-extension esbenp.prettier-vscode
        code --install-extension eamodio.gitlens
        code --install-extension usernamehw.errorlens
        code --install-extension ms-vscode.vscode-typescript-next
        echo -e "${GREEN}✓ VS Code extensions installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ VS Code CLI not found (code command)${NC}"
fi

# ============================================================
# SUMMARY
# ============================================================

echo ""
echo -e "${CYAN}══════════════════════════════════════════════=${NC}"
echo -e "${GREEN}  ✅ SETUP COMPLETE!${NC}"
echo -e "${CYAN}══════════════════════════════════════════════=${NC}"
echo ""
echo "Installed Components:"
echo "  ✓ Core: Python 3.11, Node.js, Git"
echo "  ✓ CLI Tools: jq, fd, ripgrep, httpie, etc."
echo "  ✓ Git: GitHub CLI, git-lfs, lazygit"
echo "  ✓ Database: Redis, PostgreSQL, SQLite"
echo "  ✓ Mobile: Xcode CLT, CocoaPods, Expo, EAS"
echo "  ✓ Python: All dependencies + dev tools"
echo "  ✓ Frontend: All npm packages"
echo "  ✓ Quality: Pre-commit hooks configured"
echo ""
echo "Quick Start:"
echo "  1. source .venv/bin/activate"
echo "  2. ./start_dev.sh"
echo ""
echo "Optional Services:"
echo "  • Start Redis:      brew services start redis"
echo "  • Start PostgreSQL: brew services start postgresql@15"
echo ""
echo "For iOS development:"
echo "  • Install Xcode from App Store"
echo "  • Run: sudo xcodebuild -license accept"
echo ""
