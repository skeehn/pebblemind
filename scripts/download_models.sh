#!/bin/bash

# PebbleMind Model Download Script
# Downloads required models for full functionality

set -e

echo "🤖 PebbleMind Model Downloader"
echo "================================"

# Create models directory
mkdir -p models

# Function to download with progress
download_with_progress() {
    local url=$1
    local output=$2
    local name=$3

    if [ -f "$output" ]; then
        echo "✅ $name already exists, skipping..."
        return
    fi

    echo "⬇️  Downloading $name..."
    if command -v wget &> /dev/null; then
        wget -q --show-progress "$url" -O "$output"
    elif command -v curl &> /dev/null; then
        curl -L -o "$output" "$url"
    else
        echo "❌ Neither wget nor curl found. Please install one of them."
        exit 1
    fi
}

# Download Qwen2.5-1.5B Instruct GGUF model
echo ""
echo "📥 Downloading LLM Model (Qwen2.5-1.5B Instruct)..."
QWEN_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
download_with_progress "$QWEN_URL" "models/qwen2.5-1.5b-instruct-q4_k_m.gguf" "Qwen2.5-1.5B GGUF Model"

# Download BGE-small embedding model
echo ""
echo "📥 Downloading Embedding Model (BGE-small)..."
if command -v pip &> /dev/null && pip show huggingface_hub &> /dev/null; then
    echo "Using huggingface-cli to download BGE-small..."
    huggingface-cli download BAAI/bge-small-en-v1.5 --local-dir models/bge-small-en-v1.5 --quiet
else
    echo "⚠️  huggingface_hub not found. Install with: pip install huggingface_hub"
    echo "   Then run: huggingface-cli download BAAI/bge-small-en-v1.5 --local-dir models/bge-small-en-v1.5"
fi

# Download Whisper models
echo ""
echo "📥 Downloading Whisper Models..."
WHISPER_BASE_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

# Base English model
download_with_progress "${WHISPER_BASE_URL}/ggml-base.en.bin" "models/ggml-base.en.bin" "Whisper Base English"

# Tiny English model (faster, less accurate)
download_with_progress "${WHISPER_BASE_URL}/ggml-tiny.en.bin" "models/ggml-tiny.en.bin" "Whisper Tiny English"

# Download Piper voices
echo ""
echo "📥 Downloading Piper TTS Voices..."
PIPER_VOICES_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

# Amy voice (low quality, fast)
download_with_progress "${PIPER_VOICES_URL}/en/en_US/amy/low/en_US-amy-low.onnx" "models/en_US-amy-low.onnx" "Piper Amy Low Voice"
download_with_progress "${PIPER_VOICES_URL}/en/en_US/amy/low/en_US-amy-low.onnx.json" "models/en_US-amy-low.onnx.json" "Piper Amy Low Config"

# Lessac voice (medium quality)
download_with_progress "${PIPER_VOICES_URL}/en/en_US/lessac/medium/en_US-lessac-medium.onnx" "models/en_US-lessac-medium.onnx" "Piper Lessac Medium Voice"
download_with_progress "${PIPER_VOICES_URL}/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" "models/en_US-lessac-medium.onnx.json" "Piper Lessac Medium Config"

echo ""
echo "🎉 Model download complete!"
echo ""
echo "📂 Models downloaded to: $(pwd)/models/"
echo ""
echo "📋 Next steps:"
echo "1. Update pebblemind.yaml with correct model paths"
echo "2. Run: pebblemind status"
echo "3. Try: pebblemind chat --interactive"
echo ""
echo "💡 Tips:"
echo "- Use ggml-tiny.en.bin for faster speech recognition"
echo "- Use amy-low for fastest text-to-speech"
echo "- Use lessac-medium for higher quality voices"
