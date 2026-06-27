#!/usr/bin/env bash
# PebbleMind One-Click Installer
# Works on macOS and Linux

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$HOME/.pebblemind"
BIN_DIR="$HOME/.local/bin"
VENV_DIR="$INSTALL_DIR/venv"
DEFAULT_MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_NAME="qwen2.5-1.5b-instruct-q4_k_m.gguf"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   PebbleMind Installer                 ║${NC}"
echo -e "${BLUE}║   Local AI Assistant                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"

# Check OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
    Darwin*)    PLATFORM=macOS;;
    *)          echo -e "${RED}❌ Unsupported OS: ${OS}${NC}"; exit 1;;
esac

echo -e "${GREEN}✓${NC} Platform: ${PLATFORM}"

# Check Python
echo -n "Checking Python... "
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "Please install Python 3.10-3.12 first:"
    if [ "$PLATFORM" = "macOS" ]; then
        echo "  brew install python@3.12"
    else
        echo "  sudo apt install python3 python3-venv python3-pip"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION}"

# Warn if Python 3.13+
if [ "$(python3 -c 'import sys; print(sys.version_info.minor)')" -ge 13 ]; then
    echo -e "${YELLOW}⚠️  Python 3.13+ detected. llama-cpp-python may need build tools.${NC}"
fi

# Check disk space
echo -n "Checking disk space... "
if [ "$PLATFORM" = "macOS" ]; then
    FREE_GB=$(df -g ~ | tail -1 | awk '{print $4}')
else
    FREE_GB=$(df -BG ~ | tail -1 | awk '{print $4}' | tr -d 'G')
fi

if [ "$FREE_GB" -lt 5 ]; then
    echo -e "${RED}❌ Only ${FREE_GB}GB free. Need at least 5GB.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} ${FREE_GB}GB available"

# Create installation directory
echo -n "Creating directories... "
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$BIN_DIR"
echo -e "${GREEN}✓${NC}"

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo -n "Creating Python virtual environment... "
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC}"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -n "Upgrading pip... "
pip install --quiet --upgrade pip setuptools wheel
echo -e "${GREEN}✓${NC}"

# Install pebblemind
echo "Installing PebbleMind..."
if [ -f "$(dirname "$0")/setup.py" ] || [ -f "$(dirname "$0")/pyproject.toml" ]; then
    # Installing from local source
    echo "  (from local source)"
    cd "$(dirname "$0")"
    pip install --quiet -e .
else
    # TODO: Install from PyPI when published
    echo -e "${RED}❌ Installation source not found${NC}"
    echo "Please clone the repository first:"
    echo "  git clone https://github.com/yourusername/pebblemind.git"
    echo "  cd pebblemind && ./install.sh"
    exit 1
fi
echo -e "${GREEN}✓${NC} PebbleMind installed"

# Create wrapper script
echo -n "Creating pebblemind command... "
cat > "$BIN_DIR/pebblemind" << 'EOF'
#!/bin/bash
source "$HOME/.pebblemind/venv/bin/activate"
python -m pebblemind "$@"
EOF
chmod +x "$BIN_DIR/pebblemind"
echo -e "${GREEN}✓${NC}"

# Check if BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}⚠️  $BIN_DIR not in PATH${NC}"
    echo ""
    echo "Add this to your ~/.zshrc or ~/.bashrc:"
    echo -e "  ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo ""
    echo "Then run: source ~/.zshrc"
fi

# Download default model (optional)
echo ""
read -p "Download default model (Qwen 2.5 1.5B, ~1GB)? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    MODEL_PATH="$INSTALL_DIR/models/$DEFAULT_MODEL_NAME"
    
    if [ -f "$MODEL_PATH" ]; then
        echo -e "${GREEN}✓${NC} Model already exists: $MODEL_PATH"
    else
        echo "Downloading model... (this may take a few minutes)"
        
        if command -v curl &> /dev/null; then
            curl -L -# -o "$MODEL_PATH" "$DEFAULT_MODEL_URL"
        elif command -v wget &> /dev/null; then
            wget --progress=bar:force -O "$MODEL_PATH" "$DEFAULT_MODEL_URL"
        else
            echo -e "${RED}❌ Neither curl nor wget found${NC}"
            echo "Please download manually:"
            echo "  $DEFAULT_MODEL_URL"
            echo "  Save to: $MODEL_PATH"
        fi
        
        if [ -f "$MODEL_PATH" ]; then
            echo -e "${GREEN}✓${NC} Model downloaded"
            
            # Set model path in config
            "$BIN_DIR/pebblemind" config set llm.model_path "$MODEL_PATH" 2>/dev/null || true
        fi
    fi
fi

# Run health check
echo ""
echo "Running health check..."
"$BIN_DIR/pebblemind" doctor

# Success message
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🎉 Installation Complete!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "Try it out:"
echo -e "  ${BLUE}pebblemind chat 'Tell me a joke'${NC}"
echo -e "  ${BLUE}pebblemind chat --interactive${NC}"
echo ""
echo "For more commands:"
echo -e "  ${BLUE}pebblemind --help${NC}"
echo ""
echo "Documentation:"
echo "  https://github.com/yourusername/pebblemind"
echo ""
