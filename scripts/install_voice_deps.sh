#!/bin/bash
# Installation script for voice processing dependencies
# Installs whisper.cpp and Piper TTS

set -e  # Exit on error

echo "================================================"
echo "  PebbleMind Voice Dependencies Installer"
echo "================================================"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "❌ Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Create dependencies directory
DEPS_DIR="${HOME}/.pebblemind/deps"
mkdir -p "$DEPS_DIR"
cd "$DEPS_DIR"

echo "Installing to: $DEPS_DIR"
echo ""

# Install whisper.cpp
echo "📦 Installing whisper.cpp..."
if [ ! -d "whisper.cpp" ]; then
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp

    # Build whisper.cpp
    make

    # Download base model
    echo "Downloading whisper base.en model..."
    bash ./models/download-ggml-model.sh base.en

    echo "✓ whisper.cpp installed successfully"
    cd ..
else
    echo "✓ whisper.cpp already installed"
fi

echo ""

# Install Piper TTS
echo "📦 Installing Piper TTS..."
PIPER_DIR="$DEPS_DIR/piper"
mkdir -p "$PIPER_DIR"
cd "$PIPER_DIR"

if [ "$OS" == "macos" ]; then
    if [ ! -f "piper" ]; then
        # Download Piper for macOS (x86_64 or arm64)
        ARCH=$(uname -m)
        if [ "$ARCH" == "arm64" ]; then
            echo "Downloading Piper for Apple Silicon..."
            curl -L "https://github.com/rhasspy/piper/releases/latest/download/piper_macos_arm64.tar.gz" -o piper.tar.gz
        else
            echo "Downloading Piper for Intel Mac..."
            curl -L "https://github.com/rhasspy/piper/releases/latest/download/piper_macos_x64.tar.gz" -o piper.tar.gz
        fi
        tar -xzf piper.tar.gz
        rm piper.tar.gz
        echo "✓ Piper TTS installed"
    else
        echo "✓ Piper TTS already installed"
    fi
elif [ "$OS" == "linux" ]; then
    if [ ! -f "piper" ]; then
        echo "Downloading Piper for Linux..."
        curl -L "https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz" -o piper.tar.gz
        tar -xzf piper.tar.gz
        rm piper.tar.gz
        echo "✓ Piper TTS installed"
    else
        echo "✓ Piper TTS already installed"
    fi
fi

# Download a default voice model
echo ""
echo "📦 Downloading default voice model (amy-low)..."
if [ ! -f "amy-low.onnx" ]; then
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx" -o amy-low.onnx
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx.json" -o amy-low.onnx.json
    echo "✓ Voice model downloaded"
else
    echo "✓ Voice model already exists"
fi

echo ""
echo "================================================"
echo "  ✓ Installation Complete!"
echo "================================================"
echo ""
echo "Dependencies installed to: $DEPS_DIR"
echo ""
echo "Add to your PATH:"
echo "  export PATH=\"$DEPS_DIR/whisper.cpp:\$PATH\""
echo "  export PATH=\"$DEPS_DIR/piper:\$PATH\""
echo ""
echo "Or add to your shell profile (.bashrc, .zshrc, etc.)"
echo ""
echo "Test whisper: whisper.cpp/main -h"
echo "Test piper: piper/piper --help"
