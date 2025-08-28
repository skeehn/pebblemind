#!/bin/bash

# PebbleMind Complete Setup Script
# Sets up the entire PebbleMind environment

set -e

echo "🤖 PebbleMind Setup"
echo "===================="

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo "✅ Python $python_version found"
else
    echo "❌ Python 3.9+ required. Found: $python_version"
    exit 1
fi

# Detect OS and install system dependencies
echo ""
echo "📦 Installing system dependencies..."

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        echo "Detected Ubuntu/Debian"
        sudo apt-get update
        sudo apt-get install -y build-essential cmake libopenblas-dev libomp-dev llvm clang
    elif command -v dnf &> /dev/null; then
        echo "Detected Fedora/RHEL"
        sudo dnf install -y gcc gcc-c++ cmake openblas-devel libomp-devel llvm clang
    elif command -v pacman &> /dev/null; then
        echo "Detected Arch Linux"
        sudo pacman -S --noconfirm base-devel cmake openblas libomp llvm clang
    else
        echo "⚠️  Unsupported Linux distribution. Please install:"
        echo "   - build-essential or base-devel"
        echo "   - cmake"
        echo "   - libopenblas-dev or openblas-devel"
        echo "   - libomp-dev or libomp-devel"
        echo "   - llvm and clang"
    fi

elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        echo "Detected macOS with Homebrew"
        brew install llvm libomp openblas cmake
    else
        echo "⚠️  Homebrew not found. Please install Homebrew and run:"
        echo "   brew install llvm libomp openblas cmake"
        exit 1
    fi

else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

# Create virtual environment
echo ""
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PebbleMind
echo ""
echo "📥 Installing PebbleMind..."
pip install -e .

# Install optional voice dependencies
echo ""
echo "🎤 Installing voice dependencies..."
pip install pyaudio soundfile librosa

# Setup environment variables for BLAS
echo ""
echo "⚡ Configuring BLAS acceleration..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    export OMP_NUM_THREADS=$(sysctl -n hw.ncpu)
    export OPENBLAS_NUM_THREADS=$(sysctl -n hw.ncpu)
else
    export OMP_NUM_THREADS=$(nproc --all)
    export OPENBLAS_NUM_THREADS=$(nproc --all)
fi

# Build llama-cpp-python with BLAS
echo ""
echo "🔧 Building llama-cpp-python with BLAS acceleration..."
CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON" \
pip install llama-cpp-python --force-reinstall --no-cache-dir

# Download models
echo ""
echo "⬇️  Downloading models..."
./scripts/download_models.sh

# Create default configuration
echo ""
echo "⚙️  Creating default configuration..."
python3 -c "
from pebblemind.config import Config
config = Config()
config.llm.model_path = 'models/qwen2.5-1.5b-instruct-q4_k_m.gguf'
config.to_file('pebblemind.yaml')
print('Configuration created: pebblemind.yaml')
"

# Test installation
echo ""
echo "🧪 Testing installation..."
python3 -c "
try:
    from pebblemind.core import PebbleMind
    print('✅ PebbleMind import successful')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    exit(1)
"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🚀 Quick start:"
echo "1. source venv/bin/activate  # Activate virtual environment"
echo "2. pebblemind status         # Check system status"
echo "3. pebblemind chat --interactive  # Start chatting"
echo ""
echo "📚 Useful commands:"
echo "- pebblemind serve          # Start API server"
echo "- pebblemind add-docs docs/ # Add documents to RAG"
echo "- pebblemind transcribe audio.wav  # Transcribe audio"
echo ""
echo "📖 Documentation: https://pebblemind.readthedocs.io/"
echo "🐛 Issues: https://github.com/yourusername/pebblemind/issues"
